import json
import re
import unittest

from tests.helpers import build_site


def graph(html):
    data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return json.loads(data.replace("<\\/", "</"))["@graph"]


class Seo(unittest.TestCase):
    def test_each_type_has_its_node(self):
        out = build_site()
        kinds = {t["@type"] for t in graph(out["blog/2026-01-01-hello.html"])}
        self.assertIn("BlogPosting", kinds)
        kinds = {t["@type"] for t in graph(out["events/2099-01-01-future-meetup.html"])}
        self.assertIn("Event", kinds)
        kinds = {t["@type"] for t in graph(out["members/ada-lovelace.html"])}
        self.assertIn("ProfilePage", kinds)
        kinds = {t["@type"] for t in graph(out["index.html"])}
        self.assertIn("WebPage", kinds)

    def test_og_type_and_article_tags_only_for_posts(self):
        out = build_site()
        post = out["blog/2026-01-01-hello.html"]
        self.assertIn('<meta property="og:type" content="article">', post)
        self.assertIn('<meta name="author" content="Ada Lovelace">', post)
        self.assertIn('<meta property="article:published_time" content="2026-01-01">', post)
        self.assertIn('<meta property="article:tag" content="note">', post)
        event = out["events/2099-01-01-future-meetup.html"]
        self.assertIn('<meta property="og:type" content="website">', event)
        self.assertNotIn("article:published_time", event)

    def test_article_wrapper_for_posts_and_events_only(self):
        out = build_site()
        self.assertIn("<article>", out["blog/2026-01-01-hello.html"])
        self.assertIn("<article>", out["events/2099-01-01-future-meetup.html"])
        self.assertNotIn("<article>", out["members/ada-lovelace.html"])
        self.assertNotIn("<article>", out["index.html"])

    def test_sitemap_lastmod_is_the_item_date(self):
        out = build_site()
        self.assertIn("<loc>https://test.example/blog/2026-01-01-hello</loc>\n\t\t<lastmod>2026-01-01</lastmod>",
                      out["sitemap.xml"])
        self.assertIn("<loc>https://test.example/</loc>\n\t\t<lastmod>2026-06-01</lastmod>", out["sitemap.xml"])
        self.assertNotIn("/404", out["sitemap.xml"])
