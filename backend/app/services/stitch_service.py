"""
Stitch integration — replaces the "ask a small free LLM to hand-write an
entire HTML/CSS/JS file" approach with a call to Google Stitch (Google
Labs' AI UI-design tool), which is purpose-built for generating
high-fidelity screens instead of asking a general chat model to
freehand a whole styled webapp.

Stitch is exposed as a remote MCP server (stitch.googleapis.com/mcp),
authenticated with an API key header (X-Goog-Api-Key). This module is a
small backend-only MCP client for the two tools we actually need:

    create_project(title)                    -> project_id
    generate_screen_from_text(projectId,      -> one or more screens,
        prompt, deviceType)                      each with real HTML

Get an API key from: https://stitch.withgoogle.com -> profile picture
(top right) -> Stitch settings -> API key section.

CONFIRMED response shape (from a live call — see stitch_debug_last_response.json
next to this file after any generation for the full raw JSON):

    {
      "projectId": "...",
      "outputComponents": [
        {"designSystem": {...}},                          # design tokens, no HTML
        {"design": {"screens": [
            {
              "title": "...",
              "screenshot": {"downloadUrl": "...(PNG image)"},
              "htmlCode": {"downloadUrl": "...", "mimeType": "text/html"},
              ...
            },
            ...  # Stitch generates several screens per call
        ]}},
        {"text": "..."},           # Stitch's own chat-style description
        {"suggestion": "..."},     # follow-up suggestions (ignored)
        ...
      ]
    }

The important gotcha: each screen has TWO download URLs —
`screenshot.downloadUrl` (a PNG image) and `htmlCode.downloadUrl` (the
actual HTML). Only `htmlCode.downloadUrl` is usable as HTML — fetching
the screenshot URL and treating it as HTML produces garbage (raw PNG
bytes rendered as text).

Since Stitch generates multiple screens per call, they're combined here
into ONE self-contained HTML file with a simple JS tab bar so the
pipeline still produces a single "prototype" output, same as before.

If STITCH_API_KEY isn't configured, or any step fails for any reason,
generate_prototype_html returns None — the caller (orchestrator.py)
falls back to the existing LLM-generated HTML path, so a Stitch outage
never hard-fails the whole pipeline.
"""

import asyncio
import json
import logging
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings

logger = logging.getLogger("protopilot.stitch")

STITCH_MCP_URL = "https://stitch.googleapis.com/mcp"

# Full raw responses get dumped here on every call (overwritten each time).
# The terminal's scrollback isn't reliable for a JSON payload this large —
# it truncates/duplicates on copy — so this file is the source of truth
# when debugging what Stitch actually returned.
_DEBUG_DUMP_PATH = Path(__file__).resolve().parents[2] / "stitch_debug_last_response.json"

# Cached in-process so we reuse one Stitch project across generations
# instead of creating a brand new (empty-history) project every time.
_cached_project_id: str | None = None


def _dump_debug(label: str, data) -> None:
    """Writes the full raw response to disk — see _DEBUG_DUMP_PATH above."""
    try:
        existing = {}
        if _DEBUG_DUMP_PATH.exists():
            existing = json.loads(_DEBUG_DUMP_PATH.read_text(encoding="utf-8"))
        existing[label] = data
        _DEBUG_DUMP_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001 — debug dump failing should never break generation
        logger.exception("Stitch: failed to write debug dump for %s", label)


def _tool_result_json(result):
    """
    MCP tool results come back as a list of content blocks. Stitch's
    tools return a JSON payload as a text block — find it and parse it.
    """
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return json.loads(block.text)
    raise RuntimeError("Stitch tool call returned no text content to parse")


async def _get_or_create_project(session: ClientSession) -> str:
    global _cached_project_id

    if settings.stitch_project_id:
        return settings.stitch_project_id
    if _cached_project_id:
        return _cached_project_id

    result = await session.call_tool("create_project", {"title": "ProtoPilot"})
    data = _tool_result_json(result)
    _dump_debug("create_project", data)

    # Stitch returns the resource name as "projects/{id}", not a bare
    # "projectId"/"id" field.
    project_id = data.get("projectId") or data.get("id") or data.get("project_id")
    if not project_id and data.get("name"):
        project_id = data["name"].rsplit("/", 1)[-1]
    if not project_id:
        raise RuntimeError(f"create_project didn't return a recognizable project id: {data}")

    _cached_project_id = project_id
    return project_id


