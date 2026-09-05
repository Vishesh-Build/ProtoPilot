"""
Model-id resolution: the bug this pins down is a dead demo.

On one day NVIDIA NIM answered `410 Gone` for meta/llama-3.1-8b-instruct
(end-of-life 2026-08-26) and Groq answered `404` for llama-3.1-8b-instant
(retired 2026-06-17). Translation, requirement extraction and all nine
agents go through the same router, so a 30-minute meeting produced a
transcript stuck in the original language and a Points panel that stayed
empty, with nothing on screen saying why.

The provider now holds a list of candidate ids and, on a "model gone"
answer, asks the provider's own GET /v1/models what it serves today and
retries once. These tests cover that path without touching the network.

Run from the backend/ directory:
    python -m unittest discover -s tests -t . -v
"""

import asyncio
import json
import logging
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.llm.providers import base as provider_base  # noqa: E402
from app.llm.providers.base import (  # noqa: E402
    ChatResult,
    OpenAICompatibleProvider,
    ProviderError,
    extract_reply_text,
    looks_like_model_error,
    parse_model_list,
    parse_retry_after,
    pick_model,
    rank_chat_models,
)

# The retry path logs a warning on purpose; keep the output about assertions.
logging.getLogger("protopilot.llm_provider").setLevel(logging.CRITICAL)


class ParseModelListTest(unittest.TestCase):
    """pydantic-settings hands env vars over as strings, never as lists."""

    def test_comma_separated_env_string(self):
        self.assertEqual(
            parse_model_list("openai/gpt-oss-20b,openai/gpt-oss-120b"),
            ["openai/gpt-oss-20b", "openai/gpt-oss-120b"],
        )

    def test_real_list_passes_through(self):
        self.assertEqual(parse_model_list(["a", "b"]), ["a", "b"])

    def test_whitespace_and_empty_segments_are_dropped(self):
        self.assertEqual(parse_model_list(" a , , b ,"), ["a", "b"])

    def test_duplicates_are_removed_but_order_is_kept(self):
        # Order is the preference order, so it must survive de-duplication.
        self.assertEqual(parse_model_list("b,a,b,c,a"), ["b", "a", "c"])

    def test_nothing_configured(self):
        self.assertEqual(parse_model_list(None), [])
        self.assertEqual(parse_model_list(""), [])
        self.assertEqual(parse_model_list([]), [])


class ModelErrorDetectionTest(unittest.TestCase):
    """
    Only "this model is gone" may trigger rediscovery. Treating a rate limit
    or an outage as a dead model would swap a working id for no reason.
    """

    def test_the_two_statuses_seen_in_production(self):
        self.assertTrue(looks_like_model_error(404, "model not found"))   # Groq
        self.assertTrue(looks_like_model_error(410, "model is EOL"))      # NIM

    def test_transient_failures_are_not_model_errors(self):
        for status in (429, 500, 502, 503, 200):
            self.assertFalse(looks_like_model_error(status, "whatever"), status)

    def test_400_is_decided_by_the_body(self):
        self.assertTrue(looks_like_model_error(
            400, "The model `llama-3.1-8b-instant` has been decommissioned"))
        self.assertTrue(looks_like_model_error(400, "this model reached end-of-life"))
        self.assertFalse(looks_like_model_error(400, "invalid api key"))
        self.assertFalse(looks_like_model_error(400, ""))


