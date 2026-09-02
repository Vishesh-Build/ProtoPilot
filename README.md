# ProtoPilot — complete project (backend + frontend)

```
protopilot/
├── backend/     FastAPI backend — see backend/README.md
└── frontend/    Electron/React frontend (light theme, photo background)
                 — see frontend/README.md
```

## Run order (every time)

**1. Backend** (its own terminal window — leave running)
```
cd backend
pip install -r requirements.txt --break-system-packages
cp .env.example .env      # fill in every value first — see backend/README.md
uvicorn app.main:app --reload
```

**2. Frontend** (a SEPARATE terminal window — leave running)
```
cd frontend
npm install
npm run electron:dev
```

Both must be running at the same time. Backend on `http://localhost:8000`,
frontend on `http://localhost:5173`.

If you get a "Can't reach the backend" error in the app, it means step 1
isn't running (or crashed) — check that terminal first.
