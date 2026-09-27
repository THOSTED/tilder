"""Code blocks in the coloured mirror: each token in its kind's colour, by
the rules highlight.py has for the HTML (and, for the shell, the command
words and options). The text is the text of txt/, byte for byte: colour
only, never a character added, so the code still copies clean."""

import re
import unittest

from tests import helpers
import ansify
import highlight
import text
from ansify import RESET

ESC = re.compile(r"\x1b\[[0-9;]*m")
IND = "     "

# One block per language, and the tokens it must colour: (kind, text).
SAMPLES = {
    "sh": ('FOO="bar" curl -fsSL $URL 42 | grep \'x\' # done\n'
           "if true; then sudo apt-get install -y jq; fi\n"
           "for f in *.md; do echo \"$f\"; done 2>&1 | less",
           [("s", '"bar"'), ("x", "curl"), ("o", "-fsSL"), ("v", "$URL"), ("n", "42"),
            ("x", "grep"), ("s", "'x'"), ("c", "# done"), ("k", "if"), ("x", "true"),
            ("k", "then"), ("x", "sudo"), ("x", "apt-get"), ("o", "-y"), ("k", "fi"),
            ("k", "for"), ("k", "in"), ("k", "do"), ("x", "echo"), ("s", '"$f"'),
            ("k", "done"), ("x", "less")]),
    "console": ("$ curl -s example.org\nsome output\n# systemctl restart caddy",
                [("p", "$ "), ("x", "curl"), ("o", "-s"), ("p", "# "), ("x", "systemctl")]),
    "python": ('@dataclass\ndef f(x=1):\n    return len("s")  # c',
               [("t", "@dataclass"), ("k", "def"), ("n", "1"), ("k", "return"),
                ("b", "len"), ("s", '"s"'), ("c", "# c")]),
    "js": ('const x = "s"; // c\nreturn null + 1;',
           [("k", "const"), ("s", '"s"'), ("c", "// c"), ("k", "return"), ("b", "null"),
            ("n", "1")]),
    "c": ('#include <stdio.h>\nint main(void) { printf("hi"); return 0; } /* c */',
          [("t", "#include"), ("b", "int"), ("b", "void"), ("s", '"hi"'), ("k", "return"),
           ("n", "0"), ("c", "/* c */")]),
    "go": ('func main() { var s string = "x"; return 1 } // c',
           [("k", "func"), ("k", "var"), ("b", "string"), ("s", '"x"'), ("k", "return"),
            ("n", "1"), ("c", "// c")]),
    "rust": ('#[derive(Debug)]\nfn main() { let s: String = "x"; println!("{}", 1); } // c',
             [("t", "#[derive(Debug)]"), ("k", "fn"), ("k", "let"), ("b", "String"),
              ("s", '"x"'), ("t", "println!"), ("n", "1"), ("c", "// c")]),
    "sql": ("SELECT count(*) FROM t WHERE a = 'x' AND b = 1; -- c",
            [("k", "SELECT"), ("b", "count"), ("k", "FROM"), ("k", "WHERE"), ("s", "'x'"),
             ("k", "AND"), ("n", "1"), ("c", "-- c")]),
    "json": ('{"a": "x", "b": 1, "c": true}',
             [("t", '"a"'), ("s", '"x"'), ("n", "1"), ("b", "true")]),
    "yaml": ('key: "x"  # c\nn: 1\nok: true\na: &anchor x',
             [("t", "key"), ("s", '"x"'), ("c", "# c"), ("n", "1"), ("b", "true"),
              ("v", "&anchor")]),
    "toml": ('[section]\n# c\nkey = "x"\nn = 1\nb = true',
             [("t", "[section]"), ("t", "key"), ("s", '"x"'), ("c", "# c"), ("n", "1"),
              ("b", "true")]),
    "caddy": ('example.org {\n  reverse_proxy {$UPSTREAM} 8080  # c\n  header "x"\n}',
              [("t", "example"), ("v", "{$UPSTREAM}"), ("n", "8080"), ("c", "# c"),
               ("t", "  header"), ("s", '"x"')]),
    "dockerfile": ('FROM python:3.12 AS base\n# c\nRUN echo "x" $HOME',
                   [("k", "FROM"), ("n", "3.12"), ("k", "AS"), ("c", "# c"), ("k", "RUN"),
                    ("s", '"x"'), ("v", "$HOME")]),
    "html": ('<!DOCTYPE html>\n<!-- c -->\n<a href="x">&amp;</a>',
             [("b", "<!DOCTYPE html>"), ("c", "<!-- c -->"), ("t", "<a"), ("v", "href"),
              ("s", '"x"'), ("t", ">"), ("b", "&amp;")]),
    "css": ('/* c */\n@media screen {\n  a { color: #fff; --x: 1px; content: "s"; margin: auto; }\n}',
            [("c", "/* c */"), ("t", "@media"), ("k", "color"), ("b", "#fff"), ("v", "--x"),
             ("n", "1px"), ("s", '"s"'), ("b", "auto")]),
    "make": ('# c\nall: build\n\tgo build $(OUT) "x"\nifdef X\nendif',
             [("c", "# c"), ("t", "all"), ("v", "$(OUT)"), ("s", '"x"'), ("k", "ifdef")]),
    "diff": ("--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n same",
             [("k", "--- a"), ("k", "+++ b"), ("gh", "@@ -1 +1 @@"), ("gd", "-old"),
              ("gi", "+new")]),
}


