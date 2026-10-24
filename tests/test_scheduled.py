"""Scheduled posts: a post dated after the build's date (BUILD_TODAY, else
the day) is not published - no page, no mirror, no card, no feed item, no
sitemap entry, no file of its folder - until a build on or after that
date. `scheduled = false` on a collection publishes every post. A link
to a scheduled post is a warning. Each build runs on an edited copy of
the fixture in a subprocess, since config reads its paths at import."""

import os
from tests import site_warnings
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import BUILDER

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"
TODAY = "2026-06-15"
LATER = "blog/2026-07-01-later"       # a flat post, in English and French
PICS = "blog/2026-07-02-pictures"     # a post kept as a folder, with a file


def post(title):
    return (f"---\ntitle: {title}\ndescription: A post written ahead of its date, "
            f"to test scheduled publishing.\n---\n\n## Body\n\nA paragraph.\n")


def add_posts(site):
    blog = site / "content" / "blog"
    (blog / "2026-07-01-later.md").write_text(post("Later"))
    (blog / "2026-07-01-later.fr.md").write_text(post("Plus tard"))
    (blog / "2026-07-02-pictures").mkdir()
    (blog / "2026-07-02-pictures" / "index.md").write_text(post("Pictures"))
    shutil.copy(blog / "2026-04-01-picture" / "square.svg", blog / "2026-07-02-pictures" / "square.svg")


def build(*edits, today=TODAY):
    """Build a copy of the fixture with the posts added, then edited by
    each edit(site); (run, {path: text})."""
    with tempfile.TemporaryDirectory() as tmp:
        site = pathlib.Path(tmp) / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        add_posts(site)
        for edit in edits:
            edit(site)
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": today}
        run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                              "--out", str(site / "out")], capture_output=True, text=True, env=env)
        out = {}
        if (site / "out").is_dir():
            for p in (site / "out").rglob("*"):
                if p.is_file() and p.suffix not in (".png", ".ico"):
                    out[str(p.relative_to(site / "out"))] = p.read_text(errors="replace")
        return run, out


def append(file, text):
    def edit(site):
        with (site / "content" / file).open("a") as f:
            f.write(text)
    return edit


def collection(key, value, name="blog"):
    """Set a key of [collections.<name>] in site.toml."""
    def edit(site):
        path = site / "content" / "site.toml"
        text = path.read_text()
        head = f"[collections.{name}]\n"
        path.write_text(text.replace(head, f"{head}{key} = {value}\n", 1))
    return edit


def mentions(out, slug):
    """Every output that names the slug."""
    return sorted(p for p, text in out.items() if slug in p or slug in text)


class Scheduled(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_, cls.out = build()
        assert cls.run_.returncode == 0, cls.run_.stderr

    def test_a_post_after_today_is_nowhere(self):
        for slug in ("2026-07-01-later", "2026-07-02-pictures"):
            self.assertEqual(mentions(self.out, slug), [], slug)

    def test_its_folder_files_are_not_copied(self):
        self.assertNotIn(f"{PICS}/square.svg", self.out)
        self.assertIn("blog/2026-04-01-picture/square.svg", self.out)

    def test_the_published_posts_are_still_there(self):
        self.assertIn("blog/2026-01-01-hello.html", self.out)
        self.assertIn("2026-01-01-hello", self.out["blog/feed.xml"])
        self.assertIn("2026-01-01-hello", self.out["sitemap.xml"])

    def test_the_summary_counts_them(self):
        self.assertRegex(self.run_.stdout, r"blog \(post, \d+ items, 2 scheduled\)")

    def test_no_warning_without_a_link(self):
        self.assertEqual(site_warnings(self.run_.stderr), [], self.run_.stderr)

    def test_on_its_date_it_is_published_everywhere(self):
        run, out = build(today="2026-07-01")
        self.assertEqual(run.returncode, 0, run.stderr)
        for path in (f"{LATER}.html", f"fr/{LATER}.html", f"txt/{LATER}.txt",
                     f"ansi/{LATER}.txt", f"txt/fr/{LATER}.txt"):
            self.assertIn(path, out)
        self.assertIn(f"https://test.example/{LATER}", out["sitemap.xml"])
        self.assertIn(f"https://test.example/{LATER}", out["blog/feed.xml"])
        self.assertIn(LATER.split("/")[1], out["blog/index.html"])
        # the next day's post still waits
        self.assertEqual(mentions(out, "2026-07-02-pictures"), [])
        self.assertRegex(run.stdout, r"blog \(post, \d+ items, 1 scheduled\)")

    def test_after_its_date_the_folder_is_copied(self):
        run, out = build(today="2026-07-02")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(f"{PICS}.html", out)
        self.assertIn(f"{PICS}/square.svg", out)
        self.assertNotIn("scheduled", run.stdout)

    def test_scheduled_false_publishes_every_post(self):
        run, out = build(collection("scheduled", "false"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(f"{LATER}.html", out)
        self.assertIn(f"{PICS}/square.svg", out)
        self.assertNotIn("scheduled", run.stdout)

    def test_scheduled_true_is_the_default(self):
        run, out = build(collection("scheduled", "true"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(out, self.out)

    def test_events_are_never_scheduled(self):
        self.assertIn("events/2099-01-01-future-meetup.html", self.out)


class Links(unittest.TestCase):
    def test_a_link_to_a_scheduled_post_warns_once_and_builds(self):
        run, out = build(append("index.md", f"\n[soon]({LATER}) and [again]({LATER}).\n"))
        self.assertEqual(run.returncode, 0, run.stderr)
        line = (f"warning: content/index.md: links to {LATER}, scheduled for 2026-07-01: "
                f"the link is broken until then. Remove the link, or publish the item earlier "
                f"(its date, or scheduled = false under [collections.blog])\n")
        self.assertIn(line, run.stderr)
        self.assertEqual(len(site_warnings(run.stderr)), 1, run.stderr)
        self.assertNotIn(f"{LATER}.html", out)

    def test_a_link_to_a_file_of_its_folder_warns(self):
        run, _ = build(append("index.md", f"\n[a picture](/{PICS}/square.svg#top)\n"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(f"links to /{PICS}/square.svg#top, scheduled for 2026-07-02", run.stderr)

    def test_a_link_from_a_french_page_with_its_prefix_warns(self):
        run, _ = build(append("index.fr.md", f"\n[bientot](/fr/{LATER})\n"))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(f"warning: content/index.fr.md: links to /fr/{LATER}, scheduled", run.stderr)

    def test_no_warning_once_published(self):
        run, _ = build(append("index.md", f"\n[soon]({LATER})\n"), today="2026-07-01")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("scheduled for", run.stderr)


class Invalid(unittest.TestCase):
    def test_scheduled_on_a_type_that_does_not_schedule(self):
        run, _ = build(collection("scheduled", "true", "events"))
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn('error: content/site.toml: collection "events" sets scheduled, '
                      'and its type "event" does not schedule its items.', run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_scheduled_must_be_a_bool(self):
        run, _ = build(collection("scheduled", '"yes"'))
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn('error: content/site.toml: collection "blog" has scheduled = \'yes\'. '
                      "Write scheduled = true or scheduled = false\n", run.stderr)


if __name__ == "__main__":
    unittest.main()
