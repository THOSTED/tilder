"""Hidden files and editors' leftovers in content/, theme/ and assets/ are
neither pages, nor items, nor copied, nor watched: a vim swap file next to
an event must not be published. .well-known/ is served on purpose."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import BUILDER, hidden

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"

LEFTOVERS = [
    "content/events/2099-01-01-future-meetup/.index.md.swp",
    "content/blog/.2026-01-01-hello.md.swo",
    "content/blog/2026-01-01-hello.md~",
    "content/blog/#notes.md#",
    "content/.#index.md",
    "content/.DS_Store",
    "content/drafts.swp",
    "content/.hidden/page.md",
    "content/.hidden/photo.png",
    "content/blog/.2026-03-03-secret.md",
    "theme/.style.css.swp",
    "theme/fonts/.DS_Store",
    "assets/logo.svg~",
]


class Rule(unittest.TestCase):
    def test_hidden(self):
        for rel in ("a/.x.swp", ".DS_Store", ".#a.md", "a.md~", "a.swp", "a.swo", "a.swx",
                    "#a.md#", ".git/HEAD", ".hidden/x.png", "a/.b/c.md"):
            self.assertTrue(hidden(rel), rel)

    def test_not_hidden(self):
        for rel in (".well-known/security.txt", "a/b.md", "x.svg", "notes#1.md", "a~b.md", "swp.md"):
            self.assertFalse(hidden(rel), rel)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp) / "site"
            shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
            (site / "assets").mkdir(exist_ok=True)
            for rel in LEFTOVERS:
                p = site / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                body = "---\ntitle: Secret\ndescription: Never published, a hidden draft of the fixture site.\n---\n"
                p.write_text(body if rel.endswith(".md") else "leftover")
            (site / "content" / ".well-known").mkdir()
            (site / "content" / ".well-known" / "security.txt").write_text("Contact: x\n")
            env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15"}
            cls.result = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                                      "--out", str(site / "out")], capture_output=True, text=True, env=env)
            cls.out = sorted(str(p.relative_to(site / "out")) for p in (site / "out").rglob("*") if p.is_file())
            import watch
            saved = (watch.CONTENT, watch.THEME, watch.ASSETS, watch.BUILDER, watch.EXTRA)
            watch.CONTENT, watch.THEME, watch.ASSETS = site / "content", site / "theme", site / "assets"
            watch.BUILDER, watch.EXTRA = site / "no-builder", []
            try:
                cls.snap = list(watch.snapshot())
            finally:
                watch.CONTENT, watch.THEME, watch.ASSETS, watch.BUILDER, watch.EXTRA = saved

    def test_it_builds(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_no_leftover_is_published(self):
        bad = [p for p in self.out if hidden(p) or "secret" in p or "hidden" in p or "#" in p]
        self.assertEqual(bad, [])

    def test_well_known_is(self):
        self.assertIn(".well-known/security.txt", self.out)

    def test_the_watcher_ignores_them(self):
        self.assertTrue(any(k.endswith("content/index.md") for k in self.snap))
        for rel in LEFTOVERS:
            self.assertFalse(any(k.endswith(rel) for k in self.snap), rel)


if __name__ == "__main__":
    unittest.main()
