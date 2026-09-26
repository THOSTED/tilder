"""The content format: front matter, blocks, lists, tables, callouts,
images. Markdown in, a tree of nodes out. See builder/docs/markdown.md."""

import posixpath
import re
import sys

from config import CONTENT
from fold import to_ascii

def front_matter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.index("\n---\n", 3)
    meta = {}
    for line in text[4:end].split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()
    return meta, text[end + 5:]


def markers(title):
    """Strip trailing {...} from a title: {#id} and classes."""
    cls, ident = [], None
    while True:
        m = re.search(r"\s*\{([^}]*)\}\s*$", title)
        if not m:
            break
        for tok in m.group(1).split():
            if tok.startswith("#"):
                ident = tok[1:]
            else:
                cls.append(tok)
        title = title[: m.start()].rstrip()
    return title, cls, ident


def raw_blocks(body):
    lines = body.split("\n")
    i, out, cur = 0, [], []
    while i < len(lines):
        l = lines[i]
        if l.strip().startswith("```"):
            # A fence of N backticks closes on a line of at least N backticks
            # and nothing else, so ```` can wrap an example containing ```.
            if cur:
                out.append(cur); cur = []
            n = len(l.strip()) - len(l.strip().lstrip("`"))
            code = []
            i += 1
            while i < len(lines) and not (
                    lines[i].strip().startswith("`" * n)
                    and lines[i].strip().strip("`") == ""):
                code.append(lines[i]); i += 1
            out.append([l] + code)
            i += 1
            continue
        if l.startswith(("## ", "### ")):
            # A heading is always a block of its own, blank line or not.
            if cur:
                out.append(cur); cur = []
            out.append([l])
        elif l.strip() == "":
            if cur:
                out.append(cur); cur = []
        else:
            cur.append(l)
        i += 1
    if cur:
        out.append(cur)
    return out


# Callout kinds: the source keyword (GitHub's aliases accepted) -> kind.
CALLOUTS = {"INFO": "info", "NOTE": "info", "TIP": "info",
            "WARNING": "warning", "IMPORTANT": "warning", "CAUTION": "warning",
            "ERROR": "error", "DANGER": "error"}
CALLOUT = re.compile(r"^\[!([A-Za-z]+)\]\s*(.*)$")
TABLE_RULE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


def inset(block):
    """`> text` lines. A line that is just `>` separates paragraphs. A first
    line `> [!INFO]`, `> [!WARNING]` or `> [!ERROR]` makes it a callout."""
    lines = [l[1:].strip() for l in block]
    kind = None
    m = CALLOUT.match(lines[0])
    if m and m.group(1).upper() in CALLOUTS:
        kind = CALLOUTS[m.group(1).upper()]
        lines[0] = m.group(2)
    paras, cur = [], []
    for l in lines:
        if l:
            cur.append(l)
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return {"k": "inset", "kind": kind, "paras": paras}


def cells(line):
    """Split a table row on unescaped pipes; `\\|` is a literal pipe."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def table(block):
    head = cells(block[0])
    align = []
    for c in cells(block[1]):
        left, right = c.startswith(":"), c.endswith(":")
        align.append("center" if left and right else "right" if right else "left")
    rows = []
    for line in block[2:]:
        row = cells(line)
        rows.append((row + [""] * len(head))[:len(head)])
    return {"k": "table", "head": head, "align": (align + ["left"] * len(head))[:len(head)],
            "rows": rows}


RULE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")
# "- item", "* item", "1. item", "1) item", at any indent (nesting).
LIST_ITEM = re.compile(r"^(\s*)(?:([-*])|(\d{1,9})[.)])\s+(.*)$")
TASK = re.compile(r"^\[([ xX])\]\s+(.*)$")


def parse_list(lines):
    """A list, nested by indentation. Each item: text, task (None, or done
    True/False), children (nested lists). An indented line that is not an
    item continues the previous item's text."""
    def new(m):
        ordered = m.group(3) is not None
        return {"k": "list", "ordered": ordered,
                "start": int(m.group(3)) if ordered else 1, "items": []}
    stack = []  # (indent, list node)
    for line in lines:
        m = LIST_ITEM.match(line)
        if not m:
            stack[-1][1]["items"][-1]["text"] += " " + line.strip()
            continue
        indent, text, task = len(m.group(1)), m.group(4).strip(), None
        t = TASK.match(text)
        if t:
            task, text = t.group(1) != " ", t.group(2)
        item = {"text": text, "task": task, "children": []}
        if not stack:
            stack.append((indent, new(m)))
        elif indent > stack[-1][0]:
            child = new(m)
            stack[-1][1]["items"][-1]["children"].append(child)
            stack.append((indent, child))
        else:
            while len(stack) > 1 and indent < stack[-1][0]:
                stack.pop()
        stack[-1][1]["items"].append(item)
    return stack[0][1]


