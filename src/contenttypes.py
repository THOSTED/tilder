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
import datetime
import importlib.util

import languages
import paths
from config import BUILDER, CFG, CONFIG, CONTENT, DATED, STATE, THEME
from markdown import front_matter
from report import BuildError, error, fail, rel

BUILTIN = BUILDER / "types"

TYPES = {}     # NAME -> module, in load order; updated after each folder
MARKERS = {}   # section marker word -> NAME of the type that lists it
ERRORS = []    # what load() and collections() found, reported together by check()

# Attributes a type may leave out, with their defaults. LAYOUT None means
# "the type's NAME".
FLAGS = {"DATED": False, "ARTICLE": False, "OG_TYPE": "website", "SCRIPT": "",
         "LAYOUT": None, "DEFAULTS": {}, "MARKERS": {},
         "SEQUENTIAL": False, "LOCALIZED_OUTPUTS": False}
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
    NAME. Problems are gathered in ERRORS, not raised: collections() adds
    its own, and check() reports them all together. A module that cannot
    be imported or fails its checks is left out of TYPES."""
    dirs = [BUILTIN, THEME / "types"] if dirs is None else list(dirs)
    TYPES.clear()
    MARKERS.clear()
    paths.ITEM_FOLDERS.clear()
    ERRORS.clear()
    errs = ERRORS
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
    MARKERS.update(claimed)
    return dict(TYPES)


def check():
    """Stop the build on what load() and collections() gathered."""
    if ERRORS:
        fail(list(ERRORS))


def _loaded():
    """"page, post, event, member (types/), doc (theme/types/doc.py)"."""
    builtin = [n for n, m in TYPES.items() if m.PATH.parent == BUILTIN]
    theme = [f"{n} ({rel(m.PATH)})" for n, m in TYPES.items() if m.PATH.parent != BUILTIN]
    parts = [", ".join(builtin) + " (types/)"] if builtin else []
    return ", ".join(parts + theme)


def collections():
    """{name: settings} of every [collections.<name>] in site.toml, each
    over its type's DEFAULTS, in declaration order. Its problems join
    load()'s, and every one is reported before the build stops."""
    out, errs = {}, ERRORS
    if "members" in CFG:
        errs.append(error(CONFIG, "[members] is no longer read",
                          'Move its keys under [collections.members], with type = "member"'))
    if "collection_defaults" in CFG:
        errs.append(error(CONFIG, "[collection_defaults] is no longer read",
                          "Set a type's words under each [collections.<name>]; "
                          "the defaults live in types/<type>.py"))
    for name, conf in CFG.get("collections", {}).items():
        kind = conf.get("type", "post")
        if kind in ("posts", "events"):
            errs.append(error(CONFIG, f'collection "{name}" has type "{kind}"; types are singular',
                              f'Write type = "{kind[:-1]}"'))
            continue
        if kind not in TYPES:
            errs.append(error(CONFIG, f'collection "{name}" has type "{kind}", which no type defines',
                              f"Types loaded: {_loaded()}"))
            continue
        merged = copy.deepcopy(TYPES[kind].DEFAULTS)
        merged.update(conf)
        merged.setdefault("dir", name)
        merged["type"] = kind
        out[name] = merged
    seen = {}
    for name, conf in out.items():
        d = conf["dir"]
        for other, od in seen.items():
            if d == od or d.startswith(od + "/") or od.startswith(d + "/"):
                errs.append(error(CONFIG, f'collections "{other}" and "{name}" share the folder content/{d}',
                                  "Give each collection its own dir"))
        seen[name] = d
    check()
    return out


def call(path, module, hook, *args, fn=None):
    """Call a type's hook (or `fn`, a marker function, named `hook`); an
    error it raises is reported as the build's own, at `path` (the item's
    file, the page, the collection's folder), naming the type module and
    the hook. The traceback is kept for --debug."""
    try:
        return (fn or getattr(module, hook))(*args)
    except BuildError:
        raise
    except Exception as e:
        raise error(path, f"{rel(module.PATH)}: {hook}() failed: {e.__class__.__name__}: {e}",
                    "Run with --debug for the traceback", exc=e)


