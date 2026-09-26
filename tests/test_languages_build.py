import unittest

from tests.helpers import build_site


class Passes(unittest.TestCase):
    def test_every_page_in_every_language(self):
        out = build_site()
        for p in ("index", "events", "members", "blog/index", "blog/2026-01-01-hello",
                  "blog/2026-02-01-only-french", "legal", "members/alan-turing", "404"):
            self.assertIn(f"{p}.html", out, p)
            self.assertIn(f"fr/{p}.html", out, p)
        self.assertIn("txt/fr/events.txt", out)
        self.assertIn("ansi/fr/events.txt", out)
        self.assertNotIn("txt/fr/404.txt", out)

    def test_translated_and_fallback_content(self):
        out = build_site()
        self.assertIn("fixtures en français", out["fr/index.html"])
        self.assertIn("<title>Bonjour - site de test</title>", out["fr/blog/2026-01-01-hello.html"])
        self.assertIn("<title>Hello - test site</title>", out["blog/2026-01-01-hello.html"])
        self.assertIn("Alan Turing", out["fr/members/alan-turing.html"])          # fallback: English content
        self.assertIn("Manuel du site de test", out["fr/members/alan-turing.html"])  # French interface
        self.assertIn("mentions légales", out["legal.html"])                       # only French exists
        self.assertIn("Seulement en français", out["blog/2026-02-01-only-french.html"])

    def test_words_and_dates_of_the_language(self):
        out = build_site()
        fr = out["fr/events.html"]
        self.assertIn('class="tag tag--next">à venir<', fr)
        self.assertIn("jeudi 1er janvier 2099", fr)
        self.assertIn('aria-label="Navigation principale"', fr)
        self.assertIn(">événements</a>", fr)
        self.assertIn("Thursday 1 January 2099", out["events.html"])

    def test_items_list_in_both_languages(self):
        out = build_site()
        self.assertIn(">Bonjour</a>", out["fr/blog/index.html"])
        self.assertIn(">Seulement en français</a>", out["fr/blog/index.html"])
        self.assertIn(">Hello</a>", out["blog/index.html"])
        self.assertIn(">Seulement en français</a>", out["blog/index.html"])     # fallback card
        self.assertIn('href="2026-02-01-only-french"', out["blog/index.html"])   # logical link, no suffix

    def test_feeds_per_language_calendar_once(self):
        out = build_site()
        self.assertIn("fr/blog/feed.xml", out)
        self.assertIn("<title>articles</title>", out["fr/blog/feed.xml"])
        self.assertIn("<title>Bonjour</title>", out["fr/blog/feed.xml"])
        self.assertIn("<link>https://test.example/fr/blog/2026-01-01-hello</link>", out["fr/blog/feed.xml"])
        self.assertIn("<language>fr</language>", out["fr/blog/feed.xml"])
        self.assertIn('<atom:link href="https://test.example/fr/blog/feed.xml"', out["fr/blog/feed.xml"])
        self.assertIn("<link>https://test.example/fr/blog/</link>", out["fr/blog/feed.xml"])
        self.assertEqual(out["blog/feed.xml"].count("<item>"), out["fr/blog/feed.xml"].count("<item>"))
        self.assertIn("events.ics", out)
        self.assertNotIn("fr/events.ics", out)
        self.assertIn("fr/talks.xml", out)

    def test_once_only_files(self):
        out = build_site()
        for f in ("sitemap.xml", "sitemap.txt", "robots.txt", "site.webmanifest", "logo.svg",
                  "members/alan-turing/notes.txt"):
            self.assertIn(f, out)
            self.assertNotIn(f"fr/{f}", out)

    def test_summary_names_the_languages(self):
        from config import STATE
        build_site()
        self.assertTrue(STATE["summary"].startswith("languages: en (default), fr\n"), STATE["summary"])
