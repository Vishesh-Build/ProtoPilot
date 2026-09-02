"""
Central configuration for the ProtoPilot backend.

Reads from environment variables (or a .env file, via pydantic-settings).
Keep all provider keys and tunables here — nothing should be hardcoded
in the router or provider modules.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM provider keys ----
    # Fallback order is fixed: NIM -> OpenRouter -> Groq.
    # A provider with no key configured is skipped automatically.
    nim_api_key: str | None = None
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "meta/llama-3.1-8b-instruct"

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    # ---- Router behavior ----
    llm_default_max_tokens: int = 700
    llm_default_temperature: float = 0.3
    llm_request_timeout_seconds: float = 30.0
    provider_cooldown_seconds: float = 60.0
    llm_mock_mode: bool = False

    # ---- Stitch (AI UI design tool) ----
    # Get a key from https://stitch.withgoogle.com -> profile -> Stitch
    # settings -> API key. Leave unset to keep the original LLM-generated
    # HTML prototype behavior (app/services/stitch_service.py falls back
    # automatically when this is None).
    stitch_api_key: str | None = None
    # Optional: pin generation to one existing Stitch project id instead of
    # auto-creating/caching one on first use.
    stitch_project_id: str | None = None
    # Default look used when the meeting's requirements don't specify a
    # color scheme or theme themselves. Change this one line any time you
    # want a different default aesthetic — no code changes needed.
    stitch_style_direction: str = (
        "dark, near-black background with an emerald green (#00E6A8) accent color"
    )

    # ---- Transcription ----
    # Model used when a GPU (CUDA) is available — bigger/more accurate,
    # since GPU inference is fast enough to afford it. RTX 2050 (4GB) etc.
    # handle "medium" fine in float16.
    whisper_model_size: str = "medium"
    whisper_gpu_compute_type: str = "float16"
    # Falls back to this smaller model on CPU (no GPU found, or the GPU
    # ran out of memory) so CPU-only mode stays fast rather than
    # accurate-but-slow. See app/transcription/whisper_service.py for the
    # actual CUDA-then-CPU fallback logic.
    whisper_cpu_fallback_model_size: str = "small"
    whisper_compute_type: str = "int8"
    # beam_size=5 (faster-whisper's own default) is noticeably slower on CPU
    # for little accuracy gain in a live-meeting setting — 3 is a good
    # speed/accuracy middle ground. Drop to 1 (greedy decoding) for the
    # fastest possible response if 3 still isn't fast enough on your hardware.
    # This is the CPU-fallback beam size — kept low so CPU-only mode stays
    # fast. GPU mode uses whisper_gpu_beam_size instead (higher, since a
    # GPU is fast enough to afford better accuracy without added lag).
    whisper_beam_size: int = 1
    whisper_gpu_beam_size: int = 5

    # ============================================================
    # ---- Auth / Users (cloud) ----
    # ============================================================
    # Async SQLAlchemy URL, e.g. for a free Neon Postgres project:
    #   postgresql+asyncpg://user:password@ep-xxxx.neon.tech/protopilot?ssl=require
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/protopilot"

    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    jwt_secret_key: str = "CHANGE-ME-in-.env-generate-a-real-64-byte-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 240
    refresh_token_expire_days: int = 30
    password_reset_token_expire_minutes: int = 30

    # Cookies must be Secure + SameSite=None for a cloud backend talking to
    # an Electron renderer on a different origin. Only disable `cookie_secure`
    # for local http:// testing.
    cookie_secure: bool = True
    cookie_domain: str | None = None  # e.g. ".protopilot.app" — leave None for local testing

    # ---- Outbound email (forgot-password links) ----
    # Any standard SMTP provider works (Gmail app password, Resend, SendGrid
    # SMTP relay, Mailgun SMTP, etc.) — this backend doesn't fake-send email;
    # if these aren't configured, /auth/forgot-password will return a clear
    # 500 instead of pretending an email went out.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str = "no-reply@protopilot.app"
    # Where the reset link should point — your Electron app's local server
    # or a hosted "reset password" page that then calls /auth/reset-password.
    password_reset_url_base: str = "http://localhost:5173/reset-password"

    # ---- OAuth (Google / GitHub) ----
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    # Where the backend sends the browser/webview after OAuth finishes.
    # In Electron this is typically a local dev server URL during dev, and
    # a custom protocol (e.g. protopilot://oauth-success) once packaged —
    # that switch happens in the Electron phase.
    oauth_success_redirect_url: str = "http://localhost:5173/?oauth=success"
    oauth_error_redirect_url: str = "http://localhost:5173/login?oauth=error"

    # ---- LiveKit (video call) ----
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    # Client-facing WebSocket URL, e.g. wss://your-project.livekit.cloud
    # (free self-serve project at https://cloud.livekit.io) or your own
    # self-hosted LiveKit server's URL.
    livekit_url: str = "wss://your-project.livekit.cloud"

    # How long (seconds) of silence ends a participant's utterance and sends
    # it to Whisper. Too short = sentences get cut mid-thought; too long =
    # noticeable transcript lag. Tune by ear once it's running.
    # 0.55 is roughly the shortest that still survives the natural pauses in
    # Hindi/Gujarati speech; below ~0.45 clauses start getting chopped into
    # fragments and ASR accuracy drops with them.
    vad_silence_timeout_seconds: float = 0.55
    # 0 (least aggressive) to 3 (most aggressive) — how strictly webrtcvad
    # treats audio as speech vs. non-speech.
    vad_aggressiveness: int = 2
    # How many participant utterances can be transcribed at once, across ALL
    # active meetings — keeps a burst of simultaneous speakers from saturating
    # the machine; extras queue instead of piling on at once.
    # At 2, a 3-4 person meeting spent real time just waiting for a slot, and
    # that wait is invisible in the logs because it happens before Whisper is
    # even called. Raise further only if the box can take it.
    max_concurrent_transcriptions: int = 4


settings = Settings()