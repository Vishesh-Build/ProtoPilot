from app.config import settings
from app.llm.providers.base import OpenAICompatibleProvider


class NimProvider(OpenAICompatibleProvider):
    name = "nim"

    def __init__(self):
        super().__init__(
            base_url=settings.nim_base_url,
            api_key=settings.nim_api_key,
            model=settings.nim_model,
            timeout=settings.llm_request_timeout_seconds,
        )
