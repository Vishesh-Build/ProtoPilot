"""
One-off live probe: does the configured GEMINI_API_KEY actually work from
THIS machine? Makes ONE cheap chat call to Gemini's OpenAI-compatible
endpoint and prints the HTTP status (401/403 = bad key, 200 = good) plus
the reply. Never prints the key value — only a masked summary.

Run from backend/:  python scripts/diag_gemini.py
"""

import asyncio

import httpx

from app.config import settings


def _mask(key: str | None) -> str:
    if not key:
        return "NOT set"
    return f"set (…{key[-4:]}, len={len(key)})"


async def probe_gemini() -> None:
    print("=== GEMINI ===")
    print("key:", _mask(settings.gemini_api_key))
    print("base_url:", settings.gemini_base_url)
    if not settings.gemini_api_key:
        print("No key — nothing to probe.")
        return
    model = settings.gemini_models.split(",")[0].strip()
    url = settings.gemini_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        # Generous, because gemini-2.5-flash "thinks" out of this same budget —
        # a tiny cap can return an empty 200, which would look like a failure
        # when the key is actually fine.
        "max_tokens": 512,
        "temperature": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(url, headers={"Authorization": f"Bearer {settings.gemini_api_key}"}, json=payload)
    except httpx.RequestError as e:
        print(f"NETWORK ERROR: {e.__class__.__name__}: {e!s}")
        return
    print(f"model={model}  HTTP {r.status_code}")
    if r.status_code >= 400:
        print("body:", r.text[:400])
        return
    try:
        data = r.json()
        msg = data["choices"][0]["message"].get("content")
        usage = data.get("usage", {})
        print("reply content:", repr(msg))
        print("usage:", usage)
    except Exception as e:  # noqa: BLE001
        print("could not parse reply:", e)


async def list_gemini_models() -> None:
    print("\n=== GEMINI /models (chat-capable ids) ===")
    if not settings.gemini_api_key:
        return
    url = settings.gemini_base_url.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url, headers={"Authorization": f"Bearer {settings.gemini_api_key}"})
    except httpx.RequestError as e:
        print(f"NETWORK ERROR: {e.__class__.__name__}: {e!s}")
        return
    if r.status_code >= 400:
        print(f"HTTP {r.status_code}:", r.text[:300])
        return
    data = r.json()
    entries = data.get("data") if isinstance(data, dict) else data
    ids = [e.get("id") for e in (entries or []) if isinstance(e, dict) and e.get("id")]
    # Just the generative "gemini-*" chat ids, newest-looking first.
    gemini_ids = sorted(i for i in ids if "gemini" in i.lower()
                        and not any(b in i.lower() for b in ("embed", "image", "tts", "audio", "vision")))
    for i in gemini_ids:
        print("  ", i)
    print(f"({len(ids)} total ids served)")


if __name__ == "__main__":
    asyncio.run(probe_gemini())
    asyncio.run(list_gemini_models())
