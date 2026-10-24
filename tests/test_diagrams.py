"""Mermaid diagrams: ```mermaid <description> "<caption>" blocks, drawn at
build time by the Mermaid CLI into diagrams/<key>.svg and shown as an
<img>; the text mirror shows the description and the source. The CLI is
mocked: TILDER_MMDC names a script that writes a fixed SVG made from its
input and configuration, and logs each call. Builds run on an edited copy
of the fixture in a subprocess, since config reads its paths at import."""

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
import diagrams
import markdown

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"

FAKE = textwrap.dedent('''\
    #!/usr/bin/env python3
    """A stand-in for mmdc: --version, or -i IN -o OUT -c CONFIG."""
    import json, os, sys
    args = sys.argv[1:]
    with open(os.environ["FAKE_LOG"], "a") as log:
        log.write(("version" if "--version" in args else "draw") + "\\n")
    if "--version" in args:
        print("fake-mmdc 1.0")
        sys.exit(0)
    get = lambda flag: args[args.index(flag) + 1]
    source = open(get("-i")).read()
    if "BROKEN" in source:
        print("Error: Parse error on line 2:", file=sys.stderr)
        sys.exit(1)
    colour = json.load(open(get("-c"))).get("themeVariables", {}).get("primaryColor", "#123456")
    label = source.splitlines()[1].strip()
    open(get("-o"), "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" id="my-svg" width="100%" '
        'style="max-width: 200px; background-color: transparent;" viewBox="0 0 200 100.4">'
        '<style>#my-svg{fill:#073642;} .node rect{rx:5px;filter:drop-shadow(1px 1px 1px #000);}</style>'
        '<defs><filter id="shadow"/></defs>'
        f'<rect x="0" y="0" width="10" height="10" rx="5" ry="5" fill="{colour}" stroke="#ABCDEF" '
        'filter="url(#shadow)"/>'
        f'<text>{label}</text></svg>')
    ''')

PALETTE = (":root { --bg: #FDF6E3; --fg: #073642; }\n"
           "@media (prefers-color-scheme: dark) { :root { --bg: #002B36; --fg: #B6C2C2; } }\n")
MERMAID_JSON = '{"theme": "base", "themeVariables": {"primaryColor": "var(--bg)"}}'

POST = textwrap.dedent('''\
    ---
    title: Drawn
    description: A post with a Mermaid diagram, to test diagrams in both renderings.
    ---

    ## Body

    ```mermaid Two boxes, the first pointing to the second "The flow, in short."
    flowchart LR
      a["first"] --> b["second"]
    ```
    ''')


def themed(site):
    """The fixture's theme with a palette and a mermaid.json."""
    with (site / "theme" / "style.css").open("a") as f:
        f.write(PALETTE)
    (site / "theme" / "mermaid.json").write_text(MERMAID_JSON)


def post(text=POST, name="2026-03-01-drawn.md"):
    def edit(site):
        (site / "content" / "blog" / name).write_text(text)
    return edit


class Built:
    """One build: run, out {path: text}, calls (the fake's log lines)."""


def build(*edits, renderer=True, cache=None, out=None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        site = tmp / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        for edit in edits:
            edit(site)
        fake = tmp / "mmdc"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        log = tmp / "log"
        log.write_text("")
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15",
               "TILDER_MMDC": str(fake) if renderer else str(tmp / "no-mmdc"),
               "TILDER_CACHE": str(cache or tmp / "cache"), "FAKE_LOG": str(log)}
        dest = out or site / "out"
        b = Built()
        b.run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                                "--out", str(dest)], capture_output=True, text=True, env=env)
        b.out = {str(p.relative_to(dest)): p.read_text(errors="replace")
                 for p in dest.rglob("*") if p.is_file() and p.suffix not in (".png", ".ico")}
        b.calls = log.read_text().split()
        return b


class Syntax(unittest.TestCase):
    def test_description_and_caption(self):
        n = markdown.diagram('Two boxes "The flow."', ["flowchart LR"])
        self.assertEqual((n["k"], n["alt"], n["caption"], n["lines"]),
                         ("diagram", "Two boxes", "The flow.", ["flowchart LR"]))

    def test_description_only(self):
        n = markdown.diagram("Two boxes, one arrow", [])
        self.assertEqual((n["alt"], n["caption"]), ("Two boxes, one arrow", ""))

    def test_nothing(self):
        n = markdown.diagram("", [])
        self.assertEqual((n["alt"], n["caption"]), ("", ""))

    def test_the_fence_is_read(self):
        n = markdown.classify(["```mermaid A box", "flowchart LR", "  a"])
        self.assertEqual((n["k"], n["alt"], n["lines"]), ("diagram", "A box", ["flowchart LR", "  a"]))

    def test_another_language_stays_code(self):
        self.assertEqual(markdown.classify(["```mermaidish", "x"])["k"], "code")
        self.assertEqual(markdown.classify(["```python", "x"])["k"], "code")


