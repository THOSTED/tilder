"""build.py --check: a theme against the contract (docs/theme.md,
"Checking a theme"). Each test runs the command on a small project in a
temporary folder."""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contract
import themecheck
from config import BUILDER

LIGHT_DARK = """
:root { --text: #1a1a1a; --bg: #ffffff; --muted: #767676; --mono: ui-monospace, monospace; }
@media (prefers-color-scheme: dark) {
	:root { --bg: #16181a; --text: #e6e6e6; --muted: #a8a8a8; }
}
"""
ALL = "\n".join(f".{c} {{ }}" for c in contract.CLASSES)
SECTION = "## The HTML the builder writes"


def contract_classes(text):
    """Every class of docs/theme.md's table, in order, without duplicates.
    A cell token like `--warning` completes the block of the class before
    it that has a modifier: `.callout--info`, `--warning` -> callout--warning."""
    rows = text.split(SECTION, 1)[1].split("\n## ", 1)[0].splitlines()
    out, block = [], None
    for row in rows:
        if not row.startswith("| ") or row.startswith("|---"):
            continue
        for token in re.findall(r"`([^`]+)`", row.split("|")[1]):
            if token.startswith("--"):
                names = [block + token]
            else:
                names = re.findall(r"\.([A-Za-z_][\w-]*)", token)
                for name in names:
                    if "--" in name:
                        block = name.split("--", 1)[0]
            out += [n for n in names if n not in out]
    return out


