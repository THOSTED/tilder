"""Syntax highlighting at build time: code -> HTML with <span> classes.

No dependency and no JavaScript. Each language is a short list of token
rules tried in order at every position; the first match wins, anything
unmatched is plain text. It is deliberately approximate - enough to make
shared code readable, not a parser.

Token classes, prefixed `hl-` in the HTML (`hl-k`, `hl-s`...) because the
bare `.s` and `.b` are the site's section classes. Styled in
assets/style.css, within the site's palette:

    k   keyword                 bold
    b   builtin, type, literal  muted
    s   string                  accent
    c   comment                 faint
    n   number                  muted
    v   variable                accent
    p   prompt ($ or #)         faint
    t   tag, section, key       bold
    gi  diff: inserted line     accent
    gd  diff: deleted line      warn
    gh  diff: hunk header       faint

    highlight(code, lang) -> str | None   None when the language is unknown
"""

import html
import re

# --- building blocks -----------------------------------------------------

def words(s):
    return set(s.split())


DQ = r'"(?:\\.|[^"\\\n])*"'
SQ = r"'(?:\\.|[^'\\\n])*'"
BT = r"`(?:\\.|[^`\\])*`"
NUM = r"\b(?:0x[0-9a-fA-F_]+|0b[01_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b"
HASH = r"#[^\n]*"
SLASH = r"//[^\n]*"
BLOCK = r"/\*[\s\S]*?\*/"
DASH = r"--[^\n]*"
WORD = r"[A-Za-z_][A-Za-z0-9_]*"


def spec(rules, keywords="", builtins=""):
    """rules: [(class, regex)], tried in order. WORD is appended last and
    classified against the keyword and builtin sets."""
    return {"rules": rules, "k": words(keywords), "b": words(builtins)}


SH = spec(
    [("c", r"(?<![\w$])#[^\n]*"), ("s", DQ), ("s", SQ),
     ("v", r"\$\{[^}\n]*\}|\$[A-Za-z_][A-Za-z0-9_]*|\$[0-9#?@*$!-]"),
     ("n", NUM)],
    "if then else elif fi for while until do done case esac in function "
    "return break continue local export readonly declare set unset shift "
    "trap exit select time",
    "echo printf cd pwd test read source eval exec true false sudo grep "
    "sed awk cat ls cp mv rm mkdir chmod chown find xargs curl wget git "
    "docker systemctl journalctl ssh scp tar")

PY = spec(
    [("c", HASH),
     ("s", r'[rbfuRBFU]{0,2}(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'),
     ("s", r"[rbfuRBFU]{0,2}" + DQ), ("s", r"[rbfuRBFU]{0,2}" + SQ),
     ("t", r"@[A-Za-z_][\w.]*"), ("n", NUM)],
    "and as assert async await break class continue def del elif else "
    "except finally for from global if import in is lambda nonlocal not or "
    "pass raise return try while with yield match case",
    "True False None self cls print len range str int float bool list dict "
    "set tuple open isinstance super object Exception")

JS = spec(
    [("c", BLOCK), ("c", SLASH), ("s", DQ), ("s", SQ), ("s", BT), ("n", NUM)],
    "break case catch class const continue debugger default delete do else "
    "export extends finally for function if import in instanceof let new of "
    "return super switch this throw try typeof var void while with yield "
    "async await from as type interface enum implements",
    "true false null undefined NaN Infinity console window document JSON "
    "Math Object Array String Number Boolean Promise Error string number "
    "boolean any unknown never void")

C = spec(
    [("c", BLOCK), ("c", SLASH), ("t", r"^[ \t]*#[ \t]*\w+"), ("s", DQ), ("s", SQ),
     ("n", NUM)],
    "auto break case const continue default do else enum extern for goto if "
    "inline register restrict return sizeof static struct switch typedef "
    "union volatile while",
    "char double float int long short signed unsigned void bool size_t "
    "ssize_t uint8_t uint16_t uint32_t uint64_t int8_t int16_t int32_t "
    "int64_t NULL true false")

