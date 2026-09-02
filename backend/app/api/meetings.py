from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.meeting_auth import get_session_or_404, require_meeting_host
from app.db.models import User
from app.meetings.session import MeetingSession, session_registry

router = APIRouter(prefix="/meetings", tags=["meetings"])


class CreateMeetingRequest(BaseModel):
    meeting_id: str
    name: str


@router.post("")
async def create_meeting(body: CreateMeetingRequest, current_user: User = Depends(get_current_user)):
    """
    Registers a meeting so it shows up in the Dashboard / Meeting History.
    Called once when the user clicks "Start Meeting" in the Create Meeting screen.
    Whoever creates it becomes the host — only they can manage requirements,
    generate the prototype, export it, or end/delete the meeting later.
    Safe to call again with the same meeting_id (e.g. reconnect) — just
    updates the name; the original host is preserved.
    """
    session = session_registry.get_or_create(body.meeting_id, name=body.name, host_user_id=current_user.id)
    return session.summary()


@router.get("")
async def list_meetings(current_user: User = Depends(get_current_user)):
    """
    Powers the Dashboard's Recent Meetings panel and the Meeting History screen.

    Scoped to meetings this user hosts. The registry is process-wide, so
    returning all of it handed every logged-in user the ids and names of
    everyone else's meetings — and a meeting_id is all you need to join.
    A participant reaches a meeting by its id (GET /meetings/{id}), not
    through this list.
    """
    return {"meetings": [s.summary() for s in session_registry.list_all() if s.is_host(current_user.id)]}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    return session.summary()


@router.get("/{meeting_id}/agent-outputs")
async def get_agent_outputs(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    return {"agent_outputs": session.agent_outputs}


@router.get("/{meeting_id}/transcript")
async def get_transcript(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    # to_dict() carries id + spoken_at, so a client reloading mid-meeting can
    # match up with the lines it already received over the WebSocket.
    return {"transcript": [line.to_dict() for line in session.transcript]}


@router.post("/{meeting_id}/end")
async def end_meeting(session: MeetingSession = Depends(require_meeting_host)):
    """Called when the host hits Stop/End Meeting — marks it ended for
    history/dashboard display, and stops the transcription bot if it's
    still connected to the LiveKit room."""
    from app.livekit.bot_manager import bot_manager
    await bot_manager.stop(session.meeting_id)
    session.mark_ended()
    return session.summary()


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: str, session: MeetingSession = Depends(require_meeting_host)):
    """Called from Meeting History's Delete action — removes it permanently. Host only."""
    from app.requirements.extractor import clear_extraction_state

    session_registry.delete(meeting_id)
    clear_extraction_state(meeting_id)
    return {"deleted": True, "meeting_id": meeting_id}
