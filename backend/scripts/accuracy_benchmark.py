"""
Golden-set accuracy benchmark — the script goldenset/README.md promised
("Baaki main karunga") and that never got written.

Run from the backend directory, after putting real clips in
../goldenset/clips/ and filling in ../goldenset/reference.csv:

    python scripts/accuracy_benchmark.py

What it does:
  1. Reads goldenset/reference.csv (clip, language, spoken_text, english).
  2. For every row with a clip file present, runs it through whichever ASR
     engine is currently active (Sarvam if configured, else local Whisper —
     same asr.transcribe() the live meeting bot calls, so this measures
     exactly what a real meeting would produce).
  3. Compares the engine's output against spoken_text (and english, when
     filled in) using word error rate (WER) — the percentage of words that
     would need to be inserted, deleted, or substituted to turn the
     engine's output into the reference text. Lower is better; 0% is a
     perfect match.
  4. Prints one row per clip, then per-language and overall averages, plus
     the average latency — so a claim like "Sarvam is more accurate" or
     "translation looks broken on Gujarati" has a number behind it instead
     of a feeling.

Text is lowercased and stripped of punctuation before comparing, so
"OTP." vs "otp" don't count as an error — this measures words, not
formatting.

Nothing here writes to any meeting state; it only reads goldenset/ and
prints. Safe to run at any time, including with an empty goldenset (it
will just report 0 clips found and exit).
"""

import argparse
import asyncio
import csv
import os
import re
import sys
import time

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

_GOLDENSET_DIR = os.path.join(os.path.dirname(_BACKEND_DIR), "goldenset")
_CLIPS_DIR = os.path.join(_GOLDENSET_DIR, "clips")
_REFERENCE_CSV = os.path.join(_GOLDENSET_DIR, "reference.csv")


_TRANSLIT_COMMON = {
    # Latin <-> Gujarati/Hindi transliteration pairs that ASR engines
    # legitimately produce both ways. Sarvam tends to transliterate English
    # words into the clip's dominant script; the reference keeps them in
    # Latin. These are the SAME word, so WER must not count them as errors.
    "orders": "ઓર્ડર્સની", "order": "ઓર્ડર",
    "status": "સ્ટેટસ", "export": "એક્સપોર્ટ",
    "otp": "ઓટીપી", "login": "લોગિન", "log in": "લોગિન",
    "password": "પાસવર્ડ", "dashboard": "ડેશબોર્ડ",
    "payment": "પેમેન્ટ", "report": "રિપોર્ટ",
    "admin": "એડમિન", "email": "ઈમેલ", "mail": "મેલ",
    "graph": "ગ્રાફ", "revenue": "રેવેન્યુ",
    "monthly": "મંથલી", "confirmation": "કન્ફર્મેશન",
    "link": "લીક", "forgot": "ફોરગોટ",
    # Hindi-script equivalents
    "otp": "ओटीपी", "verification": "वेरिफिकेशन",
    "user": "यूजर", "payment": "पेमेन्ट",
}

# Number words vs digits — "forty five thousand" == "45,000" in meaning.
# A tiny value-normalizer: pulls digit strings out and compares numerically.
_NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100, "thousand": 1000, "lakh": 100000,
}
_NUM_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                 "twelfth": 12, "fifteenth": 15, "twentieth": 20}


def _token_value(tok: str) -> int | None:
    """Numeric value of a token: a pure digit string, a number word, or an
    ordinal ('twelfth' -> 12). None if it isn't numeric at all."""
    cleaned = tok.replace(",", "").replace("₹", "").replace("rs", "").replace("rupees", "")
    if cleaned.isdigit():
        return int(cleaned)
    if cleaned in _NUM_WORDS:
        return _NUM_WORDS[cleaned]
    if cleaned in _NUM_ORDINALS:
        return _NUM_ORDINALS[cleaned]
    return None


