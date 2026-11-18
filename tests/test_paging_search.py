import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
import text
from config import load_config


def setUpModule():
    load_config()
    contenttypes.load([contenttypes.BUILTIN])


class Paging(unittest.TestCase):
    def test_paged_path(self):
        self.assertEqual(contenttypes.paged_path("blog/index.html", 1), "blog/index.html")
        self.assertEqual(contenttypes.paged_path("blog/index.html", 2), "blog/2.html")
        self.assertEqual(contenttypes.paged_path("events.html", 3), "events/3.html")

    def test_pager_links_the_neighbours(self):
        first = contenttypes._pager("blog/index.html", 1, 3)
        self.assertEqual(first["text"], "page 1 of 3 · [next](blog/2)")
        middle = contenttypes._pager("blog/index.html", 2, 3)
        self.assertEqual(middle["text"], "[previous](blog/) · page 2 of 3 · [next](blog/3)")
        self.assertEqual(middle["txt"], "previous : /blog/ · page 2 of 3 · next : /blog/3")
        last = contenttypes._pager("events.html", 2, 2)
        self.assertEqual(last["text"], "[previous](events) · page 2 of 2")


class Tags(unittest.TestCase):
    def test_post_tags_and_tag(self):
        post = contenttypes.TYPES["post"]
        self.assertEqual(post.tags({"tag": "réseau", "tags": "dns, tls, réseau"}), ["réseau", "dns", "tls"])
        self.assertEqual(post.tags({}), [])


class Sidebar(unittest.TestCase):
    def test_a_card_has_a_bar_down_its_side(self):
        lines = text.sidebar(["       Title", "       meta", "", "           body"], "     ")
        self.assertEqual(lines, ["     ,", "     | Title", "     | meta", "     |", "     |     body", "     '"])

    def test_tags_too_long_go_under_the_title(self):
        b = {"title": "A title", "meta": ["`" + w + "`" for w in ["one", "two"] * 8], "blocks": []}
        out = text.txt_entry(b, "     ")
        self.assertEqual(out[0], "     A title")
        self.assertTrue(out[1].startswith("     [ one ] [ two ]"))
        self.assertTrue(all(len(l) <= text.WIDTH for l in out))

    def test_a_linked_title_shows_its_url_under_it(self):
        out = text.txt_entry({"title": "[A post](blog/-/2026-01-01-a)", "meta": ["`news`"], "blocks": []}, "     ")
        self.assertTrue(out[0].startswith("     A post") and out[0].endswith("[ news ]"))
        self.assertEqual(out[1], "     /blog/-/2026-01-01-a")

    def test_internal_links_show_their_path(self):
        self.assertEqual(text.txt("see [the events](events) and [top](#top)"), "see the events (/events) and top")
        self.assertEqual(text.txt("[home](./#join), [feed](blog/feed.xml)"), "home (/#join), feed (/blog/feed.xml)")
