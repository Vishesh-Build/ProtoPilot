"""
In-page navigation for the combined Stitch prototype.

The prototype used to be navigable only through a full-width top tab bar
(the .pp-tab-bar screen-switcher). A live user's complaint: clicking the
actual UI — a nav link, an "Explore Now" button, a restaurant card — did
nothing; only that top bar switched screens. This wires those in-page
clicks to real screen switches by matching a click's text against each
screen's distinctive title words, and demotes the tab bar to a discreet
corner fallback.

Two things get pinned here, because both are easy to regress:

  * The distinctive-token logic (_screen_nav_tokens): the invented brand
    word that appears in every title must be dropped (it names no single
    screen), stopwords must be dropped, and every screen must keep at least
    one token so it stays reachable by click.
  * The combined HTML (_combine_screens): each screen's iframe carries the
    nav script pointed at window.parent.ppShowScreen, the safety-net comes
    first so the nav script's capture listener wins, and the old dominant
    top tab bar is gone in favour of the corner switcher.

Run from the backend/ directory:
    python -m unittest tests.test_stitch_navigation -v
"""

import json
import re
import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.services import stitch_service  # noqa: E402


class ScreenNavTokensTest(unittest.TestCase):
    def test_the_invented_brand_word_is_dropped(self):
        # Exactly the live run's titles. "dineflow" is in all four, so it
        # identifies no screen and must not become a nav keyword — otherwise
        # every click carrying the brand would match the first screen.
        titles = [
            "Login | DineFlow",
            "The Hearth - Management | DineFlow",
            "Restaurants | DineFlow Admin",
            "User Management | DineFlow Admin",
        ]
        tokens = stitch_service._screen_nav_tokens(titles)
        for screen_tokens in tokens:
            self.assertNotIn("dineflow", screen_tokens,
                             "the brand word appears in every title — it names no single screen")

    def test_every_screen_keeps_at_least_one_distinctive_token(self):
        titles = [
            "Login | DineFlow",
            "The Hearth - Management | DineFlow",
            "Restaurants | DineFlow Admin",
            "User Management | DineFlow Admin",
        ]
        tokens = stitch_service._screen_nav_tokens(titles)
        self.assertEqual(len(tokens), 4)
        for i, screen_tokens in enumerate(tokens):
            self.assertTrue(screen_tokens, f"screen {i} has no token, so no click could ever reach it")

    def test_distinctive_words_land_on_the_right_screen(self):
        titles = [
            "Login | DineFlow",
            "The Hearth - Management | DineFlow",
            "Restaurants | DineFlow Admin",
            "User Management | DineFlow Admin",
        ]
        tokens = stitch_service._screen_nav_tokens(titles)
        self.assertIn("login", tokens[0])
        self.assertIn("restaurants", tokens[2])
        # "user" is unique to screen 3; "management" is shared with screen 1,
        # so the unique word must be what identifies it.
        self.assertIn("user", tokens[3])

    def test_stopwords_never_become_nav_keywords(self):
        # "Page"/"View"/"the" carry no meaning; a click on generic chrome
        # text like "View" must not yank the user to some screen.
        titles = ["Home Page", "Orders View", "Settings"]
        tokens = stitch_service._screen_nav_tokens(titles)
        flat = [t for screen in tokens for t in screen]
        for stop in ("page", "view", "the"):
            self.assertNotIn(stop, flat)

    def test_a_word_shared_by_some_screens_does_not_hijack_its_twin(self):
        # "Management" is in two titles. It must not be a keyword for either
        # while each still has its own unique word ("hearth", "user"), or a
        # click on one would ambiguously match the other.
        titles = [
            "The Hearth - Management | DineFlow",
            "User Management | DineFlow Admin",
        ]
        tokens = stitch_service._screen_nav_tokens(titles)
        self.assertIn("hearth", tokens[0])
        self.assertIn("user", tokens[1])
        self.assertNotIn("management", tokens[0])
        self.assertNotIn("management", tokens[1])


class CombineScreensNavigationTest(unittest.TestCase):
    SCREENS = [
        {"title": "Login | DineFlow", "html_url": "u0"},
        {"title": "Restaurants | DineFlow Admin", "html_url": "u1"},
        {"title": "User Management | DineFlow Admin", "html_url": "u2"},
    ]
    HTMLS = [
        "<html><body><h1>Login</h1></body></html>",
        "<html><body><a href='#'>Restaurants</a></body></html>",
        "<html><body><a href='#'>User Management</a></body></html>",
    ]

    def test_each_screen_gets_a_nav_script_pointed_at_the_parent(self):
        combined = stitch_service._combine_screens(self.SCREENS, self.HTMLS)
        # One nav script per screen, each calling the combiner's switcher via
        # the parent frame. The call form ppShowScreen(idx) appears once per
        # script (the guard check uses a different form), so it's the clean
        # per-screen marker. srcdoc escaping leaves it untouched — no quotes.
        self.assertEqual(combined.count("window.parent.ppShowScreen(idx)"), len(self.SCREENS))

    def test_the_dominant_top_tab_bar_is_gone(self):
        combined = stitch_service._combine_screens(self.SCREENS, self.HTMLS)
        # The old full-width sticky top bar is replaced by a corner switcher.
        self.assertNotIn('class="pp-tab-bar"', combined)
        self.assertIn("pp-switcher", combined)

    def test_the_corner_switcher_still_lists_every_screen(self):
        combined = stitch_service._combine_screens(self.SCREENS, self.HTMLS)
        # Fallback must stay complete — one switcher button per screen.
        self.assertEqual(combined.count('class="pp-tab-btn"'), len(self.SCREENS))
        for i in range(len(self.SCREENS)):
            self.assertIn(f'ppShowScreen({i})', combined)

    def test_nav_tokens_are_embedded_as_valid_json(self):
        # The script embeds the token table as JSON; a broken embed would
        # throw in the iframe and silently kill all in-page navigation. Test
        # the script builder directly — in the combined file the srcdoc is
        # HTML-escaped (" -> &quot;), which isn't valid JSON to re.search on.
        tokens = stitch_service._screen_nav_tokens([s["title"] for s in self.SCREENS])
        script = stitch_service._build_screen_nav_script(tokens, current_index=1)
        match = re.search(r"var NAV = (\{.*?\});", script)
        self.assertIsNotNone(match, "the nav script must embed a NAV payload")
        payload = json.loads(match.group(1))
        self.assertIn("tokens", payload)
        self.assertEqual(payload["current"], 1)
        self.assertEqual(len(payload["tokens"]), len(self.SCREENS))

    def test_single_screen_prototype_is_returned_untouched_but_for_safety_net(self):
        one = stitch_service._combine_screens(self.SCREENS[:1], self.HTMLS[:1])
        # No switcher chrome, no iframes — a single screen is the page itself.
        self.assertNotIn("pp-switcher", one)
        self.assertNotIn("srcdoc", one)


if __name__ == "__main__":
    unittest.main(verbosity=2)
