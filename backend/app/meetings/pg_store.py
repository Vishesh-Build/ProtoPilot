"""
Postgres-backed store for meeting session state.

This is the deploy-safe twin of `store.py` (the SQLite store). On a host with
an ephemeral disk (Render, Fly, most free PaaS) the SQLite file is wiped on
every deploy/restart, taking every meeting, transcript and generated prototype
with it. Pointing the meeting store at the same managed Postgres the auth DB
already uses (Neon) makes that state survive redeploys.

Design — deliberately a *drop-in* for `SessionStore`:

  * Same public method names and signatures, all still **synchronous**, so
    `SessionRegistry` and every `MeetingSession` mutator call it exactly as
    they call the SQLite store — nothing else in the app changes, and the
    choice between the two backends is one setting (`meeting_store_backend`).
  * Backed by a **synchronous** SQLAlchemy Core engine, NOT the auth DB's
    async engine: the registry calls these methods without `await` (under a
    threading.Lock), so an async engine could not be driven from here without
    reworking every call site. A separate sync engine keeps that contract.
  * `pool_pre_ping=True` + a short `pool_recycle`: Neon (and most managed
    Postgres) silently drop idle connections, and without pre-ping the first
    write after an idle spell would raise. This is the same reliability
    pattern the auth engine already uses (`app/db/database.py`).
  * Every statement is written to be valid on BOTH Postgres and SQLite
    (`ON CONFLICT DO NOTHING`, named binds, no dialect-only syntax). That is
    what lets the tests exercise the real store logic against an in-memory
    SQLite engine with no network — see tests/test_pg_store.py.

Latency note: with SQLite these writes were microsecond-fast local-disk calls
made straight on the event loop; against Neon each is a network round trip
(tens of ms). The caption critical path does exactly one INSERT before the
broadcast, so that is the added per-caption latency. For the documented target
(a single backend instance, a handful of concurrent meetings) that is fine;
moving the hot-path writes onto `asyncio.to_thread` would be the next step if a
much larger meeting ever needs it, but that also moves the in-memory list
mutation off the single event-loop thread, so it is intentionally NOT done here.

Concurrency: unlike the SQLite store there is no single shared connection and
so no store-level lock — each call checks out its own pooled connection and
Postgres serialises writes itself. Meeting ids/line ids are still generated
in-process by `MeetingSession` (single instance per meeting in the registry),
so a single backend process hands out unique ids; the `next_*_id` columns are
only the restart-recovery hint. Multiple *processes* writing the same meeting
is out of scope, exactly as it was for the SQLite store.
"""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from app.meetings.session import MeetingSession, Requirement, TranscriptLine

logger = logging.getLogger("protopilot.meetings.pg_store")

# Split into individual statements: SQLAlchemy's text() executes one statement
# per call (there is no cross-dialect `executescript`). All of these are valid
# on Postgres and on SQLite >= 3.24, which is what keeps the store testable
# against an in-memory SQLite engine with no network.
_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS meetings (
      meeting_id     TEXT PRIMARY KEY,
      name           TEXT NOT NULL DEFAULT 'Untitled Meeting',
      host_user_id   TEXT NULL,
      created_at     TEXT NOT NULL,
      ended_at       TEXT NULL,
      status         TEXT NOT NULL DEFAULT 'active',
      next_line_id   INTEGER NOT NULL DEFAULT 1,
      next_req_id    INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
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
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_transcript_spoken ON transcript_lines (meeting_id, spoken_at)",
    "CREATE INDEX IF NOT EXISTS idx_transcript_pending ON transcript_lines (meeting_id, extracted)",
    """
    CREATE TABLE IF NOT EXISTS requirements (
      meeting_id     TEXT NOT NULL,
      requirement_id INTEGER NOT NULL,
      title          TEXT NOT NULL,
      category       TEXT NOT NULL,
      priority       TEXT NOT NULL,
      confidence     INTEGER NOT NULL,
      status         TEXT NOT NULL DEFAULT 'pending',
      PRIMARY KEY (meeting_id, requirement_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_outputs (
      meeting_id     TEXT NOT NULL,
      agent_id       TEXT NOT NULL,
      output         TEXT NOT NULL,
      PRIMARY KEY (meeting_id, agent_id)
    )
    """,
)


