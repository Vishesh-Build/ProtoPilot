"""
The ASR layer: which engine transcribes an utterance, what it returns, and
how many may run at once.

Three bugs from real meetings are pinned down here.

  * A cloud failure must cost one utterance, not the meeting. A single
    Sarvam error falls back to local Whisper for that utterance only; the
    process latches to Whisper only after several failures in a row, when
    the key or the network is genuinely wrong.
  * Concurrency has to depend on the device. ctranslate2 already spreads one
    transcription across every core, so two at once on CPU makes both
    slower: a log showed 5.28s of audio taking 34.92s while the queue wait
    grew to 170.83s and the worst caption landed 195.97s after it was
    spoken. On CPU the limit is 1, in code, where a stale .env cannot
    override it.
  * Sarvam's response envelope could not be verified from the machine this
    was written on, so the parser is deliberately forgiving. These tests
    hold it to that promise across every shape those APIs plausibly return.

Run from the backend/ directory:
    python -m unittest discover -s tests -t . -v
"""

import asyncio
import logging
import unittest
import wave
from io import BytesIO
from unittest import mock

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.transcription import asr  # noqa: E402

# Fallback and latch paths log on purpose; keep the output about assertions.
logging.getLogger("protopilot.asr").setLevel(logging.CRITICAL)


