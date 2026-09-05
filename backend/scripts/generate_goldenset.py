"""
Generates the golden-set clips via Sarvam's bulbul:v3 TTS, so the benchmark
has real speech to measure. Categories cover exactly what a real client
meeting contains (per goldenset/README.md): feature demands, screens,
payment, login, reports — not poetry.

  01-04  Gujarati            (clean)
  05-08  Hindi               (clean)
  09-12  English             (clean)
  13-16  Gujarati+Hindi mix
  17-20  Gujarati+English mix
  21-22  fast speech (Hindi/Gujarati, spoken quickly via longer dense text)
  23-24  short sentences
  25-26  numbers/names (amounts, dates, people names, product names)
  27-28  mild background noise (white noise mixed at ~-20dB)
  29-30  noisy + short (noise + short sentence)

Output: goldenset/clips/*.wav (22.05kHz mono from Sarvam, resampled here to
16kHz mono PCM16 WAV — the same shape the meeting bot consumes) and an
updated goldenset/reference.csv with spoken_text + english filled in.

Run from backend/:
    python scripts/generate_goldenset.py
"""

import asyncio
import base64
import csv
import io
import os
import sys
import time
import urllib.request
import wave
import urllib.parse

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)
os.chdir(_BACKEND_DIR)

from app.config import settings  # noqa: E402

_GOLDENSET = os.path.join(os.path.dirname(_BACKEND_DIR), "goldenset")
_CLIPS_DIR = os.path.join(_GOLDENSET, "clips")
_REF_CSV = os.path.join(_GOLDENSET, "reference.csv")

