"""
Turns new transcript lines into structured requirements.

Token-efficiency note: this only sends the transcript lines added since
the last extraction (not the whole meeting so far), plus the titles of
requirements already found (so the model doesn't repeat them). This is
the same "minimize tokens, maximize quality" principle the LLM router
was built around.
"""

import json
import logging

from app.llm.router import llm_router
from app.meetings.session import MeetingSession, TranscriptLine

logger = logging.getLogger("protopilot.requirements")

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
    transcript_block = "\n".join(f"{line.speaker}: {line.english_text}" for line in new_lines)
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
    Looks at transcript lines added since the last extraction and returns
    any new requirements found (as plain dicts, not yet added to the session —
    the caller decides whether/how to store them).
    """
    new_lines = session.new_transcript_since_last_extraction()
    if not new_lines:
        return []

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
        logger.warning("requirement extraction failed for meeting %s: %s", session.meeting_id, e)
        return []
    finally:
        # Mark as processed regardless of success — a failed extraction
        # shouldn't be silently retried forever on the same lines, since
        # the next batch of new lines will still get looked at normally.
        session.mark_extracted_up_to_current()

    # Basic shape validation — skip anything malformed rather than crash.
    valid = [item for item in items if isinstance(item, dict) and "title" in item]
    return valid