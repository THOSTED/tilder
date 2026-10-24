"""Static maps on event pages: with [maps] enabled and an event's lat and
lon, a few tiles fetched at build time, composed with a marker into
maps/<key>.png, shown in a figure that links to OpenStreetMap, with the
attribution. The network is mocked: the tile URL template is a file://
one, and a fake rsvg-convert first on PATH answers with fixed bytes.
Builds run on an edited copy of the fixture in a subprocess."""

import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zlib

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
from config import BUILDER
import images
import maps

FIXTURE = pathlib.Path(__file__).resolve().parent / "site"
EVENT = "events/2099-01-01-future-meetup"

FAKE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import os, sys
    svg = sys.stdin.buffer.read()
    if b"data:image/png;base64," in svg:
        open(os.environ["FAKE_LOG"], "a").write("map\\n")
    sys.stdout.buffer.write(b"\\x89PNG\\r\\n\\x1a\\nfake")
    ''')


def png(width, height, pixels):
    """An 8-bit RGBA PNG; pixels: rows of (r, g, b, a)."""
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in pixels)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def enable(**keys):
    def edit(site):
        lines = "\n".join(f"{k} = {v!r}".replace("'", '"') if isinstance(v, str) else f"{k} = {str(v).lower()}"
                          for k, v in {"enabled": True, **keys}.items())
        with (site / "content" / "site.toml").open("a") as f:
            f.write(f"\n[maps]\n{lines}\n")
    return edit


def coordinates(site):
    """The fixture's event has lat: 45.75 and lon: 4.85 already."""


def no_coordinates(site):
    p = site / "content" / f"{EVENT}.md"
    p.write_text(p.read_text().replace("lat: 45.75\nlon: 4.85\n", "", 1))


def build(*edits, cache=None, tiles=True, tile_dir=None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        site = tmp / "site"
        shutil.copytree(FIXTURE, site, ignore=shutil.ignore_patterns("__pycache__"))
        tile_dir = tile_dir or tmp / "tiles"
        if tiles:
            for z, x, y in [(16, x, y) for x, y, *_ in maps.tiles(45.75, 4.85, 16, 720, 360)]:
                (tile_dir / str(z) / str(x)).mkdir(parents=True, exist_ok=True)
                (tile_dir / str(z) / str(x) / f"{y}.png").write_bytes(b"tile")
        for edit in edits:
            edit(site, tile_dir) if edit.__code__.co_argcount == 2 else edit(site)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "rsvg-convert").write_text(FAKE)
        (bin_dir / "rsvg-convert").chmod(0o755)
        log = tmp / "log"
        log.write_text("")
        env = {**os.environ, "SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15",
               "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
               "TILDER_CACHE": str(cache or tmp / "cache"), "FAKE_LOG": str(log),
               "TILDER_D2": str(tmp / "no-d2")}
        run = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                              "--out", str(site / "out")], capture_output=True, text=True, env=env)
        out = {str(p.relative_to(site / "out")): p.read_bytes() for p in (site / "out").rglob("*") if p.is_file()}
        return run, out, log.read_text().split()


def file_tiles(site, tile_dir):
    with (site / "content" / "site.toml").open("a") as f:
        f.write(f'tiles = "file://{tile_dir}/{{z}}/{{x}}/{{y}}.png"\n')


class Geometry(unittest.TestCase):
    def test_the_point_is_the_centre(self):
        x, y = maps.pixel(0, 0, 1)
        self.assertEqual((x, y), (256, 256))

    def test_a_handful_of_tiles_cover_the_window(self):
        ts = maps.tiles(45.7813865, 4.8744488, 16, 720, 360)
        self.assertLessEqual(len(ts), 12)
        self.assertGreaterEqual(len(ts), 6)
        self.assertLessEqual(min(left for *_, left, _ in ts), 0)
        self.assertLessEqual(min(top for *_, top in ts), 0)
        self.assertGreaterEqual(max(left for *_, left, _ in ts) + 256, 720)
        self.assertGreaterEqual(max(top for *_, top in ts) + 256, 360)

    def test_never_guessed(self):
        for meta in ({}, {"lat": "45.7"}, {"lat": "x", "lon": "4"}, {"lat": "91", "lon": "4"}):
            self.assertIsNone(maps.coordinates(meta), meta)
        self.assertEqual(maps.coordinates({"lat": "45.5", "lon": 4}), (45.5, 4.0))


class Palette(unittest.TestCase):
    def test_few_colours_become_an_indexed_png_with_the_same_pixels(self):
        colours = [(255, 0, 0, 255), (0, 128, 0, 255), (0, 0, 255, 128)]
        pixels = [[colours[(x + y) % 3] for x in range(64)] for y in range(32)]
        source = png(64, 32, pixels)
        out = images.palette_png(source)
        chunks = dict(images._chunks(out))
        self.assertEqual(struct.unpack(">IIBB", chunks[b"IHDR"][:10]), (64, 32, 8, 3))
        palette = [chunks[b"PLTE"][i:i + 3] for i in range(0, len(chunks[b"PLTE"]), 3)]
        alpha = chunks.get(b"tRNS", b"") + b"\xff" * 256
        data = zlib.decompress(chunks[b"IDAT"])
        got = [[tuple(palette[data[y * 65 + 1 + x]]) + (alpha[data[y * 65 + 1 + x]],) for x in range(64)]
               for y in range(32)]
        self.assertEqual(got, pixels)
        self.assertLess(len(out), len(source) + 1)

    def test_anything_else_is_kept(self):
        self.assertEqual(images.palette_png(b"not a png"), b"not a png")


class Built(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result, cls.out, cls.calls = build(enable(), file_tiles, coordinates)
        assert cls.result.returncode == 0, cls.result.stderr

    def test_the_event_shows_its_map(self):
        html = self.out[f"{EVENT}.html"].decode()
        m = re.search(r'<figure class="figure map"><a href="https://www\.openstreetmap\.org/\?mlat=45\.75'
                      r'&amp;mlon=4\.85#map=17/45\.75/4\.85"[^>]*><img src="\.\./(maps/[0-9a-f]{20}'
                      r'\.png)" alt="Map of Library, Springfield" width="720" height="360" loading="lazy" '
                      r'decoding="async"></a><figcaption><a href="https://www\.openstreetmap\.org/copyright"'
                      r'[^>]*>© OpenStreetMap contributors', html)
        self.assertIsNotNone(m, html)
        self.assertIn(m.group(1), self.out)
        self.assertEqual(self.calls, ["map"])          # drawn once, for both languages

    def test_the_text_mirror_is_unchanged(self):
        self.assertNotIn("contributors", self.out[f"txt/{EVENT}.txt"].decode())

    def test_no_request_from_the_page(self):
        html = self.out[f"{EVENT}.html"].decode()
        self.assertNotRegex(html, r'(src|srcset)="https?://')


class Choices(unittest.TestCase):
    def test_off_by_default(self):
        run, out, calls = build(coordinates)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("figure map", out[f"{EVENT}.html"].decode())
        self.assertFalse([p for p in out if p.startswith("maps/")])

    def test_no_coordinates_no_map(self):
        run, out, calls = build(enable(), file_tiles, no_coordinates)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("figure map", out[f"{EVENT}.html"].decode())
        self.assertEqual(calls, [])

    def test_a_failed_fetch_warns_and_keeps_the_link(self):
        run, out, _ = build(enable(), file_tiles, coordinates, tiles=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr.count("no map: the tiles cannot be fetched"), 1, run.stderr)
        self.assertIn(f"warning: content/{EVENT}.md: no map", run.stderr)
        html = out[f"{EVENT}.html"].decode()
        self.assertNotIn("figure map", html)
        self.assertIn("openstreetmap.org/?mlat=", html)

    def test_tiles_are_fetched_once(self):
        with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as server:
            tile_dir = pathlib.Path(server) / "tiles"
            first = build(enable(), file_tiles, coordinates, cache=pathlib.Path(cache), tile_dir=tile_dir)
            shutil.rmtree(tile_dir)     # the second build has no tile server at all: the cache serves
            second = build(enable(), file_tiles, coordinates, cache=pathlib.Path(cache), tiles=False,
                           tile_dir=tile_dir)
            cached = list((pathlib.Path(cache) / "maps" / "tiles").glob("*.png"))
        self.assertEqual(first[0].returncode, 0, first[0].stderr)
        self.assertEqual(second[0].returncode, 0, second[0].stderr)
        self.assertNotIn("no map", second[0].stderr)
        self.assertIn("figure map", second[1][f"{EVENT}.html"].decode())
        self.assertTrue(6 <= len(cached) <= 12, len(cached))


class Agent(unittest.TestCase):
    def test_the_user_agent_names_tilder_and_the_site(self):
        import config
        saved = config.CFG.get("site")
        config.CFG["site"] = {"url": "https://test.example"}
        try:
            self.assertRegex(maps.user_agent(), r"^tilder/\S+ \(\+https://test\.example\)$")
        finally:
            if saved is None:
                config.CFG.pop("site")
            else:
                config.CFG["site"] = saved


if __name__ == "__main__":
    unittest.main()
