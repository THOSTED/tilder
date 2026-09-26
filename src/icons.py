"""Icons and the share preview, made at every build - nothing committed.

From the project's assets/logo.svg: favicon.ico (16, 32, 48), the PNG icons
(180, 192, 512). From the theme's share.svg, if it has one, filled from
site.toml: share.png, 1200x630.
"""

import base64
import html as H
import re
import sys
from urllib.parse import urlparse

from config import ASSETS, CFG, theme_file
from images import ico, rasterize

ICONS = (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512))
PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def _fill(template, computed):
    """{{ name }}: a computed value, else a site.toml value, XML-escaped."""
    def value(m):
        name = m.group(1)
        if name in computed:
            return computed[name]
        node = CFG
        for part in name.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ValueError(f"share.svg: unknown placeholder {{{{ {name} }}}}")
            node = node[part]
        return H.escape(str(node))
    return PLACEHOLDER.sub(value, template)


def generated():
    """{output path: bytes} for every icon and the share preview. Empty
    when no SVG renderer is installed (the build has warned)."""
    out = {}
    logo_path = ASSETS / CFG["share"]["logo_svg"]
    if not logo_path.is_file():
        print(f"warning: no {logo_path.name} in assets/: no icons, no share.png",
              file=sys.stderr)
        return out
    logo = logo_path.read_bytes()
    for name, size in ICONS:
        png = rasterize(logo, size, size)
        if png:
            out[name] = png
    small = [(s, rasterize(logo, s, s)) for s in (16, 32, 48)]
    if all(png for _, png in small):
        out["favicon.ico"] = ico(small)

    template = theme_file("share.svg")
    if not template.is_file():  # the theme has no preview: og:image uses the icon
        return out
    card = list(CFG["share"]["card"]) + ["", ""]
    svg = _fill(template.read_text(), {
        "logo": "data:image/svg+xml;base64," + base64.b64encode(logo).decode(),
        "manual_upper": H.escape(CFG["site"]["manual"].upper()),
        # Lowercase, like the wordmark on the page (text-transform in style.css).
        "wordmark": H.escape(CFG["site"]["name"].lower()),
        "domain": H.escape(urlparse(CFG["site"]["url"]).netloc),
        "card_1": H.escape(card[0]),
        "card_2": H.escape(card[1]),
    })
    png = rasterize(svg.encode(), 1200, 630)
    if png:
        out[CFG["share"]["image"]] = png
    return out
