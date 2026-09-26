import os
import subprocess
import sys
import unittest

from tests.helpers import build_site  # noqa: F401
import watch
from config import BUILDER, THEME


class Watch(unittest.TestCase):
    def test_restart_predicate(self):
        code = ("/site/builder/", "/site/theme/types/")
        self.assertTrue(watch.restarts({"/site/builder/src/page.py"}, code))
        self.assertTrue(watch.restarts({"/site/theme/types/talk.py"}, code))
        self.assertFalse(watch.restarts({"/site/theme/style.css", "/site/content/index.md"}, code))
        self.assertFalse(watch.restarts({"/site/theme/typesetting.css"}, code))
        self.assertEqual(watch.CODE, (str(BUILDER) + os.sep, str(THEME / "types") + os.sep))

    def test_version_flag(self):
        entry = str(BUILDER / "build.py")
        env = {**os.environ, "TILDER_VERSION": "v1.2.3"}
        self.assertEqual(subprocess.run([sys.executable, entry, "--version"], capture_output=True,
                                        text=True, env=env).stdout.strip(), "v1.2.3")
        env.pop("TILDER_VERSION")
        self.assertEqual(subprocess.run([sys.executable, entry, "--version"], capture_output=True,
                                        text=True, env=env).stdout.strip(), "dev")
