"""Share previews per page: the theme's share-page.svg (or share-<type>.svg)
filled with each page's fields, drawn to previews/<key>.png, and named by
og:image, twitter:image and a post's JSON-LD. The rasteriser is mocked: a
fake rsvg-convert first on PATH keeps each SVG it is given and answers
with fixed bytes. Builds run on an edited copy of the fixture in a
subprocess, since config reads its paths at import."""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import BUILDER
import previews

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"
PNG = b"\x89PNG\r\n\x1a\nfake"

FAKE = textwrap.dedent('''\
    #!/usr/bin/env python3
    """A stand-in for rsvg-convert: keeps the SVG, writes fixed bytes."""
    import os, sys, uuid
    svg = sys.stdin.buffer.read()
    if b"page-template" in svg:
        with open(os.path.join(os.environ["FAKE_DIR"], uuid.uuid4().hex + ".svg"), "wb") as f:
            f.write(svg)
    sys.stdout.buffer.write(b"\\x89PNG\\r\\n\\x1a\\nfake")
    ''')

TEMPLATE = ('<svg xmlns="http://www.w3.org/2000/svg" id="page-template">'
            "<t n='man'>{{ man }}</t><t n='path'>{{ path }}</t><t n='url'>{{ url }}</t>"
            "<t n='title_1'>{{ title_1 }}</t><t n='title_2'>{{ title_2 }}</t>"
            "<t n='shift'>{{ title_shift }}</t><t n='detail_1'>{{ detail_1 }}</t>"
            "<t n='detail_2'>{{ detail_2 }}</t><t n='tags'>{{ tags }}</t>"
            "<t n='wordmark'>{{ wordmark }}</t><t n='bg'>{{ share.background_color }}</t></svg>")


def with_template(site, name="share-page.svg", text=TEMPLATE):
    (site / "theme" / name).write_text(text)


