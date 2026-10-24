"""Mermaid diagrams: a ```mermaid block drawn at build time into an SVG file,
diagrams/<key>.svg at the site root, shown by the page as an <img>.

The drawing is the Mermaid CLI's (`mmdc`, or the command TILDER_MMDC
names), an outside tool like rsvg-convert: without it, the build warns once
and the page shows the diagram's source, with its description. The theme
gives the look:

    theme/mermaid.json   Mermaid's configuration; a colour may be written
                         var(--token), a custom property of style.css
    style.css            the tokens, light and dark
    [diagrams]           in theme.toml: fold (Mermaid's own colours -> a
                         token), sharp, shadow

Mermaid draws with fixed colours. Each colour that is the light value of a
token becomes var(--token), and the SVG defines the tokens, light and
under prefers-color-scheme: dark, so the figure follows the reader's
scheme like the page does. Corners are squared and shadows dropped unless
the theme says otherwise. Fonts: the theme's fonts/, so labels are measured
in its typeface.

A drawing is cached by a key of everything it depends on (source,
configuration, palette, fonts, the renderer's version): in memory, in
TILDER_CACHE (else a folder of the system's temporary directory), and in
the previous output (--out), so a rebuild draws only what changed.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from config import CFG, STATE, THEME, THEME_TOML, theme_file
from report import error, warning

VERSION = 1             # of the post-processing below: part of the key
FOLDER = "diagrams"     # where the SVGs land, at the site root
TIMEOUT = 120           # seconds for one drawing
SVG = "http://www.w3.org/2000/svg"
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*\)")
ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

MEMORY = {}     # key -> SVG text, for the life of the process (--watch)
FILES = {}      # this build's drawings: "diagrams/<key>.svg" -> SVG text
_said = set()   # warnings already given in this build
_renderer = {}  # the command and its version, found once per process


def reset():
    """Before each build."""
    FILES.clear()
    _said.clear()


def command():
    """The Mermaid CLI's argv prefix, or None when it is not installed."""
    name = os.environ.get("TILDER_MMDC", "mmdc")
    if name not in _renderer:
        path = shutil.which(name)
        version = ""
        if path:
            try:
                version = subprocess.run([path, "--version"], capture_output=True, text=True,
                                         timeout=TIMEOUT).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                path = None
        _renderer[name] = (path, version)
    return _renderer[name]


def _say(key, path, what, hint=""):
    if key not in _said:
        _said.add(key)
        warning(path, what, hint)


# --- the theme's look ---------------------------------------------------------

def palette():
    """(light, dark): {token: value} of the colour tokens of the theme's
    style.css, in its order; dark is {} when the theme has no dark scheme."""
    import themecheck  # it imports config and report, as this module does
    css = theme_file("style.css")
    if not css.is_file():
        return {}, {}
    found = themecheck.tokens(css.read_text())
    colour = lambda v: bool(HEX.fullmatch(v.strip()))
    light = {k: v.strip() for k, v in found["light"].items() if colour(v)}
    dark = {k: v.strip() for k, v in (found["dark"] or {}).items() if k in light and colour(v)}
    return light, dark


def settings():
    """[diagrams] of the configuration, checked."""
    conf = CFG.get("diagrams", {})
    fold = conf.get("fold", {})
    if not isinstance(fold, dict) or not all(
            isinstance(k, str) and HEX.fullmatch(k) and isinstance(v, str) and v.startswith("--")
            for k, v in fold.items()):
        raise error(THEME_TOML, "[diagrams] fold must map colours to tokens",
                    'Write fold = { "#ECECFF" = "--bg" }')
    return {"fold": {_long(k): v for k, v in fold.items()},
            "sharp": conf.get("sharp", True) is not False,
            "shadow": conf.get("shadow", False) is True}


def mermaid_config(light):
    """theme/mermaid.json as text, var(--token) replaced by the token's
    light value; "{}" when the theme has none."""
    path = theme_file("mermaid.json")
    if not path.is_file():
        return "{}", None
    text = path.read_text()
    try:
        json.loads(text)
    except ValueError as e:
        raise error(path, f"is not valid JSON: {e}", "Fix the JSON syntax there") from None

    def value(m):
        if m.group(1) not in light:
            raise error(path, f"{m.group(0)} names no colour token of style.css",
                        "Use a custom property of :root whose value is a #hex colour")
        return light[m.group(1)]
    return VAR.sub(value, text), path


