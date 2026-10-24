"""D2 diagrams: ```d2 <description> "<caption>" blocks, drawn at build time
by the D2 CLI into diagrams/<key>.svg and shown as an <img>; the text
mirror shows the description, then the author's ```text drawing when one
follows the block, else the D2 source. The CLI is mocked: TILDER_D2 names
a script that keeps the source it is given (the theme's configuration
appended) and writes a fixed SVG, and logs each call. Builds run on an
edited copy of the fixture in a subprocess, since config reads its paths
at import."""

import os
from tests import site_warnings
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
    """A stand-in for d2: --version, or [--font-X FILE]... IN OUT."""
    import os, sys
    args = sys.argv[1:]
    with open(os.environ["FAKE_LOG"], "a") as log:
        log.write(("version" if "--version" in args else "draw") + "\\n")
    if "--version" in args:
        print("v0.9.0-fake")
        sys.exit(0)
    fonts = [args[i] + "=" + os.path.basename(args[i + 1]) for i in range(len(args) - 2) if args[i].startswith("--font-")]
    src, out = args[-2], args[-1]
    text = open(src).read()
    open(os.environ["FAKE_LOG"] + ".src", "w").write(text)
    open(os.environ["FAKE_LOG"] + ".fonts", "w").write(" ".join(fonts))
    if "BROKEN" in text:
        print(f"err: failed to compile {src}: {src}:2:1: unexpected text", file=sys.stderr)
        sys.exit(1)
    label = text.splitlines()[0]
    open(out, "w").write('<?xml version="1.0" encoding="utf-8"?><svg xmlns="http://www.w3.org/2000/svg" '
                         f'viewBox="0 0 200 100.4"><text>{label}</text></svg>')
    ''')

PALETTE = (":root { --bg: #FDF6E3; --fg: #073642; --accent: #0F6E68; }\n"
           "@media (prefers-color-scheme: dark) { :root { --bg: #002B36; --fg: #B6C2C2; } }\n")
THEME_TOML = '\n[diagrams]\nlayout = "elk"\npad = 8\n\n[diagrams.d2]\nN1 = "--fg"\nN7 = "--bg"\nAA2 = "--accent"\n'

POST = textwrap.dedent('''\
    ---
    title: Drawn
    description: A post with a D2 diagram, to test diagrams in both renderings.
    ---

    ## Body

    ```d2 Two boxes, the first pointing to the second "The flow, in short."
    a: first
    b: second
    a -> b
    ```
    ''')

DRAWING = textwrap.dedent('''\

    ```text {text}
    [ first ] --> [ second ]
    ```
    ''')
HTML_ONLY = POST.replace('"The flow, in short."', '"The flow, in short." {html}')


def themed(site):
    """The fixture's theme with a palette and a [diagrams] table."""
    with (site / "theme" / "style.css").open("a") as f:
        f.write(PALETTE)
    with (site / "theme" / "theme.toml").open("a") as f:
        f.write(THEME_TOML)


def post(text=POST, name="2026-03-01-drawn.md"):
    def edit(site):
        (site / "content" / "blog" / name).write_text(text)
    return edit


class Built:
    """One build: run, out {path: text}, calls (the fake's log), source, fonts."""


def build(*edits, renderer=True, cache=None, out=None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        site = tmp / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        for edit in edits:
            edit(site)
        fake = tmp / "d2"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        log = tmp / "log"
        log.write_text("")
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15",
               "TILDER_D2": str(fake) if renderer else str(tmp / "no-d2"),
               "TILDER_CACHE": str(cache or tmp / "cache"), "FAKE_LOG": str(log)}
        dest = out or site / "out"
        b = Built()
        b.run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                                "--out", str(dest)], capture_output=True, text=True, env=env)
        b.out = {str(p.relative_to(dest)): p.read_text(errors="replace")
                 for p in dest.rglob("*") if p.is_file() and p.suffix not in (".png", ".ico")}
        b.calls = log.read_text().split()
        b.source = (tmp / "log.src").read_text() if (tmp / "log.src").is_file() else ""
        b.fonts = (tmp / "log.fonts").read_text() if (tmp / "log.fonts").is_file() else ""
        return b


class Syntax(unittest.TestCase):
    def test_description_and_caption(self):
        n = markdown.diagram('Two boxes "The flow."', ["a -> b"])
        self.assertEqual((n["k"], n["alt"], n["caption"], n["lines"]),
                         ("diagram", "Two boxes", "The flow.", ["a -> b"]))

    def test_description_only(self):
        n = markdown.diagram("Two boxes, one arrow", [])
        self.assertEqual((n["alt"], n["caption"]), ("Two boxes, one arrow", ""))

    def test_the_fence_is_read(self):
        n = markdown.classify(["```d2 A box", "a -> b"])
        self.assertEqual((n["k"], n["alt"], n["lines"]), ("diagram", "A box", ["a -> b"]))

    def test_another_language_stays_code(self):
        for fence in ("```d2x", "```mermaid A box", "```python"):
            self.assertEqual(markdown.classify([fence, "x"])["k"], "code", fence)

    def parse(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "page.md"
            p.write_text("---\ntitle: t\ndescription: d\n---\n\n## S\n\n" + body)
            _, sections, _ = markdown.parse(p)
        return sections[0]["blocks"]

    def test_a_text_block_right_after_a_html_diagram_is_its_drawing(self):
        blocks = self.parse("```d2 A {html}\na -> b\n```\n\n```text {text}\n[a] -> [b]\n```\n")
        self.assertEqual([b["k"] for b in blocks], ["diagram"])
        self.assertEqual((blocks[0]["only"], blocks[0]["ascii"]), ("html", ["[a] -> [b]"]))

    def test_any_text_only_block_pairs(self):
        blocks = self.parse("```d2 A {html}\na -> b\n```\n```{text}\n[a] -> [b]\n```\n")
        self.assertEqual(blocks[0]["ascii"], ["[a] -> [b]"])

    def test_a_plain_text_block_after_a_diagram_is_just_code(self):
        blocks = self.parse("```d2 A\na -> b\n```\n\n```text\n[a] -> [b]\n```\n")
        self.assertEqual([b["k"] for b in blocks], ["diagram", "code"])
        self.assertNotIn("ascii", blocks[0])
        self.assertIsNone(blocks[1]["only"])

    def test_a_text_block_after_a_diagram_shown_in_both_is_its_own(self):
        blocks = self.parse("```d2 A\na -> b\n```\n\n```text {text}\n[a] -> [b]\n```\n")
        self.assertEqual([(b["k"], b["only"]) for b in blocks], [("diagram", None), ("code", "text")])

    def test_a_text_block_after_something_else_is_code(self):
        blocks = self.parse("```d2 A {html}\na -> b\n```\n\nA paragraph.\n\n```text {text}\n[a]\n```\n")
        self.assertEqual([b["k"] for b in blocks], ["diagram", "para", "code"])
        self.assertNotIn("ascii", blocks[0])

    def test_only_one_drawing(self):
        blocks = self.parse("```d2 A {html}\na -> b\n```\n\n```text {text}\none\n```\n\n```text {text}\ntwo\n```\n")
        self.assertEqual([b["k"] for b in blocks], ["diagram", "code"])

    def test_markers_after_the_caption(self):
        n = markdown.classify(['```d2 Two {boxes} "The {flow}." {html}', "a -> b"])
        self.assertEqual((n["alt"], n["caption"], n["only"]), ("Two {boxes}", "The {flow}.", "html"))


class Config(unittest.TestCase):
    def test_the_overrides_light_and_dark(self):
        light = {"--fg": "#073642", "--bg": "#FDF6E3"}
        dark = {"--fg": "#B6C2C2", "--bg": "#002B36"}
        conf = diagrams.d2_config("elk", 16, {"N1": "--fg", "N7": "--bg"}, light, dark)
        self.assertIn("layout-engine: elk\n    pad: 16\n    theme-id: 0\n", conf)
        self.assertIn('theme-overrides: {\n      N1: "#073642"\n      N7: "#FDF6E3"\n    }', conf)
        self.assertIn('dark-theme-id: 200\n    dark-theme-overrides: {\n      N1: "#B6C2C2"\n      N7: "#002B36"\n', conf)

    def test_no_dark_scheme_no_dark_theme(self):
        conf = diagrams.d2_config("dagre", 16, {"N1": "--fg"}, {"--fg": "#000000"}, {})
        self.assertNotIn("dark", conf)

    def test_sized_from_the_view_box(self):
        svg = '<?xml version="1.0"?><svg xmlns="x" viewBox="0 0 854 574.5"><svg class="i" width="9"></svg></svg>'
        self.assertIn('<svg xmlns="x" viewBox="0 0 854 574.5" width="854" height="574.5">', diagrams._sized(svg))


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

    def test_the_source_gets_the_theme_after_it(self):
        src = self.b.source
        self.assertTrue(src.startswith("a: first\nb: second\na -> b\n\nvars: {"), src)
        self.assertIn("layout-engine: elk", src)
        self.assertIn("pad: 8", src)
        self.assertIn('N1: "#073642"', src)
        self.assertIn('AA2: "#0F6E68"', src)
        self.assertIn("dark-theme-id: 200", src)
        self.assertIn('N7: "#002B36"', src)
        # --accent is not redefined in the dark scheme: it keeps its value there
        self.assertIn('AA2: "#0F6E68"', src.split("dark-theme-overrides")[1])

    def test_the_svg_is_written_with_its_size(self):
        svg = self.b.out[self.svg_path()]
        self.assertIn('viewBox="0 0 200 100.4" width="200" height="100.4"', svg)

    def test_the_text_mirror_shows_the_source_without_a_drawing(self):
        txt = self.b.out["txt/blog/2026-03-01-drawn.txt"]
        self.assertIn("[ diagram ] Two boxes, the first pointing to the second", txt)
        self.assertIn("The flow, in short.", txt)
        self.assertRegex(txt, r"\.-- d2 -+\.\n +a: first\n +b: second\n +a -> b\n")

    def test_one_drawing_for_both_languages(self):
        self.assertEqual(self.b.calls.count("draw"), 1)
        self.assertEqual(len([p for p in self.b.out if p.startswith("diagrams/")]), 1)
        self.assertIn(f'src="../../{self.svg_path()}"', self.b.out["fr/blog/2026-03-01-drawn.html"])

    def test_no_warning(self):
        self.assertEqual(site_warnings(self.b.run.stderr), [], self.b.run.stderr)


class Drawing(unittest.TestCase):
    def test_the_text_drawing_replaces_the_source_in_the_mirror_only(self):
        b = build(themed, post(HTML_ONLY + DRAWING))
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        txt = b.out["txt/blog/2026-03-01-drawn.txt"]
        self.assertRegex(txt, r"The flow, in short\.\n +\.-+\.\n +\[ first \] --> \[ second \]\n +'-+'")
        self.assertNotIn("a -> b", txt)
        html = b.out["blog/2026-03-01-drawn.html"]
        self.assertNotIn("[ first ]", html)
        self.assertIn('<img src="../diagrams/', html)
        self.assertEqual(site_warnings(b.run.stderr), [], b.run.stderr)

    def test_a_drawing_too_wide_or_not_ascii_warns(self):
        wide = "x" * 69
        b = build(themed, post(HTML_ONLY + f"\n```text {{text}}\n{'x' * 68}\n{wide}\nécrit\n```\n"))
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertIn("warning: content/blog/2026-03-01-drawn.md: the text drawing of a d2 diagram is 69 columns "
                      "wide, line 2; the text mirror holds 68 there. Draw it in 68 columns or fewer", b.run.stderr)
        self.assertIn("the text drawing of a d2 diagram has a character that is not ASCII, line 3: 'écrit'",
                      b.run.stderr)
        self.assertEqual(len(site_warnings(b.run.stderr)), 2, b.run.stderr)

    def test_a_html_diagram_without_a_drawing_is_not_in_the_mirror(self):
        b = build(themed, post(HTML_ONLY))
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertNotIn("diagram", b.out["txt/blog/2026-03-01-drawn.txt"])
        self.assertIn('<img src="../diagrams/', b.out["blog/2026-03-01-drawn.html"])

    def test_a_text_diagram_is_its_source_in_the_mirror_only(self):
        text = POST.replace('"The flow, in short."', '"The flow, in short." {text}')
        b = build(themed, post(text.replace("Two boxes, the first pointing to the second ", "")))
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertEqual(b.calls.count("draw"), 0)
        self.assertNotIn("figure", b.out["blog/2026-03-01-drawn.html"].split("<main")[-1])
        self.assertRegex(b.out["txt/blog/2026-03-01-drawn.txt"], r"\.-- d2 -+\.\n +a: first")
        self.assertNotIn("without a description", b.run.stderr)      # no image, no alt text needed

    def test_the_width_counts_an_entry_deeper(self):
        text = HTML_ONLY.replace("## Body\n\n", "## Body\n\n### An entry\n\n  ").replace(
            "\na: first\nb: second\na -> b\n```\n", "\n  a: first\n  b: second\n  a -> b\n  ```\n")
        text += "\n  ```text {text}\n  " + "x" * 65 + "\n  ```\n"
        b = build(themed, post(text))
        self.assertIn("is 65 columns wide, line 1; the text mirror holds 64 there", b.run.stderr)


class Cache(unittest.TestCase):
    def test_the_cache_folder_spares_a_second_drawing(self):
        with tempfile.TemporaryDirectory() as cache:
            first = build(themed, post(), cache=pathlib.Path(cache))
            second = build(themed, post(), cache=pathlib.Path(cache))
        self.assertEqual(first.calls.count("draw"), 1)
        self.assertEqual(second.calls.count("draw"), 0)

    def test_the_previous_output_spares_it_too(self):
        with tempfile.TemporaryDirectory() as out:
            first = build(themed, post(), out=pathlib.Path(out))
            second = build(themed, post(), out=pathlib.Path(out))
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


class Fonts(unittest.TestCase):
    def test_the_theme_fonts_are_passed(self):
        def fonts(site):
            (site / "theme" / "fonts").mkdir(exist_ok=True)
            (site / "theme" / "fonts" / "mono.ttf").write_bytes(b"regular")
            (site / "theme" / "fonts" / "mono-bold.ttf").write_bytes(b"bold")
            p = site / "theme" / "theme.toml"
            p.write_text(p.read_text().replace("[diagrams]\n", '[diagrams]\nfont_regular = "mono.ttf"\n'
                                                                'font_bold = "mono-bold.ttf"\n', 1))
        b = build(themed, post(), fonts)
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertEqual(sorted(b.fonts.split()), ["--font-bold=mono-bold.ttf", "--font-italic=mono.ttf",
                                                   "--font-regular=mono.ttf", "--font-semibold=mono-bold.ttf"])


class Fallback(unittest.TestCase):
    def test_without_a_renderer_the_source_and_its_description(self):
        b = build(themed, post(), post(POST, "2026-03-02-drawn-too.md"), renderer=False)
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertEqual(b.run.stderr.count("(the D2 CLI): diagrams are shown as their source"), 1, b.run.stderr)
        html = b.out["blog/2026-03-01-drawn.html"]
        self.assertIn('<figure class="figure"><pre class="code" data-lang="d2" tabindex="0"><code>'
                      'a: first\nb: second\na -&gt; b</code></pre>'
                      '<figcaption>Two boxes, the first pointing to the second The flow, in short.'
                      '</figcaption></figure>', html)
        self.assertFalse([p for p in b.out if p.startswith("diagrams/")])


class Problems(unittest.TestCase):
    def test_a_diagram_without_a_description_warns_once(self):
        text = POST.replace('```d2 Two boxes, the first pointing to the second "The flow, in short."', "```d2")
        b = build(themed, post(text))
        self.assertEqual(b.run.returncode, 0, b.run.stderr)
        self.assertEqual(b.run.stderr.count(
            "warning: content/blog/2026-03-01-drawn.md: a d2 diagram without a description. "
            "Describe it after the word d2: ```d2 What the diagram shows"), 1, b.run.stderr)

    def test_a_diagram_that_cannot_be_drawn_stops_the_build(self):
        b = build(themed, post(POST.replace("a -> b\n", "a -> b\nBROKEN\n")))
        self.assertEqual(b.run.returncode, 1, b.run.stderr)
        self.assertIn("error: content/blog/2026-03-01-drawn.md: a d2 diagram cannot be drawn: "
                      "line 2:1: unexpected text. Fix its source (the syntax: https://d2lang.com/tour/intro)",
                      b.run.stderr)
        self.assertNotIn("Traceback", b.run.stderr)

    def test_a_token_style_css_lacks(self):
        def bad(site):
            with (site / "theme" / "theme.toml").open("a") as f:
                f.write('B1 = "--nope"\n')
        b = build(themed, bad, post())
        self.assertEqual(b.run.returncode, 1, b.run.stderr)
        self.assertIn('error: theme/theme.toml: [diagrams.d2] B1 = "--nope" names no colour token of style.css',
                      b.run.stderr)

    def test_an_unknown_layout(self):
        def bad(site):
            p = site / "theme" / "theme.toml"
            p.write_text(p.read_text().replace('layout = "elk"', 'layout = "tala"'))
        b = build(themed, bad, post())
        self.assertEqual(b.run.returncode, 1, b.run.stderr)
        self.assertIn('[diagrams] layout is "tala", not a layout D2 ships. Write one of dagre, elk', b.run.stderr)


if __name__ == "__main__":
    unittest.main()