class PickModelTest(unittest.TestCase):
    def test_configured_order_wins_not_served_order(self):
        # Predictability matters more than what happens to sort first: the
        # first configured candidate is the one that was chosen on purpose.
        served = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        candidates = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
        self.assertEqual(pick_model(served, candidates), "openai/gpt-oss-20b")

    def test_falls_through_to_the_next_candidate_that_is_served(self):
        self.assertEqual(
            pick_model(["openai/gpt-oss-120b"], ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]),
            "openai/gpt-oss-120b",
        )

    def test_same_model_behind_a_different_namespace(self):
        # Groq serves "openai/gpt-oss-20b", other gateways serve "gpt-oss-20b".
        self.assertEqual(pick_model(["gpt-oss-20b"], ["openai/gpt-oss-20b"]), "gpt-oss-20b")
        self.assertEqual(pick_model(["openai/gpt-oss-20b"], ["gpt-oss-20b"]), "openai/gpt-oss-20b")

    def test_non_chat_models_are_never_picked(self):
        # These endpoints list embeddings, ASR and TTS next to chat models,
        # and picking one would fail far more confusingly than a dead id.
        served = [
            "nvidia/nv-embedqa-e5-v5", "whisper-large-v3", "playai-tts",
            "meta/llama-guard-4-12b", "nvidia/nemoretriever-parse",
        ]
        self.assertIsNone(pick_model(served, ["meta/llama-3.1-8b-instruct"]))

    def test_heuristic_prefers_an_instruct_model_near_20b(self):
        served = ["some-base-model", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]
        self.assertEqual(pick_model(served, ["a-model-nobody-serves"]), "openai/gpt-oss-20b")

    def test_heuristic_still_answers_when_nothing_is_instruct_tuned(self):
        self.assertEqual(pick_model(["mystery-24b", "mystery-400b"], []), "mystery-24b")

    def test_nothing_served_means_leave_the_model_alone(self):
        self.assertIsNone(pick_model([], ["openai/gpt-oss-20b"]))

    def test_the_actual_nim_regression(self):
        # The configured id was EOL; NIM still served plenty of chat models.
        served = [
            "meta/llama-3.3-70b-instruct",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nv-embedqa-e5-v5",
        ]
        candidates = [
            "meta/llama-3.3-70b-instruct",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "meta/llama-3.1-8b-instruct",
        ]
        self.assertEqual(pick_model(served, candidates), "meta/llama-3.3-70b-instruct")


class RankChatModelsTest(unittest.TestCase):
    """
    preflight.py prints this order so the preference list in config.py can be
    edited from evidence. It must therefore agree with what pick_model would
    actually do, which is why both call the same function.
    """

    def test_non_chat_entries_are_dropped(self):
        served = ["nvidia/nv-embedqa-e5-v5", "whisper-large-v3", "openai/gpt-oss-20b"]
        self.assertEqual(rank_chat_models(served), ["openai/gpt-oss-20b"])

    def test_instruct_tuned_ids_come_first(self):
        ranked = rank_chat_models(["mystery-22b", "llama-3.3-70b-instruct"])
        self.assertEqual(ranked[0], "llama-3.3-70b-instruct")

    def test_the_head_is_what_pick_model_falls_back_to(self):
        served = ["some-base-model", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]
        self.assertEqual(rank_chat_models(served)[0], pick_model(served, ["nobody-serves-this"]))


class ExtractReplyTextTest(unittest.TestCase):
    """
    An HTTP 200 is not an answer. This is the check that stops an empty
    envelope from being handed to the requirement extractor, where it looks
    exactly like a meeting in which nobody asked for anything.
    """

    @staticmethod
    def _reply(message, finish_reason="stop"):
        return {"choices": [{"message": message, "finish_reason": finish_reason}]}

    def test_normal_answer(self):
        text, problem = extract_reply_text(self._reply({"content": "  ready  "}))
        self.assertEqual(text, "ready")
        self.assertEqual(problem, "")

    def test_the_groq_gpt_oss_case_reasoning_ate_the_budget(self):
        # content: null + finish_reason: length + text in `reasoning` is the
        # exact envelope that crashed preflight on .strip().
        text, problem = extract_reply_text(self._reply(
            {"content": None, "reasoning": "The user wants one word. I should..."},
            finish_reason="length",
        ))
        self.assertEqual(text, "")
        self.assertIn("reasoning", problem)
        self.assertIn("max_tokens", problem)
        self.assertIn("finish_reason=length", problem)

    def test_the_other_reasoning_key(self):
        _, problem = extract_reply_text(self._reply(
            {"content": "", "reasoning_content": "thinking out loud"}))
        self.assertIn("reasoning", problem)

    def test_truncated_before_any_visible_text(self):
        _, problem = extract_reply_text(self._reply({"content": ""}, finish_reason="length"))
        self.assertIn("cut off", problem)
        self.assertIn("max_tokens", problem)

    def test_whitespace_only_is_not_an_answer(self):
        text, problem = extract_reply_text(self._reply({"content": "   \n "}))
        self.assertEqual(text, "")
        self.assertTrue(problem)

    def test_content_as_a_list_of_parts(self):
        # Some gateways answer with typed content parts instead of a string.
        text, problem = extract_reply_text(self._reply(
            {"content": [{"type": "text", "text": "rea"}, {"type": "text", "text": "dy"}]}))
        self.assertEqual(text, "ready")
        self.assertEqual(problem, "")

    def test_shapes_that_are_not_replies_at_all(self):
        for payload in ({}, {"choices": []}, {"choices": [None]}, [], None, "nope"):
            text, problem = extract_reply_text(payload)
            self.assertEqual(text, "", payload)
            self.assertTrue(problem, payload)

    def test_the_problem_names_the_finish_reason_it_did_get(self):
        _, problem = extract_reply_text(self._reply({"content": None},
                                                    finish_reason="content_filter"))
        self.assertIn("content_filter", problem)


