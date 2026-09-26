import pathlib
import shutil
import unittest

from tests.helpers import build_site
from tests.test_languages import run, scratch


class Sitemap(unittest.TestCase):
    def test_alternates(self):
        out = build_site()
        sm = out["sitemap.xml"]
        self.assertIn('xmlns:xhtml="http://www.w3.org/1999/xhtml"', sm)
        self.assertIn("\t<url>\n\t\t<loc>https://test.example/fr/events</loc>\n\t\t<lastmod>2026-06-01</lastmod>\n"
                      '\t\t<xhtml:link rel="alternate" hreflang="en" href="https://test.example/events"/>\n'
                      '\t\t<xhtml:link rel="alternate" hreflang="fr" href="https://test.example/fr/events"/>\n'
                      '\t\t<xhtml:link rel="alternate" hreflang="x-default" href="https://test.example/events"/>\n'
                      "\t</url>\n", sm)
        self.assertIn("https://test.example/fr/blog/2026-02-01-only-french\n", out["sitemap.txt"])
        self.assertIn("https://test.example/blog/2026-02-01-only-french\n", out["sitemap.txt"])
        self.assertNotIn("/404", out["sitemap.txt"])


class TextMirror(unittest.TestCase):
    def test_languages_line(self):
        out = build_site()
        lines = out["txt/events.txt"].splitlines()
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "LANGUAGES: en fr")
        self.assertIn("LANGUAGES: en fr", out["txt/fr/events.txt"])
        self.assertIn("[ a venir ]", out["txt/fr/events.txt"])                   # folded
        self.assertIn("jeudi 1er janvier 2099", out["txt/fr/events.txt"])


class Monolingual(unittest.TestCase):
    """A site that declares no languages: not one byte of the feature."""

    def setUp(self):
        self.tmp, self.site = scratch()
        content = self.site / "content"
        toml = content / "site.toml"
        toml.write_text("\n".join(l for l in toml.read_text().splitlines()
                                  if not l.startswith("languages =") and l.split("#")[0].strip() not in
                                  ('[languages]', 'en = "English"', 'fr = "Français"')) + "\n")
        (content / "site.fr.toml").unlink()
        for f in list(content.rglob("*.fr.md")):
            f.unlink()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_nothing_of_the_feature(self):
        code, err = run(self.site)
        self.assertEqual(code, 0, err)
        out = self.site / "out"
        self.assertFalse((out / "fr").exists())
        index = (out / "index.html").read_text()
        self.assertNotIn("hreflang", index)
        self.assertNotIn('<nav class="languages"', index)
        self.assertNotIn("og:locale:alternate", index)
        self.assertIn('<main id="contenu" lang="en">', index)
        self.assertNotIn("xmlns:xhtml", (out / "sitemap.xml").read_text())
        self.assertNotIn("LANGUAGES:", (out / "txt" / "index.txt").read_text())
