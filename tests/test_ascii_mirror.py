"""txt/ is ASCII only (AGENTS.md §4): whatever the source holds, to_ascii
folds it or drops it."""

import unittest

from tests.helpers import build_site
from fold import to_ascii


class Fold(unittest.TestCase):
    def test_arrows_and_signs(self):
        self.assertEqual(to_ascii("↑ back to top"), "^ back to top")
        self.assertEqual(to_ascii("← previous ↓ →"), "<- previous v ->")
        self.assertEqual(to_ascii("≥ 1, ≤ 2, ≠ 3"), ">= 1, <= 2, != 3")
        self.assertEqual(to_ascii("Straße"), "Strasse")

    def test_anything_else_is_dropped(self):
        self.assertEqual(to_ascii("ok ✓ done"), "ok done")
        self.assertEqual(to_ascii("a ✓  b", squeeze=False), "a   b")
        self.assertTrue(to_ascii("日本語 🙂 ☃ Ω").isascii())


class Mirror(unittest.TestCase):
    def test_every_txt_file_is_ascii(self):
        out = build_site()
        txt = [p for p in out if p.startswith("txt/")]
        self.assertTrue(txt)
        for path in txt:
            self.assertTrue(out[path].isascii(), path)

    def test_a_table_cell_folds_its_arrow(self):
        page = build_site()["txt/guides/tuning.txt"]
        self.assertIn('"^ back to top"', page)
        self.assertIn('"<- previous", >= 1, Strasse', page)


if __name__ == "__main__":
    unittest.main()
