import contextlib
import io
import json
import re
import textwrap
import unittest

from tests.helpers import build_site, rebuild
import contenttypes
from config import STATE, THEME, load_config


class ThemeType(unittest.TestCase):
    def test_loaded_from_the_theme(self):
        load_config()
        types = contenttypes.load()
        self.assertEqual(list(types), ["event", "member", "page", "post", "talk"])
        self.assertEqual(types["talk"].PATH.parent.name, "types")
        self.assertEqual(contenttypes.MARKERS["talks"], "talk")

    def test_lists_renders_twice_feeds_and_validates(self):
        out = build_site()
        page = out["talks.html"]
        self.assertIn('class="entry entry--next entry--link"', page)
        self.assertIn("<span>speaker: Grace Hopper</span>", page)
        self.assertIn("speaker: Grace Hopper", out["txt/talks.txt"])
        own = out["talks/2099-03-01-first-talk.html"]
        self.assertIn("<article>", own)
        self.assertIn("speaker: Grace Hopper", own)
        self.assertIn("<title>First talk</title>", out["talks.xml"])
        data = re.search(r'<script type="application/ld\+json">(.*?)</script>', own, re.S).group(1)
        self.assertIn("Event", {n["@type"] for n in json.loads(data)["@graph"]})
        self.assertIn("SITE-TALKS(7)", out["txt/talks/2099-03-01-first-talk.txt"])
        self.assertNotIn("types/talk.py", out)                     # never served

    def test_summary_names_the_theme_type(self):
        load_config()
        contenttypes.load()
        colls = contenttypes.collections()
        items = {n: contenttypes.load_items(n, c) for n, c in colls.items()}
        self.assertTrue(contenttypes.summary(colls, items).startswith(
            "types: event, member, page, post; from theme: talk\n"))

    def test_empty_list_text_is_the_talks_own(self):
        load_config()
        talk = contenttypes.load()["talk"]
        chosen = talk.MARKERS["talks"]([], {**talk.DEFAULTS})
        self.assertEqual(chosen["items"], [])
        self.assertEqual(chosen["empty"], "No upcoming talk.")

    def test_theme_member_replaces_the_builtin_silently(self):
        mine = THEME / "types" / "member.py"
        mine.write_text(textwrap.dedent('''
            from contenttypes import TYPES
            builtin = TYPES["member"]
            NAME = "member"
            SCRIPT = builtin.SCRIPT
            DEFAULTS = builtin.DEFAULTS
            MARKERS = {"members": builtin.MARKERS["members"]}
            defaults, sort_key = builtin.defaults, builtin.sort_key
            json_ld, list_data = builtin.json_ld, builtin.list_data

            def entry(item, link, conf):
                node = builtin.entry(item, link, conf)
                node["title"] += " (theme card)"
                return node
        '''))
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                out = rebuild()
        finally:
            mine.unlink()
            for cached in (THEME / "types" / "__pycache__").glob("member.*"):
                cached.unlink()
        self.assertIn("(theme card)", out["members.html"])
        self.assertEqual(STATE["summary"].splitlines()[0],
                         "types: event, page, post; from theme: member, talk")
        self.assertNotIn("member", "".join(l for l in err.getvalue().splitlines(True)
                                           if l.startswith("warning:")))
