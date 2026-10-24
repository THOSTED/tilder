"""D2 diagrams: a ```d2 block drawn at build time into an SVG file,
diagrams/<key>.svg at the site root, shown by the page as an <img>.

The drawing is the D2 CLI's (`d2`, or the command TILDER_D2 names), an
outside tool like rsvg-convert: a single binary, no browser. Without it,
the build warns once and the page shows the diagram's source, with its
description. The theme gives the look, in theme.toml:

    [diagrams]       layout (dagre, elk), pad, the font files of fonts/
    [diagrams.d2]    D2's colour codes (N1..N7, B1..B6, AA2.., AB4..) ->
                     custom properties of style.css

Each code takes its token's light value in D2's theme-overrides, and its
dark value in dark-theme-overrides: D2 writes both into the SVG, under
prefers-color-scheme, so the figure follows the reader's scheme like the
page does. The fonts are embedded by D2 itself.

A {text} code block right after a {html} d2 block is the diagram's
drawing for the text mirror, never shown on the web page; it must be
ASCII and fit the mirror (draw_all warns).

A drawing is cached by a key of everything it depends on (source,
configuration, colours, fonts, the renderer's version): in memory, in
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

from config import CFG, INDENT, STATE, THEME, THEME_TOML, WIDTH, theme_file
from report import error, warning

VERSION = 2             # of the configuration written below: part of the key
FOLDER = "diagrams"     # where the SVGs land, at the site root
TIMEOUT = 60            # seconds for one drawing
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")
CODE = re.compile(r"^(N[1-7]|B[1-6]|AA[245]|AB[45])$")
LAYOUTS = ("dagre", "elk")
FONTS = ("regular", "italic", "bold", "semibold")
# A drawing for the text mirror sits in a code frame: the section's indent,
# then two spaces inside the frame; an entry's blocks four columns deeper.
FRAME_WIDTH = WIDTH - INDENT - 2

MEMORY = {}     # key -> SVG text, for the life of the process (--watch)
FILES = {}      # this build's drawings: "diagrams/<key>.svg" -> SVG text
_said = set()   # warnings already given in this build
_renderer = {}  # the command and its version, found once per process


def reset():
    """Before each build."""
    FILES.clear()
    _said.clear()


def command():
    """(path, version) of the D2 CLI; path None when it is not installed."""
    name = os.environ.get("TILDER_D2", "d2")
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
    style.css; dark is {} when the theme has no dark scheme."""
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
    """[diagrams] of the configuration, checked: (layout, pad, {code:
    token}, {font: path})."""
    conf = CFG.get("diagrams", {})
    layout = conf.get("layout", "dagre")
    if layout not in LAYOUTS:
        raise error(THEME_TOML, f"[diagrams] layout is {json.dumps(layout)}, not a layout D2 ships",
                    f"Write one of {', '.join(LAYOUTS)}")
    pad = conf.get("pad", 16)
    if not isinstance(pad, int) or isinstance(pad, bool) or pad < 0:
        raise error(THEME_TOML, f"[diagrams] pad is {pad!r}", "Write a number of pixels, like 16")
    codes = conf.get("d2", {})
    if not isinstance(codes, dict) or not all(
            isinstance(k, str) and CODE.match(k) and isinstance(v, str) and v.startswith("--")
            for k, v in codes.items()):
        raise error(THEME_TOML, "[diagrams.d2] must map D2's colour codes to tokens",
                    'Write N1 = "--fg", with codes N1-N7, B1-B6, AA2, AA4, AA5, AB4, AB5')
    fonts = {}
    for name in FONTS:
        file = conf.get(f"font_{name}", "")
        if file:
            path = THEME / "fonts" / file
            if not path.is_file():
                raise error(THEME_TOML, f"[diagrams] font_{name} names no file of theme/fonts/: {file}",
                            "Name a .woff2, .ttf or .otf file of the theme's fonts/")
            fonts[name] = path
    if "bold" in fonts:
        fonts.setdefault("semibold", fonts["bold"])
    if "regular" in fonts:
        fonts.setdefault("italic", fonts["regular"])
    return layout, pad, codes, fonts