def _build_stitch_prompt(context: str) -> str:
    """
    Turns the UI/API/Database agents' output into a design brief Stitch
    can work from, plus the product's default style direction — Stitch
    reads style instructions fine from plain English, unlike a raw HTML
    system prompt.

    The default color/theme direction is set once, in
    settings.stitch_style_direction (app/config.py) — edit that if you
    want every generation to default to a different look. If the
    requirements/context themselves mention a specific color scheme or
    theme (e.g. someone said "make it blue and white" in the meeting and
    that became a requirement), that explicit instruction is told to
    take priority over the default here.
    """
    return (
        "Design a premium, modern, production-level SaaS product UI based on "
        "the following product spec (screens, API endpoints, and data model). "
        "This should look like a real AI startup product, not a generic "
        "template.\n\n"
        f"{context}\n\n"
        "Style direction: minimal, futuristic, premium, clean, responsive, "
        "with subtle glassmorphism on cards/panels, smooth transitions, "
        "modern typography, rounded cards, and excellent spacing/whitespace. "
        "The layout must be fully responsive — use fluid widths, flexbox/"
        "grid, and sensible breakpoints so it looks correct on both "
        "desktop and mobile viewports, not just one fixed width. "
        "If the product spec above states or implies a specific color "
        "palette, theme, or brand direction, follow that instead of "
        "anything below — an explicit instruction in the spec always wins. "
        f"Otherwise, default to this look: {settings.stitch_style_direction}\n\n"
        "Invent a plausible product name — no placeholder branding, no "
        "lorem ipsum.\n\n"
        "Interactivity (important — this is a clickable prototype, not a "
        "static mock): every button, tab, icon, toggle, and form on the "
        "screen must have working inline JS so clicking it visibly does "
        "something — switch a tab, open/close a panel, update a number or "
        "list on the page with sample data, show a brief confirmation, etc. "
        "There is no real backend, so fake it with plain JS and sample data, "
        "but nothing should be a dead click with no visible response."
    )


_SPEC_TITLE_MARKERS = ("spec", "specification", "overview doc", "product doc")

# Injected into every Stitch screen before combining. Belt-and-suspenders on
# top of the interactivity instruction in the prompt above: even if Stitch
# forgets to wire up some button, this guarantees a click still gets a
# visible response instead of doing nothing. It only reacts to elements that
# don't already have their own onclick/href/type=submit handling, so it
# never fights with whatever Stitch actually wired up.
_CLICK_SAFETY_NET_SCRIPT = """
<script>
(function () {
  function alreadyHandled(el) {
    if (el.hasAttribute('onclick')) return true;
    if (el.tagName === 'A' && el.getAttribute('href') && el.getAttribute('href') !== '#') return true;
    if (el.tagName === 'BUTTON' && el.type === 'submit') return true;
    return false;
  }
  function showPing(el) {
    var ping = document.createElement('div');
    ping.textContent = '\\u2713';
    ping.style.cssText = 'position:absolute;pointer-events:none;font-size:11px;' +
      'color:#00E6A8;font-weight:700;opacity:0;transition:opacity .15s,transform .4s;' +
      'transform:translateY(0);z-index:99999;';
    var rect = el.getBoundingClientRect();
    ping.style.left = (rect.right - 14 + window.scrollX) + 'px';
    ping.style.top = (rect.top - 6 + window.scrollY) + 'px';
    document.body.appendChild(ping);
    requestAnimationFrame(function () { ping.style.opacity = '1'; });
    setTimeout(function () {
      ping.style.opacity = '0';
      ping.style.transform = 'translateY(-10px)';
    }, 400);
    setTimeout(function () { ping.remove(); }, 800);
    el.style.transition = el.style.transition || 'transform .12s';
    var prevTransform = el.style.transform;
    el.style.transform = 'scale(0.97)';
    setTimeout(function () { el.style.transform = prevTransform || ''; }, 120);
  }
  document.addEventListener('click', function (e) {
    var el = e.target.closest('button, a, [role="button"], [data-clickable]');
    if (!el || alreadyHandled(el)) return;
    showPing(el);
  }, true);
})();
</script>
"""


def _extract_screens(gen_data: dict) -> list[dict]:
    """
    Pulls the list of {"title": ..., "html_url": ...} out of the confirmed
    outputComponents shape. Skips screens with no htmlCode entry rather
    than guessing — screenshot.downloadUrl is deliberately NOT used here,
    it's a PNG image, not HTML.

    Also skips "spec"/summary screens Stitch sometimes generates alongside
    the real UI screens (e.g. a "Product Spec" screen that's just markdown
    text, not an actual interface) — those aren't useful as a prototype
    tab and would otherwise show up as a blank-looking text page.
    """
    screens: list[dict] = []
    for component in gen_data.get("outputComponents", []):
        design = component.get("design")
        if not design:
            continue
        for screen in design.get("screens", []):
            title = screen.get("title", "Screen")
            if any(marker in title.lower() for marker in _SPEC_TITLE_MARKERS):
                continue
            html_url = (screen.get("htmlCode") or {}).get("downloadUrl")
            if html_url:
                screens.append({"title": title, "html_url": html_url})
    return screens


