"""
Preflight — prove what actually works BEFORE a meeting, not during one.

Run from the backend directory:

    python scripts/preflight.py

Every failure this script reports has already happened in a real meeting on
this project:

  * Both LLM providers answered "your model is gone" (NIM 410 for
    meta/llama-3.1-8b-instruct, EOL 2026-08-26; Groq 404 for
    llama-3.1-8b-instant, retired 2026-06-17). Translation, requirement
    extraction and the whole 9-agent pipeline stopped at once, and the
    Points panel stayed empty for a 30-minute meeting with no error
    visible anywhere in the UI.
  * CUDA loaded but died on first use ("cublas64_12.dll is not found"),
    silently latching transcription onto the CPU, where 5.28s of audio
    took 34.92s and the worst caption arrived 195.97s after it was spoken.
  * Whisper's language auto-detect picked Telugu for English speech.
  * A provider answered HTTP 200 with `"content": null` — a reasoning model
    that spent its whole token budget thinking — which reads downstream as
    "the meeting contained no requirements".

So this script asks each provider what it really serves today, sends one
tiny real request to each, checks that a JSON array comes back the way the
requirement extractor needs it, loads the actual Whisper model and times
one actual transcription. It prints a table and exits non-zero if anything
a demo depends on is broken.

Nothing here writes to any meeting state; it is safe to run at any time.
"""

import argparse
import asyncio
import json
import math
import os
import struct
import sys
import time

# Run from anywhere: config.py reads .env relative to the process cwd, so
# pin the cwd to backend/ before importing anything from app.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

OK, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"

_rows: list[tuple[str, str, str]] = []


def record(check: str, status: str, detail: str = "") -> None:
    _rows.append((check, status, detail))
    prefix = {OK: "  [ok]  ", FAIL: "  [FAIL]", WARN: "  [warn]", SKIP: "  [skip]"}[status]
    print(f"{prefix} {check}" + (f" — {detail}" if detail else ""), flush=True)


def section(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def tone_pcm16(seconds: float = 2.0, sample_rate: int = 16000, freq: float = 220.0) -> bytes:
    """
    A synthetic clip, so preflight needs no audio files checked into the repo.
    A tone is not speech, so an empty transcript is a perfectly good result —
    what is being tested is that the key is accepted, the endpoint exists, the
    model id is real, and how long the round trip takes.
    """
    frames = int(sample_rate * seconds)
    return b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * (i / sample_rate))))
        for i in range(frames)
    )


