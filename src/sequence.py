"""Collection navigation: a collection's items in order as a sidebar
({{ collection_nav }}), a page's neighbours ({{ prev }}, {{ next }}), and
their line in the text mirror, for a SEQUENTIAL type. The order is the one
load_items returns (the type's sort_key); groups come from the items'
`group:`. docs/theme.md is the contract."""

import html as H

from config import CFG, WIDTH
from fold import to_ascii

GAP = 2  # the least space between the two sides of the text line


def shown(path, colls, items):
    """(name, items) of the collection a page shows: the one it is an item
    of, or the one whose own page it is (<dir>/index.html, or <dir>.html
    beside the folder: a bare list marker's rule). (None, []) else."""
    for name, its in items.items():
        if any(it["path"] == path for it in its):
            return name, its
    folder = path[:-5].removesuffix("/index")
    for name, conf in colls.items():
        if folder == conf["dir"]:
            return name, items.get(name, [])
    return None, []


def groups(items):
    """[(label or None, [item])]: the items without a group first, then each
    group in the order of its first item."""
    loose, named = [], {}
    for it in items:
        g = it["meta"].get("group")
        if g is None or g == "":
            loose.append(it)
        else:
            named.setdefault(str(g), []).append(it)
    return ([(None, loose)] if loose else []) + list(named.items())


def neighbours(items, path):
    """(previous item, next item) of the page in the order, groups ignored;
    None at an end, or both when the page is not one of the items."""
    paths = [it["path"] for it in items]
    if path not in paths:
        return None, None
    i = paths.index(path)
    return (items[i - 1] if i > 0 else None,
            items[i + 1] if i + 1 < len(items) else None)


def title(item):
    return item["meta"].get("title") or item.get("slug", "")


def nav_html(items, path, conf, res):
    """{{ collection_nav }}: every item, grouped, the page's own marked.
    `res` resolves a root-relative page target from the page."""
    if not items:
        return ""
    label = H.escape(conf.get("nav_label") or CFG["labels"]["collection_nav"])

    def li(it, ind):
        current = ' aria-current="page"' if it["path"] == path else ""
        return f'{ind}<li><a href="{res(it["path"][:-5])}"{current}>{H.escape(title(it))}</a></li>'

    out = [f'<nav class="collection-nav" aria-label="{label}">', "<ul>"]
    for group, its in groups(items):
        if group is None:
            out += [li(it, "\t") for it in its]
            continue
        out.append(f'\t<li class="collection-group"><span class="collection-group-label">'
                   f'{H.escape(group)}</span>')
        out.append("\t<ul>")
        out += [li(it, "\t\t") for it in its]
        out += ["\t</ul>", "\t</li>"]
    out += ["</ul>", "</nav>"]
    return "\n".join(out)


def link_html(kind, item, res):
    """{{ prev }} or {{ next }} (kind "prev" or "next"): a link to the
    neighbour, labelled from [labels]; empty without one."""
    if item is None:
        return ""
    label = H.escape(CFG["labels"][kind])
    return (f'<a class="{kind}" rel="{kind}" href="{res(item["path"][:-5])}">'
            f'<span class="{kind}-label">{label}</span> {H.escape(title(item))}</a>')


def clip(text, width):
    return text if len(text) <= width else text[:width - 3] + "..."


def line(prev, nxt):
    """The text mirror's line: `previous: <title>` on the left, `next:
    <title>` on the right, ASCII, WIDTH columns at most, a title cut with
    ... when both do not fit. Empty when there is neither."""
    left = f"{to_ascii(CFG['labels']['prev'])}: {to_ascii(prev)}" if prev else ""
    right = f"{to_ascii(CFG['labels']['next'])}: {to_ascii(nxt)}" if nxt else ""
    if left and right and len(left) + len(right) > WIDTH - GAP:
        room = WIDTH - GAP
        half = room // 2
        if len(left) <= half:
            right = clip(right, room - len(left))
        elif len(right) <= half:
            left = clip(left, room - len(right))
        else:
            left, right = clip(left, half), clip(right, room - half)
    left, right = clip(left, WIDTH), clip(right, WIDTH)
    if not left and not right:
        return ""
    if left and right:
        return left + " " * (WIDTH - len(left) - len(right)) + right
    return left or " " * (WIDTH - len(right)) + right


def txt_line(item, colls, items):
    """The line for an item's text mirror: only for a SEQUENTIAL type."""
    if not item["type"].SEQUENTIAL:
        return ""
    _, its = shown(item["path"], colls, items)
    prev, nxt = neighbours(its, item["path"])
    return line(prev and title(prev), nxt and title(nxt))
