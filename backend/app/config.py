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
    # Fallback order is fixed: Groq -> NIM -> OpenRouter (see app/llm/router.py
    # for why Groq leads). A provider with no key configured is skipped.
    #
    # Each provider takes a COMMA-SEPARATED LIST of model ids, tried in order.
    # Hosted model ids get retired on a schedule — NIM answered 410 Gone for
    # meta/llama-3.1-8b-instruct (EOL 2026-08-26) and Groq answered 404 for
    # llama-3.1-8b-instant (retired 2026-06-17), which killed translation,
    # requirement extraction and the whole 9-agent pipeline at once. On a
    # "model gone" reply the provider now asks GET /v1/models what it really
    # serves and picks a replacement itself, so this list is a preference
    # order, not a single point of failure.
    #
    # Every id below is either already proven to work or was seen in a real
    # GET /v1/models answer from that provider — none of them is a guess. An
    # id that turns out to be gone costs one extra round trip at startup and
    # is then replaced automatically, so the strongest model leads the list
    # and the fast one sits directly behind it.
    nim_api_key: str | None = None
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    # openai/gpt-oss-20b leads because NIM's own /v1/models answered with it
    # on 2026-09-02, while both ids below it had stopped being served — with
    # them in front, every process start paid a 410 first.
    nim_models: str = (
        "openai/gpt-oss-20b,"
        "meta/llama-3.3-70b-instruct,"
        "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    )

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Left in the order it was already configured in: OpenRouter's free tier
    # uses a `:free` suffix per id, and inventing a suffixed id nobody has
    # seen served would be exactly the guess this whole mechanism replaced.
    # The llama-3.1-8b entry is gone because that family is the one that was
    # retired underneath us.
    openrouter_models: str = (
        "openai/gpt-oss-20b:free,"
        "meta-llama/llama-3.3-70b-instruct:free"
    )

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # gpt-oss-120b is the strongest free model on GroqCloud, so it leads: the
    # nine agents and the requirement extractor are judged on the quality of
    # what they write, not on shaving a second off it. gpt-oss-20b sits second
    # as the fast, higher-throughput fallback — a 429 on 120b is transient, so
    # the router simply moves on, and NIM serves gpt-oss-20b as well.
    groq_models: str = (
        "openai/gpt-oss-120b,"
        "openai/gpt-oss-20b,"
        "llama-3.3-70b-versatile"
    )

    # ---- Google Gemini (optional, but the best free budget available) ----
    # Groq's free tier is 8000 tokens/MINUTE. The 9-agent pipeline needs
    # ~25,000 tokens for one full run, so on Groq alone a generation spends
    # ~3 minutes just waiting for that per-minute budget to refill — which is
    # exactly the rate limit the live demo hit. Gemini's free tier has a far
    # larger per-minute token budget, so when a key is set the router leads
    # with Gemini (see app/llm/router.py) and the whole rate-limit problem
    # goes away; when it is NOT set this is skipped and the chain is exactly
    # what it was before (Groq -> NIM -> OpenRouter), so adding this is
    # zero-risk.
    #
    # Get a free key in ~2 min: https://aistudio.google.com/apikey — then put
    #   GEMINI_API_KEY=your-key-here
    # in backend/.env and restart the backend. Nothing else to change.
    #
    # This talks to Gemini's OpenAI-COMPATIBLE endpoint (…/v1beta/openai), so
    # it reuses the exact same OpenAICompatibleProvider as Groq/NIM — Bearer
    # auth, /chat/completions and /models all work unchanged.
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    # gemini-3.6-flash leads: it is Google's own recommended-stable flash
    # (the successor it names when the retired gemini-2.5-flash 404s) and,
    # being less bleeding-edge than 3.8, it is the one that reliably answers
    # 200 rather than 503 "high demand" — checked live 2026-09-04. The newer
    # gemini-3.8-flash and the gemini-flash-latest alias sit behind it. NOTE
    # the router only tries a *different* Gemini model on a 404/410 (model
    # retired) via GET /models rediscovery — a 503 on the lead fails the whole
    # Gemini provider through to Groq — so the lead must be a reliably-live id,
    # not merely the newest.
    gemini_models: str = (
        "gemini-3.6-flash,"
        "gemini-3.8-flash,"
        "gemini-flash-latest"
    )

    # ---- Router behavior ----
    # 700 was too tight to be safe. gpt-oss and other reasoning models think
    # in tokens drawn from this same budget, and when it runs out they return
    # `content: null` with `finish_reason: "length"` — an HTTP 200 carrying no
    # answer, which is exactly what an empty Points panel looked like from the
    # outside. This is a ceiling and not a spend, so the headroom is free.
    llm_default_max_tokens: int = 2048
    llm_default_temperature: float = 0.3
    llm_request_timeout_seconds: float = 30.0
    provider_cooldown_seconds: float = 60.0
    llm_mock_mode: bool = False

    # How long the router may honor a provider's Retry-After during the
    # GENERATION pipeline, in seconds. The meeting/caption path uses a short
    # ceiling (LLMRouter._RATE_LIMIT_MAX_WAIT, ~20s) because a caption that
    # lands half a minute late is useless — but a generation run is expected
    # to take a minute or two, so there it is fine, and far better, to pay a
    # provider's honest "wait 24s" than to fail the agent and cascade five
    # more. The live demo's Groq 429s asked for ~24s and the 20s ceiling
    # abandoned them; this is why generation gets its own, larger ceiling.
    # (With a Gemini key set this rarely matters — Gemini's budget means the
    # pipeline seldom hits a 429 at all — but it makes generation reliable
    # even on Groq+NIM alone.)
    llm_generation_max_rate_limit_wait: float = 45.0

    # How many generation-agent LLM calls may be in flight at once. The 9-agent
    # DAG has a wave that fires concurrent calls (ui + backend share one), and
    # on a free tier two provider calls landing in the same instant split that
    # tier's per-minute token budget between them — one wins and the other gets
    # a 429 or an overload timeout. That is exactly what failed the backend
    # agent (and everything downstream of it) in the live run, twice, while its
    # wave-mate ui succeeded. Serialising to 1 gives each agent the whole budget
    # in turn; the widest wave is two agents, so the cost is one agent's latency,
    # not real parallelism. Raise this only on a paid tier with headroom for
    # concurrent calls.
    llm_generation_concurrency: int = 1

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
    # Which ASR engine to use: "sarvam", "whisper", or "auto".
    # "auto" (default) means Sarvam when SARVAM_API_KEY is set, local
    # Whisper otherwise — so adding the key is the only step needed to
    # switch, and removing it silently falls back instead of breaking.
    asr_provider: str = "auto"

    # ---- Sarvam AI (cloud ASR, built for Indian languages) ----
    # Free key from https://dashboard.sarvam.ai. Chosen over local Whisper
    # for the three languages this project actually needs (Gujarati, Hindi,
    # English, including code-mixed speech) and because it needs no GPU:
    # a CPU-only laptop running Whisper "small" took 34-79s per utterance,
    # which is unusable in a live meeting.
    sarvam_api_key: str | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"
    # saaras:v3 is Sarvam's current recommended model (June 2026): one model,
    # one endpoint (/speech-to-text), a `mode` parameter picks the behaviour.
    # Previously this pointed at saaras:v2.5 (a separate /speech-to-text-translate
    # endpoint) and saarika:v2.5 (below) — both are legacy now, both are
    # marked "will be deprecated soon" in Sarvam's docs, and v3 is the more
    # accurate model besides, so this is a straight accuracy + stability
    # upgrade, not just a version bump.
    sarvam_model: str = "saaras:v3"
    # Same v3 model, same /speech-to-text endpoint — asr.py passes
    # mode="transcribe" here and mode="translate" for sarvam_model above, so
    # this only needs to be a separate setting in case someone wants to pin
    # a different model for the original-language pass specifically.
    sarvam_stt_model: str = "saaras:v3"
    sarvam_include_original: bool = True
    sarvam_timeout_seconds: float = 20.0
    # Sarvam is remote, so slots here are network round trips rather than
    # CPU cores — several can be in flight at once without contention.
    max_concurrent_sarvam_requests: int = 6

    # ---- Local Whisper (fallback ASR) ----
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
    # Whisper auto-detect picks from ~99 languages, and on a short noisy
    # utterance from the CPU "small" model that guess is close to random:
    # a real meeting log had English speech detected as Telugu at 0.68
    # confidence, then hi/en/gu all at ~0.32, and every one of those lines
    # came back as gibberish. Restricting the choice to the languages this
    # project actually supports makes a Telugu/Urdu/Marathi misfire
    # structurally impossible. Set to "" to allow all languages again.
    whisper_allowed_languages: str = "en,hi,gu"
    # 0 = let ctranslate2 use every core. Fine when one transcription runs
    # at a time; see max_concurrent_transcriptions_cpu below.
    whisper_cpu_threads: int = 0

    # ============================================================
    # ---- Auth / Users (cloud) ----
    # ============================================================
    # Async SQLAlchemy URL, e.g. for a free Neon Postgres project:
    #   postgresql+asyncpg://user:password@ep-xxxx.neon.tech/protopilot?ssl=require
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/protopilot"

    # Where meeting state (transcript, requirements, agent outputs) lives:
    #   "sqlite"   -> a local file at meeting_store_path (default; local dev)
    #   "postgres" -> the same managed Postgres as the auth DB (database_url)
    # A cloud host with an ephemeral disk (Render/Fly free tiers) wipes the
    # SQLite file on every deploy/restart, losing every meeting and its
    # generated prototype. Setting MEETING_STORE_BACKEND=postgres there puts
    # meeting state in Neon alongside auth, so it survives redeploys. Local
    # dev leaves this as "sqlite" and nothing changes.
    meeting_store_backend: str = "sqlite"

    # Local SQLite file holding meeting state (used when meeting_store_backend
    # is "sqlite"). Survives backend restarts on a persistent disk — the
    # in-memory dict used before lost everything on a restart, taking the
    # generated prototype with it. Relative paths resolve against the backend
    # working dir.
    meeting_store_path: str = "./protopilot_meetings.db"

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

    # Extra CORS origins, comma-separated. The Electron app serves its UI from
    # http://localhost:5173 (dev + packaged), which is already allowed; this
    # is for any additional frontend hosts (e.g. a deployed web build) that
    # should reach this backend.
    extra_cors_origins: str = ""

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
    #
    # This value applies on GPU only. On CPU the limit is forced to
    # max_concurrent_transcriptions_cpu regardless of what is set here,
    # because ctranslate2 already parallelises one transcription across every
    # core: running two at once does not double throughput, it makes both
    # slower. A real meeting log showed 5.28s of audio taking 34.92s and the
    # queue wait snowballing to 170.83s, for a worst-case caption 195.97s
    # after the words were spoken. One at a time on CPU is genuinely faster.
    max_concurrent_transcriptions: int = 4
    max_concurrent_transcriptions_cpu: int = 1


settings = Settings()