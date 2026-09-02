"""
Host-only enforcement for meeting-scoped endpoints.

Any endpoint that manages a meeting (accept/reject requirements, trigger
generation, export, end/delete the meeting) should depend on
`require_meeting_host` instead of loading the session and user separately —
keeps the "only the host can do this" rule in one place.
"""

from fastapi import Depends, HTTPException, WebSocket, status

from app.core.deps import get_current_user
from app.db.models import User
from app.meetings.session import MeetingSession, session_registry


def get_session_or_404(meeting_id: str) -> MeetingSession:
    session = session_registry.get(meeting_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No session found for meeting_id='{meeting_id}'")
    return session


async def require_meeting_host(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
) -> MeetingSession:
    """
    Loads the meeting and confirms the authenticated user is its host.
    Any participant can be in the call/transcript, but only the host can
    reach an endpoint that depends on this.
    """
    session = get_session_or_404(meeting_id)

    if session.host_user_id is None:
        # Shouldn't normally happen (host is set at creation) — fail closed
        # rather than silently letting the first requester claim it here.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This meeting has no assigned host yet.")

    if not session.is_host(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the meeting host can do this.")

    return session


async def get_ws_user_id(websocket: WebSocket) -> str | None:
    """
    Resolves the access-token cookie on a WebSocket handshake into a user_id.
    Returns None (never raises) — websocket callers close() the connection
    themselves with a proper code/reason instead of an HTTP exception.
    """
    import jwt as _jwt
    from app.core.security import decode_access_token

    token = websocket.cookies.get("access_token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except _jwt.PyJWTError:
        return None


async def require_ws_meeting_host(websocket: WebSocket, meeting_id: str) -> tuple[MeetingSession | None, bool]:
    """
    Returns (session, is_host). Caller is responsible for closing the socket
    with an appropriate code if is_host is False or session is None —
    this never raises, since raising inside a WS handler after accept()
    doesn't send a clean close frame.
    """
    session = session_registry.get(meeting_id)
    if session is None:
        return None, False

    user_id = await get_ws_user_id(websocket)
    return session, session.is_host(user_id)