class _FakeProvider(OpenAICompatibleProvider):
    """
    A real provider with the two HTTP methods replaced. Everything under
    test — the retry decision, the lock, the dead-id bookkeeping — is the
    real implementation. Both fakes await, so coroutines actually interleave
    and the concurrency test means something.
    """

    name = "fake"

    def __init__(self, served, candidates, dead=()):
        super().__init__(
            base_url="https://example.invalid/v1",
            api_key="test-key",
            models=candidates,
            timeout=1.0,
        )
        self.served = list(served)
        self.dead = set(dead)
        self.attempts: list[str] = []
        self.list_models_calls = 0

    async def list_models(self):
        await asyncio.sleep(0)
        self.list_models_calls += 1
        return list(self.served)

    async def _post_chat(self, messages, max_tokens, temperature):
        model = self.model
        await asyncio.sleep(0)
        self.attempts.append(model)
        if model in self.dead:
            raise ProviderError(
                self.name, f"HTTP 410 for model {model!r}: end of life",
                model_gone=True, model=model,
            )
        return ChatResult(text="ready", provider=self.name, model=model)


class RediscoveryTest(unittest.IsolatedAsyncioTestCase):
    MESSAGES = [{"role": "user", "content": "hi"}]

    async def _chat(self, provider):
        return await provider.chat(self.MESSAGES, max_tokens=8, temperature=0.0)

    async def test_dead_model_is_replaced_and_retried_once(self):
        provider = _FakeProvider(
            served=["alive-70b-instruct"],
            candidates=["dead-8b", "alive-70b-instruct"],
            dead=["dead-8b"],
        )
        result = await self._chat(provider)
        self.assertEqual(result.text, "ready")
        self.assertEqual(result.model, "alive-70b-instruct")
        self.assertEqual(provider.attempts, ["dead-8b", "alive-70b-instruct"])
        self.assertEqual(provider.model, "alive-70b-instruct")
        self.assertEqual(provider.list_models_calls, 1)

    async def test_only_one_retry_then_the_error_propagates(self):
        # Otherwise a provider whose whole list is dead would retry forever
        # instead of letting the router move on to the next provider.
        provider = _FakeProvider(
            served=["also-dead"], candidates=["dead-8b", "also-dead"],
            dead=["dead-8b", "also-dead"],
        )
        with self.assertRaises(ProviderError):
            await self._chat(provider)
        self.assertEqual(len(provider.attempts), 2)

    async def test_a_rate_limit_never_touches_the_model(self):
        provider = _FakeProvider(served=["something-else"], candidates=["good-model"])
        provider.dead = set()

        async def rate_limited(messages, max_tokens, temperature):
            provider.attempts.append(provider.model)
            raise ProviderError(provider.name, "rate limited (429)", model=provider.model)

        provider._post_chat = rate_limited
        with self.assertRaises(ProviderError):
            await self._chat(provider)
        self.assertEqual(provider.attempts, ["good-model"])
        self.assertEqual(provider.model, "good-model")
        self.assertEqual(provider.list_models_calls, 0)

    async def test_unanswerable_models_endpoint_leaves_the_id_alone(self):
        # list_models() returns [] for "couldn't ask", which must not be read
        # as "this provider has no models" — that would wipe a working id.
        provider = _FakeProvider(served=[], candidates=["dead-8b"], dead=["dead-8b"])
        with self.assertRaises(ProviderError):
            await self._chat(provider)
        self.assertEqual(provider.model, "dead-8b")
        self.assertEqual(provider.attempts, ["dead-8b"])

    async def test_a_retired_id_is_never_chosen_again(self):
        provider = _FakeProvider(
            served=["dead-a", "dead-b", "alive-c-instruct"],
            candidates=["dead-a", "dead-b", "alive-c-instruct"],
            dead=["dead-a"],
        )
        await self._chat(provider)
        self.assertEqual(provider.model, "dead-b")

        # dead-b dies later in the same session, the way a staggered
        # deprecation schedule actually retires models.
        provider.dead.add("dead-b")
        result = await self._chat(provider)
        self.assertEqual(result.model, "alive-c-instruct")
        self.assertEqual(provider._dead_models, {"dead-a", "dead-b"})

    async def test_nine_concurrent_agents_ask_the_models_endpoint_once(self):
        # The 9-agent pipeline fans out at once. Every one of them hits the
        # dead id, and they must not each independently GET /models.
        provider = _FakeProvider(
            served=["alive-70b-instruct"],
            candidates=["dead-8b", "alive-70b-instruct"],
            dead=["dead-8b"],
        )
        results = await asyncio.gather(*(self._chat(provider) for _ in range(9)))

        self.assertEqual([r.model for r in results], ["alive-70b-instruct"] * 9)
        self.assertEqual(provider.list_models_calls, 1)
        # The replacement must not be marked dead by the eight failures that
        # were already in flight when it was installed.
        self.assertEqual(provider._dead_models, {"dead-8b"})
        self.assertEqual(provider.model, "alive-70b-instruct")

    async def test_a_failure_arriving_after_the_swap_does_not_poison_the_replacement(self):
        # The nine agents don't fail in lockstep. One can still be in flight
        # with the dead id when another installs the replacement, and that
        # late failure must not retire the model that is now working.
        provider = _FakeProvider(
            served=["alive-70b-instruct"],
            candidates=["dead-8b", "alive-70b-instruct"],
            dead=["dead-8b"],
        )
        calls = {"n": 0}

        async def staggered(messages, max_tokens, temperature):
            model = provider.model  # read at entry, as the real client does
            calls["n"] += 1
            if calls["n"] == 2:
                # The second caller went out with the dead id; hold its
                # failure until the first caller has installed the new one.
                for _ in range(100):
                    if provider.model != "dead-8b":
                        break
                    await asyncio.sleep(0)
            provider.attempts.append(model)
            if model in provider.dead:
                raise ProviderError(
                    provider.name, f"HTTP 410 for model {model!r}: end of life",
                    model_gone=True, model=model,
                )
            return ChatResult(text="ready", provider=provider.name, model=model)

        provider._post_chat = staggered
        results = await asyncio.gather(self._chat(provider), self._chat(provider))

        self.assertEqual([r.model for r in results], ["alive-70b-instruct"] * 2)
        self.assertEqual(provider._dead_models, {"dead-8b"},
                         "the late failure blamed the replacement instead of the id it used")
        self.assertEqual(provider.list_models_calls, 1)

    async def test_no_key_and_no_model_fail_before_any_request(self):
        unkeyed = _FakeProvider(served=[], candidates=["m"])
        unkeyed.api_key = None
        with self.assertRaises(ProviderError):
            await self._chat(unkeyed)

        modelless = _FakeProvider(served=[], candidates=[])
        with self.assertRaises(ProviderError):
            await self._chat(modelless)
        self.assertEqual(modelless.attempts, [])


