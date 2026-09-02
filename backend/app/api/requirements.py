from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.meeting_auth import get_session_or_404, require_meeting_host
from app.db.models import User
from app.meetings.session import MeetingSession

router = APIRouter(prefix="/meetings", tags=["requirements"])


class StatusUpdate(BaseModel):
    status: str  # "pending" | "approved" | "rejected"


class TitleUpdate(BaseModel):
    title: str


@router.get("/{meeting_id}/requirements")
async def list_requirements(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    return {
        "requirements": [r.__dict__ for r in session.requirements],
        "readiness_percent": session.readiness_percent(),
    }


@router.patch("/{meeting_id}/requirements/{requirement_id}/status")
async def update_status(
    requirement_id: int,
    body: StatusUpdate,
    session: MeetingSession = Depends(require_meeting_host),
):
    """Accept/reject a requirement — host only."""
    if body.status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="status must be pending, approved, or rejected")

    for r in session.requirements:
        if r.id == requirement_id:
            r.status = body.status
            return {"requirement": r.__dict__, "readiness_percent": session.readiness_percent()}

    raise HTTPException(status_code=404, detail=f"No requirement with id={requirement_id}")


@router.patch("/{meeting_id}/requirements/{requirement_id}/title")
async def update_title(
    requirement_id: int,
    body: TitleUpdate,
    session: MeetingSession = Depends(require_meeting_host),
):
    """Edit a requirement's title — host only, same as accept/reject."""
    for r in session.requirements:
        if r.id == requirement_id:
            r.title = body.title
            return {"requirement": r.__dict__}

    raise HTTPException(status_code=404, detail=f"No requirement with id={requirement_id}")