class WavWrappingTest(unittest.TestCase):
    """The bot holds bare PCM frames; an HTTP ASR API needs a real file."""

    def test_header_is_a_16khz_mono_16bit_wav(self):
        pcm = b"\x01\x02" * 1600  # 0.1s
        blob = asr.pcm16_to_wav_bytes(pcm)
        self.assertTrue(blob.startswith(b"RIFF"))
        self.assertIn(b"WAVE", blob[:16])

        with wave.open(BytesIO(blob), "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), 16000)
            self.assertEqual(wav.getnframes(), 1600)
            self.assertEqual(wav.readframes(1600), pcm)

    def test_frames_survive_untouched(self):
        pcm = bytes(range(256)) * 8
        with wave.open(BytesIO(asr.pcm16_to_wav_bytes(pcm)), "rb") as wav:
            self.assertEqual(wav.readframes(wav.getnframes()), pcm)

    def test_empty_audio_is_still_a_valid_wav(self):
        with wave.open(BytesIO(asr.pcm16_to_wav_bytes(b"")), "rb") as wav:
            self.assertEqual(wav.getnframes(), 0)


class LanguageNormalisationTest(unittest.TestCase):
    """Sarvam says `hi-IN`, Whisper says `hi`. The UI must see one form."""

    def test_region_suffix_is_dropped(self):
        self.assertEqual(asr.normalise_language("hi-IN"), "hi")
        self.assertEqual(asr.normalise_language("gu-IN"), "gu")
        self.assertEqual(asr.normalise_language("en-US"), "en")

    def test_case_and_whitespace(self):
        self.assertEqual(asr.normalise_language("  EN-us "), "en")

    def test_missing_becomes_unknown_rather_than_empty(self):
        for value in (None, "", "   ", "unknown", "null", "none", "NONE"):
            self.assertEqual(asr.normalise_language(value), "unknown", repr(value))


class ForgivingParserTest(unittest.TestCase):
    """
    _first_string is the one piece written against an unverified contract, so
    it is held to every envelope these APIs plausibly return. A key rename
    should cost a caption, never a crash.
    """

    def _text(self, payload):
        return asr._first_string(payload, asr._TEXT_KEYS)

    def test_flat_response(self):
        self.assertEqual(self._text({"transcript": "mujhe login chahiye"}), "mujhe login chahiye")

    def test_key_order_decides_between_two_present_keys(self):
        # _TEXT_KEYS puts "transcript" first, so it wins over "text".
        self.assertEqual(self._text({"text": "second", "transcript": "first"}), "first")

    def test_nested_under_a_wrapper(self):
        for wrapper in ("data", "result", "results", "output", "response"):
            self.assertEqual(self._text({wrapper: {"transcript": "nested"}}), "nested", wrapper)

    def test_top_level_list(self):
        self.assertEqual(self._text([{"transcript": "first item"}]), "first item")

    def test_list_under_a_wrapper(self):
        self.assertEqual(self._text({"results": [{"text": "in a list"}]}), "in a list")

    def test_blank_and_whitespace_values_are_not_answers(self):
        self.assertEqual(self._text({"transcript": "   ", "text": "real"}), "real")

    def test_unknown_shapes_return_empty_instead_of_raising(self):
        for payload in ({}, [], None, "a string", 42, {"unrelated": "x"}, {"data": None}):
            self.assertEqual(self._text(payload), "", repr(payload))

    def test_language_keys_are_read_from_the_same_shapes(self):
        self.assertEqual(
            asr._first_string({"data": {"language_code": "gu-IN"}}, asr._LANGUAGE_KEYS),
            "gu-IN",
        )

    def test_deep_nesting_gives_up_rather_than_recursing_forever(self):
        payload = {"data": {"data": {"data": {"data": {"data": {"transcript": "too deep"}}}}}}
        self.assertEqual(self._text(payload), "")


GUJARATI = "મને લોગિન જોઈએ"
ENGLISH = "I need a login"


class SarvamResponseTest(unittest.IsolatedAsyncioTestCase):
    """
    saaras:v3 runs both passes against the SAME endpoint (/speech-to-text),
    distinguished only by the `mode` form field: mode="translate" returns the
    English line, mode="transcribe" returns the line as it was actually
    spoken. Both run in parallel; only the translate one is essential.
    """

    def setUp(self):
        self.provider = asr.SarvamProvider()
        self.provider.api_key = "test-key"
        self.calls: list[tuple[str, str]] = []  # (mode, model)

    def _serve(self, **by_mode):
        async def fake_post(path, wav_bytes, model, mode=None, language_code=None):
            self.calls.append((mode, model))
            assert path == "/speech-to-text", f"saaras:v3 uses one endpoint, got {path}"
            reply = by_mode[mode]
            if isinstance(reply, BaseException):
                raise reply
            return reply

        self.provider._post = fake_post

    async def test_both_passes_are_merged(self):
        self._serve(
            translate={"transcript": ENGLISH, "language_code": "gu-IN"},
            transcribe={"transcript": GUJARATI},
        )
        result = await self.provider.transcribe(b"\x00\x00" * 8000)

        self.assertEqual(result.text, GUJARATI)
        self.assertEqual(result.english_text, ENGLISH)
        self.assertEqual(result.language, "gu")
        self.assertEqual(result.provider, "sarvam")
        # A language identifier, not a coin flip — so the low-confidence
        # warning downstream must not fire on every Sarvam line.
        self.assertEqual(result.language_probability, 1.0)
        self.assertEqual({mode for mode, _ in self.calls}, {"translate", "transcribe"})

    async def test_english_is_reused_when_the_original_pass_fails(self):
        # Losing the original-language line must not discard an utterance
        # whose English text arrived perfectly well.
        self._serve(
            translate={"transcript": ENGLISH, "language_code": "hi-IN"},
            transcribe=asr.AsrError("boom"),
        )
        result = await self.provider.transcribe(b"\x00\x00" * 8000)
        self.assertEqual(result.text, ENGLISH)
        self.assertEqual(result.english_text, ENGLISH)
        self.assertEqual(result.language, "hi")

    async def test_a_failed_translate_pass_is_raised_so_whisper_can_take_over(self):
        self._serve(
            translate=asr.AsrError("sarvam HTTP 401"),
            transcribe={"transcript": GUJARATI},
        )
        with self.assertRaises(asr.AsrError):
            await self.provider.transcribe(b"\x00\x00" * 8000)

    async def test_no_text_anywhere_is_silence_not_a_failure(self):
        # Both passes answered 200 with nothing in them. That is the engine
        # working correctly on audio with no words — a breath, a cough, or the
        # pause between two sentences, all of which VAD forwards. Raising a
        # plain AsrError here is what latched a live meeting over to Whisper
        # after three pauses, so the distinct type is the fix and this test is
        # what holds it: AsrSilence, checked before the generic AsrError.
        self._serve(translate={}, transcribe={})
        with self.assertRaises(asr.AsrSilence):
            await self.provider.transcribe(b"\x00\x00" * 8000)

    async def test_silence_is_still_an_asr_error_for_older_callers(self):
        # Subclass, so any `except AsrError` written before the split keeps
        # behaving as it did rather than letting the exception escape.
        self.assertTrue(issubclass(asr.AsrSilence, asr.AsrError))

    async def test_language_falls_back_to_the_original_pass(self):
        self._serve(
            translate={"transcript": ENGLISH},
            transcribe={"transcript": GUJARATI, "language_code": "gu-IN"},
        )
        result = await self.provider.transcribe(b"\x00\x00" * 8000)
        self.assertEqual(result.language, "gu")

    async def test_language_is_unknown_rather_than_guessed(self):
        self._serve(
            translate={"transcript": ENGLISH},
            transcribe={"transcript": GUJARATI},
        )
        result = await self.provider.transcribe(b"\x00\x00" * 8000)
        self.assertEqual(result.language, "unknown")

    async def test_one_request_when_the_original_line_is_turned_off(self):
        self._serve(translate={"transcript": ENGLISH, "language_code": "en-IN"})
        with mock.patch.object(asr.settings, "sarvam_include_original", False):
            result = await self.provider.transcribe(b"\x00\x00" * 8000)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], "translate")
        self.assertEqual(result.text, ENGLISH)
        self.assertEqual(result.english_text, ENGLISH)

    async def test_each_mode_gets_its_own_configured_model(self):
        self._serve(
            translate={"transcript": ENGLISH, "language_code": "gu-IN"},
            transcribe={"transcript": GUJARATI},
        )
        await self.provider.transcribe(b"\x00\x00" * 8000)
        sent = dict(self.calls)
        self.assertEqual(sent["translate"], asr.settings.sarvam_model)
        self.assertEqual(sent["transcribe"], asr.settings.sarvam_stt_model)