class Fit(unittest.TestCase):
    LIGHT = {"--bg": "#FDF6E3", "--fg": "#073642"}
    DARK = {"--bg": "#002B36", "--fg": "#B6C2C2"}
    LOOK = {"fold": {"#ECECFF": "--bg"}, "sharp": True, "shadow": False}
    RAW = ('<svg xmlns="http://www.w3.org/2000/svg" width="100%" style="max-width: 50px; '
           'background-color: transparent;" viewBox="4 4 50 20.5">'
           '<style>.a{fill:#073642;rx:3px;filter:drop-shadow(1px 1px #000)}</style>'
           '<filter id="f"/><rect rx="4" ry="4" fill="#fdf6e3" stroke="#ececff" filter="url(#f)"/>'
           '<text fill="#ABCDEF">x</text></svg>')

    def setUp(self):
        self.svg, self.unknown = diagrams.fit(self.RAW, self.LIGHT, self.DARK, self.LOOK)

    def test_colours_become_tokens_light_and_dark(self):
        self.assertIn("fill:var(--bg)", self.svg)
        self.assertIn("stroke:var(--bg)", self.svg)       # folded
        self.assertIn(".a{fill:var(--fg)", self.svg)
        self.assertIn("<style>:root{--bg:#FDF6E3;--fg:#073642}"
                      "@media (prefers-color-scheme: dark){:root{--bg:#002B36;--fg:#B6C2C2}}</style>",
                      self.svg)

    def test_unknown_colours_are_reported_and_kept(self):
        self.assertEqual(self.unknown, ["#000", "#ABCDEF"])
        self.assertIn("#ABCDEF", self.svg)

    def test_sharp_and_no_shadow(self):
        self.assertIn('rx="0" ry="0"', self.svg)
        self.assertIn("rx:0", self.svg)
        self.assertNotIn("filter", self.svg)

    def test_natural_size(self):
        self.assertIn('width="50"', self.svg)
        self.assertIn('height="20.5"', self.svg)
        self.assertNotIn("max-width", self.svg)

    def test_the_theme_may_keep_corners_and_shadows(self):
        svg, _ = diagrams.fit(self.RAW, self.LIGHT, self.DARK,
                              {"fold": {}, "sharp": False, "shadow": True})
        self.assertIn('rx="4"', svg)
        self.assertIn('filter="url(#f)"', svg)

    def test_no_palette_no_tokens(self):
        svg, unknown = diagrams.fit(self.RAW, {}, {}, self.LOOK)
        self.assertEqual(unknown, [])
        self.assertNotIn("var(", svg)
        self.assertNotIn(":root", svg)


class Drawn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = build(themed, post())
        assert cls.b.run.returncode == 0, cls.b.run.stderr

    def svg_path(self):
        m = re.search(r'<img src="\.\./(diagrams/[0-9a-f]{20}\.svg)"', self.b.out["blog/2026-03-01-drawn.html"])
        self.assertIsNotNone(m, self.b.out["blog/2026-03-01-drawn.html"])
        return m.group(1)

    def test_the_page_shows_an_image_of_the_drawing(self):
        html = self.b.out["blog/2026-03-01-drawn.html"]
        self.assertRegex(html, r'<figure class="figure"><img src="\.\./diagrams/[0-9a-f]{20}\.svg" '
                               r'alt="Two boxes, the first pointing to the second" width="200" height="100" '
                               r'loading="lazy" decoding="async"><figcaption>The flow, in short\.</figcaption></figure>')
        self.assertNotIn("<svg", html)

    def test_the_svg_file_is_written_and_themed(self):
        svg = self.b.out[self.svg_path()]
        self.assertIn("fill:var(--bg)", svg)        # mermaid.json's var(--bg), drawn, then a token again
        self.assertIn("@media (prefers-color-scheme: dark){:root{--bg:#002B36;--fg:#B6C2C2}}", svg)
        self.assertIn("first", svg)

    def test_the_text_mirror_has_the_description_then_the_source(self):
        txt = self.b.out["txt/blog/2026-03-01-drawn.txt"]
        self.assertIn("[ diagram ] Two boxes, the first pointing to the second", txt)
        self.assertIn("The flow, in short.", txt)
        self.assertRegex(txt, r"\.-- mermaid -+\.\n +flowchart LR\n +a\[\"first\"\] --> b\[\"second\"\]")
        self.assertLessEqual(max(len(l) for l in txt.splitlines()), 75)

    def test_one_drawing_for_both_languages(self):
        self.assertEqual(self.b.calls.count("draw"), 1)
        self.assertEqual(len([p for p in self.b.out if p.startswith("diagrams/")]), 1)
        fr = self.b.out["fr/blog/2026-03-01-drawn.html"]
        self.assertIn(f'src="../../{self.svg_path()}"', fr)

    def test_the_colours_the_theme_does_not_map_are_said(self):
        self.assertIn("warning: theme/mermaid.json: diagram colours left as they are: #000 #ABCDEF. "
                      "Map each to a token under [diagrams] fold in theme.toml", self.b.run.stderr)

    def test_a_fold_silences_them(self):
        def fold(site):
            with (site / "theme" / "theme.toml").open("a") as f:
                f.write('\n[diagrams.fold]\n"#ABCDEF" = "--fg"\n"#000" = "--fg"\n')
        b = build(themed, post(), fold)
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertNotIn("warning:", b.run.stderr)


