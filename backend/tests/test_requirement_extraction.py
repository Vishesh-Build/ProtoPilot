"""
Requirement-extraction concurrency: the bug this pins down is silent
requirement loss.

Every finished utterance fires extraction. The old code marked the whole
transcript as processed *after* the LLM call returned, so anything spoken
while that call was in flight was marked "done" without ever being read —
the client's requirement vanished with nothing in the logs.

These tests drive the REAL extractor. Only the LLM router is faked, because
it is the one piece that would hit the network.

Run from the backend/ directory:
    python -m unittest discover -s tests -t . -v
"""

import asyncio
import json
import logging
import sys
import types
import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

# Several tests exercise the failure paths on purpose, which log warnings.
# Keep the test output about the assertions, not the expected noise.
logging.getLogger("protopilot.requirements").setLevel(logging.CRITICAL)


# --- Fake the LLM router before importing the extractor -----------------
# app.llm.router imports httpx and reads provider config; none of that is
# needed to test the concurrency rules, and it must never make a real call.
class _FakeResult:
    def __init__(self, text):
        self.text = text


class _FakeRouter:
    def __init__(self):
        self.calls = []
        self.reply = "[]"
        self.delay = 0.0
        self.raise_exc = None
        # Kept so a test can assert which token budget the extractor asked
        # for: too small a budget is how a reasoning model returns nothing.
        self.last_kwargs: dict = {}

    async def chat(self, messages, **kwargs):
        self.calls.append(messages)
        self.last_kwargs = kwargs
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.raise_exc:
            raise self.raise_exc
        return _FakeResult(self.reply)


fake_router = _FakeRouter()
_stub = types.ModuleType("app.llm.router")
_stub.llm_router = fake_router
sys.modules["app.llm.router"] = _stub

from app.meetings.session import MeetingSession  # noqa: E402
from app.requirements import extractor  # noqa: E402


class ExtractionTestCase(unittest.IsolatedAsyncioTestCase):
    """Shared reset so one test's fake replies can't leak into another."""

    meeting_id = "m-extract"

    def setUp(self):
        fake_router.calls.clear()
        fake_router.reply = "[]"
        fake_router.delay = 0.0
        fake_router.raise_exc = None
        fake_router.last_kwargs = {}
        extractor._locks.clear()
        self.session = MeetingSession(meeting_id=self.meeting_id)

    def pending_ids(self):
        return [line.id for line in self.session.pending_extraction_lines()]


class BasicExtractionTest(ExtractionTestCase):
    async def test_returns_parsed_requirements_and_marks_lines_read(self):
        fake_router.reply = json.dumps(
            [{"title": "OTP login", "category": "Auth", "priority": "High", "confidence": 90}]
        )
        self.session.add_transcript_line("Client", "hi", "login OTP se hona chahiye")

        found = await extractor.extract_new_requirements(self.session)

        self.assertEqual([r["title"] for r in found], ["OTP login"])
        self.assertEqual(self.pending_ids(), [], "lines that were read should not be re-sent")

    async def test_no_pending_lines_means_no_llm_call(self):
        self.assertEqual(await extractor.extract_new_requirements(self.session), [])
        self.assertEqual(fake_router.calls, [], "must not spend a call on an empty transcript")

    async def test_prompt_uses_translation_when_available_original_otherwise(self):
        translated = self.session.add_transcript_line("A", "gu", "મને લોગિન જોઈએ")
        self.session.set_translation(translated.id, "I need a login")
        self.session.add_transcript_line("B", "hi", "payment bhi chahiye")

        await extractor.extract_new_requirements(self.session)

        prompt = fake_router.calls[0][1]["content"]
        self.assertIn("I need a login", prompt)
        self.assertNotIn("મને લોગિન જોઈએ", prompt, "translated line should go as English")
        self.assertIn("payment bhi chahiye", prompt, "untranslated line still goes as-is")

    async def test_malformed_items_are_skipped_not_crashed_on(self):
        fake_router.reply = json.dumps(["just a string", {"no_title": 1}, {"title": "Real one"}])
        self.session.add_transcript_line("A", "en", "we need a dashboard")

        found = await extractor.extract_new_requirements(self.session)
        self.assertEqual([r["title"] for r in found], ["Real one"])

    async def test_fenced_json_is_still_parsed(self):
        fake_router.reply = '```json\n[{"title": "Fenced reply"}]\n```'
        self.session.add_transcript_line("A", "en", "add a report screen")

        found = await extractor.extract_new_requirements(self.session)
        self.assertEqual([r["title"] for r in found], ["Fenced reply"])


