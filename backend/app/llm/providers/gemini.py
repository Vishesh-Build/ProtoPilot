from app.config import settings
from app.llm.providers.base import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    """
    Google Gemini via its OpenAI-compatible endpoint
    (https://generativelanguage.googleapis.com/v1beta/openai).

    Nothing here differs from the Groq/NIM clients except the base_url, key
    and model list — Gemini's OpenAI-compat surface speaks the same Bearer
    auth, /chat/completions and /models the shared base already handles. It
    exists as its own class only so the router can name it and lead with it.

    Why it leads the chain when configured: Groq's free tier is 8000
    tokens/minute, and one 9-agent generation needs ~25k tokens, so Groq
    alone spends minutes waiting on that ceiling — the exact rate limit the
    live demo hit. Gemini's free per-minute budget is far larger, so trying
    it first is what actually makes generation fast and reliable. With no
    GEMINI_API_KEY set, is_configured is False and the router skips straight
    to Groq, so the chain is unchanged from before.
    """

    name = "gemini"

    def __init__(self):
        super().__init__(
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_api_key,
            models=settings.gemini_models,
            timeout=settings.llm_request_timeout_seconds,
        )
