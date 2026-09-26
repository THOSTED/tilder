import unittest

import report
from config import CONTENT, layout
from tests.helpers import build_site


class Layouts(unittest.TestCase):
    def test_type_layout_when_the_theme_has_it(self):
        out = build_site()
        self.assertIn('<body class="layout-event event">', out["events/2099-01-01-future-meetup.html"])
        self.assertIn("<body>", out["blog/2026-01-01-hello.html"])          # post: no layouts/post.html, falls back
        self.assertIn("<body>", out["members/ada-lovelace.html"])
        self.assertNotIn("layouts/event.html", out)                          # never served

    def test_front_matter_layout_wins(self):
        # The event layout, asked for by a plain page.
        page = CONTENT / "special.md"
        page.write_text("---\nman: TEST(1)\ntitle: special\ndescription: A page that asks for the event layout.\n"
                        "tagline: t\nnav: -\nlayout: event\n---\n\n## Name\n\nspecial {mono}\n")
        try:
            from tests.helpers import rebuild
            out = rebuild()
        finally:
            page.unlink()
        self.assertIn('<body class="layout-event page">', out["special.html"])

    def test_unknown_layout_asked_for_is_an_error(self):
        with self.assertRaises(report.BuildError) as cm:
            layout("nope", asked_by=CONTENT / "x.md")
        self.assertEqual(str(cm.exception),
                         'content/x.md: layout "nope" names no theme/layouts/nope.html. '
                         "Add that file to the theme, or drop `layout:`")

    def test_unknown_type_layout_falls_back_silently(self):
        path, text = layout("nope")
        self.assertEqual(path.name, "layout.html")

    def test_unknown_placeholder_names_the_layout_file(self):
        import page
        with self.assertRaises(report.BuildError) as cm:
            page.fill("<p>{{ nothing.here }}</p>", {}, {}, CONTENT.parent / "theme" / "layout.html")
        self.assertIn("theme/layout.html: unknown placeholder {{ nothing.here }}", str(cm.exception))
