# Claude Code Handoff — ProtoPilot Capstone (2026-09-04)

You are continuing work on ProtoPilot, a capstone project: LiveKit Cloud meeting → hidden server-side bot → webrtcvad segmentation → Sarvam/Whisper ASR → LLM translation → requirement extraction → 9-agent DAG pipeline (8 waves) → clickable HTML prototype.

Stack: FastAPI + uvicorn backend on port 8000; Electron 31 + React 18 + Vite 5 frontend on 5173, no react-router. Python 3.11 (Windows), node 22 (Windows).

## Where this work came from, and what changes for you

Everything up to now was done from a sandboxed Linux VM with the repo mounted but **no network access**. Every edit is real and on disk in this folder; what the sandbox could never do was install a package, call a provider, or start a server. That shaped the code in ways worth knowing:

- **The test suite is stdlib `unittest` only, and must stay that way.** No pytest, no fixtures, no network. `backend/tests/stubs.py` stubs pydantic-settings, httpx, faster-whisper, webrtcvad, livekit and mcp — but *only when the real package is missing*, so on a fully-installed machine the same tests run against the real imports. The httpx stub raises on every request by design: a test that tries to reach the network should fail loudly, not quietly pass against a live API.
- **The stubbed settings deliberately do not read `backend/.env`**, so tests run against `app/config.py` defaults. A `.env` value silently overriding a default has already caused a bug here.
- You are presumably running on Windows with network. That means you *can* do the two things the sandbox couldn't: `pip install -r requirements.txt` and actually run the app. Use that — the owed verification below is the whole point.
- Windows `node_modules` cannot run `vite`/`rollup`/`esbuild` under Linux (platform-specific native binaries). Irrelevant to you on Windows; mentioned only so you don't misread past notes about checking JSX with `@babel/parser` instead of building.
- `backend/.env` holds live API keys. Never commit it, never echo a key value — report `set` / `NOT set`. There is no git identity configured in this repo, so if you commit, pass it per command: `git -c user.name=... -c user.email=...`.

## Current state

Backend test suite: **220 tests, all green.** `python3 -m compileall -q app tests` clean.

**LIVE END-TO-END PROOF PASSED (2026-09-04, Windows, real providers).** `backend/scripts/prove_pipeline.py` runs the real 9-agent pipeline against live providers and reported `pipeline_complete` — all nine agents COMPLETED and a ~126 KB multi-screen clickable prototype via Google Stitch — after two earlier runs that ended `pipeline_failed` (backend/qa/devops fell). The difference was the two fixes in the "demo-reliability round" section below. Re-run any time: `cd backend && PYTHONPATH=. python scripts/prove_pipeline.py` (spends real tokens, ~4½ min, writes `scripts/prove_pipeline_output.html`). **Caveat: this proof starts from a requirements list — the meeting → requirements half (LiveKit/VAD/ASR/translate/extract) is NOT exercised by it.**

A live demo run froze mid-pipeline. The log showed one failure chain with four links. All four are now fixed in code; read carefully which are **proven on Windows** and which are only **proven offline**:

1. **Sarvam silence latched the whole session onto local Whisper** — VERIFIED ON WINDOWS. Three pauses (speech energy, no words — "Hmm.") came back HTTP 200 with an empty transcript, were counted as failures, and after 3 the session fell back to local Whisper for good (captions 1.2s → 8–25s, Gujarati misdetected as Telugu/Bengali). Fixed with an `AsrSilence` exception in `backend/app/transcription/asr.py`: silence is not failure and does not touch the streak. The live log now shows `sarvam heard no speech in this utterance — nothing to transcribe, streak untouched`, and Gujarati came back `lang=gu conf=1.00` with sub-1.5s captions.
2. **Translation starved a reasoning model** — VERIFIED ON WINDOWS. `min(300, ...)` max_tokens meant gpt-oss-120b spent its entire budget on hidden reasoning and returned `content: null, finish_reason: length`, so requirements came back empty. Fixed in `backend/app/transcription/translate.py` with a floor of `settings.llm_default_max_tokens`.
3. **A 429 was treated as an outage** — OFFLINE ONLY, WINDOWS RUN OWED. Groq answered `429, retry-after=10s`. The router slept its own 1s + 2s backoff, gave up 7 seconds early, and then put Groq in a 60s cooldown — so a provider that was alive and had told us exactly when to come back was taken off the board for the rest of the wave. The API agent failed and five agents fell with it (UI, Backend, QA, DevOps, Prototype). Fixed in `providers/base.py` (`parse_retry_after()`, `ProviderError.retry_after`) and `router.py` (honor the provider's ask, cap at 20s, no cooldown for rate limits, at most 2 retries). Also fixed the useless `network error:` with nothing after it — a timed-out httpx exception stringifies to `""`, so the message now carries the exception class name.
4. **The pipeline claimed success while agents sat FAILED** — OFFLINE ONLY, WINDOWS RUN OWED. The orchestrator always emitted `pipeline_complete` once the waves finished, so the UI showed a clickable "Prototype ready — open it in Prototype Viewer" panel next to Prototype FAILED at 0%. That is the worst kind of bug in a demo: it lies to the person watching. Fixed: `orchestrator.run_pipeline` now emits `{"type": "pipeline_failed", "message": "...names..."}` when any agent failed, and `pipeline_complete` only when all nine completed. `GenerationPipelinePage.jsx` guards the success panel on `failedCount === 0`, shows "N failed" and a "Build failed" pill, and no longer paints a false "Lost connection" banner when React StrictMode double-mounts and closes a CONNECTING socket.

## Update — demo-reliability round (2026-09-04, this session)

The root cause the earlier round under-weighted was **physics, not a lone bug**: Groq's free tier is 8000 tokens/minute, one full 9-agent run needs ~25k, and agents firing concurrently on that ceiling cannot all be served. Three changes made the pipeline complete reliably; the live proof above confirms them together.

1. **Gemini added as the optional lead provider** (`providers/gemini.py`, `router.py`, `config.py`). Its free per-minute budget is far larger than Groq's, so with `GEMINI_API_KEY` set the chain is Gemini → Groq → NIM → OpenRouter; with no key it is unchanged (Groq-first), so this is zero-risk for the meeting path. Lead model `gemini-3.6-flash` (2.5-flash now 404s "no longer available"; 3.8-flash 503s more under load). The router only rediscovers a *different* Gemini model on 404/410, so the lead must be a reliably-live id, not the newest.
2. **Transient 5xx is retried, not cooled down** (`base.py`: `ProviderError.transient` + `is_transient_status`; `router.py`). Gemini answers 503 "high demand, try again later" — a transient overload, not an outage. It is now retried in place like a 429, and if it persists the router moves on WITHOUT a 60s cooldown, so the lead is still tried for the next agent. A live run died exactly here (503 → hard-fail + cooldown → three agents fell).
3. **Generation LLM calls are serialised** (`settings.llm_generation_concurrency = 1`; an `asyncio.Semaphore` created per run in `orchestrator.run_pipeline`, wrapping both `llm_router.chat` sites). ui + backend share a wave; firing both provider calls at once split the free-tier budget and one always 429'd/timed out (backend failed, qa + devops skipped under it — twice). One call at a time gives each agent the whole budget in turn; widest wave is two agents, so the cost is one agent's latency, not real parallelism. Also `settings.llm_generation_max_rate_limit_wait = 45.0` lets generation wait out an honest ~24s Retry-After that the caption path (20s ceiling) rightly abandons.

A run now takes ~4½ min on the free tier — that is the serialized-calls + Stitch reality, not a bug; raise `llm_generation_concurrency` only on a paid tier. `GEMINI_API_KEY` is in `backend/.env` (gitignored, untracked; never committed or echoed).

## Your first job

The requirements → prototype pipeline is proven end to end (see the live proof above), and previous-round fixes 3 and 4 (429-as-outage, false `pipeline_complete`) are confirmed by it: the run honored a transient ask with no cooldown and ended on an honest `pipeline_complete`. Two things remain:

- **If a backend was already running before these edits, restart it** — a live server does not pick up on-disk code or the new `.env` key until restarted (`python -m uvicorn app.main:app --port 8000` from `backend/`). The proof script runs a fresh process, so it is unaffected.
- **A full real-meeting run is still owed** — the proof skips the meeting → requirements half. Run one meeting end to end and read the log for: a 429 logging the provider's own number and *retrying after that long*; no bare `network error:` with nothing after the colon (each should name an exception class); and, if any agent fails, an honest `pipeline_failed` with the UI refusing to show "Prototype ready". Offline tests prove the logic; only Windows proves the product.

## What's owed / not yet verified

- **The meeting → requirements half is unproven this round.** `prove_pipeline.py` starts from a requirements list, so LiveKit → VAD → Sarvam/Whisper → translation → extraction was NOT exercised by the live proof — only requirements → 9 agents → prototype was. A full real-meeting run is still owed. (Previous-round fixes 3 and 4 are now confirmed by the pipeline proof.)
- **`frontend/src/pages/AIWorkforcePage.jsx`** is a ~400-line dead shell (never routed, ~130 inline hex colours). Not demo-blocking; delete or wire it, don't half-do it.
- **`frontend/build/` is empty** — a packaged Electron build would have no renderer. Dev mode is what the demo uses, so this only matters if packaging comes up.
- **`requirements.txt` is unpinned** — a fresh `pip install` on a new machine can pull something incompatible with Python 3.11. Pin before anyone else clones this.
- **Meeting rename on resume** is not implemented.
- ~~`orchestrator.run_one` catches only `RuntimeError`~~ — DONE this round: widened to `except Exception`, so an unexpected error (raw httpx escape, `TypeError` in a prompt builder) fails only that agent — logged with a traceback — instead of tearing down the whole wave's `asyncio.gather`.
- **Golden-set evaluation** — Gujarati/Hindi/English clips exist but there are no per-language accuracy numbers yet.

## How to run

Backend (Windows):
```
cd "C:\Users\vishe\OneDrive\Documents\PROTOTYPE CAPSTONE\backend"
python -m uvicorn app.main:app --port 8000
```

Frontend (Windows, dev — this is what the demo uses):
```
cd "C:\Users\vishe\OneDrive\Documents\PROTOTYPE CAPSTONE\frontend"
npm run electron:dev
```

Tests (anywhere with python3):
```
cd backend
python3 -m unittest discover -s tests -t .
```

Preflight:
```
cd backend
python scripts/preflight.py
```

## Files most likely to need edits

- `backend/app/llm/router.py` — retry/cool-down semantics for 429.
- `backend/app/llm/providers/base.py` — `ProviderError` carries `retry_after`, `parse_retry_after()`, `extract_reply_text()` empty-reply detection.
- `backend/app/transcription/asr.py` — `AsrSilence`.
- `backend/app/transcription/translate.py` — max_tokens floor.
- `backend/app/agents/orchestrator.py` — `pipeline_complete` vs `pipeline_failed` verdict.
- `frontend/src/pages/GenerationPipelinePage.jsx` — socket handlers, `finishedRef`, `failedCount` guard.

User speaks Hinglish — reply in Hinglish. Be direct. Be honest about what is verified versus owed; this project has suffered from two over-optimistic claims already (the false "Prototype ready" panel, and an earlier session declaring the pipeline safe while a silent bug still broke it). Prioritise reliability over features: the product's promise is "meeting in, prototype out", and the demo has failed twice via non-obvious chains — silence latching, translation starvation, 429 cooldowns — each of which looked like a different bug from the outside. When you change provider/transcription/agent code, add regression tests against `tests.stubs`; when you can't verify something, say so plainly and don't let "tests are green" stand in for "proven on Windows".