class ProviderSelectionTest(unittest.TestCase):
    """
    Which engine is chosen, and — the part that matters at a demo — the
    honesty of the answer. `active_provider_name()` is what the UI shows, so
    it must never claim Sarvam when Whisper is doing the work.
    """

    def setUp(self):
        self._latch = asr._sarvam_latched_off
        self._key = asr._sarvam.api_key

    def tearDown(self):
        asr._sarvam_latched_off = self._latch
        asr._sarvam.api_key = self._key

    def _select(self, mode, key):
        # api_key is read off the provider instance, not settings: it is
        # captured once at construction, which is exactly why a test that
        # patched settings alone would pass while proving nothing.
        asr._sarvam.api_key = key
        with mock.patch.object(asr.settings, "asr_provider", mode):
            return asr.sarvam_enabled(), asr.active_provider_name()

    def test_auto_uses_sarvam_when_a_key_exists(self):
        self.assertEqual(self._select("auto", "test-key"), (True, "sarvam"))

    def test_auto_falls_back_to_whisper_with_no_key(self):
        # The offline default. Nothing to configure, nothing to pay for.
        self.assertEqual(self._select("auto", None), (False, "whisper"))
        self.assertEqual(self._select("auto", ""), (False, "whisper"))

    def test_whisper_can_be_forced_even_with_a_key(self):
        self.assertEqual(self._select("whisper", "test-key"), (False, "whisper"))

    def test_forcing_sarvam_without_a_key_still_transcribes(self):
        # A misconfiguration must degrade to local Whisper, not to silence.
        self.assertEqual(self._select("sarvam", None), (False, "whisper"))

    def test_mode_is_read_case_and_whitespace_insensitively(self):
        self.assertEqual(self._select("  WHISPER ", "test-key"), (False, "whisper"))

    def test_the_latch_overrides_everything(self):
        asr._sarvam_latched_off = True
        self.assertEqual(self._select("sarvam", "test-key"), (False, "whisper"))


def _returns(value):
    """An async stand-in for whisper_service.ensure_model_loaded()."""

    async def fake():
        return value

    return fake


