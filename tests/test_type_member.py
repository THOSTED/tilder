import unittest

import contenttypes
from config import load_config

CONF = None


def setUpModule():
    global CONF
    load_config()
    member = contenttypes.load([contenttypes.BUILTIN])["member"]
    CONF = {**member.DEFAULTS, "dir": "members", "type": "member",
            "categories": ["admin", "mentor", "member"]}


def item(slug="ada-lovelace", **meta):
    m = {"title": "Ada Lovelace", "description": "One sentence.", "first_name": "Ada", "last_name": "Lovelace"}
    m.update(meta)
    return {"slug": slug, "date": None, "meta": m, "src": None, "path": f"members/{slug}.html",
            "collection": "members", "conf": CONF, "type": contenttypes.TYPES["member"]}


class Member(unittest.TestCase):
    def setUp(self):
        self.member = contenttypes.TYPES["member"]

    def test_flags(self):
        self.assertFalse(self.member.DATED)
        self.assertFalse(self.member.ARTICLE)
        self.assertEqual(self.member.SCRIPT, "members.js")
        self.assertEqual(set(self.member.MARKERS), {"members"})
        self.assertFalse(self.member.HAS_FEED)

    def test_card_in_the_grid(self):
        node = self.member.entry(item(category="admin", pronouns="she/her", affiliation="Analytical Engines",
                                      github="https://github.com/ada https://github.com/engines",
                                      website="https://ada.example"), True, CONF)
        self.assertEqual(node["title"], "[Ada Lovelace](members/ada-lovelace)")
        self.assertEqual(node["cls"], [])
        self.assertEqual(node["meta"], ["she/her", "Analytical Engines", "`admin`"])
        self.assertEqual(node["data"], {"category": "admin", "search": "ada lovelace"})
        self.assertEqual(node["blocks"], [{"k": "profiles", "items": [
            ("github", "GitHub (ada)", "https://github.com/ada"),
            ("github", "GitHub (engines)", "https://github.com/engines"),
            ("website", "website", "https://ada.example"),
        ]}])

    def test_full_mentor_says_so(self):
        node = self.member.entry(item(category="mentor", capacity="2 per term", full="yes"), True, CONF)
        self.assertEqual(node["meta"], ["2 per term", "full", "`mentor`"])
        self.assertEqual(node["cls"], ["full"])

    def test_display_name_and_default_category(self):
        node = self.member.entry(item(display_name="Ada"), False, CONF)
        self.assertEqual(node["title"], "Ada")
        self.assertTrue(node["own"])
        self.assertEqual(node["meta"], ["`member`"])
        self.assertEqual(node["data"]["search"], "ada lovelace")

    def test_sort_key_category_then_last_name(self):
        admin = item("z", category="admin", last_name="Zuse")
        member = item("a", category="member", last_name="Émile")
        stray = item("q", category="guest", last_name="Q")
        keys = sorted([self.member.sort_key(it, CONF) for it in (stray, member, admin)])
        self.assertEqual([k[2] for k in keys], ["z", "a", "q"])
        self.assertEqual(self.member.sort_key(member, CONF)[1], "emile")

    def test_defaults(self):
        it = item()
        del it["meta"]["description"]
        self.member.defaults(it, CONF)
        self.assertEqual(it["meta"]["man"], "SITE-MEMBERS(7)")
        self.assertEqual(it["meta"]["nav"], "members")
        self.assertEqual(it["meta"]["description"], "")

    def test_grid_marker(self):
        r = self.member.MARKERS["members"]([item()], CONF)
        self.assertEqual(r["cls"], ["grid"])
        self.assertEqual(r["empty"], "No member listed yet.")
        self.assertEqual(len(r["items"]), 1)

    def test_list_data(self):
        self.assertEqual(self.member.list_data(CONF), {
            "search_label": "search", "search_placeholder": "first or last name",
            "all": "all", "one": "entry", "many": "entries", "none": "No entry matches."})

    def test_json_ld(self):
        node = self.member.json_ld(item(github="https://github.com/ada", affiliation="Engines"), CONF)
        self.assertEqual(node["@type"], "ProfilePage")
        self.assertEqual(node["mainEntity"]["sameAs"], ["https://github.com/ada"])
        self.assertEqual(node["mainEntity"]["affiliation"], {"@type": "Organization", "name": "Engines"})
        self.assertEqual(node["mainEntity"]["memberOf"], {"@id": "https://test.example/#organization"})
