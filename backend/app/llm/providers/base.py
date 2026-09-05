"""
Shared interface for LLM providers.

NIM, OpenRouter, and Groq all expose an OpenAI-compatible
`/chat/completions` endpoint, so a single implementation covers all
three — only base_url, api_key, and model differ.

Model ids are not stable, and that is the expensive lesson baked into
this file. On the same day NVIDIA NIM answered `410 Gone` for
meta/llama-3.1-8b-instruct (end-of-life 2026-08-26) and Groq answered
`404` for llama-3.1-8b-instant (retired 2026-06-17). Translation,
requirement extraction and the entire 9-agent pipeline all go through
this class, so those two retirements together meant a live meeting
produced captions stuck in the original language and a permanently
empty Points panel, with nothing on screen explaining why.

So a provider holds a *list* of candidate model ids instead of one, and
when the API says the current id is gone it asks that provider's own
`GET /v1/models` endpoint what it actually serves today, picks the best
match itself, and retries. The next retirement then costs one extra
HTTP round trip instead of a dead demo — nobody should be editing .env
fifteen minutes before a presentation.

The second lesson is quieter and cost just as much: an HTTP 200 does not
mean there is an answer in the envelope. Reasoning models (gpt-oss and
friends) think in tokens that come out of the same `max_tokens` budget,
so a budget that is too small for the task returns
`"content": null, "finish_reason": "length"` — a perfectly successful
request carrying nothing. Downstream, the extractor parses that empty
string, finds no JSON, and the Points panel stays empty with nothing in
the log. `extract_reply_text` therefore treats "no visible text" as a
failure with a stated cause, so the router falls through to the next
provider instead of passing an empty string on as a result.
"""

import asyncio
import email.utils
import logging
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import httpx

logger = logging.getLogger("protopilot.llm_provider")

class ProviderError(Exception):
    """Raised when a provider fails to respond successfully.
    The router catches this and moves to the next provider in the chain."""

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        model_gone: bool = False,
        model: str | None = None,
        rate_limited: bool = False,
        retry_after: float | None = None,
        transient: bool = False,
    ):
        self.provider = provider
        self.message = message
        # True only for HTTP 429. Like model_gone, this is emphatically NOT an
        # outage: the provider is healthy and is asking us to slow down. Nine
        # agents fire at once, so hitting a free tier's per-minute ceiling is
        # routine — and a 60s cooldown for it took the whole provider away and
        # failed five agents (UI, Backend, QA, DevOps, Prototype) in one wave.
        self.rate_limited = rate_limited
        # The pause the provider asked for, in seconds, when it said one
        # (Retry-After header). The router sleeps this long — asking for 10s
        # and retrying after 3 is giving up on a provider that would have
        # answered. When the header is absent, the router falls back to its
        # own short backoff.
        self.retry_after = retry_after
        # True for a transient server-side hiccup: an HTTP 5xx / "high demand,
        # try again later" (Gemini answers 503 for exactly this). Like a 429
        # this is NOT an outage — the provider is up and the model exists, it
        # is momentarily overloaded — so the router retries it in place with a
        # short backoff and, crucially, does NOT cool the provider down for
        # 60s: a transient spike clears in seconds and the lead provider has to
        # stay in play for the next agent. A live run died exactly here —
        # Gemini 503'd once, was treated as a hard failure plus a 60s cooldown,
        # and three agents fell with it.
        self.transient = transient
        # True only when the failure was specifically "this model id no
        # longer exists". The router treats that differently from a rate
        # limit or an outage: putting a provider in a 60s cooldown because
        # of a dead *model id* would only delay finding the working one.
        self.model_gone = model_gone
        # Which model id this request actually used. Carried on the error
        # because nine agents call chat() at once: by the time a failure is
        # handled, self.model may already have been swapped by another
        # coroutine, and blaming the *current* id would retire a model that
        # is working perfectly well.
        self.model = model
        super().__init__(f"[{provider}] {message}")


@dataclass
class ChatResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


