import unittest

from tests.helpers import build_site


class Smoke(unittest.TestCase):
    def test_pages_are_built_twice(self):
        out = build_site()
        for page in ("index", "events", "members", "blog/index",
                     "blog/2026-01-01-hello", "events/2099-01-01-future-meetup",
                     "members/ada-lovelace"):
            self.assertIn(f"{page}.html", out, page)
        # Task 6 makes this members/alan-turing.html
        self.assertIn("members/alan-turing/index.html", out)
        self.assertIn("txt/index.txt", out)
        self.assertIn("ansi/index.txt", out)
        self.assertNotIn("txt/404.txt", out)  # text: no

    def test_upcoming_and_past_follow_the_fixed_date(self):
        out = build_site()
        events = out["events.html"]
        self.assertIn("Future meetup", events)
        self.assertIn("Past meetup", events)
        self.assertIn('class="tag tag--next">upcoming<', events)
        self.assertIn('class="tag">past<', events)

    def test_a_file_beside_a_member_page_is_copied(self):
        out = build_site()
        self.assertIn("members/alan-turing/notes.txt", out)
