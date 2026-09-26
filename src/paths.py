"""From content/ paths to output paths, URLs and relative links."""

import os

from config import CONTENT, DATED

def txt_name(html_path):
    n = html_path[:-5]
    if n.endswith("/index"):
        n = n[: -len("/index")]
    return n


def clean_url(html_path):
    n = html_path[:-5]
    if n == "index":
        return "/"
    if n.endswith("/index"):
        return "/" + n[: -len("/index")] + "/"
    return "/" + n


def relative(from_dir, target):
    """Resolve a root-relative target ("", "events", "blog/", "./#id") from
    the directory of the page being rendered. A bare "#id" stays on the page."""
    if target.startswith("http") or target.startswith("#"):
        return target
    target, hash_, frag = target.partition("#")
    if target in ("", "."):
        target = ""
    return _relative(from_dir, target.removeprefix("./")) + hash_ + frag


def _relative(from_dir, target):
    base = from_dir or "."
    if target == "":
        r = os.path.relpath(".", base)
        return "./" if r == "." else r + "/"
    if target.endswith("/"):
        r = os.path.relpath(target.rstrip("/"), base)
        return "./" if r == "." else r + "/"
    # A page, not a folder: resolve its folder, then add its name. Otherwise
    # "events" seen from events/... would be the folder itself (".").
    folder, name = os.path.split(target)
    r = os.path.relpath(folder or ".", base)
    return name if r == "." else f"{r}/{name}"


def rendered(path):
    """A Markdown file is a page unless a part of its path starts with `_`
    (templates), or it sits in a dated folder without being its index.md."""
    rel = path.relative_to(CONTENT)
    if any(part.startswith("_") for part in rel.parts):
        return False
    return rel.name == "index.md" or not DATED.match(rel.parent.name)


def page_path(src):
    """content/blog/X/index.md -> blog/X.html: a dated folder's page sits
    next to the folder, so the URL does not change with the layout."""
    rel = src.relative_to(CONTENT)
    if rel.name == "index.md" and DATED.match(rel.parent.name):
        return str(rel.parent) + ".html"
    return str(rel.with_suffix(".html"))
