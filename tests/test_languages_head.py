import json
import re
import unittest

from tests.helpers import build_site


def graph(html):
    data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return json.loads(data.replace("<\\/", "</"))["@graph"]


class Head(unittest.TestCase):
    def test_hreflang_on_every_page(self):
        out = build_site()
        en, fr = out["events.html"], out["fr/events.html"]
        for page in (en, fr):
            self.assertIn('<link rel="alternate" hreflang="en" href="https://test.example/events">', page)
            self.assertIn('<link rel="alternate" hreflang="fr" href="https://test.example/fr/events">', page)
            self.assertIn('<link rel="alternate" hreflang="x-default" href="https://test.example/events">', page)
        self.assertIn('<link rel="alternate" hreflang="fr" href="https://test.example/fr/">', out["index.html"])
        self.assertIn('<link rel="alternate" hreflang="fr" href="https://test.example/fr/blog/">', out["blog/index.html"])
        self.assertIn('<link rel="canonical" href="https://test.example/fr/events">', fr)
        self.assertIn('<link rel="canonical" href="https://test.example/events">', en)

    def test_og_locale_and_alternate(self):
        out = build_site()
        self.assertIn('<meta property="og:locale" content="fr_FR">', out["fr/events.html"])
        self.assertIn('<meta property="og:locale:alternate" content="en_GB">', out["fr/events.html"])
        self.assertIn('<meta property="og:locale" content="en_GB">', out["events.html"])
        self.assertIn('<meta property="og:locale:alternate" content="fr_FR">', out["events.html"])
        self.assertIn('<meta property="og:url" content="https://test.example/fr/events">', out["fr/events.html"])

    def test_content_lang_and_html_lang(self):
        out = build_site()
        self.assertIn('<html lang="fr">', out["fr/members.html"])
        self.assertIn('<main id="contenu" lang="en">', out["fr/members.html"])     # fallback content
        self.assertIn('<main id="contenu" lang="fr">', out["fr/index.html"])
        self.assertIn('<html lang="en">', out["legal.html"])
        self.assertIn('<main id="contenu" lang="fr">', out["legal.html"])          # only French exists
        self.assertIn('<main id="contenu" lang="en">', out["index.html"])

    def test_in_language(self):
        out = build_site()
        page = next(n for n in graph(out["fr/members.html"]) if n["@type"] == "WebPage")
        self.assertEqual(page["inLanguage"], "en")
        site = next(n for n in graph(out["fr/members.html"]) if n["@type"] == "WebSite")
        self.assertEqual(site["inLanguage"], "fr")
        post = next(n for n in graph(out["fr/blog/2026-01-01-hello.html"]) if n["@type"] == "BlogPosting")
        self.assertEqual(post["inLanguage"], "fr")


class Switcher(unittest.TestCase):
    def test_languages_nav(self):
        out = build_site()
        self.assertIn('<nav class="languages" aria-label="Langues">\n'
                      '\t<a href="../events" hreflang="en" lang="en">English</a>\n'
                      '\t<a href="events" hreflang="fr" lang="fr" aria-current="page">Français</a>\n'
                      '</nav>', out["fr/events.html"])
        self.assertIn('<a href="events" hreflang="en" lang="en" aria-current="page">English</a>\n'
                      '\t<a href="fr/events" hreflang="fr" lang="fr">Français</a>', out["events.html"])
        self.assertIn('<a href="../../blog/" hreflang="en" lang="en">English</a>', out["fr/blog/index.html"])
        self.assertIn('<a href="../fr/blog/2026-01-01-hello" hreflang="fr" lang="fr">Français</a>',
                      out["blog/2026-01-01-hello.html"])

    def test_wordmark_language_segment(self):
        out = build_site()
        self.assertIn('<a href="./">fr</a>', out["fr/events.html"])           # the segment links to /fr/
        self.assertNotIn(">en</a>", out["events.html"])
        self.assertIn('<a href="../">fr</a>', out["fr/blog/2026-01-01-hello.html"])
