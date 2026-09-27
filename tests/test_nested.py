"""Nested collections: a `recursive` collection reads its subfolders
(docs/types.md). The fixture's manual/ is one: start, the usage section
(its own page, basics, a grouped advanced, the item folder deep), end,
and extra/, a section without its own page."""

import re
import unittest

from tests.helpers import build_site, rebuild
import contenttypes
import languages
import paths
import report
import sequence
from config import BUILDER, CFG, CONTENT

ORDER = ["start", "usage", "usage/basics", "usage/advanced", "usage/deep", "end", "extra/tips"]


def nav(page):
    start = page.index('<nav class="collection-nav"')
    return page[start:page.index("</nav>", start) + len("</nav>")]


def h1(page):
    return re.search(r"<h1.*?</h1>", page).group(0)


class Items(unittest.TestCase):
    def setUp(self):
        languages.setup()
        contenttypes.load()
        self.colls = contenttypes.collections()
        self.items = contenttypes.load_items("manual", self.colls["manual"])

    def test_slugs_paths_and_sections_in_depth_first_order(self):
        self.assertEqual([it["slug"] for it in self.items], ORDER)
        by = {it["slug"]: it for it in self.items}
        self.assertEqual(by["usage/basics"]["path"], "manual/usage/basics.html")
        self.assertEqual(by["usage/basics"]["section"], "usage")
        self.assertEqual(by["usage"]["path"], "manual/usage.html")
        self.assertEqual(by["usage"]["section"], "")
        self.assertEqual(by["usage/deep"]["path"], "manual/usage/deep.html")
        self.assertEqual(by["usage/deep"]["section"], "usage")
        self.assertEqual(by["extra/tips"]["section"], "extra")
        self.assertEqual(by["start"]["section"], "")
        self.assertTrue(all(it["collection"] == "manual" for it in self.items))

    def test_folders_are_sections_or_items(self):
        self.assertIn("manual/usage/deep", paths.ITEM_FOLDERS)
        self.assertNotIn("manual/usage", paths.ITEM_FOLDERS)
        self.assertEqual(paths.SECTIONS["manual/usage"], True)
        self.assertEqual(paths.SECTIONS["manual/extra"], False)
        self.assertTrue(paths.rendered(CONTENT / "manual/usage/basics.md"))
        self.assertTrue(paths.rendered(CONTENT / "manual/usage/index.md"))
        self.assertFalse(paths.rendered(CONTENT / "manual/usage/_draft.md"))
        self.assertEqual(paths.page_path(CONTENT / "manual/usage/index.md"), "manual/usage.html")
        self.assertEqual(paths.page_path(CONTENT / "manual/usage/deep/index.md"), "manual/usage/deep.html")

    def test_templates_are_not_items(self):
        self.assertNotIn("usage/_draft", [it["slug"] for it in self.items])
        self.assertNotIn("manual/usage/_draft.html", build_site())

    def test_language_fallback_per_file(self):
        languages.use("fr")
        contenttypes.load()
        items = contenttypes.load_items("manual", contenttypes.collections()["manual"])
        languages.use(languages.default())
        by = {it["slug"]: it for it in items}
        self.assertEqual(by["usage/basics"]["meta"]["title"], "Les bases")
        self.assertEqual(by["usage/basics"]["content_lang"], "fr")
        self.assertEqual(by["usage"]["content_lang"], "en")
        self.assertEqual([it["slug"] for it in items], ORDER)


class Refused(unittest.TestCase):
    def setUp(self):
        languages.setup()
        contenttypes.load()

    def fails_with(self, *fragments):
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.collections()
        text = "\n".join(m for m, _ in cm.exception.items)
        for f in fragments:
            self.assertIn(f, text)

    def test_a_dated_collection_cannot_be_recursive(self):
        CFG["collections"]["blog"]["recursive"] = True
        self.fails_with('collection "blog" is recursive, and its type "post" is dated: '
                        "a dated collection cannot be recursive", "Remove recursive")

    def test_recursive_is_a_boolean(self):
        CFG["collections"]["manual"]["recursive"] = "yes"
        self.fails_with("collection \"manual\" has recursive = 'yes'",
                        "Write recursive = true or recursive = false")

    def test_two_files_for_one_item(self):
        twin = CONTENT / "manual/usage.md"
        twin.write_text("---\ntitle: Twin\n---\n")
        try:
            with self.assertRaises(report.BuildError) as cm:
                contenttypes.load_items("manual", contenttypes.collections()["manual"])
        finally:
            twin.unlink()
        self.assertIn("is a second file for the item usage", str(cm.exception))
        self.assertIn("content/manual/usage", str(cm.exception))


