import pathlib
import unittest

from tests.helpers import rebuild
from config import THEME


class Scripts(unittest.TestCase):
    def test_type_script_only_where_it_lists_and_only_if_shipped(self):
        js = THEME / "members.js"
        js.write_text("/* fixture */\n")
        try:
            out = rebuild()
        finally:
            js.unlink()
        self.assertIn('<script src="members.js" defer></script>', out["members.html"])
        self.assertNotIn("members.js", out["members/ada-lovelace.html"])
        self.assertNotIn("members.js", out["index.html"])
        self.assertIn("members.js", out)  # the theme file is served
        without = rebuild()
        self.assertNotIn("members.js", without["members.html"])
        self.assertNotIn("members.js", without)

    def test_code_js_is_not_a_type_script(self):
        js = THEME / "code.js"
        js.write_text("/* fixture */\n")
        try:
            out = rebuild()
        finally:
            js.unlink()
        self.assertIn('<script src="../code.js" defer data-copy="copy" data-copied="copied"></script>',
                      out["blog/2026-01-01-hello.html"])
        self.assertNotIn("code.js", out["members.html"])