def to_sync_pg_url(database_url: str) -> str:
    """
    Turn the auth DB's async URL into a synchronous psycopg2 URL for this store.

    The auth DB is configured as `postgresql+asyncpg://...` (see settings) and
    asyncpg spells its TLS option `ssl=require`; the synchronous psycopg2 driver
    used here wants `postgresql+psycopg2://...` and `sslmode=require` instead.
    Converting here means the operator sets ONE DATABASE_URL and both the auth
    DB and the meeting store use it correctly.
    """
    parts = urlsplit(database_url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql") or scheme.startswith("postgresql+"):
        scheme = "postgresql+psycopg2"
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    # asyncpg: ssl=require|true ; psycopg2: sslmode=require. Only translate when
    # the operator hasn't already given a psycopg2-style sslmode.
    ssl_value = query.pop("ssl", None)
    if ssl_value is not None and "sslmode" not in query:
        query["sslmode"] = "require" if ssl_value in ("require", "true", "1", "yes") else ssl_value
    new_query = urlencode(query)
    return urlunsplit((scheme, parts.netloc, parts.path, new_query, parts.fragment))


class PostgresSessionStore:
    """
    Synchronous, SQLAlchemy-Core-backed twin of `SessionStore`. Construct it
    with a sync Engine — production passes a Neon psycopg2 engine (via
    `init_pg_store`); tests pass an in-memory SQLite engine, since every
    statement below is valid on both.
    """

    def __init__(self, engine: Engine):
        self._engine = engine
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._engine.begin() as conn:
            for stmt in _SCHEMA_STATEMENTS:
                conn.execute(text(stmt))

    def close(self) -> None:
        self._engine.dispose()

    # ------------------------------------------------------------------ reads

    def has_meeting(self, meeting_id: str) -> bool:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM meetings WHERE meeting_id = :mid"),
                {"mid": meeting_id},
            ).first()
            return row is not None

    def load_meeting(self, meeting_id: str) -> "MeetingSession | None":
        """
        Hydrates a full MeetingSession, or None if the meeting doesn't exist.
        Identical in shape to SessionStore.load_meeting: transcript sorted by
        spoken_at then insertion order, requirements in insertion order, agent
        outputs as a dict, and the id counters advanced past the stored maxima.
        """
        from app.meetings.session import MeetingSession, Requirement, TranscriptLine

        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT meeting_id, name, host_user_id, created_at, ended_at, status, "
                    "next_line_id, next_req_id FROM meetings WHERE meeting_id = :mid"
                ),
                {"mid": meeting_id},
            ).mappings().first()
            if row is None:
                return None

            transcript_rows = conn.execute(
                text(
                    "SELECT line_id, speaker, language, original_text, english_text, "
                    "spoken_at, extracted FROM transcript_lines "
                    "WHERE meeting_id = :mid ORDER BY spoken_at, line_id"
                ),
                {"mid": meeting_id},
            ).mappings().all()
            requirement_rows = conn.execute(
                text(
                    "SELECT requirement_id, title, category, priority, confidence, status "
                    "FROM requirements WHERE meeting_id = :mid ORDER BY requirement_id"
                ),
                {"mid": meeting_id},
            ).mappings().all()
            output_rows = conn.execute(
                text("SELECT agent_id, output FROM agent_outputs WHERE meeting_id = :mid"),
                {"mid": meeting_id},
            ).mappings().all()

        session = MeetingSession(
            meeting_id=row["meeting_id"],
            name=row["name"],
            host_user_id=row["host_user_id"],
            created_at=row["created_at"],
            ended_at=row["ended_at"],
            status=row["status"],
        )
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
        """Meeting ids ordered by created_at desc — matches SessionRegistry.list_all."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT meeting_id FROM meetings ORDER BY created_at DESC")
            ).all()
        return [r[0] for r in rows]

    # ----------------------------------------------------------------- writes

    def insert_meeting(self, session: "MeetingSession") -> None:
        """Creates the meeting row; no-op if it already exists (get_or_create
        semantics live in the registry, this is just the insert primitive)."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO meetings "
                    "(meeting_id, name, host_user_id, created_at, ended_at, status, "
                    " next_line_id, next_req_id) "
                    "VALUES (:meeting_id, :name, :host_user_id, :created_at, :ended_at, "
                    " :status, 1, 1) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "meeting_id": session.meeting_id,
                    "name": session.name,
                    "host_user_id": session.host_user_id,
                    "created_at": session.created_at,
                    "ended_at": session.ended_at,
                    "status": session.status,
                },
            )

    def update_meeting_name(self, meeting_id: str, name: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE meetings SET name = :name WHERE meeting_id = :mid"),
                {"name": name, "mid": meeting_id},
            )

    def update_meeting_host(self, meeting_id: str, host_user_id: str) -> None:
        """Backfills host_user_id only if it was NULL — an existing host is
        never overwritten (matches get_or_create semantics)."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE meetings SET host_user_id = :host WHERE meeting_id = :mid "
                    "AND host_user_id IS NULL"
                ),
                {"host": host_user_id, "mid": meeting_id},
            )

    def update_meeting_ended(self, meeting_id: str, status: str, ended_at: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE meetings SET status = :status, ended_at = :ended_at WHERE meeting_id = :mid"),
                {"status": status, "ended_at": ended_at, "mid": meeting_id},
            )

    def insert_transcript_line(self, meeting_id: str, line: "TranscriptLine") -> None:
        """Inserts the line and advances next_line_id past it in one transaction,
        so a restart never hands out the same id twice."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO transcript_lines "
                    "(meeting_id, line_id, speaker, language, original_text, "
                    " english_text, spoken_at, extracted) "
                    "VALUES (:mid, :line_id, :speaker, :language, :original_text, "
                    " :english_text, :spoken_at, :extracted)"
                ),
                {
                    "mid": meeting_id,
                    "line_id": line.id,
                    "speaker": line.speaker,
                    "language": line.language,
                    "original_text": line.original_text,
                    "english_text": line.english_text,
                    "spoken_at": line.spoken_at,
                    "extracted": 1 if line.extracted else 0,
                },
            )
            conn.execute(
                text("UPDATE meetings SET next_line_id = :next WHERE meeting_id = :mid"),
                {"next": line.id + 1, "mid": meeting_id},
            )

    def update_translation(self, meeting_id: str, line_id: int, english_text: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE transcript_lines SET english_text = :en "
                    "WHERE meeting_id = :mid AND line_id = :lid"
                ),
                {"en": english_text, "mid": meeting_id, "lid": line_id},
            )

    def mark_lines_extracted(self, meeting_id: str, line_ids: list[int]) -> None:
        """Sets extracted=1 for the given ids; anything not listed is left
        alone (the property the requirement extractor relies on)."""
        if not line_ids:
            return
        # Chunked so the IN-list stays well under SQLite's variable limit on the
        # test path; Postgres' limit is far higher, so this is just a safe cap.
        stmt = text(
            "UPDATE transcript_lines SET extracted = 1 "
            "WHERE meeting_id = :mid AND line_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        for chunk_start in range(0, len(line_ids), 500):
            chunk = line_ids[chunk_start:chunk_start + 500]
            with self._engine.begin() as conn:
                conn.execute(stmt, {"mid": meeting_id, "ids": chunk})

    def insert_requirement(self, meeting_id: str, req: "Requirement") -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO requirements "
                    "(meeting_id, requirement_id, title, category, priority, confidence, status) "
                    "VALUES (:mid, :rid, :title, :category, :priority, :confidence, :status)"
                ),
                {
                    "mid": meeting_id,
                    "rid": req.id,
                    "title": req.title,
                    "category": req.category,
                    "priority": req.priority,
                    "confidence": req.confidence,
                    "status": req.status,
                },
            )
            conn.execute(
                text("UPDATE meetings SET next_req_id = :next WHERE meeting_id = :mid"),
                {"next": req.id + 1, "mid": meeting_id},
            )

    def update_requirement_status(self, meeting_id: str, requirement_id: int, status_value: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE requirements SET status = :status "
                    "WHERE meeting_id = :mid AND requirement_id = :rid"
                ),
                {"status": status_value, "mid": meeting_id, "rid": requirement_id},
            )

    def update_requirement_title(self, meeting_id: str, requirement_id: int, title: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE requirements SET title = :title "
                    "WHERE meeting_id = :mid AND requirement_id = :rid"
                ),
                {"title": title, "mid": meeting_id, "rid": requirement_id},
            )

    def replace_agent_outputs(self, meeting_id: str, outputs: dict[str, str]) -> None:
        """Replaces the full set of agent outputs atomically (one DELETE + bulk
        INSERT in a transaction), matching the in-memory overwrite semantics."""
        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM agent_outputs WHERE meeting_id = :mid"),
                {"mid": meeting_id},
            )
            if outputs:
                conn.execute(
                    text(
                        "INSERT INTO agent_outputs (meeting_id, agent_id, output) "
                        "VALUES (:mid, :agent_id, :output)"
                    ),
                    [
                        {"mid": meeting_id, "agent_id": agent_id, "output": output}
                        for agent_id, output in outputs.items()
                    ],
                )

    def delete_meeting(self, meeting_id: str) -> bool:
        """Removes the meeting and all dependent rows in one transaction.
        Returns True if the meeting row existed."""
        with self._engine.begin() as conn:
            for table in ("transcript_lines", "requirements", "agent_outputs"):
                conn.execute(
                    text(f"DELETE FROM {table} WHERE meeting_id = :mid"),
                    {"mid": meeting_id},
                )
            result = conn.execute(
                text("DELETE FROM meetings WHERE meeting_id = :mid"),
                {"mid": meeting_id},
            )
            return result.rowcount > 0


