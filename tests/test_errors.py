"""Errors of a whole build, seen as the user sees them: one line on stderr,
exit status 1, a traceback only with --debug. Each test builds an edited
copy of the fixture in a subprocess, since config reads its paths at import."""

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

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"


class Errors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = pathlib.Path(self.tmp.name) / "site"
        shutil.copytree(FIXTURE, self.site, ignore=shutil.ignore_patterns("__pycache__"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = self.site / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text))

    def declare(self, toml):
        with (self.site / "content" / "site.toml").open("a") as f:
            f.write("\n" + textwrap.dedent(toml))

    def build(self, *flags):
        env = {**os.environ, "SITE_ROOT": str(self.site), "BUILD_TODAY": "2026-06-15"}
        return subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(self.site),
                               "--out", str(self.site / "out"), *flags],
                              capture_output=True, text=True, env=env)

    def add_bad_type(self):
        self.write("theme/types/bad.py", '''
            NAME = "bad"
            def entry(item, link, conf):
                raise KeyError("boom")
        ''')
        self.declare('[collections.bads]\ntype = "bad"\n')
        self.write("content/bads/one.md", """\
            ---
            title: One
            description: An item of a type whose entry function raises, to test the error line.
            ---

            ## Body

            A paragraph.
        """)

    def test_hook_error_is_one_line_naming_module_and_hook(self):
        self.add_bad_type()
        run = self.build()
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("error: content/bads/one.md: theme/types/bad.py: entry() failed: KeyError: 'boom'. "
                      "Run with --debug for the traceback\n", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_hook_error_traceback_with_debug(self):
        self.add_bad_type()
        run = self.build("--debug")
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("theme/types/bad.py: entry() failed: KeyError: 'boom'", run.stderr)
        self.assertIn("Traceback", run.stderr)

    def test_post_without_title_names_the_file(self):
        self.write("content/blog/2026-02-01-untitled.md", """\
            ---
            description: A post with no title, to test the error line.
            ---

            ## Body

            A paragraph.
        """)
        run = self.build()
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("error: content/blog/2026-02-01-untitled.md: types/post.py: entry() failed: "
                      "KeyError: 'title'. Run with --debug for the traceback\n", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_page_error_outside_a_hook_names_the_file(self):
        # No section: no card, so the missing title fails in the page's own rendering.
        self.write("content/blog/2026-02-01-untitled.md", "---\ndescription: No title.\n---\n\nText.\n")
        run = self.build()
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("error: content/blog/2026-02-01-untitled.md: cannot be built: KeyError: 'title'. "
                      "Run with --debug for the traceback\n", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_bad_date_in_a_file_name(self):
        self.write("content/events/2026-13-01-x.md", "---\ntitle: X\ndescription: A bad date.\n---\n")
        run = self.build()
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn('error: content/events/2026-13-01-x.md: "2026-13-01" is not a date. '
                      "Name the file YYYY-MM-DD-slug.md with the event's date\n", run.stderr)

    def test_type_and_collection_errors_are_reported_together(self):
        self.write("theme/types/clash.py", '''
            NAME = "clash"
            MARKERS = {"upcoming": lambda items, conf: {"items": []}}
            def entry(item, link, conf):
                return None
        ''')
        self.declare('[collections.oops]\ntype = "tlak"\n')
        run = self.build()
        self.assertEqual(run.returncode, 1, run.stderr)
        lines = [l for l in run.stderr.splitlines() if l.startswith("error: ")]
        self.assertEqual(len(lines), 2, run.stderr)
        self.assertIn('theme/types/clash.py: MARKERS["upcoming"] is already claimed by type "event" '
                      "(types/event.py)", lines[0])
        self.assertIn('content/site.toml: collection "oops" has type "tlak", which no type defines', lines[1])


if __name__ == "__main__":
    unittest.main()
