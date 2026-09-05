"""
Gemini as the optional lead provider.

Two promises get pinned here, because both matter to the fix:

  * When a GEMINI_API_KEY is configured, Gemini LEADS the fallback chain.
    Groq's free tier is 8000 tokens/minute and one 9-agent generation needs
    ~25k, so Groq-first means minutes of waiting on that ceiling — the rate
    limit the live demo died on. Gemini's far larger free budget is only
    useful if it is actually tried first.
  * When it is NOT configured it is skipped, and the chain is exactly what
    it was before Gemini existed (Groq -> NIM -> OpenRouter). Adding a lead
    provider must not change the meeting path for anyone without the key.

Run from the backend/ directory:
    python -m unittest tests.test_gemini_provider -v
"""

import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.llm import router as router_module  # noqa: E402
from app.llm.providers.gemini import GeminiProvider  # noqa: E402


class GeminiProviderTest(unittest.TestCase):
    def test_talks_to_the_openai_compatible_endpoint(self):
        # The whole reason it can reuse OpenAICompatibleProvider unchanged:
        # base.py appends /chat/completions and /models to this base_url, so
        # it must be the …/v1beta/openai surface, not the native Gemini API.
        provider = GeminiProvider()
        self.assertEqual(provider.name, "gemini")
        self.assertIn("generativelanguage.googleapis.com", provider.base_url)
        self.assertTrue(
            provider.base_url.endswith("/openai"),
            "must point at the OpenAI-compatible surface so /chat/completions resolves",
        )

    def test_leads_with_a_flash_model(self):
        # gemini-3.6-flash leads: Google's recommended-stable flash, the one
        # that reliably answers 200 not 503, checked live 2026-09-04 (the
        # older gemini-2.5-flash now 404s "no longer available to new users").
        # gemini-3.8-flash sits behind it as the newer backstop.
        provider = GeminiProvider()
        self.assertEqual(provider.candidates[0], "gemini-3.6-flash")
        self.assertIn("gemini-3.8-flash", provider.candidates)

    def test_no_key_means_unconfigured_so_the_meeting_path_is_unchanged(self):
        # The contract that keeps adding Gemini zero-risk: with no key it
        # reports unconfigured, the router skips it, and the chain is the old
        # Groq-first one. Force the key off rather than trusting the ambient
        # environment — on a fully-installed machine the real pydantic-settings
        # reads backend/.env (the stub only stands in when the package is
        # missing), so a developer who added a real GEMINI_API_KEY must not
        # flip this test red. The logic under test is is_configured, not .env.
        provider = GeminiProvider()
        provider.api_key = None
        self.assertFalse(provider.is_configured)

    def test_a_key_turns_it_on(self):
        provider = GeminiProvider()
        provider.api_key = "test-key-not-real"
        self.assertTrue(provider.is_configured)


class RouterLeadsWithGeminiTest(unittest.TestCase):
    def test_gemini_is_first_then_the_old_chain(self):
        names = [p.name for p in router_module.LLMRouter().providers]
        self.assertEqual(
            names, ["gemini", "groq", "nim", "openrouter"],
            "Gemini must lead so its large free budget is tried before Groq's 8000 TPM ceiling",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