async def check_llm() -> None:
    """
    For each provider: is a key present, what does it serve today, are the
    configured candidate ids still among them, does one real (tiny) chat call
    come back, and does that answer parse as the JSON array the requirement
    extractor demands. The middle question is the one that was missing when a
    30-minute meeting produced zero requirement points; the last one is the
    difference between "a provider replied" and "the Points panel can fill".
    """
    section("LLM providers — translation, requirement extraction, 9-agent pipeline")
    try:
        from app.config import settings
        from app.llm.providers.base import ProviderError, pick_model, rank_chat_models
        from app.llm.router import llm_router
    except ImportError as e:
        record("llm imports", FAIL, f"{e} — run: pip install -r requirements.txt")
        return

    if settings.llm_mock_mode:
        record("LLM_MOCK_MODE", WARN, "true — the router returns canned text and never calls a provider")

    for provider in llm_router.providers:
        tag = provider.name
        if not provider.is_configured:
            record(f"{tag}: api key", SKIP, f"{tag.upper()}_API_KEY not set in backend/.env")
            continue

        served = await provider.list_models()
        if not served:
            record(
                f"{tag}: GET /models", WARN,
                "provider would not list its models — a retired id could not be auto-replaced",
            )
        else:
            alive = [c for c in provider.candidates if c in served]
            record(
                f"{tag}: GET /models", OK,
                f"{len(served)} models served, {len(alive)}/{len(provider.candidates)} configured ids alive",
            )
            # What this provider would fall back to if every configured id
            # were retired tomorrow. Printed so the preference order in
            # config.py stays an evidence-based choice instead of a guess.
            ranked = rank_chat_models(served)
            record(
                f"{tag}: chat models", OK if ranked else WARN,
                ("auto-pick order: " + ", ".join(ranked[:6])) if ranked
                else "none of the served ids look like a chat model",
            )
            if not alive:
                record(
                    f"{tag}: configured ids", WARN,
                    f"none of [{', '.join(provider.candidates)}] is served today — "
                    f"auto-pick would choose {pick_model(served, provider.candidates)!r}",
                )

        # Not max_tokens=8. Reasoning models (gpt-oss and friends) think in
        # tokens taken from this same budget, so a tiny budget returns
        # `content: null` with `finish_reason: "length"` — an HTTP 200 with no
        # answer in it, which is indistinguishable from a broken provider.
        # Ask for the real budget the pipeline uses.
        budget = max(256, int(settings.llm_default_max_tokens))
        t0 = time.monotonic()
        try:
            result = await provider.chat(
                [{"role": "user", "content": "Reply with exactly one word: ready"}],
                max_tokens=budget,
                temperature=0.0,
            )
        except ProviderError as e:
            record(f"{tag}: chat", FAIL, e.message)
            continue
        except Exception as e:  # noqa: BLE001 — preflight reports, never crashes
            record(f"{tag}: chat", FAIL, f"{type(e).__name__}: {e}")
            continue

        # `or ""` on purpose: a provider that answers 200 with content: null
        # used to crash this script on .strip(), which is a poor way to find
        # out that the model had nothing to say.
        reply = (result.text or "").strip()
        elapsed = time.monotonic() - t0
        if reply:
            record(
                f"{tag}: chat", OK,
                f"model={provider.model} answered in {elapsed:.2f}s -> {reply[:40]!r}",
            )
        else:
            record(
                f"{tag}: chat", WARN,
                f"model={provider.model} answered HTTP 200 in {elapsed:.2f}s but with no text — "
                f"a reasoning model can spend all {budget} tokens thinking; raise "
                f"LLM_DEFAULT_MAX_TOKENS or use a non-reasoning id",
            )
            continue

        # The one-word reply proves the key and the model id. It does not
        # prove the Points panel can fill, which needs strict JSON back.
        await _check_json_reply(provider, tag, budget)


async def _check_json_reply(provider, tag: str, budget: int) -> None:
    """
    The requirement extractor's whole contract is "reply with a JSON array
    and nothing else". A model can pass the one-word probe and still fail
    this — chatty preambles, markdown fences, or a reasoning model that runs
    out of budget mid-array — and every one of those shows up in the UI as a
    Points panel that simply stays empty.
    """
    from app.llm.providers.base import ProviderError

    prompt = (
        "Extract requirements from this meeting line and reply with a JSON array "
        'of objects with keys title, category, priority, confidence and nothing else. '
        'Line: "we need a login page with google sign-in".'
    )
    try:
        result = await provider.chat(
            [{"role": "user", "content": prompt}], max_tokens=budget, temperature=0.0,
        )
    except ProviderError as e:
        record(f"{tag}: json reply", WARN, f"{e.message} — requirement extraction would fail here")
        return
    except Exception as e:  # noqa: BLE001
        record(f"{tag}: json reply", WARN, f"{type(e).__name__}: {e}")
        return

    text = (result.text or "").strip()
    body = text
    if body.startswith("```"):  # ```json fences are the usual offender
        body = body.strip("`")
        body = body.split("\n", 1)[-1] if "\n" in body else body
        body = body.rsplit("```", 1)[0]
    start, end = body.find("["), body.rfind("]")
    if start == -1 or end <= start:
        record(
            f"{tag}: json reply", WARN,
            f"no JSON array in the answer -> {text[:60]!r} — extraction would find no points",
        )
        return
    try:
        points = json.loads(body[start:end + 1])
    except ValueError as e:
        record(f"{tag}: json reply", WARN, f"array did not parse ({e}) -> {text[:60]!r}")
        return
    fenced = "" if text.startswith("[") else " (wrapped in prose/fences, extractor strips them)"
    record(
        f"{tag}: json reply", OK,
        f"{len(points)} requirement(s) parsed from {result.model}{fenced}",
    )