# 404 = "no such model" (Groq, OpenRouter), 410 = "model reached end of
# life" (NVIDIA NIM). Some gateways instead answer 400 with the reason in
# the body, so in that case the body is inspected rather than trusting the
# status code alone.
_MODEL_GONE_STATUSES = {404, 410}
_MODEL_GONE_HINTS = (
    "model", "decommission", "deprecat", "end of life", "end-of-life",
    "no longer supported", "does not exist", "not found", "retired",
)

# Substrings that mark a /models entry as something other than a chat
# model. These endpoints list embedding, rerank, ASR, TTS and image models
# right next to chat models, and silently picking one of those would fail
# in a far more confusing way than the dead id being replaced.
_NOT_CHAT = (
    "embed", "rerank", "whisper", "tts", "stt", "speech", "voice", "audio",
    "guard", "safety", "moderation", "shield", "image", "video", "vision",
    "sdxl", "flux", "diffusion", "ocr", "retrieval", "playai", "riva",
    "nemoretriever", "parakeet", "canary", "clip",
)

_PARAM_COUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b(?![a-z0-9])")

# Where a reasoning model puts its chain of thought when `content` is empty.
# Finding text here is the tell-tale of an exhausted token budget, so it is
# quoted in the error — but never used as the answer, because thinking is not
# an answer and feeding it to the JSON extractor would produce nonsense.
_REASONING_KEYS = ("reasoning", "reasoning_content")

# Ties are broken towards this parameter count: small enough to answer
# while a meeting is still running, big enough to obey the extractor's
# "reply with a JSON array and nothing else" instruction.
_PREFERRED_PARAM_COUNT = 20.0


def parse_model_list(models: str | list[str] | None) -> list[str]:
    """
    Accepts either a real list or one comma-separated env value
    (`GROQ_MODELS=openai/gpt-oss-20b,openai/gpt-oss-120b`), because
    pydantic-settings hands env vars over as plain strings.
    """
    if not models:
        return []
    if isinstance(models, str):
        models = models.split(",")
    seen: set[str] = set()
    ordered: list[str] = []
    for model in models:
        model = model.strip()
        if model and model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered


def parse_retry_after(value: str | None) -> float | None:
    """
    The Retry-After header in seconds (or, rarely, as an HTTP-date).

    Returns None for anything that isn't a usable number — a missing header,
    a mangled value — so the caller can fall back to its own backoff. The
    header is the provider's *ask*, not a suggestion: ignoring it and
    retrying sooner is how one live 429 ("retry-after=10s") became a failed
    agent, then five more, then no prototype for the demo.
    """
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return seconds if seconds >= 0 else None
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None or when.tzinfo is None:
        return None
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def looks_like_model_error(status_code: int, body: str) -> bool:
    if status_code in _MODEL_GONE_STATUSES:
        return True
    if status_code == 400:
        low = body.lower()
        return any(hint in low for hint in _MODEL_GONE_HINTS)
    return False


# 5xx that mean "up but momentarily unable" rather than "model gone" or "bad
# request": retry with backoff instead of failing the provider. 503 is
# Gemini's "high demand, try again later"; 500/502/504 are the usual gateway
# hiccups. A transient error is retried in place and — unlike a real outage —
# never earns a 60s cooldown, so the lead provider is still tried next agent.
_TRANSIENT_STATUSES = {500, 502, 503, 504}


def is_transient_status(status_code: int) -> bool:
    return status_code in _TRANSIENT_STATUSES


def is_chat_model(model_id: str) -> bool:
    low = model_id.lower()
    return not any(bad in low for bad in _NOT_CHAT)


def param_count(model_id: str) -> float:
    """Rough parameter count read out of the id ("gpt-oss-20b" -> 20.0)."""
    match = _PARAM_COUNT_RE.search(model_id.lower())
    return float(match.group(1)) if match else 999.0


