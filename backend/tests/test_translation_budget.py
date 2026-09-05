"""
The token budget the per-caption translation call asks for.

From a real hackathon run. A Hindi caption went to translation and both
providers answered like this:

    groq failed: empty reply from model 'openai/gpt-oss-120b': model returned
      281 characters of reasoning and no answer (finish_reason=length)
    nim  failed: empty reply from model 'openai/gpt-oss-20b': model returned
      275 characters of reasoning and no answer (finish_reason=length)

The caller had sized max_tokens for the ANSWER — `min(300, words*3 + 40)`,
so about 61 tokens for a short line. Every model the router picks today is a
reasoning model, and those spend the SAME budget thinking before emitting a
visible character, so the answer never started. The damage did not stop at one
caption: both providers were marked failed and put in cooldown, so the
requirement extraction that ran next reported "All LLM providers failed" and
the Points panel stopped filling for the rest of the meeting.

The rule these tests hold: the request must always carry enough budget for
invisible reasoning plus the answer, and it must never shrink below the
project-wide default that the agents and the extractor already use.

Run from the backend/ directory:
    python -m unittest tests.test_translation_budget -v
"""

import logging
import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.config import settings  # noqa: E402
from app.llm.providers.base import ChatResult  # noqa: E402
from app.transcription import translate  # noqa: E402

logging.getLogger("protopilot.translate").setLevel(logging.CRITICAL)

HINDI = "Order ka daily report bhi dikhna chahiye."
GUJARATI = "Grahak ne order no status message thi janavvu joie."


class _RecordingRouter:
    """Captures the kwargs of each chat() call and returns a fixed answer."""

    def __init__(self, answer="the daily order report should be visible"):
        self.calls = []
        self.answer = answer

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return ChatResult(
            text=self.answer, model="m-1", provider="stub", input_tokens=1, output_tokens=1,
        )

    @property
    def last_max_tokens(self):
        return self.calls[-1]["max_tokens"]


class TranslationBudgetTest(unittest.IsolatedAsyncioTestCase):
    def _router(self, answer="translated"):
        router = _RecordingRouter(answer)
        patch = mock.patch.object(translate, "llm_router", router)
        patch.start()
        self.addCleanup(patch.stop)
        return router

    async def test_a_short_line_still_gets_room_to_think(self):
        # The exact shape of the failure: ~8 words. The old formula asked for
        # 64 tokens and the model spent 281 characters reasoning first.
        router = self._router()
        await translate.translate_to_english(HINDI, "hi")

        self.assertGreaterEqual(
            router.last_max_tokens, 512,
            "a reasoning model needs budget for the thinking AND the answer",
        )

    async def test_the_budget_never_drops_below_the_project_default(self):
        # The agents and the extractor run on llm_default_max_tokens (2048 after
        # the earlier empty-reply fix). Translation asking for less was how one
        # call path stayed broken while the others were fixed.
        router = self._router()
        for text, language in ((HINDI, "hi"), (GUJARATI, "gu"), ("Haan.", "hi")):
            router.calls.clear()
            await translate.translate_to_english(text, language)
            self.assertGreaterEqual(router.last_max_tokens, settings.llm_default_max_tokens)

    async def test_a_long_utterance_gets_more_than_the_floor(self):
        # An 8-second utterance can carry a lot of words, so the budget has to
        # grow with them and not sit at the floor. Short lines are all clamped
        # UP to llm_default_max_tokens, which is the point of the floor — so the
        # comparison that means anything is long-vs-floor, not long-vs-short.
        router = self._router()

        await translate.translate_to_english("shabd " * 8, "hi")
        self.assertEqual(router.last_max_tokens, settings.llm_default_max_tokens,
                         "a short line rides the floor")

        await translate.translate_to_english("shabd " * 600, "hi")
        self.assertGreater(router.last_max_tokens, settings.llm_default_max_tokens,
                           "a long line must not be truncated mid-translation")

    async def test_english_never_reaches_the_provider(self):
        # Most captions in this demo are English. Spending a round trip (and a
        # rate-limit slot) to translate English into English is what leaves no
        # headroom for the lines that actually need it.
        router = self._router()

        result = await translate.translate_to_english("We need a food delivery app.", "en")

        self.assertEqual(result, "We need a food delivery app.")
        self.assertEqual(router.calls, [])

    async def test_blank_text_never_reaches_the_provider(self):
        # Silence now yields an empty caption rather than a fake failure; it
        # must not turn into an LLM call either.
        router = self._router()

        self.assertEqual(await translate.translate_to_english("", "hi"), "")
        self.assertEqual(await translate.translate_to_english("   ", "gu"), "   ")
        self.assertEqual(router.calls, [])

    async def test_a_translation_failure_returns_the_original_line(self):
        # A caption in the wrong language beats no caption. This is what keeps
        # a provider outage from blanking the transcript.
        class _FailingRouter:
            async def chat(self, **kwargs):
                raise RuntimeError("All LLM providers failed or are unavailable.")

        with mock.patch.object(translate, "llm_router", _FailingRouter()):
            result = await translate.translate_to_english(HINDI, "hi")

        # The spoken words survive, and the line says plainly that the English
        # version is missing rather than passing the original off as English.
        self.assertIn(HINDI, result)
        self.assertIn("translation unavailable", result)

    async def test_the_retry_for_untranslated_output_keeps_the_full_budget(self):
        # translate.py retries once when the answer still contains non-Latin
        # script. That retry must not be the one that gets starved.
        router = self._router(answer="अभी भी हिन्दी")

        await translate.translate_to_english(HINDI, "hi")

        self.assertEqual(len(router.calls), 2, "a non-English answer is retried once")
        for call in router.calls:
            self.assertGreaterEqual(call["max_tokens"], settings.llm_default_max_tokens)


if __name__ == "__main__":
    unittest.main(verbosity=2)
