import contextlib
import io
import pathlib
import unittest

from tests import helpers  # noqa: F401 - triggers tests.__init__ setup
import report
from config import ROOT


class Report(unittest.TestCase):
    def test_message_shape(self):
        e = report.error(ROOT / "content" / "site.toml", 'collection "talks" has type "talk", which no type defines',
                         "Types loaded: page, post")
        self.assertEqual(e.items[0][0],
                         'content/site.toml: collection "talks" has type "talk", which no type defines. '
                         "Types loaded: page, post")

    def test_line_and_no_hint(self):
        e = report.error(ROOT / "content" / "x.md", "bad key", line=3)
        self.assertEqual(str(e), "content/x.md:3: bad key")

    def test_path_outside_root_is_kept(self):
        e = report.error(pathlib.Path("/elsewhere/t.py"), "boom")
        self.assertEqual(str(e), "/elsewhere/t.py: boom")

    def test_fail_gathers(self):
        with self.assertRaises(report.BuildError) as cm:
            report.fail([report.error("a", "one"), report.error("b", "two", "fix it")])
        self.assertEqual([m for m, _ in cm.exception.items], ["a: one", "b: two. fix it"])

    def test_report_prints_one_line_per_item(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            report.report(report.BuildError([("a: one", None), ("b: two", None)]))
        self.assertEqual(err.getvalue(), "error: a: one\nerror: b: two\n")

    def test_report_hides_traceback_without_debug(self):
        err = io.StringIO()
        cause = ValueError("inner")
        with contextlib.redirect_stderr(err):
            report.report(report.error("t.py", "cannot be imported", exc=cause))
        self.assertNotIn("Traceback", err.getvalue())
        report.DEBUG = True
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                report.report(report.error("t.py", "cannot be imported", exc=cause))
            self.assertIn("ValueError: inner", err.getvalue())
        finally:
            report.DEBUG = False

    def test_report_any_exception(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            report.report(KeyError("title"))
        self.assertEqual(err.getvalue(), "error: KeyError: 'title'\n")

    def test_warning(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            report.warning("content/x.md", "image has no alt text", "Write one")
        self.assertEqual(err.getvalue(), "warning: content/x.md: image has no alt text. Write one\n")