def rank_chat_models(served: list[str]) -> list[str]:
    """
    The served ids that are usable for chat, best guess first.

    This is the last-resort ordering: it only decides anything when none of
    the configured candidates is served any more. Instruction-tuned ids come
    first, then the one closest to _PREFERRED_PARAM_COUNT — deliberately not
    "the biggest", because a 400B id on a free tier answers too slowly to be
    useful while a meeting is still running.

    Exposed so `scripts/preflight.py` can print exactly the order the code
    would choose, instead of a second opinion that might disagree with it.
    """
    def rank(model_id: str) -> tuple[int, float, str]:
        low = model_id.lower()
        looks_instructed = any(tag in low for tag in ("instruct", "chat", "gpt-oss", "-it"))
        return (
            0 if looks_instructed else 1,
            abs(param_count(model_id) - _PREFERRED_PARAM_COUNT),
            model_id,
        )

    return sorted((m for m in served if is_chat_model(m)), key=rank)


def extract_reply_text(data: object) -> tuple[str, str]:
    """
    Pull the assistant's visible answer out of an OpenAI-shaped reply.

    Returns `(text, problem)` where exactly one side is filled in. When
    there is no answer, `problem` says *why* in words that are worth
    reading in a log: an empty reply is otherwise indistinguishable from a
    model that had nothing to say, and the usual cause is a reasoning model
    spending the whole `max_tokens` budget thinking.
    """
    if not isinstance(data, dict):
        return "", f"reply was {type(data).__name__}, not a JSON object"
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return "", "reply carried no choices"
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message")
    message = message if isinstance(message, dict) else {}

    content = message.get("content")
    if isinstance(content, list):
        # Some gateways return content as a list of typed parts.
        content = "".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    if isinstance(content, str) and content.strip():
        return content.strip(), ""

    finish = choice.get("finish_reason") or "unspecified"
    thinking = next(
        (message[key] for key in _REASONING_KEYS
         if isinstance(message.get(key), str) and message[key].strip()),
        "",
    )
    if thinking:
        return "", (
            f"model returned {len(thinking)} characters of reasoning and no answer "
            f"(finish_reason={finish}) — raise max_tokens: reasoning models spend the "
            f"same budget thinking before they write anything visible"
        )
    if finish == "length":
        return "", (
            "reply was cut off before any visible text (finish_reason=length) — "
            "raise max_tokens"
        )
    return "", f"reply carried no text at all (finish_reason={finish})"


def pick_model(served: list[str], candidates: list[str]) -> str | None:
    """
    Choose a model id from what the provider says it serves *today*.

    Order of preference:
      1. a configured candidate served verbatim — configured order wins, so
         the choice stays predictable instead of "whatever sorted first"
      2. a configured candidate matching a served id apart from namespace:
         `openai/gpt-oss-20b` and `gpt-oss-20b` are the same model behind
         two different gateways
      3. any served chat model, per `rank_chat_models`

    Returns None when the list holds nothing usable, which the caller
    treats as "leave the model alone and let the router fall through".
    """
    chat_models = rank_chat_models(served)
    if not chat_models:
        return None

    for candidate in candidates:
        if candidate in chat_models:
            return candidate

    for candidate in candidates:
        tail = candidate.split("/")[-1].lower()
        if not tail:
            continue
        for served_id in served:
            if served_id not in chat_models:
                continue
            served_tail = served_id.split("/")[-1].lower()
            if tail == served_tail or tail in served_tail or served_tail in tail:
                return served_id

    return chat_models[0]


