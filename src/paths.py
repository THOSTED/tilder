"""From content/ paths to output paths, URLs and relative links. Paths are
logical, without a language prefix; the prefix is added here where a URL
or a link leaves the language (clean_url, absolute, a /-leading target or
a file target, which resolve from the site root)."""

import os

from config import CONTENT, DATED, STATE, apex
from languages import prefix, split

# content/-relative folders that are one item each (a member kept as a
# folder with a file beside its page): only their index.md is a page, and
# it is served next to the folder. Filled by contenttypes.load_items.
ITEM_FOLDERS = set()

# content/-relative folders that are sections of a recursive collection:
# folders holding items, mapped to whether they have their own page
# (index.md, or a <name>.md beside the folder), which is served next to
# the folder like an item folder's. Their other files are pages too.
# Filled by contenttypes.load_items.
SECTIONS = {}


def item_folder(rel_parent):
    """Is this content/-relative folder one item?"""
    return bool(DATED.match(rel_parent.name)) or str(rel_parent) in ITEM_FOLDERS


def txt_name(html_path):
    n = html_path[:-5]
    if n.endswith("/index"):
        n = n[: -len("/index")]
    return n


def clean_url(html_path, lang=None):
    """The URL path of a page in a language (default: the current pass):
    "/", "/fr/", "/fr/events", "/blog/"."""
    n = html_path[:-5]
    p = prefix(lang)
    if n == "index":
        return "/" + p
    if n.endswith("/index"):
        return "/" + p + n[: -len("/index")] + "/"
    return "/" + p + n


def absolute(rel, lang=None):
    """The absolute URL of a root-relative file of a language: feeds."""
    return f"{apex()}/{prefix(lang)}{rel}"


def is_file(target):
    """Does a root-relative target name a file rather than a page? Its last
    segment has an extension: style.css, events.ics, blog/x/p.svg. A page
    has none (events, blog/hello), or ends in "/" (blog/), or is empty."""
    last = target.rstrip("/").rsplit("/", 1)[-1]
    return "." in last and not target.endswith("/")


def relative(from_dir, target, page=None):
    """Resolve a target from the directory of the page being rendered.
    A page target ("", "events", "blog/", "./#id") stays inside the
    language; a file target (style.css, logo.svg, events.ics: anything
    with an extension) and a target starting with "/" resolve from the
    site root, where the build writes files once, so a page may also link
    to another language ("/events", "/fr/events"). page=True keeps a file
    target inside the language: a feed, the one file written per language.
    A bare "#id" stays on the page."""
    if target.startswith("http") or target.startswith("#"):
        return target
    target, hash_, frag = target.partition("#")
    if target.startswith("/") or (is_file(target) and page is not True):
        base = (STATE["prefix"] + from_dir).rstrip("/")
        return _relative(base, target.lstrip("/").removeprefix("./")) + hash_ + frag
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
    (templates), or it sits in an item's folder without being its index
    (index.md, index.fr.md)."""
    rel = path.relative_to(CONTENT)
    if any(part.startswith("_") for part in rel.parts):
        return False
    name, _ = split(rel.stem)
    return name == "index" or not item_folder(rel.parent)


def page_path(src):
    """content/blog/X/index.md -> blog/X.html: an item folder's page sits
    next to the folder. The language suffix is not part of the path:
    about.fr.md -> about.html."""
    rel = src.relative_to(CONTENT)
    name, _ = split(rel.stem)
    if name == "index" and (item_folder(rel.parent) or SECTIONS.get(str(rel.parent))):
        return str(rel.parent) + ".html"
    return str(rel.with_name(name + ".html"))
