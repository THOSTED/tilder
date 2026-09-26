"""Paths, site.toml, and the state one build shares.

The builder serves any project laid out like this one:

    <root>/content/     the pages and content/site.toml
    <root>/theme/       the site's theme: layout.html (required), style.css,
                        scripts, fonts, icons, share.svg (docs/theme.md)
    <root>/assets/      the project's files, served as-is: logo.svg...

<root> is --root (set as SITE_ROOT by build.py), else the current directory
when it has a content/ folder, else the folder that holds builder/.
"""

import datetime
import os
import pathlib
import re
import tomllib

BUILDER = pathlib.Path(__file__).resolve().parent.parent   # the generator's root
DEFAULTS = BUILDER / "defaults.toml"


def _root():
    if os.environ.get("SITE_ROOT"):
        return pathlib.Path(os.environ["SITE_ROOT"]).resolve()
    cwd = pathlib.Path.cwd()
    return cwd if (cwd / "content").is_dir() else BUILDER.parent


ROOT = _root()
CONTENT = ROOT / "content"
THEME = ROOT / "theme"             # the site's own theme (builder/starter/theme to begin)
THEME_TOML = THEME / "theme.toml"
ASSETS = ROOT / "assets"
EXTRA = [p for p in [ROOT / "LICENSE"] if p.is_file()]  # served as-is at the root
CONFIG = CONTENT / "site.toml"
WIDTH = 75  # text mirror: fits an 80-column terminal with room to spare
INDENT = 5
# A dated item: a blog post or an event, as `NAME.md` or `NAME/index.md`
# (a folder, to keep its images next to it).
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9-]+$")

# Files of the theme (and of assets/, which may override them) read by the
# build and never served.
UNSERVED = ("layout.html", "share.svg", "theme.toml")
UNSERVED_DIRS = ("icons/", "layouts/", "types/")

# content/site.toml over theme/theme.toml over builder/defaults.toml, re-read at every build (see
# load_config). Every user-facing string and site-wide value comes from
# there: the builder holds none. Mutated in place, so `from config import
# CFG` stays valid.
CFG = {}

# What one build shares: the date that decides upcoming and past events.
STATE = {"today": ""}


def theme_file(name):
    """A theme file: the one in assets/ if there is one, else theme/. The
    path may not exist: every theme file but layout.html is optional."""
    own = ASSETS / name
    return own if own.is_file() else THEME / name


def served(rel):
    """Is this theme- or assets-relative path a file to serve as-is?"""
    return rel not in UNSERVED and not rel.startswith(UNSERVED_DIRS)


def layout(name=None, asked_by=None):
    """(path, text) of the layout to fill: theme/layouts/<name>.html when
    the theme has it, else layout.html. A name the front matter asked for
    (asked_by: the page's file) must exist; a type's LAYOUT may not."""
    from report import error  # config is imported by report
    if name:
        path = theme_file(f"layouts/{name}.html")
        if path.is_file():
            return path, path.read_text()
        if asked_by is not None:
            raise error(asked_by, f'layout "{name}" names no theme/layouts/{name}.html',
                        "Add that file to the theme, or drop `layout:`")
    path = theme_file("layout.html")
    if not path.is_file():
        raise error(THEME, "no layout.html: a site needs a theme",
                    "Copy starter/theme/ to begin")
    return path, path.read_text()


def _merge(base, over):
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config():
    """defaults.toml, then the theme's theme.toml if it has one, then the
    site's content/site.toml: the site has the last word."""
    with DEFAULTS.open("rb") as f:
        data = tomllib.load(f)
    if THEME_TOML.is_file():
        with THEME_TOML.open("rb") as f:
            _merge(data, tomllib.load(f))
    with CONFIG.open("rb") as f:
        _merge(data, tomllib.load(f))
    CFG.clear()
    CFG.update(data)
    CFG["site"]["updated"] = str(CFG["site"]["updated"])


def apex():
    return CFG["site"]["url"].rstrip("/")


def rfc822(iso):
    return datetime.date.fromisoformat(iso).strftime("%a, %d %b %Y 00:00:00 +0000")
