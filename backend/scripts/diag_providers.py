"""
One-off live diagnostic: what do Groq and NIM actually do from THIS machine
right now? Prints Groq's real rate-limit headers (the TPM/RPM budget the
pipeline is bumping into) and whether NIM answers a real chat call.

Run: python scripts/diag_providers.py
Reads .env via app.config.settings. Never prints key values.
"""

import asyncio
import json

import httpx

from app.config import settings


def _mask(key: str | None) -> str:
    if not key:
        return "NOT set"
    return f"set (…{key[-4:]}, len={len(key)})"


async def probe_groq() -> None:
    print("\n=== GROQ ===")
    print("key:", _mask(settings.groq_api_key))
    if not settings.groq_api_key:
        return
    model = settings.groq_models.split(",")[0].strip()
    url = settings.groq_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 20,
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(url, headers={"Authorization": f"Bearer {settings.groq_api_key}"}, json=payload)
    print(f"model={model}  HTTP {r.status_code}")
    rl = {k: v for k, v in r.headers.items() if "ratelimit" in k.lower() or k.lower() == "retry-after"}
    print("rate-limit headers:")
    for k in sorted(rl):
        print(f"   {k}: {rl[k]}")
    if r.status_code >= 400:
        print("body:", r.text[:300])


async def probe_nim() -> None:
    print("\n=== NIM ===")
    print("key:", _mask(settings.nim_api_key))
    print("base_url:", settings.nim_base_url)
    if not settings.nim_api_key:
        return
    model = settings.nim_models.split(",")[0].strip()
    url = settings.nim_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 20,
        "temperature": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(url, headers={"Authorization": f"Bearer {settings.nim_api_key}"}, json=payload)
    except httpx.RequestError as e:
        print(f"NETWORK ERROR: {e.__class__.__name__}: {e!s} (str empty? {not str(e).strip()})")
        return
    print(f"model={model}  HTTP {r.status_code}")
    if r.status_code >= 400:
        print("body:", r.text[:300])
    else:
        try:
            data = r.json()
            msg = data["choices"][0]["message"].get("content")
            print("reply content:", repr(msg))
        except Exception as e:  # noqa: BLE001
            print("could not parse reply:", e)


async def main() -> None:
    await probe_groq()
    await probe_nim()


if __name__ == "__main__":
    asyncio.run(main())
