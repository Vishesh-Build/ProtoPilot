"""
SQLite-backed store for meeting session state.

The previous in-memory dict lost every meeting on backend restart. This module
adds a write-through persistence layer that survives restarts without changing
the public API of `MeetingSession` / `Requirement` / `TranscriptLine` — those
are still plain dataclasses, and a test that does `MeetingSession(meeting_id="x")`
without any DB continues to work exactly as it did.

Design:

  * One file = one SQLite database. The path is taken from settings
    (`meeting_store_path`, default `./protopilot_meetings.db`) and the schema
    is created idempotently on first call to `init_store()`.
  * The store is a thin layer over stdlib `sqlite3`. The app already pulls
    `sqlalchemy[asyncio]>=2.0` for the auth DB; this is intentionally a
    separate, dependency-free connection so the meeting path can't block on
    or be blocked by the cloud auth DB.
  * All mutating methods are synchronous and take a `MeetingSession` (or the
    individual fields). Callers running in an asyncio context wrap them in
    `asyncio.to_thread` only if they care about latency on long writes — the
    writes themselves are single-statement and microsecond-fast.
  * `load_meeting()` returns a fully-hydrated `MeetingSession` (transcript
    sorted by spoken_at, requirements in insertion order, agent_outputs dict),
    so the in-memory representation after a load is identical to one that was
    just constructed in-process.

Concurrency: SQLite's own locking is sufficient for the access pattern
(one writer per meeting at a time, occasional concurrent reads). A single
process is the documented target. Multi-process write contention would
require WAL mode + retry-on-busy, which is out of scope here.
"""

from __future__ import annotations

import bisect
import datetime
import logging
import sqlite3
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.meetings.session import MeetingSession, Requirement, TranscriptLine

logger = logging.getLogger("protopilot.meetings.store")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
  meeting_id     TEXT PRIMARY KEY,
  name           TEXT NOT NULL DEFAULT 'Untitled Meeting',
  host_user_id   TEXT NULL,
  created_at     TEXT NOT NULL,
  ended_at       TEXT NULL,
  status         TEXT NOT NULL DEFAULT 'active',
  next_line_id   INTEGER NOT NULL DEFAULT 1,
  next_req_id    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transcript_lines (
  meeting_id     TEXT NOT NULL,
  line_id        INTEGER NOT NULL,
  speaker        TEXT NOT NULL,
  language       TEXT NOT NULL,
  original_text  TEXT NOT NULL,
  english_text   TEXT NULL,
  spoken_at      TEXT NOT NULL,
  extracted      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (meeting_id, line_id)
);
CREATE INDEX IF NOT EXISTS idx_transcript_spoken
  ON transcript_lines (meeting_id, spoken_at);
CREATE INDEX IF NOT EXISTS idx_transcript_pending
  ON transcript_lines (meeting_id, extracted);

