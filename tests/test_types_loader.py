import contextlib
import io
import pathlib
import tempfile
import textwrap
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
import report


def write(folder, name, body):
    p = pathlib.Path(folder) / f"{name}.py"
    p.write_text(textwrap.dedent(body))
    return p


class Loader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_minimal_module_gets_defaults(self):
        write(self.dir, "note", 'NAME = "note"\ndef entry(item, link, conf): return None\n')
        types = contenttypes.load([self.dir])
        m = types["note"]
        self.assertFalse(m.DATED)
        self.assertFalse(m.ARTICLE)
        self.assertEqual(m.OG_TYPE, "website")
        self.assertEqual(m.LAYOUT, "note")
        self.assertEqual(m.SCRIPT, "")
        self.assertEqual(m.DEFAULTS, {})
        self.assertEqual(m.MARKERS, {})
        self.assertFalse(m.HAS_FEED)
        item = {"slug": "s", "meta": {}}
        self.assertEqual(m.sort_key(item, {}), "s")
        self.assertIsNone(m.json_ld(item, {}))
        self.assertIsNone(m.feed_item(item, {}))
        self.assertEqual(m.meta_tags(item, {}), [])
        self.assertEqual(m.outputs([], {}), {})
        self.assertEqual(m.list_data({}), {})
        self.assertIsNone(m.defaults(item, {}))

    def test_later_dir_replaces_by_name(self):
        a, b = self.dir / "a", self.dir / "b"
        a.mkdir(); b.mkdir()
        write(a, "member", 'NAME = "member"\nDATED = False\ndef entry(item, link, conf): return "a"\n')
        write(b, "mine", 'NAME = "member"\ndef entry(item, link, conf): return "b"\n')
        types = contenttypes.load([a, b])
        self.assertEqual(list(types), ["member"])
        self.assertEqual(types["member"].entry(None, True, {}), "b")

    def test_theme_type_can_build_on_a_builtin(self):
        a, b = self.dir / "a", self.dir / "b"
        a.mkdir(); b.mkdir()
        write(a, "event", 'NAME = "event"\nDEFAULTS = {"x": 1}\ndef entry(item, link, conf): return None\n')
        write(b, "talk", '''
            from contenttypes import TYPES
            NAME = "talk"
            DEFAULTS = {**TYPES["event"].DEFAULTS, "y": 2}
            def entry(item, link, conf): return None
        ''')
        types = contenttypes.load([a, b])
        self.assertEqual(types["talk"].DEFAULTS, {"x": 1, "y": 2})

    def test_underscore_files_are_skipped(self):
        write(self.dir, "_draft", "raise RuntimeError('never imported')\n")
        self.assertEqual(contenttypes.load([self.dir]), {})

    def errors(self, *dirs):
        contenttypes.load(list(dirs))   # gathers, does not raise
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.check()
        return [m for m, _ in cm.exception.items]

    def test_missing_name_and_entry(self):
        p = write(self.dir, "bad", "X = 1\n")
        msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 2)
        self.assertTrue(all(m.startswith(f"{p}: ") for m in msgs), msgs)
        self.assertIn("NAME must be a string", msgs[0])
        self.assertIn("entry(item, link, conf) is missing", msgs[1])

    def test_import_failure_is_one_line_and_names_the_file(self):
        p = write(self.dir, "broken", "def entry(item, link, conf)\n")  # SyntaxError
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 1)
        self.assertIn(f"{p}: cannot be imported: SyntaxError", msgs[0])
        self.assertIn("--debug", msgs[0])
        self.assertNotIn("Traceback", err.getvalue())

    def test_wrong_attribute_types(self):
        write(self.dir, "bad", 'NAME = "bad"\nDATED = "yes"\nMARKERS = ["x"]\ndef entry(item, link, conf): return None\n')
        msgs = self.errors(self.dir)
        self.assertTrue(any("DATED must be a bool" in m for m in msgs), msgs)
        self.assertTrue(any("MARKERS must be a dict" in m for m in msgs), msgs)

    def test_marker_clash_names_both(self):
        write(self.dir, "post", 'NAME = "post"\nMARKERS = {"posts": lambda items, conf: {}}\ndef entry(item, link, conf): return None\n')
        write(self.dir, "news", 'NAME = "news"\nMARKERS = {"posts": lambda items, conf: {}}\ndef entry(item, link, conf): return None\n')
        msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 1)
        self.assertIn('MARKERS["posts"] is already claimed by type "news"', msgs[0])
        self.assertIn('naming yours "news"', msgs[0])

    def test_same_name_in_one_dir_is_an_error(self):
        write(self.dir, "a", 'NAME = "dup"\ndef entry(item, link, conf): return None\n')
        write(self.dir, "b", 'NAME = "dup"\ndef entry(item, link, conf): return None\n')
        msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 1)
        self.assertIn('NAME "dup" is also the name of', msgs[0])

    def test_all_errors_are_gathered(self):
        write(self.dir, "one", "X = 1\n")
        write(self.dir, "two", "def entry(item, link, conf)\n")
        self.assertEqual(len(self.errors(self.dir)), 3)

    def test_markers_index(self):
        write(self.dir, "ev", 'NAME = "ev"\nMARKERS = {"upcoming": lambda i, c: {}, "past": lambda i, c: {}}\ndef entry(item, link, conf): return None\n')
        contenttypes.load([self.dir])
        self.assertEqual(contenttypes.MARKERS, {"upcoming": "ev", "past": "ev"})
