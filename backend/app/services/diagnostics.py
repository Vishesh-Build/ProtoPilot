"""
Diagnostics & System Health Service for ProtoPilot.

Monitors operational health of all external dependencies (Groq, Gemini,
Sarvam AI, LiveKit, Neon Postgres), tracks active and historical incidents,
and generates human-readable Reason and Solution explanations for each problem.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
import pathlib
import sys
import time
import uuid
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("protopilot.diagnostics")


class Incident:
    def __init__(
        self,
        category: str,
        title: str,
        reason: str,
        solution: str,
        severity: str = "WARNING",
        raw_details: str | None = None,
        status: str = "active",
        incident_id: str | None = None,
        timestamp: str | None = None,
    ):
        self.id = incident_id or str(uuid.uuid4())[:8]
        self.timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.category = category  # LLM_QUOTA, VIDEO_CALL, DATABASE, TRANSCRIPTION, PIPELINE, SYSTEM
        self.title = title
        self.reason = reason
        self.solution = solution
        self.severity = severity  # CRITICAL, WARNING, INFO, RESOLVED
        self.raw_details = raw_details
        self.status = status  # active, resolved
        self.resolved_at: str | None = None
        self.occurrences = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "category": self.category,
            "title": self.title,
            "reason": self.reason,
            "solution": self.solution,
            "severity": self.severity,
            "raw_details": self.raw_details,
            "status": self.status,
            "resolved_at": self.resolved_at,
            "occurrences": self.occurrences,
        }


class DiagnosticsService:
    _instance: DiagnosticsService | None = None

    def __init__(self):
        self._incidents: list[Incident] = []
        self._lock = asyncio.Lock()
        self._start_time = time.time()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> DiagnosticsService:
        if cls._instance is None:
            cls._instance = DiagnosticsService()
        return cls._instance

    def initialize(self):
        """Scan recent logs to populate historical incidents on startup."""
        if self._initialized:
            return
        self._initialized = True
        self._parse_recent_logs()

    # ------------------------------------------------------------------ Incidents
    def record_incident(
        self,
        category: str,
        title: str,
        reason: str,
        solution: str,
        severity: str = "WARNING",
        raw_details: str | None = None,
    ) -> Incident:
        """Records a new problem or increments occurrence of recent duplicate."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Check for recent identical active incident to prevent spamming
        for inc in self._incidents:
            if inc.status == "active" and inc.category == category and inc.title == title:
                inc.occurrences += 1
                inc.timestamp = now_ts
                if raw_details:
                    inc.raw_details = raw_details
                return inc

        incident = Incident(
            category=category,
            title=title,
            reason=reason,
            solution=solution,
            severity=severity,
            raw_details=raw_details,
        )
        self._incidents.insert(0, incident)
        # Keep maximum 100 historical incidents
        if len(self._incidents) > 100:
            self._incidents = self._incidents[:100]

        logger.info("diagnostics: recorded incident [%s] %s", category, title)
        return incident

    def resolve_incident(self, incident_id: str) -> bool:
        """Marks an active incident as resolved."""
        for inc in self._incidents:
            if inc.id == incident_id:
                inc.status = "resolved"
                inc.resolved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                return True
        return False

    def clear_resolved_incidents(self):
        self._incidents = [inc for inc in self._incidents if inc.status == "active"]

    def get_incidents(self) -> dict[str, list[dict[str, Any]]]:
        active = [inc.to_dict() for inc in self._incidents if inc.status == "active"]
        history = [inc.to_dict() for inc in self._incidents if inc.status == "resolved"]
        return {"active": active, "history": history}

    # ------------------------------------------------------------------ Probes
    async def check_database(self) -> dict[str, Any]:
        """Probes DB connection and measures latency."""
        t0 = time.monotonic()
        try:
            from sqlalchemy import text
            from app.db.database import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            is_neon = "neon.tech" in str(settings.database_url)
            engine_name = "Neon Postgres (SSL)" if is_neon else "Local Database"
            return {
                "name": "Database",
                "status": "healthy",
                "engine": engine_name,
                "latency_ms": latency_ms,
                "message": f"Connected to {engine_name} ({latency_ms}ms)",
            }
        except Exception as e:
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            err_msg = str(e)
            self.record_incident(
                category="DATABASE",
                title="Database Connection Refused",
                reason="The database could not be reached or rejected the connection (check SSL parameters).",
                solution="Ensure DATABASE_URL has ssl=require or valid Neon credentials.",
                severity="CRITICAL",
                raw_details=err_msg,
            )
            return {
                "name": "Database",
                "status": "error",
                "latency_ms": latency_ms,
                "message": err_msg[:120],
            }

    async def check_gemini(self) -> dict[str, Any]:
        """Probes Google Gemini API key and quota status."""
        key = settings.gemini_api_key
        if not key:
            return {
                "name": "Google Gemini",
                "status": "unconfigured",
                "message": "No GEMINI_API_KEY configured (optional, but recommended for large token budget).",
            }

        t0 = time.monotonic()
        url = f"{settings.gemini_base_url.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url, headers={"Authorization": f"Bearer {key}"})
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            if res.status_code == 200:
                return {
                    "name": "Google Gemini",
                    "status": "healthy",
                    "latency_ms": latency_ms,
                    "model": "gemini-3.6-flash",
                    "message": f"Operational ({latency_ms}ms)",
                }
            elif res.status_code == 429:
                self.record_incident(
                    category="LLM_QUOTA",
                    title="Gemini Quota Exceeded (429)",
                    reason="Google Gemini AI Studio quota or rate limit was reached.",
                    solution="Wait 60s for quota replenishment or create a new free key at https://aistudio.google.com/apikey.",
                    severity="WARNING",
                )
                return {"name": "Google Gemini", "status": "rate_limited", "message": "HTTP 429: Rate limit exceeded"}
            elif res.status_code == 401 or res.status_code == 403:
                self.record_incident(
                    category="LLM_QUOTA",
                    title="Gemini API Key Invalid (401)",
                    reason="Configured GEMINI_API_KEY was rejected by Google AI Studio.",
                    solution="Generate a valid key at https://aistudio.google.com/apikey and update in .env / Render.",
                    severity="CRITICAL",
                )
                return {"name": "Google Gemini", "status": "invalid_key", "message": f"HTTP {res.status_code}: Invalid Key"}
            else:
                return {"name": "Google Gemini", "status": "warning", "message": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"name": "Google Gemini", "status": "unreachable", "message": str(e)[:100]}

    async def check_groq(self) -> dict[str, Any]:
        """Probes Groq Cloud API key and rate-limit status."""
        key = settings.groq_api_key
        if not key:
            return {
                "name": "Groq AI",
                "status": "unconfigured",
                "message": "No GROQ_API_KEY configured.",
            }

        t0 = time.monotonic()
        url = f"{settings.groq_base_url.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url, headers={"Authorization": f"Bearer {key}"})
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            if res.status_code == 200:
                return {
                    "name": "Groq AI",
                    "status": "healthy",
                    "latency_ms": latency_ms,
                    "model": "llama-3.3-70b-versatile",
                    "message": f"Operational ({latency_ms}ms)",
                }
            elif res.status_code == 429:
                self.record_incident(
                    category="LLM_QUOTA",
                    title="Groq Rate Limit Exceeded (429)",
                    reason="Groq Free Tier TPM (8,000 tokens/min) or RPM was exceeded during agent pipeline.",
                    solution="Add a GEMINI_API_KEY to lead generation with larger quotas, or wait 60s for refill.",
                    severity="WARNING",
                )
                return {"name": "Groq AI", "status": "rate_limited", "message": "HTTP 429: TPM/RPM rate limit hit"}
            elif res.status_code == 401:
                self.record_incident(
                    category="LLM_QUOTA",
                    title="Groq API Key Invalid / Suspended (401)",
                    reason="Configured GROQ_API_KEY was rejected by GroqCloud.",
                    solution="Verify GROQ_API_KEY at https://console.groq.com/keys.",
                    severity="CRITICAL",
                )
                return {"name": "Groq AI", "status": "invalid_key", "message": "HTTP 401: Invalid Key"}
            else:
                return {"name": "Groq AI", "status": "warning", "message": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"name": "Groq AI", "status": "unreachable", "message": str(e)[:100]}

    async def check_sarvam(self) -> dict[str, Any]:
        """Probes Sarvam AI Speech-to-Text key and balance."""
        key = settings.sarvam_api_key
        if not key:
            return {
                "name": "Sarvam AI (ASR)",
                "status": "unconfigured",
                "message": "No SARVAM_API_KEY set — falling back to local Whisper CPU (slower, high RAM).",
            }

        t0 = time.monotonic()
        # Sarvam doesn't have /models, but we can verify auth via base URL or lightweight call
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(f"{settings.sarvam_base_url.rstrip('/')}/", headers={"api-subscription-key": key})
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            # Sarvam root returns 404 or 200 depending on gateway, but 401/403 means auth rejected
            if res.status_code in (401, 403, 402):
                self.record_incident(
                    category="TRANSCRIPTION",
                    title="Sarvam AI Credits Exhausted (API Khatam)",
                    reason="Sarvam AI returned 401/402. The trial credits (₹1000) have expired or key is invalid.",
                    solution="Log into https://dashboard.sarvam.ai to check wallet credits or generate a fresh key.",
                    severity="CRITICAL",
                )
                return {"name": "Sarvam AI (ASR)", "status": "credits_exhausted", "message": f"HTTP {res.status_code}: Credits exhausted or invalid"}

            return {
                "name": "Sarvam AI (ASR)",
                "status": "healthy",
                "latency_ms": latency_ms,
                "model": settings.sarvam_model,
                "message": f"Active cloud ASR ({latency_ms}ms)",
            }
        except Exception as e:
            return {"name": "Sarvam AI (ASR)", "status": "warning", "message": str(e)[:100]}

    async def check_livekit(self) -> dict[str, Any]:
        """Probes LiveKit Cloud connection & API credentials."""
        url = settings.livekit_url
        key = settings.livekit_api_key
        secret = settings.livekit_api_secret

        if not url or not key or not secret:
            self.record_incident(
                category="VIDEO_CALL",
                title="LiveKit Video Call Unconfigured",
                reason="LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET is missing.",
                solution="Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in backend/.env or Render Dashboard.",
                severity="CRITICAL",
            )
            return {"name": "LiveKit Video", "status": "unconfigured", "message": "Missing LiveKit credentials"}

        t0 = time.monotonic()
        try:
            from livekit import api as lk_api
            lk = lk_api.LiveKitAPI(url, key, secret)
            rooms = await lk.room.list_rooms(lk_api.ListRoomsRequest())
            await lk.aclose()
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            return {
                "name": "LiveKit Video",
                "status": "healthy",
                "latency_ms": latency_ms,
                "active_rooms": len(rooms.rooms),
                "message": f"Connected to LiveKit Cloud ({len(rooms.rooms)} active rooms, {latency_ms}ms)",
            }
        except Exception as e:
            err_msg = str(e)
            self.record_incident(
                category="VIDEO_CALL",
                title="LiveKit Call Server Unreachable (Video Call Kaam Nahi Kar Raha)",
                reason="Failed to connect to LiveKit server or API Key/Secret was rejected.",
                solution="Check https://cloud.livekit.io to verify your LiveKit project is running and keys match.",
                severity="CRITICAL",
                raw_details=err_msg,
            )
            return {"name": "LiveKit Video", "status": "error", "message": err_msg[:120]}

    def check_system_resources(self) -> dict[str, Any]:
        """System metrics: memory, uptime, platform."""
        uptime_sec = int(time.time() - self._start_time)
        h = uptime_sec // 3600
        m = (uptime_sec % 3600) // 60
        s = uptime_sec % 60
        uptime_str = f"{h}h {m}m {s}s"

        import platform
        res = {
            "uptime": uptime_str,
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "pid": os.getpid(),
        }

        try:
            import psutil
            process = psutil.Process()
            mem_mb = round(process.memory_info().rss / (1024 * 1024), 1)
            res["memory_rss_mb"] = mem_mb
            res["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        except Exception:
            res["memory_rss_mb"] = "N/A"

        return res

    async def check_all(self) -> dict[str, Any]:
        """Runs all live health probes concurrently."""
        db_res, gemini_res, groq_res, sarvam_res, lk_res = await asyncio.gather(
            self.check_database(),
            self.check_gemini(),
            self.check_groq(),
            self.check_sarvam(),
            self.check_livekit(),
            return_exceptions=True,
        )

        providers = [
            db_res if isinstance(db_res, dict) else {"name": "Database", "status": "error", "message": str(db_res)},
            gemini_res if isinstance(gemini_res, dict) else {"name": "Google Gemini", "status": "error", "message": str(gemini_res)},
            groq_res if isinstance(groq_res, dict) else {"name": "Groq AI", "status": "error", "message": str(groq_res)},
            sarvam_res if isinstance(sarvam_res, dict) else {"name": "Sarvam AI", "status": "error", "message": str(sarvam_res)},
            lk_res if isinstance(lk_res, dict) else {"name": "LiveKit Video", "status": "error", "message": str(lk_res)},
        ]

        overall = "healthy"
        for p in providers:
            st = p.get("status")
            if st in ("error", "credits_exhausted", "invalid_key"):
                overall = "critical"
                break
            elif st in ("rate_limited", "warning", "unreachable"):
                overall = "degraded"

        return {
            "overall_status": overall,
            "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "providers": providers,
            "system": self.check_system_resources(),
            "incidents": self.get_incidents(),
        }

    # ------------------------------------------------------------------ Log Parser
    def _parse_recent_logs(self):
        """Scans protopilot.log to restore historical incidents."""
        log_file = pathlib.Path(__file__).resolve().parent.parent.parent / "protopilot.log"
        if not log_file.is_file():
            return

        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-200:]  # last 200 lines

            for line in lines:
                lower = line.lower()
                if "rate limit" in lower or "429" in lower:
                    if "groq" in lower:
                        self.record_incident(
                            category="LLM_QUOTA",
                            title="Groq Rate Limit Exceeded (429)",
                            reason="Groq per-minute token quota (8,000 TPM) was exceeded during pipeline execution.",
                            solution="Add GEMINI_API_KEY in backend/.env to lead generation with larger quotas.",
                            severity="WARNING",
                            raw_details=line.strip()[:200],
                        )
                    elif "gemini" in lower:
                        self.record_incident(
                            category="LLM_QUOTA",
                            title="Gemini Quota Exceeded (429)",
                            reason="Google AI Studio per-minute token limit reached.",
                            solution="Wait 60 seconds or generate a fresh key at https://aistudio.google.com/apikey.",
                            severity="WARNING",
                            raw_details=line.strip()[:200],
                        )
                elif "connection is insecure" in lower or "sslmode=require" in lower:
                    self.record_incident(
                        category="DATABASE",
                        title="Neon Postgres Insecure Connection Rejected",
                        reason="Neon Postgres requires SSL connections; asyncpg connected without SSL parameters.",
                        solution="Ensure database engine connects with connect_args={'ssl': 'require'} and ?ssl=require.",
                        severity="CRITICAL",
                        raw_details=line.strip()[:200],
                    )
                elif "sarvam" in lower and ("fail" in lower or "401" in lower or "402" in lower):
                    self.record_incident(
                        category="TRANSCRIPTION",
                        title="Sarvam AI Cloud ASR Failure",
                        reason="Sarvam API returned an error or authentication failed during audio transcription.",
                        solution="Verify SARVAM_API_KEY at https://dashboard.sarvam.ai.",
                        severity="WARNING",
                        raw_details=line.strip()[:200],
                    )
                elif "livekit" in lower and ("error" in lower or "failed" in lower or "disconnect" in lower):
                    self.record_incident(
                        category="VIDEO_CALL",
                        title="LiveKit Room Stream Disconnected",
                        reason="WebRTC media track or transcription bot encountered a disconnection.",
                        solution="Verify LiveKit project status and room tokens.",
                        severity="WARNING",
                        raw_details=line.strip()[:200],
                    )
        except Exception as e:
            logger.debug("Failed parsing protopilot.log: %s", e)


diagnostics_service = DiagnosticsService.get_instance()