def _fonts():
    """What the theme's fonts are, for the key: name and size of each."""
    folder = THEME / "fonts"
    return [(f.name, f.stat().st_size) for f in sorted(folder.glob("*"))] if folder.is_dir() else []


# --- drawing --------------------------------------------------------------------

def draw(source, src):
    """The path from the site root of the diagram's SVG ("diagrams/<key>.svg"),
    or None when no renderer is installed. `src` is the page, for messages."""
    path, version = command()
    if path is None:
        _say("none", None, f"no {os.environ.get('TILDER_MMDC', 'mmdc')} (the Mermaid CLI): "
             "diagrams are shown as their source",
             "Build with tilder's -mermaid image, or install @mermaid-js/mermaid-cli")
        return None
    light, dark = palette()
    look = settings()
    config, config_path = mermaid_config(light)
    key = hashlib.sha256(json.dumps(
        [VERSION, source, config, version, _fonts(), light, dark, look],
        sort_keys=True).encode()).hexdigest()[:20]
    name = f"{FOLDER}/{key}.svg"
    svg = MEMORY.get(key) or _cached(key, name)
    if svg is None:
        raw = _render(path, source, config, src)
        svg, unknown = fit(raw, light, dark, look)
        if unknown and config_path is not None:
            _say(("colours", tuple(unknown)), config_path,
                 f"diagram colours left as they are: {' '.join(unknown)}",
                 f"Map each to a token under [diagrams] fold in {THEME_TOML.name}")
        _store(key, svg)
    MEMORY[key] = svg
    FILES[name] = svg
    return name


def _cache_dir():
    if os.environ.get("TILDER_CACHE"):
        return pathlib.Path(os.environ["TILDER_CACHE"]) / "mermaid"
    return pathlib.Path(tempfile.gettempdir()) / "tilder-mermaid"


def _cached(key, name):
    """A drawing made by an earlier process: the cache folder, else the
    previous build's output."""
    places = [_cache_dir() / f"{key}.svg"]
    if STATE.get("out"):
        places.append(pathlib.Path(STATE["out"]) / name)
    for p in places:
        try:
            return p.read_text()
        except OSError:
            continue
    return None


def _store(key, svg):
    try:
        d = _cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f".{key}.tmp"
        tmp.write_text(svg)
        os.replace(tmp, d / f"{key}.svg")
    except OSError:
        pass        # a read-only cache: the memory one still serves --watch


def _render(path, source, config, src):
    """The Mermaid CLI's SVG for `source`, as text."""
    from images import _fontconfig  # the theme's fonts, as TTF, for fontconfig
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / "in.mmd").write_text(source)
        (d / "config.json").write_text(config)
        # A container has no user namespace for Chromium's sandbox; the
        # page drawn is the site's own source, never a visitor's.
        (d / "puppeteer.json").write_text(json.dumps({"args": ["--no-sandbox", "--disable-gpu"]}))
        env = dict(os.environ, FONTCONFIG_FILE=_fontconfig())
        env.setdefault("HOME", tmp)
        cmd = [path, "-q", "-i", str(d / "in.mmd"), "-o", str(d / "out.svg"),
               "-c", str(d / "config.json"), "-p", str(d / "puppeteer.json"), "-b", "transparent"]
        try:
            run = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise error(src, f"a mermaid diagram took more than {TIMEOUT} s to draw",
                        "Simplify it, or check that the Mermaid CLI runs") from None
        out = d / "out.svg"
        if run.returncode != 0 or not out.is_file():
            lines = [l.strip() for l in (run.stderr or run.stdout).splitlines() if l.strip()]
            said = next((l for l in lines if "rror" in l), lines[0] if lines else "no output")
            raise error(src, f"a mermaid diagram cannot be drawn: {said}",
                        "Fix its source (the syntax: https://mermaid.js.org/)")
        return out.read_text()


# --- fitting the drawing to the theme -------------------------------------------

