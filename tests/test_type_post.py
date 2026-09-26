import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
from config import STATE, load_config

CONF = None


def setUpModule():
    global CONF
    load_config()
    STATE["today"] = "2026-06-15"
    post = contenttypes.load([contenttypes.BUILTIN])["post"]
    CONF = {**post.DEFAULTS, "dir": "blog", "type": "post", "feed": "blog/feed.xml"}


def item(**meta):
    m = {"title": "Hello", "description": "One sentence."}
    m.update(meta)
    return {"slug": "2026-01-01-hello", "date": "2026-01-01", "meta": m, "src": None,
            "path": "blog/2026-01-01-hello.html", "collection": "blog", "conf": CONF,
            "type": contenttypes.TYPES["post"]}


class Post(unittest.TestCase):
    def setUp(self):
        self.post = contenttypes.TYPES["post"]

    def test_flags(self):
        self.assertEqual(self.post.NAME, "post")
        self.assertTrue(self.post.DATED)
        self.assertTrue(self.post.ARTICLE)
        self.assertEqual(self.post.OG_TYPE, "article")
        self.assertEqual(self.post.LAYOUT, "post")
        self.assertEqual(set(self.post.MARKERS), {"posts"})
        self.assertTrue(self.post.HAS_FEED)

    def test_defaults_fill_the_front_matter(self):
        it = item()
        self.post.defaults(it, CONF)
        self.assertEqual(it["meta"]["man"], "SITE-BLOG(7)")
        self.assertEqual(it["meta"]["nav"], "blog/")
        self.assertEqual(it["meta"]["tagline"], "Thursday 1 January 2026")

    def test_card_in_a_list(self):
        node = self.post.entry(item(author="Ada", tag="note"), True, CONF)
        self.assertEqual(node, {
            "k": "entry", "id": None, "cls": ["link"], "own": False,
            "title": "[Hello](blog/2026-01-01-hello)",
            "meta": ["2026-01-01 | Thursday 1 January 2026", "Ada", "`note`"],
            "blocks": [{"k": "para", "text": "One sentence.", "cls": []}],
        })

    def test_card_on_its_own_page(self):
        node = self.post.entry(item(), False, CONF)
        self.assertEqual(node["title"], "Hello")
        self.assertTrue(node["own"])
        self.assertEqual(node["cls"], [])
        self.assertEqual(node["blocks"], [])

    def test_posts_marker_lists_newest_first(self):
        a, b = item(), item()
        b["slug"], b["date"] = "2026-02-01-later", "2026-02-01"
        r = self.post.MARKERS["posts"]([a, b], CONF)
        self.assertEqual([it["slug"] for it, _ in r["items"]], ["2026-02-01-later", "2026-01-01-hello"])
        self.assertEqual(r["empty"], "No post yet.")

    def test_json_ld(self):
        node = self.post.json_ld(item(author="Ada"), CONF)
        self.assertEqual(node["@type"], "BlogPosting")
        self.assertEqual(node["datePublished"], "2026-01-01")
        self.assertEqual(node["author"], {"@type": "Person", "name": "Ada"})
        self.assertEqual(node["publisher"], {"@id": "https://test.example/#organization"})

    def test_meta_tags(self):
        self.assertEqual(self.post.meta_tags(item(author="Ada", tag="note"), CONF), [
            ("name", "author", "Ada"),
            ("property", "article:published_time", "2026-01-01"),
            ("property", "article:tag", "note"),
        ])
        self.assertEqual(self.post.meta_tags(item(), CONF),
                         [("property", "article:published_time", "2026-01-01")])

    def test_feed_item(self):
        self.assertEqual(self.post.feed_item(item(), CONF), {
            "title": "Hello", "link": "https://test.example/blog/2026-01-01-hello",
            "description": "One sentence.", "date": "2026-01-01"})
