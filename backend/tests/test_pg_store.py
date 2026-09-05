"""
Round-trip tests for app.meetings.pg_store.PostgresSessionStore.

The Postgres store is the deploy-safe twin of the SQLite SessionStore: same
public methods, same synchronous contract, so SessionRegistry and every
MeetingSession mutator drive it unchanged. These tests prove that twin behaves
identically — insert/load/mutate/delete all round-trip the same way — WITHOUT a
network or a real Postgres.

How: every statement in pg_store is written to be valid on both Postgres and
SQLite, so we point PostgresSessionStore at an in-memory SQLite engine
(`sqlite://`, StaticPool so one shared connection survives across checkouts).
That exercises the real store code — the same INSERT/UPDATE/DELETE/ON CONFLICT
SQL and the same MeetingSession hydration — just against a local engine. The
Postgres-only concerns (the driver, pool_pre_ping, the async->sync URL rewrite)
are covered separately in test_pg_url_rewrite below, which needs no engine.

Run from the backend/ directory:
    python -m unittest tests.test_pg_store -v
"""

import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

try:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    _HAVE_SQLALCHEMY = True
except ImportError:  # SQLAlchemy is a real backend dep (auth DB) but not stubbed
    _HAVE_SQLALCHEMY = False

from app.meetings.session import MeetingSession  # noqa: E402


def _make_session(meeting_id: str = "m-store") -> MeetingSession:
    """A populated session — same fixture shape as test_session_store."""
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


@unittest.skipUnless(_HAVE_SQLALCHEMY, "SQLAlchemy not installed")
class PgStoreTestBase(unittest.TestCase):
    def setUp(self):
        from app.meetings.pg_store import PostgresSessionStore

        # One in-memory SQLite DB shared across all pooled connections, so the
        # schema created in __init__ is visible to every subsequent statement.
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        self.store = PostgresSessionStore(self.engine)

    def tearDown(self):
        self.store.close()


class SchemaTest(PgStoreTestBase):
    def test_init_is_idempotent(self):
        # A second store on the SAME engine re-runs CREATE TABLE IF NOT EXISTS
        # and must not blow up or duplicate anything.
        from app.meetings.pg_store import PostgresSessionStore

        another = PostgresSessionStore(self.engine)
        self.assertFalse(another.has_meeting("nope"))

    def test_fresh_store_is_empty(self):
        self.assertEqual(self.store.list_meeting_ids(), [])
        self.assertIsNone(self.store.load_meeting("anything"))


class MeetingRowTest(PgStoreTestBase):
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
        self.assertIsNone(loaded.ended_at)

    def test_insert_is_idempotent(self):
        s = MeetingSession(meeting_id="m-once", name="v1")
        self.store.insert_meeting(s)
        # Second insert with the same id must not raise (ON CONFLICT DO NOTHING).
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
        self.assertEqual(self.store.load_meeting("m-host").host_user_id, "alice")

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