def fit(raw, light, dark, look):
    """(svg, unknown): Mermaid's SVG with its colours as tokens, its size
    fixed, corners squared and shadows dropped as the theme says; the
    colours no token matched."""
    lookup = {}
    for name, value in light.items():
        lookup.setdefault(_long(value), name)
    lookup.update({k: v for k, v in look["fold"].items() if v in light})
    used, unknown = set(), set()

    def var(m):
        name = lookup.get(_long(m.group(0)))
        if name is None:
            if light:
                unknown.add(m.group(0).upper())
            return m.group(0)
        used.add(name)
        return f"var({name})"

    root = ET.fromstring(raw)
    for el in list(root.iter()):
        tag = el.tag.split("}")[-1]
        # A presentation attribute cannot hold var(): the colour moves to style.
        moved = []
        for attr in ("fill", "stroke", "stop-color", "color", "flood-color"):
            value = el.get(attr)
            if value and HEX.fullmatch(value.strip()):
                moved.append(f"{attr}:{HEX.sub(var, value.strip())}")
                del el.attrib[attr]
        style = HEX.sub(var, el.get("style", ""))
        if moved:
            style = ";".join(moved) + (";" + style if style else "")
        if style:
            el.set("style", style)
        if look["sharp"]:
            for attr in ("rx", "ry"):
                if attr in el.attrib:
                    el.set(attr, "0")
        if not look["shadow"]:
            el.attrib.pop("filter", None)
        if tag == "style" and el.text:
            text = HEX.sub(var, el.text)
            if look["sharp"]:
                text = re.sub(r"\b(rx|ry)\s*:\s*[^;}]+", r"\1:0", text)
            if not look["shadow"]:
                text = re.sub(r"filter\s*:\s*[^;}]+;?", "", text)
            el.text = text
    if not look["shadow"]:
        for parent in list(root.iter()):
            for child in list(parent):
                if child.tag.split("}")[-1] == "filter":
                    parent.remove(child)
    _size(root)
    if used:
        names = [n for n in light if n in used]
        css = ":root{" + ";".join(f"{n}:{light[n]}" for n in names) + "}"
        if any(n in dark for n in names):
            css += ("@media (prefers-color-scheme: dark){:root{"
                    + ";".join(f"{n}:{dark[n]}" for n in names if n in dark) + "}}")
        style = ET.Element(f"{{{SVG}}}style")
        style.text = css
        root.insert(0, style)
    return ET.tostring(root, encoding="unicode") + "\n", sorted(unknown)


def _long(colour):
    """#abc -> #AABBCC; #aabbcc -> #AABBCC."""
    c = colour.upper()
    return "#" + "".join(ch * 2 for ch in c[1:]) if len(c) == 4 else c


def _size(root):
    """The drawing at its natural size: width and height from the viewBox,
    instead of Mermaid's width="100%" and max-width, so the page can write
    them on the <img> and never stretch it."""
    box = root.get("viewBox", "").replace(",", " ").split()
    if len(box) != 4:
        return
    try:
        w, h = float(box[2]), float(box[3])
    except ValueError:
        return
    root.set("width", f"{w:g}")
    root.set("height", f"{h:g}")
    style = re.sub(r"max-width\s*:\s*[^;]+;?\s*", "", root.get("style", "")).strip()
    if style:
        root.set("style", style)
    else:
        root.attrib.pop("style", None)


def size(name):
    """(width, height) of a drawing of this build, rounded."""
    m = re.search(r'<svg[^>]*\swidth="([\d.]+)"[^>]*\sheight="([\d.]+)"', FILES.get(name, ""))
    return (round(float(m.group(1))), round(float(m.group(2)))) if m else None


# --- the pages' diagram blocks ---------------------------------------------------

def draw_all(nodes, src):
    """Draw every diagram block of a page; warn once about one without a
    description. Each block gets "svg": its path, or None."""
    for n in nodes:
        if n["k"] == "diagram":
            if not n["alt"].strip():
                _say(("alt", str(src), "\n".join(n["lines"])), src,
                     "a mermaid diagram without a description",
                     'Describe it after the word mermaid: ```mermaid What the diagram shows')
            n["svg"] = draw("\n".join(n["lines"]) + "\n", src)
        draw_all(n.get("blocks", []), src)


def outputs():
    """{path: SVG text} of this build's drawings."""
    return dict(FILES)

