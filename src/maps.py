"""Static maps on event pages: for an event with `lat` and `lon`, a few map
tiles around the point, fetched at build time, composed into one PNG with
a marker, maps/<key>.png. Visitors load nothing from another host.

Opt-in: [maps] enabled = true in site.toml. The tiles come from [maps]
tiles, OpenStreetMap's by default, whose usage policy the build follows: a
User-Agent naming tilder and the site, a handful of tiles per map, and a
cache that outlives the process (TILDER_CACHE, else a folder of the
system's temporary directory), so a tile is fetched once, not at every
rebuild, and again only when it is older than [maps] max_age_days. A
composed map is also reused from the previous output.

Never guessed: no lat and lon, no map. A fetch that fails, or no
rasteriser, is a warning: the page keeps its OpenStreetMap link, the build
goes on. The tiles are composed as an SVG (each tile a data: URI, the
whole cropped and centred on the point), then rasterised like share.png:
a PNG is a fraction of the SVG's size, which carries every tile whole in
base64.
"""

import base64
import hashlib
import math
import os
import pathlib
import tempfile
import time
import urllib.parse
import urllib.request

from config import CFG, STATE
from images import palette_png, rasterize
from report import warning

VERSION = 1             # of the composition below: part of the key
FOLDER = "maps"         # where the PNGs land, at the site root
TILE = 256              # px, the size of a tile
TIMEOUT = 10            # s, per tile

MEMORY = {}     # key -> PNG bytes, for the life of the process (--watch)
FILES = {}      # this build's maps: "maps/<key>.png" -> PNG bytes
_said = set()


def reset():
    FILES.clear()
    _said.clear()


def _say(key, path, what, hint=""):
    if key not in _said:
        _said.add(key)
        warning(path, what, hint)


def _cache_dir():
    base = os.environ.get("TILDER_CACHE")
    return (pathlib.Path(base) if base else pathlib.Path(tempfile.gettempdir()) / "tilder") / "maps"


def user_agent():
    """Who asks: tilder, its version, and the site, as the tile usage policy wants."""
    return f"tilder/{os.environ.get('TILDER_VERSION', 'dev')} (+{CFG['site']['url']})"


# --- tiles -----------------------------------------------------------------

def pixel(lat, lon, zoom):
    """The point's position in the world map at `zoom`, in pixels."""
    n = TILE * 2 ** zoom
    x = (lon + 180) / 360 * n
    lat = max(min(lat, 85.0511), -85.0511)
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def tiles(lat, lon, zoom, width, height):
    """[(tile x, tile y, left, top)]: the tiles under a width x height
    window centred on the point, and where each sits in the window."""
    px, py = pixel(lat, lon, zoom)
    left, top = px - width / 2, py - height / 2
    count = 2 ** zoom
    out = []
    for ty in range(math.floor(top / TILE), math.floor((top + height - 1) / TILE) + 1):
        if not 0 <= ty < count:
            continue
        for tx in range(math.floor(left / TILE), math.floor((left + width - 1) / TILE) + 1):
            out.append((tx % count, ty, tx * TILE - left, ty * TILE - top))
    return out


def fetch(url):
    """A tile's bytes: from the cache when it is fresh enough, else from the
    server (then kept). A stale tile serves when the server cannot."""
    conf = CFG["maps"]
    path = _cache_dir() / "tiles" / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".png")
    fresh = conf["max_age_days"] * 86400
    if path.is_file() and time.time() - path.stat().st_mtime < fresh:
        return path.read_bytes()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as r:
            data = r.read()
    except Exception:
        if path.is_file():
            return path.read_bytes()
        raise
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except OSError:
        pass
    return data


# --- the map -------------------------------------------------------------------

def svg(lat, lon, images):
    """The map as an SVG: the tiles, cropped by the frame, and the marker
    at the centre."""
    conf = CFG["maps"]
    w, h = conf["width"], conf["height"]
    colour = conf["marker"] or CFG["share"]["theme_color"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
             f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for (left, top), data in images:
        uri = "data:image/png;base64," + base64.b64encode(data).decode()
        # Whole pixels: a tile drawn between two pixels would be resampled,
        # its few colours smeared into thousands (images.palette_png).
        parts.append(f'<image x="{round(left)}" y="{round(top)}" width="{TILE}" height="{TILE}" '
                     f'xlink:href="{uri}" href="{uri}"/>')
    cx, cy = w / 2, h / 2
    # A pin: a disc on a point, its tip on the place.
    parts.append(f'<path d="M{cx} {cy} l-9 -15 a11 11 0 1 1 18 0 z" fill="{colour}" '
                 f'stroke="#FFFFFF" stroke-width="2.5" stroke-linejoin="round"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy - 21}" r="4" fill="#FFFFFF"/>')
    parts.append("</svg>")
    return "\n".join(parts).encode()


def coordinates(meta):
    """(lat, lon) as floats, or None: never guessed."""
    try:
        lat, lon = float(meta["lat"]), float(meta["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def draw(meta, src):
    """The path from the site root of the event's map ("maps/<key>.png"),
    or None: maps off, no coordinates, or the tiles or the rasteriser
    missing (a warning). `src` is the event's file, for messages."""
    conf = CFG["maps"]
    point = coordinates(meta) if conf["enabled"] else None
    if point is None:
        return None
    lat, lon = point
    zoom, w, h = conf["zoom"], conf["width"], conf["height"]
    marker = conf["marker"] or CFG["share"]["theme_color"]
    key = hashlib.sha256(repr((VERSION, conf["tiles"], zoom, w, h, round(lat, 7), round(lon, 7),
                               marker)).encode()).hexdigest()[:20]
    name = f"{FOLDER}/{key}.png"
    png = MEMORY.get(key) or _previous(name)
    if png is None:
        try:
            images = [((left, top), fetch(conf["tiles"].format(z=zoom, x=tx, y=ty)))
                      for tx, ty, left, top in tiles(lat, lon, zoom, w, h)]
        except Exception as e:
            host = urllib.parse.urlsplit(conf["tiles"]).netloc or conf["tiles"]
            _say(("fetch", str(src)), src, f"no map: the tiles cannot be fetched from {host} "
                 f"({e.__class__.__name__}: {e})", "The page keeps its OpenStreetMap link")
            return None
        try:
            png = rasterize(svg(lat, lon, images), w, h)
            png = png and palette_png(png)
        except Exception as e:      # a renderer that fails on a tile
            _say(("draw", str(src)), src, f"no map: it cannot be drawn ({e.__class__.__name__})",
                 "The page keeps its OpenStreetMap link")
            return None
        if png is None:
            return None             # no rasteriser: the build has warned
    MEMORY[key] = png
    FILES[name] = png
    return name


def _previous(name):
    if not STATE.get("out"):
        return None
    try:
        return (pathlib.Path(STATE["out"]) / name).read_bytes()
    except OSError:
        return None


def outputs():
    return dict(FILES)