def _combine_screens(screens: list[dict], htmls: list[str]) -> str:
    """
    Combines N standalone Stitch screen HTML documents into one file with
    a tab bar, using an <iframe srcdoc="..."> per screen rather than
    splicing each screen's <body> into a shared page.

    This matters: each Stitch screen is a fully self-contained document
    with its own element ids and its own inline <script> that queries
    those ids. Splicing multiple screens' bodies into ONE shared DOM
    causes id collisions between screens — a button's onclick script in
    screen 2 can end up querying an element that actually belongs to
    screen 1, silently breaking every interactive control. An iframe per
    screen keeps each screen's DOM and script fully isolated, so
    whatever Stitch generated keeps working exactly as it does when
    opened on its own.
    """
    def _inject_safety_net(html: str) -> str:
        if "</body>" in html:
            return html.replace("</body>", _CLICK_SAFETY_NET_SCRIPT + "</body>", 1)
        return html + _CLICK_SAFETY_NET_SCRIPT

    htmls = [_inject_safety_net(h) for h in htmls]

    if len(screens) == 1:
        return htmls[0]

    import html as _html_mod  # stdlib html-escaping, only needed here

    nav_buttons = "\n".join(
        f'<button class="pp-tab-btn" onclick="ppShowScreen({i})" id="pp-tab-btn-{i}">{_html_mod.escape(screen["title"])}</button>'
        for i, screen in enumerate(screens)
    )
    frames = "\n".join(
        f'<div class="pp-screen" id="pp-screen-{i}" style="display:{"block" if i == 0 else "none"}">'
        f'<iframe class="pp-frame" srcdoc="{_html_mod.escape(html)}"></iframe></div>'
        for i, html in enumerate(htmls)
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Prototype</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #0a0c10; }}
  .pp-tab-bar {{
    position: sticky; top: 0; z-index: 9999; display: flex; gap: 4px;
    padding: 10px 16px; background: #0a0c10; border-bottom: 1px solid rgba(255,255,255,0.08);
  }}
  .pp-tab-btn {{
    background: transparent; border: 1px solid rgba(255,255,255,0.15); color: #e2e2e8;
    padding: 6px 14px; border-radius: 8px; font-family: system-ui, sans-serif; font-size: 13px;
    cursor: pointer;
  }}
  .pp-tab-btn.active {{ background: #00e6a8; color: #04140f; border-color: #00e6a8; font-weight: 600; }}
  .pp-screen {{ height: calc(100vh - 44px); }}
  .pp-frame {{ width: 100%; height: 100%; border: 0; display: block; }}
</style>
</head>
<body>
<div class="pp-tab-bar">{nav_buttons}</div>
{frames}
<script>
function ppShowScreen(idx) {{
  document.querySelectorAll('.pp-screen').forEach(function(el, i) {{
    el.style.display = (i === idx) ? 'block' : 'none';
  }});
  document.querySelectorAll('.pp-tab-btn').forEach(function(el, i) {{
    el.classList.toggle('active', i === idx);
  }});
}}
ppShowScreen(0);
</script>
</body>
</html>"""


async def generate_prototype_html(context: str) -> str | None:
    """
    Generates screens in Stitch from the pipeline's UI/API/Database
    context and returns them combined into one HTML file. Returns None
    (never raises) if Stitch isn't configured or the call fails for any
    reason — the caller should fall back to the existing LLM path.

    Retries once on failure — Stitch is a BETA product and occasionally
    returns an empty/transient response; a single retry clears that
    without wasting a whole pipeline run on a one-off blip.
    """
    if not settings.stitch_api_key:
        return None

    last_error: Exception | None = None
    for attempt in range(1, 3):  # try once, then one retry
        try:
            return await _generate_prototype_html_once(context)
        except Exception as e:  # noqa: BLE001 — retry once, then fall back to LLM
            last_error = e
            logger.warning("Stitch attempt %d/2 failed: %s", attempt, e)
            if attempt < 2:
                await asyncio.sleep(2)

    logger.exception("Stitch generation failed after retry, falling back to LLM.", exc_info=last_error)
    return None


async def _generate_prototype_html_once(context: str) -> str | None:
    prompt = _build_stitch_prompt(context)
    headers = {"X-Goog-Api-Key": settings.stitch_api_key}
    logger.info("Stitch: starting generation (project_id_configured=%s)", bool(settings.stitch_project_id))

    async with streamablehttp_client(STITCH_MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            project_id = await _get_or_create_project(session)

            gen_result = await session.call_tool(
                "generate_screen_from_text",
                {"projectId": project_id, "prompt": prompt, "deviceType": "DESKTOP"},
            )
            gen_data = _tool_result_json(gen_result)
            _dump_debug("generate_screen_from_text", gen_data)

            screens = _extract_screens(gen_data)
            logger.info("Stitch: found %d screen(s) with html: %s", len(screens), [s["title"] for s in screens])

            if not screens:
                logger.warning("Stitch: no screens with htmlCode in response — see %s", _DEBUG_DUMP_PATH)
                return None

    htmls = []
    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
        for screen in screens:
            resp = await client.get(screen["html_url"])
            resp.raise_for_status()
            htmls.append(resp.text)

    combined = _combine_screens(screens, htmls)
    logger.info("Stitch: combined %d screen(s) into %d bytes of HTML.", len(screens), len(combined))
    return combined