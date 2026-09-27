"""jsonc, kyaml and markdown: their tokens in the HTML (the exact spans)
and in the text mirror (the same kinds), their aliases."""

import unittest

import highlight


def span(cls, text):
    return f'<span class="hl-{cls}">{text}</span>'


def kinds(code, lang):
    """The coloured tokens of the text mirror, stripped as it shows them."""
    return [(k, t.strip()) for k, t in highlight.kinds(code, lang) if k and t.strip()]


class Aliases(unittest.TestCase):
    def test_the_new_names_and_their_aliases(self):
        for name, lang in [("jsonc", "jsonc"), ("json-with-comments", "jsonc"),
                           ("JSONC", "jsonc"), ("kyaml", "kyaml"), ("kyml", "kyaml"),
                           ("markdown", "markdown"), ("md", "markdown"),
                           ("mdown", "markdown"), ("Markdown", "markdown")]:
            self.assertEqual(highlight.canonical(name), lang, name)

    def test_unknown_languages_stay_unknown(self):
        for name in ("json5", "cobol", "mkd", ""):
            self.assertIsNone(highlight.canonical(name), name)
            self.assertIsNone(highlight.highlight("x", name), name)
            self.assertIsNone(highlight.kinds("x", name), name)

    def test_html_and_text_cover_the_code_exactly(self):
        for lang, code in [("jsonc", JSONC), ("kyaml", KYAML), ("markdown", MARKDOWN)]:
            self.assertEqual("".join(t for _, t in highlight.kinds(code, lang)), code, lang)
            self.assertEqual("".join(t for _, t in highlight._tokens(code, lang, lambda c: [(None, c)])),
                             code, lang)


JSONC = '''{
  // a comment
  "url": "http://example.org/*x*/", /* inline */ "n": -1.5,
  "ok": true, "none": null,
}'''


class Jsonc(unittest.TestCase):
    def test_html(self):
        self.assertEqual(highlight.highlight(JSONC, "jsonc"), "\n".join([
            "{",
            "  " + span("c", "// a comment"),
            "  " + span("t", '"url"') + ": " + span("s", '"http://example.org/*x*/"') + ", "
            + span("c", "/* inline */") + " " + span("t", '"n"') + ": " + span("n", "-1.5") + ",",
            "  " + span("t", '"ok"') + ": " + span("b", "true") + ", " + span("t", '"none"') + ": "
            + span("b", "null") + ",",
            "}"]))

    def test_text_kinds(self):
        self.assertEqual(kinds(JSONC, "jsonc"), [
            ("c", "// a comment"), ("t", '"url"'), ("s", '"http://example.org/*x*/"'),
            ("c", "/* inline */"), ("t", '"n"'), ("n", "-1.5"), ("t", '"ok"'), ("b", "true"),
            ("t", '"none"'), ("b", "null")])

    def test_a_comment_across_lines(self):
        self.assertEqual(highlight.highlight("/* a\n b */ 1", "jsonc"),
                         span("c", "/* a\n b */") + " " + span("n", "1"))

    def test_json_itself_is_unchanged(self):
        self.assertEqual(highlight.highlight('{"a": 1} // x', "json"),
                         '{' + span("t", '"a"') + ": " + span("n", "1") + "} // x")


KYAML = '''---
{
  apiVersion: "v1",  # the API
  "quoted-key": "x: y",
  spec: {replicas: 3, ports: [80, 443], paused: false, x: null},
}'''


class Kyaml(unittest.TestCase):
    def test_html(self):
        self.assertEqual(highlight.highlight(KYAML, "kyaml"), "\n".join([
            span("t", "---"),
            "{",
            "  " + span("t", "apiVersion") + ": " + span("s", '"v1"') + ",  " + span("c", "# the API"),
            "  " + span("t", '"quoted-key"') + ": " + span("s", '"x: y"') + ",",
            "  " + span("t", "spec") + ": {" + span("t", "replicas") + ": " + span("n", "3") + ", "
            + span("t", "ports") + ": [" + span("n", "80") + ", " + span("n", "443") + "], "
            + span("t", "paused") + ": " + span("b", "false") + ", " + span("t", "x") + ": "
            + span("b", "null") + "},",
            "}"]))

    def test_text_kinds(self):
        self.assertEqual(kinds('{a: "b", "c": 1, d: true}  # e', "kyml"), [
            ("t", "a"), ("s", '"b"'), ("t", '"c"'), ("n", "1"), ("t", "d"), ("b", "true"),
            ("c", "# e")])

    def test_a_hash_in_a_string_is_not_a_comment(self):
        self.assertEqual(kinds('{a: "#x"}', "kyaml"), [("t", "a"), ("s", '"#x"')])


