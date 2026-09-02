"""
LLM Router — sequential fallback chain.

Order is fixed: NIM -> OpenRouter -> Groq.
Every agent call in ProtoPilot goes through `llm_router.chat(...)`
rather than calling a provider directly, so the fallback logic
only has to live in one place.

Design goals (per project decision):
  - minimize token usage
  - maximize output quality
  - single tester right now, so no need for load-balancing or
    multi-user rate-limit handling — just reliability when a
    provider is down or rate-limited.
"""

import logging
import time

from app.config import settings
from app.llm.providers.base import ChatResult, ProviderError
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
        # Fixed order — do not reorder without updating ARCHITECTURE.md
        self.providers = [NimProvider(), OpenRouterProvider(), GroqProvider()]
        self._cooldown_until: dict[str, float] = {}

    def _is_cooling_down(self, provider_name: str) -> bool:
        until = self._cooldown_until.get(provider_name)
        return until is not None and time.monotonic() < until

    def _start_cooldown(self, provider_name: str):
        self._cooldown_until[provider_name] = time.monotonic() + settings.provider_cooldown_seconds

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ChatResult:
        """
        Try each provider in order. Returns the first successful result.
        Raises RuntimeError only if every configured provider fails.
        """
        max_tokens = max_tokens or settings.llm_default_max_tokens
        temperature = temperature if temperature is not None else settings.llm_default_temperature

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
                result = await provider.chat(messages, max_tokens, temperature)
                logger.info(
                    "llm call succeeded via %s (in=%s out=%s tokens)",
                    provider.name, result.input_tokens, result.output_tokens,
                )
                return result
            except ProviderError as e:
                logger.warning("%s failed: %s", provider.name, e.message)
                errors.append(f"{provider.name}: {e.message}")
                self._start_cooldown(provider.name)
                continue

        raise RuntimeError(
            "All LLM providers failed or are unavailable. "
            + ("; ".join(errors) if errors else "No provider has an API key configured.")
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
            }
            for p in self.providers
        ]


# Single shared instance — import this everywhere agents need LLM access.
llm_router = LLMRouter()
