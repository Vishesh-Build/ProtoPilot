"""
The generation socket's replay-vs-rerun decision.

A built prototype is replayed for free when the Generation Pipeline page is
merely re-opened — re-running the 9-agent pipeline every time would double
the token spend for an identical result. But that replay also meant a
requirement approved *after* the build could never reach the prototype: the
socket always handed back the stale outputs. The host pressing "Regenerate"
sends ?force=1, which must skip the replay and run afresh over whatever is
approved *now* — including the just-added requirement.

These drive the handler directly with a fake WebSocket and a patched
run_pipeline, so nothing here touches an LLM or the network.

Run from the backend/ directory:
    python -m unittest tests.test_generate_force -v
"""

import logging
import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.ws import generate  # noqa: E402
from app.meetings.session import MeetingSession  # noqa: E402

logging.getLogger("protopilot.ws.generate").setLevel(logging.CRITICAL)


class _FakeWebSocket:
    """The slice of Starlette's WebSocket the handler actually uses."""

    def __init__(self, query_params=None):
        self.query_params = query_params or {}
        self.sent: list[dict] = []
        self.close_code = None
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self, code=1000):
        self.close_code = code


class _State:
    """Stands in for an AgentState — the handler only reads .output."""

    def __init__(self, output):
        self.output = output


class GenerateForceTest(unittest.IsolatedAsyncioTestCase):
    # What a fresh run "produces", so we can tell it apart from the stale build.
    FRESH_STATES = {
        "pm": _State("new pm"),
        "prototype": _State("<html>NEW</html>"),
    }

    def _built_session(self, meeting_id: str) -> MeetingSession:
        """A meeting that already has a prototype and one approved requirement."""
        s = MeetingSession(meeting_id=meeting_id, host_user_id="u1")
        s.add_requirements([{"title": "Login screen"}])
        s.update_requirement_status(s.requirements[0].id, "approved")
        s.agent_outputs = {"pm": "old pm", "prototype": "<html>OLD</html>"}
        return s

    async def _drive(self, session: MeetingSession, force: bool):
        ws = _FakeWebSocket(query_params={"force": "1"} if force else {})
        with mock.patch.object(
            generate, "require_ws_meeting_host",
            new=mock.AsyncMock(return_value=(session, True)),
        ), mock.patch.object(
            generate, "run_pipeline",
            new=mock.AsyncMock(return_value=self.FRESH_STATES),
        ) as run_mock:
            await generate.generate_socket(ws, session.meeting_id)
        return ws, run_mock

    async def test_without_force_a_built_prototype_is_replayed_not_rerun(self):
        s = self._built_session("m-replay")
        ws, run_mock = await self._drive(s, force=False)

        run_mock.assert_not_called()
        types = [e["type"] for e in ws.sent]
        self.assertIn("pipeline_complete", types)
        self.assertNotIn("error", types)
        # The stale outputs are handed back untouched — no paid re-run.
        self.assertEqual(s.agent_outputs["prototype"], "<html>OLD</html>")

    async def test_force_reruns_even_when_a_prototype_already_exists(self):
        s = self._built_session("m-force")
        ws, run_mock = await self._drive(s, force=True)

        run_mock.assert_called_once()
        # The fresh run's outputs replace the stale build.
        self.assertEqual(s.agent_outputs["prototype"], "<html>NEW</html>")
        self.assertEqual(s.agent_outputs["pm"], "new pm")

    async def test_force_run_includes_a_requirement_approved_after_the_build(self):
        s = self._built_session("m-newreq")
        # The "you missed one" moment: raised and approved after the build.
        s.add_requirements([{"title": "Export invoice to PDF"}])
        s.update_requirement_status(s.requirements[1].id, "approved")

        _, run_mock = await self._drive(s, force=True)

        approved_titles = [r["title"] for r in run_mock.call_args.args[0]]
        self.assertIn("Export invoice to PDF", approved_titles,
                      "the newly-approved requirement must reach the regeneration")
        self.assertIn("Login screen", approved_titles,
                      "the original requirements must still be there too")


if __name__ == "__main__":
    unittest.main(verbosity=2)
