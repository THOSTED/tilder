"""The text mirror: ASCII, 75 columns, the same tree as the page.

render_txt() returns the text with invisible marks: CODE_ON / CODE_OFF
around inline `code`, CODE_BLOCK at the start of a code block's lines
(HL_BLOCK when its language is highlighted), FRAME at the start of its two
rules, LIST_ON / LIST_OFF around a list item's marker, and in a highlighted
code block, HL[kind] ... HL_OFF around each token (highlight.KINDS).
plain() removes them for txt/; ansify.py turns them into colour for ansi/.
Widths are measured without them.
"""

import re

import highlight
import inline
import languages
from config import CFG, INDENT, WIDTH
from fold import to_ascii
from inline import CODE_OFF, CODE_ON

CODE_BLOCK = "\x04"
LIST_ON, LIST_OFF = "\x05", "\x06"  # around a list marker: -, 1., - [x]
FRAME = "\x07"                      # a code block's top or bottom rule
# A highlighted code block: its lines start with HL_BLOCK, and each token
# is between HL[kind] and HL_OFF. The C0 codes Python counts as spaces
# (\x09-\x0d, \x1c-\x1f) and ESC (\x1b) are never marks.
HL_BLOCK, HL_OFF = "\x01", "\x08"
HL = {kind: chr(0x0e + n) for n, kind in enumerate(highlight.KINDS)}  # \x0e-\x1a
_MARKS = re.compile("[\x01-\x08\x0e-\x1a]")


def plain(text):
    """The text without its marks: what txt/ serves."""
    return _MARKS.sub("", text)


def vlen(text):
    """Visible length: marks take no column."""
    return len(plain(text))