class _FakeHttpResponse:
    """Just enough of an httpx.Response for _post_chat to read."""

    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)
        # Real responses always have headers; _post_chat reads Retry-After on a
        # 429. Defaulting to {} keeps every existing caller working.
        self.headers = headers or {}

    def json(self):
        return self._payload


def _client_answering(response):
    """
    An httpx.AsyncClient stand-in, so the *real* _post_chat runs — the
    response-shape handling is the code under test here, and going through
    a fake provider would skip exactly the lines that matter.
    """
    class _FakeAsyncClient:
        posts: list[dict] = []

        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def post(self, url, headers=None, json=None):  # noqa: A002
            _FakeAsyncClient.posts.append(json)
            await asyncio.sleep(0)
            return response

        async def get(self, url, headers=None):
            raise AssertionError("an empty reply must not trigger model rediscovery")

    _FakeAsyncClient.posts = []
    return _FakeAsyncClient


class RateLimitTest(unittest.IsolatedAsyncioTestCase):
    """
    HTTP 429 is the provider saying "slow down", not "I am down".

    A real run put nine agents on Groq's free tier at once; the first 429 sent
    the whole provider into a 60s cooldown, NIM had a network blip in the same
    window, and five agents (UI, Backend, QA, DevOps, Prototype) failed — so
    the prototype the demo exists to show was never generated.
    """

    MESSAGES = [{"role": "user", "content": "hi"}]

    def _provider(self):
        return OpenAICompatibleProvider(
            base_url="https://example.invalid/v1", api_key="test-key",
            models=["m-20b"], timeout=1.0,
        )

    async def test_a_429_is_flagged_rate_limited_and_spares_the_model(self):
        client = _client_answering(_FakeHttpResponse({}, status_code=429))
        with mock.patch.object(provider_base.httpx, "AsyncClient", client):
            with self.assertRaises(ProviderError) as caught:
                await self._provider().chat(self.MESSAGES, 64, 0.0)

        error = caught.exception
        self.assertTrue(error.rate_limited)
        # Being throttled says nothing about the model id, and retiring a
        # working one because of a 429 is a bug this suite already pins.
        self.assertFalse(error.model_gone)
        self.assertEqual(error.model, "m-20b")

    async def test_retry_after_is_reported_when_the_provider_sends_one(self):
        client = _client_answering(
            _FakeHttpResponse({}, status_code=429, headers={"retry-after": "7"})
        )
        with mock.patch.object(provider_base.httpx, "AsyncClient", client):
            with self.assertRaises(ProviderError) as caught:
                await self._provider().chat(self.MESSAGES, 64, 0.0)
        self.assertIn("retry-after=7s", caught.exception.message)

    async def test_a_missing_retry_after_header_does_not_crash(self):
        # _FakeHttpResponse gained `headers` for this: reading resp.headers on a
        # response that has none is an AttributeError at the exact moment the
        # provider is already struggling.
        client = _client_answering(_FakeHttpResponse({}, status_code=429))
        with mock.patch.object(provider_base.httpx, "AsyncClient", client):
            with self.assertRaises(ProviderError) as caught:
                await self._provider().chat(self.MESSAGES, 64, 0.0)
        self.assertIn("rate limited (429)", caught.exception.message)
        self.assertNotIn("retry-after", caught.exception.message)

    async def test_retry_after_is_carried_as_seconds_on_the_error(self):
        # The router needs the NUMBER, not a string in the message: sleeping
        # "10s" requires parsing the header. The old code only put it in the
        # log line and the router retried after its own 1s+2s — 7s before the
        # provider said it would be ready. That cost the whole pipeline.
        client = _client_answering(
            _FakeHttpResponse({}, status_code=429, headers={"retry-after": "10"})
        )
        with mock.patch.object(provider_base.httpx, "AsyncClient", client):
            with self.assertRaises(ProviderError) as caught:
                await self._provider().chat(self.MESSAGES, 64, 0.0)
        self.assertEqual(caught.exception.retry_after, 10.0)
        self.assertIn("retry-after=10s", caught.exception.message)