async def check_sarvam() -> None:
    """
    Sarvam's response envelope was verified against the current API docs
    (docs.sarvam.ai/api-reference-docs/speech-to-text/apis/rest-api):
    /speech-to-text with model=saaras:v3 returns {"transcript", "language_code",
    "request_id"}. asr.py's parser looks for "transcript"/"language_code"
    first for exactly that reason, and falls back to older key names
    defensively in case Sarvam changes the envelope again.

    _post/_first_string are private on purpose — preflight is the one place
    that legitimately wants the raw envelope rather than a tidy AsrResult.
    """
    section("Sarvam ASR — primary transcription engine")
    try:
        from app.config import settings
        from app.transcription import asr
    except ImportError as e:
        record("sarvam imports", FAIL, f"{e} — run: pip install -r requirements.txt")
        return

    if not settings.sarvam_api_key:
        record(
            "SARVAM_API_KEY", SKIP,
            "not set in backend/.env — every utterance will be transcribed by local Whisper "
            "on this machine instead (free key: https://dashboard.sarvam.ai)",
        )
        return

    provider = asr.SarvamProvider()
    wav = asr.pcm16_to_wav_bytes(tone_pcm16(2.0))

    for label, path, model, mode in (
        ("speech-to-text (translate)", "/speech-to-text", settings.sarvam_model, "translate"),
        ("speech-to-text (transcribe)", "/speech-to-text", settings.sarvam_stt_model, "transcribe"),
    ):
        t0 = time.monotonic()
        try:
            payload = await provider._post(path, wav, model, mode=mode)
        except asr.AsrError as e:
            record(f"sarvam {label}", FAIL, str(e))
            continue
        except Exception as e:  # noqa: BLE001
            record(f"sarvam {label}", FAIL, f"{type(e).__name__}: {e}")
            continue

        keys = ", ".join(sorted(payload)) if isinstance(payload, dict) else type(payload).__name__
        record(
            f"sarvam {label}", OK,
            f"HTTP 200 in {time.monotonic() - t0:.2f}s, model={model}, top-level keys=[{keys}]",
        )

        text = asr._first_string(payload, asr._TEXT_KEYS)
        language = asr._first_string(payload, asr._LANGUAGE_KEYS)
        if text or language:
            record(
                f"sarvam {label}: parser", OK,
                f"transcript={text[:30]!r} language={language!r} — a tone has no words, so "
                f"empty text here is expected and harmless",
            )
        else:
            record(
                f"sarvam {label}: parser", WARN,
                "found neither a transcript nor a language code at any key asr.py knows about. "
                "That is ambiguous on a synthetic tone, so re-run with --audio <real clip.wav>; "
                "if it still finds nothing, add the real key names to asr._TEXT_KEYS / "
                "asr._LANGUAGE_KEYS using the key list above",
            )

    record(
        "sarvam concurrency", OK,
        f"{settings.max_concurrent_sarvam_requests} requests in flight; "
        f"include_original={settings.sarvam_include_original}",
    )


