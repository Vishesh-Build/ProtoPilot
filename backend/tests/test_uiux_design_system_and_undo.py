"""
Tests for UI/UX Pro Max Design System Engine, domain-adaptive human-grade
prototype synthesis, and Prototype Backup / Undo checkpointing.
"""

import io
import unittest
import zipfile
from unittest import mock

from app.agents import orchestrator
from app.agents.design_system import build_prototype_design_brief, build_ui_design_brief, resolve_design_system
from app.agents.prototype_fallback import build_executive_prototype_html
from app.api.meetings import TweakPrototypeRequest, UndoPrototypeRequest, get_agent_outputs, tweak_prototype, undo_prototype
from app.exports.builder import build_export_zip
from app.llm.providers.base import ChatResult
from app.meetings.session import MeetingSession, Requirement


class DesignSystemResolutionTest(unittest.TestCase):
    def test_healthcare_defaults_to_calm_clinical_light_theme(self):
        ds = resolve_design_system("Clinic appointment booking, patient records, and prescription PDF download")
        self.assertEqual(ds["domain"], "healthcare")
        self.assertEqual(ds["mode"], "light")
        self.assertTrue(ds["prefer_light"])
        self.assertEqual(ds["tokens"].accent, "#0F766E")

    def test_fintech_india_upi_uses_inr_and_respects_dark_only_when_requested(self):
        ds_light = resolve_design_system("UPI expense tracker and GST invoicing web app")
        self.assertEqual(ds_light["domain"], "fintech")
        self.assertEqual(ds_light["locale"], "IN")
        self.assertEqual(ds_light["currency_symbol"], "₹")
        self.assertEqual(ds_light["mode"], "light")

        ds_dark = resolve_design_system("Dark mode financial web app UI with auto-sync UPI transactions")
        self.assertEqual(ds_dark["domain"], "fintech")
        self.assertEqual(ds_dark["locale"], "IN")
        self.assertEqual(ds_dark["mode"], "dark")
        self.assertEqual(ds_dark["tokens"].bg, "#0A0C10")

    def test_commerce_uses_warm_editorial_ivory_palette_and_website_layout(self):
        ds = resolve_design_system("Online sneaker storefront website with catalog filters, wishlist, shopping cart, and checkout")
        self.assertEqual(ds["domain"], "commerce")
        self.assertEqual(ds["layout_mode"], "website")
        self.assertEqual(ds["mode"], "light")
        self.assertEqual(ds["tokens"].bg, "#FAF9F6")
        self.assertEqual(ds["tokens"].accent, "#C2410C")

        web_html = build_executive_prototype_html(
            states=None,
            requirements_block=(
                "- [High] Sneaker & Streetwear Storefront Website (Storefront)\n"
                "- [High] Product Quick-View, Wishlist & Slide-Over Shopping Bag (Cart)\n"
                "- [Medium] Promo Code WELCOME10 & Order Tracking (Orders)"
            ),
        )
        ok, reason = orchestrator.validate_prototype_html(web_html)
        self.assertTrue(ok, reason)
        self.assertIsNone(orchestrator._diagnose_prototype_quality(web_html))
        self.assertIn("Featured Catalog", web_html)
        self.assertIn("cart-backdrop", web_html)
        self.assertIn("WELCOME10", web_html)
        self.assertIn("light-theme-toggle", web_html)
        self.assertNotIn("sidebar", web_html.lower())

    def test_synthesized_prototype_has_real_axes_2026_dates_and_zero_slop_cliches(self):
        req_block = (
            "- [High] Mobile Number & OTP Authentication (Auth)\n"
            "- [High] Auto-sync UPI Transactions (Payments)\n"
            "- [Medium] Real-time Expense & Cashflow Analytics (Analytics)"
        )
        html = build_executive_prototype_html(states=None, requirements_block=req_block)
        ok, reason = orchestrator.validate_prototype_html(html)
        self.assertTrue(ok, reason)
        self.assertIsNone(orchestrator._diagnose_prototype_quality(html))
        self.assertNotIn("Whole Foods Market", html)
        self.assertNotIn("Oct 24, 2023", html)
        self.assertIn("2026", html)
        self.assertIn("₹", html)
        self.assertIn("formatYTick", html)
        self.assertIn("light-theme-toggle", html)
        # Ensure brief builder injects domain tokens and anti-patterns cleanly
        brief = build_prototype_design_brief(req_block)
        self.assertIn("Mercury / Stripe", brief)
        self.assertIn("Oct 24, 2023", brief)  # banned list explicitly mentioned in instructions
        ui_brief = build_ui_design_brief(req_block)
        self.assertIn("₹ INR", ui_brief)