GO = spec(
    [("c", BLOCK), ("c", SLASH), ("s", DQ), ("s", BT), ("s", SQ), ("n", NUM)],
    "break case chan const continue default defer else fallthrough for func "
    "go goto if import interface map package range return select struct "
    "switch type var",
    "bool byte complex64 complex128 error float32 float64 int int8 int16 "
    "int32 int64 rune string uint uint8 uint16 uint32 uint64 uintptr true "
    "false nil iota append cap close copy delete len make new panic print "
    "println recover")

RUST = spec(
    [("c", BLOCK), ("c", SLASH), ("s", DQ), ("t", r"#!?\[[^\]\n]*\]"),
     ("b", r"'[a-z_]+\b(?!')"), ("s", SQ), ("t", r"\b[a-z_]+!"), ("n", NUM)],
    "as async await break const continue crate dyn else enum extern fn for "
    "if impl in let loop match mod move mut pub ref return self Self static "
    "struct super trait type unsafe use where while",
    "bool char str String i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 "
    "usize f32 f64 Option Some None Result Ok Err Vec Box true false")

SQL = spec(
    [("c", DASH), ("c", BLOCK), ("s", SQ), ("s", DQ), ("n", NUM)],
    "select from where and or not insert into values update set delete "
    "create table index view drop alter add column primary key foreign "
    "references join left right inner outer on group by order having limit "
    "offset as distinct union all case when then else end is null like in "
    "exists begin commit rollback grant revoke with returning default",
    "int integer bigint smallint text varchar char boolean date timestamp "
    "timestamptz serial uuid json jsonb numeric real true false count sum "
    "avg min max now coalesce")

JSON = spec(
    [("t", r'"(?:\\.|[^"\\\n])*"(?=\s*:)'), ("s", DQ), ("n", r"-?" + NUM)],
    "", "true false null")

YAML = spec(
    [("c", r"(?<!\S)#[^\n]*"), ("t", r"^[ \t]*(?:- )?[\w./-]+(?=:(?:\s|$))"),
     ("s", DQ), ("s", SQ), ("v", r"[&*][\w-]+"), ("t", r"^---$|^\.\.\.$"),
     ("n", NUM)],
    "", "true false yes no on off null")

INI = spec(
    [("c", r"^[ \t]*[#;][^\n]*"), ("t", r"^[ \t]*\[[^\]\n]*\]"),
     ("t", r"^[ \t]*[\w.-]+(?=[ \t]*=)"), ("s", DQ), ("s", SQ), ("n", NUM)],
    "", "true false")

CONF = spec(  # Caddyfile, nginx, and friends
    [("c", r"(?<!\S)#[^\n]*"), ("s", DQ), ("s", BT),
     ("v", r"\{\$?[\w.:-]+\}|\$[\w]+"), ("t", r"@[\w-]+"),
     ("t", r"^[ \t]*[a-z_][\w-]*"), ("n", NUM)],
    "", "on off")

DOCKER = spec(
    [("c", r"^[ \t]*#[^\n]*"),
     ("k", r"^[ \t]*(?i:FROM|RUN|CMD|LABEL|EXPOSE|ENV|ADD|COPY|ENTRYPOINT|"
           r"VOLUME|USER|WORKDIR|ARG|ONBUILD|STOPSIGNAL|HEALTHCHECK|SHELL)\b"),
     ("s", DQ), ("s", SQ), ("v", r"\$\{[^}\n]*\}|\$\w+"), ("n", NUM)],
    "AS as")

MARKUP = spec(
    [("c", r"<!--[\s\S]*?-->"), ("b", r"<!\w[^>]*>"),
     ("t", r"</?[\w:-]+|/?>"), ("s", DQ), ("s", SQ),
     ("b", r"&[\w#]+;"), ("v", r"\b[\w:-]+(?==)")])

CSS = spec(
    [("c", BLOCK), ("s", DQ), ("s", SQ),
     ("t", r"@[\w-]+"), ("v", r"--[\w-]+"),
     ("b", r"#[0-9a-fA-F]{3,8}\b"), ("n", r"-?\d*\.?\d+(?:px|rem|em|ch|%|s|ms|vh|vw|fr)?\b"),
     ("k", r"[\w-]+(?=\s*:[^{};]*;)")],
    "", "none auto inherit initial unset var calc important")

