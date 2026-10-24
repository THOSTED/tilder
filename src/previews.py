"""Share previews per page: a 1200x630 PNG drawn at build time from the
theme's share-<type>.svg, else share-page.svg, filled with the page's own
fields - nothing committed. The landing page keeps the site's card,
share.png (icons.py); so does a page marked noindex, and a page that sets
`image:` shows that image instead.

Text is fitted by character count - the template is meant for a
monospace face - and cut with "..." when it does not fit: the title on
[share] title_lines lines of title_columns, the detail lines on
detail_columns. Everything is XML-escaped.

Each preview is named by a hash of the filled SVG and the fonts that draw
it, previews/<key>.png, and cached like the diagrams: in memory, in
TILDER_CACHE (else a folder of the system's temporary directory), and in
the previous output.
"""

import base64
import hashlib
import html as H
import os
import pathlib
import tempfile
from urllib.parse import urlparse

from config import ASSETS, CFG, STATE, THEME, apex, theme_file
from dates import human_date
from icons import PLACEHOLDER
from images import rasterize
from report import error

FOLDER = "previews"     # where the PNGs land, at the site root
VERSION = 1             # of the filling below: part of the key
WIDTH, HEIGHT = 1200, 630

MEMORY = {}     # key -> PNG bytes, for the life of the process (--watch)
FILES = {}      # this build's previews: "previews/<key>.png" -> PNG bytes


def reset():
    FILES.clear()


def template(item):
    """The theme's template for this page, or None."""
    for name in (f"share-{item['type'].NAME}.svg", "share-page.svg"):
        path = theme_file(name)
        if path.is_file():
            return path
    return None


# --- fitting text ------------------------------------------------------------

def cut(text, columns):
    """`text` in at most `columns` characters, cut with "..." when longer,
    at a space when one is near."""
    text = " ".join(text.split())
    if len(text) <= columns:
        return text
    room = max(columns - 3, 1)
    head = text[:room]
    space = head.rfind(" ")
    if space >= room // 2:
        head = head[:space]
    return head.rstrip(" ,;:.-") + "..."


def wrap(text, columns, lines):
    """`text` on at most `lines` lines of `columns` characters, broken at
    spaces (a word longer than a line is split); the last line ends with
    "..." when the text does not fit. Always `lines` strings, the unused
    ones empty."""
    out, line = [], ""
    for word in text.split():
        while len(word) > columns:
            if line:
                out.append(line)
                line = ""
            out.append(word[:columns])
            word = word[columns:]
        if line and len(line) + 1 + len(word) > columns:
            out.append(line)
            line = ""
        line = f"{line} {word}" if line else word
    if line:
        out.append(line)
    if len(out) > lines:
        out = out[:lines - 1] + [cut(" ".join(out[lines - 1:]), columns)]
    return out + [""] * (lines - len(out))


# --- the page's fields ---------------------------------------------------------

def path_of(item):
    """The page's place in the site, as the preview's ~/<site> path shows
    it: "/events" for an event (its collection's folder), "/mentorat" for a
    page, "/blog" for a folder's own page. Without a language prefix."""
    p = item["path"][:-5]
    own_index = p.endswith("/index")
    p = p.removesuffix("/index")
    if item.get("collection") and not own_index:
        p = p.rpartition("/")[0]
    return "/" + p if p and p != "index" else ""


