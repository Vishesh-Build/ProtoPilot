"""
LLM Router — sequential fallback chain.

Order: Gemini -> Groq -> NIM -> OpenRouter. Every agent call in ProtoPilot
goes through `llm_router.chat(...)` rather than calling a provider
directly, so the fallback logic only has to live in one place. A provider
with no API key configured is skipped, so with no GEMINI_API_KEY set the
chain is simply Groq -> NIM -> OpenRouter, exactly as it was before Gemini
was added — nothing about the meeting path changes.

Why Gemini leads when it is configured: Groq's free tier is 8000
tokens/minute, and one full 9-agent generation needs ~25k tokens, so on
Groq alone a run spends ~3 minutes just waiting for that per-minute budget
to refill — which is the rate limit the live demo hit, five agents failing
in one wave. Gemini's free per-minute token budget is far larger, so
trying it first is what makes generation fast and reliable instead of
rate-limit-bound.

Why Groq sits second (and leads when there is no Gemini key): it has
answered real chat calls from this machine, and its free tier serves both
gpt-oss sizes, so the strongest model and the fastest one are one fallback
step apart. Within Groq the list leads with openai/gpt-oss-120b for output
quality and drops to openai/gpt-oss-20b when the bigger model is
rate-limited. NIM sits third as the quota backstop — it serves gpt-oss-20b
too — and OpenRouter last because its free tier is the least predictable.

Note that an empty answer counts as a failure here, not as a result: a
provider that returns HTTP 200 with `content: null` (a reasoning model
that spent the whole token budget thinking) raises, and the chain moves
on. Passing an empty string down to the extractor is what makes the
Points panel look like a meeting with no requirements in it.

Design goals (per project decision):
  - minimize token usage
  - maximize output quality
  - single tester right now, so no need for load-balancing or
    multi-user rate-limit handling — just reliability when a
    provider is down or rate-limited.
"""

import asyncio
import logging
import time

from app.config import settings
from app.llm.providers.base import ChatResult, ProviderError
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.nim import NimProvider
from app.llm.providers.openrouter import OpenRouterProvider

logger = logging.getLogger("protopilot.llm_router")


def _mock_chat_result(messages: list[dict]) -> ChatResult:
    """
    Fake response for LLM_MOCK_MODE=true — lets you exercise the whole
    pipeline (WebSocket -> transcription -> "LLM call" -> response handling)
    without spending real API tokens. Recognizes the requirement-extractor's
    system prompt specifically so that flow gets back valid, usable JSON
    instead of a plain string.
    """
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")

    if "JSON array" in system and "requirement" in system.lower():
        text = (
            '[{"title": "Mock requirement (LLM_MOCK_MODE on)", '
            '"category": "General", "priority": "Medium", "confidence": 75}]'
        )
    else:
        text = "[MOCK RESPONSE — LLM_MOCK_MODE is on in .env, no real API call was made]"

    return ChatResult(text=text, provider="mock", model="mock", input_tokens=0, output_tokens=0)


