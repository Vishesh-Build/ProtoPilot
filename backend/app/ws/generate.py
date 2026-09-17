"""
Runs the AI Workforce pipeline for a meeting's currently-approved
requirements and streams live status over a WebSocket. Host only —
this feeds directly into the export the host later downloads.

Protocol:
  Client connects to /ws/meeting/{meeting_id}/generate
  Server starts the pipeline (or re-attaches to an ongoing run) using
  session.requirements where status == "approved", and streams:

    {"type": "agent_update", "agent": "architect", "name": "System Architect",
     "status": "working", "progress": 50}
    {"type": "agent_log", "agent": "architect", "message": "..."}
    {"type": "agent_output", "agent": "architect", "output": "..."}
    {"type": "pipeline_complete"}   # every agent completed
    {"type": "pipeline_failed", "message": "..."}  # run is OVER, one or more agents failed
    {"type": "pipeline_cancelled", "message": "..."} # run was cancelled by the host
    {"type": "error", "message": "..."}

Client can send:
    {"type": "cancel"}  # aborts the active pipeline run immediately
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.definitions import AGENT_DEFINITIONS
from app.agents.orchestrator import run_pipeline
from app.core.meeting_auth import require_ws_meeting_host

logger = logging.getLogger("protopilot.ws.generate")

router = APIRouter()


class ActivePipeline:
    """
    Manages an active 9-agent pipeline execution for a meeting.
    Supports multiple concurrent WebSocket listeners, event replay on
    reconnect, and clean in-flight cancellation.
    """

    def __init__(self, meeting_id: str, approved_requirements: list[dict]):
        self.meeting_id = meeting_id
        self.approved_requirements = approved_requirements
        self.listeners: set[WebSocket] = set()
        self.events_history: list[dict] = []
        self.current_states: dict[str, dict] = {}
        self.task: asyncio.Task | None = None
        self.is_cancelled: bool = False
        self.completion_event = asyncio.Event()

    async def emit(self, event: dict):
        self.events_history.append(event)
        etype = event.get("type")
        if etype == "agent_update":
            agent_id = event.get("agent")
            if agent_id:
                self.current_states[agent_id] = event

        dead = []
        for ws in list(self.listeners):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.listeners.discard(ws)

    def cancel(self):
        self.is_cancelled = True
        if self.task and not self.task.done():
            self.task.cancel()

    def get_summary(self) -> dict:
        total_progress = sum(s.get("progress", 0) for s in self.current_states.values())
        overall_pct = round(total_progress / max(1, len(AGENT_DEFINITIONS)))
        current_agent = None
        for agent_id, state in self.current_states.items():
            if state.get("status") in ("working", "thinking"):
                current_agent = agent_id
                break
        return {
            "running": not self.completion_event.is_set() and not self.is_cancelled,
            "cancelled": self.is_cancelled,
            "overall_pct": min(100, overall_pct),
            "current_agent": current_agent,
        }


# Active pipelines indexed by meeting_id
_active_pipelines: dict[str, ActivePipeline] = {}


def cancel_pipeline(meeting_id: str) -> bool:
    """Cancels an ongoing generation pipeline for the given meeting."""
    active = _active_pipelines.get(meeting_id)
    if active and not active.completion_event.is_set():
        logger.info("meeting %s: cancel_pipeline requested", meeting_id)
        active.cancel()
        return True
    return False


def get_pipeline_status(meeting_id: str) -> dict:
    """Returns the current running status of a meeting's pipeline."""
    active = _active_pipelines.get(meeting_id)
    if active and not active.completion_event.is_set():
        return active.get_summary()
    return {"running": False, "cancelled": False, "overall_pct": 0, "current_agent": None}


