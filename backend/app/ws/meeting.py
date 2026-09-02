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
    - {"type": "transcript", "speaker": "<participant name>",
       "language": "hi", "language_confidence": 0.94,
       "original_text": "...", "english_text": "...", "timestamp": "..."}
    - {"type": "requirements", "new": [...], "readiness_percent": 42}
    - {"type": "error", "message": "..."}
    - {"type": "participant_speaking", "speaker": "...", "speaking": true}

Client -> Server: nothing required. The socket is receive-only from the
client's point of view; it just needs to stay open.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.connection_manager import meeting_connections
from app.meetings.session import session_registry

logger = logging.getLogger("protopilot.ws.meeting")

router = APIRouter()


@router.websocket("/ws/meeting/{meeting_id}")
async def meeting_socket(websocket: WebSocket, meeting_id: str):
    await websocket.accept()

    session = session_registry.get(meeting_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": f"No session found for meeting_id='{meeting_id}'"})
        await websocket.close(code=4404)
        return

    await meeting_connections.connect(meeting_id, websocket)
    logger.info("meeting %s: client connected to transcript feed", meeting_id)

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
