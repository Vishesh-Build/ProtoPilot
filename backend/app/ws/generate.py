"""
Runs the AI Workforce pipeline for a meeting's currently-approved
requirements and streams live status over a WebSocket. Host only —
this feeds directly into the export the host later downloads.

Protocol:
  Client connects to /ws/meeting/{meeting_id}/generate
  Server immediately starts the pipeline using session.requirements
  where status == "approved", and streams:

    {"type": "agent_update", "agent": "architect", "name": "System Architect",
     "status": "working", "progress": 50}
    {"type": "agent_log", "agent": "architect", "message": "..."}
    {"type": "agent_output", "agent": "architect", "output": "..."}
    {"type": "pipeline_complete"}
    {"type": "error", "message": "..."}  (e.g. no approved requirements yet, or not the host)

The socket closes on its own once the pipeline finishes — this isn't a
long-lived connection like the meeting transcript socket.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.orchestrator import run_pipeline
from app.core.meeting_auth import require_ws_meeting_host

logger = logging.getLogger("protopilot.ws.generate")

router = APIRouter()

# One pipeline per meeting at a time. A single run is 9 agents across 8
# waves of LLM calls, so a double-clicked Generate button (or a reconnect
# while a run is still going) would double the token spend and let two
# runs race to overwrite session.agent_outputs. Checked and set with no
# await in between, so the set needs no lock.
_running_pipelines: set[str] = set()


@router.websocket("/ws/meeting/{meeting_id}/generate")
async def generate_socket(websocket: WebSocket, meeting_id: str):
    await websocket.accept()

    session, is_host = await require_ws_meeting_host(websocket, meeting_id)

    if session is None:
        await websocket.send_json({"type": "error", "message": f"No session found for meeting_id='{meeting_id}'"})
        await websocket.close(code=4404)
        return

    if not is_host:
        logger.warning("meeting %s: non-host tried to trigger generation", meeting_id)
        await websocket.send_json({"type": "error", "message": "Only the meeting host can generate the prototype."})
        await websocket.close(code=4403)
        return

    logger.info("meeting %s: generation started by host", meeting_id)

    approved = [
        {"title": r.title, "category": r.category, "priority": r.priority}
        for r in session.requirements
        if r.status == "approved"
    ]

    if not approved:
        await websocket.send_json({
            "type": "error",
            "message": "No approved requirements yet — approve at least one before generating.",
        })
        await websocket.close()
        return

    if meeting_id in _running_pipelines:
        logger.warning("meeting %s: generation requested while one is already running", meeting_id)
        await websocket.send_json({
            "type": "error",
            "message": "Generation is already running for this meeting — watch the existing run.",
        })
        await websocket.close(code=4409)
        return

    async def emit(event: dict):
        try:
            await websocket.send_json(event)
        except Exception:  # noqa: BLE001 — client may have disconnected mid-stream
            logger.debug("meeting %s: failed to emit event (client likely disconnected)", meeting_id)

    _running_pipelines.add(meeting_id)
    try:
        final_states = await run_pipeline(approved, emit)
        session.agent_outputs = {agent_id: state.output for agent_id, state in final_states.items() if state.output}
    except WebSocketDisconnect:
        logger.info("meeting %s: client disconnected during generation", meeting_id)
        return
    except Exception as e:  # noqa: BLE001
        # Without this the socket just closed silently on any non-RuntimeError
        # failure and the Pipeline screen sat on "working" forever.
        logger.exception("meeting %s: generation failed", meeting_id)
        await emit({"type": "error", "message": f"Generation failed: {e}"})
        await websocket.close(code=1011)
        return
    finally:
        _running_pipelines.discard(meeting_id)

    await websocket.close()
    logger.info("meeting %s: generation finished", meeting_id)
