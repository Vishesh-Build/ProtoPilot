"""
Local transcription via faster-whisper.

The model is loaded once (lazily, on first use) and reused for every
utterance — loading it per-request would be far too slow.

GPU / CPU strategy:
Tries CUDA first (settings.whisper_model_size on the GPU, e.g. "medium" —
much faster and more accurate than CPU at the same model size). If CUDA
isn't available, or the GPU is too small for that model (out-of-memory —
a real risk on a 4GB card with "medium"), it automatically falls back to
CPU using settings.whisper_cpu_fallback_model_size (a smaller model, so
CPU-only mode stays fast rather than accurate-but-slow).

That covers load-time failures (model won't even construct). There's a
second, sneakier failure mode: on some Windows setups, WhisperModel(...,
device="cuda") constructs fine, but the FIRST actual transcribe() call
throws (e.g. "Library cublas64_12.dll is not found or cannot be
loaded") — the GPU looked fine until CUDA runtime libraries were
actually needed. transcribe_utterance() catches that too: on any
transcribe() failure it permanently switches to the CPU model for the
rest of the process and retries that one utterance, so a live meeting
never just stops transcribing — worst case it gets quietly slower after
one failed utterance instead of breaking entirely.

Language handling: Whisper's own auto-detect chooses from ~99
languages, and on a short noisy utterance from the CPU "small" model
that choice is close to a coin flip — a real meeting log had English
speech detected as Telugu at 0.68 confidence, and Hindi/English/Gujarati
sitting at ~0.32 each on lines that came back as gibberish. So detection
now runs as its own cheap pass and the winner is picked from
settings.whisper_allowed_languages ("en,hi,gu") instead of the full set,
which makes a Telugu/Urdu/Marathi misfire structurally impossible. Set
that setting to "" to restore plain auto-detect.
"""

import asyncio
import logging
import os
import sys
import time

import numpy as np

# On Windows, pip-installed nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels
# place their DLLs under site-packages\nvidia\<pkg>\bin\, which isn't on
# the system PATH by default. There are TWO different mechanisms at play,
# and BOTH are needed:
#
#   1. os.add_dll_directory() — covers DLLs that Python/ctypes loads
#      directly.
#   2. os.environ["PATH"] — ctranslate2's native code resolves its
#      dependencies (cublas64_12.dll, cudnn64_9.dll) via the standard
#      LoadLibrary search path. add_dll_directory() does NOT affect that
#      search, which is exactly why a model could LOAD on CUDA (loading
#      needs no cuBLAS) and then FAIL at the first transcribe() call with
#      "Library cublas64_12.dll is not found or cannot be loaded" —
#      verified live on this machine before this fix.
#
# Both must run BEFORE faster_whisper (and therefore ctranslate2) is
# imported, because ctranslate2 resolves its import-time dependencies
# through the same search. (Confirmed path layout — Windows wheels use
# \bin\, not \lib\ like the Linux wheels do.) If you installed CUDA
# Toolkit + cuDNN system-wide and they're already on PATH, this whole
# block is a harmless no-op.
if sys.platform == "win32":
    for _pkg_name in ("nvidia.cublas", "nvidia.cuda_nvrtc", "nvidia.cudnn"):
        try:
            _pkg = __import__(_pkg_name, fromlist=["__path__"])
            _bin_dir = os.path.join(_pkg.__path__[0], "bin")
            if os.path.isdir(_bin_dir):
                os.add_dll_directory(_bin_dir)
                # Prepend so the pip wheels' DLLs win over any stale
                # system CUDA that might also be on PATH.
                if _bin_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")
        except ImportError:
            pass  # that particular nvidia-*-cu12 package isn't installed — CPU fallback below handles it

from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger("protopilot.whisper")

_model: WhisperModel | None = None
_model_lock = asyncio.Lock()
_EXPECTED_SAMPLE_RATE = 16000

# Set once get_model() successfully loads a model — lets transcribe_utterance
# log/tune based on which device actually ended up being used.
_active_device: str | None = None

# Flipped to True the first time a CUDA transcribe() call fails at runtime
# (as opposed to failing to load) — forces every subsequent load to go
# straight to CPU instead of retrying a GPU that's already proven broken.
_cuda_runtime_broken = False