class OpenAICompatibleProvider:
    """
    Thin async client for any OpenAI-compatible chat completions API.
    Used as the base for the NIM, OpenRouter, and Groq clients.
    """

    name: str = "base"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        models: str | list[str] | None,
        timeout: float,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.candidates = parse_model_list(models)
        self.model = self.candidates[0] if self.candidates else ""
        self.timeout = timeout
        # Model ids this provider has already answered "gone" for. Without
        # it, rediscovery could hand back the same dead id in a loop.
        self._dead_models: set[str] = set()
        # Serialises rediscovery: nine agents call chat() at once, and they
        # must not all independently GET /models over the same failure.
        self._rediscovery_lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> ChatResult:
        if not self.is_configured:
            raise ProviderError(self.name, "no API key configured")
        if not self.model:
            raise ProviderError(self.name, "no model id configured")

        try:
            return await self._post_chat(messages, max_tokens, temperature)
        except ProviderError as first_error:
            if not first_error.model_gone:
                raise
            # The id that actually failed, not whatever self.model says now —
            # a concurrent call may already have replaced it.
            dead_model = first_error.model or self.model
            replacement = await self._rediscover_model(dead_model)
            if replacement is None:
                raise
            logger.warning(
                "%s: model %r is gone (%s) — retrying once with %r, which the provider "
                "currently lists as available",
                self.name, dead_model, first_error.message, replacement,
            )
            # Exactly one retry. If the replacement is rejected too, the
            # error propagates and the router moves to the next provider.
            return await self._post_chat(messages, max_tokens, temperature)

    async def _post_chat(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> ChatResult:
        url = f"{self.base_url}/chat/completions"
        # Read once: self.model can change mid-request when another coroutine
        # discovers this id is dead, and the request, the result and any error
        # all have to agree on which model was really used.
        model = self.model
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
        except httpx.RequestError as e:
            # string(e) is empty for a timeout — the log ended with
            # "network error:" and a void, which reads as "the provider is
            # broken" when it really means "this one call waited too long".
            detail = e.__class__.__name__ + (f": {e}" if str(e).strip() else "")
            raise ProviderError(self.name, f"network error: {detail}", model=model) from e

        if resp.status_code == 429:
            # Surface the provider's own Retry-After when it sends one, so the
            # router waits the amount actually being asked for.
            retry_after = parse_retry_after(resp.headers.get("retry-after", ""))
            raise ProviderError(
                self.name,
                f"rate limited (429){f', retry-after={retry_after:g}s' if retry_after else ''}",
                model=model,
                rate_limited=True,
                retry_after=retry_after,
            )
        if resp.status_code >= 400:
            raise ProviderError(
                self.name,
                f"HTTP {resp.status_code} for model {model!r}: {resp.text[:200]}",
                model_gone=looks_like_model_error(resp.status_code, resp.text),
                transient=is_transient_status(resp.status_code),
                model=model,
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise ProviderError(self.name, f"unexpected response shape: {e}", model=model) from e

        text, problem = extract_reply_text(data)
        if not text:
            # An HTTP 200 with nothing in it must not be reported as success.
            # Every caller — translation, requirement extraction, all nine
            # agents — parses this string, and an empty one produces an empty
            # Points panel that looks identical to "the meeting had no
            # requirements in it". Raising lets the router try the next
            # provider and puts the reason in the log.
            raise ProviderError(
                self.name, f"empty reply from model {model!r}: {problem}", model=model,
            )

        usage = data.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        return ChatResult(
            text=text,
            provider=self.name,
            model=model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    async def list_models(self) -> list[str]:
        """
        Ask the provider what it serves right now. Returns [] on any
        failure, because "couldn't ask" must be treated as "don't know" and
        never as "this provider has no models" — the difference matters,
        one leaves the configured id alone and the other would wipe it.
        """
        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._headers())
            if resp.status_code >= 400:
                logger.warning(
                    "%s: GET /models returned HTTP %s — cannot auto-pick a replacement model",
                    self.name, resp.status_code,
                )
                return []
            data = resp.json()
        except (httpx.RequestError, ValueError) as e:
            logger.warning("%s: GET /models failed (%s)", self.name, e)
            return []

        entries = data.get("data") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            return []
        served: list[str] = []
        for entry in entries:
            model_id = entry.get("id") if isinstance(entry, dict) else entry
            if isinstance(model_id, str) and model_id:
                served.append(model_id)
        return served

    async def _rediscover_model(self, dead_model: str) -> str | None:
        """
        Called only after a "model gone" answer. Records the dead id, asks
        the provider for its live list, and installs the best replacement
        for the rest of the process. Returns None when nothing better is
        available, in which case the original error stands.

        `dead_model` is passed in rather than read from self.model so that a
        late-arriving failure for an already-replaced id cannot retire the
        replacement.
        """
        async with self._rediscovery_lock:
            if self.model != dead_model:
                return self.model  # a concurrent call already fixed it
            self._dead_models.add(dead_model)

            served = await self.list_models()
            if not served:
                return None

            choice = pick_model(
                [m for m in served if m not in self._dead_models],
                [c for c in self.candidates if c not in self._dead_models],
            )
            if choice is None:
                return None
            self.model = choice
            return choice