class MidFlightLineTest(ExtractionTestCase):
    """The regression that motivated the per-line flag."""

    async def test_line_spoken_during_the_llm_call_stays_pending(self):
        fake_router.delay = 0.05
        self.session.add_transcript_line("Client", "hi", "pehli baat")

        task = asyncio.create_task(extractor.extract_new_requirements(self.session))
        await asyncio.sleep(0.01)  # extraction is now waiting on the model
        late = self.session.add_transcript_line("Client", "hi", "aur ek zaroori baat")
        await task

        # Old behaviour: this list came back empty and "aur ek zaroori baat"
        # was never shown to the model by any round.
        self.assertEqual(self.pending_ids(), [late.id])

    async def test_the_mid_flight_line_is_picked_up_by_the_next_round(self):
        fake_router.delay = 0.05
        self.session.add_transcript_line("Client", "hi", "pehli baat")

        task = asyncio.create_task(extractor.extract_new_requirements(self.session))
        await asyncio.sleep(0.01)
        self.session.add_transcript_line("Client", "hi", "aur ek zaroori baat")
        await task

        fake_router.delay = 0.0
        await extractor.extract_new_requirements(self.session)

        second_prompt = fake_router.calls[1][1]["content"]
        self.assertIn("aur ek zaroori baat", second_prompt)
        self.assertEqual(self.pending_ids(), [])


class ConcurrentCallTest(ExtractionTestCase):
    async def test_overlapping_calls_do_not_pay_twice_for_the_same_lines(self):
        # Every finished utterance fires extraction, so overlap is the norm.
        fake_router.delay = 0.05
        self.session.add_transcript_line("A", "en", "we need a login screen")

        results = await asyncio.gather(
            extractor.extract_new_requirements(self.session),
            extractor.extract_new_requirements(self.session),
        )

        self.assertEqual(len(fake_router.calls), 1, "the second caller should find nothing pending")
        self.assertEqual(results[1], [])

    async def test_two_meetings_are_not_serialised_against_each_other(self):
        other = MeetingSession(meeting_id="m-other")
        self.session.add_transcript_line("A", "en", "meeting one line")
        other.add_transcript_line("B", "en", "meeting two line")

        await asyncio.gather(
            extractor.extract_new_requirements(self.session),
            extractor.extract_new_requirements(other),
        )
        self.assertEqual(len(fake_router.calls), 2, "per-meeting locks, not one global lock")


class FailureHandlingTest(ExtractionTestCase):
    async def test_provider_failure_leaves_lines_pending_for_a_retry(self):
        fake_router.raise_exc = RuntimeError("all providers failed")
        line = self.session.add_transcript_line("A", "en", "we need an admin panel")

        self.assertEqual(await extractor.extract_new_requirements(self.session), [])
        self.assertEqual(self.pending_ids(), [line.id], "a provider hiccup must not cost a requirement")

    async def test_unparseable_reply_leaves_lines_pending(self):
        fake_router.reply = "Sure! Here are the requirements you asked for."
        line = self.session.add_transcript_line("A", "en", "we need an admin panel")

        self.assertEqual(await extractor.extract_new_requirements(self.session), [])
        self.assertEqual(self.pending_ids(), [line.id])

    async def test_json_object_instead_of_array_leaves_lines_pending(self):
        fake_router.reply = '{"title": "not in an array"}'
        line = self.session.add_transcript_line("A", "en", "we need an admin panel")

        self.assertEqual(await extractor.extract_new_requirements(self.session), [])
        self.assertEqual(self.pending_ids(), [line.id])

    async def test_a_failed_round_is_retried_successfully_later(self):
        fake_router.raise_exc = RuntimeError("provider down")
        self.session.add_transcript_line("A", "en", "we need an admin panel")
        await extractor.extract_new_requirements(self.session)

        fake_router.raise_exc = None
        fake_router.reply = json.dumps([{"title": "Admin panel"}])
        found = await extractor.extract_new_requirements(self.session)

        self.assertEqual([r["title"] for r in found], ["Admin panel"])
        self.assertEqual(self.pending_ids(), [])