CREATE TABLE IF NOT EXISTS requirements (
  meeting_id     TEXT NOT NULL,
  requirement_id INTEGER NOT NULL,
  title          TEXT NOT NULL,
  category       TEXT NOT NULL,
  priority       TEXT NOT NULL,
  confidence     INTEGER NOT NULL,
  status         TEXT NOT NULL DEFAULT 'pending',
  PRIMARY KEY (meeting_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS agent_outputs (
  meeting_id     TEXT NOT NULL,
  agent_id       TEXT NOT NULL,
  output         TEXT NOT NULL,
  PRIMARY KEY (meeting_id, agent_id)
);
"""


class SessionStore:
    """
    Owns one sqlite3 connection. Created once at startup via `init_store()`,
    then read/written from anywhere in the process.

    Methods are intentionally low-level — `SessionRegistry` is the higher-level
    abstraction that handles caching, write-through on mutation, and the
    `get_or_create` semantics that this layer doesn't know about.
    """

    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        # check_same_thread=False because the asyncio event loop runs the
        # connection on whichever thread happens to be active. SQLite serialises
        # its own writes internally, and the connection has a single internal
        # mutex, so the "one writer at a time" guarantee is preserved.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._lock:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------ reads

    def has_meeting(self, meeting_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("SELECT 1 FROM meetings WHERE meeting_id = ?", (meeting_id,))
            return cur.fetchone() is not None

    def load_meeting(self, meeting_id: str) -> "MeetingSession | None":
        """
        Hydrates a full MeetingSession from the store, or returns None if no
        such meeting exists. Transcript comes back sorted by spoken_at (then
        insertion order) so the in-memory representation matches what the
        dataclass produces from a fresh `add_transcript_line` sequence.
        """
        # Local import: `app.meetings.session` is the file we're persisting,
        # and importing it from inside this module keeps both sides
        # independently importable in tests.
        from app.meetings.session import MeetingSession, Requirement, TranscriptLine

        with self._lock:
            row = self._conn.execute(
                "SELECT meeting_id, name, host_user_id, created_at, ended_at, status, "
                "next_line_id, next_req_id FROM meetings WHERE meeting_id = ?",
                (meeting_id,),
            ).fetchone()
            if row is None:
                return None

            transcript_rows = self._conn.execute(
                "SELECT line_id, speaker, language, original_text, english_text, "
                "spoken_at, extracted FROM transcript_lines "
                "WHERE meeting_id = ? ORDER BY spoken_at, line_id",
                (meeting_id,),
            ).fetchall()
            requirement_rows = self._conn.execute(
                "SELECT requirement_id, title, category, priority, confidence, status "
                "FROM requirements WHERE meeting_id = ? ORDER BY requirement_id",
                (meeting_id,),
            ).fetchall()
            output_rows = self._conn.execute(
                "SELECT agent_id, output FROM agent_outputs WHERE meeting_id = ?",
                (meeting_id,),
            ).fetchall()

        import itertools

        session = MeetingSession(
            meeting_id=row["meeting_id"],
            name=row["name"],
            host_user_id=row["host_user_id"],
            created_at=row["created_at"],
            ended_at=row["ended_at"],
            status=row["status"],
        )
        # The dataclass has its own _id_counter / _line_counter; advance them
        # past the last id we've already used so the next add_* call doesn't
        # collide with rows that are already in the DB.
        session._id_counter = itertools.count(row["next_req_id"])
        session._line_counter = itertools.count(row["next_line_id"])

        for tr in transcript_rows:
            session.transcript.append(TranscriptLine(
                id=tr["line_id"],
                speaker=tr["speaker"],
                language=tr["language"],
                original_text=tr["original_text"],
                english_text=tr["english_text"],
                spoken_at=tr["spoken_at"],
                extracted=bool(tr["extracted"]),
            ))

        for rr in requirement_rows:
            session.requirements.append(Requirement(
                id=rr["requirement_id"],
                title=rr["title"],
                category=rr["category"],
                priority=rr["priority"],
                confidence=rr["confidence"],
                status=rr["status"],
            ))

        for ar in output_rows:
            session.agent_outputs[ar["agent_id"]] = ar["output"]

        return session

    def list_meeting_ids(self) -> list[str]:
        """Returns meeting ids ordered by created_at desc — matches the
        in-memory SessionRegistry.list_all ordering."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT meeting_id FROM meetings ORDER BY created_at DESC"
            ).fetchall()
        return [r["meeting_id"] for r in rows]

    # ----------------------------------------------------------------- writes

    def insert_meeting(self, session: "MeetingSession") -> None:
        """Creates the meeting row. No-op if it already exists — `get_or_create`
        semantics are the caller's job; this is the primitive that does the
        insert half."""
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO meetings "
                "(meeting_id, name, host_user_id, created_at, ended_at, status, "
                " next_line_id, next_req_id) "
                "VALUES (?, ?, ?, ?, ?, ?, 1, 1)",
                (
                    session.meeting_id,
                    session.name,
                    session.host_user_id,
                    session.created_at,
                    session.ended_at,
                    session.status,
                ),
            )

    def update_meeting_name(self, meeting_id: str, name: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE meetings SET name = ? WHERE meeting_id = ?",
                (name, meeting_id),
            )

    def update_meeting_host(self, meeting_id: str, host_user_id: str) -> None:
        """Backfills host_user_id only if it was previously NULL — matches
        `get_or_create` semantics: an existing host is never overwritten."""
        with self._lock:
            self._conn.execute(
                "UPDATE meetings SET host_user_id = ? "
                "WHERE meeting_id = ? AND host_user_id IS NULL",
                (host_user_id, meeting_id),
            )

    def update_meeting_ended(self, meeting_id: str, status: str, ended_at: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE meetings SET status = ?, ended_at = ? WHERE meeting_id = ?",
                (status, ended_at, meeting_id),
            )

    def insert_transcript_line(self, meeting_id: str, line: "TranscriptLine") -> None:
        """Atomically inserts the line and advances the meeting's next_line_id
        past it, so a subsequent restart never hands out the same id twice."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO transcript_lines "
                "(meeting_id, line_id, speaker, language, original_text, "
                " english_text, spoken_at, extracted) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    meeting_id, line.id, line.speaker, line.language,
                    line.original_text, line.english_text, line.spoken_at,
                    1 if line.extracted else 0,
                ),
            )
            self._conn.execute(
                "UPDATE meetings SET next_line_id = ? WHERE meeting_id = ?",
                (line.id + 1, meeting_id),
            )

    def update_translation(self, meeting_id: str, line_id: int, english_text: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE transcript_lines SET english_text = ? "
                "WHERE meeting_id = ? AND line_id = ?",
                (english_text, meeting_id, line_id),
            )

    def mark_lines_extracted(self, meeting_id: str, line_ids: list[int]) -> None:
        """Sets extracted=1 for the given ids in one statement. Anything not
        in the list is left alone — that's the property the requirement
        extractor relies on."""
        if not line_ids:
            return
        # sqlite has a default SQLITE_MAX_VARIABLE_NUMBER of 999; chunk to be
        # safe even though meeting transcripts never get that long.
        for chunk_start in range(0, len(line_ids), 500):
            chunk = line_ids[chunk_start:chunk_start + 500]
            placeholders = ",".join("?" for _ in chunk)
            params: list = [meeting_id, *chunk]
            with self._lock:
                self._conn.execute(
                    f"UPDATE transcript_lines SET extracted = 1 "
                    f"WHERE meeting_id = ? AND line_id IN ({placeholders})",
                    params,
                )

    def insert_requirement(self, meeting_id: str, req: "Requirement") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO requirements "
                "(meeting_id, requirement_id, title, category, priority, confidence, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (meeting_id, req.id, req.title, req.category, req.priority,
                 req.confidence, req.status),
            )
            self._conn.execute(
                "UPDATE meetings SET next_req_id = ? WHERE meeting_id = ?",
                (req.id + 1, meeting_id),
            )

    def update_requirement_status(self, meeting_id: str, requirement_id: int, status_value: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE requirements SET status = ? "
                "WHERE meeting_id = ? AND requirement_id = ?",
                (status_value, meeting_id, requirement_id),
            )

    def update_requirement_title(self, meeting_id: str, requirement_id: int, title: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE requirements SET title = ? "
                "WHERE meeting_id = ? AND requirement_id = ?",
                (title, meeting_id, requirement_id),
            )

    def replace_agent_outputs(self, meeting_id: str, outputs: dict[str, str]) -> None:
        """Replaces the full set of agent outputs for a meeting. This matches
        the in-memory behaviour where the pipeline run overwrites the entire
        dict atomically. One DELETE + bulk INSERT, all in one statement."""
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                self._conn.execute(
                    "DELETE FROM agent_outputs WHERE meeting_id = ?",
                    (meeting_id,),
                )
                if outputs:
                    self._conn.executemany(
                        "INSERT INTO agent_outputs (meeting_id, agent_id, output) "
                        "VALUES (?, ?, ?)",
                        [(meeting_id, agent_id, output) for agent_id, output in outputs.items()],
                    )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def delete_meeting(self, meeting_id: str) -> bool:
        """Removes the meeting and all its dependent rows. Returns True if
        anything was deleted."""
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                for table in ("transcript_lines", "requirements", "agent_outputs"):
                    self._conn.execute(
                        f"DELETE FROM {table} WHERE meeting_id = ?",
                        (meeting_id,),
                    )
                cur = self._conn.execute(
                    "DELETE FROM meetings WHERE meeting_id = ?",
                    (meeting_id,),
                )
                self._conn.execute("COMMIT")
                return cur.rowcount > 0
            except Exception:
                self._conn.execute("ROLLBACK")
                raise


# Module-level singleton. `init_store()` is called once from main.py's
# startup event; tests construct their own SessionStore against a temp file
# and never touch the singleton.
_store: SessionStore | None = None
_store_lock = threading.Lock()


def init_store(db_path: str | Path) -> SessionStore:
    """
    Idempotent startup hook. Replaces the singleton in place (or creates it
    on first call). Tests should NOT call this — they instantiate SessionStore
    directly against a tmp file.
    """
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        # Ensure the parent directory exists so a path like ./data/meetings.db
        # doesn't fail on a fresh checkout.
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _store = SessionStore(db_path)
        logger.info("meeting store ready at %s", db_path)
        return _store


def get_store() -> SessionStore:
    """
    Returns the process-wide store. Raises if init_store() hasn't been called
    — that's the right behaviour in production (fail fast) and tests bypass
    it by holding their own store.
    """
    if _store is None:
        raise RuntimeError(
            "meeting store is not initialised — call app.meetings.store.init_store(path) "
            "from the FastAPI startup event before handling any request"
        )
    return _store