def load_wav_16k_mono(path: str) -> bytes:
    """
    Read a PCM WAV and hand back mono 16-bit 16kHz frames — exactly what the
    VAD and Whisper consume, so `--audio` accepts a normal recording instead
    of demanding a pre-converted one. Raises ValueError with a fix in the
    message.
    """
    import wave

    with wave.open(path, "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        raw = wav.readframes(wav.getnframes())

    if width != 2:
        raise ValueError(f"{width * 8}-bit audio — re-export as 16-bit PCM WAV")
    if channels == 1 and rate == 16000:
        return raw

    try:
        import audioop  # stdlib through 3.12; removed in 3.13
    except ImportError as e:
        raise ValueError(
            f"{channels}ch @ {rate}Hz and this Python has no audioop to convert it — "
            f"re-export as mono 16kHz"
        ) from e

    if channels == 2:
        raw = audioop.tomono(raw, 2, 0.5, 0.5)
    elif channels != 1:
        raise ValueError(f"{channels} channels — re-export as mono")
    if rate != 16000:
        raw, _ = audioop.ratecv(raw, 2, 1, rate, 16000, None)
    return raw


async def check_whisper(audio_path: str | None, skip: bool) -> None:
    """
    Loads the real model, reports which device it actually landed on, and
    times one real transcription. The device line is the important one: a
    silent CUDA -> CPU latch is what turned a 5s utterance into 35s of work
    and pushed one caption 196s behind the speaker.
    """
    section("Local Whisper — fallback transcription engine")
    if skip:
        record("whisper", SKIP, "--skip-whisper passed")
        return
    try:
        from app.config import settings
        from app.transcription import whisper_service
    except ImportError as e:
        record("faster-whisper import", FAIL, f"{e} — pip install faster-whisper")
        return

    t0 = time.monotonic()
    try:
        device = await whisper_service.ensure_model_loaded()
    except Exception as e:  # noqa: BLE001
        record("whisper model load", FAIL, f"{type(e).__name__}: {e}")
        return
    load_time = time.monotonic() - t0

    if device == "cuda":
        record(
            "whisper device", OK,
            f"CUDA, model={settings.whisper_model_size}, "
            f"beam_size={settings.whisper_gpu_beam_size}, loaded in {load_time:.1f}s",
        )
    else:
        record(
            "whisper device", WARN,
            f"CPU, model={settings.whisper_cpu_fallback_model_size}, "
            f"beam_size={settings.whisper_beam_size}, loaded in {load_time:.1f}s — "
            f"CUDA was unavailable or refused to load",
        )

    allowed = whisper_service.allowed_languages()
    record(
        "whisper languages", OK if allowed else WARN,
        ",".join(allowed) + " (misdetection outside this set is impossible)" if allowed
        else "no allow-list — full 99-language auto-detect, which picked Telugu for English speech",
    )

    if audio_path:
        try:
            pcm = load_wav_16k_mono(audio_path)
        except (OSError, ValueError, EOFError) as e:
            record("whisper audio", FAIL, f"{audio_path}: {e}")
            return
        synthetic = False
    else:
        pcm = tone_pcm16(3.0)
        synthetic = True

    seconds = len(pcm) / 32000  # 16000 samples/s * 2 bytes
    t0 = time.monotonic()
    try:
        result = await whisper_service.transcribe_utterance(pcm)
    except Exception as e:  # noqa: BLE001
        record("whisper transcribe", FAIL, f"{type(e).__name__}: {e}")
        return
    elapsed = time.monotonic() - t0

    device_now = whisper_service.active_device() or device
    if device_now != device:
        record(
            "whisper CUDA runtime", FAIL,
            f"the model loaded on CUDA but the first transcribe() failed, so it latched to "
            f"{device_now} — this is the cublas64_12.dll case. "
            f"Fix: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12",
        )

    ratio = elapsed / seconds if seconds else 0.0
    # `or ""` because an empty transcript is a legitimate result here (a tone
    # is not speech) and must not turn a report into a traceback.
    heard = (result.text or "").strip()
    detail = (
        f"{seconds:.1f}s of audio in {elapsed:.2f}s = {ratio:.1f}x real time on {device_now}"
        f" | lang={result.language} conf={result.language_probability:.2f} text={heard[:40]!r}"
    )
    if synthetic:
        # A tone is not speech, so the VAD filter may throw most of it away
        # and make this look far faster than a real meeting ever will.
        # Reporting it as a verdict would be a lie.
        record(
            "whisper warm-up", OK,
            detail + " — synthetic tone, so this is a floor and not a real-world number. "
            "Re-run with --audio <clip.wav> for a number you can trust",
        )
    elif ratio <= 1.0:
        record("whisper speed", OK, detail)
    elif ratio <= 3.0:
        record("whisper speed", WARN, detail + " — captions will visibly trail the speaker")
    else:
        record("whisper speed", FAIL, detail + " — a live meeting falls minutes behind at this rate")


def check_config() -> None:
    """
    Print the values actually in effect. This exists because backend/.env
    silently overrides every default in config.py: a tuning change was made
    in config.py, appeared to do nothing, and the reason was a stale line in
    .env. Reading the numbers back from settings is the only honest way to
    know what the process will really use.
    """
    section("Effective configuration (.env overrides config.py — these are the real values)")
    try:
        from app.config import settings
    except ImportError as e:
        record("config import", FAIL, str(e))
        return

    keyed = lambda value: "set" if value else "NOT set"  # noqa: E731 — never print the secret itself
    record("keys present", OK, (
        f"groq={keyed(settings.groq_api_key)}, nim={keyed(settings.nim_api_key)}, "
        f"openrouter={keyed(settings.openrouter_api_key)}, sarvam={keyed(settings.sarvam_api_key)}, "
        f"livekit={keyed(settings.livekit_api_key and settings.livekit_api_secret)}"
    ))
    record("asr_provider", OK, f"{settings.asr_provider!r} (auto = Sarvam when keyed, else Whisper)")
    record("vad", OK, (
        f"silence_timeout={settings.vad_silence_timeout_seconds}s, "
        f"aggressiveness={settings.vad_aggressiveness}"
    ))
    record("transcription concurrency", OK, (
        f"gpu={settings.max_concurrent_transcriptions}, cpu={settings.max_concurrent_transcriptions_cpu} "
        f"(the CPU value is forced in code, not read from .env, because two CPU transcriptions at "
        f"once make both slower)"
    ))


def verdict() -> int:
    section("Summary")
    width = max(len(check) for check, _, _ in _rows) if _rows else 0
    for check, status, _ in _rows:
        print(f"  {check.ljust(width)}   {status}")

    def has(prefix: str, status: str) -> bool:
        return any(c.startswith(prefix) and s == status for c, s, _ in _rows)

    llm_ready = any(c.endswith(": chat") and s == OK for c, s, _ in _rows)
    points_ready = any(c.endswith(": json reply") and s == OK for c, s, _ in _rows)
    empty_reply = any(c.endswith(": chat") and s == WARN for c, s, _ in _rows)
    llm_checked = not has("llm", SKIP)
    # Must match the label the Sarvam section actually records — which is
    # f"sarvam {label}" for label "speech-to-text (translate)". An earlier
    # spelling here ("sarvam speech-to-text-translate") matched no row ever
    # recorded, so this was always False and the summary claimed "local
    # Whisper" even when Sarvam had just answered 200. Compared exactly, so
    # the "…: parser" row cannot satisfy it on its own.
    sarvam_ready = any(c == "sarvam speech-to-text (translate)" and s == OK for c, s, _ in _rows)
    whisper_ready = has("whisper device", OK) or has("whisper device", WARN)
    fails = [c for c, s, _ in _rows if s == FAIL]

    print()
    print(f"  transcription: {'Sarvam (cloud)' if sarvam_ready else 'local Whisper' if whisper_ready else 'NOTHING WORKS'}")
    if not llm_checked:
        print("  requirement points / 9-agent pipeline: not checked (--skip-llm)")
    elif points_ready:
        print("  requirement points / 9-agent pipeline: working")
    elif llm_ready:
        # A provider talks but would not produce a parseable requirement
        # array — the exact shape of "the meeting ran and the panel stayed
        # empty", so it must not be reported as working.
        print("  requirement points / 9-agent pipeline: AT RISK — a provider answers, but no "
              "provider returned a parseable JSON array")
    else:
        print("  requirement points / 9-agent pipeline: DEAD — no LLM provider answered")

    todo: list[str] = []
    if llm_checked and not llm_ready:
        todo.append(
            "No LLM provider answered a chat request. Translation, requirement extraction and the "
            "whole 9-agent pipeline go through the same router, so the Points panel will stay empty "
            "and nothing on screen will say why. Check the FAIL lines above: a 404/410 means the "
            "model id retired (the provider now auto-picks a replacement, so a FAIL here means even "
            "GET /models refused), anything about a key means the key itself."
        )
    if empty_reply:
        todo.append(
            "A provider answered HTTP 200 with no text. That is a reasoning model (gpt-oss and "
            "friends) spending the whole max_tokens budget thinking before it writes anything "
            "visible. Raise LLM_DEFAULT_MAX_TOKENS in backend/.env — the value is a ceiling, not a "
            "spend — or put a non-reasoning id first in that provider's list in app/config.py."
        )
    if llm_checked and llm_ready and not points_ready:
        todo.append(
            "Every provider that answered failed the JSON-array probe, which is the requirement "
            "extractor's actual contract. Captions and translation would still work, but the Points "
            "panel would stay empty. See the 'json reply' lines above for what came back instead."
        )
    if has("SARVAM_API_KEY", SKIP):
        todo.append(
            "Add SARVAM_API_KEY to backend/.env (free key: https://dashboard.sarvam.ai). It moves "
            "transcription off this machine, is built for Gujarati/Hindi/English including "
            "code-mixed speech, and its translate endpoint returns English directly — which also "
            "deletes one LLM call per caption."
        )
    if has("whisper device", WARN) or has("whisper CUDA runtime", FAIL):
        todo.append(
            "CUDA is not usable, so Whisper fell back to the smaller CPU model. Fix with: "
            "pip install nvidia-cublas-cu12 nvidia-cudnn-cu12  (the DLLs ship in those wheels and "
            "whisper_service.py already adds their bin/ directories to the DLL search path)."
        )
    if has("whisper speed", FAIL):
        todo.append(
            "Local Whisper is slower than real time on this machine, which is unrecoverable in a "
            "live meeting: the queue grows for as long as anyone keeps talking. Sarvam or a working "
            "GPU is the only fix — no tuning gets there from here."
        )

    if todo:
        section("Do this before the demo")
        for i, item in enumerate(todo, 1):
            print(f"  {i}. {item}\n")

    if fails:
        print(f"\nFAILED: {len(fails)} check(s) — {', '.join(fails)}")
        return 1
    print("\nAll checks passed (warnings above are non-fatal).")
    return 0


async def run(args: argparse.Namespace) -> int:
    print(f"ProtoPilot preflight — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"backend: {_BACKEND_DIR}")

    # One dependency probe up front. Without it, a missing package turns into
    # four identical import failures and a "NOTHING WORKS" verdict that hides
    # the one-line cause.
    try:
        import app.config  # noqa: F401
    except ImportError as e:
        print(f"\nCannot import the backend at all: {e}")
        print("The dependencies aren't installed in this interpreter. From backend/, run:")
        print("    pip install -r requirements.txt")
        print("Nothing else in this report would mean anything until that succeeds.")
        return 1

    check_config()
    if args.skip_llm:
        section("LLM providers")
        record("llm", SKIP, "--skip-llm passed")
    else:
        await check_llm()
    await check_sarvam()
    await check_whisper(args.audio, args.skip_whisper)
    return verdict()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prove what actually works before a ProtoPilot demo.",
    )
    parser.add_argument(
        "--audio", metavar="CLIP.wav",
        help="a real recording to transcribe, so the Whisper timing means something "
             "(any PCM WAV — it is converted to mono 16kHz here)",
    )
    parser.add_argument("--skip-llm", action="store_true", help="don't call the LLM providers")
    parser.add_argument(
        "--skip-whisper", action="store_true",
        help="don't load the local model (the first load downloads a few hundred MB)",
    )
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()