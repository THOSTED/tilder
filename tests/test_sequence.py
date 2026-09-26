import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import sequence
from config import load_config


def it(path, title, group=None, **meta):
    m = {"title": title, **meta}
    if group is not None:
        m["group"] = group
    return {"path": path, "meta": m}


A = it("docs/a.html", "Alpha")
B = it("docs/b.html", "Beta", "Basics")
C = it("docs/c.html", "Gamma", "Advanced")
D = it("docs/d.html", "Delta", "Basics")
ITEMS = [A, B, C, D]
COLLS = {"docs": {"dir": "docs", "type": "doc"}, "blog": {"dir": "blog", "type": "post"}}
ALL = {"docs": ITEMS, "blog": [it("blog/x.html", "X")]}
same = lambda u: u


class Order(unittest.TestCase):
    def test_shown(self):
        self.assertEqual(sequence.shown("docs/c.html", COLLS, ALL), ("docs", ITEMS))
        self.assertEqual(sequence.shown("docs/index.html", COLLS, ALL), ("docs", ITEMS))
        self.assertEqual(sequence.shown("docs.html", COLLS, ALL), ("docs", ITEMS))
        self.assertEqual(sequence.shown("about.html", COLLS, ALL), (None, []))
        self.assertEqual(sequence.shown("blog/index.html", COLLS, {}), ("blog", []))

    def test_groups_first_appearance_loose_first(self):
        self.assertEqual(sequence.groups(ITEMS), [(None, [A]), ("Basics", [B, D]), ("Advanced", [C])])
        self.assertEqual(sequence.groups([A]), [(None, [A])])
        self.assertEqual(sequence.groups([]), [])
        self.assertEqual(sequence.groups([it("p.html", "P", 2024)]), [("2024", [it("p.html", "P", 2024)])])

    def test_neighbours_ignore_groups(self):
        self.assertEqual(sequence.neighbours(ITEMS, "docs/a.html"), (None, B))
        self.assertEqual(sequence.neighbours(ITEMS, "docs/c.html"), (B, D))
        self.assertEqual(sequence.neighbours(ITEMS, "docs/d.html"), (C, None))
        self.assertEqual(sequence.neighbours(ITEMS, "docs/index.html"), (None, None))
        self.assertEqual(sequence.neighbours([A], "docs/a.html"), (None, None))

    def test_title_falls_back_to_the_slug(self):
        self.assertEqual(sequence.title({"path": "docs/x.html", "meta": {}, "slug": "x"}), "x")


class Html(unittest.TestCase):
    def setUp(self):
        load_config()

    def test_nav(self):
        self.assertEqual(sequence.nav_html(ITEMS, "docs/b.html", {}, same), "\n".join([
            '<nav class="collection-nav" aria-label="In this section">',
            "<ul>",
            '\t<li><a href="docs/a">Alpha</a></li>',
            '\t<li class="collection-group"><span class="collection-group-label">Basics</span>',
            "\t<ul>",
            '\t\t<li><a href="docs/b" aria-current="page">Beta</a></li>',
            '\t\t<li><a href="docs/d">Delta</a></li>',
            "\t</ul>",
            "\t</li>",
            '\t<li class="collection-group"><span class="collection-group-label">Advanced</span>',
            "\t<ul>",
            '\t\t<li><a href="docs/c">Gamma</a></li>',
            "\t</ul>",
            "\t</li>",
            "</ul>",
            "</nav>"]))

    def test_nav_label_and_empty(self):
        self.assertIn('aria-label="Doc pages"', sequence.nav_html([A], "", {"nav_label": "Doc pages"}, same))
        self.assertEqual(sequence.nav_html([], "docs/a.html", {}, same), "")

    def test_links(self):
        self.assertEqual(sequence.link_html("prev", A, same),
                         '<a class="prev" rel="prev" href="docs/a"><span class="prev-label">previous</span> Alpha</a>')
        self.assertEqual(sequence.link_html("next", D, same),
                         '<a class="next" rel="next" href="docs/d"><span class="next-label">next</span> Delta</a>')
        self.assertEqual(sequence.link_html("next", None, same), "")

    def test_titles_are_escaped(self):
        odd = it("docs/o.html", "A <b> & c", "x < y")
        self.assertIn(">A &lt;b&gt; &amp; c</a>", sequence.nav_html([odd], "", {}, same))
        self.assertIn(">x &lt; y</span>", sequence.nav_html([odd], "", {}, same))
        self.assertIn(" A &lt;b&gt; &amp; c</a>", sequence.link_html("prev", odd, same))


class Line(unittest.TestCase):
    def setUp(self):
        load_config()

    def test_both_sides(self):
        self.assertEqual(sequence.line("Introduction", "Deployment"),
                         "previous: Introduction" + " " * 37 + "next: Deployment")

    def test_one_side(self):
        self.assertEqual(sequence.line(None, "Setup"), " " * 64 + "next: Setup")
        self.assertEqual(sequence.line("Tuning", None), "previous: Tuning")
        self.assertEqual(sequence.line(None, None), "")

    def test_line_cuts_long_titles(self):
        both = sequence.line("A" * 60, "B" * 60)
        self.assertEqual(both, "previous: " + "A" * 23 + "..." + "  " + "next: " + "B" * 28 + "...")
        self.assertEqual(len(both), 75)
        short_long = sequence.line("Intro", "B" * 80)
        self.assertEqual(short_long, "previous: Intro  next: " + "B" * 49 + "...")
        self.assertEqual(len(short_long), 75)
        self.assertEqual(len(sequence.line(None, "B" * 90)), 75)

    def test_ascii(self):
        self.assertEqual(sequence.line("Étape à suivre", None), "previous: Etape a suivre")

    def test_txt_line_only_for_sequential_types(self):
        seq = type("T", (), {"SEQUENTIAL": True})
        flat = type("T", (), {"SEQUENTIAL": False})
        items = {"docs": [dict(x, type=seq) for x in ITEMS]}
        self.assertEqual(sequence.txt_line(items["docs"][0], COLLS, items), " " * 65 + "next: Beta")
        plain = [dict(x, type=flat) for x in ITEMS]
        self.assertEqual(sequence.txt_line(plain[0], COLLS, {"docs": plain}), "")