# ---------------------------------------------------------------------------
# What each clip says. Content = things clients actually say in requirement
# meetings. `speaker` rotates so all clips aren't one voice.
# English column = the intended MEANING (for translation-WER), not a word
# for word transliteration — this is how a human would write the reference.
# ---------------------------------------------------------------------------
CLIPS = [
    # --- Gujarati, normal pace (4) ---
    ("01_gu.wav", "gu", "priya",
     "અમારે લોગિન સ્ક્રીન પર ઈમેલ અને પાસવર્ડ બંને જોઈએ છે.",
     "We need both email and password on the login screen."),
    ("02_gu.wav", "gu", "aditya",
     "ડેશબોર્ડ પર દરેક યુઝરની પેમેન્ટ હિસ્ટ્રી દેખાવી જોઈએ.",
     "The dashboard should show every user's payment history."),
    ("03_gu.wav", "gu", "priya",
     "રિપોર્ટ ડાઉનલોડ કરવાનું બટન ઉપરના જમણા ખૂણામાં રાખો.",
     "Put the report download button in the top right corner."),
    ("04_gu.wav", "gu", "ritu",
     "એડમિન પેનલમાં બધા યુઝર્સની યાદી અને તેમનો સ્ટેટસ દેખાય.",
     "The admin panel should show all users in a list with their status."),

    # --- Hindi, normal pace (4) ---
    ("05_hi.wav", "hi", "aditya",
     "लॉगिन पेज पर ओटीपी वेरिफिकेशन भी होना चाहिए।",
     "The login page should also have OTP verification."),
    ("06_hi.wav", "hi", "priya",
     "पेमेंट गेटवे से रीफंड का ऑप्शन डायरेक्ट ऐप में दिखाना है।",
     "The refund option from the payment gateway should be shown directly in the app."),
    ("07_hi.wav", "hi", "ritu",
     "हर ट्रांजैक्शन की डिटेल रिपोर्ट में डेट और टाइम के साथ आनी चाहिए।",
     "Every transaction's details should appear in the report with date and time."),
    ("08_hi.wav", "hi", "aditya",
     "नोटिफिकेशन सेटिंग में यूजर खुद चुन सके कि कौन सी अलर्ट चाहिए।",
     "In notification settings the user should be able to choose which alerts they want."),

    # --- English, normal pace (4) ---
    ("09_en.wav", "en", "aditya",
     "We need a dashboard that shows monthly revenue and active users.",
     "We need a dashboard that shows monthly revenue and active users."),
    ("10_en.wav", "en", "priya",
     "The admin panel should let us export the user list as a CSV file.",
     "The admin panel should let us export the user list as a CSV file."),
    ("11_en.wav", "en", "ritu",
     "Please add a search bar on the orders page with filters by date.",
     "Please add a search bar on the orders page with filters by date."),
    ("12_en.wav", "en", "aditya",
     "The API should support pagination for large result sets.",
     "The API should support pagination for large result sets."),

    # --- Gujarati + Hindi code-mix (4) ---
    ("13_mix_gh.wav", "mix_gh", "priya",
     "લોગિન કરતા વખતे OTP वेरिफिकेशन જોઈએ છે, वरना यूજर गलत पેमेन્ટ કરશે.",
     "OTP verification is needed while logging in, otherwise the user will make wrong payments."),
    ("14_mix_gh.wav", "mix_gh", "aditya",
     "ડેશબોર્ડ पर हर यूજरनું स्कोर अને रीफंड स્ટેટસ दેખાવો.",
     "Show every user's score and refund status on the dashboard."),
    ("15_mix_gh.wav", "mix_gh", "ritu",
     "રિપોર્ટ डाउनलोड करने का बटन डેશબોર્� पर ही रাখો.",
     "Keep the report download button on the dashboard itself."),
    ("16_mix_gh.wav", "mix_gh", "aditya",
     "એડમિન पैनल में टीम के सब लोगोंને રोल आપવાનું આવશે.",
     "The admin panel will need to let us assign roles to the whole team."),

    # --- Gujarati + English code-mix (4) ---
    ("17_mix_ge.wav", "mix_ge", "priya",
     "લોગિન સ્ક્રીન પર forgot password નો લિંક પણ રાખો.",
     "Also keep a forgot password link on the login screen."),
    ("18_mix_ge.wav", "mix_ge", "aditya",
     "પેમેન્ટ કર્યા પછી confirmation email આવવો જોઈએ.",
     "A confirmation email should arrive after payment."),
    ("19_mix_ge.wav", "mix_ge", "ritu",
     "ડેશબોર્ડ પર monthly revenue નો graph દેખાડો.",
     "Show a graph of monthly revenue on the dashboard."),
    ("20_mix_ge.wav", "mix_ge", "priya",
     "રિપોર્ટ માં બધા orders ની status export કરો.",
     "Export the status of all orders in the report."),

    # --- fast speech (2): dense, longer sentences force quicker delivery ---
    ("21_fast_hi.wav", "fast_hi", "aditya",
     "जल्दी बताइए, पेमेंट गेटवे में कौन से मोड चाहिए, UPI, कार्ड, नेट बैंकिंग तीनों, और रीफंड का स्लैब भी बता दीजिए।",
     "Quickly tell me which payment gateway modes are needed, UPI, card, net banking, all three, and also tell us the refund slab."),
    ("22_fast_gu.wav", "fast_gu", "priya",
     "ઝડપથી કહો, લોગિન માં ઈમેલ, ઓટીપી, પાસવર્ડ ત્રણેય જોઈએ છે, અને ડેશબોર્ડ પર રિપોર્ટ પણ ડાયરેક્ટ ડાઉનલોડ થવો જોઈએ.",
     "Quickly, login needs email, OTP, password, all three, and the report on the dashboard should be directly downloadable too."),

    # --- short sentences (2) ---
    ("23_short_hi.wav", "short_hi", "aditya",
     "डार्क मोड भी चाहिए।",
     "Dark mode is also needed."),
    ("24_short_gu.wav", "short_gu", "priya",
     "બટન વાદળી રાખો.",
     "Keep the button blue."),

    # --- numbers/names (2) ---
    ("25_num_en.wav", "num_en", "aditya",
     "Rahul from Infosys approved a budget of forty five thousand rupees on August twelfth.",
     "Rahul from Infosys approved a budget of forty five thousand rupees on August twelfth."),
    ("26_num_hi.wav", "num_hi", "priya",
     "मीटिंग 15 अगस्त को दोपहर 3 बजे है, नेहा और आरव भी आएंगे।",
     "The meeting is on August 15 at 3 in the afternoon, Neha and Aarav will also come."),

    # --- mild background noise (2) ---
    ("27_noisy_gu.wav", "noisy_gu", "priya",
     "એડમિન પેનલમાં બધા યુઝર્સની યાદી અને તેમનો સ્ટેટસ દેખાય.",
     "The admin panel should show all users in a list with their status."),
    ("28_noisy_hi.wav", "noisy_hi", "aditya",
     "लॉगिन पेज पर ओटीपी वेरिफिकेशन भी होना चाहिए।",
     "The login page should also have OTP verification."),

    # --- noisy + short (2) ---
    ("29_noisy_short.wav", "noisy_short", "ritu",
     "રિપોર્ટ કાલે મોકલો.",
     "Send the report tomorrow."),
    ("30_noisy_short2.wav", "noisy_short2", "aditya",
     "मीटिंग कोई नहीं छोड़ेगा।",
     "No one will skip the meeting."),
]

