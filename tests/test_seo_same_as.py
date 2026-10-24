"""[seo] same_as: the organisation's official profiles elsewhere, written as
the sameAs of the Organization node in every page's JSON-LD. Absolute
http(s) URLs only; empty by default, and then no sameAs at all. Each build
runs on an edited copy of the fixture in a subprocess, since config reads
its paths at import."""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import BUILDER

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"
HINT = 'Give a list of absolute http(s) URLs, like ["https://example.org/our-page"]'


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
        out = {}
        if (site / "out").is_dir():
            for p in (site / "out").rglob("*.html"):
                out[str(p.relative_to(site / "out"))] = p.read_text()
        return run, out


def setting(value, file="site.toml"):
    """Set [seo] same_as in content/<file>, inside its [seo] table if it has one."""
    def edit(site):
        path = site / "content" / file
        text = path.read_text() if path.is_file() else ""
        line = f"same_as = {value}\n"
        if re.search(r"^\[seo\]\s*$", text, re.M):
            text = re.sub(r"^\[seo\]\s*$\n?", lambda m: "[seo]\n" + line, text, count=1, flags=re.M)
        else:
            text += f"\n[seo]\n{line}"
        path.write_text(text)
    return edit


def organization(html):
    data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    graph = json.loads(data.replace("<\\/", "</"))["@graph"]
    return next(n for n in graph if n["@type"] == "Organization")


class SameAs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run, cls.default = build()
        assert run.returncode == 0, run.stderr

    def test_unset_writes_no_same_as(self):
        for path, html in self.default.items():
            if "application/ld+json" in html:
                self.assertNotIn("sameAs", organization(html), path)

    def test_an_empty_list_changes_nothing(self):
        run, out = build(setting("[]"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(out, self.default)

    def test_the_urls_are_the_organizations_same_as_on_every_page(self):
        urls = ["https://www.linkedin.com/company/example/", "http://example.org/about"]
        run, out = build(setting(json.dumps(urls)))
        self.assertEqual(run.returncode, 0, run.stderr)
        pages = [p for p, html in out.items() if "application/ld+json" in html]
        self.assertTrue(pages)
        for path in pages:
            self.assertEqual(organization(out[path])["sameAs"], urls, path)

    def test_only_the_organization_changes(self):
        run, out = build(setting('["https://example.org/a"]'))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(sorted(out), sorted(self.default))
        for path, html in self.default.items():
            self.assertEqual(out[path].replace(',"sameAs":["https://example.org/a"]', ""), html, path)

    def test_a_language_file_sets_its_own(self):
        run, out = build(setting('["https://example.org/fr"]', "site.fr.toml"))
        self.assertEqual(run.returncode, 0, run.stderr)
        fr = [p for p in out if p.startswith("fr/") and "application/ld+json" in out[p]]
        self.assertTrue(fr)
        for path, html in out.items():
            if "application/ld+json" not in html:
                continue
            if path in fr:
                self.assertEqual(organization(html)["sameAs"], ["https://example.org/fr"], path)
            else:
                self.assertNotIn("sameAs", organization(html), path)


class Invalid(unittest.TestCase):
    def assertRefused(self, value, what, file="site.toml", count=1):
        run, _ = build(setting(value, file))
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn(f"error: content/{file}: [seo] same_as {what}. {HINT}\n", run.stderr)
        self.assertEqual(run.stderr.count("error: "), count, run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_a_string_instead_of_a_list(self):
        self.assertRefused('"https://example.org/"', 'is "https://example.org/", not a list')

    def test_a_relative_url(self):
        self.assertRefused('["/about"]', 'holds "/about", not an absolute http(s) URL')

    def test_a_url_without_a_scheme(self):
        self.assertRefused('["www.example.org"]', 'holds "www.example.org", not an absolute http(s) URL')

    def test_another_scheme(self):
        self.assertRefused('["mailto:a@example.org"]',
                           'holds "mailto:a@example.org", not an absolute http(s) URL')

    def test_no_host(self):
        self.assertRefused('["https://"]', 'holds "https://", not an absolute http(s) URL')

    def test_a_space(self):
        self.assertRefused('["https://example.org/a b"]',
                           'holds "https://example.org/a b", not an absolute http(s) URL')

    def test_not_a_string(self):
        self.assertRefused("[42]", "holds 42, not an absolute http(s) URL")

    def test_every_bad_entry_is_reported(self):
        self.assertRefused('["/a", "https://example.org/", "/b"]',
                           'holds "/b", not an absolute http(s) URL', count=2)

    def test_in_a_language_file(self):
        self.assertRefused('["/about"]', 'holds "/about", not an absolute http(s) URL', "site.fr.toml")


if __name__ == "__main__":
    unittest.main()
