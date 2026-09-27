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


SH_KEYWORDS = ("if then else elif fi for while until do done case esac in function "
               "return break continue local export readonly declare set unset shift "
               "trap exit select time")
SH_COMMENT = r"(?<![\w$])#[^\n]*"
SH_VAR = r"\$\{[^}\n]*\}|\$[A-Za-z_][A-Za-z0-9_]*|\$[0-9#?@*$!-]"
SH = spec(
    [("c", SH_COMMENT), ("s", DQ), ("s", SQ), ("v", SH_VAR), ("n", NUM)],
    SH_KEYWORDS,
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


def lex(code, sp):
    """[(class or None, text)], covering the code exactly, in order."""
    rx = _compile(sp)
    out, pos = [], 0
    for m in rx.finditer(code):
        if m.start() > pos:
            out.append((None, code[pos:m.start()]))
        text = m.group(0)
        if m.lastgroup == "w":
            low = text.lower() if sp is SQL else text
            cls = "k" if low in sp["k"] else "b" if low in sp["b"] else None
        else:
            cls = sp["rules"][int(m.lastgroup[1:])][0]
        out.append((cls, text))
        pos = m.end()
    out.append((None, code[pos:]))
    return out


def _lines(code, line):
    """line(text) -> tokens, for each line, the newlines between them."""
    out = []
    for n, text in enumerate(code.split("\n")):
        if n:
            out.append((None, "\n"))
        out.extend(line(text))
    return out


def _diff_line(line):
    if line.startswith(("+++", "---", "diff ", "index ")):
        return [("k", line)]
    if line.startswith("@@"):
        return [("gh", line)]
    if line.startswith("+"):
        return [("gi", line)]
    if line.startswith("-"):
        return [("gd", line)]
    return [(None, line)]


def _console_line(shell):
    """`$ cmd` and `# cmd` lines are shell; everything else is output."""
    def line(text):
        m = re.match(r"^([\w@.:~/-]*[$#] )(.*)$", text)
        return [("p", m.group(1))] + shell(m.group(2)) if m else [(None, text)]
    return line


def _tokens(code, lang, shell):
    lang = canonical(lang)
    if lang is None:
        return None
    if lang == "text":
        return [(None, code)]
    if lang == "diff":
        return _lines(code, _diff_line)
    if lang == "console":
        return _lines(code, _console_line(shell))
    if lang == "sh":
        return shell(code)
    return lex(code, LANGS[lang])


def highlight(code, lang):
    toks = _tokens(code, lang, lambda c: lex(c, SH))
    if toks is None:
        return None
    return "".join(span(c, t) if c else html.escape(t, quote=False) for c, t in toks)


# --- the text mirror -----------------------------------------------------
#
# The coloured text mirror (ansify.py) has the same tokens, and for shell
# two more that HTML has no class for: the command word (x) and an option
# (o). A command word is the first word of a command: at a line's start,
# after | || && ; & ( $( or a backquote, after a prefix such as sudo, and
# after a variable assignment.

KINDS = ("k", "b", "s", "c", "n", "v", "p", "t", "gi", "gd", "gh", "x", "o")

SH_TEXT = spec(
    [("c", SH_COMMENT), ("s", DQ), ("s", SQ), ("v", SH_VAR),
     ("r", r"&>>?|\d*(?:>>?|<<?|<>)(?:&\d*-?)?"),      # a redirection: 2>&1
     ("op", r"\|\||&&|\|&?|;;?|&|\$\(|[()`]"),         # what starts a command
     ("o", r"(?<![^\s|;&(`])--?[A-Za-z0-9][\w-]*"),
     ("word", r"[\w./~+@%:,=^-]+")],
    SH_KEYWORDS)
# The keywords after which the next word is a name, not a command.
NAMING = {"for", "select", "case", "function"}
# The commands whose next word is a command too (a keyword's always is).
PREFIXES = {"sudo", "doas", "env", "nohup", "exec", "command", "builtin", "nice",
            "xargs", "watch"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
NUMBER = re.compile(NUM)


def shell(code):
    """Shell tokens for the text mirror: SH's, plus the command words (x)
    and the options (o)."""
    out = []
    cmd = True       # the next word is a command
    naming = False   # the next word is a name (for NAME in ...)
    named = False    # the last word was that name: `in` is a keyword
    glued = False    # a value glued to an assignment: FOO="bar"
    for cls, text in lex(code, SH_TEXT):
        if cls is None:  # spaces and the rest: a newline starts a command,
            nl = text.rfind("\n")  # unless the line ended with a backslash
            if nl >= 0 and not text[:nl].endswith("\\"):
                cmd, naming, named = True, False, False
            glued = glued and not text
            out.append((None, text))
            continue
        assign = False
        if cls in ("op", "r"):
            if cls == "op":
                cmd = text != ")"
            cls = None
        elif cls in ("s", "v"):
            cmd = cmd and glued
            assign = glued
        elif cls == "word":
            if naming:
                cls, naming, named = None, False, True
                out.append((cls, text))
                continue
            if cmd and ASSIGN.match(text):
                cls, assign = None, True
            elif cmd:
                cls = "k" if text in SH_TEXT["k"] else "x"
                naming = text in NAMING
                cmd = text in PREFIXES or (cls == "k" and not naming)
            elif text == "in" and named:
                cls = "k"
            else:
                cls = "n" if NUMBER.fullmatch(text) else None
        named, glued = False, assign
        out.append((cls, text))
    return [(c, t) for c, t in out if t]


def kinds(code, lang):
    """The tokens of the text mirror: [(kind or None, text)] covering the
    code exactly, kind in KINDS; None when the language is unknown."""
    return _tokens(code, lang, shell)