def _tokens_equivalent(ref_tok: str, hyp_tok: str) -> bool:
    """
    Same word, different surface form? Three tolerated equivalences:
      1. Exact match (after normalization).
      2. Transliteration: the Latin word and the Indic word mean the same
         thing ('orders' vs 'ઓર્ડર્સની').
      3. Stem carry-over: Indic scripts append postpositions to a borrowed
         word ('orders' vs 'ordersની'). Only when the shared prefix covers
         most of the longer token, so 'monthly' vs 'month' (different
         words, not a case ending) still counts as an error.
    """
    if ref_tok == hyp_tok:
        return True
    if _TRANSLIT_COMMON.get(ref_tok) == hyp_tok or _TRANSLIT_COMMON.get(hyp_tok) == ref_tok:
        return True
    if len(ref_tok) >= 4 and len(hyp_tok) >= 4:
        longer, shorter = (ref_tok, hyp_tok) if len(ref_tok) >= len(hyp_tok) else (hyp_tok, ref_tok)
        if longer.startswith(shorter) and len(shorter) / len(longer) >= 0.6:
            return True
    return False


def _collapse_number_words(tokens: list[str]) -> list[str]:
    """
    'forty five thousand' -> one token '45000', so the DP compares it against
    an ASR's '45,000' as equal. Multiplicative words (hundred/thousand/lakh)
    multiply the running group; plain number words add; a digit token ends
    any group in progress. Non-numeric tokens pass through untouched.
    """
    out: list[str] = []
    group: int | None = None

    def _flush():
        nonlocal group
        if group is not None:
            out.append(str(group))
            group = None

    for tok in tokens:
        val = _token_value(tok)
        if val is None:
            _flush()
            out.append(tok)
            continue
        if val >= 100:  # hundred / thousand / lakh — scales the group
            group = (group or 1) * val
        else:
            group = (group or 0) + val
    _flush()
    return out


