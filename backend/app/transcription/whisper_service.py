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

Language detection is automatic: faster-whisper detects the spoken
language per segment when `language=None` is passed. This is what
lets a single meeting move between English, Hindi, and Gujarati
without any manual toggle.
"""

import asyncio
import logging
import os
import sys
import time

import numpy as np

# On Windows, pip-installed nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels
# place their DLLs under site-packages\nvidia\<pkg>\bin\, which isn't on
# the system PATH by default — ctranslate2 (which faster-whisper uses
# under the hood) can't find cublas64_12.dll / cudnn64_9.dll without
# this. (Confirmed path layout — Windows wheels use \bin\, not \lib\
# like the Linux wheels do.) If you installed CUDA Toolkit + cuDNN
# system-wide instead and they're already on PATH, this whole block is
# a harmless no-op.
if sys.platform == "win32":
    for _pkg_name in ("nvidia.cublas", "nvidia.cuda_nvrtc", "nvidia.cudnn"):
        try:
            _pkg = __import__(_pkg_name, fromlist=["__path__"])
            _bin_dir = os.path.join(_pkg.__path__[0], "bin")
            if os.path.isdir(_bin_dir):
                os.add_dll_directory(_bin_dir)
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


def _load_model_blocking(force_cpu: bool = False) -> tuple[WhisperModel, str]:
    """
    Runs on a worker thread (model loading is blocking). Tries CUDA first
    (unless force_cpu, e.g. because CUDA already failed once at runtime
    this session), falls back to CPU on any failure — wrong CUDA/cuDNN
    install, no GPU present, or the GPU running out of memory for this
    model size are all treated the same way: log it and fall back, never
    crash the app over it.
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
            logger.info("faster-whisper: using CUDA (model=%s)", settings.whisper_model_size)
            return model, "cuda"
        except Exception as e:  # noqa: BLE001 — any GPU failure (no CUDA, OOM, driver) falls back to CPU
            logger.warning(
                "faster-whisper: CUDA load failed (%s) — falling back to CPU with model=%s",
                e, settings.whisper_cpu_fallback_model_size,
            )

    model = WhisperModel(
        settings.whisper_cpu_fallback_model_size,
        device="cpu",
        compute_type=settings.whisper_compute_type,
    )
    logger.info("faster-whisper: using CPU (model=%s)", settings.whisper_cpu_fallback_model_size)
    return model, "cpu"


async def get_model() -> WhisperModel:
    global _model, _active_device
    if _model is None:
        async with _model_lock:
            if _model is None:  # re-check inside the lock
                # Model loading is CPU/IO-bound and blocking — run off the event loop.
                _model, _active_device = await asyncio.to_thread(_load_model_blocking, _cuda_runtime_broken)
    return _model


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


def _run_transcribe(model: WhisperModel, audio: np.ndarray, device: str) -> tuple[str, str, float]:
    t0 = time.monotonic()
    beam_size = settings.whisper_gpu_beam_size if device == "cuda" else settings.whisper_beam_size
    segments, info = model.transcribe(
        audio,
        language=None,  # auto-detect — this is the important part
        vad_filter=True,  # trims leading/trailing silence
        beam_size=beam_size,
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
    elapsed = time.monotonic() - t0
    logger.info(
        "whisper[%s]: transcribed %.2fs of audio in %.2fs (beam_size=%d)",
        device, len(audio) / _EXPECTED_SAMPLE_RATE, elapsed, beam_size,
    )
    return text, info.language, info.language_probability


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