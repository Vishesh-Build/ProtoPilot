"""
Shared interface for LLM providers.

NIM, OpenRouter, and Groq all expose an OpenAI-compatible
`/chat/completions` endpoint, so a single implementation covers
all three — only base_url, api_key, and model differ.
"""

from dataclasses import dataclass

import httpx


class ProviderError(Exception):
    """Raised when a provider fails to respond successfully.
    The router catches this and moves to the next provider in the chain."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


@dataclass
class ChatResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class OpenAICompatibleProvider:
    """
    Thin async client for any OpenAI-compatible chat completions API.
    Used as the base for the NIM, OpenRouter, and Groq clients.
    """

    name: str = "base"

    def __init__(self, base_url: str, api_key: str | None, model: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> ChatResult:
        if not self.is_configured:
            raise ProviderError(self.name, "no API key configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise ProviderError(self.name, f"network error: {e}") from e

        if resp.status_code == 429:
            raise ProviderError(self.name, "rate limited (429)")
        if resp.status_code >= 400:
            raise ProviderError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderError(self.name, f"unexpected response shape: {e}") from e

        return ChatResult(
            text=choice,
            provider=self.name,
            model=self.model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
