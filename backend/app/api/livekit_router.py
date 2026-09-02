import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.core.deps import get_current_user
from app.core.meeting_auth import get_session_or_404, require_meeting_host
from app.db.models import User
from app.livekit.bot_manager import bot_manager
from app.meetings.session import MeetingSession

logger = logging.getLogger("protopilot.livekit")
router = APIRouter(prefix="/meetings", tags=["livekit"])


def _require_configured():
    if not (settings.livekit_api_key and settings.livekit_api_secret and settings.livekit_url):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LiveKit isn't configured on the server yet (LIVEKIT_API_KEY / "
                   "LIVEKIT_API_SECRET / LIVEKIT_URL missing in .env).",
        )


class LiveKitTokenResponse(BaseModel):
    livekit_url: str
    token: str
    room_name: str


@router.post("/{meeting_id}/livekit-token", response_model=LiveKitTokenResponse)
async def get_livekit_token(meeting_id: str, current_user: User = Depends(get_current_user)):
    """
    Issues a real, scoped LiveKit join token — any authenticated user can
    request one for a meeting that already exists (any participant, not
    just the host, since everyone needs to join the call and speak).
    The token is tied to this exact room and this exact user's identity —
    it can't be replayed for a different meeting or spoofed as someone else.
    """
    _require_configured()
    get_session_or_404(meeting_id)  # 404s if the host hasn't created this meeting yet

    from livekit import api as lk_api

    token = (
        lk_api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(current_user.id)
        .with_name(current_user.name)
        .with_grants(
            lk_api.VideoGrants(
                room_join=True,
                room=meeting_id,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )

    return LiveKitTokenResponse(livekit_url=settings.livekit_url, token=token, room_name=meeting_id)


@router.post("/{meeting_id}/start-call")
async def start_call(session: MeetingSession = Depends(require_meeting_host)):
    """
    Host-only. Starts the server-side transcription bot for this meeting —
    it joins the LiveKit room, subscribes to every participant's audio as
    they publish it, and transcribes each one separately. Safe to call
    again if it's already running (no duplicate bot gets started).
    """
    _require_configured()
    await bot_manager.start(session.meeting_id)
    return {"started": True, "meeting_id": session.meeting_id}


@router.post("/{meeting_id}/stop-call")
async def stop_call(session: MeetingSession = Depends(require_meeting_host)):
    """Host-only. Disconnects the transcription bot from the LiveKit room."""
    await bot_manager.stop(session.meeting_id)
    return {"stopped": True, "meeting_id": session.meeting_id}
