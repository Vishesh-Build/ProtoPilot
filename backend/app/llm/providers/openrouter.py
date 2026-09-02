from app.config import settings
from app.llm.providers.base import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"

    def __init__(self):
        super().__init__(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            timeout=settings.llm_request_timeout_seconds,
        )
