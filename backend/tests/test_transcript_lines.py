"""
Transcript-line behaviour: ids, chronological ordering, late translations.

These are the mechanics that let a caption appear the instant Whisper
returns and get patched afterwards, so they're worth pinning down.

Run from the backend/ directory:
    python -m unittest discover -s tests -t . -v

Deliberately stdlib-only (unittest, no pytest) and imports nothing that
touches the network or the database, so it runs anywhere with plain Python.
"""

import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.meetings.session import MeetingSession  # noqa: E402


class TranscriptLineIdsTest(unittest.TestCase):
    def setUp(self):
        self.session = MeetingSession(meeting_id="m-ids")

    def test_ids_are_unique_and_increasing(self):
        ids = [self.session.add_transcript_line("Vishesh", "hi", f"line {i}").id for i in range(5)]
        self.assertEqual(ids, [1, 2, 3, 4, 5])
        self.assertEqual(len(set(ids)), 5)

    def test_ids_are_per_session_not_global(self):
        other = MeetingSession(meeting_id="m-other")
        self.assertEqual(self.session.add_transcript_line("A", "hi", "x").id, 1)
        self.assertEqual(other.add_transcript_line("B", "gu", "y").id, 1)

    def test_display_text_falls_back_to_original_until_translated(self):
        line = self.session.add_transcript_line("Vishesh", "gu", "મને લોગિન જોઈએ")
        # No translation yet: a caption must never render as an empty string.
        self.assertIsNone(line.english_text)
        self.assertEqual(line.display_text(), "મને લોગિન જોઈએ")

        self.session.set_translation(line.id, "I need a login")
        self.assertEqual(line.display_text(), "I need a login")

    def test_to_dict_carries_id_and_spoken_at(self):
        line = self.session.add_transcript_line("Vishesh", "hi", "namaste", spoken_at="2026-09-02T10:00:00Z")
        self.assertEqual(
            line.to_dict(),
            {
                "id": line.id,
                "speaker": "Vishesh",
                "language": "hi",
                "original_text": "namaste",
                "english_text": None,
                "spoken_at": "2026-09-02T10:00:00Z",
            },
        )


class ChronologicalOrderTest(unittest.TestCase):
    """
    Utterances are transcribed concurrently, so a long one spoken first can
    finish after a short one spoken later. Arrival order is therefore not
    chronology, and the transcript has to sort itself out by spoken_at.
    """

    def setUp(self):
        self.session = MeetingSession(meeting_id="m-order")

    def _texts(self):
        return [line.original_text for line in self.session.transcript]

    def test_late_arriving_earlier_utterance_lands_before_it(self):
        self.session.add_transcript_line("A", "hi", "spoken second", spoken_at="2026-09-02T10:00:05Z")
        self.session.add_transcript_line("B", "hi", "spoken first", spoken_at="2026-09-02T10:00:01Z")
        self.assertEqual(self._texts(), ["spoken first", "spoken second"])

    def test_ids_stay_with_arrival_order_while_position_follows_time(self):
        late = self.session.add_transcript_line("A", "hi", "spoken second", spoken_at="2026-09-02T10:00:05Z")
        early = self.session.add_transcript_line("B", "hi", "spoken first", spoken_at="2026-09-02T10:00:01Z")
        # The client matches transcript_update on line_id, so ids must NOT be
        # renumbered when a line is inserted ahead of an existing one.
        self.assertEqual((late.id, early.id), (1, 2))
        self.assertEqual([line.id for line in self.session.transcript], [2, 1])

    def test_shuffled_arrival_still_ends_up_sorted(self):
        stamps = ["10:00:09", "10:00:02", "10:00:07", "10:00:01", "10:00:04"]
        for stamp in stamps:
            self.session.add_transcript_line("A", "hi", stamp, spoken_at=f"2026-09-02T{stamp}Z")
        self.assertEqual(self._texts(), sorted(stamps))

    def test_equal_timestamps_keep_arrival_order(self):
        same = "2026-09-02T10:00:00Z"
        self.session.add_transcript_line("A", "hi", "first in", spoken_at=same)
        self.session.add_transcript_line("B", "hi", "second in", spoken_at=same)
        self.assertEqual(self._texts(), ["first in", "second in"])


class SetTranslationTest(unittest.TestCase):
    def setUp(self):
        self.session = MeetingSession(meeting_id="m-translate")

    def test_patches_only_the_matching_line(self):
        first = self.session.add_transcript_line("A", "gu", "એક")
        second = self.session.add_transcript_line("B", "hi", "दो")

        patched = self.session.set_translation(second.id, "two")
        self.assertIs(patched, second)
        self.assertEqual(second.english_text, "two")
        self.assertIsNone(first.english_text)

    def test_unknown_id_returns_none_instead_of_raising(self):
        # Happens if a translation lands after the meeting was deleted.
        self.assertIsNone(self.session.set_translation(999, "ignored"))


class SummaryTest(unittest.TestCase):
    def test_has_prototype_is_true_only_for_the_prototype_agent(self):
        session = MeetingSession(meeting_id="m-summary")
        self.assertFalse(session.summary()["has_prototype"])

        session.agent_outputs["pm"] = "# PRD..."
        self.assertFalse(session.summary()["has_prototype"], "a PM-only run is not a prototype")

        session.agent_outputs["prototype"] = "<html>...</html>"
        self.assertTrue(session.summary()["has_prototype"])

    def test_languages_used_is_deduped_in_first_seen_order(self):
        session = MeetingSession(meeting_id="m-langs")
        for lang in ["hi", "gu", "hi", "en", "gu"]:
            session.add_transcript_line("A", lang, "x")
        self.assertEqual(session.summary()["languages"], ["hi", "gu", "en"])


if __name__ == "__main__":
    unittest.main()