class Cache(unittest.TestCase):
    def test_the_cache_folder_spares_a_second_drawing(self):
        with tempfile.TemporaryDirectory() as cache:
            first = build(themed, post(), cache=pathlib.Path(cache))
            second = build(themed, post(), cache=pathlib.Path(cache))
        self.assertEqual(first.calls.count("draw"), 1)
        self.assertEqual(second.calls.count("draw"), 0)
        self.assertEqual({p: t for p, t in first.out.items() if p.startswith("diagrams/")},
                         {p: t for p, t in second.out.items() if p.startswith("diagrams/")})

    def test_the_previous_output_spares_it_too(self):
        with tempfile.TemporaryDirectory() as out:
            first = build(themed, post(), out=pathlib.Path(out))
            second = build(themed, post(), out=pathlib.Path(out))   # each run: a new, empty cache
        self.assertEqual(first.calls.count("draw"), 1)
        self.assertEqual(second.calls.count("draw"), 0)

    def test_a_new_palette_is_a_new_drawing(self):
        def dark(site):
            with (site / "theme" / "style.css").open("a") as f:
                f.write("@media (prefers-color-scheme: dark) { :root { --bg: #111111; } }\n")
        with tempfile.TemporaryDirectory() as cache:
            first = build(themed, post(), cache=pathlib.Path(cache))
            second = build(themed, post(), dark, cache=pathlib.Path(cache))
        self.assertEqual(second.calls.count("draw"), 1)
        self.assertNotEqual(sorted(p for p in first.out if p.startswith("diagrams/")),
                            sorted(p for p in second.out if p.startswith("diagrams/")))


class Fallback(unittest.TestCase):
    def test_without_a_renderer_the_source_and_its_description(self):
        b = build(themed, post(), post(POST, "2026-03-02-drawn-too.md"), renderer=False)
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertEqual(b.run.stderr.count("(the Mermaid CLI): diagrams are shown as their source"), 1,
                         b.run.stderr)
        html = b.out["blog/2026-03-01-drawn.html"]
        self.assertIn('<figure class="figure"><pre class="code" data-lang="mermaid" tabindex="0"><code>'
                      'flowchart LR\n  a[&quot;first&quot;] --&gt; b[&quot;second&quot;]</code></pre>'
                      '<figcaption>Two boxes, the first pointing to the second The flow, in short.'
                      '</figcaption></figure>', html.replace('"first"', "&quot;first&quot;")
                      .replace('"second"', "&quot;second&quot;"))
        self.assertFalse([p for p in b.out if p.startswith("diagrams/")])
        self.assertIn("[ diagram ] Two boxes", b.out["txt/blog/2026-03-01-drawn.txt"])


class Problems(unittest.TestCase):
    def test_a_diagram_without_a_description_warns_once(self):
        text = POST.replace("```mermaid Two boxes, the first pointing to the second "
                            '"The flow, in short."', "```mermaid")
        b = build(themed, post(text))
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertEqual(b.run.stderr.count(
            "warning: content/blog/2026-03-01-drawn.md: a mermaid diagram without a description. "
            "Describe it after the word mermaid: ```mermaid What the diagram shows"), 1, b.run.stderr)
        self.assertIn('alt=""', b.out["blog/2026-03-01-drawn.html"])

    def test_a_diagram_that_cannot_be_drawn_stops_the_build(self):
        b = build(themed, post(POST.replace("flowchart LR", "flowchart LR\nBROKEN")))
        self.assertEqual(b.run.returncode, 1, b.run.stderr)
        self.assertIn("error: content/blog/2026-03-01-drawn.md: a mermaid diagram cannot be drawn: "
                      "Error: Parse error on line 2:. Fix its source (the syntax: https://mermaid.js.org/)",
                      b.run.stderr)
        self.assertNotIn("Traceback", b.run.stderr)

    def test_a_token_style_css_lacks(self):
        def bad(site):
            (site / "theme" / "mermaid.json").write_text('{"themeVariables": {"primaryColor": "var(--nope)"}}')
        b = build(themed, post(), bad)
        self.assertEqual(b.run.returncode, 1, b.run.stderr)
        self.assertIn("error: theme/mermaid.json: var(--nope) names no colour token of style.css",
                      b.run.stderr)

    def test_mermaid_json_is_not_served(self):
        b = build(themed, post())
        self.assertNotIn("mermaid.json", b.out)


if __name__ == "__main__":
    unittest.main()