def render(lang, code):
    """(the block's lines in ansi/, the same in txt/), as a page shows them."""
    marked = text.txt_code({"k": "code", "lang": lang, "lines": code.split("\n")}, IND)
    page = "\n".join(["HEAD", "", "BODY"] + marked + ["", "FOOT"])
    lines = ansify.ansify(page).split("\n")[3:-2]
    return lines, [text.plain(l) for l in marked]


class Highlighted(unittest.TestCase):
    def setUp(self):
        self.accent = ansify.ACCENT
        ansify.ACCENT = ansify.sgr("cyan")

    def tearDown(self):
        ansify.ACCENT = self.accent

    def test_text_and_ansify_share_their_marks(self):
        self.assertEqual((text.HL_BLOCK, text.HL_OFF, text.HL),
                         (ansify.HL_BLOCK, ansify.HL_OFF, ansify.HL))
        marks = [text.HL_BLOCK, text.HL_OFF, *text.HL.values()]
        self.assertEqual(len(set(marks)), len(marks))
        for mark in marks:
            self.assertFalse(mark.isspace() or mark == "\x1b" or "\x02" <= mark <= "\x07", repr(mark))
            self.assertEqual(text.plain("a" + mark + "b"), "ab")

    def test_every_language_of_highlight_has_a_sample(self):
        langs = {highlight.canonical(l) for l in SAMPLES}
        self.assertEqual(langs, set(highlight.LANGS) | {"console", "diff"})

    def test_each_token_has_its_kind(self):
        for lang, (code, expected) in SAMPLES.items():
            toks = [(k, t) for k, t in highlight.kinds(code, lang) if k]
            for tok in expected:
                self.assertIn(tok, toks, lang)

    def test_each_token_has_its_kinds_colour(self):
        colours = ansify.token_colours()
        for lang, (code, expected) in SAMPLES.items():
            shown = "\n".join(render(lang, code)[0])
            for kind, tok in expected:
                self.assertIn(colours[kind] + tok.strip() + RESET, shown, (lang, kind, tok))

    def test_the_colours(self):
        c = ansify.token_colours()
        self.assertEqual((c["k"], c["x"], c["b"], c["o"]),
                         ("\033[1m\033[36m", "\033[1m\033[36m", "\033[36m", "\033[36m"))
        self.assertEqual((c["s"], c["c"], c["n"], c["gi"], c["gd"], c["t"]),
                         ("\033[32m", "\033[2m", "\033[35m", "\033[32m", "\033[31m", "\033[1m"))

    def test_the_accent_follows_the_site(self):
        ansify.ACCENT = ansify.sgr(208)
        shown = "\n".join(render("python", "def f(): pass")[0])
        self.assertIn("\033[1m\033[38;5;208mdef" + RESET, shown)

    def test_stripped_it_is_the_text_and_the_code_copies_clean(self):
        for lang, (code, _) in SAMPLES.items():
            shown, plain = render(lang, code)
            self.assertEqual([ESC.sub("", l) for l in shown], plain, lang)
            self.assertEqual(plain[1:-1], [(IND + "  " + l.expandtabs(4)).rstrip()
                                           if l.strip() else plain[1 + n]
                                           for n, l in enumerate(code.split("\n"))], lang)

    def test_the_frame_keeps_its_style(self):
        shown, plain = render("python", "x = 1")
        self.assertEqual(shown[0], IND + ansify.DIM + plain[0].lstrip() + RESET)
        self.assertEqual(shown[-1], IND + ansify.DIM + plain[-1].lstrip() + RESET)

    def test_no_background_and_nothing_but_colour(self):
        for lang, (code, _) in SAMPLES.items():
            for seq in re.findall(r"\x1b\[([0-9;]*)m", "\n".join(render(lang, code)[0])):
                self.assertRegex(seq, r"^(0|1|2|3[0-7]|38;5;\d+)$", lang)

    def test_a_long_line_is_cut_and_its_colour_carries_on(self):
        code = 'x = "' + "a" * 100 + '"  # the end'
        shown, plain = render("python", code)
        self.assertTrue(all(len(l) <= 75 for l in plain))
        self.assertEqual([ESC.sub("", l) for l in shown], plain)
        green = ansify.token_colours()["s"]
        first, second = shown[1], shown[2]
        self.assertTrue(first.endswith(RESET + "\\"), first)   # closed before the cut
        self.assertTrue(second.startswith(IND + "    " + green), second)  # reopened after it
        self.assertIn(ansify.DIM + "# the end" + RESET, second)
        self.assertEqual("".join(p[len(IND) + 2:] for p in plain[1:3]),
                         code[:67] + "\\  " + code[67:])

    def test_trailing_spaces_are_not_coloured(self):
        marked = text.txt_code({"k": "code", "lang": "python", "lines": ["x = 1  # c   "]}, IND)
        self.assertEqual(text.plain(marked[1].rstrip()), text.plain(marked[1]).rstrip())

    def test_plain_text_and_unknown_languages_keep_the_command_rule(self):
        for lang in ("text", "", "cobol"):
            shown, _ = render(lang, "curl example.org")
            self.assertEqual(shown[1], IND + "  " + ansify.ACCENT + "curl example.org" + RESET, lang)

    def test_the_fixture_console_block(self):
        out = helpers.build_site()
        self.assertIn("\033[2m$" + RESET + " \033[1m\033[36mecho" + RESET + " hello",
                      out["ansi/blog/2026-01-01-hello.txt"])
        self.assertIn("  $ echo hello\n", out["txt/blog/2026-01-01-hello.txt"])


class ShellCommands(unittest.TestCase):
    def commands(self, code):
        return [t for k, t in highlight.kinds(code, "sh") if k == "x"]

    def test_after_operators_and_prefixes(self):
        self.assertEqual(self.commands("a | b && c; d || e & f $(g) `h` (i)"),
                         list("abcdefghi"))
        self.assertEqual(self.commands("sudo env nohup make"), ["sudo", "env", "nohup", "make"])

    def test_arguments_redirections_and_assignments(self):
        self.assertEqual(self.commands("A=1 B=\"x\" run arg 2>&1 >/dev/null | tee log"),
                         ["run", "tee"])

    def test_a_continued_line_continues_the_command(self):
        self.assertEqual(self.commands("curl \\\n  -o x url\nls"), ["curl", "ls"])

    def test_a_closing_parenthesis_is_never_coloured(self):
        for code in ("(curl example.org/x)", "echo $(curl example.org/x)."):
            toks = highlight.kinds(code, "sh")
            self.assertIn((None, ")"), toks, code)
            shown = "\n".join(render("sh", code)[0])
            self.assertNotRegex(shown, r"\)\x1b\[0m", code)


if __name__ == "__main__":
    unittest.main()