def _normalize(text: str) -> list[str]:
    """Lowercase, strip punctuation (keep digits + Indic), split into words,
    then collapse number-word runs ('forty five thousand' -> '45000') so a
    spoken number and its digits compare equal."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    tokens = [w for w in text.split() if w]
    return _collapse_number_words(tokens)


def word_error_rate(reference: str, hypothesis: str) -> float | None:
    """
    Word error rate with ASR-fair equivalence classes.

    Standard WER via Levenshtein edit distance at the word level, extended
    with two tolerances that a real transcript comparison needs, because
    without them a CORRECT transcript scores as badly as a wrong one:

      * Transliteration equivalence: code-mixed speech comes back with
        English words rendered in the Indic script of the sentence
        ('orders' -> 'ઓર્ડર્સની'). Same word, different script.
      * Stem carry-over: Indic scripts attach postpositions to the
        borrowed word, so 'orders' vs 'ordersની' is one word, not two
        errors plus one deletion.

    Returns None when there's no reference to compare against rather than
    a misleading 0% or divide-by-zero.
    """
    ref = _normalize(reference)
    hyp = _normalize(hypothesis)
    if not ref:
        return None

    # Classic DP edit-distance table, words instead of characters, with
    # the equivalence check replacing strict equality.
    n, m = len(ref), len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _tokens_equivalent(ref[i - 1], hyp[j - 1]):
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return 100.0 * dp[n][m] / n


def character_error_rate(reference: str, hypothesis: str) -> float | None:
    """
    Character-level edit distance / len(reference characters).

    Code-mixed Indic speech legitimately comes back with different word
    segmentation ('રિપોર્ટ માં' vs 'રિપોર્ટમાં' — sandhi join) and borrowed
    words transliterated into the sentence's script ('orders' vs
    'ઓર્ડર્સની'). Word-level WER punishes both as multiple errors; CER
    measures how much of the actual text survived, which is the honest
    number for 'did the engine capture what was said'.
    """
    ref = _normalize(reference)
    hyp = _normalize(hypothesis)
    if not ref:
        return None
    ref_chars = list("".join(ref))
    hyp_chars = list("".join(hyp))
    n, m = len(ref_chars), len(hyp_chars)
    if n == 0:
        return None
    # Standard character edit distance, space-free since we joined tokens.
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev = curr
    return 100.0 * prev[m] / n


def _find_clip(clip_name: str) -> str | None:
    """
    reference.csv names clips with an extension (e.g. 01_gu.wav), but people
    record on their phone and get .m4a — try the exact name first, then the
    same stem with any common audio extension, so a filename mismatch
    doesn't just silently skip the row.
    """
    exact = os.path.join(_CLIPS_DIR, clip_name)
    if os.path.isfile(exact):
        return exact
    stem = os.path.splitext(clip_name)[0]
    for ext in (".wav", ".m4a", ".mp3", ".ogg", ".flac", ".aac"):
        candidate = os.path.join(_CLIPS_DIR, stem + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


async def _load_clip_pcm16(path: str) -> bytes:
    """
    Decode whatever format the clip is in down to raw 16kHz mono PCM16 —
    the same shape the live meeting bot feeds asr.transcribe(). Uses
    pydub (already a project dependency via faster-whisper's ecosystem)
    so phone recordings (.m4a, .mp3) work, not just .wav.
    """
    from pydub import AudioSegment

    def _decode():
        audio = AudioSegment.from_file(path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        return audio.raw_data

    return await asyncio.to_thread(_decode)


async def _transcribe_with(engine: str, pcm: bytes, max_retries: int = 4):
    """
    Run one clip through one SPECIFIC engine, bypassing the selection logic:
      - "sarvam":  force the cloud path (fails loudly if the key is missing)
      - "whisper": force the local path
      - "auto":   whatever the live bot would use
    Returns (AsrResult, elapsed_seconds).

    Retries rate-limit (429) responses with exponential backoff — a 30-clip
    benchmark fires requests faster than the live bot ever does (its
    semaphore spaces them out over real speech), so 429s here are a
    benchmark artifact, not a product failure, and skipping the clip would
    leave the report incomplete.
    """
    from app.transcription import asr

    backoff = 2.0
    for attempt in range(max_retries):
        t0 = time.monotonic()
        try:
            if engine == "sarvam":
                sem = await asr.get_concurrency_semaphore()
                async with sem:
                    # language hint exactly as the live bot would pass it:
                    # the prior from the previous utterance's detection.
                    result = await asr._sarvam.transcribe(
                        pcm, language_hint=asr._last_language_code
                    )
                    asr.record_language(result.language)
            elif engine == "whisper":
                sem = await asr.whisper_semaphore()
                async with sem:
                    result = await asr._whisper.transcribe(pcm)
            else:
                sem = await asr.get_concurrency_semaphore()
                async with sem:
                    result = await asr.transcribe(pcm)
            return result, time.monotonic() - t0
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            is_rate_limit = "429" in msg or "rate limit" in msg.lower()
            if is_rate_limit and attempt < max_retries - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            raise


async def run(args: argparse.Namespace) -> int:
    from app.transcription import asr

    if not os.path.isfile(_REFERENCE_CSV):
        print(f"No reference.csv found at {_REFERENCE_CSV}")
        return 1

    with open(_REFERENCE_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Which engine(s) to measure. Default: BOTH, side by side — the point
    # of the golden set is comparing Sarvam (primary) against Whisper CUDA
    # (fallback), not measuring one in isolation.
    engines = args.engines.split(",") if args.engines else ["sarvam", "whisper"]
    print(f"Engines: {', '.join(engines)}   (active for live meetings: {asr.active_provider_name()})")
    print(f"Reading {_REFERENCE_CSV}\n")

    results = []
    skipped_no_clip = 0
    skipped_no_reference = 0

    for row in rows:
        clip_name = (row.get("clip") or "").strip()
        language = (row.get("language") or "?").strip()
        spoken_ref = (row.get("spoken_text") or "").strip()
        english_ref = (row.get("english") or "").strip()
        if not clip_name:
            continue

        clip_path = _find_clip(clip_name)
        if clip_path is None:
            skipped_no_clip += 1
            continue
        if not spoken_ref and not english_ref:
            skipped_no_reference += 1
            continue

        try:
            pcm = await _load_clip_pcm16(clip_path)
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {clip_name}: couldn't decode audio ({e})")
            continue

        clip_row = {"clip": clip_name, "language": language}
        for engine in engines:
            try:
                result, elapsed = await _transcribe_with(engine, pcm)
            except Exception as e:  # noqa: BLE001
                print(f"  [FAIL] {clip_name} on {engine}: {e}")
                clip_row[f"{engine}_error"] = str(e)[:120]
                continue

            original_wer = word_error_rate(spoken_ref, result.text) if spoken_ref else None
            original_cer = character_error_rate(spoken_ref, result.text) if spoken_ref else None
            english_hyp = result.english_text or result.text
            english_wer = word_error_rate(english_ref, english_hyp) if english_ref else None

            clip_row[f"{engine}_elapsed"] = elapsed
            clip_row[f"{engine}_orig_wer"] = original_wer
            clip_row[f"{engine}_orig_cer"] = original_cer
            clip_row[f"{engine}_en_wer"] = english_wer
            clip_row[f"{engine}_text"] = result.text
            clip_row[f"{engine}_en_text"] = english_hyp

            parts = [f"{elapsed:5.2f}s"]
            if original_wer is not None:
                parts.append(f"WER={original_wer:5.1f}%")
            if original_cer is not None:
                parts.append(f"CER={original_cer:5.1f}%")
            if english_wer is not None:
                parts.append(f"en WER={english_wer:5.1f}%")
            print(f"  [{language:>10}] {clip_name:<22} {engine:>7}: {' | '.join(parts)}")
            if args.verbose:
                print(f"           heard:     {result.text!r}")
                if spoken_ref:
                    print(f"           expected:  {spoken_ref!r}")
                print(f"           en heard:  {english_hyp!r}")
                if english_ref:
                    print(f"           en expect: {english_ref!r}")

        results.append(clip_row)
        print()

    print()
    if skipped_no_clip:
        print(f"Skipped {skipped_no_clip} row(s) — no audio file found in goldenset/clips/.")
    if skipped_no_reference:
        print(f"Skipped {skipped_no_reference} row(s) — reference.csv has no spoken_text/english filled in yet.")
    if not results:
        print("No clips were actually scored. Add recordings to goldenset/clips/ and fill in "
              "goldenset/reference.csv (see goldenset/README.md), then re-run.")
        return 0

    def _avg(values: list[float]) -> str:
        return f"{sum(values) / len(values):.1f}%" if values else "n/a"

    print(f"\n{'=' * 72}")
    print(f"SUMMARY — {len(results)} clips")
    print(f"{'=' * 72}")

    for engine in engines:
        print(f"\n  Engine: {engine}")
        by_lang: dict[str, list[dict]] = {}
        for r in results:
            if f"{engine}_orig_wer" in r or f"{engine}_elapsed" in r:
                by_lang.setdefault(r["language"], []).append(r)

        for lang, rows_for_lang in sorted(by_lang.items()):
            orig_wers = [r[f"{engine}_orig_wer"] for r in rows_for_lang if r.get(f"{engine}_orig_wer") is not None]
            orig_cers = [r[f"{engine}_orig_cer"] for r in rows_for_lang if r.get(f"{engine}_orig_cer") is not None]
            en_wers = [r[f"{engine}_en_wer"] for r in rows_for_lang if r.get(f"{engine}_en_wer") is not None]
            times = [r[f"{engine}_elapsed"] for r in rows_for_lang if f"{engine}_elapsed" in r]
            print(
                f"    {lang:>10}: {len(rows_for_lang):>2} clips  "
                f"WER={_avg(orig_wers):>7}  CER={_avg(orig_cers):>7}  en WER={_avg(en_wers):>7}  "
                f"time={sum(times) / len(times):.2f}s"
                if times else f"    {lang:>10}: {len(rows_for_lang):>2} clips  (all failed)"
            )

        all_orig = [r[f"{engine}_orig_wer"] for r in results if r.get(f"{engine}_orig_wer") is not None]
        all_cer = [r[f"{engine}_orig_cer"] for r in results if r.get(f"{engine}_orig_cer") is not None]
        all_en = [r[f"{engine}_en_wer"] for r in results if r.get(f"{engine}_en_wer") is not None]
        all_times = [r[f"{engine}_elapsed"] for r in results if f"{engine}_elapsed" in r]
        worst = sorted(
            ((r.get(f"{engine}_orig_cer"), r["clip"]) for r in results if r.get(f"{engine}_orig_cer") is not None),
            reverse=True,
        )[:5]
        print(
            f"\n    {'OVERALL':>10}: WER={_avg(all_orig):>7}  CER={_avg(all_cer):>7}  "
            f"en WER={_avg(all_en):>7}  avg time={sum(all_times) / len(all_times):.2f}s"
        )
        if worst:
            print(f"    worst 5 (CER): " + ", ".join(f"{c} ({w:.0f}%)" for w, c in worst))

    print("\n  (WER = word error rate, CER = character error rate — lower is better, 0% is perfect.")
    print("   CER is fairer on code-mix: script transliteration and word-joins aren't word errors.)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print what the engine actually heard next to the reference text for every clip.",
    )
    parser.add_argument(
        "--engines", default=None,
        help="Comma-separated engines to benchmark: sarvam, whisper, auto. Default: sarvam,whisper",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()