async def _handle_socket_listener(websocket: WebSocket, active: ActivePipeline):
    """Waits for pipeline completion while listening for client messages (e.g. cancel)."""
    has_receive = hasattr(websocket, "receive_text")
    if not has_receive:
        await active.completion_event.wait()
        return

    while not active.completion_event.is_set():
        receive_task = asyncio.create_task(websocket.receive_text())
        wait_task = asyncio.create_task(active.completion_event.wait())
        done, _ = await asyncio.wait([receive_task, wait_task], return_when=asyncio.FIRST_COMPLETED)

        if receive_task in done:
            wait_task.cancel()
            try:
                raw = receive_task.result()
                data = json.loads(raw)
                if data.get("type") == "cancel":
                    logger.info("meeting %s: cancel requested via websocket", active.meeting_id)
                    active.cancel()
            except Exception:
                # Client disconnected or sent unparseable data
                break
        else:
            receive_task.cancel()


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

    # Check if a pipeline is ALREADY running for this meeting.
    # If so, attach this websocket as a listener and replay the current progress!
    active = _active_pipelines.get(meeting_id)
    if active and not active.completion_event.is_set():
        logger.info("meeting %s: client reconnected to ongoing pipeline", meeting_id)
        active.listeners.add(websocket)

        # 1. Replay current agent states so the UI fast-forwards immediately
        for agent_id, state in active.current_states.items():
            try:
                await websocket.send_json(state)
            except Exception:
                active.listeners.discard(websocket)
                return

        # 2. Replay all agent outputs and recent logs
        for event in active.events_history:
            if event.get("type") in ("agent_output", "agent_log"):
                try:
                    await websocket.send_json(event)
                except Exception:
                    active.listeners.discard(websocket)
                    return

        # If already cancelled, notify immediately
        if active.is_cancelled:
            try:
                await websocket.send_json({
                    "type": "pipeline_cancelled",
                    "message": "Generation was cancelled by the host.",
                })
            except Exception:
                pass

        try:
            await _handle_socket_listener(websocket, active)
        except WebSocketDisconnect:
            pass
        finally:
            active.listeners.discard(websocket)
            try:
                await websocket.close()
            except Exception:
                pass
        return

    # A completed run already exists: replay its outputs for free instead of
    # starting a second paid 9-agent run.
    force = websocket.query_params.get("force") in ("1", "true", "yes")
    if not force and session.agent_outputs.get("prototype"):
        logger.info("meeting %s: replaying already-generated outputs (no re-run)", meeting_id)
        for agent_id, output in session.agent_outputs.items():
            await websocket.send_json({
                "type": "agent_update", "agent": agent_id,
                "status": "completed", "progress": 100,
            })
            await websocket.send_json({"type": "agent_output", "agent": agent_id, "output": output})
        await websocket.send_json({"type": "pipeline_complete"})
        await websocket.close()
        return

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

    logger.info("meeting %s: starting fresh generation pipeline", meeting_id)
    active = ActivePipeline(meeting_id, approved)
    _active_pipelines[meeting_id] = active
    active.listeners.add(websocket)

    async def pipeline_worker():
        try:
            final_states = await run_pipeline(approved, active.emit)
            session.replace_agent_outputs(
                {agent_id: state.output for agent_id, state in final_states.items() if state.output}
            )
        except asyncio.CancelledError:
            logger.info("meeting %s: pipeline worker cancelled", meeting_id)
            await active.emit({
                "type": "pipeline_cancelled",
                "message": "Generation was cancelled by the host.",
            })
        except WebSocketDisconnect:
            logger.info("meeting %s: client disconnected during generation", meeting_id)
        except Exception as e:  # noqa: BLE001
            logger.exception("meeting %s: generation failed", meeting_id)
            await active.emit({"type": "error", "message": f"Generation failed: {e}"})
        finally:
            active.completion_event.set()
            _active_pipelines.pop(meeting_id, None)

    active.task = asyncio.create_task(pipeline_worker())

    try:
        await _handle_socket_listener(websocket, active)
        if active.task and not active.task.done():
            # If the socket listener exited (e.g. client closed or fake socket finished),
            # wait for the pipeline task to finish if this was a driven test.
            if not hasattr(websocket, "receive_text"):
                await active.task
    except WebSocketDisconnect:
        logger.info("meeting %s: primary client disconnected, pipeline continues in background", meeting_id)
    finally:
        active.listeners.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass

    logger.info("meeting %s: generate_socket handler finished", meeting_id)