class Check(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "content").mkdir()
        (self.root / "content" / "site.toml").write_text("")
        (self.root / "theme").mkdir()

    def tearDown(self):
        shutil.rmtree(self.root)

    def theme(self, css=None, toml=None):
        if css is not None:
            (self.root / "theme" / "style.css").write_text(css)
        if toml is not None:
            (self.root / "theme" / "theme.toml").write_text(textwrap.dedent(toml))

    def run_check(self, *extra):
        return subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(self.root),
                               "--check", *extra], capture_output=True, text=True)

    def test_a_complete_theme_passes_and_builds_nothing(self):
        self.theme(ALL + LIGHT_DARK, '[check]\ncontrast = [["--text", "--bg"], ["--muted", "--bg"]]\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        self.assertEqual(r.stdout, f"classes: {len(contract.CLASSES)} of the contract, all styled\n"
                                   "contrast: 4 pairs (light, dark), all at or above 4.5:1\n")
        self.assertFalse((self.root / "public").exists())

    def test_a_missing_class_is_named(self):
        css = "\n".join(f".{c} {{ }}" for c in contract.CLASSES if c != "toc-label")
        self.theme(css + "\n/* .toc-label { } */\n.toc-labels { }\n")
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stderr, "error: theme/style.css: no rule for .toc-label. Style it, or name it "
                                   "in [check] unstyled (theme/theme.toml)\n")
        self.assertIn(f"classes: 1 of {len(contract.CLASSES)} not styled", r.stdout)
        self.assertIn("contrast: skipped, no [check] contrast in theme/theme.toml", r.stdout)

    def test_unstyled_is_honoured(self):
        css = "\n".join(f".{c} {{ }}" for c in contract.CLASSES if c not in ("icon", "u"))
        self.theme(css, '[check]\nunstyled = ["icon", ".u"]\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"classes: {len(contract.CLASSES) - 2} of the contract, all styled", r.stdout)

    def test_low_contrast_is_named_with_its_ratio_in_each_scheme(self):
        css = ALL + ":root { --text: #777777; --bg: #ffffff; }\n" \
            "@media (prefers-color-scheme: dark) { :root { --text: #555555; --bg: #000000; } }\n"
        self.theme(css, '[check]\ncontrast = [["--text", "--bg"]]\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("error: theme/style.css: light: --text on --bg is 4.48:1, below 4.5:1. "
                      "Darken or lighten one of them", r.stderr)
        self.assertIn("error: theme/style.css: dark: --text on --bg is 2.82:1, below 4.5:1.", r.stderr)
        self.assertIn("contrast: 2 of 2 pairs below 4.5:1", r.stdout)

    def test_contrast_min(self):
        css = ALL + ":root { --text: #777777; --bg: #ffffff; }\n"
        self.theme(css, '[check]\ncontrast = [["--text", "--bg"]]\ncontrast_min = 3\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("contrast: 1 pairs (light), all at or above 3:1", r.stdout)

    def test_a_token_that_is_not_a_hex_colour(self):
        css = ALL + ":root { --text: var(--ink); --bg: #fff; }\n"
        self.theme(css, '[check]\ncontrast = [["--text", "--bg"], ["--gone", "--bg"]]\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("error: theme/style.css: light: --text is var(--ink), not a hex colour. "
                      "Write it #rrggbb, or leave its pairs out of [check] contrast", r.stderr)
        self.assertIn("error: theme/style.css: light: --gone is not set in :root.", r.stderr)

    def test_no_style_css(self):
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("classes: skipped, no theme/style.css", r.stdout)
        self.theme(toml='[check]\ncontrast = [["--text", "--bg"]]\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("error: theme/style.css: is missing, and [check] contrast names colours of it", r.stderr)

    def test_malformed_settings(self):
        self.theme(ALL, '[check]\ncontrast = ["--text", "--bg"]\nunstyled = "icon"\ncontrast_min = "AA"\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("theme/theme.toml: [check] contrast must be a list of pairs", r.stderr)
        self.assertIn("theme/theme.toml: [check] unstyled must be a list of class names", r.stderr)
        self.assertIn("theme/theme.toml: [check] contrast_min must be a number", r.stderr)

    def test_invalid_toml_is_named(self):
        self.theme(ALL, "[check\n")
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("error: theme/theme.toml: is not valid TOML:", r.stderr)

    def test_markdown_table(self):
        self.theme(ALL + LIGHT_DARK, '[check]\ncontrast = [["--text", "--bg"]]\n')
        r = self.run_check("--markdown")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "| scheme | foreground | background | ratio | minimum |\n"
                                   "|---|---|---|---:|---:|\n"
                                   "| light | `--text` | `--bg` | 17.40 | 4.5 |\n"
                                   "| dark | `--text` | `--bg` | 14.26 | 4.5 |\n")
        self.assertIn("contrast: 2 pairs (light, dark), all at or above 4.5:1", r.stderr)   # not in the table

    def test_a_theme_alone_without_content(self):
        shutil.rmtree(self.root / "content")
        self.theme(ALL + LIGHT_DARK, '[check]\ncontrast = [["--text", "--bg"]]\n')
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["theme"])


class Parts(unittest.TestCase):
    def test_tokens_dark_inherits_light(self):
        t = themecheck.tokens(LIGHT_DARK)
        self.assertEqual(t["light"]["--muted"], "#767676")
        self.assertEqual(t["dark"]["--mono"], "ui-monospace, monospace")   # not redefined: inherited
        self.assertEqual(t["dark"]["--bg"], "#16181a")
        self.assertIsNone(themecheck.tokens(":root { --bg: #fff; }")["dark"])

    def test_important_is_not_part_of_the_value(self):
        self.assertEqual(themecheck.tokens(":root { --bg: #fff !important; }")["light"], {"--bg": "#fff"})

    def test_root_inside_another_media_is_not_the_light_scheme(self):
        css = ":root { --bg: #ffffff; }\n@media print { :root { --bg: #000000; } }\n"
        self.assertEqual(themecheck.tokens(css)["light"], {"--bg": "#ffffff"})

    def test_ratio(self):
        self.assertAlmostEqual(themecheck.ratio("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(themecheck.ratio("#fff", "#ffffff"), 1.0)

    def test_missing_ignores_comments_and_longer_names(self):
        css = "/* .a { } */ .ab { } .b-c { } .c:hover { }"
        self.assertEqual(themecheck.missing(css, ["a", "b", "c"]), ["a", "b"])

    def test_a_brace_in_a_string_does_not_end_a_rule(self):
        css = ".a { content: \"}\"; color: red; }\n.b { content: '{'; }\n:root { --bg: #fff; }\n"
        self.assertEqual([p for p, _ in themecheck.rules(css)], [".a", ".b", ":root"])
        self.assertEqual(themecheck.tokens(css)["light"], {"--bg": "#fff"})


class Contract(unittest.TestCase):
    def test_classes_equal_the_table_of_docs_theme_md(self):
        text = (BUILDER / "docs" / "theme.md").read_text()
        self.assertEqual(contract_classes(text), list(contract.CLASSES))

    def test_the_starter_passes(self):
        r = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(BUILDER / "starter"),
                            "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("all styled", r.stdout)
        self.assertIn("contrast: 20 pairs (light, dark), all at or above 4.5:1", r.stdout)
