"""
Tests for ProtoPilot Admin API & System Diagnostics Service.

Verifies:
1. Strict 403 Forbidden enforcement on unauthorized requests (zero data leakage).
2. Successful authorization via X-Admin-Secret header or cookie.
3. Health probes and incident tracking (deduplication, resolution, history).
4. Reason and Solution generation for system problems (LLM quota, LiveKit, DB).
"""

import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:
    import stubs
stubs.install()

from fastapi import HTTPException
from app.api.admin import (
    VerifyAdminRequest,
    clear_resolved_incidents,
    get_incidents,
    get_system_health,
    require_admin,
    resolve_incident,
    verify_admin_access,
)
from app.config import settings
from app.services.diagnostics import DiagnosticsService, Incident


class AdminSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def test_unauthorized_access_raises_403(self):
        req = mock.MagicMock()
        req.query_params = {}
        db = mock.AsyncMock()

        with self.assertRaises(HTTPException) as ctx:
            await require_admin(
                request=req,
                x_admin_secret=None,
                admin_secret_cookie=None,
                access_token=None,
                db=db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access Denied", ctx.exception.detail)

    async def test_wrong_secret_raises_403(self):
        req = mock.MagicMock()
        req.query_params = {}
        db = mock.AsyncMock()

        with self.assertRaises(HTTPException) as ctx:
            await require_admin(
                request=req,
                x_admin_secret="wrong-secret-key",
                admin_secret_cookie=None,
                access_token=None,
                db=db,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_correct_secret_header_authorizes(self):
        req = mock.MagicMock()
        req.query_params = {}
        db = mock.AsyncMock()

        auth = await require_admin(
            request=req,
            x_admin_secret=settings.admin_secret_key,
            admin_secret_cookie=None,
            access_token=None,
            db=db,
        )
        self.assertTrue(auth["authorized"])
        self.assertEqual(auth["auth_type"], "secret_key")

    async def test_correct_secret_cookie_authorizes(self):
        req = mock.MagicMock()
        req.query_params = {}
        db = mock.AsyncMock()

        auth = await require_admin(
            request=req,
            x_admin_secret=None,
            admin_secret_cookie=settings.admin_secret_key,
            access_token=None,
            db=db,
        )
        self.assertTrue(auth["authorized"])
        self.assertEqual(auth["auth_type"], "secret_key")

    async def test_verify_access_endpoint_sets_cookie(self):
        req = mock.MagicMock()
        req.query_params = {}
        resp = mock.MagicMock()
        db = mock.AsyncMock()

        body = VerifyAdminRequest(secret=settings.admin_secret_key)
        res = await verify_admin_access(
            request=req,
            response=resp,
            body=body,
            x_admin_secret=None,
            admin_secret_cookie=None,
            access_token=None,
            db=db,
        )
        self.assertTrue(res["authorized"])
        self.assertTrue(resp.set_cookie.called)
        call_kwargs = resp.set_cookie.call_args[1]
        self.assertEqual(call_kwargs.get("key"), "admin_secret")
        self.assertEqual(call_kwargs.get("value"), settings.admin_secret_key)


class DiagnosticsServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.svc = DiagnosticsService()

    def test_record_and_resolve_incident(self):
        inc = self.svc.record_incident(
            category="LLM_QUOTA",
            title="Groq Rate Limit Exceeded (429)",
            reason="8,000 TPM limit exceeded.",
            solution="Add GEMINI_API_KEY in backend/.env or wait 60 seconds.",
            severity="WARNING",
            raw_details="Rate limit reached for model llama-3.3-70b-versatile",
        )
        self.assertEqual(inc.category, "LLM_QUOTA")
        self.assertEqual(inc.status, "active")

        incidents = self.svc.get_incidents()
        self.assertEqual(len(incidents["active"]), 1)
        self.assertEqual(len(incidents["history"]), 0)
        self.assertEqual(incidents["active"][0]["title"], "Groq Rate Limit Exceeded (429)")
        self.assertEqual(incidents["active"][0]["reason"], "8,000 TPM limit exceeded.")
        self.assertIn("GEMINI_API_KEY", incidents["active"][0]["solution"])

        # Resolving moves to history
        ok = self.svc.resolve_incident(inc.id)
        self.assertTrue(ok)

        incidents2 = self.svc.get_incidents()
        self.assertEqual(len(incidents2["active"]), 0)
        self.assertEqual(len(incidents2["history"]), 1)
        self.assertEqual(incidents2["history"][0]["status"], "resolved")
        self.assertIsNotNone(incidents2["history"][0]["resolved_at"])

    def test_duplicate_incidents_increment_occurrence_count(self):
        inc1 = self.svc.record_incident(
            category="VIDEO_CALL",
            title="LiveKit Bot Disconnected",
            reason="Network disconnect",
            solution="Check LiveKit credentials.",
        )
        self.assertEqual(inc1.occurrences, 1)

        inc2 = self.svc.record_incident(
            category="VIDEO_CALL",
            title="LiveKit Bot Disconnected",
            reason="Network disconnect",
            solution="Check LiveKit credentials.",
        )
        self.assertEqual(inc2.occurrences, 2)
        self.assertEqual(len(self.svc.get_incidents()["active"]), 1)

    async def test_check_all_probes_and_returns_diagnostics(self):
        with mock.patch.object(self.svc, "check_database", return_value={"name": "Database", "status": "healthy"}), \
             mock.patch.object(self.svc, "check_gemini", return_value={"name": "Google Gemini", "status": "healthy"}), \
             mock.patch.object(self.svc, "check_groq", return_value={"name": "Groq AI", "status": "healthy"}), \
             mock.patch.object(self.svc, "check_sarvam", return_value={"name": "Sarvam AI", "status": "healthy"}), \
             mock.patch.object(self.svc, "check_livekit", return_value={"name": "LiveKit Video", "status": "healthy"}):
            
            res = await self.svc.check_all()
            self.assertEqual(res["overall_status"], "healthy")
            self.assertEqual(len(res["providers"]), 5)
            self.assertIn("system", res)
            self.assertIn("incidents", res)


class AdminEndpointsTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_system_health_endpoint(self):
        admin_auth = {"authorized": True, "auth_type": "secret_key"}
        with mock.patch("app.api.admin.diagnostics_service.check_all") as mock_check:
            mock_check.return_value = {
                "overall_status": "healthy",
                "providers": [],
                "incidents": {"active": [], "history": []},
            }
            res = await get_system_health(admin_auth=admin_auth)
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["diagnostics"]["overall_status"], "healthy")

    async def test_resolve_incident_endpoint(self):
        admin_auth = {"authorized": True, "auth_type": "secret_key"}
        with mock.patch("app.api.admin.diagnostics_service.resolve_incident", return_value=True), \
             mock.patch("app.api.admin.diagnostics_service.get_incidents", return_value={"active": [], "history": []}):
            res = await resolve_incident(incident_id="inc-123", admin_auth=admin_auth)
            self.assertEqual(res["status"], "ok")
            self.assertIn("resolved", res["message"])


if __name__ == "__main__":
    unittest.main()
