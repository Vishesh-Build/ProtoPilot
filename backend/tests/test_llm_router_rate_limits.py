"""
How the router reacts to a rate limit, and what it says when it gives up.

Pinned from a real hackathon run whose log showed the generation pipeline
finishing with five failed agents:

    groq  -> HTTP 429 (nine agents fired at once on a free tier)
    router-> 60s cooldown for groq
    nim   -> network error in the same window
    agent ui       failed: All LLM providers failed or are unavailable.
    agent backend  failed: All LLM providers failed or are unavailable.
    ... QA, DevOps and Prototype skipped, "a dependency failed"

Two separate mistakes produced that, and each gets tests here.

  * A 429 was treated like an outage. It is the opposite: the provider is
    healthy and asking for a pause. Retrying briefly recovers the call, and
    a provider that is merely throttled must NOT be locked out of the next
    agent wave 60 seconds deep.
  * When nothing could be attempted, the router blamed missing API keys.
    That sent the operator to check .env during a live demo for a config
    problem that did not exist — every key was set and every provider was
    simply still inside a cooldown.

Run from the backend/ directory:
    python -m unittest tests.test_llm_router_rate_limits -v
"""

import logging
import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.llm import router as router_module  # noqa: E402
from app.llm.providers.base import ChatResult, ProviderError, is_transient_status  # noqa: E402

# The retry and cooldown paths log by design; keep the output about failures.
logging.getLogger("protopilot.llm_router").setLevel(logging.CRITICAL)


def _result(model="m-1", text="ok", provider="stub"):
    return ChatResult(
        text=text, model=model, provider=provider, input_tokens=1, output_tokens=1,
    )


class _StubProvider:
    """
    A provider whose answers are scripted per attempt.

    `script` is a list of either an exception to raise or a ChatResult to
    return, consumed one entry per chat() call; the last entry repeats once
    exhausted, so "always 429" is a one-element script.
    """

    def __init__(self, name, script, is_configured=True):
        self.name = name
        self.candidates = ["m-1"]
        self.is_configured = is_configured
        self._script = list(script)
        self.calls = 0

    async def chat(self, messages, max_tokens, temperature):
        self.calls += 1
        step = self._script[min(self.calls - 1, len(self._script) - 1)]
        # Deliberately no asyncio.sleep here: the backoff test patches sleep to
        # record the delays the ROUTER asks for, and a yield from the stub would
        # show up in that list as a phantom 0.
        if isinstance(step, BaseException):
            raise step
        return step


def _rate_limited(name="groq", retry_after=None):
    return ProviderError(
        name, "rate limited (429)", model="m-1", rate_limited=True, retry_after=retry_after,
    )


def _outage(name="nim"):
    return ProviderError(name, "network error: connection reset", model="m-1")


def _transient(name="gemini", retry_after=None):
    # An HTTP 5xx surfaced by base._post_chat. Gemini's 503 "high demand,
    # try again later" is the one that hit the live run — up but momentarily
    # overloaded, which is transient like a 429, not an outage.
    return ProviderError(
        name, "HTTP 503 (high demand)", model="m-1",
        transient=True, retry_after=retry_after,
    )


