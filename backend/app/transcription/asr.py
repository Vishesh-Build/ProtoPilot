"""
ASR provider layer — which engine turns audio into text.

Two engines, one interface:

  SarvamProvider (primary when SARVAM_API_KEY is set)
      Cloud ASR built for Indian languages. Two things make it the right
      default for this project. First, it needs no GPU: the CPU-only
      Whisper path on this machine took 34-79 seconds per utterance and
      pushed the worst caption to 196 seconds after the words were spoken,
      which is not a transcription problem you can tune your way out of.
      Second, it uses saaras:v3 on /speech-to-text with mode="translate",
      which returns English directly, so the separate translation LLM
      call per line disappears along with its latency and its failure
      mode. (Sarvam's older saaras:v2.5 /speech-to-text-translate endpoint
      is legacy now and due to be deprecated — v3 is both the more
      accurate model and the one guaranteed to keep working.)

  WhisperProvider (fallback, and the only engine with no API key needed)
      Local faster-whisper. Still the offline safety net, and still what
      runs if Sarvam is unreachable mid-meeting.

Failure policy: a single Sarvam failure falls back to Whisper for that
one utterance only — a dropped packet should not downgrade the whole
meeting. Only after _SARVAM_FAILURE_LIMIT failures in a row does the
process latch to Whisper, on the assumption the key or the network is
genuinely wrong rather than briefly unlucky.
"""

import asyncio
import io
import logging
import wave

import httpx

from app.config import settings
from app.transcription import whisper_service

logger = logging.getLogger("protopilot.asr")

_SAMPLE_RATE = 16000
_SARVAM_FAILURE_LIMIT = 3

class AsrError(Exception):
    """One utterance could not be transcribed by a given engine."""


class AsrSilence(AsrError):
    """
    The engine answered normally and reported no speech in the audio.

    This is NOT a failure: VAD hands over anything above the noise floor, so
    a breath, a cough, a chair or a pause between sentences all reach the
    engine as a perfectly valid request that correctly comes back empty.

    It matters that this is a separate type, because a real 3.5-minute
    meeting contains several such utterances, and counting them as Sarvam
    failures latched the whole session over to local Whisper after three
    pauses — captions went from ~1.2s to 8-25s mid-demo for a cloud engine
    that was working fine the entire time.
    """


class AsrResult:
    """
    What one engine made of one utterance.

    `english_text` is None when the engine only produced the original
    language — that's the signal for the caller to run the translation LLM.
    When it's already set (Sarvam's translate endpoint), that call is
    skipped entirely, which is most of the reason Sarvam is the default.
    """

    def __init__(
        self,
        text: str,
        language: str,
        language_probability: float,
        provider: str,
        english_text: str | None = None,
    ):
        self.text = text
        self.language = language
        self.language_probability = language_probability
        self.provider = provider
        self.english_text = english_text


