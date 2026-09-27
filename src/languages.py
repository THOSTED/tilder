"""Languages: the default at the root, every other declared language under
its own prefix (/en/); page.<lang>.md next to page.md; a fallback so that
every declared language is a complete tree. docs/languages.md.

The build runs one pass per language (languages.use). Paths stay logical
everywhere; the prefix is added at the edges (paths.py, build.py).
"""

import copy
import json
import re
import tomllib

from ansify import COLOURS, sgr
from config import CFG, CONFIG, CONTENT, STATE, THEME, THEME_TOML, load_config
from report import error, fail

# What looks like a language code after the last dot of a file stem: en,
# fr, pt-br. A stem like "v1.2" or "notes.final" is a plain name.
SUFFIX = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,4})?$")

CONFIGS = {}   # lang -> the full configuration of that language (a copy)


def split(stem):
    """"about.en" -> ("about", "en"); "about" -> ("about", None). In a
    monolingual site (and before setup) there is no suffix to read:
    "notes.old" -> ("notes.old", None)."""
    if len(STATE["languages"]) <= 1:
        return stem, None
    name, dot, suffix = stem.rpartition(".")
    if dot and SUFFIX.match(suffix):
        return name, suffix
    return stem, None


def declared():
    return list(STATE["languages"])


def default():
    return STATE["default"]


def multilingual():
    return len(STATE["languages"]) > 1


def prefix(lang=None):
    """"" for the default language (and before setup), "fr/" for another."""
    lang = lang or STATE["lang"]
    return "" if not lang or lang == STATE["default"] else f"{lang}/"


def pick(candidates, lang):
    """The file that serves a page in `lang`, and its content language.
    candidates: {lang or None: path}. Order: the language, the default, no
    suffix, then the other declared languages in declaration order."""
    order = [lang, STATE["default"], None]
    order += [l for l in STATE["languages"] if l not in order]
    for key in order:
        if key in candidates:
            return candidates[key], key or STATE["default"]
    return None, None


def use(lang):
    """Load the language's configuration and make it the current pass."""
    load_config(lang)
    STATE["lang"], STATE["prefix"] = lang, prefix(lang)


def _language_files():
    """(path, lang) of every site.<lang>.toml and theme.<lang>.toml.
    Everything between the first and the last dot is the language:
    site.x.y.toml reads as language "x.y", which setup refuses as
    undeclared. A theme.<lang>.toml of an undeclared language is setup's
    to ignore: a theme is reused across sites."""
    out = []
    for folder, stem in ((CONTENT, "site"), (THEME, "theme")):
        for p in sorted(folder.glob(f"{stem}.*.toml")) if folder.is_dir() else []:
            out.append((p, p.name[len(stem) + 1:-5]))
    return out


def setup():
    """Read [site] lang and languages, check them and the language files,
    load every language's configuration into CONFIGS, and leave the
    default one loaded. Every problem is reported before the build stops."""
    load_config()
    dflt = CFG["site"]["lang"]
    langs = list(CFG["site"].get("languages") or [dflt])
    errs = []
    if dflt not in langs:
        errs.append(error(CONFIG, f'[site] languages does not contain the default language "{dflt}"',
                          "Add it, or change [site] lang"))
        langs.insert(0, dflt)
    listed = ", ".join(langs)
    for path, lang in _language_files():
        if lang not in langs and path.parent == THEME:
            continue        # a reusable theme may carry languages this site lacks
        if lang not in langs:
            errs.append(error(path, f'"{lang}" is not a declared language',
                              f"Declared: {listed} ([site] languages in {CONFIG.relative_to(CONTENT.parent)})"))
            continue
        with path.open("rb") as f:
            said = tomllib.load(f).get("site", {}).get("lang")
        if said and said != lang:
            errs.append(error(path, f'[site] lang is "{said}", not "{lang}"',
                              "A language's file sets its own lang, or leaves it out"))
    # split() reads suffixes only once the site is known to be multilingual;
    # a monolingual site has no suffix to check: notes.old.md is a page.
    STATE["default"], STATE["languages"] = dflt, langs
    for f in sorted(CONTENT.rglob("*.md")) if len(langs) > 1 else []:
        if any(part.startswith("_") for part in f.relative_to(CONTENT).parts):
            continue
        _, lang = split(f.stem)
        if lang and lang not in langs:
            errs.append(error(f, f'"{lang}" is not a declared language',
                              f"Declared: {listed} ([site] languages in {CONFIG.relative_to(CONTENT.parent)})"))
    CONFIGS.clear()
    for lang in langs:
        load_config(lang)
        CONFIGS[lang] = copy.deepcopy(CFG)
        for e in _accent(lang):     # a bad accent in site.toml is every language's: said once
            if e.items not in [x.items for x in errs]:
                errs.append(e)
    if errs:
        fail(errs)
    use(dflt)
    return langs


def _accent(lang):
    """[text] accent of the language just loaded, as errors: [] when it is
    a colour sgr() knows. The error names the file that set it, the most
    specific one: site.<lang>.toml, site.toml, theme.<lang>.toml, theme.toml."""
    value = CFG["text"]["accent"]
    if sgr(value) is not None:
        return []
    files = (CONTENT / f"site.{lang}.toml", CONFIG, THEME / f"theme.{lang}.toml", THEME_TOML)
    path = next((f for f in files if _sets_accent(f)), CONFIG)
    return [error(path, f"[text] accent is {json.dumps(value, default=str)}, not a colour",
                  f"Set one of {', '.join(COLOURS)}, "
                  "or a 256-colour index from 16 to 255 (208: orange)")]


def _sets_accent(path):
    if not path.is_file():
        return False
    with path.open("rb") as f:
        return "accent" in tomllib.load(f).get("text", {})


def pages():
    """Every rendered .md, grouped by logical path: {"about.md": {None:
    Path("content/about.md"), "fr": Path("content/about.fr.md")}}. Keys are
    content/-relative, suffix stripped; a folder item keeps its
    "<folder>/index.md" key."""
    import paths  # paths imports this module
    table = {}
    for f in sorted(CONTENT.rglob("*.md")):
        if not paths.rendered(f):
            continue
        rel = f.relative_to(CONTENT)
        name, lang = split(rel.stem)
        key = str(rel.with_name(name + ".md"))
        table.setdefault(key, {})[lang] = f
    return table