class RetryAfterHeaderTest(unittest.TestCase):
    """Parsing the Retry-After header itself, in both its forms."""

    def test_a_plain_number_of_seconds(self):
        self.assertEqual(parse_retry_after("10"), 10.0)
        self.assertEqual(parse_retry_after(" 7 "), 7.0)
        self.assertEqual(parse_retry_after("2.5"), 2.5)

    def test_an_http_date_is_converted_to_seconds_from_now(self):
        # Some providers (Groq among them) send an absolute time instead of a
        # count. This is computed against now, so assert a window, not a number.
        when = datetime.now(timezone.utc) + timedelta(seconds=8)
        value = when.strftime("%a, %d %b %Y %H:%M:%S GMT")
        parsed = parse_retry_after(value)
        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(parsed, 5.0)
        self.assertLessEqual(parsed, 9.0)

    def test_a_past_date_means_no_wait_at_all(self):
        value = "Mon, 01 Jan 2001 00:00:00 GMT"
        self.assertEqual(parse_retry_after(value), 0.0)

    def test_garbage_returns_none_for_the_fallback(self):
        self.assertIsNone(parse_retry_after(""))
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after("soon"))
        self.assertIsNone(parse_retry_after("-3"))
        self.assertIsNone(parse_retry_after("tomorrow"))


