"""
In-memory state for a single meeting session.

This is intentionally simple (a dict in process memory, not a database) —
ProtoPilot has one user, one meeting at a time, running on their own
machine. If/when multi-session persistence matters, this is the module
to swap for a real SQLite-backed store (the schema already exists per
Phase 0's ARCHITECTURE.md).
"""

import datetime
import difflib
import itertools
import re
import threading
from dataclasses import dataclass, field


@dataclass
class TranscriptLine:
    """
    One utterance. `id` exists so the line can be shown immediately and
    patched later: translation is a network call, and a caption must never
    wait on the network to appear on screen.
    """

    id: int
    speaker: str
    language: str
    original_text: str
    # None means "translation still in flight". Readers should use
    # display_text(), which falls back to the original.
    english_text: str | None = None
    # When the audio finished, captured before transcription starts.
    # Utterances are transcribed concurrently and therefore finish out of
    # order, so this — not arrival order — is the real chronology.
    spoken_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    # Set only on the lines actually handed to the requirement extractor.
    # A per-line flag rather than a shared index is what makes overlapping
    # extractions safe (see requirements/extractor.py).
    extracted: bool = False

    def display_text(self) -> str:
        return self.english_text or self.original_text

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "speaker": self.speaker,
            "language": self.language,
            "original_text": self.original_text,
            "english_text": self.english_text,
            "spoken_at": self.spoken_at,
        }


@dataclass
class Requirement:
    id: int
    title: str
    category: str
    priority: str  # "High" | "Medium" | "Low"
    confidence: int  # 0-100
    status: str = "pending"  # "pending" | "approved" | "rejected"