def _cuda_warmup_transcribe(model: WhisperModel) -> None:
    """
    Runs one tiny real transcribe() on the freshly-loaded CUDA model.

    This is the fix for the "CUDA loads fine, then dies at the first real
    caption" trap: loading the model needs no cuBLAS/cuDNN, so a broken
    CUDA runtime only reveals itself when the first utterance's encoder
    pass calls into it — by which point the meeting is live and the line
    the user is watching pays the cost (fallback CPU retry + 10x latency
    on that one utterance). A 0.2s silent clip here surfaces the same
    failure at load time instead, in well under a second.

    Raises whatever the real transcribe would — the caller treats that as
    "CUDA load failed" and falls back to CPU, loudly and up front.
    """
    import numpy as np

    silent = np.zeros(3200, dtype=np.float32)  # 0.2s of 16kHz silence
    segments, _info = model.transcribe(
        silent, vad_filter=False, beam_size=1, condition_on_previous_text=False
    )
    for _ in segments:  # force the generator to actually run
        pass


def _load_model_blocking(force_cpu: bool = False) -> tuple[WhisperModel, str]:
    """
    Runs on a worker thread (model loading is blocking). Tries CUDA first
    (unless force_cpu, e.g. because CUDA already failed once at runtime
    this session), falls back to CPU on any failure — wrong CUDA/cuDNN
    install, no GPU present, or the GPU running out of memory for this
    model size are all treated the same way: log it and fall back, never
    crash the app over it.

    "Any failure" includes the warmup: a model that loads but can't run
    one real transcribe is NOT a working CUDA model, and handing it to a
    live meeting is how a caption ends up 10x slower than it should be.
    """
    if not force_cpu:
        try:
            logger.info(
                "Loading faster-whisper model=%s on CUDA (compute_type=%s)...",
                settings.whisper_model_size, settings.whisper_gpu_compute_type,
            )
            model = WhisperModel(
                settings.whisper_model_size,
                device="cuda",
                compute_type=settings.whisper_gpu_compute_type,
            )
            _cuda_warmup_transcribe(model)
            logger.info("faster-whisper: using CUDA (model=%s, warmup ok)", settings.whisper_model_size)
            return model, "cuda"
        except Exception as e:  # noqa: BLE001 — load OR warmup failure: fall back to CPU
            logger.warning(
                "faster-whisper: CUDA unavailable (%s) — falling back to CPU with model=%s",
                e, settings.whisper_cpu_fallback_model_size,
            )

    model = WhisperModel(
        settings.whisper_cpu_fallback_model_size,
        device="cpu",
        compute_type=settings.whisper_compute_type,
        cpu_threads=settings.whisper_cpu_threads,
    )
    logger.warning(
        "faster-whisper: using CPU (model=%s). Expect several seconds per utterance — "
        "CPU transcription of Hindi/Gujarati is the slowest and least accurate path this "
        "project has. Set SARVAM_API_KEY to move transcription off this machine entirely, "
        "or fix CUDA (pip install nvidia-cublas-cu12 nvidia-cudnn-cu12) to use the "
        "'%s' model on the GPU instead.",
        settings.whisper_cpu_fallback_model_size, settings.whisper_model_size,
    )
    return model, "cpu"


async def get_model() -> WhisperModel:
    global _model, _active_device
    if _model is None:
        async with _model_lock:
            if _model is None:  # re-check inside the lock
                # Model loading is CPU/IO-bound and blocking — run off the event loop.
                _model, _active_device = await asyncio.to_thread(_load_model_blocking, _cuda_runtime_broken)
    return _model


async def ensure_model_loaded() -> str:
    """
    Loads the model if it isn't loaded yet and returns the device actually
    in use ("cuda" or "cpu"). Anything that needs to size a concurrency
    limit has to await this first, because the correct limit depends
    entirely on the answer — see app/livekit/transcription_bot.py.
    """
    await get_model()
    return _active_device or "cpu"


def active_device() -> str | None:
    """Device in use, or None if no model has been loaded yet."""
    return _active_device


async def _fall_back_to_cpu() -> WhisperModel:
    """
    Called when a CUDA transcribe() call fails at runtime (model loaded
    fine, but actual inference didn't). Forces a fresh CPU model and
    makes every future get_model() call skip CUDA entirely for the rest
    of this process — one failure is enough to stop trying the broken GPU.
    """
    global _model, _active_device, _cuda_runtime_broken
    async with _model_lock:
        _cuda_runtime_broken = True
        logger.warning("faster-whisper: CUDA failed at runtime — switching to CPU for the rest of this session.")
        _model, _active_device = await asyncio.to_thread(_load_model_blocking, True)
    return _model


def pcm16_bytes_to_float32(raw: bytes) -> np.ndarray:
    """
    Convert raw 16-bit PCM audio (mono, 16kHz — what the client should send)
    into the float32 numpy array faster-whisper expects.
    """
    int16 = np.frombuffer(raw, dtype=np.int16)
    return int16.astype(np.float32) / 32768.0


class TranscriptResult:
    def __init__(self, text: str, language: str, language_probability: float):
        self.text = text
        self.language = language
        self.language_probability = language_probability