def load_items(name, conf):
    """Every item of a collection, in the type's order, as served in the
    current language: <slug>.md, <slug>.<lang>.md, or <slug>/index(.<lang>).md
    in content/<dir>/, the file chosen by the language fallback
    (languages.pick). For a DATED type the slug starts with YYYY-MM-DD.
    Names starting with _ are templates."""
    module, base, items = TYPES[conf["type"]], CONTENT / conf["dir"], []
    groups = {}  # slug -> {lang or None: source file}
    for f in sorted(base.iterdir()) if base.is_dir() else []:
        if f.name.startswith("_"):
            continue
        if f.suffix == ".md":
            slug, lang = languages.split(f.stem)
            if slug != "index":
                groups.setdefault(slug, {})[lang] = f
        elif f.is_dir():
            for g in sorted(f.glob("index*.md")):
                if languages.split(g.stem)[0] == "index":
                    groups.setdefault(f.name, {})[languages.split(g.stem)[1]] = g
    for slug, candidates in groups.items():
        src, content_lang = languages.pick(candidates, STATE["lang"])
        if src is None:
            raise error(base / slug, "no file serves this item in the current language",
                        "Run languages.setup() before load_items(): the declared languages are unknown")
        date = None
        if module.DATED:
            m = DATED.match(slug)
            if not m:
                continue  # not an item: a plain page in the folder
            try:
                datetime.date.fromisoformat(m.group(1))
            except ValueError:
                raise error(src, f'"{m.group(1)}" is not a date',
                            f"Name the file YYYY-MM-DD-slug.md with the {module.NAME}'s date")
            date = m.group(1)
        elif src.parent != base:
            paths.ITEM_FOLDERS.add(str(src.parent.relative_to(CONTENT)))
        meta, _ = front_matter(src.read_text())
        items.append({"slug": slug, "date": date, "meta": meta, "src": src,
                      "path": f"{conf['dir']}/{slug}.html", "collection": name,
                      "conf": conf, "type": module, "lang": STATE["lang"],
                      "content_lang": content_lang})
    for it in items:
        call(it["src"], module, "defaults", it, conf)
    return sorted(items, key=lambda it: call(it["src"], module, "sort_key", it, conf))


def page_item(src, meta):
    """A .md outside every collection, as an item of type page."""
    return {"slug": src.stem, "date": None, "meta": meta, "src": src,
            "path": paths.page_path(src), "collection": None, "conf": {}, "type": TYPES["page"],
            "lang": STATE["lang"], "content_lang": STATE["content_lang"]}


def _target(marker, src, path, colls):
    """The collection a marker lists: {upcoming:meetups} names it; a bare
    {upcoming} is the page's own collection of that type (its folder, or
    the page named like the folder: events.md for events/), else the first
    collection of the type. None when the site has none."""
    word, _, name = marker.partition(":")
    kind = MARKERS[word]
    same = [n for n, c in colls.items() if c["type"] == kind]
    if name:
        if name not in same:
            raise error(src, f"{{{marker}}} names no {kind} collection",
                        f"Collections of that type: {', '.join(same) or 'none'}")
        return name
    folder = path[:-5].removesuffix("/index")
    own = [n for n in same if folder == colls[n]["dir"] or folder.startswith(colls[n]["dir"] + "/")]
    return (own or same or [None])[0]


def fill_lists(sections, src, path, colls, items):
    """Fill every section carrying a list marker ({posts}, {upcoming:meetups},
    {members}...) with cards, and put an item's own card at the top of
    its page. items: {collection name: [item]}."""
    for s in sections:
        for marker in list(s["cls"]):
            word = marker.partition(":")[0]
            if word not in MARKERS:
                continue
            module = TYPES[MARKERS[word]]
            name = _target(marker, src, path, colls)
            conf, its = colls.get(name, {}), items.get(name, [])
            chosen = call(src, module, f'MARKERS["{word}"]', its, conf, fn=module.MARKERS[word])
            cards = []
            for it, extra in chosen["items"]:
                node = call(it["src"], module, "entry", it, True, conf)
                if node is None:
                    continue
                node["cls"] = list(extra) + node.get("cls", [])
                cards.append(node)
            s["cls"].extend(chosen.get("cls", []))
            s["blocks"] = (cards or [{"k": "empty", "text": chosen.get("empty", "")}]) + s["blocks"]
            s["data"] = call(src, module, "list_data", conf) if name else {}
            s["script"] = module.SCRIPT
    for its in items.values():
        for it in its:
            if it["path"] == path and sections:
                card = call(it["src"], it["type"], "entry", it, False, it["conf"])
                if card is not None:
                    sections[0]["blocks"].append(card)


def summary(colls, items):
    """What the build understood, in two lines."""
    builtin = [n for n, m in TYPES.items() if m.PATH.parent == BUILTIN]
    theme = [n for n, m in TYPES.items() if m.PATH.parent != BUILTIN]
    first = "types: " + ", ".join(builtin) + (f"; from theme: {', '.join(theme)}" if theme else "")
    parts = []
    for name, conf in colls.items():
        if not (CONTENT / conf["dir"]).is_dir():
            parts.append(f"{name} ({conf['type']}, no folder)")
        else:
            n = len(items.get(name, []))
            parts.append(f"{name} ({conf['type']}, {n} item{'s' if n != 1 else ''})")
    return first + "\ncollections: " + ", ".join(parts)
