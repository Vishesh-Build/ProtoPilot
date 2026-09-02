"""
Broadcasts events (transcript lines, new requirements, errors) to every
client currently watching a given meeting.

Before the video-call change, `/ws/meeting/{meeting_id}` had exactly one
connection (the single PC recording the room). Now every participant's
Electron app opens this socket to watch the live transcript, so events
need to fan out to all of them, not just whichever one happened to send
the audio.
"""

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("protopilot.ws.connections")


class MeetingConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, meeting_id: str, websocket: WebSocket):
        async with self._lock:
            self._connections.setdefault(meeting_id, set()).add(websocket)

    async def disconnect(self, meeting_id: str, websocket: WebSocket):
        async with self._lock:
            conns = self._connections.get(meeting_id)
            if conns is not None:
                conns.discard(websocket)
                if not conns:
                    del self._connections[meeting_id]

    async def broadcast(self, meeting_id: str, payload: dict):
        conns = self._connections.get(meeting_id)
        if not conns:
            return
        # Snapshot before iterating — a disconnect during broadcast
        # shouldn't mutate the set we're looping over.
        for ws in list(conns):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                logger.debug("meeting %s: dropping a stale connection during broadcast", meeting_id)
                await self.disconnect(meeting_id, ws)


# Single shared instance for the process — same principle as session_registry.
meeting_connections = MeetingConnectionManager()