class ReplyWrappingTest(ExtractionTestCase):
    """
    The prompt says "reply with a JSON array and nothing else"; models add
    fences and pleasantries anyway. Every wrapping that still contains the
    array must survive, because the alternative is a client watching an
    empty Points panel while a perfectly good answer is thrown away.
    """

    ARRAY = '[{"title": "Admin panel", "category": "General", "priority": "Low", "confidence": 70}]'

    async def _extract(self, reply):
        fake_router.reply = reply
        line = self.session.add_transcript_line("A", "en", "we need an admin panel")
        return await extractor.extract_new_requirements(self.session), line

    async def test_json_fences(self):
        found, _ = await self._extract("```json\n" + self.ARRAY + "\n```")
        self.assertEqual([r["title"] for r in found], ["Admin panel"])
        self.assertEqual(self.pending_ids(), [])

    async def test_a_preamble_and_a_closing_sentence(self):
        found, _ = await self._extract(
            "Sure! Here are the requirements I found:\n" + self.ARRAY + "\nLet me know if you "
            "want more detail."
        )
        self.assertEqual([r["title"] for r in found], ["Admin panel"])
        self.assertEqual(self.pending_ids(), [], "a chatty model must not cost a round")

    async def test_a_fenced_array_with_a_preamble(self):
        found, _ = await self._extract("Here you go:\n```json\n" + self.ARRAY + "\n```")
        self.assertEqual([r["title"] for r in found], ["Admin panel"])

    async def test_a_truncated_array_stays_pending(self):
        # finish_reason=length mid-array: there is a "[" but no closing "]".
        found, line = await self._extract('[{"title": "Admin pan')
        self.assertEqual(found, [])
        self.assertEqual(self.pending_ids(), [line.id])

    async def test_no_text_at_all_stays_pending(self):
        found, line = await self._extract(None)
        self.assertEqual(found, [])
        self.assertEqual(self.pending_ids(), [line.id])

    async def test_the_extractor_asks_for_the_configured_budget(self):
        # 800 was hardcoded here, below the agents' own 1600, on the one call
        # the Points panel depends on.
        from app.config import settings

        await self._extract(self.ARRAY)
        self.assertEqual(fake_router.last_kwargs.get("max_tokens"),
                         settings.llm_default_max_tokens)
        self.assertGreaterEqual(settings.llm_default_max_tokens, 1600)


class BacklogCapTest(ExtractionTestCase):
    async def test_backlog_is_bounded_when_the_provider_stays_down(self):
        fake_router.raise_exc = RuntimeError("provider down")
        cap = extractor._MAX_PENDING_LINES

        for i in range(cap + 25):
            self.session.add_transcript_line("A", "en", f"line {i}")
            await extractor.extract_new_requirements(self.session)

        pending = self.session.pending_extraction_lines()
        self.assertEqual(len(pending), cap, "an unbounded backlog would grow the prompt forever")
        # The oldest are the ones dropped, so the newest context survives.
        self.assertEqual(pending[-1].original_text, f"line {cap + 24}")
        self.assertEqual(len(self.session.transcript), cap + 25, "dropped from the backlog, not the transcript")


class LockCleanupTest(ExtractionTestCase):
    async def test_clear_extraction_state_removes_the_meetings_lock(self):
        self.session.add_transcript_line("A", "en", "hello")
        await extractor.extract_new_requirements(self.session)
        self.assertIn(self.meeting_id, extractor._locks)

        extractor.clear_extraction_state(self.meeting_id)
        self.assertNotIn(self.meeting_id, extractor._locks)

    def test_clearing_an_unknown_meeting_is_harmless(self):
        extractor.clear_extraction_state("never-existed")


if __name__ == "__main__":
    unittest.main()
