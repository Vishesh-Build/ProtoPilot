"""
Translates transcript text to English using the same LLM router every
agent uses (Groq -> NIM -> OpenRouter). Kept as a separate, tiny function
so the prompt and token budget for this specific job stay easy to tune.

Note: when Sarvam is the active ASR provider it already returns English
(speech-to-text-translate), so this module is skipped entirely on that
path — see app/transcription/asr.py. It still runs for every utterance
transcribed locally by Whisper.
"""

import logging
import re

from app.config import settings
from app.llm.router import llm_router

logger = logging.getLogger("protopilot.translate")

# Whisper's language codes for the three languages ProtoPilot supports.
ENGLISH_CODES = {"en"}

TRANSLATE_SYSTEM_PROMPT = (
    "You are a translation engine embedded in a live meeting transcription tool. "
    "Translate the given text to natural, professional English.\n\n"
    "STRICT RULES:\n"
    "1. Your entire output must be in English, written in the Latin/Roman alphabet.\n"
    "2. Do NOT leave any words in Devanagari, Gujarati script, or any non-Latin script.\n"
    "3. If the input already contains English technical terms (e.g. OTP, API, login, "
    "database), keep those terms as-is in the English output.\n"
    "4. Output ONLY the translation — no notes, no quotes, no explanations, "
    "no repeating the original text.\n\n"
    "Example:\n"
    "Input: मुझे OTP based login system banana hai\n"
    "Output: I want to build an OTP-based login system."
)

# Devanagari (Hindi) and Gujarati Unicode block ranges — used to detect
# when the model failed to actually translate and just echoed the input.
_NON_LATIN_SCRIPT_PATTERN = re.compile(r"[\u0900-\u097F\u0A80-\u0AFF]")


def _looks_untranslated(text: str) -> bool:
    return bool(_NON_LATIN_SCRIPT_PATTERN.search(text))


async def translate_to_english(text: str, source_language: str) -> str:
    """
    Returns the English translation of `text`.
    If the detected language is already English, returns `text` unchanged
    and skips the LLM call entirely — no reason to spend tokens on it.
    """
    if source_language in ENGLISH_CODES or not text.strip():
        return text

    async def _attempt(emphasize: bool) -> str:
        system = TRANSLATE_SYSTEM_PROMPT
        if emphasize:
            system += (
                "\n\nIMPORTANT: Your previous attempt still contained non-English "
                "script. This time, output MUST be 100% English/Latin script, no exceptions."
            )
        result = await llm_router.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            # Sized for the ANSWER only — which is what a tight ceiling here
            # used to assume. Reasoning models (gpt-oss on Groq and NIM, which
            # is what the router picks today) spend this same budget thinking
            # before they emit a single visible character, so a one-line Hindi
            # caption came back with 281 characters of reasoning, no answer and
            # finish_reason=length. That failed BOTH providers, put them in
            # cooldown, and the next requirement extraction then reported
            # "no provider has an API key" for a session with two live keys.
            # The floor covers the thinking; the per-word term still keeps a
            # long utterance from being truncated.
            max_tokens=max(settings.llm_default_max_tokens, len(text.split()) * 6 + 200),
            temperature=0.1,
        )
        return result.text.strip()

    try:
        translated = await _attempt(emphasize=False)

        if _looks_untranslated(translated):
            logger.warning(
                "translation still non-English on first attempt (lang=%s), retrying once", source_language
            )
            translated = await _attempt(emphasize=True)

        if _looks_untranslated(translated):
            logger.warning("translation failed twice (lang=%s) — showing original with a marker", source_language)
            return f"[translation failed — showing original] {text}"

        return translated

    except RuntimeError as e:
        # Translation failing shouldn't take down the whole transcript feed —
        # fall back to showing the original text with a marker.
        logger.warning("translation failed (lang=%s): %s", source_language, e)
        return f"[translation unavailable] {text}"