class TranscriptLineTest(PgStoreTestBase):
    def _persist(self, s: MeetingSession) -> None:
        self.store.insert_meeting(s)
        for line in s.transcript:
            self.store.insert_transcript_line(s.meeting_id, line)

    def test_insert_and_load_round_trip(self):
        s = MeetingSession(meeting_id="m-tr")
        s.add_transcript_line("Vishesh", "hi", "namaste", spoken_at="2026-09-02T10:00:00Z")
        s.add_transcript_line("Client", "gu", "kem cho", spoken_at="2026-09-02T10:00:01Z",
                              english_text="how are you")
        self._persist(s)

        loaded = self.store.load_meeting("m-tr")
        self.assertEqual(len(loaded.transcript), 2)
        self.assertEqual([l.speaker for l in loaded.transcript], ["Vishesh", "Client"])
        self.assertIsNone(loaded.transcript[0].english_text)
        self.assertEqual(loaded.transcript[1].english_text, "how are you")

    def test_chronological_order_survives_late_arrivals(self):
        s = MeetingSession(meeting_id="m-order")
        s.add_transcript_line("A", "hi", "second", spoken_at="2026-09-02T10:00:05Z")
        s.add_transcript_line("B", "hi", "first", spoken_at="2026-09-02T10:00:01Z")
        s.add_transcript_line("C", "hi", "third", spoken_at="2026-09-02T10:00:09Z")
        self._persist(s)

        loaded = self.store.load_meeting("m-order")
        self.assertEqual([l.original_text for l in loaded.transcript], ["first", "second", "third"])

    def test_ids_advance_past_persisted_max(self):
        s = MeetingSession(meeting_id="m-cnt")
        s.add_transcript_line("A", "en", "x")
        s.add_transcript_line("A", "en", "y")
        self._persist(s)

        loaded = self.store.load_meeting("m-cnt")
        new_line = loaded.add_transcript_line("A", "en", "z")
        self.assertEqual(new_line.id, 3)

    def test_update_translation_patches_only_the_matching_line(self):
        s = MeetingSession(meeting_id="m-trans")
        s.add_transcript_line("A", "gu", "ek")
        b = s.add_transcript_line("B", "gu", "be")
        self._persist(s)

        self.store.update_translation("m-trans", b.id, "two")

        loaded = self.store.load_meeting("m-trans")
        self.assertIsNone(loaded.transcript[0].english_text)
        self.assertEqual(loaded.transcript[1].english_text, "two")

    def test_mark_lines_extracted_targets_only_listed_ids(self):
        s = MeetingSession(meeting_id="m-ext")
        ids = [s.add_transcript_line("A", "en", f"line {i}").id for i in range(4)]
        self._persist(s)

        self.store.mark_lines_extracted("m-ext", [ids[0], ids[2]])

        loaded = self.store.load_meeting("m-ext")
        flags = [l.extracted for l in loaded.transcript]
        self.assertEqual(flags, [True, False, True, False])

    def test_mark_lines_extracted_empty_list_is_noop(self):
        s = MeetingSession(meeting_id="m-empty")
        s.add_transcript_line("A", "en", "x")
        self._persist(s)
        self.store.mark_lines_extracted("m-empty", [])
        self.assertFalse(self.store.load_meeting("m-empty").transcript[0].extracted)


class RequirementTest(PgStoreTestBase):
    def _persist(self, s: MeetingSession) -> None:
        self.store.insert_meeting(s)
        for r in s.requirements:
            self.store.insert_requirement(s.meeting_id, r)

    def test_insert_and_load_round_trip(self):
        s = MeetingSession(meeting_id="m-req")
        s.add_requirements([
            {"title": "Login", "category": "Auth", "priority": "High", "confidence": 90},
            {"title": "Dark mode", "category": "UI", "priority": "Low", "confidence": 60},
        ])
        self._persist(s)

        loaded = self.store.load_meeting("m-req")
        self.assertEqual(len(loaded.requirements), 2)
        self.assertEqual(loaded.requirements[0].title, "Login")
        self.assertEqual(loaded.requirements[1].priority, "Low")

    def test_status_and_title_updates_persist(self):
        s = MeetingSession(meeting_id="m-mut")
        s.add_requirements([{"title": "Original", "category": "X", "priority": "High", "confidence": 80}])
        self._persist(s)

        req_id = s.requirements[0].id
        self.store.update_requirement_status("m-mut", req_id, "approved")
        self.store.update_requirement_title("m-mut", req_id, "Edited")

        loaded = self.store.load_meeting("m-mut")
        self.assertEqual(loaded.requirements[0].status, "approved")
        self.assertEqual(loaded.requirements[0].title, "Edited")


class AgentOutputsTest(PgStoreTestBase):
    def test_replace_replaces_full_set(self):
        s = MeetingSession(meeting_id="m-out")
        self.store.insert_meeting(s)

        self.store.replace_agent_outputs("m-out", {"pm": "v1", "architect": "v1"})
        self.store.replace_agent_outputs("m-out", {"pm": "v2", "prototype": "v2"})

        loaded = self.store.load_meeting("m-out")
        self.assertEqual(set(loaded.agent_outputs.keys()), {"pm", "prototype"})
        self.assertEqual(loaded.agent_outputs["pm"], "v2")
        self.assertEqual(loaded.agent_outputs["prototype"], "v2")

    def test_replace_with_empty_dict_clears(self):
        s = MeetingSession(meeting_id="m-clr")
        self.store.insert_meeting(s)
        self.store.replace_agent_outputs("m-clr", {"pm": "x"})
        self.store.replace_agent_outputs("m-clr", {})
        self.assertEqual(self.store.load_meeting("m-clr").agent_outputs, {})