class ConcurrencyLimitTest(unittest.IsolatedAsyncioTestCase):
    """
    The limit that made captions land three minutes late. On CPU it must be
    1 — decided here in code, where a stale .env cannot raise it.
    """

    def setUp(self):
        asr._semaphores.clear()
        self._key = asr._sarvam.api_key
        self._latch = asr._sarvam_latched_off
        asr._sarvam_latched_off = False

    def tearDown(self):
        asr._semaphores.clear()
        asr._sarvam.api_key = self._key
        asr._sarvam_latched_off = self._latch

    async def _capacity(self, sem):
        """How many slots the semaphore hands out before it would block."""
        taken = 0
        while not sem.locked():
            await sem.acquire()
            taken += 1
        for _ in range(taken):
            sem.release()
        return taken

    async def _whisper_limit(self, device):
        with mock.patch.object(asr.whisper_service, "ensure_model_loaded", _returns(device)):
            return await self._capacity(await asr.whisper_semaphore())

    async def test_cpu_allows_exactly_one(self):
        self.assertEqual(await self._whisper_limit("cpu"), 1)
        self.assertEqual(asr.settings.max_concurrent_transcriptions_cpu, 1,
                         "the CPU default itself is the fix — 2 is what broke the meeting")

    async def test_gpu_allows_the_configured_number(self):
        self.assertEqual(await self._whisper_limit("cuda"),
                         asr.settings.max_concurrent_transcriptions)

    async def test_a_runtime_fall_back_to_cpu_gets_its_own_limit(self):
        # The CUDA->CPU latch happens on the first transcribe(), after a
        # semaphore may already exist for "cuda". Keying by device means the
        # CPU limit is not inherited from the GPU one.
        await self._whisper_limit("cuda")
        self.assertEqual(await self._whisper_limit("cpu"), 1)
        self.assertEqual(set(asr._semaphores), {"whisper-cuda", "whisper-cpu"})

    async def test_the_same_device_is_never_given_a_second_semaphore(self):
        # Two semaphores for one device would mean twice the limit.
        with mock.patch.object(asr.whisper_service, "ensure_model_loaded", _returns("cpu")):
            first = await asr.whisper_semaphore()
            second = await asr.whisper_semaphore()
        self.assertIs(first, second)

    async def test_sarvam_gets_the_network_limit_and_never_loads_a_model(self):
        asr._sarvam.api_key = "test-key"
        # ensure_model_loaded would raise here: the cloud path must not touch
        # the local model just to work out how many requests it may make.
        def explode():
            raise AssertionError("the Sarvam path must not load the Whisper model")

        with mock.patch.object(asr.whisper_service, "ensure_model_loaded", explode), \
                mock.patch.object(asr.settings, "asr_provider", "auto"):
            sem = await asr.get_concurrency_semaphore()
        self.assertEqual(await self._capacity(sem),
                         asr.settings.max_concurrent_sarvam_requests)

    async def test_without_a_key_the_active_limit_is_whispers(self):
        asr._sarvam.api_key = None
        with mock.patch.object(asr.whisper_service, "ensure_model_loaded", _returns("cpu")), \
                mock.patch.object(asr.settings, "asr_provider", "auto"):
            sem = await asr.get_concurrency_semaphore()
        self.assertEqual(await self._capacity(sem), 1)


