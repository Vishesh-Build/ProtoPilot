"""
Live end-to-end proof: run the real 9-agent generation pipeline against the
real providers (Gemini -> Groq -> NIM) and report whether it reaches
pipeline_complete with a usable prototype. This is the demo-readiness check
the unit tests deliberately can't be — it spends real tokens and calls the
real Stitch MCP server, exactly like a live generation does.

Run from backend/:  python scripts/prove_pipeline.py
The prototype it produces is written next to this file so it can be opened.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Make `app` importable and read the real .env, whether this is launched as
# `python scripts/prove_pipeline.py` or `python -m scripts.prove_pipeline`
# from anywhere — same bootstrap preflight.py uses.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.agents.orchestrator import run_pipeline
from app.agents.state import AgentStatus

# A small but real spec so every agent has something concrete to work from.
REQUIREMENTS = [
    {"title": "Users can browse restaurants and their menus", "category": "Core", "priority": "High"},
    {"title": "Users can add items to a cart and place an order", "category": "Core", "priority": "High"},
    {"title": "Users can track order status in real time", "category": "Core", "priority": "Medium"},
    {"title": "Admins can manage menu items and prices", "category": "Admin", "priority": "Medium"},
]

OUTPUT_HTML = Path(__file__).resolve().parent / "prove_pipeline_output.html"


async def main() -> None:
    verdict = {"type": None, "message": ""}

    async def emit(event: dict) -> None:
        t = event.get("type")
        if t == "agent_log":
            print(f"   . [{event.get('agent')}] {event.get('message')}")
        elif t == "agent_output":
            print(f"   OK [{event.get('agent')}] produced {len(event.get('output') or '')} chars")
        elif t in ("pipeline_complete", "pipeline_failed"):
            verdict["type"] = t
            verdict["message"] = event.get("message", "")

    print("Running the real pipeline (Gemini -> Groq -> NIM)...\n")
    start = time.monotonic()
    states = await run_pipeline(REQUIREMENTS, emit)
    elapsed = time.monotonic() - start

    print("\n---- per-agent result ----")
    for aid, s in states.items():
        mark = "OK" if s.status == AgentStatus.COMPLETED else "XX"
        print(f"  {mark} {aid:10s} {s.status.name:10s} out={len(s.output or '')} chars")

    print(f"\nVERDICT: {verdict['type']}   (took {elapsed:.1f}s)")
    if verdict["message"]:
        print("message:", verdict["message"])

    proto = states.get("prototype")
    if proto and proto.status == AgentStatus.COMPLETED and proto.output:
        OUTPUT_HTML.write_text(proto.output, encoding="utf-8")
        print(f"prototype HTML -> {OUTPUT_HTML}  ({len(proto.output)} chars) — open it in a browser")
    else:
        print("NO prototype HTML produced")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:  # noqa: BLE001
        import traceback
        print("\nUNEXPECTED ERROR running the pipeline:")
        traceback.print_exc()