class PrototypeUndoWorkflowTest(unittest.IsolatedAsyncioTestCase):
    async def test_tweak_pushes_backup_and_undo_restores_original_prototype(self):
        orig_html = (
            "<!DOCTYPE html><html><head><style>body{margin:0;color:#111;background:#fff;}</style></head>"
            "<body><h1>Original LedgerCraft Workspace</h1>"
            "<div class='nav-item'>Overview</div><button onclick='x()'>Filter</button><button onclick='y()'>Create</button>"
            "<svg viewBox='0 0 200 100'><rect x='10' y='10' width='40' height='80'/></svg>"
            "<p>" + ("Realistic domain table entries and financial cashflow insights ready for inspection. " * 12) + "</p>"
            "<script>function x(){} function y(){}</script></body></html>"
        )
        tweaked_html = orig_html.replace("Original LedgerCraft Workspace", "Tweaked Dark LedgerCraft Workspace")

        session = MeetingSession(meeting_id="m-undo-1", name="FinTech Demo", host_user_id="host-1")
        session.requirements.append(Requirement(id=1, title="Auto-sync UPI", category="Payments", priority="High", confidence=95, status="approved"))
        session.agent_outputs["prototype"] = orig_html

        fake_router = mock.AsyncMock()
        fake_router.chat.return_value = ChatResult(text=tweaked_html, provider="gemini", model="gemini-3.5-flash-lite", finish_reason="stop")
        broadcasts = []

        async def rec_broadcast(mid, payload):
            broadcasts.append((mid, payload))

        with mock.patch("app.llm.router.llm_router", fake_router), \
             mock.patch("app.core.connection_manager.meeting_connections.broadcast", new=rec_broadcast):
            out_before = await get_agent_outputs(session=session)
            self.assertFalse(out_before["can_undo"])

            res = await tweak_prototype(TweakPrototypeRequest(prompt="Switch theme to dark mode"), session=session)
            self.assertEqual(res["status"], "success")
            self.assertTrue(res["can_undo"])
            self.assertIn("Tweaked Dark LedgerCraft Workspace", session.agent_outputs["prototype"])

            undone = await undo_prototype(UndoPrototypeRequest(), session=session)
            self.assertEqual(undone["status"], "restored")
            self.assertFalse(undone["can_undo"])
            self.assertEqual(session.agent_outputs["prototype"], orig_html)
            self.assertEqual(len(broadcasts), 2)
            self.assertEqual(broadcasts[-1][1]["prototype"], orig_html)

            # Fallback client-checkpoint restore also works after server restart clears memory stack
            session.agent_outputs["prototype"] = tweaked_html
            session.prototype_history.clear()
            undone_fallback = await undo_prototype(UndoPrototypeRequest(previous_html=orig_html), session=session)
            self.assertEqual(undone_fallback["prototype"], orig_html)

        # Ensure ZIP export only includes real deliverables and never pollutes outputs
        zbytes = build_export_zip(session)
        with zipfile.ZipFile(io.BytesIO(zbytes), "r") as zf:
            names = set(zf.namelist())
            self.assertIn("09_prototype.html", names)
            self.assertNotIn("prototype_history", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