class Pages(unittest.TestCase):
    def test_every_item_is_a_page_and_the_file_beside_is_copied(self):
        out = build_site()
        for slug in ORDER:
            self.assertIn(f"manual/{slug}.html", out, slug)
            self.assertIn(f"txt/manual/{slug}.txt", out, slug)
        self.assertIn("manual/index.html", out)
        self.assertNotIn("manual/usage/index.html", out)
        self.assertNotIn("manual/usage/deep/index.html", out)
        self.assertIn("manual/usage/deep/notes.txt", out)

    def test_order_reaches_the_outputs(self):
        out = build_site()
        self.assertEqual(out["manual/index.json"],
                         '["Start", "Usage", "Basics", "Advanced", "Deep", "End", "Tips"]')
        self.assertEqual(out["fr/manual/index.json"],
                         '["Start", "Usage", "Les bases", "Advanced", "Deep", "End", "Tips"]')

    def test_the_wordmark_names_every_folder(self):
        out = build_site()
        basics = h1(out["manual/usage/basics.html"])
        self.assertIn('<a href="../">Manual</a>', basics)
        self.assertIn('<a href="../usage">Usage</a>', basics)
        self.assertIn('<span class="here">Basics</span>', basics)
        tips = h1(out["manual/extra/tips.html"])
        self.assertIn('<span class="sr-only">, </span>extra<span class="slash"', tips)
        self.assertNotIn('href="../extra', tips)
        self.assertIn('<a href="../usage">Usage</a>', h1(out["manual/usage/deep.html"]))

    def test_a_section_with_a_page_beside_its_folder_is_linked(self):
        beside = CONTENT / "manual/extra.md"
        beside.write_text(
            "---\ntitle: Extra things\n"
            "description: A page beside its own folder becomes the section "
            "page, and the wordmark links to it.\norder: 4\n---\n\n"
            "## Name\n\nextra {mono}\n")
        try:
            languages.setup()
            contenttypes.load()
            contenttypes.load_items("manual", contenttypes.collections()["manual"])
            self.assertEqual(paths.SECTIONS["manual/extra"], True)
            out = rebuild()
        finally:
            beside.unlink()
        tips = h1(out["manual/extra/tips.html"])
        self.assertIn('<a href="../extra">Extra things</a>', tips)
        self.assertIn('<a class="collection-section-label" href="../extra">Extra things</a>',
                      nav(out["manual/extra/tips.html"]))


class Neighbours(unittest.TestCase):
    def link(self, page, kind):
        m = re.search(rf'<a class="{kind}" rel="{kind}" href="([^"]*)"><span class="{kind}-label">'
                      rf'[^<]*</span> ([^<]*)</a>', page)
        return m and (m.group(1), m.group(2))

    def test_across_sections(self):
        out = build_site()
        self.assertEqual(self.link(out["manual/usage.html"], "prev"), ("start", "Start"))
        self.assertEqual(self.link(out["manual/usage.html"], "next"), ("usage/basics", "Basics"))
        self.assertEqual(self.link(out["manual/usage/basics.html"], "prev"), ("../usage", "Usage"))
        self.assertEqual(self.link(out["manual/end.html"], "prev"), ("usage/deep", "Deep"))
        self.assertEqual(self.link(out["manual/end.html"], "next"), ("extra/tips", "Tips"))
        self.assertIsNone(self.link(out["manual/extra/tips.html"], "next"))

    def test_text_line(self):
        out = build_site()
        self.assertEqual(out["txt/manual/usage/deep.txt"].splitlines()[-3],
                         "previous: Advanced" + " " * 48 + "next: End")


class Order(unittest.TestCase):
    def it(self, slug, order):
        return {"slug": slug, "section": slug.rpartition("/")[0],
                "meta": {"title": slug, "order": order}, "path": f"d/{slug}.html"}

    def test_depth_first(self):
        items = [self.it("z/b", 1), self.it("a", 2), self.it("z", 1), self.it("y/q", 5),
                 self.it("z/a", 2), self.it("x/w/v", 1), self.it("c", 3)]
        key = lambda it: (it["meta"]["order"], it["slug"])
        got = [it["slug"] for it in contenttypes._depth_first(items, key)]
        # z sorts by its own page (order 1), before a and c; x and y have
        # no own page: after, by name; x/w/v is two sections down.
        self.assertEqual(got, ["z", "z/b", "z/a", "a", "c", "x/w/v", "y/q"])

    def test_flat_items_keep_the_type_order(self):
        items = [self.it("b", 2), self.it("a", 2), self.it("c", 1)]
        key = lambda it: (it["meta"]["order"], it["slug"])
        self.assertEqual([it["slug"] for it in contenttypes._depth_first(items, key)], ["c", "a", "b"])


class Flat(unittest.TestCase):
    def test_a_flat_collection_ignores_a_subfolder_of_pages(self):
        folder = CONTENT / "guides/extras"
        folder.mkdir()
        (folder / "more.md").write_text(
            "---\nman: TEST(1)\ntitle: More\n"
            "description: A page in a subfolder of a flat collection, not an item of it.\n"
            "tagline: t\nnav: -\n---\n\n## Name\n\nmore {mono}\n")
        try:
            out = rebuild()
        finally:
            (folder / "more.md").unlink()
            folder.rmdir()
        self.assertNotIn("collection-nav", out["guides/extras/more.html"])
        self.assertEqual(out["guides/index.json"], build_site()["guides/index.json"])
        self.assertEqual(nav(out["guides/setup.html"]), nav(build_site()["guides/setup.html"]))


