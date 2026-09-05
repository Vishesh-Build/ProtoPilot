"""
Registry-level tests for the write-through wiring in SessionRegistry.

These exercise the new code path in app/meetings/session.py: when a store
is configured, get_or_create / get / list_all / delete consult SQLite,
and the existing get_or_create semantics (name overwrites, host only
backfills, no override) are preserved across the load/save boundary.

Tests that don't configure a store fall through to the in-memory path
and are already covered by test_transcript_lines and
test_requirement_extraction (which build MeetingSession directly).

Run from the backend/ directory:
    python -m unittest tests.test_session_registry_persistence -v
"""

import tempfile
import unittest
from pathlib import Path

from app.meetings.session import MeetingSession, SessionRegistry
from app.meetings.store import SessionStore


def _isolated_registry() -> tuple[SessionRegistry, SessionStore, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    store = SessionStore(Path(tmp.name) / "registry.db")
    reg = SessionRegistry(store=store)
    return reg, store, tmp


class RegistryWithoutStoreTest(unittest.TestCase):
    """
    A registry with no store keeps the pre-persistence behaviour. The
    existing tests rely on this — they don't call init_store().
    """

    def test_in_memory_path_still_works(self):
        reg = SessionRegistry()
        s1 = reg.get_or_create("m-im", name="First", host_user_id="alice")
        self.assertEqual(s1.host_user_id, "alice")

        # Second call backfills host only if None.
        s2 = reg.get_or_create("m-im", host_user_id="bob")
        self.assertIs(s1, s2)
        self.assertEqual(s2.host_user_id, "alice", "existing host must NOT be overridden")

    def test_in_memory_get_returns_none_for_unknown(self):
        reg = SessionRegistry()
        self.assertIsNone(reg.get("nope"))

    def test_in_memory_list_returns_in_reverse_creation_order(self):
        reg = SessionRegistry()
        # Explicit created_at so the sort key is deterministic — three
        # meetings built in a tight loop can get the same microsecond
        # stamp, and a stable sort then keeps insertion order.
        for i, stamp in enumerate(["10:00:01", "10:00:02", "10:00:03"]):
            s = reg.get_or_create(f"m-{i}")
            s.created_at = f"2026-09-02T{stamp}Z"
        ids = [s.meeting_id for s in reg.list_all()]
        self.assertEqual(ids, ["m-2", "m-1", "m-0"])

    def test_in_memory_delete_drops_only_that_meeting(self):
        reg = SessionRegistry()
        reg.get_or_create("m-a")
        reg.get_or_create("m-b")
        self.assertTrue(reg.delete("m-a"))
        self.assertIsNone(reg.get("m-a"))
        self.assertIsNotNone(reg.get("m-b"))
        self.assertFalse(reg.delete("m-a"))


class RegistryWithStoreTest(unittest.TestCase):
    """The new behaviour: a registry that consults + writes a SessionStore."""

    def setUp(self):
        self.reg, self.store, self.tmp = _isolated_registry()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_get_or_create_persists_new_meeting_to_store(self):
        s = self.reg.get_or_create("m-new", name="Kickoff", host_user_id="alice")

        # Source of truth is now the store, not the in-process cache.
        self.assertTrue(self.store.has_meeting("m-new"))
        loaded = self.store.load_meeting("m-new")
        self.assertEqual(loaded.name, "Kickoff")
        self.assertEqual(loaded.host_user_id, "alice")
        self.assertEqual(loaded.meeting_id, "m-new")

    def test_get_or_create_idempotent(self):
        a = self.reg.get_or_create("m-once", name="v1", host_user_id="alice")
        b = self.reg.get_or_create("m-once", name="v1", host_user_id="alice")
        self.assertIs(a, b, "second call returns the same in-process object")

    def test_name_update_writes_through_to_store(self):
        self.reg.get_or_create("m-name", name="Original")
        self.reg.get_or_create("m-name", name="Renamed")
        self.assertEqual(self.store.load_meeting("m-name").name, "Renamed")

    def test_host_backfill_does_not_override_existing_host(self):
        self.reg.get_or_create("m-h", host_user_id="alice")
        self.reg.get_or_create("m-h", host_user_id="bob")
        self.assertEqual(self.store.load_meeting("m-h").host_user_id, "alice")

    def test_host_backfills_when_previously_none(self):
        self.reg.get_or_create("m-h2", host_user_id=None)
        self.reg.get_or_create("m-h2", host_user_id="carol")
        self.assertEqual(self.store.load_meeting("m-h2").host_user_id, "carol")

    def test_get_hydrates_from_store_on_miss(self):
        # Pre-populate the store directly (as if from a prior process).
        s = MeetingSession(meeting_id="m-prior", name="Old", host_user_id="alice")
        s.add_transcript_line("A", "en", "previous", spoken_at="2026-09-02T10:00:00Z")
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

        # A fresh registry against the same store must read the meeting back.
        fresh_reg = SessionRegistry(store=self.store)
        loaded = fresh_reg.get("m-prior")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Old")
        self.assertEqual([l.original_text for l in loaded.transcript], ["previous"])

    def test_list_all_returns_hydrated_sessions(self):
        for mid in ("a", "b", "c"):
            self.reg.get_or_create(mid)
        # Force a fresh registry so list_all has to hydrate everything.
        fresh_reg = SessionRegistry(store=self.store)
        ids = [s.meeting_id for s in fresh_reg.list_all()]
        self.assertEqual(set(ids), {"a", "b", "c"})

    def test_delete_removes_from_store_and_cache(self):
        self.reg.get_or_create("m-del")
        self.assertTrue(self.store.has_meeting("m-del"))
        self.assertTrue(self.reg.delete("m-del"))
        self.assertFalse(self.store.has_meeting("m-del"))
        self.assertIsNone(self.reg.get("m-del"))

    def test_delete_unknown_meeting_returns_false(self):
        self.assertFalse(self.reg.delete("never-existed"))

    def test_set_store_late_binds_and_clears_cache(self):
        # Registry with no store: meetings live in memory.
        reg = SessionRegistry()
        reg.get_or_create("m-late", name="v1")
        # Now the store comes online; cache must be invalidated so the
        # next read goes to the store and reflects current truth.
        reg.set_store(self.store)
        self.assertIsNone(reg.get("m-late"), "the cache must be cleared on set_store")


class RestartSimulationTest(unittest.TestCase):
    """
    End-to-end: a meeting goes through a registry backed by a store, then
    a brand-new registry opens the same file and finds the same meeting.
    This is the exact behaviour the user asked for ('backend restart =
    meeting still there').
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "restart.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_meeting_survives_registry_recreation(self):
        store1 = SessionStore(self.path)
        reg1 = SessionRegistry(store=store1)
        reg1.get_or_create("m-survive", name="Sprint planning", host_user_id="alice")
        store1.close()

        # Simulate a full process restart.
        store2 = SessionStore(self.path)
        reg2 = SessionRegistry(store=store2)
        loaded = reg2.get("m-survive")
        self.assertIsNotNone(loaded, "meeting must survive a process restart")
        self.assertEqual(loaded.name, "Sprint planning")
        self.assertEqual(loaded.host_user_id, "alice")
        store2.close()


if __name__ == "__main__":
    unittest.main()
