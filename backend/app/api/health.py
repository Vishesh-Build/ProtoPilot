from fastapi import APIRouter

from app.llm.router import llm_router

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/llm/status")
async def llm_status():
    """Shows which providers are configured and which are currently cooling down."""
    return {"providers": llm_router.status()}
