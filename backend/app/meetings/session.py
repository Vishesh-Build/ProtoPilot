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
    speaker: str
    language: str
    original_text: str
    english_text: str


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
    # Index into `transcript` marking what's already been sent to the
    # requirement extractor — so re-extraction only looks at new lines.
    last_extracted_index: int = 0
    # Filled in after the agent pipeline runs — agent_id -> its output text.
    agent_outputs: dict = field(default_factory=dict)

    _id_counter: "itertools.count" = field(default_factory=lambda: itertools.count(1))

    def add_transcript_line(self, speaker: str, language: str, original_text: str, english_text: str):
        self.transcript.append(TranscriptLine(speaker, language, original_text, english_text))

    def new_transcript_since_last_extraction(self) -> list[TranscriptLine]:
        return self.transcript[self.last_extracted_index:]

    def mark_extracted_up_to_current(self):
        self.last_extracted_index = len(self.transcript)

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

    def mark_ended(self):
        self.status = "ended"
        self.ended_at = datetime.datetime.utcnow().isoformat() + "Z"

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
            "has_prototype": bool(self.agent_outputs),
        }


class SessionRegistry:
    """Thread-safe registry so concurrent WebSocket connections don't race."""

    def __init__(self):
        self._sessions: dict[str, MeetingSession] = {}
        self._lock = threading.Lock()

    def get_or_create(self, meeting_id: str, name: str | None = None, host_user_id: str | None = None) -> MeetingSession:
        with self._lock:
            if meeting_id not in self._sessions:
                self._sessions[meeting_id] = MeetingSession(
                    meeting_id=meeting_id,
                    name=name or "Untitled Meeting",
                    host_user_id=host_user_id,
                )
            else:
                session = self._sessions[meeting_id]
                if name:
                    # If a name arrives later (e.g. Create Meeting form) and the
                    # session already exists, update it rather than ignore it.
                    session.name = name
                if session.host_user_id is None and host_user_id is not None:
                    # Backfills the host if the session was somehow created
                    # before a host was known — does NOT override an existing host.
                    session.host_user_id = host_user_id
            return self._sessions[meeting_id]

    def get(self, meeting_id: str) -> MeetingSession | None:
        return self._sessions.get(meeting_id)

    def list_all(self) -> list[MeetingSession]:
        # Most recent first.
        return sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)

    def delete(self, meeting_id: str) -> bool:
        with self._lock:
            if meeting_id in self._sessions:
                del self._sessions[meeting_id]
                return True
            return False


# Single shared registry for the process.
session_registry = SessionRegistry()