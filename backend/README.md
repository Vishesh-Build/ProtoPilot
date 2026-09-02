# ProtoPilot Backend — complete, consolidated

This is the FULL backend — your original agent/LLM/transcription code
untouched, plus everything built across every phase: real auth (email +
Google/GitHub OAuth), host-only permissions, and real LiveKit video calls
with per-participant transcription. Drop this whole `app/` folder in place
of your current one (back it up first if you want to compare).

## 1. Install

```
pip install -r requirements.txt --break-system-packages
```
(drop `--break-system-packages` if you're using a venv properly activated)

## 2. Configure

```
cp .env.example .env
```
Then fill in every value — see the comments in `.env.example` for exactly
where to get each one (Neon for the database, cloud.livekit.io for video,
Google Cloud Console + GitHub Developer Settings for OAuth, Gmail app
password or any SMTP provider for email). Nothing fake-works without its
real key — if a section isn't configured, that feature returns a clear
error instead of pretending to succeed.

**Also rotate** the NIM/GROQ keys you pasted in chat earlier — regenerate
them from NVIDIA/Groq's dashboards and put the new ones in `.env`.

## 3. Run

```
uvicorn app.main:app --reload
```

Tables are created automatically on first startup. Visit
`http://localhost:8000/docs` for the live interactive API reference —
every endpoint below is real and listed there.

## What's real, by feature

| Feature | Endpoints | Notes |
|---|---|---|
| Register/Login/Logout | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me` | bcrypt hashing, JWT httpOnly cookies |
| Forgot/Reset password | `/auth/forgot-password`, `/auth/reset-password` | real SMTP email, single-use signed token |
| Google/GitHub login | `/auth/google/login`, `/auth/github/login` (+ callbacks) | real OAuth2, links to existing accounts by email |
| Create/manage meetings | `/meetings`, `/meetings/{id}`, `/meetings/{id}/end`, DELETE `/meetings/{id}` | end/delete are host-only |
| Requirements | `/meetings/{id}/requirements`, PATCH `.../status`, `.../title` | accept/reject/edit — host-only |
| Video call | `/meetings/{id}/livekit-token`, `/meetings/{id}/start-call`, `/meetings/{id}/stop-call` | real LiveKit rooms, per-participant tracks |
| Live transcript | `ws://.../ws/meeting/{id}` | broadcasts to every connected participant |
| Prototype generation | `ws://.../ws/meeting/{id}/generate` | host-only, real 9-agent pipeline |
| Export | `/meetings/{id}/export/status`, `/meetings/{id}/export` | host-only, real ZIP of whatever was actually produced |

## Folder map (what's new vs. untouched)

```
app/
├── main.py                 EDITED — every router wired in, CORS, startup/shutdown
├── config.py                 EDITED — every setting from every phase
├── db/                        NEW — User table (async SQLAlchemy)
├── core/
│   ├── security.py             EDITED — + OAuth state tokens
│   ├── deps.py, email.py,        NEW — auth building blocks
│   │   rate_limit.py, session_cookies.py,
│   │   oauth_providers.py, oauth_users.py
│   ├── meeting_auth.py           NEW — host-only enforcement (HTTP + WS)
│   └── connection_manager.py      NEW — broadcasts to every participant
├── livekit/                        NEW — transcription bot + per-meeting registry
├── schemas/auth.py                  NEW
├── api/
│   ├── auth.py, oauth.py, livekit_router.py   NEW
│   ├── meetings.py, requirements.py, exports.py   EDITED — host-only
│   └── health.py, llm_test.py                        UNTOUCHED
├── ws/
│   ├── meeting.py                EDITED — broadcast-only now (LiveKit carries audio)
│   └── generate.py                EDITED — host-only
├── agents/, llm/, requirements/,     UNTOUCHED — your original pipeline,
│   transcription/, exports/,          agents, and export builder, exactly
│   meetings/session.py (+host_user_id)  as you wrote them
```

## Still outside this backend's scope

- Settings/Notifications/Command-palette screens in the frontend are
  intentionally local-only — nothing here was asked to persist settings,
  push real notifications, or power global search, so nothing fake was
  built for them.
- Idle-meeting cleanup: if a host navigates away without clicking "End
  Meeting", the transcription bot stays connected to an empty LiveKit room
  until the process restarts. Fine for now; worth a TTL/cleanup job later
  if this goes to real users.
