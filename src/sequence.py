"""Collection navigation: a collection's items in order as a sidebar
({{ collection_nav }}), a page's neighbours ({{ prev }}, {{ next }}), and
their line in the text mirror, for a SEQUENTIAL type. The order is the one
load_items returns (the type's sort_key, depth-first in a recursive collection); groups come from the items' group:, sections from their folders.
docs/theme.md is the contract."""

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
    group in the order of its first item. An entry of the sidebar's tree
    (tree()) may stand for an item: a section groups by its own page."""
    loose, named = [], {}
    for it in items:
        g = _meta(it).get("group")
        if g is None or g == "":
            loose.append(it)
        else:
            named.setdefault(str(g), []).append(it)
    return ([(None, loose)] if loose else []) + list(named.items())


def _meta(entry):
    """An item's front matter; a section's is its own page's, or none."""
    if "entries" in entry:
        return entry["own"]["meta"] if entry["own"] else {}
    return entry["meta"]


def tree(items):
    """The items as the sidebar shows them: a list of entries, each an item
    or a section {"path": "guide", "own": its own page's item or None,
    "entries": [...]}, in the order of `items` (a recursive collection's
    depth-first order, contenttypes.load_items). A flat collection is its
    list of items."""
    below = set()  # every section: each folder of an item's section
    for it in items:
        parts = it.get("section", "").split("/") if it.get("section") else []
        below.update("/".join(parts[:i + 1]) for i in range(len(parts)))
    top, nodes = [], {}

    def node(path):
        if path not in nodes:
            nodes[path] = {"path": path, "own": None, "entries": []}
            parent = path.rpartition("/")[0]
            (node(parent)["entries"] if parent else top).append(nodes[path])
        return nodes[path]

    for it in items:
        if it.get("slug") in below:
            node(it["slug"])["own"] = it
        elif it.get("section"):
            node(it["section"])["entries"].append(it)
        else:
            top.append(it)
    return top


def _holds(entry, path):
    """Is the page at `path` this entry, or inside this section?"""
    if "entries" not in entry:
        return entry["path"] == path
    return (entry["own"] is not None and entry["own"]["path"] == path) or \
        any(_holds(e, path) for e in entry["entries"])


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
    """{{ collection_nav }}: every item, grouped, the page's own marked; a
    recursive collection's sections nested, the one holding the page open.
    `res` resolves a root-relative page target from the page."""
    if not items:
        return ""
    label = H.escape(conf.get("nav_label") or CFG["labels"]["collection_nav"])

    def current(it):
        return ' aria-current="page"' if it["path"] == path else ""

    def entry(e, ind):
        if "entries" not in e:
            return [f'{ind}<li><a href="{res(e["path"][:-5])}"{current(e)}>{H.escape(title(e))}</a></li>']
        cls = "collection-section" + (" collection-section--open" if _holds(e, path) else "")
        own = e["own"]
        head = (f'<a class="collection-section-label" href="{res(own["path"][:-5])}"{current(own)}>'
                f'{H.escape(title(own))}</a>' if own else
                f'<span class="collection-section-label">{H.escape(e["path"].rpartition("/")[2])}</span>')
        return ([f'{ind}<li class="{cls}">{head}', f"{ind}<ul>"]
                + level(e["entries"], ind + "\t") + [f"{ind}</ul>", f"{ind}</li>"])

    def level(entries, ind):
        out = []
        for group, its in groups(entries):
            if group is None:
                for e in its:
                    out += entry(e, ind)
                continue
            out.append(f'{ind}<li class="collection-group"><span class="collection-group-label">'
                       f'{H.escape(group)}</span>')
            out.append(f"{ind}<ul>")
            for e in its:
                out += entry(e, ind + "\t")
            out += [f"{ind}</ul>", f"{ind}</li>"]
        return out

    return "\n".join([f'<nav class="collection-nav" aria-label="{label}">', "<ul>"]
                     + level(tree(items), "\t") + ["</ul>", "</nav>"])


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
