"""
Live test: transcribe a real WAV file with Whisper (local) and Sarvam (cloud),
measure latency + accuracy for each.

Run from backend/: python scripts/latency_test.py [path-to-wav]
"""
import asyncio
import io
import os
import sys
import time
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")  # Hindi/Gujarati text on a cp1252 console

from app.config import settings
from app.transcription import asr, whisper_service


def wav_to_pcm16(path: str) -> bytes:
    with wave.open(path, "rb") as wav:
        assert wav.getframerate() == 16000, f"expected 16kHz, got {wav.getframerate()}"
        return wav.readframes(wav.getnframes())


async def main(path: str):
    pcm = wav_to_pcm16(path)
    print(f"\n=== audio: {path} ({len(pcm) / 32000:.2f}s) ===")

    # --- Whisper (local) ---
    device = await whisper_service.ensure_model_loaded()
    print(f"whisper device: {device}")
    t0 = time.perf_counter()
    result = await asr.transcribe(pcm)
    t_whisper = time.perf_counter() - t0
    print(f"WHISPER  [{result.provider}] {t_whisper:.2f}s | lang={result.language} ({result.language_probability:.2f})")
    print(f"  text: {result.text!r}")
    print(f"  english: {result.english_text!r}")

    # --- Sarvam (cloud) ---
    sarvam = asr.SarvamProvider()
    if sarvam.is_configured:
        try:
            t0 = time.perf_counter()
            wav_bytes = asr.pcm16_to_wav_bytes(pcm)
            payload = await sarvam._post("/speech-to-text", wav_bytes, settings.sarvam_model, mode="translate")
            t_sarvam = time.perf_counter() - t0
            english = asr._first_string(payload, asr._TEXT_KEYS)
            lang = asr.normalise_language(asr._first_string(payload, asr._LANGUAGE_KEYS))
            print(f"SARVAM   {t_sarvam:.2f}s | lang={lang}")
            print(f"  english: {english!r}")
            print(f"  raw payload keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload)}")
        except Exception as e:
            print(f"SARVAM FAILED: {e}")
    else:
        print("SARVAM: no key configured")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("usage: python scripts/latency_test.py <file.wav>")
        sys.exit(1)
    asyncio.run(main(path))
