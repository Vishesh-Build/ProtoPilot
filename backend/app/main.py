import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, exports, health, livekit_router, llm_test, meetings, oauth, requirements
from app.db.database import init_models
from app.ws import generate, meeting

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ProtoPilot Backend", version="0.2.0")

# The Electron app always loads over http://localhost:5173 — the Vite dev
# server during development, and a small local static server (started in
# electron/main.js) serving the built app in a packaged release. Same origin
# both ways on purpose, so cookies/CORS behave identically in dev and prod.
# If you later deploy the backend somewhere real, add that frontend's actual
# origin here too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await init_models()


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