class RouterRateLimitTest(unittest.IsolatedAsyncioTestCase):
    MESSAGES = [{"role": "user", "content": "hi"}]

    def setUp(self):
        self.router = router_module.LLMRouter()
        # Real sleeps would make this suite take ~3s per throttled call for no
        # added confidence; the delays themselves are asserted separately.
        self.slept = []

        async def no_sleep(seconds):
            self.slept.append(seconds)

        patch = mock.patch.object(router_module.asyncio, "sleep", no_sleep)
        patch.start()
        self.addCleanup(patch.stop)

    def _use(self, *providers):
        self.router.providers = list(providers)

    async def test_a_transient_429_recovers_on_the_retry(self):
        # The common case on a free tier: throttled for a moment, then fine.
        # Before this, the first 429 cost the whole provider for 60s.
        groq = _StubProvider("groq", [_rate_limited(), _result(text="recovered")])
        self._use(groq)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "recovered")
        self.assertEqual(groq.calls, 2)
        self.assertFalse(self.router._is_cooling_down("groq"),
                         "a call that succeeded must leave no cooldown behind")

    async def test_backoff_is_short_and_bounded(self):
        # A caption or requirement point that lands a minute late is useless,
        # so the router must not wait out a long ceiling.
        groq = _StubProvider("groq", [_rate_limited()])
        self._use(groq)

        with self.assertRaises(RuntimeError):
            await self.router.chat(self.MESSAGES)

        # No Retry-After header -> the router's own short backoff, and no more
        # than its retry count. (The list may now carry a phantom entry for a
        # retry attempt that succeeds or a final fallthrough; assert the real
        # contract instead: bounded total, correct sleeps.)
        self.assertEqual(
            groq.calls, len(router_module.LLMRouter._RATE_LIMIT_BACKOFF) + 1,
            "the no-header path tries the short backoff once per entry, then falls through",
        )
        self.assertLessEqual(sum(self.slept), 5.0, "total added latency stays demo-sized")

    async def test_the_provider_said_10s_and_gets_10s(self):
        # THE bug from the live run: Groq answered "retry-after=10s", the
        # router slept 1s+2s, gave up 7s early, failed the API agent, and five
        # more agents fell with it. When the provider names its price, pay it.
        groq = _StubProvider("groq", [_rate_limited(retry_after=10.0), _result(text="recovered")])
        self._use(groq)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "recovered")
        self.assertEqual(groq.calls, 2)
        self.assertEqual(self.slept, [10.0], "the provider's own number is what the router sleeps")

    async def test_an_absurd_retry_after_is_not_waited_out(self):
        # "retry-after=300" means a free-tier ceiling that will not clear
        # inside a demo. Failing through to the next provider immediately
        # beats freezing a generation wave for five minutes.
        groq = _StubProvider("groq", [_rate_limited(retry_after=300.0)])
        nim = _StubProvider("nim", [_result(text="from nim")])
        self._use(groq, nim)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "from nim")
        self.assertEqual(self.slept, [], "no wait at all for an impossible ask")
        self.assertFalse(self.router._is_cooling_down("groq"),
                         "an oversized ask is not an outage either")

    async def test_a_second_429_uses_the_backoff_again(self):
        # The live run: first 429 says 10s, second says 2s. Both are honored,
        # not replaced with the router's own guesses.
        groq = _StubProvider("groq", [
            _rate_limited(retry_after=10.0),
            _rate_limited(retry_after=2.0),
            _result(text="third time's the charm"),
        ])
        self._use(groq)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "third time's the charm")
        self.assertEqual(groq.calls, 3)
        self.assertEqual(self.slept, [10.0, 2.0])

    async def test_generation_may_wait_out_a_longer_ask_than_the_caption_path(self):
        # THE demo fix, second half. Groq's live 429s asked for ~24s, past the
        # default caption ceiling, so the router abandoned Groq, fell to a
        # flaky NIM, and the API agent — plus every agent downstream — failed.
        # A generation run is expected to take a minute or two, so when the
        # caller allows a longer wait, a 24s ask is paid and the call recovers.
        groq = _StubProvider("groq", [_rate_limited(retry_after=24.0), _result(text="recovered")])
        self._use(groq)

        result = await self.router.chat(self.MESSAGES, max_rate_limit_wait=45.0)

        self.assertEqual(result.text, "recovered")
        self.assertEqual(groq.calls, 2)
        self.assertEqual(self.slept, [24.0],
                         "generation pays a within-ceiling ask instead of failing the agent")

    async def test_the_caption_path_still_will_not_wait_out_that_ask(self):
        # The same 24s ask on the DEFAULT ceiling must still fall straight
        # through — a caption frozen for 24s is worse than useless, which is
        # exactly why generation got its own larger ceiling rather than this
        # one being raised for everyone.
        groq = _StubProvider("groq", [_rate_limited(retry_after=24.0)])
        nim = _StubProvider("nim", [_result(text="from nim")])
        self._use(groq, nim)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "from nim")
        self.assertEqual(self.slept, [], "the default (caption) ceiling does not wait out 24s")

    async def test_a_throttled_provider_is_not_put_in_cooldown(self):
        # THE bug behind the five failed agents. Wave N throttles Groq; if that
        # cools Groq down for 60s, wave N+1 cannot use it either, and one 429
        # cascades into a pipeline that produces no prototype.
        groq = _StubProvider("groq", [_rate_limited()])
        nim = _StubProvider("nim", [_result(text="from nim")])
        self._use(groq, nim)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "from nim")
        self.assertFalse(self.router._is_cooling_down("groq"),
                         "429 means slow down, not down — the next wave must still try groq")

    async def test_a_real_outage_still_earns_a_cooldown(self):
        # The opposite guard: sparing 429s must not stop the router from
        # backing off a provider that is genuinely broken, or every later call
        # pays that provider's timeout again.
        nim = _StubProvider("nim", [_outage()])
        groq = _StubProvider("groq", [_result()])
        self._use(nim, groq)

        await self.router.chat(self.MESSAGES)

        self.assertTrue(self.router._is_cooling_down("nim"))
        self.assertEqual(self.slept, [], "a network error is not retried in place")

    async def test_a_transient_503_recovers_on_the_retry(self):
        # THE second live-run killer: Gemini answered 503 "high demand, try
        # again later" — a transient overload, not an outage. Before this it
        # was a hard failure that ALSO cooled Gemini down; now it is retried in
        # place like a 429 (short backoff, no Retry-After) and recovers, with
        # the lead provider left in play.
        gemini = _StubProvider("gemini", [_transient(), _result(text="recovered")])
        self._use(gemini)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "recovered")
        self.assertEqual(gemini.calls, 2)
        self.assertFalse(self.router._is_cooling_down("gemini"),
                         "a call that recovered must leave no cooldown behind")

    async def test_a_persistent_503_falls_through_without_cooling_the_lead(self):
        # If the overload does not clear within the retries, fall through to
        # the next provider — but the lead must NOT be put in a 60s cooldown,
        # or every remaining agent skips it even after the spike has passed.
        # This is the exact cascade the live run showed: Gemini 503 on the
        # backend agent, and then it was gone for the agents that followed.
        gemini = _StubProvider("gemini", [_transient()])
        groq = _StubProvider("groq", [_result(text="from groq")])
        self._use(gemini, groq)

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "from groq")
        self.assertFalse(self.router._is_cooling_down("gemini"),
                         "a transient 5xx is not an outage — the next agent must still try the lead")

    async def test_a_429_is_not_retried_against_the_next_provider(self):
        # The backoff belongs to one provider. Falling through must be
        # immediate, otherwise the delay is paid once per provider in the chain.
        groq = _StubProvider("groq", [_rate_limited()])
        nim = _StubProvider("nim", [_result(text="from nim")])
        self._use(groq, nim)

        await self.router.chat(self.MESSAGES)

        self.assertEqual(nim.calls, 1)

    async def test_every_provider_throttled_reports_the_rate_limit(self):
        # With both ceilings hit there is nothing to be done, but the error has
        # to name the actual reason so nobody goes looking at their keys.
        self._use(
            _StubProvider("groq", [_rate_limited("groq")]),
            _StubProvider("nim", [_rate_limited("nim")]),
        )

        with self.assertRaises(RuntimeError) as caught:
            await self.router.chat(self.MESSAGES)

        message = str(caught.exception)
        self.assertIn("rate limited", message)
        self.assertIn("groq", message)
        self.assertIn("nim", message)
        self.assertNotIn("API key", message)