def fill(text, width):
    """Greedy word wrap on spaces, measured without the marks. Never breaks
    a word (a URL, a command) nor at a hyphen."""
    lines, cur = [], ""
    for word in text.split():
        if cur and vlen(cur) + 1 + vlen(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    if cur:
        lines.append(cur)
    return lines


def txt(text):
    """Inline markup to marked ASCII."""
    return to_ascii(inline.to_text(text, marks=True))

def rule(left, mid, right):
    gap = WIDTH - len(left) - len(mid) - len(right)
    return left + " " * (gap // 2) + mid + " " * (gap - gap // 2) + right


def wrap(text, ind):
    return [ind + l for l in fill(text, WIDTH - len(ind))] or [""]


def txt_code(b, ind):
    """Framed by two rules that say which end is which - .-- lang ---. above,
    '------' below - the code indented inside, and nothing extra on the
    code's own lines, so it copies clean from a terminal. Verbatim, but a line past the 75th
    column is cut and continued on the next line, the cut marked by a
    backslash - a shell reads it the same."""
    span = WIDTH - len(ind)
    lang = re.sub(r"[^a-z0-9+#-]", "", b.get("lang", "").lower())
    top = f".-- {lang} " if lang else ".-"
    out = [FRAME + ind + top + "-" * (span - len(top) - 1) + "."]
    ind += "  "
    width = WIDTH - len(ind)
    lines = [to_ascii(line.expandtabs(4), squeeze=False) for line in b["lines"]]
    # Plain text (```text) is not highlighted: its command lines are ansify's.
    plain_text = highlight.canonical(b.get("lang", "")) in (None, "text")
    toks = None if plain_text else highlight.kinds("\n".join(lines), b["lang"])
    start = CODE_BLOCK if toks is None else HL_BLOCK
    for line, kinds in zip(lines, _kinds_by_line(toks, lines)):
        while len(line) > width:
            out.append(start + ind + _marked(line[:width - 1], kinds[:width - 1]) + "\\")
            line, kinds = "  " + line[width - 1:], [None, None] + kinds[width - 1:]
        out.append(start + ind + _marked(line, kinds))
    out.append(FRAME + ind[:-2] + "'" + "-" * (span - 2) + "'")
    return out


def _kinds_by_line(toks, lines):
    """Each line's kind per character (None: no colour), from the tokens
    of the whole block."""
    if toks is None:
        return [[None] * len(line) for line in lines]
    chars = [kind for kind, text in toks for _ in text]
    out, pos = [], 0
    for line in lines:
        out.append(chars[pos:pos + len(line)])
        pos += len(line) + 1
    return out


def _marked(line, kinds):
    """The line with each run of one kind between HL[kind] and HL_OFF. The
    spaces around a run take no colour (the text's lines are stripped of
    their trailing spaces)."""
    out, n = [], 0
    while n < len(line):
        end = n
        while end < len(line) and kinds[end] == kinds[n]:
            end += 1
        run = line[n:end]
        body = run.strip()
        if kinds[n] and body:
            lead = run[:len(run) - len(run.lstrip())]
            run = lead + HL[kinds[n]] + body + HL_OFF + run[len(lead) + len(body):]
        out.append(run)
        n = end
    return "".join(out)


def txt_list(b, ind):
    """  - item, 1. item, - [x] item; wrapped lines and nested lists align
    under the item's text."""
    out = []
    for n, i in enumerate(b["items"]):
        marker = f"{b['start'] + n}." if b["ordered"] else "-"
        if i["task"] is not None:
            marker += " [x]" if i["task"] else " [ ]"
        head = ind + "  " + marker + " "
        lines = fill(txt(i["text"]), WIDTH - len(head)) or [""]
        out.append(ind + "  " + LIST_ON + marker + LIST_OFF + " " + lines[0])
        out.extend(" " * len(head) + l for l in lines[1:])
        for child in i["children"]:
            out.extend(txt_list(child, ind + " " * (len(marker) + 1)))
    return out


def txt_callout(b, ind):
    """A box, the label in its top rule:  +- ATTENTION ----+"""
    width = WIDTH - len(ind)
    label = to_ascii(CFG["labels"][b["kind"]])
    out = [ind + "+- " + label + " " + "-" * (width - len(label) - 5) + "+"]
    for i, t in enumerate(b["paras"]):
        if i:
            out.append(ind + "|" + " " * (width - 2) + "|")
        for line in fill(txt(t), width - 4):
            out.append(ind + "| " + line + " " * (width - 4 - vlen(line)) + " |")
    out.append(ind + "+" + "-" * (width - 2) + "+")
    return out


def txt_table(b, ind):
    """Columns padded to their widest cell, like `column -t`. If that does
    not fit in 75 columns, one record per row instead: `Header: value`."""
    text = lambda c: to_ascii(inline.to_text(c))
    head = [text(c) for c in b["head"]]
    rows = [[text(c) for c in r] for r in b["rows"]]
    widths = [max(len(r[i]) for r in [head] + rows) for i in range(len(head))]
    if len(ind) + sum(widths) + 2 * (len(widths) - 1) <= WIDTH:
        def line(r):
            cols = []
            for c, w, a in zip(r, widths, b["align"]):
                cols.append(c.rjust(w) if a == "right" else c.center(w) if a == "center"
                            else c.ljust(w))
            return (ind + "  ".join(cols)).rstrip()
        return [line(head), ind + "  ".join("-" * w for w in widths)] + [line(r) for r in rows]
    out = []
    key = max(len(h) for h in head) + 2
    for n, r in enumerate(rows):
        if n:
            out.append("")
        for h, c in zip(head, r):
            lines = wrap(c, ind + " " * key) if c else [""]
            out.append((ind + (h + ":").ljust(key) + lines[0].lstrip()).rstrip())
            out.extend(lines[1:])
    return out


def txt_blocks(blocks, ind):
    out = []
    for b in blocks:
        if out and out[-1] != "":
            out.append("")
        if b["k"] in ("para", "empty"):
            text = b.get("txt", b["text"])
            if not text:
                continue
            out.extend(wrap(txt(text), ind))
        elif b["k"] == "list":
            out.extend(txt_list(b, ind))
        elif b["k"] == "rule":
            out.append(ind + "-" * (WIDTH - len(ind)))
        elif b["k"] == "code":
            out.extend(txt_code(b, ind))
        elif b["k"] == "inset":
            if b["kind"]:
                out.extend(txt_callout(b, ind))
            else:
                for i, t in enumerate(b["paras"]):
                    if i:
                        out.append("")
                    out.extend(wrap(txt(t), ind + "  "))
        elif b["k"] == "table":
            out.extend(txt_table(b, ind))
        elif b["k"] == "toc":
            shown = [x for x in b["sections"] if "html" not in x["cls"]]
            out.append(ind + to_ascii(CFG["labels"]["toc"]).upper())
            for n, x in enumerate(shown, 1):
                out.append(f"{ind}  {n:>2}. {to_ascii(x['title']).upper()}")
        elif b["k"] == "profiles":
            for key, label, url in b["items"]:
                out.extend(wrap(to_ascii(f"{label}: {url}"), ind))
        elif b["k"] == "image":
            # The path from the root, not the full URL: a URL does not fit in
            # 75 columns and cannot be cut; the path is enough for curl.
            src = b["src"] if b["src"].startswith("http") else f"/{b['src']}"
            alt = to_ascii(b["alt"]) or "image"
            out.extend(wrap(f"[ {to_ascii(CFG['labels']['image'])} ] {alt}", ind))
            if b["caption"]:
                out.extend(wrap(txt(b["caption"]), ind + "  "))
            out.append(ind + "  " + to_ascii(src))
        elif b["k"] == "entry":
            title = txt(b["title"])
            tags = [m[1:-1] for m in b["meta"] if m.startswith("`") and m.endswith("`")]
            line = ind + title
            if tags:
                tag = "[ " + to_ascii(tags[0]) + " ]"
                if vlen(line) + 2 + len(tag) <= WIDTH:
                    line += " " * (WIDTH - vlen(line) - len(tag)) + tag
            out.append(line)
            for m in b["meta"]:
                if m.startswith("`"):
                    continue
                val = m.split(" | ", 1)[1] if " | " in m else m
                out.extend(wrap(to_ascii(val), ind))
            body = txt_blocks(b["blocks"], ind + "    ")
            if body:
                out.append("")
                out.extend(body)
    return out


def render_txt(meta, sections, around=""):
    """The page's text mirror. `around`: the line of a sequential type's
    neighbours (sequence.txt_line), set before the footer rule."""
    man = to_ascii(meta["man"])
    out = [rule(man, to_ascii(CFG["site"]["manual"]), man)]
    if languages.multilingual():
        out += ["", "LANGUAGES: " + " ".join(languages.declared())]
    for s in sections:
        if "html" in s["cls"]:
            continue
        out.append("")
        out.append(to_ascii(s["title"]).upper())
        out.extend(txt_blocks(s["blocks"], " " * INDENT))
    if around:
        out += ["", around]
    out.append("")
    foot = CFG["footer"]
    out.append(rule(to_ascii(foot["left"]), to_ascii(CFG["site"]["updated"]), to_ascii(foot["right"])))
    text = "\n".join(l.rstrip() for l in out) + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)