class FallbackAndLatchTest(unittest.IsolatedAsyncioTestCase):
    """
    What one cloud failure costs. The answer has to be one utterance — a
    dropped packet must not downgrade a 30-minute meeting — while a wrong
    key, which fails every time, must stop being retried per caption.
    """

    def setUp(self):
        self._key = asr._sarvam.api_key
        asr._sarvam.api_key = "test-key"
        asr._sarvam_latched_off = False
        asr._sarvam_consecutive_failures = 0
        asr._semaphores.clear()

        self.sarvam_calls = 0
        self.whisper_calls = 0
        self.semaphore_calls = 0
        self.sarvam_fails = True

        async def sarvam_transcribe(raw_pcm16, language_hint=None):
            self.sarvam_calls += 1
            if self.sarvam_fails:
                raise asr.AsrError("sarvam HTTP 403: invalid subscription key")
            return asr.AsrResult("cloud line", "gu", 1.0, "sarvam", english_text="cloud english")

        async def whisper_transcribe(raw_pcm16):
            self.whisper_calls += 1
            return asr.AsrResult("local line", "hi", 0.7, "whisper")

        async def fake_semaphore():
            # Counted, so the tests can prove which slot the fallback takes
            # without loading a real model to find out the device.
            self.semaphore_calls += 1
            return asyncio.Semaphore(1)

        for patch in (
            mock.patch.object(asr._sarvam, "transcribe", sarvam_transcribe),
            mock.patch.object(asr._whisper, "transcribe", whisper_transcribe),
            mock.patch.object(asr, "whisper_semaphore", fake_semaphore),
            mock.patch.object(asr.settings, "asr_provider", "auto"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        asr._sarvam.api_key = self._key
        asr._sarvam_latched_off = False
        asr._sarvam_consecutive_failures = 0
        asr._semaphores.clear()

    AUDIO = b"\x00\x00" * 8000

    async def test_a_single_cloud_failure_costs_one_utterance_not_the_meeting(self):
        result = await asr.transcribe(self.AUDIO)

        self.assertEqual(result.provider, "whisper")
        self.assertEqual(result.text, "local line")
        self.assertIsNone(result.english_text, "Whisper's line still needs translating")
        self.assertFalse(asr._sarvam_latched_off)
        self.assertEqual(asr._sarvam_consecutive_failures, 1)

        # The next utterance tries the cloud again rather than giving up.
        await asr.transcribe(self.AUDIO)
        self.assertEqual(self.sarvam_calls, 2)

    async def test_the_fallback_takes_a_whisper_slot_of_its_own(self):
        # The caller holds a Sarvam slot, which allows six at once. Reusing it
        # for the local model would put six transcriptions on the cores —
        # the exact contention that made captions land 196s late.
        await asr.transcribe(self.AUDIO)
        self.assertEqual(self.semaphore_calls, 1)
        self.assertEqual(self.whisper_calls, 1)

    async def test_three_failures_in_a_row_latch_to_whisper(self):
        for _ in range(asr._SARVAM_FAILURE_LIMIT):
            await asr.transcribe(self.AUDIO)

        self.assertTrue(asr._sarvam_latched_off)
        self.assertEqual(asr.active_provider_name(), "whisper",
                         "the UI must say Whisper once Whisper is doing the work")

        # From here the cloud is not tried again: no per-caption timeout.
        self.sarvam_fails = False
        result = await asr.transcribe(self.AUDIO)
        self.assertEqual(self.sarvam_calls, asr._SARVAM_FAILURE_LIMIT)
        self.assertEqual(result.provider, "whisper")

    async def test_silence_never_latches_however_often_it_happens(self):
        # THE demo bug. A real 3.5-minute meeting had Sarvam answer 200 with an
        # empty transcript three times — breaths and pauses between sentences —
        # and the session latched to local Whisper for good. Captions went from
        # ~1.2s to 8-25s, one line came back as Telugu, and a cloud engine that
        # never failed once was never called again.
        async def silent(raw_pcm16, language_hint=None):
            self.sarvam_calls += 1
            raise asr.AsrSilence("sarvam heard no speech in this utterance")

        with mock.patch.object(asr._sarvam, "transcribe", silent):
            for _ in range(asr._SARVAM_FAILURE_LIMIT * 3):
                result = await asr.transcribe(self.AUDIO)
                self.assertEqual(result.text, "", "silence must produce no caption")

        self.assertFalse(asr._sarvam_latched_off, "silence is not a Sarvam failure")
        self.assertEqual(asr._sarvam_consecutive_failures, 0)
        self.assertEqual(asr.active_provider_name(), "sarvam")
        self.assertEqual(self.whisper_calls, 0,
                         "re-transcribing silence locally would waste the single CPU slot")

    async def test_silence_does_not_reset_a_real_failure_streak_into_a_latch(self):
        # Interleaving matters: two real failures, then a pause, then a third
        # real failure must NOT latch, because the streak is broken. The rule
        # stays "three consecutive genuine failures".
        await asr.transcribe(self.AUDIO)
        await asr.transcribe(self.AUDIO)
        self.assertEqual(asr._sarvam_consecutive_failures, 2)

        async def silent(raw_pcm16, language_hint=None):
            raise asr.AsrSilence("no speech")

        with mock.patch.object(asr._sarvam, "transcribe", silent):
            await asr.transcribe(self.AUDIO)

        await asr.transcribe(self.AUDIO)
        self.assertFalse(asr._sarvam_latched_off)
        self.assertEqual(asr._sarvam_consecutive_failures, 1)

    async def test_a_success_resets_the_counter(self):
        await asr.transcribe(self.AUDIO)
        await asr.transcribe(self.AUDIO)
        self.assertEqual(asr._sarvam_consecutive_failures, 2)

        self.sarvam_fails = False
        result = await asr.transcribe(self.AUDIO)
        self.assertEqual(result.provider, "sarvam")
        self.assertEqual(result.english_text, "cloud english")
        self.assertEqual(asr._sarvam_consecutive_failures, 0)

        # Two more failures must not latch: three *consecutive* is the rule,
        # otherwise an hour of occasional hiccups would disable the cloud.
        self.sarvam_fails = True
        await asr.transcribe(self.AUDIO)
        await asr.transcribe(self.AUDIO)
        self.assertFalse(asr._sarvam_latched_off)

    async def test_the_whisper_only_path_does_not_acquire_a_second_slot(self):
        # The caller's slot already IS the Whisper slot. Acquiring it again
        # here would deadlock at a limit of 1 — no captions at all.
        asr._sarvam.api_key = None
        result = await asr.transcribe(self.AUDIO)

        self.assertEqual(result.provider, "whisper")
        self.assertEqual(self.semaphore_calls, 0)
        self.assertEqual(self.sarvam_calls, 0)


class LanguageHintTest(unittest.IsolatedAsyncioTestCase):
    """
    The short-clip language-ID failure: a 1.5s Gujarati clip came back as
    Telugu (same sounds, wrong script) because automatic language ID needs
    more audio than that. The fix: Sarvam only gets the language hint on
    SHORT clips, and the hint comes from what it detected on the last
    longer one. A long clip must NEVER be hinted — meetings switch
    languages, and the engine's own ID is better than a stale prior.
    """

    def setUp(self):
        self.provider = asr.SarvamProvider()
        self.provider.api_key = "test-key"
        self.hints: list[str | None] = []

        async def fake_post(path, wav_bytes, model, mode=None, language_code=None):
            self.hints.append(language_code)
            return {"transcript": "text", "language_code": "gu-IN"}

        self.provider._post = fake_post
        asr._last_language_code = None

    def tearDown(self):
        asr._last_language_code = None

    def _pcm(self, seconds: float) -> bytes:
        return b"\x00\x00" * int(16000 * seconds)

    async def test_short_clip_gets_the_hint(self):
        result = await self.provider.transcribe(self._pcm(1.5), language_hint="gu-IN")
        self.assertEqual(self.hints, ["gu-IN", "gu-IN"], "both passes must be hinted on a short clip")
        self.assertEqual(result.language, "gu")

    async def test_long_clip_is_never_hinted(self):
        await self.provider.transcribe(self._pcm(4.0), language_hint="gu-IN")
        self.assertEqual(self.hints, [None, None], "a long clip must trust the engine's own language ID")

    async def test_no_hint_available_means_no_hint_sent(self):
        await self.provider.transcribe(self._pcm(1.0), language_hint=None)
        self.assertEqual(self.hints, [None, None])

    def test_record_language_updates_the_prior(self):
        asr.record_language("gu")
        self.assertEqual(asr._last_language_code, "gu-IN",
                         "the hint field needs BCP-47 — a bare 'gu' is a 400 from Sarvam")
        asr.record_language("unknown")  # must not overwrite with garbage
        self.assertEqual(asr._last_language_code, "gu-IN")
        asr.record_language(None)
        self.assertEqual(asr._last_language_code, "gu-IN", "None must not clear a good prior")


if __name__ == "__main__":
    unittest.main()