class DeleteTest(PgStoreTestBase):
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

        # No orphaned rows in any dependent table.
        from sqlalchemy import text
        with self.engine.connect() as conn:
            for table in ("transcript_lines", "requirements", "agent_outputs"):
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE meeting_id = :mid"),
                    {"mid": "m-del"},
                ).scalar()
                self.assertEqual(count, 0, f"orphaned rows in {table}")

    def test_delete_unknown_meeting_returns_false(self):
        self.assertFalse(self.store.delete_meeting("never-existed"))


class ListTest(PgStoreTestBase):
    def test_list_orders_by_created_at_desc(self):
        for mid, stamp in [("a", "2026-09-02T10:00:01Z"),
                           ("b", "2026-09-02T10:00:02Z"),
                           ("c", "2026-09-02T10:00:03Z")]:
            s = MeetingSession(meeting_id=mid, name=mid.upper())
            s.created_at = stamp
            self.store.insert_meeting(s)
        self.assertEqual(self.store.list_meeting_ids(), ["c", "b", "a"])


class FullRoundTripTest(PgStoreTestBase):
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
        self.assertEqual(len(loaded.pending_extraction_lines()), 3)
        self.assertEqual(loaded.readiness_percent(), 0)

        new_line = loaded.add_transcript_line("D", "en", "fourth")
        self.store.insert_transcript_line(loaded.meeting_id, new_line)
        loaded.set_translation(new_line.id, "fourth (en)")
        self.store.update_translation(loaded.meeting_id, new_line.id, "fourth (en)")
        loaded.mark_extracted([1, 2])
        self.store.mark_lines_extracted(loaded.meeting_id, [1, 2])

        reloaded = self.store.load_meeting("m-full")
        self.assertEqual([l.id for l in reloaded.transcript], [1, 2, 3, 4])
        self.assertEqual(reloaded.transcript[3].english_text, "fourth (en)")
        pending_ids = [l.id for l in reloaded.pending_extraction_lines()]
        self.assertEqual(pending_ids, [3, 4])


class PgUrlRewriteTest(unittest.TestCase):
    """
    The async->sync URL rewrite is pure string logic and needs no engine, so
    it runs even where SQLAlchemy isn't installed. This is the one piece of
    pg_store that only matters on the real Postgres path (the driver and TLS
    option differ between asyncpg and psycopg2), so it's worth pinning.
    """

    def test_asyncpg_becomes_psycopg2(self):
        from app.meetings.pg_store import to_sync_pg_url
        out = to_sync_pg_url("postgresql+asyncpg://u:p@host.neon.tech/db")
        self.assertTrue(out.startswith("postgresql+psycopg2://"))
        self.assertIn("u:p@host.neon.tech", out)

    def test_ssl_require_becomes_sslmode_require(self):
        from app.meetings.pg_store import to_sync_pg_url
        out = to_sync_pg_url("postgresql+asyncpg://u:p@host.neon.tech/db?ssl=require")
        self.assertIn("sslmode=require", out)
        self.assertNotIn("ssl=require", out)

    def test_plain_postgres_scheme_gets_psycopg2_driver(self):
        from app.meetings.pg_store import to_sync_pg_url
        out = to_sync_pg_url("postgres://u:p@host/db")
        self.assertTrue(out.startswith("postgresql+psycopg2://"))

    def test_existing_sslmode_is_left_alone(self):
        from app.meetings.pg_store import to_sync_pg_url
        out = to_sync_pg_url("postgresql+asyncpg://u:p@host/db?sslmode=verify-full")
        self.assertIn("sslmode=verify-full", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