MARKDOWN = '''---
title: Hello, world
description: snake_case_value
---

## Title {grid} {#id}

Some snake_case_names, **bold**, *em* and _em_, `inline code`, 2 * 3 * 4.
A [link](https://example.org/a_b_c) and https://example.org/d_e_f bare.

- [x] done
- [ ] todo
  1. nested

> [!WARNING]
> Careful with `public/`.

| a | b |
|:--|--:|
| `1` | 2 |

```python
x = "not highlighted"  # plain
```

<!-- TO FILL:
several lines -->
[TOC]

***

Classes at the end. {small muted}
![alt](logo_big.svg "caption")'''


class Markdown(unittest.TestCase):
    def test_text_kinds(self):
        self.assertEqual(kinds(MARKDOWN, "markdown"), [
            ("p", "---"), ("t", "title"), ("t", "description"), ("p", "---"),
            ("t", "## Title"), ("v", "{grid}"), ("v", "{#id}"),
            ("b", "**bold**"), ("b", "*em*"), ("b", "_em_"), ("s", "`inline code`"),
            ("v", "https://example.org/a_b_c"),
            ("b", "-"), ("b", "[x]"), ("b", "-"), ("b", "[ ]"), ("b", "1."),
            ("p", ">"), ("k", "[!WARNING]"), ("p", ">"), ("s", "`public/`"),
            ("p", "|"), ("p", "|"), ("p", "|"), ("p", "|:--|--:|"),
            ("p", "|"), ("s", "`1`"), ("p", "|"), ("p", "|"),
            ("c", "```python"), ("c", "```"),
            ("c", "<!-- TO FILL:"), ("c", "several lines -->"), ("k", "[TOC]"), ("p", "***"),
            ("v", "{small muted}"), ("v", "logo_big.svg"), ("s", '"caption"')])

    def test_html(self):
        html = highlight.highlight(MARKDOWN, "markdown")
        for part in [
                span("p", "---") + "\n" + span("t", "title") + ": Hello, world\n",
                span("t", "## Title") + " " + span("v", "{grid}") + " " + span("v", "{#id}") + "\n",
                "Some snake_case_names, " + span("b", "**bold**") + ", " + span("b", "*em*")
                + " and " + span("b", "_em_") + ", " + span("s", "`inline code`") + ", 2 * 3 * 4.\n",
                "A [link](" + span("v", "https://example.org/a_b_c")
                + ") and https://example.org/d_e_f bare.\n",
                span("b", "-") + " " + span("b", "[x]") + " done\n",
                "  " + span("b", "1.") + " nested\n",
                span("p", "&gt;") + " " + span("k", "[!WARNING]") + "\n",
                span("p", "|") + " a " + span("p", "|") + " b " + span("p", "|") + "\n"
                + span("p", "|:--|--:|") + "\n",
                span("c", "```python") + '\nx = "not highlighted"  # plain\n' + span("c", "```") + "\n",
                span("c", "&lt;!-- TO FILL:") + "\n" + span("c", "several lines --&gt;") + "\n"
                + span("k", "[TOC]") + "\n",
                "Classes at the end. " + span("v", "{small muted}") + "\n",
                "![alt](" + span("v", "logo_big.svg") + " " + span("s", '"caption"') + ")"]:
            self.assertIn(part, html)

    def test_no_false_positives(self):
        for code in ["snake_case_names and _private_thing and a_b_",
                     "see https://example.org/a_b_c_d and file_name_here.md",
                     "2 * 3 * 4 and a* b", "#hashtag, ####### seven", "Note: a colon",
                     "a | b in prose", "C++ and x--y", "[not a link] (x)"]:
            self.assertEqual(kinds(code, "markdown"), [], code)
        self.assertEqual(kinds("- not a key: here", "md"), [("b", "-")])

    def test_front_matter_only_at_the_top(self):
        self.assertEqual(kinds("text\n\n---\nkey: value\n---", "md"),
                         [("p", "---"), ("p", "---")])
        self.assertEqual(kinds("---\nno: closing", "md"), [("p", "---")])

    def test_a_fence_closes_only_on_as_many_backticks(self):
        code = "````markdown\n```sh\nls\n```\n````\n**b**"
        self.assertEqual(kinds(code, "md"),
                         [("c", "````markdown"), ("c", "````"), ("b", "**b**")])

    def test_an_unclosed_fence_leaves_the_rest_plain(self):
        self.assertEqual(kinds("```\n**not bold**", "md"), [("c", "```")])

    def test_headings(self):
        self.assertEqual(kinds("# One\n###### Six {next}\n### Spring meetup {next}", "md"),
                         [("t", "# One"), ("t", "###### Six"), ("v", "{next}"),
                          ("t", "### Spring meetup"), ("v", "{next}")])

    def test_an_indented_entry_body(self):
        code = "### Talk\n\n  - 2026-05-16 | Saturday\n  - `upcoming`\n\n  [site ↗](https://x.org/) {small}"
        self.assertEqual(kinds(code, "md"), [
            ("t", "### Talk"), ("b", "-"), ("b", "-"), ("s", "`upcoming`"),
            ("v", "https://x.org/"), ("v", "{small}")])


if __name__ == "__main__":
    unittest.main()
