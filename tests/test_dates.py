import unittest

from tests import helpers  # noqa: F401 - triggers tests.__init__ setup
from config import CFG, load_config
from dates import human_date


class Dates(unittest.TestCase):
    def test_words_from_config(self):
        load_config()
        self.assertEqual(human_date("2026-06-15"), "Monday 15 June 2026")

    def test_first_of_month_word(self):
        load_config()
        CFG["dates"]["first"] = "1st"
        try:
            self.assertEqual(human_date("2026-06-01"), "Monday 1st June 2026")
        finally:
            load_config()
