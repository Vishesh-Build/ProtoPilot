# ProtoPilot — Frontend (real, backend-connected)

Light theme / photo-background design. Every page is now wired to the
real backend — no fake/demo data anywhere.

## Run it

```
npm install
npm run electron:dev
```

Backend must already be running on `http://localhost:8000` (see
`../backend/README.md`) — this app talks to it via `src/lib/api.js`.

## Pages

```
src/
├── App.jsx                    ← navigation + real session/meeting state
├── main.jsx
├── lib/api.js                   ← the one backend client every page uses
└── pages/
    ├── HomePage.jsx               (unchanged)
    ├── LoginPage.jsx               real /auth/login + Google/GitHub OAuth
    ├── RegisterPage.jsx            real /auth/register
    ├── ForgotPasswordPage.jsx      real /auth/forgot-password
    ├── ResetPasswordPage.jsx       real /auth/reset-password (NEW)
    ├── DashboardPage.jsx           real meeting list/stats from /meetings
    ├── LiveMeetingCall.jsx         real LiveKit video call + live transcript
    ├── AIWorkforcePage.jsx         real live agent status/progress
    ├── GenerationPipelinePage.jsx  owns the real generation WebSocket —
    │                                 opening this page IS what starts a
    │                                 real backend pipeline run
    └── PrototypeViewerPage.jsx     real generated HTML + real export
```

## Electron

`npm run electron:dev` runs Vite + Electron together. `npm run
electron:build:win` produces a real installer in `release/`.