def pcm16_to_wav_bytes(raw_pcm16: bytes, sample_rate: int = _SAMPLE_RATE) -> bytes:
    """
    Wrap raw mono PCM16 in a WAV container. The bot holds bare PCM frames
    from LiveKit; an HTTP ASR API wants a file with a header.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(raw_pcm16)
    return buffer.getvalue()


def normalise_language(code: str | None) -> str:
    """`hi-IN` -> `hi`, so Sarvam and Whisper report languages the same way."""
    if not code:
        return "unknown"
    cleaned = str(code).strip().lower()
    if cleaned in ("", "unknown", "null", "none"):
        return "unknown"
    return cleaned.split("-")[0]


def _first_string(payload, keys: tuple[str, ...], depth: int = 0) -> str:
    """
    Pull the first non-empty string at any of `keys`, following one or two
    levels of `data`/`result` nesting.

    Deliberately forgiving: the exact response envelope could not be
    verified from this workspace, so the parser accepts every shape these
    APIs plausibly return rather than hard-coding one and failing loudly on
    a key rename.
    """
    if isinstance(payload, list):
        return _first_string(payload[0], keys, depth) if payload else ""
    if not isinstance(payload, dict) or depth > 3:
        return ""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for nest in ("data", "result", "results", "output", "response"):
        if nest in payload:
            found = _first_string(payload[nest], keys, depth + 1)
            if found:
                return found
    return ""


_TEXT_KEYS = ("transcript", "text", "transcript_text", "translated_text", "translation")
_LANGUAGE_KEYS = ("language_code", "detected_language_code", "language", "src_lang", "source_language_code")


class SarvamProvider:
    name = "sarvam"

    def __init__(self):
        self.base_url = settings.sarvam_base_url.rstrip("/")
        self.api_key = settings.sarvam_api_key
        self.timeout = settings.sarvam_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _post(self, path: str, wav_bytes: bytes, model: str, mode: str | None = None, language_code: str | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = {"model": model}
        if mode is not None:
            # Only meaningful for saaras:v3 on /speech-to-text — the legacy
            # /speech-to-text-translate endpoint doesn't take this field at all.
            data["mode"] = mode
        if language_code is not None:
            # Verified live on saaras:v3: passing language_code=gu-IN forces
            # the right script when the clip is too short for reliable
            # automatic language ID (a 1.5s Gujarati clip came back as
            # Telugu otherwise — same sounds, wrong script). Longer clips
            # don't need it, and the hint is only ever sent for them.
            data["language_code"] = language_code
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    headers={"api-subscription-key": self.api_key or ""},
                    files={"file": ("utterance.wav", wav_bytes, "audio/wav")},
                    data=data,
                )
        except httpx.RequestError as e:
            raise AsrError(f"sarvam network error on {path}: {e}") from e

        if resp.status_code >= 400:
            raise AsrError(f"sarvam HTTP {resp.status_code} on {path}: {resp.text[:200]}")
        try:
            payload = resp.json()
        except ValueError as e:
            raise AsrError(f"sarvam returned non-JSON on {path}: {e}") from e
        if not isinstance(payload, (dict, list)):
            raise AsrError(f"sarvam returned unexpected JSON type on {path}: {type(payload).__name__}")
        return payload

    async def _translate(self, wav_bytes: bytes, language_code: str | None = None) -> dict:
        # saaras:v3, mode="translate" — speech straight to English. Same
        # endpoint as _original below; only the mode differs.
        return await self._post("/speech-to-text", wav_bytes, settings.sarvam_model, mode="translate", language_code=language_code)

    async def _original(self, wav_bytes: bytes, language_code: str | None = None) -> dict:
        # saaras:v3, mode="transcribe" — text in whichever language was
        # actually spoken, for the on-screen original-language caption.
        return await self._post("/speech-to-text", wav_bytes, settings.sarvam_stt_model, mode="transcribe", language_code=language_code)

    async def transcribe(self, raw_pcm16: bytes, language_hint: str | None = None) -> AsrResult:
        """
        language_hint: optional BCP-47 code ("gu-IN") carried from the
        speaker's previous utterances. Sent to Sarvam only for SHORT clips
        (< ~2s), where automatic language ID is unreliable — the measured
        golden-set failure was a 1.5s Gujarati clip transcribed as Telugu.
        Longer clips leave it to the engine (better at language ID than a
        stale hint could ever be, and meetings do switch languages).
        """
        wav_bytes = pcm16_to_wav_bytes(raw_pcm16)

        # Only hint for short clips. The duration is exact from the PCM size.
        seconds = len(raw_pcm16) / 32000.0
        hint = language_hint if (language_hint and seconds < 2.5) else None

        if settings.sarvam_include_original:
            # Both calls run in parallel, so keeping the original-language
            # line on screen costs a request but no extra wall-clock time.
            # return_exceptions stops a failure of the secondary call from
            # discarding an utterance whose English text arrived fine.
            translate_payload, original_payload = await asyncio.gather(
                self._translate(wav_bytes, hint),
                self._original(wav_bytes, hint),
                return_exceptions=True,
            )
        else:
            translate_payload = await self._translate(wav_bytes, hint)
            original_payload = None

        if isinstance(translate_payload, BaseException):
            raise translate_payload

        english_text = _first_string(translate_payload, _TEXT_KEYS)
        language = normalise_language(_first_string(translate_payload, _LANGUAGE_KEYS))

        original_text = ""
        if isinstance(original_payload, BaseException):
            logger.warning(
                "sarvam: original-language pass failed (%s) — using the English text for both fields",
                original_payload,
            )
        elif original_payload is not None:
            original_text = _first_string(original_payload, _TEXT_KEYS)
            if language == "unknown":
                language = normalise_language(_first_string(original_payload, _LANGUAGE_KEYS))

        if not english_text and not original_text:
            # HTTP 200 with an empty transcript means "no words in this audio",
            # not "the engine is broken" — see AsrSilence. Sarvam even told us
            # which language it thought it heard, so the request itself was fine.
            raise AsrSilence("sarvam heard no speech in this utterance")

        return AsrResult(
            # With only the translate call available the original-language
            # line genuinely doesn't exist; showing the English text in both
            # places is honest, a blank caption would not be.
            text=original_text or english_text,
            language=language,
            # Sarvam reports a language code, not a probability. 1.0 records
            # "this came from a language identifier, not a coin flip", so the
            # low-confidence warning downstream doesn't fire on every line.
            language_probability=1.0,
            provider=self.name,
            english_text=english_text or original_text,
        )


class WhisperProvider:
    name = "whisper"

    @property
    def is_configured(self) -> bool:
        return True  # local model, nothing to configure

    async def transcribe(self, raw_pcm16: bytes) -> AsrResult:
        result = await whisper_service.transcribe_utterance(raw_pcm16)
        return AsrResult(
            text=result.text,
            language=result.language,
            language_probability=result.language_probability,
            provider=self.name,
            english_text=None,  # Whisper transcribes only — translation is a separate step
        )


_sarvam = SarvamProvider()
_whisper = WhisperProvider()

# Flipped once Sarvam has failed _SARVAM_FAILURE_LIMIT times in a row, at
# which point the problem is the key or the network rather than bad luck and
# retrying it per utterance only adds latency to every single caption.
_sarvam_latched_off = False
_sarvam_consecutive_failures = 0


def sarvam_enabled() -> bool:
    mode = settings.asr_provider.strip().lower()
    if mode == "whisper" or _sarvam_latched_off:
        return False
    if mode == "sarvam":
        return _sarvam.is_configured
    return _sarvam.is_configured  # "auto": Sarvam when a key exists


def active_provider_name() -> str:
    return _sarvam.name if sarvam_enabled() else _whisper.name


_semaphores: dict[str, asyncio.Semaphore] = {}
_semaphore_lock = asyncio.Lock()


async def _semaphore_for(key: str, limit: int) -> asyncio.Semaphore:
    limit = max(1, limit)
    existing = _semaphores.get(key)
    if existing is not None:
        return existing
    async with _semaphore_lock:
        if key not in _semaphores:
            _semaphores[key] = asyncio.Semaphore(limit)
            logger.info("asr: %s — allowing %d concurrent transcription(s)", key, limit)
        return _semaphores[key]


async def whisper_semaphore() -> asyncio.Semaphore:
    """
    Whisper's own limit, which cannot be known until the model has loaded
    and reported which device it ended up on.

    On GPU: settings.max_concurrent_transcriptions.
    On CPU: settings.max_concurrent_transcriptions_cpu (1), because
      ctranslate2 already spreads one transcription across every core.
      Running two at once doesn't double throughput, it halves both — the
      log that motivated this showed 5.28s of audio taking 34.92s while the
      queue backed up to a 170.83s wait and the worst caption landed 196s
      after the words were spoken.
    """
    device = await whisper_service.ensure_model_loaded()
    limit = (
        settings.max_concurrent_transcriptions
        if device == "cuda"
        else settings.max_concurrent_transcriptions_cpu
    )
    return await _semaphore_for(f"whisper-{device}", limit)


async def get_concurrency_semaphore() -> asyncio.Semaphore:
    """How many utterances may be in flight at once for the active engine."""
    if sarvam_enabled():
        # Network round trips rather than CPU cores, so several at once is free.
        return await _semaphore_for("sarvam", settings.max_concurrent_sarvam_requests)
    return await whisper_semaphore()


# Language hints keyed by SPEAKER, not globally. A meeting has several
# participants and each one stays in their own language for the most part —
# a global "last language" made speaker B's clip inherit speaker A's
# language and the forced script came out wrong (measured: a Hindi clip
# rendered in Gujarati script because the previous clip was Gujarati).
# Per-speaker priors make the hint trustworthy enough to send.
_speaker_languages: dict[str, str] = {}
# The language Sarvam last reported anywhere in this meeting — fallback for
# a speaker's very first utterance (better than nothing).
_last_language_code: str | None = None


# Maps the normalised 2-letter codes (what AsrResult.language carries) back
# to the BCP-47 codes Sarvam's language_code request field accepts.
_BCP47 = {
    "gu": "gu-IN", "hi": "hi-IN", "en": "en-IN", "bn": "bn-IN",
    "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN", "od": "od-IN",
    "pa": "pa-IN", "ta": "ta-IN", "te": "te-IN", "as": "as-IN",
    "ur": "ur-IN", "ne": "ne-IN", "kok": "kok-IN",
}


def record_language(language: str, speaker: str | None = None) -> None:
    """Called with the language Sarvam itself detected on a longer clip —
    feeding it back as a hint for the same speaker's next short one.
    Stores the BCP-47 form, because that's what the language_code request
    field takes (sending the plain 'gu' gets a 400 back)."""
    global _last_language_code
    if not language or language == "unknown":
        return  # never record garbage
    bcp47 = _BCP47.get(language)
    if not bcp47:
        return
    if speaker:
        _speaker_languages[speaker] = bcp47
    _last_language_code = bcp47


def language_hint_for(speaker: str | None) -> str | None:
    """The best available language prior for a speaker's next utterance:
    their own last-detected language, else the meeting's last one."""
    if speaker and speaker in _speaker_languages:
        return _speaker_languages[speaker]
    return _last_language_code


