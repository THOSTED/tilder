"""What docs/markdown.md says about edge cases, pinned: an event's past by
its start date, an italic lead-in, the callout's role, an all-bold
paragraph, and the backslash that escapes nothing."""

import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
import markdown
import page
import text
from config import STATE, load_config


def setUpModule():
    load_config()


def render(line):
    """One source line -> (node, HTML, plain text)."""
    node = markdown.classify([line])
    html = "".join(page.html_blocks([node], lambda u: u, ind=""))
    txt = text.plain("\n".join(text.txt_blocks([node], "")))
    return node, html, txt


class Documented(unittest.TestCase):
    def test_an_event_is_past_once_its_start_date_has_gone_by(self):
        STATE["today"] = "2026-06-15"
        event = contenttypes.load([contenttypes.BUILTIN])["event"]
        conf = {**event.DEFAULTS, "dir": "events", "type": "event"}
        # Started yesterday, ends tomorrow: already past.
        item = {"slug": "2026-06-14-camp", "date": "2026-06-14", "src": None,
                "meta": {"title": "Camp", "description": "Two days.", "end": "2026-06-16"},
                "path": "events/2026-06-14-camp.html", "collection": "events",
                "conf": conf, "type": event}
        self.assertIn("`past`", event.entry(item, True, conf)["meta"])
        self.assertEqual([i["slug"] for i, _ in event.MARKERS["past"]([item], conf)["items"]],
                         ["2026-06-14-camp"])
        self.assertEqual(event.MARKERS["upcoming"]([item], conf)["items"], [])
        today = {**item, "slug": "2026-06-15-talk", "date": "2026-06-15"}
        self.assertIn("`upcoming`", event.entry(today, True, conf)["meta"])

    def test_an_italic_lead_in_is_an_ordinary_paragraph(self):
        node, html, txt = render("*Soon.* Check back later.")
        self.assertEqual(node["k"], "para")
        self.assertEqual(html, "<p><em>Soon.</em> Check back later.</p>")
        self.assertEqual(txt, "Soon. Check back later.")

    def test_every_callout_is_a_note(self):
        for kind in ("INFO", "WARNING", "ERROR"):
            _, html, _ = render(f"> [!{kind}] Text.")
            self.assertIn('role="note"', html)
            self.assertNotIn('role="alert"', html)

    def test_an_all_bold_paragraph_is_an_empty_state_in_italics(self):
        node, html, txt = render("**All bold.**")
        self.assertEqual(node["k"], "empty")
        self.assertEqual(html, '<p class="empty"><em>All bold.</em></p>')
        self.assertEqual(txt, "All bold.")

    def test_a_backslash_escapes_nothing(self):
        _, html, txt = render(r"a \*b* c")
        self.assertEqual(html, r"<p>a \<em>b</em> c</p>")
        self.assertEqual(txt, r"a \b c")


if __name__ == "__main__":
    unittest.main()
