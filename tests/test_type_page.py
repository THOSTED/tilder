import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
from config import load_config


class Page(unittest.TestCase):
    def setUp(self):
        load_config()
        self.page = contenttypes.load([contenttypes.BUILTIN])["page"]

    def test_a_page_has_no_card(self):
        item = {"slug": "index", "date": None, "meta": {"title": "t", "description": "d"},
                "path": "index.html", "collection": None, "conf": {}, "type": self.page}
        self.assertIsNone(self.page.entry(item, False, {}))
        self.assertFalse(self.page.DATED)
        self.assertEqual(self.page.MARKERS, {})

    def test_web_page_node(self):
        item = {"meta": {"title": "about", "description": "d"}, "path": "about.html", "conf": {}}
        node = self.page.json_ld(item, {})
        self.assertEqual(node, {"@type": "WebPage", "name": "about - test site", "description": "d",
                                "isPartOf": {"@id": "https://test.example/#website"}})
