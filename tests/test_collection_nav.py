import json
import pathlib
import shutil
import tempfile
import textwrap
import unittest

from tests.helpers import build_site
import contenttypes
from config import load_config


class Flags(unittest.TestCase):
    def test_defaults_and_theme_values(self):
        load_config()
        types = contenttypes.load()
        for name in ("page", "post", "event", "member", "talk"):
            self.assertFalse(types[name].SEQUENTIAL, name)
            self.assertFalse(types[name].LOCALIZED_OUTPUTS, name)
        self.assertTrue(types["guide"].SEQUENTIAL)
        self.assertTrue(types["guide"].LOCALIZED_OUTPUTS)

    def test_flag_kind_is_checked(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            (tmp / "odd.py").write_text(textwrap.dedent('''
                NAME = "odd"
                SEQUENTIAL = "yes"
                def entry(item, link, conf):
                    return None
            '''))
            load_config()
            contenttypes.load([contenttypes.BUILTIN, tmp])
            messages = [str(e) for e in contenttypes.ERRORS]
        finally:
            shutil.rmtree(tmp)
        self.assertTrue(any("SEQUENTIAL must be a bool, not a str" in m for m in messages), messages)
        self.assertNotIn("odd", contenttypes.TYPES)


class LocalizedOutputs(unittest.TestCase):
    def test_one_file_per_language(self):
        out = build_site()
        self.assertEqual(json.loads(out["guides/index.json"]),
                         ["Introduction", "Setup", "Deployment", "Tuning"])
        self.assertEqual(json.loads(out["fr/guides/index.json"]),
                         ["Introduction", "Installation", "Deployment", "Tuning"])

    def test_other_outputs_stay_once(self):
        out = build_site()
        self.assertIn("events.ics", out)
        self.assertNotIn("fr/events.ics", out)
