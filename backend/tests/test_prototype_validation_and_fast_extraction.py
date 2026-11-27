"""
Regression tests for:
  1. Truncated/incomplete prototype HTML (the live FinFlow AA solid-black-screen
     bug where max_tokens cut off inside <style> with no <body>) being rejected,
     retried cleanly, and never shipping broken HTML.
  2. Real-time requirement extraction using low reasoning_effort + tight failover
     budgets so Points don't lag ~36s behind Live Transcript.
  3. OpenAICompatibleProvider reasoning_effort HTTP-400 auto-fallback.
  4. Participant access guard (require_meeting_participant), /llm/chat admin gate,
     and Stitch sandbox postMessage navigation.
"""

import json
import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:
    import stubs
stubs.install()

from fastapi import HTTPException  # noqa: E402

from app.agents import definitions, orchestrator  # noqa: E402
from app.agents.state import AgentStatus  # noqa: E402
from app.api.llm_test import chat as llm_test_chat  # noqa: E402
from app.config import settings  # noqa: E402
from app.core.meeting_auth import require_meeting_participant  # noqa: E402
from app.llm import router as router_module  # noqa: E402
from app.llm.providers.base import ChatResult, OpenAICompatibleProvider, ProviderError  # noqa: E402
from app.meetings.session import MeetingSession, session_registry  # noqa: E402
from app.services import stitch_service  # noqa: E402