def d2_config(layout, pad, codes, light, dark):
    """The `vars: { d2-config: ... }` block appended to every source: the
    layout, the padding, theme 0 and its overrides, the dark theme 200 and
    its overrides when the theme has a dark scheme (D2 applies the dark
    overrides only with a dark theme)."""
    for code, token in codes.items():
        if token not in light:
            raise error(THEME_TOML, f'[diagrams.d2] {code} = "{token}" names no colour token of style.css',
                        "Use a custom property of :root whose value is a #hex colour")
    lines = ["vars: {", "  d2-config: {", f"    layout-engine: {layout}", f"    pad: {pad}",
             "    theme-id: 0"]
    if codes:
        lines.append("    theme-overrides: {")
        lines += [f'      {code}: "{light[token]}"' for code, token in codes.items()]
        lines.append("    }")
    if dark:
        lines.append("    dark-theme-id: 200")
        dark_codes = {c: t for c, t in codes.items() if t in dark}
        if dark_codes:
            lines.append("    dark-theme-overrides: {")
            lines += [f'      {code}: "{dark[token]}"' for code, token in dark_codes.items()]
            lines.append("    }")
    return "\n".join(lines + ["  }", "}"]) + "\n"


def _ttf(path):
    """A font D2 can read: a .ttf or .otf as it is; a .woff2 decompressed
    to TTF, as for share.png (images._fontconfig); None without a
    decompressor."""
    if path.suffix.lower() in (".ttf", ".otf"):
        return path
    from images import _fontconfig
    _fontconfig()
    ttf = pathlib.Path(tempfile.gettempdir()) / "site-builder-fonts" / "ttf" / (path.stem + ".ttf")
    return ttf if ttf.is_file() else None


# --- drawing --------------------------------------------------------------------

def draw(source, src):
    """The path from the site root of the diagram's SVG ("diagrams/<key>.svg"),
    or None when no renderer is installed. `src` is the page, for messages."""
    path, version = command()
    if path is None:
        _say("none", None, f"no {os.environ.get('TILDER_D2', 'd2')} (the D2 CLI): "
             "diagrams are shown as their source",
             "Build with tilder's image, or install D2 (https://d2lang.com)")
        return None
    light, dark = palette()
    layout, pad, codes, fonts = settings()
    config = d2_config(layout, pad, codes, light, dark)
    ttfs = {}
    for name, font in fonts.items():
        ttf = _ttf(font)
        if ttf is None:
            _say(("font", name), THEME_TOML,
                 f"[diagrams] font_{name} cannot be read without woff2_decompress",
                 "Install it (tilder's image has it), or name a .ttf file: D2 draws with its own font")
        else:
            ttfs[name] = ttf
    fonts_key = sorted((n, p.name, p.stat().st_size) for n, p in ttfs.items())
    key = hashlib.sha256(json.dumps([VERSION, source, config, version, fonts_key],
                                    sort_keys=True).encode()).hexdigest()[:20]
    name = f"{FOLDER}/{key}.svg"
    svg = MEMORY.get(key) or _cached(key, name)
    if svg is None:
        svg = _sized(_render(path, source, config, ttfs, src))
        _store(key, svg)
    MEMORY[key] = svg
    FILES[name] = svg
    return name


def _cache_dir():
    if os.environ.get("TILDER_CACHE"):
        return pathlib.Path(os.environ["TILDER_CACHE"]) / "diagrams"
    return pathlib.Path(tempfile.gettempdir()) / "tilder-diagrams"


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


