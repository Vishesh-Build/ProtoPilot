"""
Turns new transcript lines into structured requirements.

Token-efficiency note: this only sends the transcript lines added since
the last extraction (not the whole meeting so far), plus the titles of
requirements already found (so the model doesn't repeat them). This is
the same "minimize tokens, maximize quality" principle the LLM router
was built around.
"""

import asyncio
import json
import logging

from app.llm.router import llm_router
from app.meetings.session import MeetingSession, TranscriptLine

logger = logging.getLogger("protopilot.requirements")

# One extraction at a time per meeting. Keyed by meeting_id rather than held
# on MeetingSession, so the session stays a plain dataclass with no asyncio
# objects in it (it's also read from sync code).
_locks: dict[str, asyncio.Lock] = {}

# Upper bound on the retry backlog if the LLM provider stays unavailable.
_MAX_PENDING_LINES = 80

SYSTEM_PROMPT = """You extract software requirements from a client meeting transcript.

You will be given:
1. A list of requirement titles already captured (do NOT repeat these or anything that means the same thing).
2. New lines of transcript since the last check.

Return ONLY a JSON array (no markdown fences, no commentary) of NEW, DISTINCT
requirements implied by the new lines. If there are none, return an empty array: []

Each item must have exactly these keys:
  "title": short, specific, actionable (e.g. "OTP-based mobile login")
  "category": one or two words (e.g. "Authentication", "Payments", "Admin")
  "priority": "High", "Medium", or "Low"
  "confidence": integer 0-100, how confident you are this is a real, distinct requirement

Do not invent requirements that aren't reasonably implied by the text. Casual
remarks, greetings, and clarifying questions are not requirements."""


def _build_user_prompt(existing_titles: list[str], new_lines: list[TranscriptLine]) -> str:
    existing_block = "\n".join(f"- {t}" for t in existing_titles) or "(none yet)"
    # display_text() falls back to the original when the translation hasn't
    # landed yet, so a line is never sent to the model as an empty string.
    transcript_block = "\n".join(f"{line.speaker}: {line.display_text()}" for line in new_lines)
    return (
        f"Already captured requirements:\n{existing_block}\n\n"
        f"New transcript lines:\n{transcript_block}"
    )


def _parse_json_array(raw: str) -> list[dict]:
    """Models sometimes wrap JSON in ```json fences despite instructions — strip if present."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise ValueError("expected a JSON array")
    return parsed


async def extract_new_requirements(session: MeetingSession) -> list[dict]:
    """
    Looks at transcript lines not yet extracted and returns any new
    requirements found (as plain dicts, not yet added to the session —
    the caller decides whether/how to store them).

    Two correctness rules live here, both learned from losing requirements:

    1. One extraction per meeting at a time. Every finished utterance fires
       this concurrently, so without the lock two calls would read the same
       lines and pay twice for the same answer.
    2. Only the lines actually sent to the model get marked. Lines that
       arrive while the LLM call is in flight stay pending and are picked up
       next round, instead of being marked processed without ever being read.
    """
    lock = _locks.setdefault(session.meeting_id, asyncio.Lock())
    async with lock:
        # Re-read after acquiring: a call that ran while we waited may have
        # already covered these lines, in which case there's nothing to do.
        new_lines = session.pending_extraction_lines()
        if not new_lines:
            return []

        # Snapshot the exact ids we're about to send. Anything appended
        # during the await below is deliberately not in this set.
        sent_ids = [line.id for line in new_lines]

        try:
            result = await llm_router.chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(session.existing_titles(), new_lines)},
                ],
                max_tokens=800,
                temperature=0.2,
            )
            items = _parse_json_array(result.text)
        except (RuntimeError, json.JSONDecodeError, ValueError) as e:
            # Left pending on purpose: a provider hiccup shouldn't cost the
            # client a requirement. The next round retries these lines along
            # with the newer ones, which also gives the model more context.
            logger.warning(
                "requirement extraction failed for meeting %s (%d lines stay pending): %s",
                session.meeting_id, len(sent_ids), e,
            )
            _drop_oldest_beyond_cap(session)
            return []

        session.mark_extracted(sent_ids)

        # Basic shape validation — skip anything malformed rather than crash.
        return [item for item in items if isinstance(item, dict) and "title" in item]


def _drop_oldest_beyond_cap(session: MeetingSession):
    """
    Bounds the retry backlog. If a provider stays down, pending lines would
    otherwise grow without limit and the prompt with them.
    """
    pending = session.pending_extraction_lines()
    overflow = len(pending) - _MAX_PENDING_LINES
    if overflow > 0:
        stale = [line.id for line in pending[:overflow]]
        session.mark_extracted(stale)
        logger.warning(
            "meeting %s: dropping %d transcript lines from the extraction backlog (cap=%d)",
            session.meeting_id, overflow, _MAX_PENDING_LINES,
        )


def clear_extraction_state(meeting_id: str):
    """Called when a meeting is deleted so the lock dict doesn't grow forever."""
    _locks.pop(meeting_id, None)