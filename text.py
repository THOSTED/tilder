"""The text mirror: ASCII, 75 columns, the same tree as the page.

render_txt() returns the text with invisible marks: CODE_ON / CODE_OFF
around inline `code`, CODE_BLOCK at the start of a code block's lines,
FRAME at the start of its two rules, LIST_ON / LIST_OFF around a list
item's marker.
plain() removes them for txt/; ansify.py turns them into colour for ansi/.
Widths are measured without them.
"""

import re

import inline
from config import CFG, INDENT, WIDTH
from fold import to_ascii
from inline import CODE_OFF, CODE_ON

CODE_BLOCK = "\x04"
LIST_ON, LIST_OFF = "\x05", "\x06"  # around a list marker: -, 1., - [x]
FRAME = "\x07"                      # a code block's top or bottom rule
_MARKS = re.compile("[\x02-\x07]")


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
    for line in b["lines"]:
        line = to_ascii(line.expandtabs(4), squeeze=False)
        while len(line) > width:
            out.append(CODE_BLOCK + ind + line[:width - 1] + "\\")
            line = "  " + line[width - 1:]
        out.append(CODE_BLOCK + ind + line)
    out.append(FRAME + ind[:-2] + "'" + "-" * (span - 2) + "'")
    return out


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
                out.extend(wrap(f"{to_ascii(label)}: {url}", ind))
        elif b["k"] == "image":
            # The path from the root, not the full URL: a URL does not fit in
            # 75 columns and cannot be cut; the path is enough for curl.
            src = b["src"] if b["src"].startswith("http") else f"/{b['src']}"
            alt = to_ascii(b["alt"]) or "image"
            out.extend(wrap(f"[ {to_ascii(CFG['labels']['image'])} ] {alt}", ind))
            if b["caption"]:
                out.extend(wrap(txt(b["caption"]), ind + "  "))
            out.append(ind + "  " + src)
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


def render_txt(meta, sections):
    man = meta["man"]
    out = [rule(man, to_ascii(CFG["site"]["manual"]), man)]
    for s in sections:
        if "html" in s["cls"]:
            continue
        out.append("")
        out.append(to_ascii(s["title"]).upper())
        out.extend(txt_blocks(s["blocks"], " " * INDENT))
    out.append("")
    foot = CFG["footer"]
    out.append(rule(to_ascii(foot["left"]), CFG["site"]["updated"], to_ascii(foot["right"])))
    text = "\n".join(l.rstrip() for l in out) + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)