TRUNCATED_FINFLOW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>FinFlow AA</title>
  <style>
    :root { --bg-dark: #070b12; }
    body { background-color: var(--bg-dark); min-height: 100vh; }
    .header-bar { padding: 12px 24px; }
    .icon-btn { display: inline-""" + ("/* padding */ " * 120)


COMPLETE_SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FinFlow AA</title>
  <style>body{background:#080c14;color:#f8fafc;font-family:sans-serif;}.card{padding:16px;border-radius:12px;}</style>
</head>
<body>
  <header>
    <h1>FinFlow AA — Financial Governance</h1>
    <button onclick="document.getElementById('status').textContent='Synced'">Auto Sync UPI</button>
  </header>
  <main>
    <section class="card">
      <h2>Account Aggregator &amp; OTP Verification</h2>
      <p id="status">All bank accounts linked via RBI AA flow and mobile OTP authentication.</p>
      <div>Monthly Recurring Volume: INR 48,25,000 across 142 verified UPI mandates.</div>
    </section>
    <svg viewBox="0 0 500 180"><path d="M0 100 L500 20" stroke="#00E6A8" fill="none"/></svg>
    <table>
      <tr><th>Feature</th><th>Status</th></tr>
      <tr><td>Dark Mode Financial Web App UI</td><td>Active</td></tr>
      <tr><td>Mobile Number &amp; OTP Authentication</td><td>Verified</td></tr>
      <tr><td>Auto-sync UPI Transactions</td><td>Live</td></tr>
    </table>
  </main>
  <script>console.log('FinFlow ready');</script>
</body>
</html>"""


class PrototypeValidationTest(unittest.TestCase):
    def test_rejects_truncated_style_without_body(self):
        ok, reason = orchestrator.validate_prototype_html(TRUNCATED_FINFLOW_HTML)
        self.assertFalse(ok)
        self.assertIn("style", reason.lower())

    def test_rejects_length_cut_without_closing_html(self):
        partial = (
            "<!DOCTYPE html><html><head><style>body{color:#fff}</style></head><body>"
            + ("<section><h2>Module Overview</h2><p>Interactive item telemetry details and workflow actions.</p></section>" * 12)
            + "</body>"
        )
        ok, reason = orchestrator.validate_prototype_html(partial, finish_reason="length")
        self.assertFalse(ok)
        self.assertIn("max_tokens", reason)

    def test_accepts_complete_interactive_html(self):
        ok, reason = orchestrator.validate_prototype_html(COMPLETE_SAMPLE_HTML, finish_reason="stop")
        self.assertTrue(ok, reason)

    def test_prototype_agent_token_ceiling_is_sufficient(self):
        self.assertGreaterEqual(definitions.AGENT_DEFINITIONS["prototype"].max_tokens, 8192)

    def test_domain_fallback_html_is_complete_agnostic_and_valid(self):
        html = orchestrator._build_fallback_prototype_html(
            requirements_block="- [High] Mobile OTP Login (Auth)\n- [Medium] Light theme in settings (UI)"
        )
        ok, reason = orchestrator.validate_prototype_html(html)
        self.assertTrue(ok, reason)
        self.assertNotIn("Fleet Dispatches", html)
        self.assertNotIn("Fuel Optimization", html)
        self.assertIn("light-theme-toggle", html)


class PrototypeRetryPipelineTest(unittest.IsolatedAsyncioTestCase):
    async def test_retries_when_first_draft_truncates_inside_style_and_keeps_attempt_two(self):
        events = []

        async def emit(ev):
            events.append(ev)

        calls = []

        class _TruncatingThenGoodRouter:
            async def chat(self, messages, max_tokens=None, temperature=None, max_rate_limit_wait=None, reasoning_effort=None):
                system = messages[0]["content"]
                calls.append((system[:30], max_tokens, reasoning_effort))
                if "Prototype Builder" in system:
                    proto_calls = [c for c in calls if "Prototype Builder" in c[0]]
                    if len(proto_calls) == 1:
                        return ChatResult(
                            text=TRUNCATED_FINFLOW_HTML,
                            provider="gemini",
                            model="gemini-3.6-flash",
                            finish_reason="length",
                        )
                    return ChatResult(
                        text=COMPLETE_SAMPLE_HTML,
                        provider="gemini",
                        model="gemini-3.6-flash",
                        finish_reason="stop",
                    )
                return ChatResult(text=f"spec for {system[:15]}", provider="gemini", model="gemini-3.6-flash")

        with mock.patch.object(orchestrator, "llm_router", _TruncatingThenGoodRouter()), \
             mock.patch.object(orchestrator, "_WAVE_STAGGER_SECONDS", 0), \
             mock.patch.object(orchestrator.stitch_service, "generate_prototype_html", new=mock.AsyncMock(return_value=None)):
            states = await orchestrator.run_pipeline(
                [{"title": "FinFlow AA", "category": "Finance", "priority": "High"}],
                emit,
            )

        self.assertEqual(states["prototype"].status, AgentStatus.COMPLETED)
        out = states["prototype"].output or ""
        ok, reason = orchestrator.validate_prototype_html(out)
        self.assertTrue(ok, reason)
        self.assertIn("Account Aggregator &amp; OTP Verification", out)
        proto_calls = [c for c in calls if "Prototype Builder" in c[0]]
        self.assertEqual(len(proto_calls), 2)
        self.assertGreaterEqual(proto_calls[0][1], 8192)
        self.assertEqual(proto_calls[0][2], "low")


class FastRealtimeFailoverTest(unittest.IsolatedAsyncioTestCase):
    async def test_extractor_uses_low_reasoning_and_realtime_wait_ceiling(self):
        from app.requirements import extractor

        captured = {}

        class _CaptureRouter:
            async def chat(self, messages, **kwargs):
                captured.update(kwargs)
                return ChatResult(
                    text='[{"title":"Dark Mode Financial UI","category":"UI","priority":"High","confidence":95}]',
                    provider="gemini",
                    model="gemini-3.6-flash",
                )

        session = MeetingSession(meeting_id="m-fast-extract")
        session.add_transcript_line("vishesh", "en", "We need dark mode financial UI with OTP login")
        with mock.patch.object(extractor, "llm_router", _CaptureRouter()):
            found = await extractor.extract_new_requirements(session)

        self.assertEqual(len(found), 1)
        self.assertEqual(captured.get("reasoning_effort"), "low")
        self.assertEqual(captured.get("max_rate_limit_wait"), settings.llm_realtime_max_rate_limit_wait)
        self.assertEqual(captured.get("timeout"), settings.llm_realtime_timeout_seconds)

    async def test_realtime_max_rate_limit_wait_skips_long_retry(self):
        router = router_module.LLMRouter()
        slept = []

        async def rec_sleep(sec):
            slept.append(sec)

        class _Slow429:
            name = "gemini"
            is_configured = True
            candidates = ["m"]

            async def chat(self, messages, max_tokens, temperature, **kwargs):
                raise ProviderError("gemini", "rate limited", rate_limited=True, retry_after=15.0)

        class _FastGroq:
            name = "groq"
            is_configured = True
            candidates = ["m"]

            async def chat(self, messages, max_tokens, temperature, **kwargs):
                return ChatResult(text='[{"title":"Fast Point"}]', provider="groq", model="m")

        router.providers = [_Slow429(), _FastGroq()]
        with mock.patch.object(router_module.asyncio, "sleep", rec_sleep):
            res = await router.chat(
                [{"role": "user", "content": "hi"}],
                max_rate_limit_wait=settings.llm_realtime_max_rate_limit_wait,
                reasoning_effort="low",
                timeout=settings.llm_realtime_timeout_seconds,
            )

        self.assertEqual(res.provider, "groq")
        self.assertEqual(slept, [])

    async def test_provider_retries_without_reasoning_effort_on_400(self):
        prov = OpenAICompatibleProvider(
            base_url="https://example.invalid/v1",
            api_key="test-key",
            models="test-model",
            timeout=10.0,
        )
        seen_payloads = []

        class _FakeResp:
            def __init__(self, status_code, data):
                self.status_code = status_code
                self._data = data
                self.text = json.dumps(data)
                self.headers = {}

            def json(self):
                return self._data

        class _FakeClient:
            def __init__(self, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, url, headers=None, json=None):
                seen_payloads.append(dict(json))
                if "reasoning_effort" in json:
                    return _FakeResp(400, {"error": {"message": "Unknown parameter: reasoning_effort"}})
                return _FakeResp(200, {"choices": [{"message": {"content": "[]"}, "finish_reason": "stop"}]})

        with mock.patch("app.llm.providers.base.httpx.AsyncClient", _FakeClient):
            res = await prov.chat([{"role": "user", "content": "hi"}], 512, 0.2, reasoning_effort="low")

        self.assertEqual(res.text, "[]")
        self.assertEqual(res.finish_reason, "stop")
        self.assertIn("reasoning_effort", seen_payloads[0])
        self.assertNotIn("reasoning_effort", seen_payloads[1])
        self.assertIn("test-model", prov._no_reasoning_param_models)

    async def test_router_rotates_candidate_models_on_429_before_sleeping(self):
        router = router_module.LLMRouter()
        slept = []

        async def rec_sleep(sec):
            slept.append(sec)

        groq = OpenAICompatibleProvider(
            base_url="https://api.groq.com/openai/v1",
            api_key="test-key",
            models=["qwen/qwen3.8-27b", "openai/gpt-oss-20b"],
            timeout=10.0,
        )
        seen_models = []

        async def fake_post(messages, max_tokens, temperature, **kwargs):
            seen_models.append(groq.model)
            if groq.model == "qwen/qwen3.8-27b":
                raise ProviderError(
                    "groq", "rate limited (429), retry-after=12s",
                    model=groq.model, rate_limited=True, retry_after=12.0,
                )
            return ChatResult(text="arch spec ok", provider="groq", model=groq.model)

        groq._post_chat = fake_post
        router.providers = [groq]

        with mock.patch.object(router_module.asyncio, "sleep", rec_sleep):
            res = await router.chat([{"role": "user", "content": "hi"}], max_rate_limit_wait=35.0)

        self.assertEqual(res.model, "openai/gpt-oss-20b")
        self.assertEqual(seen_models, ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"])
        self.assertEqual(slept, [], "rotating to second model avoids 12s Retry-After sleep")

    async def test_router_rescues_using_cooled_provider_when_active_ones_fail(self):
        router = router_module.LLMRouter()

        class _CooledLead:
            name = "gemini"
            is_configured = True
            candidates = ["gemini-3.6-flash"]

            async def chat(self, messages, max_tokens, temperature, **kwargs):
                return ChatResult(text="rescued", provider="gemini", model="gemini-3.6-flash")

        class _FailingSecond:
            name = "groq"
            is_configured = True
            candidates = ["m-1"]

            async def chat(self, messages, max_tokens, temperature, **kwargs):
                raise ProviderError("groq", "rate limited (429)", model="m-1", rate_limited=True, retry_after=99.0)

        router.providers = [_CooledLead(), _FailingSecond()]
        router._start_cooldown("gemini")

        res = await router.chat([{"role": "user", "content": "hi"}], max_rate_limit_wait=5.0)
        self.assertEqual(res.provider, "gemini")
        self.assertEqual(res.text, "rescued")
        self.assertFalse(router._is_cooling_down("gemini"))

    def test_nim_default_candidates_exclude_eol_and_account_404_models(self):
        from app.llm.providers.nim import NimProvider

        nim = NimProvider()
        self.assertNotIn("openai/gpt-oss-20b", nim.candidates)
        self.assertNotIn("meta/llama-3.2-11b-vision-instruct", nim.candidates)
        self.assertNotIn("google/gemma-3-12b-it", nim.candidates)
        self.assertTrue(any("nemotron" in c or "minimax" in c for c in nim.candidates))


class SecurityAndStitchSandboxTest(unittest.IsolatedAsyncioTestCase):
    async def test_non_admitted_user_blocked_by_participant_guard(self):
        session = MeetingSession(meeting_id="m-sec-1", host_user_id="host-1")
        session_registry._sessions["m-sec-1"] = session
        try:
            host_user = type("U", (), {"id": "host-1"})()
            outsider = type("U", (), {"id": "outsider-2"})()
            admitted = type("U", (), {"id": "guest-3"})()
            session.approve_join("guest-3")

            self.assertIs(await require_meeting_participant("m-sec-1", host_user), session)
            self.assertIs(await require_meeting_participant("m-sec-1", admitted), session)
            with self.assertRaises(HTTPException) as ctx:
                await require_meeting_participant("m-sec-1", outsider)
            self.assertEqual(ctx.exception.status_code, 403)
        finally:
            session_registry._sessions.pop("m-sec-1", None)

    def test_llm_chat_route_requires_admin_dependency(self):
        from fastapi.routing import APIRoute
        from app.api.llm_test import router as llm_router_api
        from app.api.admin import require_admin

        routes = [r for r in llm_router_api.routes if isinstance(r, APIRoute) and r.path == "/llm/chat"]
        self.assertEqual(len(routes), 1)
        dep_calls = [d.call for d in routes[0].dependant.dependencies]
        self.assertIn(require_admin, dep_calls)

    async def test_joiner_can_lookup_meeting_summary_before_knock_while_ws_gates_admission(self):
        from app.api.meetings import get_meeting
        from app.ws import meeting as ws_meeting

        session = MeetingSession(meeting_id="m-join-1", name="Friend Call", host_user_id="host-1")
        session_registry._sessions["m-join-1"] = session
        try:
            friend = type("U", (), {"id": "friend-2"})()
            summary = await get_meeting("m-join-1", friend)
            self.assertEqual(summary["meeting_id"], "m-join-1")

            sent, closed = [], []

            class _FakeWS:
                cookies = {}
                headers = {}
                query_params = {}

                async def accept(self):
                    pass

                async def send_json(self, data):
                    sent.append(data)

                async def close(self, code=1000):
                    closed.append(code)

            with mock.patch.object(ws_meeting, "get_ws_user_id", new=mock.AsyncMock(return_value="friend-2")):
                await ws_meeting.meeting_socket(_FakeWS(), "m-join-1")

            self.assertEqual(closed, [4403])
        finally:
            session_registry._sessions.pop("m-join-1", None)

    def test_stitch_combined_screens_support_postmessage_navigation(self):
        combined = stitch_service._combine_screens(
            [{"title": "Overview"}, {"title": "Transactions"}],
            ["<html><body><h1>Overview</h1><a href='#'>Transactions</a></body></html>",
             "<html><body><h1>Transactions</h1><a href='#'>Overview</a></body></html>"],
        )
        self.assertIn("pp-show-screen", combined)
        self.assertIn("postMessage", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
