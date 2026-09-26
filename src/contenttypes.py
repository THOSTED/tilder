"""Content types: the modules that say what a kind of content is.

A type is one Python module - types/<name>.py here, theme/types/<name>.py in
a theme - with the interface docs/types.md describes: NAME, a few flags, and
functions that turn an item into nodes of the tree (a card), a schema.org
node, a feed item, extra files. The built-in types are written exactly as a
theme would write one; a theme module with the same NAME replaces one.

This module loads and validates them (load), declares the collections of
site.toml (collections), reads their items (load_items) and fills the lists
that section markers ask for (fill_lists).
"""

import copy
import importlib.util

from config import BUILDER, THEME
from report import error, fail, rel

BUILTIN = BUILDER / "types"

TYPES = {}     # NAME -> module, in load order; updated after each folder
MARKERS = {}   # section marker word -> NAME of the type that lists it

# Attributes a type may leave out, with their defaults. LAYOUT None means
# "the type's NAME".
FLAGS = {"DATED": False, "ARTICLE": False, "OG_TYPE": "website", "SCRIPT": "",
         "LAYOUT": None, "DEFAULTS": {}, "MARKERS": {}}
# Functions a type may leave out, with what the build does then.
HOOKS = {
    "defaults": lambda item, conf: None,
    "sort_key": lambda item, conf: item["slug"],
    "json_ld": lambda item, conf: None,
    "feed_item": lambda item, conf: None,
    "meta_tags": lambda item, conf: [],
    "outputs": lambda items, conf: {},
    "list_data": lambda conf: {},
}


def _import(path, tag):
    """Import a type file under a private name: a theme's event.py must
    shadow nothing on sys.path."""
    spec = importlib.util.spec_from_file_location(f"_tilder_type_{tag}_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check(module, path):
    """Every problem of a freshly imported type module, as a list."""
    errs = []
    name = getattr(module, "NAME", None)
    if not isinstance(name, str) or not name.isidentifier():
        errs.append(error(path, 'NAME must be a string and a valid identifier, like "talk"',
                          "Set NAME at the top of the module"))
    if not callable(getattr(module, "entry", None)):
        errs.append(error(path, "entry(item, link, conf) is missing",
                          "Every type defines entry: it returns an entry node, or None"))
    for attr, default in FLAGS.items():
        value = getattr(module, attr, default)
        kind = str if default is None else type(default)
        if value is not None and not isinstance(value, kind):
            errs.append(error(path, f"{attr} must be a {kind.__name__}, not a {type(value).__name__}"))
    for hook in HOOKS:
        if hasattr(module, hook) and not callable(getattr(module, hook)):
            errs.append(error(path, f"{hook} must be a function"))
    markers = getattr(module, "MARKERS", {})
    if isinstance(markers, dict):
        for word, fn in markers.items():
            if not callable(fn):
                errs.append(error(path, f'MARKERS["{word}"] must be a function'))
    return errs


def _complete(module, path):
    """Fill what the module left out, so the build never tests for it."""
    module.HAS_FEED = hasattr(module, "feed_item")
    for attr, default in FLAGS.items():
        if not hasattr(module, attr):
            setattr(module, attr, copy.deepcopy(default))
    if module.LAYOUT is None:
        module.LAYOUT = module.NAME
    for hook, fn in HOOKS.items():
        if not hasattr(module, hook):
            setattr(module, hook, fn)
    module.PATH = path
    return module


def load(dirs=None):
    """Load the type modules: the generator's types/, then theme/types/ (or
    `dirs`, in order). A later folder replaces an earlier type of the same
    NAME. Every problem is reported before the build stops."""
    dirs = [BUILTIN, THEME / "types"] if dirs is None else list(dirs)
    TYPES.clear()
    MARKERS.clear()
    errs = []
    for n, folder in enumerate(dirs):
        seen = {}  # NAME -> path, within this folder
        for path in sorted(folder.glob("*.py")) if folder.is_dir() else []:
            if path.name.startswith("_"):
                continue
            try:
                module = _import(path, n)
            except Exception as e:  # a SyntaxError, an import that fails...
                errs.append(error(path, f"cannot be imported: {e.__class__.__name__}: {e}",
                                  "Run with --debug for the traceback", exc=e))
                continue
            bad = _check(module, path)
            if bad:
                errs.extend(bad)
                continue
            if module.NAME in seen:
                errs.append(error(path, f'NAME "{module.NAME}" is also the name of {rel(seen[module.NAME])}',
                                  "Two types in one folder cannot share a name"))
                continue
            seen[module.NAME] = path
            TYPES[module.NAME] = _complete(module, path)
    claimed = {}
    for name, module in TYPES.items():
        for word in module.MARKERS:
            if word in claimed:
                other = TYPES[claimed[word]]
                errs.append(error(module.PATH,
                                  f'MARKERS["{word}"] is already claimed by type "{other.NAME}" ({rel(other.PATH)})',
                                  f'Rename the marker, or replace that type by naming yours "{other.NAME}"'))
            claimed.setdefault(word, name)
    if errs:
        TYPES.clear()
        fail(errs)
    MARKERS.update(claimed)
    return dict(TYPES)
