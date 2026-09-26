import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import served


class Served(unittest.TestCase):
    def test_site_files_are_served(self):
        for rel in ("style.css", "members.js", "code.js", "fonts/JetBrainsMono-Regular.woff2",
                    "fonts/OFL.txt", ".well-known/security.txt", "logo.svg", "docs/notes.md"):
            self.assertTrue(served(rel), rel)

    def test_build_inputs_are_not_served(self):
        for rel in ("layout.html", "layouts/event.html", "share.svg", "icons/github.svg",
                    "types/talk.py", "theme.toml", "theme.fr.toml", "site.toml", "site.fr.toml"):
            self.assertFalse(served(rel), rel)

    def test_repository_files_are_not_served(self):
        # A theme in its own repository, used as a submodule: its .git
        # pointer, its git dot-files and its own README and LICENCE.
        for rel in (".git", ".gitignore", ".gitmodules", ".gitattributes", "fonts/.gitkeep",
                    "README.md", "LICENSE", "LICENSE.txt"):
            self.assertFalse(served(rel), rel)
        self.assertTrue(served("docs/README.md"))   # only the root's README is the repository's
