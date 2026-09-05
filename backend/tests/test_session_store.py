"""
Round-trip tests for app.meetings.store.SessionStore.

These tests don't touch the rest of the app — they instantiate SessionStore
against a temp file, drive every public method, and assert what comes back.
That keeps the "did the schema actually persist what I gave it" question
honest without conflating it with the dataclass or registry behaviour.

Run from the backend/ directory:
    python -m unittest tests.test_session_store -v
"""

import datetime
import itertools
import tempfile
import unittest
from pathlib import Path

from app.meetings.session import MeetingSession, Requirement, TranscriptLine
from app.meetings.store import SessionStore


def _make_session(meeting_id: str = "m-store") -> MeetingSession:
    """A populated session, used as a fixture for round-trip tests."""
    s = MeetingSession(meeting_id=meeting_id, host_user_id="user-1")
    s.add_transcript_line("A", "hi", "first", spoken_at="2026-09-02T10:00:01Z")
    s.add_transcript_line("B", "gu", "second", spoken_at="2026-09-02T10:00:02Z")
    s.add_transcript_line("C", "en", "third", spoken_at="2026-09-02T10:00:03Z")
    s.add_requirements([
        {"title": "Login screen", "category": "Auth", "priority": "High", "confidence": 90},
        {"title": "Dark mode", "category": "UI", "priority": "Medium", "confidence": 70},
    ])
    s.agent_outputs["pm"] = "# PRD ..."
    return s


class SessionStoreTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()


class SchemaTest(SessionStoreTestBase):
    def test_init_is_idempotent(self):
        # Calling _ensure_schema twice (the second via a brand-new store on
        # the same file) must not blow up or duplicate anything.
        another = SessionStore(Path(self.tmp.name) / "test.db")
        try:
            self.assertTrue(another.has_meeting("nope") is False)
        finally:
            another.close()

    def test_fresh_store_is_empty(self):
        self.assertEqual(self.store.list_meeting_ids(), [])
        self.assertIsNone(self.store.load_meeting("anything"))


class MeetingRowTest(SessionStoreTestBase):
    def test_insert_then_load_returns_same_fields(self):
        s = MeetingSession(meeting_id="m-row", name="Client kickoff", host_user_id="u1")
        s.add_transcript_line("A", "en", "x", spoken_at="2026-09-02T10:00:00Z")
        s.add_requirements([{"title": "R1"}])

        self.store.insert_meeting(s)
        loaded = self.store.load_meeting("m-row")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.meeting_id, "m-row")
        self.assertEqual(loaded.name, "Client kickoff")
        self.assertEqual(loaded.host_user_id, "u1")
        self.assertEqual(loaded.status, "active")
        self.assertEqual(loaded.ended_at, None)

    def test_insert_is_idempotent(self):
        s = MeetingSession(meeting_id="m-once", name="v1")
        self.store.insert_meeting(s)
        # Second insert with the same id must not raise.
        self.store.insert_meeting(s)
        self.assertEqual(len(self.store.list_meeting_ids()), 1)

    def test_name_update_writes_through(self):
        s = MeetingSession(meeting_id="m-name", name="Original")
        self.store.insert_meeting(s)
        self.store.update_meeting_name("m-name", "Renamed")
        self.assertEqual(self.store.load_meeting("m-name").name, "Renamed")

    def test_host_backfill_does_not_overwrite_existing_host(self):
        s = MeetingSession(meeting_id="m-host", host_user_id="alice")
        self.store.insert_meeting(s)

        self.store.update_meeting_host("m-host", "bob")
        # alice is preserved — matches in-memory get_or_create semantics.
        self.assertEqual(self.store.load_meeting("m-host").host_user_id, "alice")

        # ...but a NULL host CAN be backfilled.
        s2 = MeetingSession(meeting_id="m-host2", host_user_id=None)
        self.store.insert_meeting(s2)
        self.store.update_meeting_host("m-host2", "carol")
        self.assertEqual(self.store.load_meeting("m-host2").host_user_id, "carol")

    def test_ended_status_persists(self):
        s = MeetingSession(meeting_id="m-end")
        self.store.insert_meeting(s)
        stamp = "2026-09-02T12:00:00Z"
        self.store.update_meeting_ended("m-end", "ended", stamp)
        loaded = self.store.load_meeting("m-end")
        self.assertEqual(loaded.status, "ended")
        self.assertEqual(loaded.ended_at, stamp)


