import logging
import logging.handlers
import pathlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.api import admin, auth, exports, health, livekit_router, llm_test, meetings, oauth, requirements
from app.config import settings
from app.db.database import init_models
from app.ws import generate, meeting

# Logs go to the terminal as before AND to backend/protopilot.log, so a
# transcription problem can be looked at after the meeting instead of only
# while it scrolls past. Rotates at 5 MB, keeps 3 files; gitignored (*.log).
_LOG_FILE = pathlib.Path(__file__).resolve().parent.parent / "protopilot.log"
_file_handler = logging.handlers.RotatingFileHandler(_LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), _file_handler])

app = FastAPI(title="ProtoPilot Backend", version="0.3.0")

# The Electron app always loads over http://localhost:5173 — the Vite dev
# server during development, and a small local static server (started in
# electron/main.js) serving the built app in a packaged release. Same origin
# both ways on purpose, so cookies/CORS behave identically in dev and prod.
# EXTRA_CORS_ORIGINS adds any additional frontend hosts (env-configured).
_extra_origins = [o.strip() for o in settings.extra_cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *_extra_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Baseline security headers on every backend response. These are the
# cheap, zero-breakage ones; a full CSP is deliberately NOT set here
# because the API serves JSON only (no HTML of its own to frame or
# inject into) and the generated-prototype iframe is already isolated by
# its sandbox attribute in the frontend (allow-scripts allow-forms, no
# allow-same-origin).
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # The backend serves an API, never a frameable page.
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.on_event("startup")
async def on_startup():
    await init_models()

    # Meeting state (transcript, requirements, agent outputs) is written
    # through a store so a backend restart no longer loses the meeting, its
    # transcript, or the generated prototype. Two backends, chosen by
    # settings.meeting_store_backend:
    #   "sqlite"   -> local file (default; fine for local dev / a persistent disk)
    #   "postgres" -> the same managed Postgres as auth, so meeting state
    #                 survives redeploys on an ephemeral-disk host (Render/Fly).
    from app.meetings.session import session_registry

    if settings.meeting_store_backend == "postgres":
        from app.meetings.pg_store import init_pg_store
        store = init_pg_store(settings.database_url)
    else:
        from app.meetings.store import init_store
        store = init_store(settings.meeting_store_path)
    session_registry.set_store(store)
    from app.services.diagnostics import diagnostics_service
    diagnostics_service.initialize()


@app.on_event("shutdown")
async def on_shutdown():
    from app.livekit.bot_manager import bot_manager
    await bot_manager.stop_all()


app.include_router(health.router)
app.include_router(admin.router)
app.include_router(llm_test.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(livekit_router.router)
app.include_router(meeting.router)
app.include_router(requirements.router)
app.include_router(generate.router)
app.include_router(meetings.router)
app.include_router(exports.router)
 
 
@app.get("/reset-password")
async def root_reset_password_redirect(token: str = ""):
    return RedirectResponse(url=f"/auth/reset-password?token={token}")


@app.get("/verify-email")
async def root_verify_email_redirect(token: str = ""):
    return RedirectResponse(url=f"/auth/verify-email?token={token}")


@app.get("/p/{meeting_id}", response_class=HTMLResponse)
async def public_prototype_view(meeting_id: str):
    """
    Public 1-click shareable prototype link.
    Allows clients, stakeholders, and testers to open and interact with the
    generated prototype in any desktop or mobile browser without logging in.
    """
    from app.meetings.session import session_registry

    # Demo project fallback
    if meeting_id.lower() in ("demo", "demo-fintrack"):
        demo_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FinTrack AI — Smart Expense Analytics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; background: #0B0F19; color: #F3F4F6; }
    .glass { background: rgba(18, 24, 38, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .grad-btn { background: linear-gradient(135deg, #4A63E8, #00C88A); }
  </style>
</head>
<body class="p-4 md:p-8 min-h-screen">
  <header class="flex items-center justify-between pb-6 border-b border-gray-800">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl grad-btn flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">FT</div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">FinTrack AI</h1>
        <p class="text-xs text-gray-400">Autonomous SaaS Expense Optimization</p>
      </div>
    </div>
    <div class="flex items-center gap-3">
      <span class="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">● Live AI Engine</span>
      <button class="px-4 py-2 rounded-xl text-xs font-bold grad-btn text-white shadow-md hover:opacity-95 transition" onclick="alert('Exporting audit report...')">Download Audit</button>
    </div>
  </header>

  <div class="grid grid-cols-1 md:grid-cols-4 gap-4 my-6">
    <div class="glass p-5 rounded-2xl">
      <div class="text-xs text-gray-400 font-medium">Monthly Active Burn</div>
      <div class="text-2xl font-bold mt-1 text-white">$48,250</div>
      <div class="text-xs text-emerald-400 mt-2 font-semibold">↓ 14.2% from last month</div>
    </div>
    <div class="glass p-5 rounded-2xl">
      <div class="text-xs text-gray-400 font-medium">AI Identified Leakage</div>
      <div class="text-2xl font-bold mt-1 text-amber-400">$6,840</div>
      <div class="text-xs text-gray-400 mt-2">7 redundant subscriptions</div>
    </div>
    <div class="glass p-5 rounded-2xl">
      <div class="text-xs text-gray-400 font-medium">Autonomous Actions</div>
      <div class="text-2xl font-bold mt-1 text-indigo-400">12 Pending</div>
      <div class="text-xs text-gray-400 mt-2">3 auto-downgrades ready</div>
    </div>
    <div class="glass p-5 rounded-2xl">
      <div class="text-xs text-gray-400 font-medium">Projected Annual Savings</div>
      <div class="text-2xl font-bold mt-1 text-emerald-400">$82,080</div>
      <div class="text-xs text-emerald-400 mt-2 font-semibold">High confidence AI audit</div>
    </div>
  </div>

  <div class="glass p-6 rounded-2xl mt-6">
    <h2 class="text-sm font-bold uppercase tracking-wider text-gray-400 mb-4">Live Recommendation Queue</h2>
    <div class="space-y-3">
      <div class="flex items-center justify-between p-4 rounded-xl bg-gray-900/60 border border-gray-800/80">
        <div>
          <div class="text-sm font-semibold text-white">Consolidate Figma Enterprise Licenses</div>
          <div class="text-xs text-gray-400 mt-0.5">14 inactive seats detected over last 60 days</div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs font-bold text-emerald-400">Save $1,050/mo</span>
          <button class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white" onclick="this.innerText='Applied ✓'; this.disabled=true;">Execute</button>
        </div>
      </div>
      <div class="flex items-center justify-between p-4 rounded-xl bg-gray-900/60 border border-gray-800/80">
        <div>
          <div class="text-sm font-semibold text-white">AWS Unattached EBS Volumes Cleanup</div>
          <div class="text-xs text-gray-400 mt-0.5">42 zombie snapshots in us-east-1</div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs font-bold text-emerald-400">Save $420/mo</span>
          <button class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white" onclick="this.innerText='Applied ✓'; this.disabled=true;">Execute</button>
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""
        return HTMLResponse(content=demo_html)

    session = session_registry.get(meeting_id)
    if not session:
        return HTMLResponse(
            status_code=404,
            content="""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ProtoPilot — Prototype Not Found</title>
            <style>body{background:#0b0f19;color:#fff;font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center;}
            .box{background:#121826;padding:32px 40px;border-radius:18px;border:1px solid #1e293b;max-width:440px;}
            h1{font-size:20px;margin:0 0 10px;font-weight:700;}p{color:#94a3b8;font-size:13.5px;line-height:1.5;margin:0;}
            .btn{margin-top:20px;display:inline-block;padding:9px 18px;border-radius:10px;background:#4A63E8;color:#fff;text-decoration:none;font-size:12px;font-weight:600;}</style></head>
            <body><div class="box"><h1>Prototype Not Found</h1><p>The meeting session is either invalid or has expired from server memory.</p></div></body></html>"""
        )

    html_content = session.agent_outputs.get("prototype")
    if not html_content:
        return HTMLResponse(
            status_code=404,
            content="""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ProtoPilot — Prototype in Progress</title>
            <style>body{background:#0b0f19;color:#fff;font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center;}
            .box{background:#121826;padding:32px 40px;border-radius:18px;border:1px solid #1e293b;max-width:440px;}
            h1{font-size:20px;margin:0 0 10px;font-weight:700;}p{color:#94a3b8;font-size:13.5px;line-height:1.5;margin:0;}
            .spin{display:inline-block;width:32px;height:32px;border:3px solid rgba(255,255,255,0.1);border-top-color:#00C88A;border-radius:50%;animation:s 1s linear infinite;margin-bottom:16px;}
            @keyframes s{to{transform:rotate(360deg)}}</style></head>
            <body><div class="box"><div class="spin"></div><h1>Generating Prototype…</h1><p>The 9 AI workforce agents are actively constructing this prototype. Please refresh this page in a few seconds.</p></div></body></html>"""
        )

    return HTMLResponse(content=html_content)