MAKE = spec(
    [("c", HASH), ("t", r"^[\w./%-]+(?=\s*:(?!=))"), ("v", r"\$\([^)\n]*\)|\$\w"),
     ("s", DQ), ("s", SQ)],
    "ifeq ifneq ifdef ifndef else endif include define endef export")

LANGS = {
    "sh": SH, "python": PY, "js": JS, "c": C, "go": GO, "rust": RUST,
    "sql": SQL, "json": JSON, "yaml": YAML, "ini": INI, "conf": CONF,
    "dockerfile": DOCKER, "html": MARKUP, "css": CSS, "make": MAKE,
}

ALIASES = {
    "bash": "sh", "shell": "sh", "zsh": "sh", "py": "python",
    "javascript": "js", "ts": "js", "typescript": "js", "node": "js",
    "h": "c", "cpp": "c", "c++": "c", "golang": "go", "rs": "rust",
    "postgres": "sql", "postgresql": "sql", "yml": "yaml", "toml": "ini",
    "cfg": "ini", "systemd": "ini", "caddy": "conf", "caddyfile": "conf",
    "nginx": "conf", "docker": "dockerfile", "containerfile": "dockerfile",
    "xml": "html", "svg": "html", "makefile": "make",
}

# Handled line by line rather than by token rules.
SPECIAL = {"console", "diff", "text", "plain", "txt"}
SPECIAL_ALIASES = {"shell-session": "console", "terminal": "console",
                   "patch": "diff"}

def canonical(lang):
    """'Bash' -> 'sh', 'yml' -> 'yaml'; None if unknown."""
    lang = lang.strip().lower()
    lang = ALIASES.get(lang, SPECIAL_ALIASES.get(lang, lang))
    if lang in ("plain", "txt"):
        lang = "text"
    return lang if lang in LANGS or lang in SPECIAL else None


def _compile(sp):
    if "re" not in sp:
        parts = [f"(?P<g{i}>{rx})" for i, (_, rx) in enumerate(sp["rules"])]
        parts.append(f"(?P<w>{WORD})")
        sp["re"] = re.compile("|".join(parts), re.M)
    return sp["re"]


def span(cls, text):
    # Prefixed: bare .s and .b are the site's section classes.
    return f'<span class="hl-{cls}">{html.escape(text, quote=False)}</span>'


def tokens(code, sp):
    rx = _compile(sp)
    out, pos = [], 0
    for m in rx.finditer(code):
        if m.start() > pos:
            out.append(html.escape(code[pos:m.start()], quote=False))
        text = m.group(0)
        if m.lastgroup == "w":
            low = text.lower() if sp is SQL else text
            if low in sp["k"]:
                out.append(span("k", text))
            elif low in sp["b"]:
                out.append(span("b", text))
            else:
                out.append(html.escape(text, quote=False))
        else:
            out.append(span(sp["rules"][int(m.lastgroup[1:])][0], text))
        pos = m.end()
    out.append(html.escape(code[pos:], quote=False))
    return "".join(out)


def diff(code):
    out = []
    for line in code.split("\n"):
        if line.startswith(("+++", "---", "diff ", "index ")):
            out.append(span("k", line))
        elif line.startswith("@@"):
            out.append(span("gh", line))
        elif line.startswith("+"):
            out.append(span("gi", line))
        elif line.startswith("-"):
            out.append(span("gd", line))
        else:
            out.append(html.escape(line, quote=False))
    return "\n".join(out)


def console(code):
    """`$ cmd` and `# cmd` lines are shell; everything else is output."""
    out = []
    for line in code.split("\n"):
        m = re.match(r"^([\w@.:~/-]*[$#] )(.*)$", line)
        if m:
            out.append(span("p", m.group(1)) + tokens(m.group(2), SH))
        else:
            out.append(html.escape(line, quote=False))
    return "\n".join(out)


def highlight(code, lang):
    lang = canonical(lang)
    if lang is None:
        return None
    if lang == "text":
        return html.escape(code, quote=False)
    if lang == "diff":
        return diff(code)
    if lang == "console":
        return console(code)
    return tokens(code, LANGS[lang])