IMAGE = re.compile(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)$')


def classify(block):
    head = block[0]
    if head.startswith("## "):
        t, cls, ident = markers(head[3:].strip())
        return {"k": "section", "title": t, "cls": cls, "id": ident, "blocks": []}
    if head.startswith("### "):
        t, cls, ident = markers(head[4:].strip())
        return {"k": "entry", "title": t, "cls": cls, "id": ident,
                "meta": [], "blocks": []}
    if head.strip().startswith("```"):
        return {"k": "code", "lang": head.strip().lstrip("`").strip(), "lines": block[1:]}
    if len(block) == 1 and RULE.match(head.strip()):
        return {"k": "rule"}
    if LIST_ITEM.match(head) and not head[0].isspace() and all(
            LIST_ITEM.match(l) or l[:1].isspace() for l in block):
        return parse_list(block)
    if all(l.startswith(">") for l in block):
        return inset(block)
    if len(block) >= 2 and all(l.strip().startswith("|") for l in block) \
            and TABLE_RULE.match(block[1].strip()):
        return table(block)
    if head.startswith("<!--"):
        return {"k": "comment", "lines": block}
    if len(block) == 1 and head.strip().upper() == "[TOC]":
        return {"k": "toc", "sections": []}  # filled once the page is parsed
    m = IMAGE.match(head.strip())
    if m and len(block) == 1:
        return {"k": "image", "alt": m.group(1), "src": m.group(2),
                "caption": m.group(3) or ""}
    text = " ".join(l.strip() for l in block)
    text, cls, _ = markers(text)
    if text.startswith("*") and text.endswith("*") and len(text) > 2:
        return {"k": "empty", "text": text[1:-1]}
    return {"k": "para", "text": text, "cls": cls}


def site_path(path):
    """content/blog/x/index.md -> blog/x : the page's folder, as a path from
    the site root. Images are written relative to it."""
    if not path.is_relative_to(CONTENT):  # a file outside content/: tests
        return ""
    return posixpath.dirname(str(path.relative_to(CONTENT)))


def resolve_images(nodes, base):
    """Turn each image's src, relative to the page's folder, into a path
    from the site root. Warn when the file is missing or alt is empty."""
    for n in nodes:
        if n["k"] == "image" and not n["src"].startswith(("http://", "https://")):
            n["src"] = posixpath.normpath(posixpath.join(base, n["src"]))
            if not (CONTENT / n["src"]).is_file():
                print(f"warning: image not found: content/{n['src']}", file=sys.stderr)
        if n["k"] == "image" and not n["alt"].strip():
            print(f"warning: image without alt text: {n['src']}", file=sys.stderr)
        resolve_images(n.get("blocks", []), base)


def parse(path):
    meta, body = front_matter(path.read_text())
    sections, section, entry = [], None, None
    after_entry = False
    preamble = []
    for block in raw_blocks(body):
        indent = len(block[0]) - len(block[0].lstrip())
        indented = indent >= 2
        if indent:
            block = [l[indent:] if l[:indent].isspace() else l.lstrip() for l in block]
        if entry is not None and not indented:
            entry = None
            after_entry = False
        n = classify(block)
        if section is None and n["k"] != "section":
            preamble.append(n)
            continue
        if n["k"] == "section":
            sections.append(n); section = n; entry = None; after_entry = False
            continue
        if n["k"] == "entry":
            section["blocks"].append(n); entry = n; after_entry = True
            continue
        if after_entry and n["k"] == "list":
            entry["meta"] = [i["text"] for i in n["items"]]; after_entry = False
            continue
        after_entry = False
        (entry["blocks"] if entry is not None else section["blocks"]).append(n)
    resolve_images(preamble + sections, site_path(path))
    anchor_sections(sections)
    fill_toc(preamble + sections, sections)
    return meta, sections, preamble


def anchor_sections(sections):
    """Give every section an id, from its title unless {#id} set one, so
    any section can be linked to, and [TOC] has targets."""
    taken = {s["id"] for s in sections if s["id"]}
    for s in sections:
        if s["id"]:
            continue
        base = re.sub(r"[^a-z0-9]+", "-", to_ascii(s["title"]).lower()).strip("-") or "section"
        ident, n = base, 2
        while ident in taken:
            ident, n = f"{base}-{n}", n + 1
        s["id"] = ident
        taken.add(ident)


def fill_toc(nodes, sections):
    """Point every [TOC] block at the page's sections."""
    for n in nodes:
        if n["k"] == "toc":
            n["sections"] = sections
        fill_toc(n.get("blocks", []), sections)
