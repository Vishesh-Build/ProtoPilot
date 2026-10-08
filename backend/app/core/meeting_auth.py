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
        # Backfill current user as host if meeting had unassigned host
        session.host_user_id = current_user.id
        if session._store is not None and hasattr(session._store, "update_meeting_host"):
            try:
                session._store.update_meeting_host(session.meeting_id, current_user.id)
            except Exception:
                pass

    if not session.is_host(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the meeting host can do this.")

    return session


async def get_ws_user_id(websocket: WebSocket) -> str | None:
    """
    Resolves the access-token from cookies, query parameters (?token=),
    or Authorization header on a WebSocket handshake into a user_id.
    """
    import jwt as _jwt
    from app.core.security import decode_access_token

    token = websocket.cookies.get("access_token")
    if not token:
        token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if not token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        return None

    token = token.strip().replace('"', '').replace("'", "")
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
    if session.host_user_id is None and user_id:
        session.host_user_id = user_id
        if session._store is not None and hasattr(session._store, "update_meeting_host"):
            try:
                session._store.update_meeting_host(session.meeting_id, user_id)
            except Exception:
                pass
    return session, session.is_host(user_id)
