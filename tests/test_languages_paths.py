import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
import languages
import paths
from config import CONTENT


class Table(unittest.TestCase):
    def setUp(self):
        languages.setup()
        contenttypes.load()
        for name, conf in contenttypes.collections().items():
            contenttypes.load_items(name, conf)

    def test_pages_grouped_by_logical_path(self):
        table = languages.pages()
        self.assertEqual(set(table["index.md"]), {None, "fr"})
        self.assertEqual(table["index.md"]["fr"], CONTENT / "index.fr.md")
        self.assertEqual(set(table["blog/2026-01-01-hello.md"]), {None, "fr"})
        self.assertEqual(set(table["legal.md"]), {"fr"})
        self.assertEqual(set(table["members/alan-turing/index.md"]), {None})
        self.assertNotIn("members/_template.md", table)

    def test_rendered_and_page_path_strip_the_suffix(self):
        self.assertTrue(paths.rendered(CONTENT / "index.fr.md"))
        self.assertEqual(paths.page_path(CONTENT / "index.fr.md"), "index.html")
        self.assertEqual(paths.page_path(CONTENT / "blog/2026-01-01-hello.fr.md"), "blog/2026-01-01-hello.html")
        self.assertEqual(paths.page_path(CONTENT / "members/alan-turing/index.md"), "members/alan-turing.html")


class Urls(unittest.TestCase):
    def setUp(self):
        languages.setup()

    def test_clean_url_takes_the_prefix(self):
        self.assertEqual(paths.clean_url("index.html"), "/")
        self.assertEqual(paths.clean_url("index.html", "fr"), "/fr/")
        self.assertEqual(paths.clean_url("events.html", "fr"), "/fr/events")
        self.assertEqual(paths.clean_url("blog/index.html", "fr"), "/fr/blog/")
        languages.use("fr")
        try:
            self.assertEqual(paths.clean_url("events.html"), "/fr/events")
            self.assertEqual(paths.absolute("blog/feed.xml"), "https://test.example/fr/blog/feed.xml")
        finally:
            languages.use("en")
        self.assertEqual(paths.absolute("blog/feed.xml"), "https://test.example/blog/feed.xml")

    def test_relative_links_stay_in_the_language(self):
        languages.use("fr")
        try:
            self.assertEqual(paths.relative("", "events"), "events")          # fr/about -> fr/events
            self.assertEqual(paths.relative("blog", "events"), "../events")
            self.assertEqual(paths.relative("", ""), "./")
            self.assertEqual(paths.relative("", "/events"), "../events")      # site root: the default language
            self.assertEqual(paths.relative("blog", "/"), "../../")
            self.assertEqual(paths.relative("", "/fr/events"), "events")      # explicit, same language
            self.assertEqual(paths.relative("", "/events#x"), "../events#x")
        finally:
            languages.use("en")
        self.assertEqual(paths.relative("", "/events"), "events")            # default pass: root is the root
        self.assertEqual(paths.relative("blog", "/fr/"), "../fr/")

    def test_file_targets_resolve_from_the_site_root(self):
        languages.use("fr")
        try:
            self.assertEqual(paths.relative("", "style.css"), "../style.css")
            self.assertEqual(paths.relative("blog", "logo.svg"), "../../logo.svg")
            self.assertEqual(paths.relative("blog", "2026-01-01-x/p.svg"), "../../2026-01-01-x/p.svg")
            self.assertEqual(paths.relative("blog", "blog/2026-01-01-x/p.svg"), "../../blog/2026-01-01-x/p.svg")
            self.assertEqual(paths.relative("", "events"), "events")          # pages stay in the language
            self.assertEqual(paths.relative("", "blog/"), "blog/")
            self.assertEqual(paths.relative("", "blog/feed.xml", page=True), "blog/feed.xml")  # a feed
        finally:
            languages.use("en")
        self.assertEqual(paths.relative("", "events.ics"), "events.ics")
        self.assertEqual(paths.relative("blog", "style.css"), "../style.css")
        self.assertTrue(paths.is_file("docs/x.pdf"))
        self.assertFalse(paths.is_file("blog/"))
        self.assertFalse(paths.is_file("blog/hello"))
        self.assertFalse(paths.is_file(""))


class DefaultPassFallback(unittest.TestCase):
    def test_pages_only_in_french_exist_at_the_root(self):
        out = helpers.rebuild()
        self.assertIn("legal.html", out)
        self.assertIn("mentions légales", out["legal.html"])
        self.assertNotIn("legal.fr.html", out)
        self.assertNotIn("index.fr.html", out)
        self.assertIn("test site", out["index.html"])                       # English wins at the root
