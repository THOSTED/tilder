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
ASSETS = ROOT / "assets"
EXTRA = [p for p in [ROOT / "LICENSE"] if p.is_file()]  # served as-is at the root
CONFIG = CONTENT / "site.toml"
WIDTH = 75  # text mirror: fits an 80-column terminal with room to spare
INDENT = 5
# A dated item: a blog post or an event, as `NAME.md` or `NAME/index.md`
# (a folder, to keep its images next to it).
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9-]+$")
COLLECTIONS = ("blog", "events")

# Files read by the build, never served. The theme's are replaced by the
# project's own copy in assets/, if it has one.
TEMPLATES = ("layout.html", "share.svg")

# content/site.toml over builder/defaults.toml, re-read at every build (see
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


def layout():
    """theme/layout.html, the one file a theme must have."""
    path = theme_file("layout.html")
    if not path.is_file():
        raise SystemExit(f"no {THEME}/layout.html: a site needs a theme - "
                         "copy builder/starter/theme/ to begin")
    return path.read_text()


def _merge(base, over):
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config():
    with DEFAULTS.open("rb") as f:
        data = tomllib.load(f)
    with CONFIG.open("rb") as f:
        _merge(data, tomllib.load(f))
    CFG.clear()
    CFG.update(data)
    CFG["site"]["updated"] = str(CFG["site"]["updated"])


def apex():
    return CFG["site"]["url"].rstrip("/")


def rfc822(iso):
    return datetime.date.fromisoformat(iso).strftime("%a, %d %b %Y 00:00:00 +0000")
