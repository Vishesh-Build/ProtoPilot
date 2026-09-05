"""
Write-through persistence: in-memory mutations made through a
registry-backed session must land in SQLite, so a process restart loses
nothing.

These complement test_session_registry_persistence (which covers the
registry's own load/save semantics) by driving the MeetingSession MUTATOR
methods — add_transcript_line, set_translation, mark_extracted,
add_requirements, mark_ended — exactly as transcription_bot.py and the
API routers call them.

Run from the backend/ directory:
    python -m unittest tests.test_write_through_persistence -v
"""

import tempfile
import unittest
from pathlib import Path

from app.meetings.session import SessionRegistry
from app.meetings.store import SessionStore


class WriteThroughTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.tmp.name) / "wt.db")
        self.registry = SessionRegistry(store=self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _restart(self) -> SessionRegistry:
        """Simulates a backend restart: new registry, same DB file."""
        self.store.close()
        self.store = SessionStore(Path(self.tmp.name) / "wt.db")
        self.registry = SessionRegistry(store=self.store)
        return self.registry


class TranscriptWriteThroughTest(WriteThroughTestBase):
    def test_added_lines_survive_restart(self):
        session = self.registry.get_or_create("m-wt", host_user_id="alice")
        first = session.add_transcript_line("A", "hi", "pehli baat", spoken_at="2026-09-04T10:00:01Z")
        second = session.add_transcript_line("B", "en", "second line", spoken_at="2026-09-04T10:00:02Z")

        reloaded = self._restart().get("m-wt")
        self.assertIsNotNone(reloaded)
        self.assertEqual([l.id for l in reloaded.transcript], [first.id, second.id])
        self.assertEqual([l.original_text for l in reloaded.transcript], ["pehli baat", "second line"])
        self.assertEqual([l.speaker for l in reloaded.transcript], ["A", "B"])

    def test_line_ids_continue_after_restart_no_collision(self):
        session = self.registry.get_or_create("m-ids")
        a = session.add_transcript_line("A", "en", "x")
        self.assertEqual(a.id, 1)

        reloaded = self._restart().get("m-ids")
        b = reloaded.add_transcript_line("A", "en", "y")
        # MUST be 2 — a colliding id would make set_translation patch the
        # wrong line and let a fresh insert violate the PK.
        self.assertEqual(b.id, 2)
        # And the new line is itself persisted.
        again = self._restart().get("m-ids")
        self.assertEqual([l.original_text for l in again.transcript], ["x", "y"])

    def test_translation_patch_survives_restart(self):
        session = self.registry.get_or_create("m-tr")
        line = session.add_transcript_line("A", "gu", "મને લોગિન જોઈએ", spoken_at="2026-09-04T10:00:00Z")
        session.set_translation(line.id, "I need a login")

        reloaded = self._restart().get("m-tr")
        self.assertEqual(reloaded.transcript[0].english_text, "I need a login")

    def test_extracted_flags_survive_restart(self):
        session = self.registry.get_or_create("m-ex")
        ids = [session.add_transcript_line("A", "en", f"line {i}").id for i in range(3)]
        # extractor marks only what it actually sent
        session.mark_extracted([ids[0], ids[2]])

        reloaded = self._restart().get("m-ex")
        self.assertEqual(
            [l.extracted for l in reloaded.transcript],
            [True, False, True],
            "a restart must not re-feed already-extracted lines (double LLM spend) "
            "or lose pending ones (silent requirement loss)",
        )

    def test_direct_constructor_session_is_in_memory_only(self):
        # The pre-persistence contract: a MeetingSession built by hand never
        # touches SQLite, no matter what it does. test_transcript_lines and
        # test_requirement_extraction depend on exactly this.
        from app.meetings.session import MeetingSession

        session = MeetingSession(meeting_id="m-direct")
        line = session.add_transcript_line("A", "en", "not persisted")
        self.assertIsNone(session._store)
        self.assertFalse(self.store.has_meeting("m-direct"))


class RequirementWriteThroughTest(WriteThroughTestBase):
    def test_added_requirements_survive_restart(self):
        session = self.registry.get_or_create("m-req")
        added = session.add_requirements([
            {"title": "OTP login", "category": "Auth", "priority": "High", "confidence": 90},
            {"title": "Dark mode", "category": "UI", "priority": "Low", "confidence": 60},
        ])
        self.assertEqual([r.id for r in added], [1, 2])

        reloaded = self._restart().get("m-req")
        self.assertEqual([r.title for r in reloaded.requirements], ["OTP login", "Dark mode"])
        self.assertEqual(reloaded.requirements[0].status, "pending")

    def test_requirement_ids_continue_after_restart(self):
        session = self.registry.get_or_create("m-rid")
        session.add_requirements([{"title": "First"}])
        reloaded = self._restart().get("m-rid")
        added = reloaded.add_requirements([{"title": "Second"}])
        self.assertEqual([r.id for r in added], [2])

    def test_duplicate_filter_uses_persisted_requirements(self):
        # _is_duplicate_title reads the in-memory list, which after a
        # restart is rehydrated from the store — so dedup must keep working
        # across restarts, or a resumed meeting accumulates near-dupes.
        session = self.registry.get_or_create("m-dup")
        session.add_requirements([{"title": "Buy order panel on the right"}])

        reloaded = self._restart().get("m-dup")
        added = reloaded.add_requirements([{"title": "Buy/sell order panel on the right"}])
        self.assertEqual(added, [], "a near-duplicate added after a restart must still be filtered")

    def test_readiness_percent_after_restart(self):
        session = self.registry.get_or_create("m-ready")
        session.add_requirements([{"title": "R1"}, {"title": "R2"}])
        # host approves one via the API path (status mutation -> Chunk 4
        # wires it; here we set it through the store to keep this test
        # independent of that wiring)
        self.store.update_requirement_status("m-ready", 1, "approved")

        reloaded = self._restart().get("m-ready")
        self.assertEqual(reloaded.readiness_percent(), 50)


class MeetingStateWriteThroughTest(WriteThroughTestBase):
    def test_mark_ended_survives_restart(self):
        session = self.registry.get_or_create("m-end")
        session.mark_ended()

        reloaded = self._restart().get("m-end")
        self.assertEqual(reloaded.status, "ended")
        self.assertIsNotNone(reloaded.ended_at)

    def test_name_and_host_backfill_persist(self):
        self.registry.get_or_create("m-nh", name="First name", host_user_id=None)
        self.registry.get_or_create("m-nh", name="Final name", host_user_id="alice")

        reloaded = self._restart().get("m-nh")
        self.assertEqual(reloaded.name, "Final name")
        self.assertEqual(reloaded.host_user_id, "alice")


class ConcurrentWriteTest(WriteThroughTestBase):
    """
    Multiple sessions sharing one store must not interfere — this is the
    multi-meeting-per-process reality once persistence lands.
    """

    def test_two_meetings_write_independently(self):
        m1 = self.registry.get_or_create("m-a", host_user_id="alice")
        m2 = self.registry.get_or_create("m-b", host_user_id="bob")

        m1.add_transcript_line("A", "en", "meeting one")
        m2.add_transcript_line("B", "hi", "meeting two", spoken_at="2026-09-04T10:00:01Z")
        m1.add_requirements([{"title": "From meeting one"}])
        m2.add_requirements([{"title": "From meeting two"}])

        self._restart()
        a = self.registry.get("m-a")
        b = self.registry.get("m-b")
        self.assertEqual([l.original_text for l in a.transcript], ["meeting one"])
        self.assertEqual([l.original_text for l in b.transcript], ["meeting two"])
        self.assertEqual([r.title for r in a.requirements], ["From meeting one"])
        self.assertEqual([r.title for r in b.requirements], ["From meeting two"])


class AgentOutputsWriteThroughTest(WriteThroughTestBase):
    def test_pipeline_output_replacement_survives_restart(self):
        session = self.registry.get_or_create("m-pipe")

        # What ws/generate.py does after run_pipeline() finishes:
        session.replace_agent_outputs({"pm": "# PRD", "architect": "# arch"})
        # A re-run replaces the whole set, exactly like the socket handler.
        session.replace_agent_outputs({"pm": "# PRD v2", "prototype": "<html>...</html>"})

        reloaded = self._restart().get("m-pipe")
        self.assertEqual(
            reloaded.agent_outputs,
            {"pm": "# PRD v2", "prototype": "<html>...</html>"},
            "a full replacement must drop stale entries across a restart",
        )

    def test_has_prototype_after_restart(self):
        session = self.registry.get_or_create("m-proto")
        session.replace_agent_outputs({"pm": "x"})
        self.assertFalse(self.registry.get("m-proto").summary()["has_prototype"])

        session.replace_agent_outputs({"prototype": "<html>hi</html>"})
        reloaded = self._restart().get("m-proto")
        self.assertTrue(reloaded.summary()["has_prototype"])


class RequirementMutationWriteThroughTest(WriteThroughTestBase):
    """The PATCH endpoints' new code path: update_requirement_status/title."""

    def _seed(self, meeting_id="m-mut") -> None:
        session = self.registry.get_or_create(meeting_id)
        session.add_requirements([{"title": "Original", "priority": "High"}])

    def test_status_mutation_survives_restart(self):
        self._seed()
        session = self.registry.get("m-mut")
        updated = session.update_requirement_status(1, "approved")
        self.assertEqual(updated.status, "approved")

        reloaded = self._restart().get("m-mut")
        self.assertEqual(reloaded.requirements[0].status, "approved")
        self.assertEqual(reloaded.readiness_percent(), 100)

    def test_title_mutation_survives_restart(self):
        self._seed()
        session = self.registry.get("m-mut")
        session.update_requirement_title(1, "Edited title")

        reloaded = self._restart().get("m-mut")
        self.assertEqual(reloaded.requirements[0].title, "Edited title")

    def test_unknown_requirement_id_returns_none_not_crash(self):
        self._seed()
        session = self.registry.get("m-mut")
        self.assertIsNone(session.update_requirement_status(99, "approved"))
        self.assertIsNone(session.update_requirement_title(99, "x"))

    def test_direct_dict_assign_still_works_in_memory(self):
        # test_transcript_lines.py's SummaryTest assigns session.agent_outputs
        # directly — that must keep working (no store, no persistence).
        from app.meetings.session import MeetingSession

        s = MeetingSession(meeting_id="m-direct2")
        s.agent_outputs["pm"] = "# PRD"
        self.assertEqual(s.agent_outputs, {"pm": "# PRD"})


if __name__ == "__main__":
    unittest.main()