@dataclass
class MeetingSession:
    meeting_id: str
    name: str = "Untitled Meeting"
    # The user who created this meeting. Only this user can accept/reject
    # requirements, trigger prototype generation, export, or end/delete the
    # meeting — every participant can join and speak, but management stays
    # with whoever started it.
    host_user_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    ended_at: str | None = None
    status: str = "active"  # "active" | "ended"

    transcript: list[TranscriptLine] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    # Filled in after the agent pipeline runs — agent_id -> its output text.
    agent_outputs: dict = field(default_factory=dict)

    _id_counter: "itertools.count" = field(default_factory=lambda: itertools.count(1))
    _line_counter: "itertools.count" = field(default_factory=lambda: itertools.count(1))

    # Set by SessionRegistry when the session is hydrated from / created into
    # the SQLite store. None means "in-memory only" (direct constructor use —
    # the path the existing unit tests take), in which case every mutator
    # below behaves exactly as it did before persistence existed.
    _store: object | None = field(default=None, repr=False, compare=False)

    def _persist_line(self, line: TranscriptLine) -> None:
        if self._store is not None:
            self._store.insert_transcript_line(self.meeting_id, line)

    def _persist_requirement(self, req: Requirement) -> None:
        if self._store is not None:
            self._store.insert_requirement(self.meeting_id, req)

    def add_transcript_line(
        self,
        speaker: str,
        language: str,
        original_text: str,
        english_text: str | None = None,
        spoken_at: str | None = None,
    ) -> TranscriptLine:
        """
        Adds a line and returns it, so the caller can broadcast it now and
        patch in the translation later via set_translation(line.id, ...).

        Inserted at its chronological position rather than appended: two
        participants' utterances are transcribed concurrently, so a longer
        one can finish after a shorter one that was spoken later.
        """
        line = TranscriptLine(
            id=next(self._line_counter),
            speaker=speaker,
            language=language,
            original_text=original_text,
            english_text=english_text,
            **({"spoken_at": spoken_at} if spoken_at else {}),
        )
        index = len(self.transcript)
        while index > 0 and self.transcript[index - 1].spoken_at > line.spoken_at:
            index -= 1
        self.transcript.insert(index, line)
        self._persist_line(line)
        return line

    def set_translation(self, line_id: int, english_text: str) -> TranscriptLine | None:
        """Fills in a translation that arrived after the line was shown."""
        for line in self.transcript:
            if line.id == line_id:
                line.english_text = english_text
                if self._store is not None:
                    self._store.update_translation(self.meeting_id, line_id, english_text)
                return line
        return None

    def pending_extraction_lines(self) -> list[TranscriptLine]:
        """Lines never handed to the requirement extractor."""
        return [line for line in self.transcript if not line.extracted]

    def mark_extracted(self, line_ids: list[int] | set[int]):
        """
        Marks exactly the lines that were sent to the extractor. Anything
        that arrived mid-call stays pending and is picked up next round —
        this is why requirements can't be silently dropped.
        """
        wanted = set(line_ids)
        touched = []
        for line in self.transcript:
            if line.id in wanted:
                line.extracted = True
                touched.append(line.id)
        if self._store is not None and touched:
            self._store.mark_lines_extracted(self.meeting_id, touched)

    def add_requirements(self, new_reqs: list[dict]) -> list[Requirement]:
        """
        Adds new requirements, skipping anything that's a near-duplicate of
        a title already captured. The extractor is told the existing titles
        and asked not to repeat them, but small rewordings ("Buy order panel
        on the right" vs "Buy/sell order panel on the right") slip through —
        this is a second, code-level safety net on top of that prompt.
        """
        added = []
        for r in new_reqs:
            if self._is_duplicate_title(r["title"]):
                continue
            req = Requirement(
                id=next(self._id_counter),
                title=r["title"],
                category=r.get("category", "General"),
                priority=r.get("priority", "Medium"),
                confidence=int(r.get("confidence", 70)),
            )
            self.requirements.append(req)
            self._persist_requirement(req)
            added.append(req)
        return added

    def _is_duplicate_title(self, title: str, threshold: float = 0.82) -> bool:
        normalized = re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()
        for existing in self.requirements:
            existing_normalized = re.sub(r"[^a-z0-9 ]", "", existing.title.lower()).strip()
            if normalized == existing_normalized:
                return True
            if difflib.SequenceMatcher(None, normalized, existing_normalized).ratio() >= threshold:
                return True
        return False

    def existing_titles(self) -> list[str]:
        return [r.title for r in self.requirements]

    def readiness_percent(self) -> int:
        if not self.requirements:
            return 0
        approved = sum(1 for r in self.requirements if r.status == "approved")
        return round((approved / len(self.requirements)) * 100)

    def languages_used(self) -> list[str]:
        seen = []
        for line in self.transcript:
            if line.language not in seen:
                seen.append(line.language)
        return seen

    def replace_agent_outputs(self, outputs: dict) -> None:
        """
        Sets the full agent_outputs dict — the pipeline overwrites the whole
        set atomically after a run, rather than merging into it. Routes
        through here (rather than assigning session.agent_outputs = ...)
        so a store-backed session persists the replacement; direct dict
        assignment still works in-memory for tests that build a session by
        hand.
        """
        self.agent_outputs = dict(outputs)
        if self._store is not None:
            self._store.replace_agent_outputs(self.meeting_id, self.agent_outputs)

    def update_requirement_status(self, requirement_id: int, status_value: str) -> "Requirement | None":
        """Accept/reject a requirement (host-only at the API layer). Returns
        the updated Requirement, or None if the id doesn't exist."""
        for r in self.requirements:
            if r.id == requirement_id:
                r.status = status_value
                if self._store is not None:
                    self._store.update_requirement_status(self.meeting_id, requirement_id, status_value)
                return r
        return None

    def update_requirement_title(self, requirement_id: int, title: str) -> "Requirement | None":
        """Edit a requirement's title (host-only at the API layer)."""
        for r in self.requirements:
            if r.id == requirement_id:
                r.title = title
                if self._store is not None:
                    self._store.update_requirement_title(self.meeting_id, requirement_id, title)
                return r
        return None

    def rename(self, new_name: str) -> None:
        """Rename the meeting (host-only at the API layer). Persists through
        the same store hook get_or_create already uses to backfill a name."""
        self.name = new_name
        if self._store is not None:
            self._store.update_meeting_name(self.meeting_id, new_name)

    def mark_ended(self):
        self.status = "ended"
        self.ended_at = datetime.datetime.utcnow().isoformat() + "Z"
        if self._store is not None:
            self._store.update_meeting_ended(self.meeting_id, self.status, self.ended_at)

    def is_host(self, user_id: str | None) -> bool:
        return user_id is not None and self.host_user_id == user_id

    def summary(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "name": self.name,
            "host_user_id": self.host_user_id,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "languages": self.languages_used(),
            "transcript_lines": len(self.transcript),
            "requirement_count": len(self.requirements),
            "readiness_percent": self.readiness_percent(),
            # Only the prototype agent produces a prototype. Checking the
            # whole dict counted a PM-only run as "prototype ready".
            "has_prototype": bool(self.agent_outputs.get("prototype")),
        }