def fields(item, logo):
    """{placeholder: XML-escaped value} for the page's template."""
    meta, conf = item["meta"], CFG["share"]
    title = wrap(meta.get("share_title") or meta.get("title", ""),
                 conf["title_columns"], conf["title_lines"])
    used = sum(1 for t in title if t)
    details = [meta.get("tagline", "") or (human_date(item["date"]) if item.get("date") else ""),
               meta.get("place", "") or meta.get("author", "")]
    if not details[0]:
        details = [details[1], ""]
    said = [d for d in details if d]   # in full, for the alt text
    details = [cut(d, conf["detail_columns"]) for d in details]
    tag = cut(meta.get("tag", ""), conf["detail_columns"])
    path = path_of(item)
    domain = urlparse(CFG["site"]["url"]).netloc
    # The address of that place, in the page's language: example.org/fr/events.
    url = (domain + "/" + STATE["prefix"] + path.lstrip("/")).rstrip("/")
    values = {
        "logo": "data:image/svg+xml;base64," + base64.b64encode(logo).decode() if logo else "",
        "manual_upper": CFG["site"]["manual"].upper(),
        "wordmark": CFG["site"]["name"].lower(),
        "domain": domain,
        "man": meta.get("man") or CFG["footer"]["right"],
        "path": path,
        "url": url,
        "title_1": title[0],
        "title_2": title[1] if len(title) > 1 else "",
        "title_3": title[2] if len(title) > 2 else "",
        # How far up what follows the title moves for each line it does not use.
        "title_shift": str(-(conf["title_lines"] - max(used, 1)) * conf["title_line_height"]),
        "detail_1": details[0],
        "detail_2": details[1],
        "tag": tag,
        "tag_width": f"{len(tag) * conf['tag_advance'] + 2 * conf['tag_padding']:g}",
        "tag_display": "inline" if tag else "none",
    }
    alt = " - ".join(x for x in (f"~/{values['wordmark']}{path}",
                                  meta.get("share_title") or meta.get("title", ""),
                                  *said, meta.get("tag", "")) if x)
    out = {k: (v if k == "logo" else H.escape(v)) for k, v in values.items()}
    return out, alt


def fill(text, values, path):
    """{{ name }}: a page field, else a site.toml value; XML-escaped."""
    def value(m):
        name = m.group(1)
        if name in values:
            return values[name]
        node = CFG
        for part in name.split("."):
            if not isinstance(node, dict) or part not in node:
                raise error(path, f"unknown placeholder {{{{ {name} }}}}",
                            "The placeholders are listed in docs/theme.md, \"Share previews\"")
            node = node[part]
        return H.escape(str(node))
    return PLACEHOLDER.sub(value, text)


# --- drawing -------------------------------------------------------------------

def _fonts():
    folder = THEME / "fonts"
    return [(f.name, f.stat().st_size) for f in sorted(folder.glob("*"))] if folder.is_dir() else []


def _cache_dir():
    if os.environ.get("TILDER_CACHE"):
        return pathlib.Path(os.environ["TILDER_CACHE"]) / "previews"
    return pathlib.Path(tempfile.gettempdir()) / "tilder-previews"


def _cached(key, name):
    places = [_cache_dir() / f"{key}.png"]
    if STATE.get("out"):
        places.append(pathlib.Path(STATE["out"]) / name)
    for p in places:
        try:
            return p.read_bytes()
        except OSError:
            continue
    return None


def _store(key, png):
    try:
        d = _cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f".{key}.tmp"
        tmp.write_bytes(png)
        os.replace(tmp, d / f"{key}.png")
    except OSError:
        pass


def wanted(item):
    meta = item["meta"]
    from seo import is_landing  # seo reads the result through share_image
    return (CFG["share"]["pages"] and not meta.get("image") and not is_landing(meta)
            and "noindex" not in meta.get("robots", "") and template(item) is not None)


def draw(item):
    """Draw the page's preview; record it in meta["_preview"] as
    (path from the site root, width, height, alt). Nothing when the page
    keeps the site's card, or no rasteriser is installed."""
    if not wanted(item):
        return
    path = template(item)
    logo_path = ASSETS / CFG["share"]["logo_svg"]
    logo = logo_path.read_bytes() if logo_path.is_file() else b""
    values, alt = fields(item, logo)
    svg = fill(path.read_text(), values, path).encode()
    key = hashlib.sha256(repr((VERSION, svg, _fonts())).encode()).hexdigest()[:20]
    name = f"{FOLDER}/{key}.png"
    png = MEMORY.get(key) or _cached(key, name)
    if png is None:
        png = rasterize(svg, WIDTH, HEIGHT)
        if png is None:
            return          # no rasteriser: the build has warned; the site's card stands
        _store(key, png)
    MEMORY[key] = png
    FILES[name] = png
    item["meta"]["_preview"] = (name, WIDTH, HEIGHT, alt)


def outputs():
    return dict(FILES)
