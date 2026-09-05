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


class RequirementCreate(BaseModel):
    title: str
    category: str = "General"
    priority: str = "Medium"


@router.get("/{meeting_id}/requirements")
async def list_requirements(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    return {
        "requirements": [r.__dict__ for r in session.requirements],
        "readiness_percent": session.readiness_percent(),
    }


@router.post("/{meeting_id}/requirements")
async def add_requirement(
    meeting_id: str,
    body: RequirementCreate,
    session: MeetingSession = Depends(require_meeting_host),
):
    """
    Manually add a requirement mid-meeting — host only.

    This is the guaranteed path for the "someone just said we missed X"
    moment: the transcription extractor usually catches it, but the host
    shouldn't have to depend on that during a live demo. It's added as
    *approved* (not pending) so the next "Regenerate" folds it into the
    already-built prototype without a second click. Near-duplicates of an
    existing requirement are rejected (409) rather than silently dropped.
    """
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title must not be empty")

    added = session.add_requirements(
        [{"title": title, "category": body.category, "priority": body.priority, "confidence": 100}]
    )
    if not added:
        raise HTTPException(status_code=409, detail="That requirement is already captured.")

    req = added[0]
    session.update_requirement_status(req.id, "approved")
    return {"requirement": req.__dict__, "readiness_percent": session.readiness_percent()}


@router.patch("/{meeting_id}/requirements/{requirement_id}/status")
async def update_status(
    requirement_id: int,
    body: StatusUpdate,
    session: MeetingSession = Depends(require_meeting_host),
):
    """Accept/reject a requirement — host only."""
    if body.status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="status must be pending, approved, or rejected")

    updated = session.update_requirement_status(requirement_id, body.status)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"No requirement with id={requirement_id}")
    return {"requirement": updated.__dict__, "readiness_percent": session.readiness_percent()}


@router.patch("/{meeting_id}/requirements/{requirement_id}/title")
async def update_title(
    requirement_id: int,
    body: TitleUpdate,
    session: MeetingSession = Depends(require_meeting_host),
):
    """Edit a requirement's title — host only, same as accept/reject."""
    updated = session.update_requirement_title(requirement_id, body.title)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"No requirement with id={requirement_id}")
    return {"requirement": updated.__dict__}
