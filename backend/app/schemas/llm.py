from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'system', 'user', or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None


class ChatResponse(BaseModel):
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