def reset_language_tracking() -> None:
    """New meeting / new bot process — stale priors from a previous meeting
    must not leak into this one."""
    global _last_language_code
    _speaker_languages.clear()
    _last_language_code = None


async def transcribe(raw_pcm16: bytes, speaker: str | None = None) -> AsrResult:
    """
    Transcribe one complete utterance with whichever engine is active,
    falling back to local Whisper if the cloud engine fails.

    speaker: used to key the per-speaker language prior that becomes the
    language_code hint on this speaker's next SHORT clip. None (e.g. from
    the benchmark or scripts) degrades to the meeting-wide prior.

    The caller is expected to already hold get_concurrency_semaphore().
    """
    global _sarvam_latched_off, _sarvam_consecutive_failures

    if not sarvam_enabled():
        # The caller's slot already IS the Whisper slot — acquiring it again
        # here would deadlock at a limit of 1.
        return await _whisper.transcribe(raw_pcm16)

    try:
        result = await _sarvam.transcribe(raw_pcm16, language_hint=language_hint_for(speaker))
    except AsrSilence as e:
        # The engine worked and there was nothing to transcribe. Do not count
        # this against the failure streak, and do not spend a Whisper slot
        # re-transcribing silence — Whisper's own VAD would just discard it
        # too, after occupying the single CPU slot for a second.
        logger.info("sarvam: %s — nothing to transcribe, streak untouched", e)
        _sarvam_consecutive_failures = 0
        return AsrResult(text="", language="unknown", language_probability=1.0,
                         provider=_sarvam.name, english_text="")
    except Exception as e:  # noqa: BLE001 — any cloud failure falls back rather than losing the line
        _sarvam_consecutive_failures += 1
        logger.warning(
            "sarvam failed (%d in a row): %s — transcribing this utterance locally instead",
            _sarvam_consecutive_failures, e,
        )
        if _sarvam_consecutive_failures >= _SARVAM_FAILURE_LIMIT:
            _sarvam_latched_off = True
            logger.error(
                "sarvam failed %d times in a row — switching to local Whisper for the rest of "
                "this session. Check SARVAM_API_KEY and SARVAM_MODEL (currently %r), then "
                "restart the backend. Run `python scripts/preflight.py` to test the key on its own.",
                _SARVAM_FAILURE_LIMIT, settings.sarvam_model,
            )
        # The caller holds a Sarvam slot, which permits several at once
        # because those are network round trips. Whisper needs its own,
        # otherwise a run of cloud failures puts six CPU transcriptions on
        # the cores at the same time — precisely the contention this file
        # exists to prevent. Different semaphore, so no deadlock.
        async with await whisper_semaphore():
            return await _whisper.transcribe(raw_pcm16)

    _sarvam_consecutive_failures = 0
    # A longer clip's detected language is this speaker's prior for their
    # next short one.
    record_language(result.language, speaker)
    return result