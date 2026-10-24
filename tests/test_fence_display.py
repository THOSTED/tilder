"""Display markers on code blocks: a fence's opening line may end with
{html} (the page only) or {text} (the text mirror only); without one a
block is in both. Only trailing {html} and {text} tokens are markers."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import BUILDER
import markdown

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"

PAGE = textwrap.dedent('''\
    ---
    man: TEST-FENCES(7)
    title: Fences
    tagline: fences
    nav: -
    description: A page of code blocks, each shown on the page, in the mirror, or both.
    ---

    ## Body

    ```console {html}
    $ echo page-only
    ```

    ```toml {text}
    mirror_only = true
    ```

    ```{text}
    no-language-mirror-only
    ```

    ```
    both-renderings
    ```

    ```text
    plain-text-both
    ```
    ''')


def build(text):
    with tempfile.TemporaryDirectory() as tmp:
        site = pathlib.Path(tmp) / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        (site / "content" / "fences.md").write_text(text)
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15",
               "TILDER_D2": str(pathlib.Path(tmp) / "no-d2")}
        run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                              "--out", str(site / "out")], capture_output=True, text=True, env=env)
        out = {}
        for name in ("fences.html", "txt/fences.txt", "ansi/fences.txt"):
            p = site / "out" / name
            out[name] = p.read_text() if p.is_file() else ""
        return run, out


class Markers(unittest.TestCase):
    def test_read(self):
        cases = {
            "```console {html}": ("console", "html"),
            "```toml {text}": ("toml", "text"),
            "```{text}": ("", "text"),
            "```": ("", None),
            "```python {html} {html}": ("python", "html"),
            "```text {other}": ("text {other}", None),     # not a marker: part of the language
            "```sh {html} x": ("sh {html} x", None),        # not trailing
        }
        for head, (lang, only) in cases.items():
            n = markdown.classify([head, "x"])
            self.assertEqual((n["k"], n["lang"], n["only"]), ("code", lang, only), head)

    def test_both_is_an_error(self):
        with self.assertRaises(markdown.FenceError):
            markdown.classify(["```sh {html} {text}", "x"])


class Rendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result, cls.out = build(PAGE)
        assert cls.result.returncode == 0, cls.result.stderr

    def test_the_page(self):
        html = self.out["fences.html"]
        for shown in ("page-only", "both-renderings", "plain-text-both"):
            self.assertIn(shown, html)
        for hidden in ("mirror_only", "no-language-mirror-only"):
            self.assertNotIn(hidden, html)

    def test_the_mirror(self):
        for name in ("txt/fences.txt", "ansi/fences.txt"):
            txt = self.out[name]
            for shown in ("mirror_only", "no-language-mirror-only", "both-renderings", "plain-text-both"):
                self.assertIn(shown, txt, name)
            self.assertNotIn("page-only", txt, name)

    def test_no_warning(self):
        self.assertNotIn("warning:", self.result.stderr)

    def test_the_copy_script_only_where_the_page_has_code(self):
        import page
        self.assertFalse(page.has_code([{"k": "code", "only": "text"}]))
        self.assertTrue(page.has_code([{"k": "code", "only": "html"}]))
        self.assertTrue(page.has_code([{"k": "code", "only": None}]))
        self.assertFalse(page.has_code([{"k": "diagram", "only": "text"}]))

    def test_both_markers_stop_the_build(self):
        run, _ = build(PAGE.replace("```console {html}", "```console {html} {text}"))
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("error: content/fences.md: a code block is marked both {html} and {text}, so it would "
                      "be shown nowhere. Keep one marker, or none to show it in both", run.stderr)
        self.assertNotIn("Traceback", run.stderr)


if __name__ == "__main__":
    unittest.main()