def build(*edits, cache=None, out=None):
    """(run, {path: bytes}, [filled SVG fields per drawing], number of drawings)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        site = tmp / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        for edit in edits:
            edit(site)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "rsvg-convert").write_text(FAKE)
        (bin_dir / "rsvg-convert").chmod(0o755)
        drawn = tmp / "drawn"
        drawn.mkdir()
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15",
               "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
               "TILDER_CACHE": str(cache or tmp / "cache"), "FAKE_DIR": str(drawn),
               "TILDER_D2": str(tmp / "no-d2")}
        dest = out or site / "out"
        run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                              "--out", str(dest)], capture_output=True, text=True, env=env)
        files = {str(p.relative_to(dest)): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
        cards = [dict(re.findall(r"<t n='(\w+)'>(.*?)</t>", p.read_text()))
                 for p in drawn.glob("*.svg")]
        return run, files, cards


def head(files, page):
    html = files[page].decode()
    meta = dict(re.findall(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"', html))
    data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return meta, json.loads(data.replace("<\\/", "</"))["@graph"]


class Fitting(unittest.TestCase):
    def test_cut(self):
        self.assertEqual(previews.cut("short", 10), "short")
        self.assertEqual(previews.cut("I-Factory, 10 avenue Jean Capelle Ouest", 24), "I-Factory, 10 avenue...")
        self.assertEqual(previews.cut("abcdefghijklmnop", 8), "abcde...")
        self.assertLessEqual(len(previews.cut("x " * 60, 48)), 48)

    def test_wrap_on_words(self):
        self.assertEqual(previews.wrap("Ce qui se passe quand tu tapes une URL", 23, 2),
                         ["Ce qui se passe quand", "tu tapes une URL"])

    def test_wrap_cuts_the_last_line(self):
        lines = previews.wrap("Mentorat et relecture de CV, stage et alternance", 23, 2)
        self.assertEqual(lines, ["Mentorat et relecture", "de CV, stage et..."])
        self.assertTrue(all(len(l) <= 23 for l in lines))

    def test_wrap_pads_and_splits_long_words(self):
        self.assertEqual(previews.wrap("Hello", 10, 2), ["Hello", ""])
        self.assertEqual(previews.wrap("abcdefghijklmnopqrstuvwxyz", 10, 2), ["abcdefghij", "klmnopq..."])
        self.assertEqual(previews.wrap("", 10, 2), ["", ""])

    def test_ascii_ellipsis_only(self):
        self.assertNotIn("…", previews.cut("a long sentence that will not fit", 12))


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result, cls.files, cls.cards = build(with_template)
        assert cls.result.returncode == 0, cls.result.stderr

    def card(self, title):
        return next(c for c in self.cards if c["title_1"].startswith(title))

    def test_a_post_has_its_own_preview_everywhere(self):
        meta, graph = head(self.files, "blog/2026-01-01-hello.html")
        url = meta["og:image"]
        self.assertRegex(url, r"^https://test\.example/previews/[0-9a-f]{20}\.png$")
        self.assertEqual(meta["twitter:image"], url)
        self.assertEqual(meta["og:image:width"], "1200")
        self.assertEqual(meta["og:image:height"], "630")
        self.assertEqual(meta["twitter:card"], "summary_large_image")
        post = next(n for n in graph if n["@type"] == "BlogPosting")
        self.assertEqual(post["image"], url)
        self.assertEqual(self.files[url.split("test.example/")[1]], PNG)

    def test_the_post_card_fields(self):
        c = self.card("Hello")
        self.assertEqual(c["man"], "SITE-BLOG(7)")    # the collection's man
        self.assertEqual((c["path"], c["url"]), ("/blog", "test.example/blog"))
        self.assertEqual(c["tags"], f'<rect x="0" y="0" width="{4 * 14.4 + 32:g}" height="48" fill="none" '
                                    'stroke="currentColor" stroke-width="2"/>'
                                    '<text x="16" y="33" fill="currentColor">note</text>')
        self.assertEqual(c["detail_2"], "Ada Lovelace")       # the author
        self.assertEqual(c["title_2"], "")
        self.assertEqual(c["shift"], "-68")                   # one title line unused

    def test_the_alt_text_says_what_the_card_shows(self):
        meta, _ = head(self.files, "blog/2026-01-01-hello.html")
        self.assertTrue(meta["og:image:alt"].startswith("~/test site/blog - Hello - "), meta["og:image:alt"])
        self.assertTrue(meta["og:image:alt"].endswith(" - Ada Lovelace - note"), meta["og:image:alt"])

    def test_an_event_card_has_its_place(self):
        c = self.card("Future meetup")
        self.assertEqual(c["path"], "/events")
        self.assertEqual(c["detail_2"], "Library, Springfield")
        self.assertEqual(c["tags"], "")

    def test_the_landing_page_keeps_the_site_card(self):
        meta, _ = head(self.files, "index.html")
        self.assertNotIn("/previews/", meta["og:image"])     # the fixture's theme has no share.svg: the icon

    def test_noindex_keeps_the_site_card(self):
        meta, _ = head(self.files, "404.html")
        self.assertNotIn("/previews/", meta["og:image"])

    def test_a_french_page_has_its_own(self):
        en, _ = head(self.files, "blog/2026-01-01-hello.html")
        fr, _ = head(self.files, "fr/blog/2026-01-01-hello.html")
        self.assertNotEqual(en["og:image"], fr["og:image"])
        self.assertTrue(any(c["url"] == "test.example/fr/blog" for c in self.cards))

    def test_templates_are_not_served(self):
        self.assertNotIn("share-page.svg", self.files)


class Tags(unittest.TestCase):
    def setUp(self):
        import config
        self.saved = dict(config.CFG.get("share", {}))
        config.CFG.setdefault("share", {}).update(
            tag_advance=10, tag_padding=5, tag_height=40, tag_baseline=28, tag_gap=10,
            tag_line_gap=10, tag_room=200)

    def tearDown(self):
        import config
        config.CFG["share"].clear()
        config.CFG["share"].update(self.saved)

    def boxes(self, tags, lines):
        svg, shown = previews.tag_boxes(tags, lines)
        rects = [tuple(float(v) for v in r) for r in
                 re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', svg)]
        return rects, shown, re.findall(r'fill="currentColor">(.*?)</text>', svg)

    def test_the_list(self):
        self.assertEqual(previews.tag_list({"tag": "note", "share_tags": " stand,  atelier technique ,note,"}),
                         ["note", "stand", "atelier technique"])
        self.assertEqual(previews.tag_list({}), [])

    def test_side_by_side_then_a_second_line(self):
        rects, shown, _ = self.boxes(["aaaa", "bbbbbbbb", "cccccccccc"], 2)
        # widths 50, 90, 110 in 200 px: two on the first line, the third below
        self.assertEqual(rects, [(0, 0, 50), (60, 0, 90), (0, 50, 110)])
        self.assertEqual(shown, ["aaaa", "bbbbbbbb", "cccccccccc"])

    def test_what_does_not_fit_is_dropped_never_overflows(self):
        rects, shown, _ = self.boxes(["aaaa", "bbbbbbbb", "cccccccccc", "d"], 1)
        self.assertEqual(shown, ["aaaa", "bbbbbbbb"])
        self.assertTrue(all(x + w <= 200 for x, _, w in rects))

    def test_a_tag_longer_than_a_line_is_cut(self):
        rects, _, texts = self.boxes(["x" * 40], 1)
        self.assertEqual(texts, ["x" * 16 + "..."])
        self.assertLessEqual(rects[0][2], 200)

    def test_text_is_escaped(self):
        _, _, texts = self.boxes(["a<b>&c"], 1)
        self.assertEqual(texts, ["a&lt;b&gt;&amp;c"])


class Choices(unittest.TestCase):
    def test_an_explicit_image_wins(self):
        def image(site):
            p = site / "content" / "blog" / "2026-01-01-hello.md"
            p.write_text(p.read_text().replace("tag: note\n", "tag: note\nimage: shot.png\n", 1))
            (site / "content" / "blog" / "shot.png").write_bytes(b"")
        run, files, _ = build(with_template, image)
        self.assertEqual(run.returncode, 0, run.stderr)
        meta, _ = head(files, "blog/2026-01-01-hello.html")
        self.assertEqual(meta["og:image"], "https://test.example/blog/shot.png")

    def test_share_title_and_escaping(self):
        def title(site):
            p = site / "content" / "blog" / "2026-01-01-hello.md"
            p.write_text(p.read_text().replace("title: Hello\n", "title: Hello\nshare_title: A <b> & \"c\"\n", 1))
        run, _, cards = build(with_template, title)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(any(c["title_1"] == "A &lt;b&gt; &amp; &quot;c&quot;" for c in cards), cards)

    def test_share_tags_and_share_detail(self):
        def tags(site):
            p = site / "content" / "events" / "2099-01-01-future-meetup.md"
            p.write_text(p.read_text().replace("title: Future meetup\n", "title: Future meetup\n"
                                               "share_tags: stand all day, workshop\nshare_detail: Downtown\n", 1))
        run, files, cards = build(with_template, tags)
        self.assertEqual(run.returncode, 0, run.stderr)
        c = next(c for c in cards if c["title_1"] == "Future meetup")
        self.assertEqual(re.findall(r'fill="currentColor">(.*?)</text>', c["tags"]), ["stand all day", "workshop"])
        self.assertEqual(c["detail_2"], "Downtown")
        meta, _ = head(files, "events/2099-01-01-future-meetup.html")
        self.assertTrue(meta["og:image:alt"].endswith(" - Downtown - stand all day - workshop"))

    def test_a_type_template_wins_over_the_page_one(self):
        run, _, cards = build(with_template,
                              lambda s: with_template(s, "share-event.svg", TEMPLATE.replace("{{ man }}", "EVENT")))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(any(c["man"] == "EVENT" and c["path"] == "/events" for c in cards))
        self.assertFalse(any(c["man"] == "EVENT" and c["path"] == "/blog" for c in cards))

    def test_pages_false_keeps_the_site_card(self):
        def off(site):
            with (site / "content" / "site.toml").open("a") as f:
                f.write("\n")
            p = site / "content" / "site.toml"
            p.write_text(p.read_text().replace("[share]\n", "[share]\npages = false\n", 1))
        run, files, cards = build(with_template, off)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(cards, [])
        self.assertFalse([p for p in files if p.startswith("previews/")])

    def test_no_template_no_preview(self):
        run, files, cards = build()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse([p for p in files if p.startswith("previews/")])

    def test_an_unknown_placeholder(self):
        run, _, _ = build(lambda s: with_template(s, text=TEMPLATE + "{{ nope }}"))
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn('error: theme/share-page.svg: unknown placeholder {{ nope }}', run.stderr)


class Cache(unittest.TestCase):
    def test_a_second_build_draws_nothing(self):
        with tempfile.TemporaryDirectory() as cache:
            _, first, drawn = build(with_template, cache=pathlib.Path(cache))
            _, second, again = build(with_template, cache=pathlib.Path(cache))
        self.assertTrue(drawn)
        self.assertEqual(again, [])
        self.assertEqual({p for p in first if p.startswith("previews/")},
                         {p for p in second if p.startswith("previews/")})

    def test_the_previous_output_serves_too(self):
        with tempfile.TemporaryDirectory() as out:
            build(with_template, out=pathlib.Path(out))
            _, _, again = build(with_template, out=pathlib.Path(out))
        self.assertEqual(again, [])


if __name__ == "__main__":
    unittest.main()
