from fastapi import APIRouter, HTTPException

from app.llm.router import llm_router
from app.schemas.llm import ChatRequest, ChatResponse

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Manual test endpoint for the LLM router.

    Example:
        POST /llm/chat
        {
          "messages": [{"role": "user", "content": "Say hello in 5 words."}]
        }

    Use this to confirm NIM -> OpenRouter -> Groq fallback is wired
    correctly before agents start depending on it.
    """
    try:
        result = await llm_router.chat(
            messages=[m.model_dump() for m in req.messages],
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return ChatResponse(
        text=result.text,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
