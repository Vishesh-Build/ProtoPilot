from app.config import settings
from app.llm.providers.base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"

    def __init__(self):
        super().__init__(
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            timeout=settings.llm_request_timeout_seconds,
        )
