import os
import subprocess
import sys
import unittest

from tests.helpers import build_site  # noqa: F401
import watch
from config import BUILDER, CONTENT, THEME


class Watch(unittest.TestCase):
    def test_restart_predicate(self):
        self.assertTrue(watch.restarts({str(BUILDER / "src" / "page.py")}))
        self.assertTrue(watch.restarts({str(THEME / "types" / "talk.py")}))
        self.assertFalse(watch.restarts({str(THEME / "style.css"), str(CONTENT / "index.md")}))

    def test_version_flag(self):
        entry = str(BUILDER / "build.py")
        env = {**os.environ, "TILDER_VERSION": "v1.2.3"}
        self.assertEqual(subprocess.run([sys.executable, entry, "--version"], capture_output=True,
                                        text=True, env=env).stdout.strip(), "v1.2.3")
        env.pop("TILDER_VERSION")
        self.assertEqual(subprocess.run([sys.executable, entry, "--version"], capture_output=True,
                                        text=True, env=env).stdout.strip(), "dev")
