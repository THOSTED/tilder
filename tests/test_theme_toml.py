import unittest

from tests.helpers import build_site


class ThemeToml(unittest.TestCase):
    def test_theme_values_reach_the_page_and_the_site_wins(self):
        out = build_site()
        self.assertIn('<meta name="theme-color" content="#123456">', out["index.html"])
        self.assertIn('"theme_color": "#123456"', out["site.webmanifest"])
        self.assertIn('"background_color": "#ABCDEF"', out["site.webmanifest"])   # site.toml over theme.toml
        self.assertNotIn("theme.toml", out)                                         # never served