class EmptyReplyOverHttpTest(unittest.IsolatedAsyncioTestCase):
    MESSAGES = [{"role": "user", "content": "hi"}]

    def _provider(self):
        return OpenAICompatibleProvider(
            base_url="https://example.invalid/v1", api_key="test-key",
            models=["m-20b"], timeout=1.0,
        )

    async def _send(self, payload):
        client = _client_answering(_FakeHttpResponse(payload))
        with mock.patch.object(provider_base.httpx, "AsyncClient", client):
            try:
                result = await self._provider().chat(self.MESSAGES, 64, 0.0)
            except ProviderError as e:
                return None, e, client
            return result, None, client

    async def test_a_real_answer_still_comes_through(self):
        result, error, _ = await self._send({
            "choices": [{"message": {"content": " ready "}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 2},
        })
        self.assertIsNone(error)
        self.assertEqual(result.text, "ready")
        self.assertEqual((result.input_tokens, result.output_tokens), (11, 2))

    async def test_an_empty_reply_is_an_error_not_a_result(self):
        # The whole point: nine agents and the extractor parse result.text,
        # and returning "" here is what emptied the Points panel.
        _, error, client = await self._send({
            "choices": [{"message": {"content": None, "reasoning": "thinking..."},
                         "finish_reason": "length"}],
        })
        self.assertIsNotNone(error)
        self.assertIn("empty reply", error.message)
        self.assertIn("max_tokens", error.message)
        self.assertEqual(error.model, "m-20b")
        # Not a dead id, so it must not retire the model or ask /models.
        self.assertFalse(error.model_gone)
        self.assertEqual(len(client.posts), 1, "an empty reply must not be retried blindly")

    async def test_a_missing_usage_block_does_not_crash(self):
        result, error, _ = await self._send({"choices": [{"message": {"content": "ok"}}]})
        self.assertIsNone(error)
        self.assertIsNone(result.input_tokens)

    async def test_a_garbled_envelope_is_reported_as_such(self):
        _, error, _ = await self._send({"unexpected": True})
        self.assertIsNotNone(error)
        self.assertIn("no choices", error.message)


class NetworkErrorMessageTest(unittest.IsolatedAsyncioTestCase):
    """
    A provider network failure had to say WHAT happened.

    The live log read:

        WARNING:protopilot.llm_router:nim failed: network error:
        WARNING:protopilot.agents:agent api failed: All LLM providers failed...

    "network error:" with nothing after the colon. httpx timeouts stringify
    to an empty string, so the message gave a person looking at the log a
    void exactly where the cause should have been — it read like "NIM is
    down" when the call had simply timed out.
    """

    MESSAGES = [{"role": "user", "content": "hi"}]

    def _provider(self):
        return OpenAICompatibleProvider(
            base_url="https://example.invalid/v1", api_key="test-key",
            models=["m-20b"], timeout=1.0,
        )

    async def _send_through_a_raising_client(self, error):
        class _FakeAsyncClient:
            def __init__(self, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc_info):
                return False

            async def post(self, url, headers=None, json=None):  # noqa: A002
                raise error

        with mock.patch.object(provider_base.httpx, "AsyncClient", _FakeAsyncClient):
            with self.assertRaises(ProviderError) as caught:
                await self._provider().chat(self.MESSAGES, 64, 0.0)
        return caught.exception.message

    async def test_a_timeout_names_the_exception_class(self):
        message = await self._send_through_a_raising_client(
            provider_base.httpx.RequestError("Read timed out")
        )
        self.assertIn("network error", message)
        self.assertIn("RequestError", message, "the exception CLASS must be named")

    async def test_an_empty_exception_string_still_names_the_class(self):
        # The exact live case: httpx times out, str(e) == "".
        message = await self._send_through_a_raising_client(
            provider_base.httpx.RequestError("")
        )
        self.assertIn("network error", message)
        self.assertIn("RequestError", message)
        self.assertNotEqual(message.rstrip(), "network error:", "must not end on a void")


if __name__ == "__main__":
    unittest.main()