BASICS_NAV = "\n".join([
    '<nav class="collection-nav" aria-label="In this section">',
    "<ul>",
    '\t<li><a href="../start">Start</a></li>',
    '\t<li class="collection-section collection-section--open"><a class="collection-section-label" href="../usage">Usage</a>',
    "\t<ul>",
    '\t\t<li><a href="basics" aria-current="page">Basics</a></li>',
    '\t\t<li><a href="deep">Deep</a></li>',
    '\t\t<li class="collection-group"><span class="collection-group-label">More</span>',
    "\t\t<ul>",
    '\t\t\t<li><a href="advanced">Advanced</a></li>',
    "\t\t</ul>",
    "\t\t</li>",
    "\t</ul>",
    "\t</li>",
    '\t<li><a href="../end">End</a></li>',
    '\t<li class="collection-section"><span class="collection-section-label">extra</span>',
    "\t<ul>",
    '\t\t<li><a href="../extra/tips">Tips</a></li>',
    "\t</ul>",
    "\t</li>",
    "</ul>",
    "</nav>"])


class Sidebar(unittest.TestCase):
    def test_tree_on_a_page_in_a_section(self):
        self.assertEqual(nav(build_site()["manual/usage/basics.html"]), BASICS_NAV)

    def test_the_section_own_page_is_current_and_open(self):
        page = nav(build_site()["manual/usage.html"])
        self.assertIn('\t<li class="collection-section collection-section--open"><a class="collection-section-label" '
                      'href="usage" aria-current="page">Usage</a>', page)
        self.assertEqual(page.count("aria-current"), 1)

    def test_other_sections_are_closed(self):
        self.assertNotIn("collection-section--open", nav(build_site()["manual/start.html"]))
        tips = nav(build_site()["manual/extra/tips.html"])
        self.assertIn('<li class="collection-section collection-section--open">'
                      '<span class="collection-section-label">extra</span>', tips)
        self.assertIn('<li class="collection-section"><a class="collection-section-label" '
                      'href="../usage">Usage</a>', tips)

    def test_the_collection_page_marks_nothing(self):
        page = nav(build_site()["manual/index.html"])
        self.assertNotIn("aria-current", page)
        self.assertNotIn("collection-section--open", page)

    def test_french_titles(self):
        self.assertIn('<a href="basics">Les bases</a>', nav(build_site()["fr/manual/usage/advanced.html"]))

    def test_the_starter_styles_the_section_classes(self):
        css = (BUILDER / "starter" / "theme" / "style.css").read_text()
        for cls in (".collection-section-label", ".collection-section--open"):
            self.assertIn(cls, css, cls)
        self.assertRegex(css, r"\.collection-section(?![\w-])")


class Tree(unittest.TestCase):
    def it(self, slug):
        return {"slug": slug, "section": slug.rpartition("/")[0], "meta": {"title": slug},
                "path": f"d/{slug}.html"}

    def test_sections_with_and_without_their_own_page(self):
        a, s, sb, bare = self.it("a"), self.it("s"), self.it("s/b"), self.it("t/c")
        self.assertEqual(sequence.tree([a, s, sb, bare]), [
            a, {"path": "s", "own": s, "entries": [sb]},
            {"path": "t", "own": None, "entries": [bare]}])

    def test_flat_items_are_their_own_tree(self):
        items = [{"path": "d/a.html", "meta": {"title": "A"}}, {"path": "d/b.html", "meta": {"title": "B"}}]
        self.assertEqual(sequence.tree(items), items)

    def test_a_section_groups_by_its_own_page(self):
        own = {**self.it("s"), "meta": {"title": "s", "group": "G"}}
        entries = sequence.tree([self.it("a"), own, self.it("s/b")])
        self.assertEqual([g for g, _ in sequence.groups(entries)], [None, "G"])


class Docs(unittest.TestCase):
    def test_the_docs_name_what_1_2_adds(self):
        types = (BUILDER / "docs" / "types.md").read_text()
        for name in ("`recursive`", "depth-first", '"section"', "a `DATED` type cannot be recursive"):
            self.assertIn(name, types, name)
        theme = (BUILDER / "docs" / "theme.md").read_text()
        for name in ("## Checking a theme", "`[check]`", "contrast_min", "--markdown",
                     "`src/contract.py`", "collection-section--open"):
            self.assertIn(name, theme, name)
        self.assertIn("--check", (BUILDER / "README.md").read_text())
        agents = (BUILDER / "AGENTS.md").read_text()
        for name in ("connect-src 'self'", "contract.py", "themecheck.py", "--check"):
            self.assertIn(name, agents, name)
