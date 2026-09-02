"""
Live meeting broadcast WebSocket.

IMPORTANT CHANGE from the single-PC version: this socket no longer
receives audio. Audio now flows over LiveKit (each participant's mic is a
separate WebRTC track), gets picked up server-side by the transcription
bot (app/livekit/transcription_bot.py), and THAT is what calls
`meeting_connections.broadcast(...)` with the results. This socket is just
what every participant's Electron app connects to in order to *receive*
those live updates — transcript lines, new requirements, errors.

  Server -> Client (broadcast to every connected participant):
    - {"type": "transcript", "line_id": 12, "speaker": "<participant name>",
       "language": "hi", "language_confidence": 0.94,
       "original_text": "...", "english_text": "<original until translated>",
       "translation_pending": true, "spoken_at": "2026-09-02T...Z"}
    - {"type": "transcript_update", "line_id": 12,
       "english_text": "...", "translation_pending": false}
    - {"type": "requirements", "new": [...], "readiness_percent": 42}
    - {"type": "error", "message": "..."}

  A line is sent as soon as Whisper returns, carrying original_text in the
  english_text field so a caption is never blank. The translation follows as
  a transcript_update for the same line_id — clients should match on line_id
  and ignore an update for a line they've already replaced.

Client -> Server: nothing required. The socket is receive-only from the
client's point of view; it just needs to stay open.

Auth: the access-token cookie is checked on the handshake. Without it the
socket closes with 4401 — a meeting_id alone used to be enough to stream
someone else's live meeting.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.connection_manager import meeting_connections
from app.core.meeting_auth import get_ws_user_id
from app.meetings.session import session_registry

logger = logging.getLogger("protopilot.ws.meeting")

router = APIRouter()


@router.websocket("/ws/meeting/{meeting_id}")
async def meeting_socket(websocket: WebSocket, meeting_id: str):
    await websocket.accept()

    # Closing before accept() doesn't deliver a code the client can read,
    # so accept first and then reject with a real close frame.
    user_id = await get_ws_user_id(websocket)
    if user_id is None:
        await websocket.send_json({"type": "error", "message": "Not authenticated."})
        await websocket.close(code=4401)
        return

    session = session_registry.get(meeting_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": f"No session found for meeting_id='{meeting_id}'"})
        await websocket.close(code=4404)
        return

    await meeting_connections.connect(meeting_id, websocket)
    logger.info("meeting %s: client connected to transcript feed (user=%s)", meeting_id, user_id)

    try:
        while True:
            # Nothing meaningful arrives from the client on this socket
            # anymore — just block here so the connection (and the
            # broadcast registration) stays alive until they disconnect.
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))
    except WebSocketDisconnect:
        logger.info("meeting %s: client disconnected from transcript feed", meeting_id)
    finally:
        await meeting_connections.disconnect(meeting_id, websocket)
