"""Image dimensions, read from the file itself: no dependency."""

import pathlib
import re
import struct


def image_size(path):
    """(width, height) of a PNG, GIF, JPEG, WebP or SVG, else None. Written
    on the <img> so the page does not jump while the image loads."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8X":
            w = int.from_bytes(data[24:27], "little") + 1
            return w, int.from_bytes(data[27:30], "little") + 1
        if data[12:16] == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, size = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + size
    if path.suffix == ".svg":
        head = data[:2000].decode("utf-8", "replace")
        w = re.search(r'<svg[^>]*\swidth="([\d.]+)', head)
        h = re.search(r'<svg[^>]*\sheight="([\d.]+)', head)
        if w and h:
            return round(float(w.group(1))), round(float(h.group(1)))
        vb = re.search(r'viewBox="[\d.-]+[ ,]+[\d.-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', head)
        if vb:
            return round(float(vb.group(1))), round(float(vb.group(2)))
    return None


# --- rasterising: icons and the share preview, made at every build ----------

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

from config import THEME

_cache = {}
_warned = []


def _fontconfig():
    """A fontconfig file that knows the theme's fonts, so rendered text uses
    the site's own typeface (JetBrains Mono). The renderer shapes text with
    HarfBuzz, which cannot read WOFF2: each font is decompressed to TTF in a
    temporary folder, with woff2_decompress when it is installed."""
    d = pathlib.Path(tempfile.gettempdir()) / "site-builder-fonts"
    d.mkdir(exist_ok=True)
    if shutil.which("woff2_decompress"):
        fonts = d / "ttf"
        fonts.mkdir(exist_ok=True)
        for src in (THEME / "fonts").glob("*.woff2"):
            ttf = fonts / (src.stem + ".ttf")
            if not ttf.is_file() or ttf.stat().st_mtime < src.stat().st_mtime:
                copy = fonts / src.name
                copy.write_bytes(src.read_bytes())
                subprocess.run(["woff2_decompress", str(copy)], capture_output=True, check=True)
                copy.unlink()  # only the TTF: fontconfig must not pick the WOFF2
    else:
        fonts = THEME / "fonts"
    conf = d / "fonts.conf"
    conf.write_text(f'<?xml version="1.0"?>\n<fontconfig><dir>{fonts}</dir>'
                    f'<include ignore_missing="yes">/etc/fonts/fonts.conf</include>'
                    f"<cachedir>{d}</cachedir></fontconfig>\n")
    return str(conf)


def rasterize(svg, width, height):
    """PNG bytes of an SVG at width x height, or None when no renderer is
    installed (the build warns once and goes on). rsvg-convert first: it
    renders text with the theme's fonts. The builder's Docker image has it."""
    key = (hashlib.sha256(svg).hexdigest(), width, height)
    if key in _cache:
        return _cache[key]
    env = dict(os.environ, FONTCONFIG_FILE=_fontconfig())
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-w", str(width), "-h", str(height), "-f", "png"]
    elif shutil.which("magick"):
        cmd = ["magick", "-background", "none", "-density", "384", "svg:-",
               "-resize", f"{width}x{height}!", "png:-"]
    else:
        if not _warned:
            print("warning: no rsvg-convert or magick: icons and share.png not made",
                  file=sys.stderr)
            _warned.append(True)
        return None
    png = subprocess.run(cmd, input=svg, capture_output=True, env=env, check=True).stdout
    _cache[key] = png
    return png


def ico(pngs):
    """A .ico holding PNG images (Windows Vista and later, every browser):
    a 6-byte header, a 16-byte entry per image, then the images."""
    head = struct.pack("<HHH", 0, 1, len(pngs))
    entries, data, offset = b"", b"", 6 + 16 * len(pngs)
    for size, png in pngs:
        s = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(png), offset)
        data += png
        offset += len(png)
    return head + entries + data
