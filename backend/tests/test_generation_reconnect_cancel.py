"""
Tests for generation pipeline reconnection, live state replay, and in-flight cancellation.

Run from the backend/ directory:
    python -m unittest tests.test_generation_reconnect_cancel -v
"""

import asyncio
import json
import logging
import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:
    import stubs
stubs.install()

from app.meetings.session import MeetingSession
from app.ws import generate

logging.getLogger("protopilot.ws.generate").setLevel(logging.CRITICAL)


class _AsyncFakeWebSocket:
    """Mock WebSocket with support for receive_text queue."""

    def __init__(self, query_params=None):
        self.query_params = query_params or {}
        self.sent: list[dict] = []
        self.close_code = None
        self.accepted = False
        self._inbox: asyncio.Queue[str] = asyncio.Queue()

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self, code=1000):
        self.close_code = code

    async def receive_text(self) -> str:
        return await self._inbox.get()

    def push_message(self, data: dict):
        self._inbox.put_nowait(json.dumps(data))


class GenerationReconnectCancelTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Reset active pipelines dictionary
        generate._active_pipelines.clear()

    def tearDown(self):
        generate._active_pipelines.clear()

    def _session_with_requirements(self, meeting_id: str) -> MeetingSession:
        s = MeetingSession(meeting_id=meeting_id, host_user_id="u1")
        s.add_requirements([{"title": "User Dashboard"}])
        s.update_requirement_status(s.requirements[0].id, "approved")
        return s

    async def test_active_pipeline_reconnection_replays_state(self):
        session = self._session_with_requirements("m-recon")
        ws1 = _AsyncFakeWebSocket(query_params={"force": "1"})

        # A pipeline that pauses midway through
        started_event = asyncio.Event()
        continue_event = asyncio.Event()

        async def slow_pipeline(approved, emit):
            await emit({"type": "agent_update", "agent": "pm", "status": "working", "progress": 50})
            await emit({"type": "agent_log", "agent": "pm", "message": "Defining scopes"})
            started_event.set()
            await continue_event.wait()
            await emit({"type": "agent_update", "agent": "pm", "status": "completed", "progress": 100})
            await emit({"type": "agent_output", "agent": "pm", "output": "PM spec"})
            await emit({"type": "pipeline_complete"})
            return {}

        with mock.patch.object(generate, "require_ws_meeting_host", new=mock.AsyncMock(return_value=(session, True))), \
             mock.patch.object(generate, "run_pipeline", side_effect=slow_pipeline):
            
            task1 = asyncio.create_task(generate.generate_socket(ws1, "m-recon"))
            await started_event.wait()

            # Verify pipeline is tracked as active
            status = generate.get_pipeline_status("m-recon")
            self.assertTrue(status["running"])
            self.assertEqual(status["current_agent"], "pm")

            # Connect second client (simulating user navigating away and coming back)
            ws2 = _AsyncFakeWebSocket()
            task2 = asyncio.create_task(generate.generate_socket(ws2, "m-recon"))
            await asyncio.sleep(0.05)

            # Check that ws2 received the replayed agent_update and agent_log
            replayed_types = [e["type"] for e in ws2.sent]
            self.assertIn("agent_update", replayed_types)
            self.assertIn("agent_log", replayed_types)
            pm_update = next(e for e in ws2.sent if e["type"] == "agent_update" and e.get("agent") == "pm")
            self.assertEqual(pm_update["status"], "working")
            self.assertEqual(pm_update["progress"], 50)

            # Let pipeline complete
            continue_event.set()
            await asyncio.gather(task1, task2)

            # Both should have received pipeline_complete
            self.assertIn("pipeline_complete", [e["type"] for e in ws1.sent])
            self.assertIn("pipeline_complete", [e["type"] for e in ws2.sent])

    async def test_cancel_pipeline_via_helper_function(self):
        session = self._session_with_requirements("m-cancel-fn")
        ws = _AsyncFakeWebSocket(query_params={"force": "1"})

        started_event = asyncio.Event()

        async def endless_pipeline(approved, emit):
            await emit({"type": "agent_update", "agent": "pm", "status": "working", "progress": 30})
            started_event.set()
            while True:
                await asyncio.sleep(1)

        with mock.patch.object(generate, "require_ws_meeting_host", new=mock.AsyncMock(return_value=(session, True))), \
             mock.patch.object(generate, "run_pipeline", side_effect=endless_pipeline):

            task = asyncio.create_task(generate.generate_socket(ws, "m-cancel-fn"))
            await started_event.wait()

            self.assertTrue(generate.get_pipeline_status("m-cancel-fn")["running"])

            # Call cancel_pipeline (as called by POST /meetings/{id}/cancel-generation)
            cancelled = generate.cancel_pipeline("m-cancel-fn")
            self.assertTrue(cancelled)

            await task

            # Verify pipeline_cancelled event was emitted
            sent_types = [e["type"] for e in ws.sent]
            self.assertIn("pipeline_cancelled", sent_types)
            self.assertFalse(generate.get_pipeline_status("m-cancel-fn")["running"])

    async def test_cancel_pipeline_via_websocket_message(self):
        session = self._session_with_requirements("m-cancel-ws")
        ws = _AsyncFakeWebSocket(query_params={"force": "1"})

        started_event = asyncio.Event()

        async def endless_pipeline(approved, emit):
            await emit({"type": "agent_update", "agent": "architect", "status": "working", "progress": 40})
            started_event.set()
            while True:
                await asyncio.sleep(1)

        with mock.patch.object(generate, "require_ws_meeting_host", new=mock.AsyncMock(return_value=(session, True))), \
             mock.patch.object(generate, "run_pipeline", side_effect=endless_pipeline):

            task = asyncio.create_task(generate.generate_socket(ws, "m-cancel-ws"))
            await started_event.wait()

            # Client sends cancel message over websocket
            ws.push_message({"type": "cancel"})

            await task

            sent_types = [e["type"] for e in ws.sent]
            self.assertIn("pipeline_cancelled", sent_types)
            self.assertFalse(generate.get_pipeline_status("m-cancel-ws")["running"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