def _render(path, source, config, ttfs, src):
    """The D2 CLI's SVG for `source`, as text. The configuration goes after
    the source, so the line numbers of D2's messages are the source's."""
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / "diagram.d2").write_text(source.rstrip("\n") + "\n\n" + config)
        cmd = [path]
        for name, ttf in ttfs.items():
            cmd += [f"--font-{name}", str(ttf)]
        cmd += [str(d / "diagram.d2"), str(d / "diagram.svg")]
        try:
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT,
                                 env=dict(os.environ, HOME=os.environ.get("HOME") or tmp))
        except subprocess.TimeoutExpired:
            raise error(src, f"a d2 diagram took more than {TIMEOUT} s to draw",
                        "Simplify it, or check that the D2 CLI runs") from None
        out = d / "diagram.svg"
        if run.returncode != 0 or not out.is_file():
            lines = [l.strip() for l in (run.stderr or run.stdout).splitlines() if l.strip()]
            said = next((l for l in lines if "err" in l.lower()), lines[0] if lines else "no output")
            said = re.sub(r"^err:\s*", "", said)
            said = re.sub(r"failed to compile \S+: ", "", said)
            said = said.replace(str(d / "diagram.d2") + ":", "line ").replace(str(d) + "/", "")
            raise error(src, f"a d2 diagram cannot be drawn: {said}",
                        "Fix its source (the syntax: https://d2lang.com/tour/intro)")
        return out.read_text()


def _sized(svg):
    """The drawing at its natural size: D2's outer <svg> has a viewBox but
    no width and height; they are written from it, so the page can give
    the <img> its size and never stretch it."""
    m = re.search(r"<svg\b[^>]*>", svg)
    if not m or re.search(r'\swidth="', m.group(0)):
        return svg
    box = re.search(r'viewBox="([-\d.]+)[ ,]+([-\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)"', m.group(0))
    if not box:
        return svg
    w, h = float(box.group(3)), float(box.group(4))
    tag = m.group(0)[:-1].rstrip("/") + f' width="{w:g}" height="{h:g}">'
    return svg[:m.start()] + tag + svg[m.end():]


def size(name):
    """(width, height) of a drawing of this build, rounded."""
    m = re.search(r"<svg\b[^>]*>", FILES.get(name, ""))
    if not m:
        return None
    w = re.search(r'\swidth="([\d.]+)"', m.group(0))
    h = re.search(r'\sheight="([\d.]+)"', m.group(0))
    return (round(float(w.group(1))), round(float(h.group(1)))) if w and h else None


# --- the pages' diagram blocks ---------------------------------------------------

def draw_all(nodes, src, width=FRAME_WIDTH):
    """Draw every diagram block of a page; warn once about one without a
    description, and about a text drawing that is not ASCII or wider than
    the mirror holds at its place (`width`: an entry's blocks sit four
    columns deeper). Each block gets "svg": its path, or None."""
    for n in nodes:
        if n["k"] == "diagram" and n.get("only") == "text":
            pass            # the mirror's only: its source, nothing to draw
        elif n["k"] == "diagram":
            source = "\n".join(n["lines"]) + "\n"
            if not n["alt"].strip():
                _say(("alt", str(src), source), src, "a d2 diagram without a description",
                     "Describe it after the word d2: ```d2 What the diagram shows")
            for i, line in enumerate(n.get("ascii") or [], 1):
                if any(ord(c) > 127 for c in line):
                    _say(("ascii", str(src), source, i), src,
                         f"the text drawing of a d2 diagram has a character that is not ASCII, "
                         f"line {i}: {line.strip()!r}",
                         "Draw it with ASCII only: the text mirror is ASCII")
                wide = len(line.expandtabs(4).rstrip())
                if wide > width:
                    _say(("wide", str(src), source, i), src,
                         f"the text drawing of a d2 diagram is {wide} columns wide, line {i}; "
                         f"the text mirror holds {width} there",
                         f"Draw it in {width} columns or fewer")
            n["svg"] = draw(source, src)
        draw_all(n.get("blocks", []), src, width - 4 if n["k"] == "entry" else width)


def outputs():
    """{path: SVG text} of this build's drawings."""
    return dict(FILES)
