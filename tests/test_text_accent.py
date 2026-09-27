"""[text] accent: the one accent of the coloured text mirror (ansi/), one of
the eight colour names or a 256-colour index from 16 to 255. Each build
runs on an edited copy of the fixture in a subprocess, since config reads
its paths at import."""

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
import ansify

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"
CYAN = "\033[36m"
ESC = re.compile(r"\x1b\[[0-9;]*m")
ACCEPTED = ("one of black, red, green, yellow, blue, magenta, cyan, white, "
            "or a 256-colour index from 16 to 255 (208: orange)")


def build(edit=None):
    """Build a copy of the fixture, edited by edit(site); (run, {path: text})."""
    with tempfile.TemporaryDirectory() as tmp:
        site = pathlib.Path(tmp) / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        if edit:
            edit(site)
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15"}
        run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                              "--out", str(site / "out")], capture_output=True, text=True, env=env)
        out = {}  # the images are left out: a rasteriser may stamp them with the time
        if (site / "out").is_dir():
            for p in (site / "out").rglob("*"):
                if p.is_file() and p.suffix not in (".png", ".ico"):
                    out[str(p.relative_to(site / "out"))] = p.read_bytes()
        return run, out


def setting(value, file="site.toml"):
    def edit(site):
        with (site / "content" / file).open("a") as f:
            f.write(f"\n[text]\naccent = {value}\n")
    return edit


class Sequence(unittest.TestCase):
    def test_names_are_the_eight_colours(self):
        names = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
        for n, name in enumerate(names):
            self.assertEqual(ansify.sgr(name), f"\033[3{n}m", name)

    def test_an_index_is_a_256_colour_foreground(self):
        self.assertEqual(ansify.sgr(16), "\033[38;5;16m")
        self.assertEqual(ansify.sgr(208), "\033[38;5;208m")
        self.assertEqual(ansify.sgr(255), "\033[38;5;255m")

    def test_anything_else_is_none(self):
        for value in ("orange", "Cyan", "208", "", 0, 15, 256, -1, True, False, 208.0, [], {}):
            self.assertIsNone(ansify.sgr(value), repr(value))

    def test_the_default_accent_is_cyan(self):
        self.assertEqual(ansify.ACCENT, CYAN)


class Accent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run, cls.default = build()
        assert run.returncode == 0, run.stderr

    def assertOnlyAccentChanged(self, out, seq):
        self.assertEqual(sorted(out), sorted(self.default))
        for path, data in self.default.items():
            if path.startswith("ansi/"):
                self.assertEqual(out[path].decode(), data.decode().replace(CYAN, seq), path)
            else:
                self.assertEqual(out[path], data, path)

    def test_the_default_is_cyan_and_saying_so_changes_nothing(self):
        self.assertIn(CYAN, self.default["ansi/index.txt"].decode())
        run, out = build(setting('"cyan"'))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(out, self.default)

    def test_a_name_changes_the_accent_sequences_only(self):
        run, out = build(setting('"yellow"'))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertOnlyAccentChanged(out, "\033[33m")

    def test_an_index_changes_the_accent_sequences_only(self):
        run, out = build(setting("208"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertOnlyAccentChanged(out, "\033[38;5;208m")
        self.assertIn("\033[38;5;208m", out["ansi/index.txt"].decode())
        for path in (p for p in out if p.startswith("ansi/")):
            txt = out["txt/" + path[len("ansi/"):]].decode()
            self.assertEqual(ESC.sub("", out[path].decode()), txt, path)

    def test_a_language_file_sets_its_own_accent(self):
        run, out = build(setting("208", "site.fr.toml"))
        self.assertEqual(run.returncode, 0, run.stderr)
        fr = [p for p in out if p.startswith("ansi/fr/")]
        self.assertTrue(fr)
        for path in (p for p in out if p.startswith("ansi/")):
            text = out[path].decode()
            if path in fr:
                self.assertNotIn(CYAN, text, path)
            else:
                self.assertEqual(out[path], self.default[path], path)
        self.assertIn("\033[38;5;208m", "".join(out[p].decode() for p in fr))


class Invalid(unittest.TestCase):
    def assertRefused(self, value, shown, file="site.toml"):
        run, _ = build(setting(value, file))
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn(f"error: content/{file}: [text] accent is {shown}, not a colour. "
                      f"Set {ACCEPTED}\n", run.stderr)
        self.assertEqual(run.stderr.count("error: "), 1, run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_an_unknown_name(self):
        self.assertRefused('"orange"', '"orange"')

    def test_a_string_that_is_not_a_name(self):
        self.assertRefused('"208"', '"208"')

    def test_one_of_the_first_sixteen_indexes(self):
        self.assertRefused("15", "15")

    def test_an_index_past_255(self):
        self.assertRefused("256", "256")

    def test_a_bool(self):
        self.assertRefused("true", "true")

    def test_in_a_language_file(self):
        self.assertRefused('"orange"', '"orange"', "site.fr.toml")


if __name__ == "__main__":
    unittest.main()