class TranscriptLineTest(SessionStoreTestBase):
    def test_insert_and_load_round_trip(self):
        s = MeetingSession(meeting_id="m-tr")
        s.add_transcript_line("Vishesh", "hi", "namaste", spoken_at="2026-09-02T10:00:00Z")
        s.add_transcript_line("Client", "gu", "kem cho", spoken_at="2026-09-02T10:00:01Z",
                              english_text="how are you")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

        loaded = self.store.load_meeting("m-tr")
        self.assertEqual(len(loaded.transcript), 2)
        self.assertEqual([l.speaker for l in loaded.transcript], ["Vishesh", "Client"])
        self.assertEqual(loaded.transcript[0].english_text, None)
        self.assertEqual(loaded.transcript[1].english_text, "how are you")

    def test_chronological_order_survives_late_arrivals(self):
        # Lines were added in non-chronological order, but the loader must
        # return them sorted by spoken_at — same as the dataclass's
        # add_transcript_line guarantees in memory.
        s = MeetingSession(meeting_id="m-order")
        s.add_transcript_line("A", "hi", "second", spoken_at="2026-09-02T10:00:05Z")
        s.add_transcript_line("B", "hi", "first", spoken_at="2026-09-02T10:00:01Z")
        s.add_transcript_line("C", "hi", "third", spoken_at="2026-09-02T10:00:09Z")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

        loaded = self.store.load_meeting("m-order")
        self.assertEqual([l.original_text for l in loaded.transcript], ["first", "second", "third"])

    def test_ids_advance_past_persisted_max(self):
        # Two lines with ids 1 and 2 were inserted. The next add on a freshly
        # loaded session must produce id 3, not 1.
        s = MeetingSession(meeting_id="m-cnt")
        s.add_transcript_line("A", "en", "x")
        s.add_transcript_line("A", "en", "y")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

        loaded = self.store.load_meeting("m-cnt")
        new_line = loaded.add_transcript_line("A", "en", "z")
        self.assertEqual(new_line.id, 3)

    def test_update_translation_patches_only_the_matching_line(self):
        s = MeetingSession(meeting_id="m-trans")
        a = s.add_transcript_line("A", "gu", "ek")
        b = s.add_transcript_line("B", "gu", "be")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

        self.store.update_translation("m-trans", b.id, "two")

        loaded = self.store.load_meeting("m-trans")
        self.assertIsNone(loaded.transcript[0].english_text)
        self.assertEqual(loaded.transcript[1].english_text, "two")

    def test_mark_lines_extracted_targets_only_listed_ids(self):
        s = MeetingSession(meeting_id="m-ext")
        ids = [s.add_transcript_line("A", "en", f"line {i}").id for i in range(4)]
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

        # Mark only ids 0 and 2.
        self.store.mark_lines_extracted("m-ext", [ids[0], ids[2]])

        loaded = self.store.load_meeting("m-ext")
        flags = [l.extracted for l in loaded.transcript]
        self.assertEqual(flags, [True, False, True, False])

    def test_mark_lines_extracted_empty_list_is_noop(self):
        s = MeetingSession(meeting_id="m-empty")
        s.add_transcript_line("A", "en", "x")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)
        # Should not raise.
        self.store.mark_lines_extracted("m-empty", [])
        self.assertFalse(self.store.load_meeting("m-empty").transcript[0].extracted)


class RequirementTest(SessionStoreTestBase):
    def test_insert_and_load_round_trip(self):
        s = MeetingSession(meeting_id="m-req")
        s.add_requirements([
            {"title": "Login", "category": "Auth", "priority": "High", "confidence": 90},
            {"title": "Dark mode", "category": "UI", "priority": "Low", "confidence": 60},
        ])
        self.store.insert_meeting(s)
        for r in s.requirements:
            self.store.insert_requirement(s.meeting_id, r)

        loaded = self.store.load_meeting("m-req")
        self.assertEqual(len(loaded.requirements), 2)
        self.assertEqual(loaded.requirements[0].title, "Login")
        self.assertEqual(loaded.requirements[1].priority, "Low")

    def test_status_and_title_updates_persist(self):
        s = MeetingSession(meeting_id="m-mut")
        s.add_requirements([{"title": "Original", "category": "X", "priority": "High", "confidence": 80}])
        self.store.insert_meeting(s)
        for r in s.requirements:
            self.store.insert_requirement(s.meeting_id, r)

        req_id = s.requirements[0].id
        self.store.update_requirement_status("m-mut", req_id, "approved")
        self.store.update_requirement_title("m-mut", req_id, "Edited")

        loaded = self.store.load_meeting("m-mut")
        self.assertEqual(loaded.requirements[0].status, "approved")
        self.assertEqual(loaded.requirements[0].title, "Edited")


