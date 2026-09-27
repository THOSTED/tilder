"""The coloured mirror colours a URL or a command line, never the
punctuation that closes the sentence around it: `(see https://x.org/a)`
colours the URL, not the `)`."""

import re
import unittest

from tests import helpers
import ansify
from ansify import ACCENT, CODE_BLOCK, RESET, UNDER


def line(body):
    """One body line of a page, coloured: the first and last lines of a
    page are its header and footer rules."""
    return ansify.ansify(f"HEAD\n\nBODY\n{body}\n\nFOOT").split("\n")[3]


def url(u):
    return ACCENT + UNDER + u + RESET


class Url(unittest.TestCase):
    def test_a_closing_parenthesis(self):
        self.assertEqual(line("  see (https://example.org/x)"),
                         "  see (" + url("https://example.org/x") + ")")

    def test_a_parenthesis_and_a_comma(self):
        self.assertEqual(line("  (https://example.org/x), then"),
                         "  (" + url("https://example.org/x") + "), then")

    def test_a_full_stop(self):
        self.assertEqual(line("  at https://example.org/x."),
                         "  at " + url("https://example.org/x") + ".")

    def test_quotes(self):
        self.assertEqual(line('  "https://example.org/x"'),
                         '  "' + url("https://example.org/x") + '"')
        self.assertEqual(line("  'https://example.org/x'"),
                         "  '" + url("https://example.org/x") + "'")

    def test_a_bracket(self):
        self.assertEqual(line("  [https://example.org/x]"),
                         "  [" + url("https://example.org/x") + "]")

    def test_parentheses_of_the_url_itself_are_kept(self):
        self.assertEqual(line("  (https://example.org/wiki/A_(b))"),
                         "  (" + url("https://example.org/wiki/A_(b)") + ")")

    def test_a_link_of_the_fixture(self):
        # A link is written `text (url)` in the mirror.
        out = helpers.build_site()
        self.assertIn("(" + url("https://example.org/meetup") + ")", out["ansi/events/2099-01-01-future-meetup.txt"])
        for path, text in out.items():
            if path.startswith("ansi/"):
                self.assertIsNone(re.search(r"\x1b\[4m[^\x1b]*[).,;:!?\"'\]]\x1b\[0m", text), path)


class Command(unittest.TestCase):
    def setUp(self):
        self.commands = ansify.COMMANDS
        ansify.COMMANDS = ["curl"]

    def tearDown(self):
        ansify.COMMANDS = self.commands

    def test_a_command_line_stops_before_a_closing_parenthesis(self):
        self.assertEqual(line(CODE_BLOCK + "  curl example.org/x)"),
                         "  " + ACCENT + "curl example.org/x" + RESET + ")")

    def test_a_command_line_keeps_its_own_parentheses(self):
        self.assertEqual(line(CODE_BLOCK + "  curl $(cat url)."),
                         "  " + ACCENT + "curl $(cat url)" + RESET + ".")

    def test_a_command_line_keeps_its_quotes(self):
        self.assertEqual(line(CODE_BLOCK + "  $ curl 'example.org/x'"),
                         "  $ " + ACCENT + "curl 'example.org/x'" + RESET)

    def test_a_command_in_parentheses_in_prose_is_not_coloured(self):
        self.assertEqual(line("  run (curl example.org/x) twice"), "  run (curl example.org/x) twice")


if __name__ == "__main__":
    unittest.main()
