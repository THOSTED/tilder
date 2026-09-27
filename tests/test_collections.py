import pathlib
import tempfile
import unittest

from tests.helpers import build_site  # triggers tests.__init__ setup
import contenttypes
import languages
import paths
import report
from config import CFG, CONTENT


class Collections(unittest.TestCase):
    def setUp(self):
        languages.setup()
        contenttypes.load()

    def test_declared_collections_merge_type_defaults(self):
        colls = contenttypes.collections()
        self.assertEqual(list(colls), ["blog", "events", "members", "news", "talks", "guides", "manual"])
        self.assertEqual(colls["blog"]["type"], "post")
        self.assertEqual(colls["blog"]["dir"], "blog")
        self.assertEqual(colls["blog"]["feed"], "blog/feed.xml")
        self.assertEqual(colls["blog"]["empty"], "No post yet.")          # from post.DEFAULTS
        self.assertEqual(colls["members"]["categories"], ["admin", "mentor", "member"])
        self.assertEqual(colls["members"]["search_label"], "search")     # from member.DEFAULTS

    def test_missing_folder_is_an_empty_collection(self):
        colls = contenttypes.collections()
        self.assertEqual(contenttypes.load_items("news", colls["news"]), [])
        out = build_site()
        self.assertFalse(any(k.startswith("news") for k in out), [k for k in out if k.startswith("news")])

    def test_items_are_sorted_by_the_type(self):
        colls = contenttypes.collections()
        events = contenttypes.load_items("events", colls["events"])
        self.assertEqual([e["slug"] for e in events], ["2000-01-01-past-meetup", "2099-01-01-future-meetup"])
        self.assertEqual(events[0]["date"], "2000-01-01")
        self.assertEqual(events[0]["path"], "events/2000-01-01-past-meetup.html")
        self.assertIs(events[0]["type"], contenttypes.TYPES["event"])
        self.assertEqual(events[0]["meta"]["man"], "SITE-EVENTS(7)")   # defaults() applied
        members = contenttypes.load_items("members", colls["members"])
        self.assertEqual([m["slug"] for m in members], ["ada-lovelace", "alan-turing"])  # admin first
        self.assertIsNone(members[0]["date"])

    def test_member_folder_registers_and_renders_flat(self):
        colls = contenttypes.collections()
        contenttypes.load_items("members", colls["members"])
        self.assertIn("members/alan-turing", paths.ITEM_FOLDERS)
        self.assertTrue(paths.rendered(CONTENT / "members/alan-turing/index.md"))
        self.assertFalse(paths.rendered(CONTENT / "members/alan-turing/notes.txt"))
        self.assertEqual(paths.page_path(CONTENT / "members/alan-turing/index.md"), "members/alan-turing.html")
        out = build_site()
        self.assertIn("members/alan-turing.html", out)
        self.assertNotIn("members/alan-turing/index.html", out)
        self.assertIn("members/alan-turing/notes.txt", out)

    def fails_with(self, *fragments):
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.collections()
        text = "\n".join(m for m, _ in cm.exception.items)
        for f in fragments:
            self.assertIn(f, text)
        return text

    def test_plural_type_is_refused_with_the_fix(self):
        CFG["collections"]["blog"]["type"] = "posts"
        self.fails_with('collection "blog" has type "posts"; types are singular', 'Write type = "post"')

    def test_unknown_type_lists_the_loaded_ones(self):
        CFG["collections"]["keynotes"] = {"type": "keynote"}   # no such type, unlike theme's "talk"
        text = self.fails_with('collection "keynotes" has type "keynote", which no type defines', "Types loaded:")
        self.assertIn("event, member, page, post (types/)", text)   # load order: file names

    def test_old_members_table_is_refused(self):
        CFG["members"] = {"categories": ["a"]}
        self.fails_with("[members] is no longer read", "[collections.members]")

    def test_old_collection_defaults_table_is_refused(self):
        CFG["collection_defaults"] = {"empty": "x"}
        self.fails_with("content/site.toml: [collection_defaults] is no longer read",
                        "the defaults live in types/<type>.py")

    def test_overlapping_dirs(self):
        CFG["collections"]["also"] = {"type": "post", "dir": "blog"}
        self.fails_with('collections "blog" and "also" share the folder content/blog')

    def test_errors_are_gathered(self):
        CFG["collections"]["blog"]["type"] = "posts"
        CFG["collections"]["keynotes"] = {"type": "keynote"}   # no such type, unlike theme's "talk"
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.collections()
        self.assertEqual(len(cm.exception.items), 2)

    def test_type_and_collection_errors_are_reported_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "clash.py").write_text(
                'NAME = "clash"\nMARKERS = {"upcoming": lambda items, conf: {}}\n'
                "def entry(item, link, conf): return None\n")
            contenttypes.load([contenttypes.BUILTIN, pathlib.Path(tmp)])   # gathers, does not raise
        CFG["collections"]["talks"]["type"] = "tlak"
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.collections()
        msgs = [m for m, _ in cm.exception.items]
        self.assertEqual(len(msgs), 4, msgs)
        self.assertIn('MARKERS["upcoming"] is already claimed by type "event" (types/event.py)', msgs[0])
        self.assertIn('content/site.toml: collection "talks" has type "tlak", which no type defines', msgs[1])
        self.assertIn('content/site.toml: collection "guides" has type "guide", which no type defines', msgs[2])
        self.assertIn('content/site.toml: collection "manual" has type "guide", which no type defines', msgs[3])