class AgentOutputsTest(SessionStoreTestBase):
    def test_replace_replaces_full_set(self):
        s = MeetingSession(meeting_id="m-out")
        self.store.insert_meeting(s)

        self.store.replace_agent_outputs("m-out", {"pm": "v1", "architect": "v1"})
        self.store.replace_agent_outputs("m-out", {"pm": "v2", "prototype": "v2"})

        loaded = self.store.load_meeting("m-out")
        self.assertEqual(
            set(loaded.agent_outputs.keys()),
            {"pm", "prototype"},
            "a full replace must drop entries that aren't in the new dict",
        )
        self.assertEqual(loaded.agent_outputs["pm"], "v2")
        self.assertEqual(loaded.agent_outputs["prototype"], "v2")

    def test_replace_with_empty_dict_clears(self):
        s = MeetingSession(meeting_id="m-clr")
        self.store.insert_meeting(s)
        self.store.replace_agent_outputs("m-clr", {"pm": "x"})
        self.store.replace_agent_outputs("m-clr", {})
        self.assertEqual(self.store.load_meeting("m-clr").agent_outputs, {})


class DeleteTest(SessionStoreTestBase):
    def test_delete_removes_meeting_and_all_dependents(self):
        s = _make_session(meeting_id="m-del")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)
        for r in s.requirements:
            self.store.insert_requirement(s.meeting_id, r)
        self.store.replace_agent_outputs(s.meeting_id, s.agent_outputs)

        self.assertTrue(self.store.delete_meeting("m-del"))
        self.assertIsNone(self.store.load_meeting("m-del"))
        # No orphaned rows — important so the meeting list doesn't
        # accidentally show the meeting back via JOINs.
        with self.store._lock:
            for table in ("transcript_lines", "requirements", "agent_outputs"):
                count = self.store._conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE meeting_id = ?", ("m-del",)
                ).fetchone()[0]
                self.assertEqual(count, 0, f"orphaned rows in {table}")

    def test_delete_unknown_meeting_returns_false(self):
        self.assertFalse(self.store.delete_meeting("never-existed"))


class ListTest(SessionStoreTestBase):
    def test_list_orders_by_created_at_desc(self):
        # Explicit created_at so the ordering is deterministic — three meetings
        # constructed back-to-back in a tight loop can otherwise get the same
        # microsecond-stamped ISO string, leaving ORDER BY created_at to
        # fall back on a non-deterministic tie-break.
        for mid, stamp in [("a", "2026-09-02T10:00:01Z"),
                           ("b", "2026-09-02T10:00:02Z"),
                           ("c", "2026-09-02T10:00:03Z")]:
            s = MeetingSession(meeting_id=mid, name=mid.upper())
            s.created_at = stamp
            self.store.insert_meeting(s)
        self.assertEqual(self.store.list_meeting_ids(), ["c", "b", "a"])


class FullRoundTripTest(SessionStoreTestBase):
    """
    A populated session goes in, comes back identically (modulo the dataclass's
    internal counters, which we don't compare) and is then mutated through the
    new instance — those mutations must persist.
    """

    def test_round_trip_then_mutate_again(self):
        s = _make_session(meeting_id="m-full")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)
        for r in s.requirements:
            self.store.insert_requirement(s.meeting_id, r)
        self.store.replace_agent_outputs(s.meeting_id, s.agent_outputs)

        loaded = self.store.load_meeting("m-full")
        self.assertEqual([l.id for l in loaded.transcript], [1, 2, 3])
        self.assertEqual([r.title for r in loaded.requirements], ["Login screen", "Dark mode"])
        self.assertEqual(loaded.agent_outputs, {"pm": "# PRD ..."})
        # Pending-extraction matches the in-memory semantics.
        self.assertEqual(len(loaded.pending_extraction_lines()), 3)
        self.assertEqual(loaded.readiness_percent(), 0)

        # Mutating the loaded session and re-persisting gives us back the
        # right state on a fresh load. This is the contract Chunk 3 will rely
        # on: in-memory mutations must be write-throughs to the store.
        new_line = loaded.add_transcript_line("D", "en", "fourth")
        for line in loaded.transcript:
            # Already-persisted lines would have been inserted via
            # insert_transcript_line on the FIRST pass; this simulates the
            # write-through that Chunk 3 will hook up.
            pass
        self.store.insert_transcript_line(loaded.meeting_id, new_line)
        loaded.set_translation(new_line.id, "fourth (en)")
        self.store.update_translation(loaded.meeting_id, new_line.id, "fourth (en)")
        loaded.mark_extracted([1, 2])
        self.store.mark_lines_extracted(loaded.meeting_id, [1, 2])

        reloaded = self.store.load_meeting("m-full")
        self.assertEqual([l.id for l in reloaded.transcript], [1, 2, 3, 4])
        self.assertEqual(reloaded.transcript[3].english_text, "fourth (en)")
        # read-readiness_percent and pending_extraction_lines are methods on
        # the dataclass and read the in-memory list, which was rehydrated
        # from the store with extracted flags set.
        pending_ids = [l.id for l in reloaded.pending_extraction_lines()]
        self.assertEqual(pending_ids, [3, 4])


if __name__ == "__main__":
    unittest.main()
