import logging
import logging.handlers
import pathlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, exports, health, livekit_router, llm_test, meetings, oauth, requirements
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

app = FastAPI(title="ProtoPilot Backend", version="0.2.0")

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


@app.on_event("shutdown")
async def on_shutdown():
    from app.livekit.bot_manager import bot_manager
    await bot_manager.stop_all()


app.include_router(health.router)
app.include_router(llm_test.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(livekit_router.router)
app.include_router(meeting.router)
app.include_router(requirements.router)
app.include_router(generate.router)
app.include_router(meetings.router)
app.include_router(exports.router)