class Lists(unittest.TestCase):
    def test_upcoming_past_next_and_own_card(self):
        out = build_site()
        events = out["events.html"]
        self.assertIn('class="entry entry--next entry--link"', events)
        self.assertIn('class="b upcoming"', events)
        self.assertIn('class="b past"', events)
        self.assertIn(">Past meetup</a>", events)
        self.assertIn("Future meetup", out["index.html"])            # {next-event}
        self.assertNotIn("Past meetup", out["index.html"])
        own = out["events/2099-01-01-future-meetup.html"]
        self.assertIn('class="entry"', own)                          # the heading card, no link
        self.assertIn("see on OpenStreetMap", own)

    def test_members_grid_and_search_words(self):
        out = build_site()
        members = out["members.html"]
        self.assertIn('class="b members grid" data-search_label="search" data-search_placeholder="first or last name" '
                      'data-all="all" data-one="entry" data-many="entries" data-none="No entry matches."', members)
        self.assertIn('data-category="admin" data-search="ada lovelace"', members)
        self.assertNotIn("members.js", members)                      # the fixture theme ships none
        self.assertIn('class="entry" data-category="member"', out["members/alan-turing.html"])

    def test_posts_list_and_text_mirror(self):
        out = build_site()
        self.assertIn(">Hello</a>", out["blog/index.html"])
        self.assertIn("[ note ]", out["txt/blog/2026-01-01-hello.txt"])
        self.assertIn("[ upcoming ]", out["txt/events.txt"])
        self.assertIn("GitHub: https://github.com/ada", out["txt/members/ada-lovelace.txt"])

    def test_named_marker_must_exist(self):
        languages.setup()
        contenttypes.load()
        colls = contenttypes.collections()
        sections = [{"k": "section", "title": "x", "cls": ["upcoming:nope"], "id": None, "blocks": []}]
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.fill_lists(sections, CONTENT / "index.md", "index.html", colls, {})
        self.assertIn("content/index.md: {upcoming:nope} names no event collection", str(cm.exception))
        self.assertIn("Collections of that type: events", str(cm.exception))

    def test_none_card_is_skipped_and_cls_may_be_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "odd.py").write_text(
                'NAME = "odd"\n'
                'MARKERS = {"odds": lambda items, conf: {"items": [(it, ["x"]) for it in items]}}\n'
                "def entry(item, link, conf):\n"
                '    return None if item["slug"] == "a" else {"k": "entry", "title": item["slug"]}\n')
            contenttypes.load([pathlib.Path(tmp)])
        items = {"o": [{"slug": s, "src": CONTENT / f"o/{s}.md", "path": f"o/{s}.html"} for s in "ab"]}
        sections = [{"k": "section", "title": "x", "cls": ["odds"], "id": None, "blocks": []}]
        contenttypes.fill_lists(sections, CONTENT / "o.md", "o.html", {"o": {"type": "odd", "dir": "o"}}, items)
        self.assertEqual(sections[0]["blocks"], [{"k": "entry", "title": "b", "cls": ["x"]}])

    def test_summary(self):
        languages.setup()
        contenttypes.load()
        colls = contenttypes.collections()
        items = {n: contenttypes.load_items(n, c) for n, c in colls.items()}
        self.assertEqual(contenttypes.summary(colls, items),
                         "types: event, member, page, post; from theme: guide, talk\n"
                         "collections: blog (post, 3 items), events (event, 2 items), "
                         "members (member, 2 items), news (post, no folder), talks (talk, 1 item), "
                         "guides (guide, 4 items), manual (guide, 7 items)")