# Module-level singleton, mirroring store.py. `init_pg_store()` is called once
# from main.py's startup event when meeting_store_backend == "postgres".
_pg_store: PostgresSessionStore | None = None


def build_meeting_engine(database_url: str) -> Engine:
    """Builds the synchronous meeting-store engine from the (async) auth URL,
    with the pre-ping + recycle settings Neon needs to survive idle drops."""
    sync_url = to_sync_pg_url(database_url)
    return create_engine(
        sync_url,
        pool_pre_ping=True,   # Neon drops idle connections; verify before use
        pool_recycle=280,     # recycle before Neon's ~5-min idle timeout
        pool_size=5,
        max_overflow=5,
        future=True,
    )


def init_pg_store(database_url: str) -> PostgresSessionStore:
    """
    Idempotent startup hook. Builds the engine (once), creates the schema, and
    returns the process-wide Postgres store. Tests do NOT call this — they
    construct PostgresSessionStore directly with their own engine.
    """
    global _pg_store
    if _pg_store is not None:
        return _pg_store
    engine = build_meeting_engine(database_url)
    _pg_store = PostgresSessionStore(engine)
    # Never log the URL — it carries the DB password.
    logger.info("meeting store ready on postgres (%s)", urlsplit(database_url).hostname or "unknown host")
    return _pg_store