class SessionRegistry:
    """
    Resolves a `MeetingSession` by id, lazily hydrating it from a
    `SessionStore` the first time it's asked for. The in-process dict is
    purely a hot-path cache: every mutation goes to the store, and a
    process restart just re-populates from SQLite on demand.

    Backwards-compat: when no store is configured, the registry behaves
    exactly as it did before persistence was added — an in-memory dict,
    lost on restart. This is the path the existing transcript-lines and
    requirement-extraction tests exercise, because they construct
    `MeetingSession` directly without ever calling `init_store()`. The
    in-memory path is preserved so those tests keep running against the
    pure dataclass API.
    """

    def __init__(self, store: "object | None" = None):
        # Using "object | None" + duck typing so this module doesn't have
        # to import app.meetings.store at top level (the store imports
        # MeetingSession from this module — a cycle).
        self._store = store
        self._sessions: dict[str, MeetingSession] = {}
        self._lock = threading.Lock()

    def set_store(self, store) -> None:
        """Late-bind the SQLite store. Called once at startup from
        main.py. After this is set, the registry stops using the
        in-memory-only path."""
        with self._lock:
            self._store = store
            # Drop the cache so the next read re-hydrates from the store —
            # any objects still in the cache were loaded from a no-store
            # world and may not match what's in the DB.
            self._sessions.clear()

    def _has_store(self) -> bool:
        return self._store is not None

    def _hydrate(self, meeting_id: str) -> MeetingSession | None:
        """Pull a session from the store and cache it. Returns None if no
        such meeting exists in the store."""
        assert self._store is not None
        loaded = self._store.load_meeting(meeting_id)
        if loaded is not None:
            loaded._store = self._store  # write-through from here on
            self._sessions[meeting_id] = loaded
        return loaded

    def get_or_create(self, meeting_id: str, name: str | None = None, host_user_id: str | None = None) -> MeetingSession:
        # The store path is the source of truth — first consult the cache,
        # then the store, then create-and-persist.
        with self._lock:
            if not self._has_store():
                # In-memory fallback for tests / unconfigured environments.
                return self._get_or_create_in_memory(meeting_id, name, host_user_id)

            session = self._sessions.get(meeting_id)
            if session is None:
                loaded = self._hydrate(meeting_id)
                if loaded is not None:
                    session = loaded
                else:
                    session = MeetingSession(
                        meeting_id=meeting_id,
                        name=name or "Untitled Meeting",
                        host_user_id=host_user_id,
                    )
                    session._store = self._store
                    self._store.insert_meeting(session)
                    self._sessions[meeting_id] = session
                    return session

            # Existing session: apply the same get_or_create semantics that
            # the in-memory version enforced, and persist the backfill.
            if name and session.name != name:
                session.name = name
                self._store.update_meeting_name(meeting_id, name)
            if session.host_user_id is None and host_user_id is not None:
                # Backfills the host if the session was somehow created
                # before a host was known — does NOT override an existing host.
                session.host_user_id = host_user_id
                self._store.update_meeting_host(meeting_id, host_user_id)
            return session

    def _get_or_create_in_memory(self, meeting_id: str, name: str | None, host_user_id: str | None) -> MeetingSession:
        """The pre-persistence behaviour, kept verbatim so the existing
        transcript-lines and requirement-extraction tests continue to work
        without a store."""
        if meeting_id not in self._sessions:
            self._sessions[meeting_id] = MeetingSession(
                meeting_id=meeting_id,
                name=name or "Untitled Meeting",
                host_user_id=host_user_id,
            )
        else:
            session = self._sessions[meeting_id]
            if name:
                session.name = name
            if session.host_user_id is None and host_user_id is not None:
                session.host_user_id = host_user_id
        return self._sessions[meeting_id]

    def get(self, meeting_id: str) -> MeetingSession | None:
        with self._lock:
            session = self._sessions.get(meeting_id)
            if session is not None:
                return session
            if not self._has_store():
                return None
            return self._hydrate(meeting_id)

    def list_all(self) -> list[MeetingSession]:
        if not self._has_store():
            # Pre-persistence behaviour: most recent first.
            return sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)

        with self._lock:
            # Drop the in-process cache for any id that no longer exists
            # in the store (e.g. deleted in another process, or via a
            # direct SQL DELETE during dev).
            live_ids = set(self._store.list_meeting_ids())
            stale = [mid for mid in self._sessions if mid not in live_ids]
            for mid in stale:
                self._sessions.pop(mid, None)

            # Hydrate anything in the store that isn't cached.
            for mid in live_ids:
                if mid not in self._sessions:
                    self._hydrate(mid)

            return sorted(
                (self._sessions[mid] for mid in live_ids),
                key=lambda s: s.created_at,
                reverse=True,
            )

    def delete(self, meeting_id: str) -> bool:
        with self._lock:
            if not self._has_store():
                if meeting_id in self._sessions:
                    del self._sessions[meeting_id]
                    return True
                return False
            # Drop from the cache first so a concurrent reader between
            # the store delete and the next get_or_create doesn't see a
            # stale MeetingSession pointing at rows that are gone.
            self._sessions.pop(meeting_id, None)
            return self._store.delete_meeting(meeting_id)


# Single shared registry for the process.
session_registry = SessionRegistry()