def allowed_languages() -> list[str]:
    return [c.strip().lower() for c in settings.whisper_allowed_languages.split(",") if c.strip()]


def pick_allowed_language(
    all_language_probs, allowed: list[str]
) -> tuple[str, float] | None:
    """
    Given faster-whisper's ranked [(code, probability), ...] list, return the
    highest-probability language that ProtoPilot actually supports.

    Returns None when the allow-list is empty or none of its languages show
    up at all — the caller then leaves plain auto-detect in place rather
    than forcing a language the audio clearly isn't.
    """
    if not allowed or not all_language_probs:
        return None
    allowed_set = set(allowed)
    best: tuple[str, float] | None = None
    for entry in all_language_probs:
        try:
            code = str(entry[0]).lower()
            probability = float(entry[1])
        except (TypeError, IndexError, ValueError):
            continue
        if code in allowed_set and (best is None or probability > best[1]):
            best = (code, probability)
    return best


def _detect_allowed_language(model: WhisperModel, audio: np.ndarray, device: str):
    """
    One cheap detection pass, constrained to the supported languages. Costs
    an extra encoder run, which is far less than a full decode wasted on a
    language nobody in the meeting is speaking.
    """
    allowed = allowed_languages()
    if not allowed:
        return None
    detect = getattr(model, "detect_language", None)
    if detect is None:
        return None  # older faster-whisper — plain auto-detect still works
    try:
        detection = detect(audio)
    except Exception as e:  # noqa: BLE001 — detection is an optimisation, never fatal
        logger.warning(
            "whisper[%s]: language detection pass failed (%s) — falling back to auto-detect", device, e
        )
        return None
    all_probs = detection[2] if isinstance(detection, tuple) and len(detection) > 2 else None
    chosen = pick_allowed_language(all_probs, allowed)
    if chosen is None:
        top = detection[0] if isinstance(detection, tuple) and detection else "?"
        logger.warning(
            "whisper[%s]: detector's best guess (%s) is not in %s and no supported language "
            "scored at all — letting Whisper auto-detect this one",
            device, top, ",".join(allowed),
        )
    return chosen


def _run_transcribe(model: WhisperModel, audio: np.ndarray, device: str) -> tuple[str, str, float]:
    t0 = time.monotonic()
    beam_size = settings.whisper_gpu_beam_size if device == "cuda" else settings.whisper_beam_size
    forced = _detect_allowed_language(model, audio, device)
    segments, info = model.transcribe(
        audio,
        # Either a language from the supported set, or None to let Whisper
        # decide when detection couldn't produce a supported one.
        language=forced[0] if forced else None,
        vad_filter=True,  # trims leading/trailing silence
        beam_size=beam_size,
        # Each utterance is an independent clip here, so carrying decoded
        # text forward between segments buys nothing and is a known cause of
        # repetition loops on short, noisy input.
        condition_on_previous_text=False,
        # Nudges Whisper to recognize common software/requirements
        # terms correctly even when they're spoken mid-sentence in
        # Hindi or Gujarati (code-switching is where ASR tends to
        # mishear things like "OTP" as "O2B").
        initial_prompt=(
            "Meeting about software requirements. Terms that may come up: "
            "OTP, login, signup, API, database, admin panel, dashboard, "
            "UPI, payment, authentication, backend, frontend."
        ),
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    language, probability = forced if forced else (info.language, info.language_probability)
    elapsed = time.monotonic() - t0
    logger.info(
        "whisper[%s]: transcribed %.2fs of audio in %.2fs (beam_size=%d, lang=%s%s)",
        device, len(audio) / _EXPECTED_SAMPLE_RATE, elapsed, beam_size, language,
        " forced" if forced else " auto",
    )
    return text, language, probability


async def transcribe_utterance(raw_pcm16: bytes) -> TranscriptResult:
    """
    Transcribes one complete utterance (audio between "start speaking" and
    "end of utterance" signals from the client) and auto-detects its language.
    """
    model = await get_model()
    audio = pcm16_bytes_to_float32(raw_pcm16)

    try:
        text, language, language_probability = await asyncio.to_thread(
            _run_transcribe, model, audio, _active_device
        )
    except Exception as e:  # noqa: BLE001 — CUDA runtime failure: fall back to CPU and retry once
        if _active_device != "cuda":
            raise  # already on CPU — a real failure, not a GPU issue, don't swallow it
        logger.warning("whisper[cuda]: transcribe failed at runtime (%s) — retrying on CPU.", e)
        cpu_model = await _fall_back_to_cpu()
        text, language, language_probability = await asyncio.to_thread(
            _run_transcribe, cpu_model, audio, _active_device
        )

    return TranscriptResult(text=text, language=language, language_probability=language_probability)