NOISY_CLIPS = {"27_noisy_gu.wav", "28_noisy_hi.wav", "29_noisy_short.wav", "30_noisy_short2.wav"}
# Which speaker+language to request from Sarvam per clip language
_LANG_CODE = {
    "gu": "gu-IN", "hi": "hi-IN", "en": "en-IN",
    "mix_gh": "gu-IN",   # Gujarati-dominant mix: use the Gujarati voice
    "mix_ge": "gu-IN",
    "fast_hi": "hi-IN", "fast_gu": "gu-IN",
    "short_hi": "hi-IN", "short_gu": "gu-IN",
    "num_en": "en-IN", "num_hi": "hi-IN",
    "noisy_gu": "gu-IN", "noisy_hi": "hi-IN",
    "noisy_short": "gu-IN", "noisy_short2": "hi-IN",
}


def _tts_sync(text: str, lang: str, speaker: str) -> bytes:
    """One synchronous TTS call. Returns WAV bytes (whatever rate Sarvam picks)."""
    req = urllib.request.Request(
        "https://api.sarvam.ai/text-to-speech",
        data=urllib.parse.quote(
            __import__("json").dumps({"inputs": [text], "target_language_code": lang, "speaker": speaker})
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "api-subscription-key": settings.sarvam_api_key or "",
        },
        method="POST",
    )
    # urllib with a JSON body (not form-encoded) — redo properly:
    import json as _json
    req.data = _json.dumps({"inputs": [text], "target_language_code": lang, "speaker": speaker}).encode("utf-8")
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = _json.loads(resp.read().decode("utf-8"))
    audio_b64 = payload["audios"][0]
    return base64.b64decode(audio_b64)


def _resample_to_16k_mono(wav_bytes: bytes) -> bytes:
    """Sarvam TTS returns 22.05kHz mono WAV — the bot consumes 16kHz. Also
    used to inject noise for the noisy clips."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        rate, n = w.getframerate(), w.getnframes()
        ch, sw = w.getnchannels(), w.getsampwidth()
        data = w.readframes(n)
    assert ch == 1 and sw == 2, f"expected mono 16-bit, got {ch}ch {sw * 8}-bit"

    import array
    samples = array.array("h", data)

    # Resample by linear interpolation to 16 kHz.
    out_len = int(len(samples) * 16000 / rate)
    resampled = array.array("h", [0] * out_len)
    for i in range(out_len):
        pos = i * rate / 16000
        i0 = int(pos)
        frac = pos - i0
        s0 = samples[i0] if i0 < len(samples) else samples[-1]
        s1 = samples[i0 + 1] if i0 + 1 < len(samples) else s0
        resampled[i] = int(s0 + (s1 - s0) * frac)
    return resampled.tobytes()


def _mix_noise(pcm: bytes, noise_ratio_db: float = -20.0) -> bytes:
    """Adds low-level white noise (fan/AC-like) at the given dB below the
    speech peak — 'mild background noise', not destruction."""
    import array
    import random

    samples = array.array("h", pcm)
    peak = max((abs(s) for s in samples), default=1) or 1
    # -20dB below peak
    noise_amp = int(peak * (10 ** (noise_ratio_db / 20)))
    rng = random.Random(42)  # deterministic clips
    for i in range(len(samples)):
        samples[i] = max(-32768, min(32767, samples[i] + rng.randint(-noise_amp, noise_amp)))
    return samples.tobytes()


def _write_wav(path: str, pcm: bytes, rate: int = 16000) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


async def main() -> int:
    if not settings.sarvam_api_key:
        print("SARVAM_API_KEY not set — cannot generate TTS clips.")
        return 1

    os.makedirs(_CLIPS_DIR, exist_ok=True)

    rows = []
    for i, (fname, lang_tag, speaker, text, english) in enumerate(CLIPS, 1):
        out_path = os.path.join(_CLIPS_DIR, fname)
        try:
            wav_bytes = await asyncio.to_thread(_tts_sync, text, _LANG_CODE[lang_tag], speaker)
            pcm = await asyncio.to_thread(_resample_to_16k_mono, wav_bytes)
            if fname in NOISY_CLIPS:
                pcm = await asyncio.to_thread(_mix_noise, pcm)
            await asyncio.to_thread(_write_wav, out_path, pcm)
            rows.append({"clip": fname, "language": lang_tag, "spoken_text": text, "english": english})
            print(f"[{i:>2}/{len(CLIPS)}] {fname:<22} {len(pcm) / 32000:.1f}s ok")
        except Exception as e:  # noqa: BLE001
            print(f"[{i:>2}/{len(CLIPS)}] {fname:<22} FAILED: {e}")
            # tiny stagger to be polite to the API
        await asyncio.sleep(0.6)

    # Rewrite reference.csv with everything we actually generated.
    with open(_REF_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["clip", "language", "speaker", "spoken_text", "english"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\nWrote {len(rows)} clips to {os.path.relpath(_CLIPS_DIR, _BACKEND_DIR)}")
    print(f"Updated {os.path.relpath(_REF_CSV, _BACKEND_DIR)}")
    return 0 if len(rows) == len(CLIPS) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
