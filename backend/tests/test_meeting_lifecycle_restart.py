"""
End-to-end meeting lifecycle across a simulated backend restart.

This drives the EXACT sequence the real app runs, in order, then restarts
the "backend" (new store + new registry over the same file) and asserts
everything survived:

  1. Host creates a meeting                (api/meetings.py create_meeting)
  2. Bot adds transcript lines + patches
     a late translation                    (transcription_bot.py)
  3. Extractor reads pending, marks sent   (requirements/extractor.py)
  4. New requirements land                 (session.add_requirements)
  5. Host approves some                    (api/requirements.py PATCH status)
  6. Pipeline replaces agent_outputs       (ws/generate.py)
  7. Host edits one requirement title      (api/requirements.py PATCH title)
  8. Host ends the meeting                 (api/meetings.py end)
  --- restart ---
  9. Dashboard lists the meeting           (api/meetings.py list)
 10. Transcript reads back, ordered        (api/meetings.py get_transcript)
 11. Requirements read back with status    (api/requirements.py list)
 12. Agent outputs / prototype intact      (api/meetings.py agent-outputs)
 13. Export builds from reloaded state     (exports/builder.py)
 14. A new utterance still works on the
     reloaded session (id continuity)       (transcription_bot.py resume)

Run from the backend/ directory:
    python -m unittest tests.test_meeting_lifecycle_restart -v
"""

import tempfile
import unittest
from pathlib import Path

from app.exports.builder import build_export_zip
from app.meetings.session import SessionRegistry
from app.meetings.store import SessionStore


class MeetingLifecycleRestartTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "lifecycle.db"
        self.store: SessionStore | None = None

    def tearDown(self):
        if self.store is not None:
            self.store.close()
        self.tmp.cleanup()

    def _fresh_backend(self) -> SessionRegistry:
        """A 'restarted' process: brand-new objects over the same file.
        Closes the previous store first — on Windows an open sqlite handle
        keeps the file locked and TemporaryDirectory.cleanup() then fails."""
        if self.store is not None:
            self.store.close()
        self.store = SessionStore(self.db_path)
        return SessionRegistry(store=self.store)

    def test_full_lifecycle_survives_restart(self):
        # ---------- process 1: the live meeting ----------
        reg = self._fresh_backend()

        # 1. host creates
        session = reg.get_or_create("meet-42", name="Client kickoff", host_user_id="alice")

        # 2. bot: two utterances, second arrives first (concurrent ASR)
        late = session.add_transcript_line(
            "Client", "hi", "pehli baat", spoken_at="2026-09-04T10:00:02Z"
        )
        early = session.add_transcript_line(
            "Host", "gu", "બીજી વાત", spoken_at="2026-09-04T10:00:01Z"
        )
        session.set_translation(late.id, "the first point")
        session.set_translation(early.id, "the second point")

        # 3+4. extractor round: only unsent lines, then mark exactly those
        pending = session.pending_extraction_lines()
        self.assertEqual([l.id for l in pending], [early.id, late.id])
        session.mark_extracted([l.id for l in pending])
        session.add_requirements([
            {"title": "OTP login", "category": "Auth", "priority": "High", "confidence": 90},
            {"title": "Payment history", "category": "Feature", "priority": "Medium", "confidence": 75},
            {"title": "Admin panel", "category": "Feature", "priority": "Low", "confidence": 60},
        ])

        # 5. host approves two of three
        session.update_requirement_status(1, "approved")
        session.update_requirement_status(2, "approved")

        # 6. pipeline runs and replaces outputs
        session.replace_agent_outputs({
            "pm": "# PRD\n- OTP login\n- Payment history",
            "architect": "# Architecture\nmonolith, sqlite, fastapi",
            "prototype": "<html><body>clickable</body></html>",
        })

        # 7. host edits a title
        session.update_requirement_title(3, "Admin dashboard panel")

        # 8. end
        session.mark_ended()

        # ---------- process 2: "backend restart" ----------
        reg = self._fresh_backend()

        # 9. dashboard list finds it
        listed = reg.list_all()
        self.assertEqual([s.meeting_id for s in listed], ["meet-42"])
        summary = listed[0].summary()
        self.assertEqual(summary["name"], "Client kickoff")
        self.assertEqual(summary["status"], "ended")
        self.assertEqual(summary["transcript_lines"], 2)
        self.assertEqual(summary["requirement_count"], 3)
        self.assertTrue(summary["has_prototype"])

        # 10. transcript: chronological + patched translations
        session = reg.get("meet-42")
        self.assertEqual([l.original_text for l in session.transcript], ["બીજી વાત", "pehli baat"])
        self.assertEqual(
            [l.english_text for l in session.transcript],
            ["the second point", "the first point"],
        )
        self.assertEqual(session.transcript[0].id, early.id, "ids must NOT be renumbered")

        # 11. requirements with status + edited title + readiness
        by_id = {r.id: r for r in session.requirements}
        self.assertEqual(by_id[1].status, "approved")
        self.assertEqual(by_id[2].status, "approved")
        self.assertEqual(by_id[3].status, "pending")
        self.assertEqual(by_id[3].title, "Admin dashboard panel")
        self.assertEqual(session.readiness_percent(), 67)

        # 12. agent outputs intact
        self.assertEqual(session.agent_outputs["prototype"], "<html><body>clickable</body></html>")

        # 13. export builds from reloaded state
        zf_bytes = build_export_zip(session)
        self.assertGreater(len(zf_bytes), 1000)

        # 14. a NEW utterance on the reloaded session works, id continues.
        # Explicit spoken_at: the machine's real clock can be behind the
        # fixed stamps used above, and insertion order is a string compare
        # on spoken_at — without this the new line would land in front.
        new_line = session.add_transcript_line(
            "Client", "en", "after restart", spoken_at="2026-09-04T10:05:00Z"
        )
        self.assertEqual(new_line.id, 3, "counter must continue past the two persisted ids")
        again = self._fresh_backend().get("meet-42")
        self.assertEqual(len(again.transcript), 3, "the post-restart utterance must also persist")

        # extraction flags: the first two are extracted, the new one pending
        self.assertEqual(
            [l.extracted for l in again.transcript],
            [True, True, False],
        )

    def test_delete_after_restart_is_complete(self):
        reg = self._fresh_backend()
        session = reg.get_or_create("gone", host_user_id="alice")
        session.add_transcript_line("A", "en", "x")
        session.add_requirements([{"title": "R"}])
        session.replace_agent_outputs({"pm": "y"})

        reg = self._fresh_backend()
        self.assertTrue(reg.delete("gone"))

        reg = self._fresh_backend()
        self.assertIsNone(reg.get("gone"))
        self.assertEqual(reg.list_all(), [])
        self.assertFalse(self.store.has_meeting("gone"))


if __name__ == "__main__":
    unittest.main()