class LLMRouter:
    def __init__(self):
        # Gemini first when it has a key (largest free budget — see the module
        # docstring), then Groq -> NIM -> OpenRouter. An unconfigured provider
        # is skipped, so no Gemini key means the chain is just Groq-first, as
        # it always was.
        self.providers = [GeminiProvider(), GroqProvider(), NimProvider(), OpenRouterProvider()]
        self._cooldown_until: dict[str, float] = {}

    def _is_cooling_down(self, provider_name: str) -> bool:
        until = self._cooldown_until.get(provider_name)
        return until is not None and time.monotonic() < until

    def _start_cooldown(self, provider_name: str):
        self._cooldown_until[provider_name] = time.monotonic() + settings.provider_cooldown_seconds

    # Attempt delays for a 429 that carries no Retry-After header, in seconds.
    # Short and few on purpose for the meeting path: a caption or a
    # requirement point is worthless if it lands a minute late, so when the
    # provider does not say how long to wait, the router would rather fall
    # through to the next provider than keep an utterance waiting.
    _RATE_LIMIT_BACKOFF = (1.0, 2.0)

    # When the provider DOES say (Retry-After), that ask is honored — up to
    # this ceiling. This is the DEFAULT ceiling, used by the meeting/caption
    # path where a point that lands half a minute late is useless. The
    # generation pipeline passes a larger ceiling via `max_rate_limit_wait`
    # (settings.llm_generation_max_rate_limit_wait), because there a run is
    # expected to take a minute or two and paying a provider's honest "wait
    # 24s" beats failing the agent and cascading five more. Asks longer than
    # the ceiling in force mean a per-minute ceiling that will not clear in
    # time, so the router falls through to the next provider immediately.
    _RATE_LIMIT_MAX_WAIT = 20.0

    # Retries attempted after the first attempt, when the provider asked for
    # a wait inside the ceiling. Two (three attempts total) covers the live
    # pattern of 10s then 2s; an agent wave that is still 429ing after that
    # belongs to the next wave.
    _RATE_LIMIT_MAX_RETRIES = 2

    async def _chat_with_retry(self, provider, messages, max_tokens, temperature, max_rate_limit_wait):
        """
        One provider, retried in place only for the two transient failures:
        HTTP 429 (asked to slow down) and an HTTP 5xx overload (up but
        momentarily unable — Gemini answers 503 "high demand, try again later").

        A 429 carries the provider's own Retry-After when it bothers to say —
        that number is the honest "wait this long", and the live run showed
        what ignoring it costs: "retry-after=10s", retried after 3s, agent
        failed, five more agents failed downstream, no prototype. `max_rate_limit_wait`
        is the longest such ask this caller will sit through; a longer ask
        falls through to the next provider instead. A 5xx rarely names a wait,
        so it uses the router's own short backoff. Every other failure (dead
        model, network, empty reply) is raised on the first attempt — those do
        not get better by asking again immediately.
        """
        retries = 0
        while True:
            try:
                return await provider.chat(messages, max_tokens, temperature)
            except ProviderError as e:
                # A 429 and a transient 5xx are the two failures worth retrying
                # in place; everything else (dead model, network error, empty
                # reply) is raised at once because it will not get better by
                # asking again right now.
                if not (e.rate_limited or e.transient):
                    raise
                if retries >= self._RATE_LIMIT_MAX_RETRIES:
                    # Last attempt was already made; let the caller see the
                    # flag and move on to the next provider.
                    raise
                delay = e.retry_after
                if delay is None:
                    # A 429 with no Retry-After, or a 5xx (which rarely carries
                    # one) — fall back to the router's own short backoff.
                    delay = self._RATE_LIMIT_BACKOFF[
                        min(retries, len(self._RATE_LIMIT_BACKOFF) - 1)
                    ]
                elif delay > max_rate_limit_wait:
                    logger.warning(
                        "%s asked for a %.0fs pause — outside the %.0fs window this call allows, "
                        "moving on without retrying or cooling down", provider.name, delay, max_rate_limit_wait,
                    )
                    raise
                logger.info(
                    "%s %s — retrying in %.1fs (%s)",
                    provider.name,
                    "rate limited" if e.rate_limited else "temporarily unavailable",
                    delay, e.message,
                )
                await asyncio.sleep(delay)
                retries += 1

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float | None = None,
        max_rate_limit_wait: float | None = None,
    ) -> ChatResult:
        """
        Try each provider in order. Returns the first successful result.
        Raises RuntimeError only if every configured provider fails.

        `max_rate_limit_wait` is the longest Retry-After this caller will sit
        through per provider before falling through to the next one. It
        defaults to the short caption-path ceiling; the generation pipeline
        passes settings.llm_generation_max_rate_limit_wait so a real 429 that
        asks for ~24s is waited out instead of failing the agent.
        """
        max_tokens = max_tokens or settings.llm_default_max_tokens
        temperature = temperature if temperature is not None else settings.llm_default_temperature
        if max_rate_limit_wait is None:
            max_rate_limit_wait = self._RATE_LIMIT_MAX_WAIT

        if settings.llm_mock_mode:
            logger.debug("LLM_MOCK_MODE is on — returning fake response, no provider called")
            return _mock_chat_result(messages)

        errors: list[str] = []

        for provider in self.providers:
            if not provider.is_configured:
                logger.debug("%s skipped: no API key configured", provider.name)
                continue

            if self._is_cooling_down(provider.name):
                logger.debug("%s skipped: in cooldown", provider.name)
                continue

            try:
                result = await self._chat_with_retry(
                    provider, messages, max_tokens, temperature, max_rate_limit_wait,
                )
                logger.info(
                    "llm call succeeded via %s model=%s (in=%s out=%s tokens)",
                    provider.name, result.model, result.input_tokens, result.output_tokens,
                )
                return result
            except ProviderError as e:
                if e.rate_limited or e.transient:
                    # Still throttled (429) or still overloaded (5xx) after the
                    # in-place retries. Move to the next provider WITHOUT a
                    # cooldown: both are transient, the provider is very likely
                    # usable again within seconds, and locking it out for 60s is
                    # how one 429 turned into five failed agents — and, in the
                    # live Gemini run, how one 503 on the LEAD provider took the
                    # lead away from every agent that came after it.
                    logger.warning(
                        "%s still %s after retries — trying the next provider, no cooldown "
                        "(transient: slow down / overloaded, not down)",
                        provider.name,
                        "rate limited" if e.rate_limited else "overloaded (5xx)",
                    )
                    errors.append(f"{provider.name}: {e.message}")
                    continue
                if e.model_gone:
                    # The provider already tried to find a live replacement
                    # from its own /models list and still failed, so this is
                    # a configuration problem a human has to look at — say so
                    # in plain language instead of burying it in a warning.
                    logger.error(
                        "%s: no usable model. Configured candidates: %s. Last error: %s. "
                        "Run `python scripts/preflight.py` to see what this provider serves today.",
                        provider.name, ", ".join(provider.candidates) or "(none)", e.message,
                    )
                else:
                    logger.warning("%s failed: %s", provider.name, e.message)
                errors.append(f"{provider.name}: {e.message}")
                self._start_cooldown(provider.name)
                continue

        if errors:
            raise RuntimeError("All LLM providers failed or are unavailable. " + "; ".join(errors))

        # Nothing was even attempted. Say WHICH of the two reasons it was:
        # claiming "no API key" when every key is present but every provider is
        # still inside a cooldown from an earlier failure sends whoever reads
        # this log to check .env for a problem that isn't there.
        configured = [p.name for p in self.providers if p.is_configured]
        cooling = [n for n in configured if self._is_cooling_down(n)]
        if cooling:
            raise RuntimeError(
                "All LLM providers failed or are unavailable. Keys are configured for "
                f"{', '.join(configured)}, but every one is still in cooldown from an earlier "
                f"failure ({', '.join(cooling)}) — retry in up to "
                f"{settings.provider_cooldown_seconds}s, and check the earlier log lines for "
                "the failure that started it."
            )
        raise RuntimeError(
            "All LLM providers failed or are unavailable. No provider has an API key configured."
        )

    def status(self) -> list[dict]:
        """Used by a debug/health endpoint to see provider state at a glance."""
        if settings.llm_mock_mode:
            return [{"provider": "mock", "configured": True, "cooling_down": False, "note": "LLM_MOCK_MODE is ON — real providers bypassed"}]
        return [
            {
                "provider": p.name,
                "configured": p.is_configured,
                "cooling_down": self._is_cooling_down(p.name),
                # The id actually in use right now, which is not necessarily
                # the first configured candidate — a retired model gets
                # swapped out at runtime.
                "model": p.model,
                "candidates": p.candidates,
            }
            for p in self.providers
        ]


# Single shared instance — import this everywhere agents need LLM access.
llm_router = LLMRouter()