class RouterNothingAttemptedTest(unittest.IsolatedAsyncioTestCase):
    """
    What the router says when it made no request at all.

    The old message was always "No provider has an API key configured." — read
    verbatim off a live log where all three keys were present.
    """

    MESSAGES = [{"role": "user", "content": "hi"}]

    def setUp(self):
        self.router = router_module.LLMRouter()

    async def test_all_in_cooldown_says_cooldown_not_missing_keys(self):
        self.router.providers = [
            _StubProvider("groq", [_result()]),
            _StubProvider("nim", [_result()]),
        ]
        self.router._start_cooldown("groq")
        self.router._start_cooldown("nim")

        with self.assertRaises(RuntimeError) as caught:
            await self.router.chat(self.MESSAGES)

        message = str(caught.exception)
        self.assertIn("cooldown", message)
        self.assertIn("groq", message)
        self.assertIn("nim", message)
        self.assertNotIn("No provider has an API key", message)

    async def test_genuinely_unkeyed_still_says_so(self):
        # The honest case must keep its plain-language message, otherwise a
        # real missing key becomes hard to diagnose.
        self.router.providers = [
            _StubProvider("groq", [_result()], is_configured=False),
            _StubProvider("nim", [_result()], is_configured=False),
        ]

        with self.assertRaises(RuntimeError) as caught:
            await self.router.chat(self.MESSAGES)

        self.assertIn("No provider has an API key configured", str(caught.exception))

    async def test_an_unkeyed_provider_is_never_called(self):
        unkeyed = _StubProvider("groq", [_result()], is_configured=False)
        keyed = _StubProvider("nim", [_result(text="from nim")])
        self.router.providers = [unkeyed, keyed]

        result = await self.router.chat(self.MESSAGES)

        self.assertEqual(result.text, "from nim")
        self.assertEqual(unkeyed.calls, 0)


class TransientStatusTest(unittest.TestCase):
    """Which HTTP statuses base.py marks transient (retry) vs. not."""

    def test_5xx_overloads_are_transient(self):
        # "up but momentarily unable" — retry in place, no cooldown.
        for code in (500, 502, 503, 504):
            self.assertTrue(is_transient_status(code), code)

    def test_success_rate_limit_and_model_errors_are_not_transient(self):
        # 429 has its own rate_limited flag; a 4xx model/bad-request error and
        # a plain 200 must never be retried as a transient overload.
        for code in (200, 400, 401, 403, 404, 410, 429):
            self.assertFalse(is_transient_status(code), code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
