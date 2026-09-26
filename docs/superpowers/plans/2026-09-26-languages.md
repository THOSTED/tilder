# Languages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve a site in several declared languages: the default at the root, the others under `/<lang>/`, every tree complete, `page.<lang>.md` next to `page.md` with a four-step fallback, one configuration file per language, `hreflang`, one sitemap, feeds per language, one calendar.

**Architecture:** The build runs one pass per declared language with that language's configuration layered on (`site.<lang>.toml`) and an output prefix. Every path the code handles stays *logical* (no prefix) — `item["path"]`, links written in content, `res()` — and the prefix is added at the edges: output file names, absolute URLs (`clean_url`), the text mirror's folder, and `/`-leading links that cross languages. A new `src/languages.py` holds the declared languages, the suffix split, the fallback pick and the per-language configuration snapshots. A resolution table computed before the passes says which source file each page uses in each language.

**Tech Stack:** Python 3.11+ standard library only. `unittest`. Caddy for the example server config.

**Spec:** `docs/superpowers/specs/2026-09-26-languages-design.md` — read it first.

## Global Constraints

- Python standard library only; no dependency (AGENTS.md §2.2).
- Everything in this repository is English: code, comments, docs, defaults, commit messages. The one exception this plan introduces on purpose: the starter's and the fixture's French files (`site.fr.toml`, `*.fr.md`), which are the feature's example and test data.
- No site's name, domain or words in this repository; the reference site is `$SITE`, the folder that holds this `builder/` as a submodule.
- **Byte-identical reference build** before and after every task: `diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after` prints nothing (rasters excluded: `rsvg-convert` is absent on this machine and the ImageMagick fallback stamps a creation time). The reference site is monolingual (`languages` absent from its `site.toml`); nothing this plan adds may change its output.
- The generator knows no language name: every word of a language comes from `site.<lang>.toml`; `defaults.toml` holds English, neutral defaults only.
- Errors keep the one shape `<file>[:<line>]: <what is wrong>. <what to do>` (`src/report.py`), gathered per phase.
- Tests: `python3 -m unittest discover -s tests -t . -v` from the repository root, green at the end of every task; every test module starts its non-stdlib imports with `from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT` (or `from tests.helpers import ...`).
- Commit messages in Conventional Commits style; no AI co-author or session trailer of any kind.

## Review Focus

Inputs the spec implies but no acceptance line names, each pinned to the task that owns the code:

1. **`site.xx.toml` for an undeclared language**: one `error:` line naming the file and the declared languages, exit 1. Pinned in Task 1.
2. **A link `[x](/events)` written in a prefixed page** (`fr/about`) resolves to `../events`; `[x](events)` resolves to `events` (stays in `fr/`). Pinned in Task 2.
3. **A dated item that exists only in a non-default language** (`2026-02-01-only-french.fr.md` with no `.md`): the default pass serves its French content, the slug is recognised without the suffix, its card lists in every language. Pinned in Task 3.
4. **The calendar is written once, at the root**, never under `fr/`; every language's RSS lists the same items. Pinned in Task 3.
5. **A site that declares no `languages`** (the reference site's case): no `hreflang`, no `LANGUAGES:` line, no `xmlns:xhtml` in the sitemap, no `<nav class="languages">`, no `fr/` output — checked on a scratch copy of the fixture with the language files removed. Pinned in Task 5.

---

## File structure

```
src/languages.py      NEW  setup(), declared(), default(), multilingual(), prefix(), split(), pick(), pages(), CONFIGS
src/config.py         load_config(lang=None) with the theme.L.toml / site.L.toml layers; STATE keys
src/paths.py          lang-aware rendered()/page_path(); clean_url(path, lang=None) with prefix; relative() `/x` rule; absolute()
src/contenttypes.py   load_items() picks each item's file for the pass; items carry lang and content_lang
src/build.py          one pass per language; prefix at the edges; sitemap/robots/manifest/calendar once; languages summary line
src/page.py           {{ languages }}, {{ content_lang }}, the wordmark's language segment
src/seo.py            hreflang links, og:locale:alternate, inLanguage, sitemap xhtml:link
src/text.py           LANGUAGES: line in multilingual sites
src/feeds.py          absolute URLs with the prefix
defaults.toml         [site] languages = [], [languages], labels.languages
tests/site/           bilingual fixture: site.fr.toml, index.fr.md, blog/2026-01-01-hello.fr.md, blog/2026-02-01-only-french.fr.md, legal.fr.md, layout with the two placeholders
tests/test_languages*.py  NEW
starter/              bilingual: site.fr.toml, index.fr.md, blog/2026-01-01-hello.fr.md, {{ languages }} in layout, .languages in style.css
examples/Caddyfile    404 per language prefix
docs/languages.md     NEW; docs/theme.md, docs/markdown.md, README.md, AGENTS.md updated
```

---

### Task 0: Baseline

- [ ] **Step 1: Build the baseline of the reference site**

```bash
SITE="$(cd .. && pwd)"; export BUILD_TODAY=2026-09-26
rm -rf /tmp/tilder-before && python3 build.py --root "$SITE" --out /tmp/tilder-before | tail -1 | cut -c1-60
python3 -m unittest discover -s tests -t . 2>&1 | tail -1
```

Expected: `built /tmp/tilder-before: ...` and `OK` (98 tests). Keep `/tmp/tilder-before` for the whole plan. No commit.

---

### Task 1: `src/languages.py` core, configuration layers, declared languages

**Files:**
- Create: `src/languages.py`
- Modify: `src/config.py` (`STATE` keys, `load_config(lang=None)`), `defaults.toml`
- Modify: `src/build.py` (call `languages.setup()` instead of a bare `load_config()`)
- Create: `tests/site/content/site.fr.toml`; Modify: `tests/site/content/site.toml`
- Test: `tests/test_languages.py`

**Interfaces:**
- Produces:
  - `config.STATE` gains `"lang": ""`, `"default": ""`, `"languages": []`, `"prefix": ""`, `"content_lang": ""`.
  - `config.load_config(lang=None)`: layers `defaults.toml < theme/theme.toml < theme/theme.<lang>.toml < content/site.toml < content/site.<lang>.toml`; with a `lang`, sets `CFG["site"]["lang"] = lang` after merging.
  - `languages.setup() -> list[str]`: loads the default configuration, reads `site.lang` and `site.languages`, validates (§3 errors, gathered), fills `STATE["default"]`, `STATE["languages"]`, `STATE["lang"]`, `STATE["prefix"]`, and `languages.CONFIGS` (`{lang: deep copy of CFG after load_config(lang)}`), then leaves `CFG` loaded for the default language. Returns the declared languages.
  - `languages.declared() -> list[str]`, `languages.default() -> str`, `languages.multilingual() -> bool`, `languages.prefix(lang=None) -> str` (`""` for the default or when no language is set up, else `f"{lang}/"`), `languages.split(stem) -> (name, lang | None)`, `languages.pick(candidates: dict[str | None, Path], lang) -> (Path | None, content_lang | None)` following the four-step fallback, `languages.use(lang)`: `load_config(lang)` plus `STATE["lang"]`/`STATE["prefix"]`.
  - `defaults.toml`: `[site] languages = []` (empty: monolingual), `[languages]` (empty table: names shown by the switcher), `[labels] languages = "Languages"`.

- [ ] **Step 1: Write the failing tests**

`tests/test_languages.py`:

```python
import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import languages
import report
from config import BUILDER, CFG, CONTENT, STATE, load_config


class Split(unittest.TestCase):
    def test_suffix(self):
        self.assertEqual(languages.split("about.en"), ("about", "en"))
        self.assertEqual(languages.split("about"), ("about", None))
        self.assertEqual(languages.split("index.pt-br"), ("index", "pt-br"))
        self.assertEqual(languages.split("2026-01-01-hello.fr"), ("2026-01-01-hello", "fr"))
        self.assertEqual(languages.split("v1.2"), ("v1.2", None))          # not a language code
        self.assertEqual(languages.split("notes.final"), ("notes.final", None))


class Setup(unittest.TestCase):
    def setUp(self):
        languages.setup()

    def test_declared_and_default(self):
        self.assertEqual(languages.default(), "en")
        self.assertEqual(languages.declared(), ["en", "fr"])
        self.assertTrue(languages.multilingual())
        self.assertEqual(languages.prefix("en"), "")
        self.assertEqual(languages.prefix("fr"), "fr/")
        self.assertEqual(STATE["lang"], "en")
        self.assertEqual(STATE["prefix"], "")

    def test_configs_per_language(self):
        self.assertEqual(languages.CONFIGS["en"]["site"]["lang"], "en")
        self.assertEqual(languages.CONFIGS["fr"]["site"]["lang"], "fr")
        self.assertEqual(languages.CONFIGS["fr"]["site"]["locale"], "fr_FR")
        self.assertEqual(languages.CONFIGS["fr"]["labels"]["skip"], "aller au contenu")
        self.assertEqual(languages.CONFIGS["fr"]["labels"]["copy"], "copy")        # not translated: inherited
        self.assertEqual(languages.CONFIGS["fr"]["nav"][0]["label"], "accueil")
        self.assertEqual(languages.CONFIGS["fr"]["dates"]["first"], "1er")
        self.assertEqual(languages.CONFIGS["fr"]["collections"]["events"]["upcoming_tag"], "à venir")
        self.assertEqual(languages.CONFIGS["en"]["labels"]["languages"], "Languages")
        self.assertEqual(languages.CONFIGS["fr"]["labels"]["languages"], "Langues")
        self.assertEqual(CFG["site"]["lang"], "en")   # setup leaves the default loaded

    def test_use_switches_the_configuration(self):
        languages.use("fr")
        try:
            self.assertEqual(CFG["site"]["lang"], "fr")
            self.assertEqual(STATE["lang"], "fr")
            self.assertEqual(STATE["prefix"], "fr/")
            self.assertEqual(CFG["site"]["name"], "test site")   # not overridden: inherited
        finally:
            languages.use("en")
        self.assertEqual(STATE["prefix"], "")

    def test_pick_follows_the_fallback_order(self):
        a, b, c, d = (pathlib.Path(x) for x in ("p.fr.md", "p.en.md", "p.md", "p.de.md"))
        self.assertEqual(languages.pick({"fr": a, "en": b, None: c}, "fr"), (a, "fr"))
        self.assertEqual(languages.pick({"en": b, None: c}, "fr"), (b, "en"))
        self.assertEqual(languages.pick({None: c}, "fr"), (c, "en"))            # no suffix: the default's content
        self.assertEqual(languages.pick({"fr": a}, "en"), (a, "fr"))            # only another language has it
        self.assertEqual(languages.pick({}, "en"), (None, None))


def scratch():
    """A copy of the fixture site in a temp dir; (tmp, site) paths."""
    tmp = tempfile.mkdtemp()
    site = pathlib.Path(tmp) / "site"
    shutil.copytree(pathlib.Path(CONTENT).parent, site)
    return tmp, site


def run(site, *args):
    r = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                        "--out", str(site / "out"), *args], capture_output=True, text=True,
                       env={"SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15", "PATH": "/usr/bin:/bin"})
    return r.returncode, r.stderr


class ConfigErrors(unittest.TestCase):
    def setUp(self):
        self.tmp, self.site = scratch()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_undeclared_language_file(self):
        (self.site / "content" / "site.de.toml").write_text('[site]\nlang = "de"\n')
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/site.de.toml: "de" is not a declared language. '
                      "Declared: en, fr ([site] languages in content/site.toml)", err)

    def test_default_missing_from_languages(self):
        toml = self.site / "content" / "site.toml"
        toml.write_text(toml.read_text().replace('languages = ["en", "fr"]', 'languages = ["fr"]'))
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/site.toml: [site] languages does not contain the default language "en". '
                      "Add it, or change [site] lang", err)

    def test_language_file_with_another_lang(self):
        fr = self.site / "content" / "site.fr.toml"
        fr.write_text(fr.read_text().replace('lang = "fr"', 'lang = "de"'))
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/site.fr.toml: [site] lang is "de", not "fr". '
                      "A language's file sets its own lang, or leaves it out", err)

    def test_errors_are_gathered(self):
        (self.site / "content" / "site.de.toml").write_text("")
        fr = self.site / "content" / "site.fr.toml"
        fr.write_text(fr.read_text().replace('lang = "fr"', 'lang = "de"'))
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertEqual(err.count("error: "), 2)
```

- [ ] **Step 2: Add the fixture's languages**

Append to `tests/site/content/site.toml`, inside `[site]` (after `title_suffix`):

```toml
languages = ["en", "fr"]        # the default first; fr is served under /fr/
```

and, as a new table after `[share]`:

```toml
[languages]                     # names shown by the language switcher
en = "English"
fr = "Français"
```

Create `tests/site/content/site.fr.toml`:

```toml
# The fixture site in French: only what differs from site.toml.

[site]
lang = "fr"
locale = "fr_FR"
manual = "Manuel du site de test"
title_suffix = " - site de test"

[labels]
skip = "aller au contenu"
nav = "Navigation principale"
languages = "Langues"
to_top = "↑ haut de page"

[[nav]]
label = "accueil"
href = ""

[[nav]]
label = "événements"
href = "events"

[[nav]]
label = "blog"
href = "blog/"

[[nav]]
label = "membres"
href = "members"

[collections.events]
upcoming_tag = "à venir"
past_tag = "passé"
none_upcoming = "Aucune rencontre annoncée."
none_past = "Aucune rencontre passée."
feed_title = "événements"

[collections.blog]
feed_title = "articles"
empty = "Aucun article."

[dates]
weekdays = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]
first = "1er"
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `python3 -m unittest tests.test_languages -v`
Expected: FAIL, `No module named 'languages'`.

- [ ] **Step 4: `defaults.toml`**

In `[site]`, after `title_suffix`:

```toml
languages = []                      # every language served, the default (lang) first;
                                    # empty: one language, no prefix (docs/languages.md)
```

In `[labels]`, after `website`:

```toml
languages = "Languages"             # the language switcher, {{ languages }}
```

After `[links]`:

```toml
# The names the language switcher shows, by code: en = "English". A language
# without a name shows its code.
[languages]
```

- [ ] **Step 5: `config.py`**

`STATE`:

```python
# What one build shares: the date that decides upcoming and past events,
# and the language of the current pass (languages.py).
STATE = {"today": "", "lang": "", "default": "", "languages": [], "prefix": "",
         "content_lang": ""}
```

`load_config`:

```python
def _layer(data, path):
    if path.is_file():
        with path.open("rb") as f:
            _merge(data, tomllib.load(f))


def load_config(lang=None):
    """defaults.toml, the theme's theme.toml, the site's content/site.toml,
    and with a language its theme.<lang>.toml and site.<lang>.toml, each
    over the previous: the site has the last word. With a language, [site]
    lang is that language."""
    with DEFAULTS.open("rb") as f:
        data = tomllib.load(f)
    _layer(data, THEME_TOML)
    if lang:
        _layer(data, THEME / f"theme.{lang}.toml")
    with CONFIG.open("rb") as f:
        _merge(data, tomllib.load(f))
    if lang:
        _layer(data, CONTENT / f"site.{lang}.toml")
        data["site"]["lang"] = lang
    CFG.clear()
    CFG.update(data)
    CFG["site"]["updated"] = str(CFG["site"]["updated"])
```

- [ ] **Step 6: `src/languages.py`**

```python
"""Languages: the default at the root, every other declared language under
its own prefix (/en/); page.<lang>.md next to page.md; a fallback so that
every declared language is a complete tree. docs/languages.md.

The build runs one pass per language (languages.use). Paths stay logical
everywhere; the prefix is added at the edges (paths.py, build.py).
"""

import copy
import re
import tomllib

from config import CFG, CONFIG, CONTENT, STATE, THEME, load_config
from report import error, fail

# What looks like a language code after the last dot of a file stem: en,
# fr, pt-br. A stem like "v1.2" or "notes.final" is a plain name.
SUFFIX = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,4})?$")

CONFIGS = {}   # lang -> the full configuration of that language (a copy)


def split(stem):
    """"about.en" -> ("about", "en"); "about" -> ("about", None)."""
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
    """(path, lang) of every site.<lang>.toml and theme.<lang>.toml."""
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
        if lang not in langs:
            errs.append(error(path, f'"{lang}" is not a declared language',
                              f"Declared: {listed} ([site] languages in {CONFIG.relative_to(CONTENT.parent)})"))
            continue
        with path.open("rb") as f:
            said = tomllib.load(f).get("site", {}).get("lang")
        if said and said != lang:
            errs.append(error(path, f'[site] lang is "{said}", not "{lang}"',
                              "A language's file sets its own lang, or leaves it out"))
    if errs:
        fail(errs)
    STATE["default"], STATE["languages"] = dflt, langs
    CONFIGS.clear()
    for lang in langs:
        load_config(lang)
        CONFIGS[lang] = copy.deepcopy(CFG)
    use(dflt)
    return langs
```

Note: `CONFIG.relative_to(CONTENT.parent)` gives `content/site.toml`; `report.rel` is not used here because the message quotes the path inside the hint, not as the error's location.

- [ ] **Step 7: `build.py` calls `setup()`**

In `build()`, replace the first line `load_config()` with `languages.setup()` (add `import languages`). Nothing else changes in this task: one pass, the default language, prefix `""`.

- [ ] **Step 8: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: all PASS (the fixture now declares `fr` but nothing renders it yet); `IDENTICAL`.

- [ ] **Step 9: Commit**

```bash
git add src/languages.py src/config.py src/build.py defaults.toml tests/site/content/site.toml tests/site/content/site.fr.toml tests/test_languages.py
git commit -m "feat: declared languages, site.<lang>.toml layers"
```

---

### Task 2: Resolution table, lang-aware paths, cross-language links

**Files:**
- Modify: `src/languages.py` (`pages()`), `src/paths.py` (`rendered`, `page_path`, `clean_url(path, lang=None)`, `relative` `/x` rule, `absolute`), `src/build.py` (pages come from the table; default pass only)
- Create: `tests/site/content/index.fr.md`, `tests/site/content/blog/2026-01-01-hello.fr.md`, `tests/site/content/legal.fr.md`
- Test: `tests/test_languages_paths.py`

**Interfaces:**
- Produces:
  - `languages.pages() -> dict[str, dict[str | None, Path]]`: `{logical content-relative path with .md (suffix stripped): {lang: source}}` for every rendered `.md`.
  - `paths.rendered(path)` and `paths.page_path(src)` strip the language suffix (`about.en.md` -> `about.html`; `hello/index.fr.md` -> `blog/hello.html`).
  - `paths.clean_url(path, lang=None) -> str`: `/` + prefix of `lang` (default: the current pass) + the clean path.
  - `paths.absolute(rel, lang=None) -> str`: `apex() + "/" + prefix + rel` (for feeds).
  - `paths.relative(from_dir, target)`: a target starting with `/` is resolved from the site root (`/events` from `fr/about` -> `../events`; from `about` -> `events`); anything else as today, inside the language.

- [ ] **Step 1: Write the fixture pages and the failing tests**

`tests/site/content/index.fr.md`:

```markdown
---
man: TEST(1)
title: site de test
description: Un site de test pour le générateur : pages, articles, rencontres, membres, et une langue de plus.
tagline: fixtures en français
nav:
---

## Nom

test - un site construit par les tests {mono}

## Prochaine {next-event}

## À propos

Un paragraphe, pour que la page ait un corps. [in English](/) {small}
```

`tests/site/content/blog/2026-01-01-hello.fr.md`:

```markdown
---
title: Bonjour
description: Le premier article du site de test, pour tester les cartes, les flux et les données structurées.
author: Ada Lovelace
tag: note
---

## Nom

bonjour - le premier article {mono}

## Corps

Un paragraphe. Voir [les événements](events) et [the English events](/events).
```

`tests/site/content/legal.fr.md` (no `.md` beside it):

```markdown
---
man: TEST(1)
title: mentions légales
description: Une page qui n'existe qu'en français ; les autres langues la servent telle quelle.
tagline: mentions
nav: -
---

## Nom

legal - les mentions légales {mono}
```

`tests/test_languages_paths.py`:

```python
import pathlib
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import languages
import paths
from config import CONTENT, STATE


class Table(unittest.TestCase):
    def setUp(self):
        languages.setup()

    def test_pages_grouped_by_logical_path(self):
        table = languages.pages()
        self.assertEqual(set(table["index.md"]), {None, "fr"})
        self.assertEqual(table["index.md"]["fr"], CONTENT / "index.fr.md")
        self.assertEqual(set(table["blog/2026-01-01-hello.md"]), {None, "fr"})
        self.assertEqual(set(table["legal.md"]), {"fr"})
        self.assertEqual(set(table["members/alan-turing/index.md"]), {None})
        self.assertNotIn("members/_template.md", table)

    def test_rendered_and_page_path_strip_the_suffix(self):
        self.assertTrue(paths.rendered(CONTENT / "index.fr.md"))
        self.assertEqual(paths.page_path(CONTENT / "index.fr.md"), "index.html")
        self.assertEqual(paths.page_path(CONTENT / "blog/2026-01-01-hello.fr.md"), "blog/2026-01-01-hello.html")
        self.assertEqual(paths.page_path(CONTENT / "members/alan-turing/index.md"), "members/alan-turing.html")


class Urls(unittest.TestCase):
    def setUp(self):
        languages.setup()

    def test_clean_url_takes_the_prefix(self):
        self.assertEqual(paths.clean_url("index.html"), "/")
        self.assertEqual(paths.clean_url("index.html", "fr"), "/fr/")
        self.assertEqual(paths.clean_url("events.html", "fr"), "/fr/events")
        self.assertEqual(paths.clean_url("blog/index.html", "fr"), "/fr/blog/")
        languages.use("fr")
        try:
            self.assertEqual(paths.clean_url("events.html"), "/fr/events")
            self.assertEqual(paths.absolute("blog/feed.xml"), "https://test.example/fr/blog/feed.xml")
        finally:
            languages.use("en")
        self.assertEqual(paths.absolute("blog/feed.xml"), "https://test.example/blog/feed.xml")

    def test_relative_links_stay_in_the_language(self):
        languages.use("fr")
        try:
            self.assertEqual(paths.relative("", "events"), "events")          # fr/about -> fr/events
            self.assertEqual(paths.relative("blog", "events"), "../events")
            self.assertEqual(paths.relative("", ""), "./")
            self.assertEqual(paths.relative("", "/events"), "../events")      # site root: the default language
            self.assertEqual(paths.relative("blog", "/"), "../../")
            self.assertEqual(paths.relative("", "/fr/events"), "events")      # explicit, same language
            self.assertEqual(paths.relative("", "/events#x"), "../events#x")
        finally:
            languages.use("en")
        self.assertEqual(paths.relative("", "/events"), "events")            # default pass: root is the root
        self.assertEqual(paths.relative("blog", "/fr/"), "../fr/")
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_languages_paths -v`
Expected: FAIL (`languages.pages` missing; `clean_url()` takes one argument).

- [ ] **Step 3: `paths.py`**

```python
"""From content/ paths to output paths, URLs and relative links. Paths are
logical, without a language prefix; the prefix is added here where a URL
or a link leaves the language (clean_url, absolute, a /-leading target)."""

import os

from config import CONTENT, DATED, STATE, apex
from languages import prefix, split

...


def item_folder(rel_parent):
    """Is this content/-relative folder one item?"""
    return bool(DATED.match(rel_parent.name)) or str(rel_parent) in ITEM_FOLDERS


def txt_name(html_path):
    ...unchanged...


def clean_url(html_path, lang=None):
    """The URL path of a page in a language (default: the current pass):
    "/", "/fr/", "/fr/events", "/blog/"."""
    n = html_path[:-5]
    p = prefix(lang)
    if n == "index":
        return "/" + p
    if n.endswith("/index"):
        return "/" + p + n[: -len("/index")] + "/"
    return "/" + p + n


def absolute(rel, lang=None):
    """The absolute URL of a root-relative file of a language: feeds."""
    return f"{apex()}/{prefix(lang)}{rel}"


def relative(from_dir, target):
    """Resolve a target from the directory of the page being rendered. A
    root-relative target ("", "events", "blog/", "./#id") is inside the
    language; a target starting with "/" is from the site root, so a page
    may link to another language ("/events", "/fr/events"). A bare "#id"
    stays on the page."""
    if target.startswith("http") or target.startswith("#"):
        return target
    target, hash_, frag = target.partition("#")
    if target.startswith("/"):
        base = (STATE["prefix"] + from_dir).rstrip("/")
        return _relative(base, target[1:]) + hash_ + frag
    if target in ("", "."):
        target = ""
    return _relative(from_dir, target.removeprefix("./")) + hash_ + frag


def _relative(from_dir, target):
    ...unchanged...


def rendered(path):
    """A Markdown file is a page unless a part of its path starts with `_`
    (templates), or it sits in an item's folder without being its index
    (index.md, index.fr.md)."""
    rel = path.relative_to(CONTENT)
    if any(part.startswith("_") for part in rel.parts):
        return False
    name, _ = split(rel.stem)
    return name == "index" or not item_folder(rel.parent)


def page_path(src):
    """content/blog/X/index.md -> blog/X.html: an item folder's page sits
    next to the folder. The language suffix is not part of the path:
    about.fr.md -> about.html."""
    rel = src.relative_to(CONTENT)
    name, _ = split(rel.stem)
    if name == "index" and item_folder(rel.parent):
        return str(rel.parent) + ".html"
    return str(rel.with_name(name + ".html"))
```

Import note: `languages` imports `config` and `report` only; `paths` may import `languages`. `languages.pages()` needs `paths.rendered`: import `paths` inside the function.

- [ ] **Step 4: `languages.pages()`**

Append to `src/languages.py`:

```python
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
```

- [ ] **Step 5: `build.py` reads pages from the table (default language only, for now)**

Replace the page loop's header:

```python
    table = languages.pages()
    for key in sorted(table):
        src, content_lang = languages.pick(table[key], STATE["lang"])
        STATE["content_lang"] = content_lang
        try:
            meta, sections, preamble = parse(src)
            ...unchanged...
```

In this task, with the default pass only, `pick` gives `legal.fr.md` for `legal.md` (step 4 of the fallback), and `hello.md` for the post (its `.fr` twin is not the default's). Items are still read by the old `load_items`; a suffixed item file with no unsuffixed twin would break here, which is why `2026-02-01-only-french.fr.md` arrives in Task 3. Add a smoke assertion to guard the direction, in `tests/test_languages_paths.py`:

```python
class DefaultPassFallback(unittest.TestCase):
    def test_pages_only_in_french_exist_at_the_root(self):
        out = helpers.rebuild()
        self.assertIn("legal.html", out)
        self.assertIn("mentions légales", out["legal.html"])
        self.assertNotIn("legal.fr.html", out)
        self.assertNotIn("index.fr.html", out)
        self.assertIn("test site", out["index.html"])                       # English wins at the root
```

- [ ] **Step 6: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL` (the reference site has no suffixed file and no `/`-leading link: check with `grep -rn "](/" $SITE/content | head` — if it has any, they resolve identically today only when written from the root; report it).

- [ ] **Step 7: Commit**

```bash
git add src/languages.py src/paths.py src/build.py tests/site/content tests/test_languages_paths.py
git commit -m "feat: language suffixes in paths, the resolution table, links across languages"
```

---

### Task 3: One pass per language

**Files:**
- Modify: `src/build.py` (the loop), `src/contenttypes.py` (`load_items`, `page_item`, `summary` unchanged), `src/feeds.py` (`absolute`), `src/seo.py` (one line in `sitemap_xml`)
- Create: `tests/site/content/blog/2026-02-01-only-french.fr.md`
- Test: `tests/test_languages_build.py`

**Interfaces:**
- Produces:
  - Items carry `"lang"` (the pass) and `"content_lang"`; `contenttypes.load_items(name, conf)` picks each item's file for `STATE["lang"]` with `languages.pick`; the dated slug is recognised without suffix.
  - `contenttypes.page_item(src, meta)` sets `lang` and `content_lang` from `STATE`.
  - `build()` output: for each language L with prefix P, `P + path` for pages, `txt/P...` and `ansi/P...`, `P + conf["feed"]` for feeds; `outputs()` (the calendar), `sitemap.*`, `robots.txt`, `site.webmanifest`, the copies and the icons once. `STATE["summary"]` starts with `languages: en (default), fr` when multilingual.
  - `feeds.rss` uses `paths.absolute` for the channel link and self link.

- [ ] **Step 1: Write the fixture item and the failing tests**

`tests/site/content/blog/2026-02-01-only-french.fr.md` (no `.md` beside it):

```markdown
---
title: Seulement en français
description: Un article qui n'existe qu'en français, servi tel quel dans les autres langues.
author: Ada Lovelace
tag: note
---

## Nom

only-french - un article sans version anglaise {mono}
```

`tests/test_languages_build.py`:

```python
import unittest

from tests.helpers import build_site


class Passes(unittest.TestCase):
    def test_every_page_in_every_language(self):
        out = build_site()
        for p in ("index", "events", "members", "blog/index", "blog/2026-01-01-hello",
                  "blog/2026-02-01-only-french", "legal", "members/alan-turing", "404"):
            self.assertIn(f"{p}.html", out, p)
            self.assertIn(f"fr/{p}.html", out, p)
        self.assertIn("txt/fr/events.txt", out)
        self.assertIn("ansi/fr/events.txt", out)
        self.assertNotIn("txt/fr/404.txt", out)

    def test_translated_and_fallback_content(self):
        out = build_site()
        self.assertIn("fixtures en français", out["fr/index.html"])
        self.assertIn("<title>Bonjour - site de test</title>", out["fr/blog/2026-01-01-hello.html"])
        self.assertIn("<title>Hello - test site</title>", out["blog/2026-01-01-hello.html"])
        self.assertIn("Alan Turing", out["fr/members/alan-turing.html"])          # fallback: English content
        self.assertIn("Manuel du site de test", out["fr/members/alan-turing.html"])  # French interface
        self.assertIn("mentions légales", out["legal.html"])                       # only French exists
        self.assertIn("Seulement en français", out["blog/2026-02-01-only-french.html"])

    def test_words_and_dates_of_the_language(self):
        out = build_site()
        fr = out["fr/events.html"]
        self.assertIn('class="tag tag--next">à venir<', fr)
        self.assertIn("jeudi 1er janvier 2099", fr)
        self.assertIn('aria-label="Navigation principale"', fr)
        self.assertIn(">événements</a>", fr)
        self.assertIn("Thursday 1 January 2099", out["events.html"])

    def test_items_list_in_both_languages(self):
        out = build_site()
        self.assertIn(">Bonjour</a>", out["fr/blog/index.html"])
        self.assertIn(">Seulement en français</a>", out["fr/blog/index.html"])
        self.assertIn(">Hello</a>", out["blog/index.html"])
        self.assertIn(">Seulement en français</a>", out["blog/index.html"])     # fallback card
        self.assertIn('href="2026-02-01-only-french"', out["blog/index.html"])   # logical link, no suffix

    def test_feeds_per_language_calendar_once(self):
        out = build_site()
        self.assertIn("fr/blog/feed.xml", out)
        self.assertIn("<title>articles</title>", out["fr/blog/feed.xml"])
        self.assertIn("<title>Bonjour</title>", out["fr/blog/feed.xml"])
        self.assertIn("<link>https://test.example/fr/blog/2026-01-01-hello</link>", out["fr/blog/feed.xml"])
        self.assertIn("<language>fr</language>", out["fr/blog/feed.xml"])
        self.assertIn('<atom:link href="https://test.example/fr/blog/feed.xml"', out["fr/blog/feed.xml"])
        self.assertIn("<link>https://test.example/fr/blog/</link>", out["fr/blog/feed.xml"])
        self.assertEqual(out["blog/feed.xml"].count("<item>"), out["fr/blog/feed.xml"].count("<item>"))
        self.assertIn("events.ics", out)
        self.assertNotIn("fr/events.ics", out)
        self.assertIn("fr/talks.xml", out)

    def test_once_only_files(self):
        out = build_site()
        for f in ("sitemap.xml", "sitemap.txt", "robots.txt", "site.webmanifest", "style.css",
                  "members/alan-turing/notes.txt"):
            self.assertIn(f, out)
            self.assertNotIn(f"fr/{f}", out)

    def test_summary_names_the_languages(self):
        from config import STATE
        build_site()
        self.assertTrue(STATE["summary"].startswith("languages: en (default), fr\n"), STATE["summary"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_languages_build -v`
Expected: FAIL on `fr/index.html`.

- [ ] **Step 3: `contenttypes.load_items` picks per language**

```python
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
    ...defaults and sort unchanged...
```

`import languages` at the top of `contenttypes.py` (`languages` imports `config`, `report`; no cycle). `page_item` gains `"lang": STATE["lang"], "content_lang": STATE["content_lang"]` (import `STATE`).

- [ ] **Step 4: `build()` loops over the languages**

```python
def build():
    """Every output file, as {relative path: bytes}: one pass per declared
    language, each under its prefix; the sitemap, robots.txt, the manifest,
    the types' own files (the calendar) and the copies once."""
    langs = languages.setup()
    STATE["today"] = os.environ.get("BUILD_TODAY") or datetime.date.today().isoformat()
    out, every, table = {}, [], {}  # every: the pages of every language, for the sitemap
    for lang in langs:
        languages.use(lang)
        inline.EXTERNAL = CFG["labels"]["external"]
        inline.NEW_TAB_LABEL = CFG["labels"]["new_tab"]
        inline.NEW_TAB = CFG["links"]["new_tab"]
        inline.SAME_TAB = tuple(CFG["links"]["same_tab"])
        ansify_module.COMMANDS = CFG["text"]["commands"]
        ansify_module.BOXES = {
            to_ascii(CFG["labels"][kind]): colour for kind, colour in
            (("info", ansify_module.CYAN), ("warning", ansify_module.YELLOW),
             ("error", ansify_module.RED))}
        contenttypes.load()
        colls = contenttypes.collections()
        items = {name: contenttypes.load_items(name, conf) for name, conf in colls.items()}
        by_src = {it["src"]: it for its in items.values() for it in its}
        if lang == langs[0]:
            # The table needs paths.ITEM_FOLDERS, which load_items fills; the
            # folders are the same in every language.
            table = languages.pages()
            head = (f"languages: {langs[0]} (default), {', '.join(langs[1:])}\n"
                    if languages.multilingual() else "")
            STATE["summary"] = head + contenttypes.summary(colls, items)
        prefix, pages = STATE["prefix"], []
        for key in sorted(table):
            src, content_lang = languages.pick(table[key], lang)
            STATE["content_lang"] = content_lang
            try:
                meta, sections, preamble = parse(src)
                it = by_src[src] if src in by_src else contenttypes.page_item(src, meta)
                meta = it["meta"]
                meta["_dir"] = site_path(src)
                pages.append(it)
                contenttypes.fill_lists(sections, src, it["path"], colls, items)
                out[prefix + it["path"]] = render_html(it, sections, preamble, colls)
                if meta.get("text", "yes") != "no":
                    marked = render_txt(meta, sections)
                    out[f"txt/{prefix}{txt_name(it['path'])}.txt"] = plain(marked)
                    out[f"ansi/{prefix}{txt_name(it['path'])}.txt"] = ansify(marked)
            except report.BuildError:
                raise
            except Exception as e:  # a missing `title:`...: name the page, not a traceback
                raise report.error(src, f"cannot be built: {e.__class__.__name__}: {e}",
                                   "Run with --debug for the traceback", exc=e)
        # Feeds per language; the types' own files (an iCalendar) once, in
        # the default language: a calendar has no interface language.
        for name, conf in colls.items():
            if not (CONTENT / conf["dir"]).is_dir():
                continue
            module = contenttypes.TYPES[conf["type"]]
            if conf.get("feed") and module.HAS_FEED:
                out[prefix + conf["feed"]] = feed(items[name], conf)
            if lang == langs[0]:
                out.update(contenttypes.call(CONTENT / conf["dir"], module, "outputs", items[name], conf))
        check(pages)
        every.extend(pages)
        if lang == langs[0]:
            out["robots.txt"] = robots(CFG["robots"], f"{apex()}/sitemap.xml")
            out["txt/robots.txt"] = robots(CFG["robots_man"])  # txt/ is the root of the plain-text host
            out["site.webmanifest"] = manifest()
    languages.use(langs[0])
    indexed = [it for it in every if "noindex" not in it["meta"].get("robots", "")]
    out["sitemap.xml"] = sitemap_xml(indexed)
    out["sitemap.txt"] = "".join(f"{apex()}{clean_url(it['path'], it['lang'])}\n" for it in
                                 sorted(indexed, key=lambda it: clean_url(it["path"], it["lang"])))
    out = {k: v.encode("utf-8") for k, v in out.items()}
    ...the copy loops, generated(), EXTRA: unchanged...
    return out
```

`sitemap_xml` is Task 5's; until then it must use `clean_url(it["path"], it["lang"])` for the `<loc>`: make that one-line change in `seo.sitemap_xml` now (`sorted(..., key=lambda it: clean_url(it["path"], it["lang"]))` and the `<loc>` likewise). In a monolingual site every `lang` is the default and the output is unchanged.

- [ ] **Step 5: `feeds.rss` links**

In `src/feeds.py`, `feed()`: `return rss(conf["feed_title"], absolute(conf["nav"]), absolute(conf["feed"]), conf["feed_description"], rows)` with `from paths import absolute, clean_url`; drop the `a = apex()` line if unused (keep `apex` for `calendar`).

- [ ] **Step 6: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`. Existing tests that count outputs (`test_collections`, `test_feeds`) still hold: nothing at the root moved.

- [ ] **Step 7: Commit**

```bash
git add src/build.py src/contenttypes.py src/feeds.py src/seo.py tests/test_languages_build.py
git commit -m "feat: one build pass per language, every tree complete"
```

---

### Task 4: `{{ languages }}`, `{{ content_lang }}`, the wordmark, `hreflang`, Open Graph, `inLanguage`

**Files:**
- Modify: `src/page.py`, `src/seo.py`, `tests/site/theme/layout.html`, `tests/site/theme/layouts/event.html`
- Test: `tests/test_languages_head.py`

**Interfaces:**
- Produces: placeholders `{{ languages }}` (the `<nav class="languages">` of spec §4, empty when monolingual) and `{{ content_lang }}`; `seo.alternates(item) -> list[str]` (the `hreflang` `<link>` lines, empty when monolingual) placed first in `head_tags`; `og:locale:alternate` after `og:locale`; `inLanguage` = `item["content_lang"]` on the page node (`WebSite` keeps the interface language: a site-level node); the wordmark's language segment.

- [ ] **Step 1: Fixture layout and failing tests**

In `tests/site/theme/layout.html` and `tests/site/theme/layouts/event.html`: change `<main id="contenu">` to `<main id="contenu" lang="{{ content_lang }}">`, and add `{{ languages }}` on its own line right after the `</nav>` of the main navigation.

`tests/test_languages_head.py`:

```python
import json
import re
import unittest

from tests.helpers import build_site


def graph(html):
    data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return json.loads(data.replace("<\\/", "</"))["@graph"]


class Head(unittest.TestCase):
    def test_hreflang_on_every_page(self):
        out = build_site()
        en, fr = out["events.html"], out["fr/events.html"]
        for page in (en, fr):
            self.assertIn('<link rel="alternate" hreflang="en" href="https://test.example/events">', page)
            self.assertIn('<link rel="alternate" hreflang="fr" href="https://test.example/fr/events">', page)
            self.assertIn('<link rel="alternate" hreflang="x-default" href="https://test.example/events">', page)
        self.assertIn('<link rel="alternate" hreflang="fr" href="https://test.example/fr/">', out["index.html"])
        self.assertIn('<link rel="alternate" hreflang="fr" href="https://test.example/fr/blog/">', out["blog/index.html"])
        self.assertIn('<link rel="canonical" href="https://test.example/fr/events">', fr)
        self.assertIn('<link rel="canonical" href="https://test.example/events">', en)

    def test_og_locale_and_alternate(self):
        out = build_site()
        self.assertIn('<meta property="og:locale" content="fr_FR">', out["fr/events.html"])
        self.assertIn('<meta property="og:locale:alternate" content="en_GB">', out["fr/events.html"])
        self.assertIn('<meta property="og:locale" content="en_GB">', out["events.html"])
        self.assertIn('<meta property="og:locale:alternate" content="fr_FR">', out["events.html"])
        self.assertIn('<meta property="og:url" content="https://test.example/fr/events">', out["fr/events.html"])

    def test_content_lang_and_html_lang(self):
        out = build_site()
        self.assertIn('<html lang="fr">', out["fr/members.html"])
        self.assertIn('<main id="contenu" lang="en">', out["fr/members.html"])     # fallback content
        self.assertIn('<main id="contenu" lang="fr">', out["fr/index.html"])
        self.assertIn('<html lang="en">', out["legal.html"])
        self.assertIn('<main id="contenu" lang="fr">', out["legal.html"])          # only French exists
        self.assertIn('<main id="contenu" lang="en">', out["index.html"])

    def test_in_language(self):
        out = build_site()
        page = next(n for n in graph(out["fr/members.html"]) if n["@type"] == "WebPage")
        self.assertEqual(page["inLanguage"], "en")
        site = next(n for n in graph(out["fr/members.html"]) if n["@type"] == "WebSite")
        self.assertEqual(site["inLanguage"], "fr")
        post = next(n for n in graph(out["fr/blog/2026-01-01-hello.html"]) if n["@type"] == "BlogPosting")
        self.assertEqual(post["inLanguage"], "fr")


class Switcher(unittest.TestCase):
    def test_languages_nav(self):
        out = build_site()
        self.assertIn('<nav class="languages" aria-label="Langues">\n'
                      '\t<a href="../events" hreflang="en" lang="en">English</a>\n'
                      '\t<a href="events" hreflang="fr" lang="fr" aria-current="page">Français</a>\n'
                      '</nav>', out["fr/events.html"])
        self.assertIn('<a href="events" hreflang="en" lang="en" aria-current="page">English</a>\n'
                      '\t<a href="fr/events" hreflang="fr" lang="fr">Français</a>', out["events.html"])
        self.assertIn('<a href="../../blog/" hreflang="en" lang="en">English</a>', out["fr/blog/index.html"])
        self.assertIn('<a href="../fr/blog/2026-01-01-hello" hreflang="fr" lang="fr">Français</a>',
                      out["blog/2026-01-01-hello.html"])

    def test_wordmark_language_segment(self):
        out = build_site()
        self.assertIn('<a href="./">fr</a>', out["fr/events.html"])           # the segment links to /fr/
        self.assertNotIn(">en</a>", out["events.html"])
        self.assertIn('<a href="../">fr</a>', out["fr/blog/2026-01-01-hello.html"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_languages_head -v`
Expected: FAIL, `unknown placeholder {{ content_lang }}` (the build stops) — the fixture layout asks for it.

- [ ] **Step 3: `seo.py`**

```python
import languages
...

def alternates(item):
    """<link rel="alternate" hreflang> for every declared language, and
    x-default for the default one; nothing in a monolingual site."""
    if not languages.multilingual():
        return []
    path = item["path"]
    out = [f'<link rel="alternate" hreflang="{L}" href="{apex() + clean_url(path, L)}">'
           for L in languages.declared()]
    out.append(f'<link rel="alternate" hreflang="x-default" href="{apex() + clean_url(path, languages.default())}">')
    return out
```

In `head_tags`: `out = alternates(item) + [f'<meta name="robots" ...>']`; after `("og:locale", CFG["site"]["locale"])` insert, when multilingual, one `("og:locale:alternate", languages.CONFIGS[L]["site"]["locale"])` per other declared language, in declaration order. In `json_ld`: `node.update({"@id": ..., "url": url, "inLanguage": item["content_lang"]})`; `site` keeps `lang` (the interface). `breadcrumbs`: the home crumb becomes `(home["label"], a + clean_url("index.html"))` (the language's landing: `/` or `/fr/`) and the section URL `s_url = f"{a}/{languages.prefix()}{section['href']}"`; in the default language both equal today's strings.

- [ ] **Step 4: `page.py`**

```python
import languages
...

def switcher(item, res):
    """{{ languages }}: every declared language, linking to this page's
    sibling; the current one marked. Empty in a monolingual site."""
    if not languages.multilingual():
        return ""
    names = languages.CONFIGS[languages.default()].get("languages", {})
    links = []
    for L in languages.declared():
        current = ' aria-current="page"' if L == STATE["lang"] else ""
        href = res("/" + clean_url(item["path"], L).lstrip("/"))
        links.append(f'\t<a href="{href}" hreflang="{L}" lang="{L}"{current}>{H.escape(names.get(L, L))}</a>')
    label = H.escape(CFG["labels"]["languages"])
    return f'<nav class="languages" aria-label="{label}">\n' + "\n".join(links) + "\n</nav>"
```

In `render_html`, the wordmark: when `STATE["prefix"]`, prepend a segment before `parents`:

```python
        parents = ""
        if STATE["prefix"]:
            parents += f'{slash}<a href="{res("")}">{H.escape(STATE["lang"])}</a>'
```

and the landing page of a prefixed language keeps `is_landing` (`~/site` alone) — no segment there. Add to `fill`'s `computed`: `"languages": switcher(item, res)`, `"content_lang": STATE["content_lang"]`. Import `STATE` from `config`.

- [ ] **Step 5: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL` (the reference layout has neither placeholder; `alternates` is empty; `og:locale:alternate` absent; `inLanguage` equals the site language for every page of a monolingual site since `content_lang` is the default).

- [ ] **Step 6: Commit**

```bash
git add src/page.py src/seo.py tests/site/theme tests/test_languages_head.py
git commit -m "feat: language switcher, content language, hreflang and locale alternates"
```

---

### Task 5: Sitemap alternates, the text mirror's `LANGUAGES:` line, the monolingual guard

**Files:**
- Modify: `src/seo.py` (`sitemap_xml`), `src/text.py` (`render_txt`)
- Test: `tests/test_languages_outputs.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_languages_outputs.py`:

```python
import pathlib
import shutil
import unittest

from tests.helpers import build_site
from tests.test_languages import run, scratch


class Sitemap(unittest.TestCase):
    def test_alternates(self):
        out = build_site()
        sm = out["sitemap.xml"]
        self.assertIn('xmlns:xhtml="http://www.w3.org/1999/xhtml"', sm)
        self.assertIn("\t<url>\n\t\t<loc>https://test.example/fr/events</loc>\n\t\t<lastmod>2026-06-01</lastmod>\n"
                      '\t\t<xhtml:link rel="alternate" hreflang="en" href="https://test.example/events"/>\n'
                      '\t\t<xhtml:link rel="alternate" hreflang="fr" href="https://test.example/fr/events"/>\n'
                      '\t\t<xhtml:link rel="alternate" hreflang="x-default" href="https://test.example/events"/>\n'
                      "\t</url>\n", sm)
        self.assertIn("https://test.example/fr/blog/2026-02-01-only-french\n", out["sitemap.txt"])
        self.assertIn("https://test.example/blog/2026-02-01-only-french\n", out["sitemap.txt"])
        self.assertNotIn("/404", out["sitemap.txt"])


class TextMirror(unittest.TestCase):
    def test_languages_line(self):
        out = build_site()
        lines = out["txt/events.txt"].splitlines()
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "LANGUAGES: en fr")
        self.assertIn("LANGUAGES: en fr", out["txt/fr/events.txt"])
        self.assertIn("[ a venir ]", out["txt/fr/events.txt"])                   # folded
        self.assertIn("jeudi 1er janvier 2099", out["txt/fr/events.txt"])


class Monolingual(unittest.TestCase):
    """A site that declares no languages: not one byte of the feature."""

    def setUp(self):
        self.tmp, self.site = scratch()
        content = self.site / "content"
        toml = content / "site.toml"
        toml.write_text("\n".join(l for l in toml.read_text().splitlines()
                                  if not l.startswith("languages =") and l.strip() not in
                                  ('[languages]', 'en = "English"', 'fr = "Français"')) + "\n")
        (content / "site.fr.toml").unlink()
        for f in list(content.rglob("*.fr.md")):
            f.unlink()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_nothing_of_the_feature(self):
        code, err = run(self.site)
        self.assertEqual(code, 0, err)
        out = self.site / "out"
        self.assertFalse((out / "fr").exists())
        index = (out / "index.html").read_text()
        self.assertNotIn("hreflang", index)
        self.assertNotIn('<nav class="languages"', index)
        self.assertNotIn("og:locale:alternate", index)
        self.assertIn('<main id="contenu" lang="en">', index)
        self.assertNotIn("xmlns:xhtml", (out / "sitemap.xml").read_text())
        self.assertNotIn("LANGUAGES:", (out / "txt" / "index.txt").read_text())
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_languages_outputs -v`
Expected: `Sitemap` and `TextMirror` FAIL; `Monolingual` passes already (it guards).

- [ ] **Step 3: `seo.sitemap_xml`**

```python
def sitemap_xml(items):
    """One sitemap for every language. lastmod: `updated:`, else an item's
    date, else [site] updated. In a multilingual site each URL lists its
    siblings as xhtml:link alternates, x-default included."""
    multi = languages.multilingual()
    rows = []
    for it in sorted(items, key=lambda it: clean_url(it["path"], it["lang"])):
        lastmod = it["meta"].get("updated") or it["date"] or CFG["site"]["updated"]
        row = (f"\t<url>\n\t\t<loc>{H.escape(apex() + clean_url(it['path'], it['lang']))}</loc>\n"
               f"\t\t<lastmod>{lastmod}</lastmod>\n")
        if multi:
            for L in languages.declared():
                row += (f'\t\t<xhtml:link rel="alternate" hreflang="{L}" '
                        f'href="{H.escape(apex() + clean_url(it["path"], L))}"/>\n')
            row += (f'\t\t<xhtml:link rel="alternate" hreflang="x-default" '
                    f'href="{H.escape(apex() + clean_url(it["path"], languages.default()))}"/>\n')
        rows.append(row + "\t</url>\n")
    ns = ' xmlns:xhtml="http://www.w3.org/1999/xhtml"' if multi else ""
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"{ns}>\n'
            + "".join(rows) + "</urlset>\n")
```

- [ ] **Step 4: `text.render_txt`**

After `out = [rule(...)]`:

```python
    if languages.multilingual():
        out += ["", "LANGUAGES: " + " ".join(languages.declared())]
```

(`import languages`.) The existing `re.sub(r"\n{3,}", ...)` keeps the spacing right.

- [ ] **Step 5: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add src/seo.py src/text.py tests/test_languages_outputs.py
git commit -m "feat: sitemap alternates and the text mirror's languages line"
```

---

### Task 6: Content errors — an undeclared suffix

**Files:**
- Modify: `src/languages.py` (`setup()` scans content for undeclared suffixes)
- Test: `tests/test_languages.py` (add to `ConfigErrors`)

- [ ] **Step 1: Write the failing test**

Add to `ConfigErrors` in `tests/test_languages.py`:

```python
    def test_undeclared_suffix_on_a_page(self):
        (self.site / "content" / "about.de.md").write_text("---\nman: T(1)\ntitle: x\ndescription: d\ntagline: t\nnav: -\n---\n\n## Name\n\nx\n")
        (self.site / "content" / "blog" / "2026-03-01-x.es.md").write_text("---\ntitle: x\ndescription: d\n---\n\n## Name\n\nx\n")
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/about.de.md: "de" is not a declared language. Declared: en, fr', err)
        self.assertIn('error: content/blog/2026-03-01-x.es.md: "es" is not a declared language', err)
        self.assertEqual(err.count("error: "), 2)

    def test_a_dotted_name_that_is_not_a_language_is_a_page(self):
        (self.site / "content" / "v1.2.md").write_text("---\nman: T(1)\ntitle: v1.2\ndescription: A page whose name has a dot but no language suffix in it.\ntagline: t\nnav: -\n---\n\n## Name\n\nx\n")
        code, err = run(self.site)
        self.assertEqual(code, 0, err)
        self.assertTrue((self.site / "out" / "v1.2.html").is_file())
```

- [ ] **Step 2: Run to see the first fail**

Run: `python3 -m unittest tests.test_languages.ConfigErrors -v`
Expected: `test_undeclared_suffix_on_a_page` FAIL (exit 0, the files render as pages `about.de.html`).

- [ ] **Step 3: Scan in `setup()`**

In `setup()`, after the language files loop and before `if errs: fail(errs)`:

```python
    for f in sorted(CONTENT.rglob("*.md")):
        if any(part.startswith("_") for part in f.relative_to(CONTENT).parts):
            continue
        _, lang = split(f.stem)
        if lang and lang not in langs:
            errs.append(error(f, f'"{lang}" is not a declared language',
                              f"Declared: {listed} ([site] languages in {CONFIG.relative_to(CONTENT.parent)})"))
```

- [ ] **Step 4: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -t . -v 2>&1 | tail -3
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`. If the reference site has a page whose stem ends in a dotted two-letter word, the scan would refuse it: check `find $SITE/content -name '*.*.md'` first (expected: nothing).

- [ ] **Step 5: Commit**

```bash
git add src/languages.py tests/test_languages.py
git commit -m "feat: refuse a language suffix that names no declared language"
```

---

### Task 7: The starter goes bilingual; the example Caddyfile

**Files:**
- Create: `starter/content/site.fr.toml`, `starter/content/index.fr.md`, `starter/content/blog/2026-01-01-hello.fr.md`
- Modify: `starter/content/site.toml`, `starter/theme/layout.html`, `starter/theme/style.css`, `examples/Caddyfile`

- [ ] **Step 1: Starter configuration**

In `starter/content/site.toml`, `[site]`: add `languages = ["en", "fr"]` after `title_suffix`, and after `[share]` a table `[languages]` with `en = "English"` and `fr = "Français"`.

`starter/content/site.fr.toml`:

```toml
# The starter in French: only what differs from site.toml. Delete this file
# and the `languages` line of site.toml for a site in one language.

[site]
lang = "fr"
locale = "fr_FR"
manual = "Manuel de mon site"
title_suffix = " - mon site"

[labels]
skip = "aller au contenu"
nav = "Navigation principale"
languages = "Langues"
to_top = "↑ haut de page"
copy = "copier"
copied = "copié"
external = "site externe"
new_tab = "nouvel onglet"
table = "tableau"
toc = "sommaire"

[[nav]]
label = "accueil"
href = ""

[[nav]]
label = "blog"
href = "blog/"

[collections.blog]
man = "MONSITE-BLOG(7)"
empty = "Aucun article pour l'instant."
feed_title = "articles"
feed_description = "Les articles."

[dates]
weekdays = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]
first = "1er"
```

- [ ] **Step 2: Starter pages**

`starter/content/index.fr.md`: the French twin of `index.md` (same `man`, `nav:` empty; `title: mon site - un site qui se lit comme une page de manuel`, `description` of 50-160 characters, `tagline: un site qui se lit comme une page de manuel`; sections `## Nom`, `## Synopsis` (the `curl example.org` block), `## Description` (two sentences saying pages are Markdown files in `content/` and that this page is the French version of `index.md`, with `[in English](/)`), `## Voir aussi` with `[le blog](blog/)`).

`starter/content/blog/2026-01-01-hello.fr.md`: the French twin of the post (`title: Bonjour`, `author: Moi`, `tag: nouveautés`, sections `## Nom`, `## Synopsis`, `## Description` translated from the English file's meaning, kept short).

- [ ] **Step 3: Starter theme**

In `starter/theme/layout.html`: `<main id="contenu" lang="{{ content_lang }}">`; after the main `</nav>` line add `{{ languages }}`. In `starter/theme/style.css`, next to the `.nav` rules, add:

```css
/* The language switcher: a small line under the navigation. */
.languages { font-size: .9em; margin: 0 0 1em; }
.languages a { margin-right: .75em; }
.languages a[aria-current] { font-weight: bold; text-decoration: none; }
```

- [ ] **Step 4: Caddyfile**

In `examples/Caddyfile`, in the site's `handle_errors` block, before `rewrite * /404.html`:

```
		# One line per language served under a prefix: its own 404 page.
		@fr path /fr/*
		rewrite @fr /fr/404.html
```

and the same in the plain-text host's `handle_errors` for `/fr/404.txt` if that block rewrites to a file (read it; if it only writes an inline message, add nothing there). Add a comment near the top: "Undeclared language prefixes are plain 404s; to redirect `/de/*` to `/`, add `redir /de/* / permanent`."

- [ ] **Step 5: Build the starter and check**

```bash
rm -rf /tmp/starter && cp -r starter /tmp/starter && python3 build.py --root /tmp/starter --out /tmp/starter-out | head -3
ls /tmp/starter-out/fr; grep -c hreflang /tmp/starter-out/index.html; grep -o '<nav class="languages".*' /tmp/starter-out/fr/index.html | head -1
python3 -m unittest discover -s tests -t . 2>&1 | tail -1
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after >/dev/null 2>&1; diff -r -x '*.png' -x '*.ico' /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: `languages: en (default), fr` in the summary; `fr/` holds `index.html`, `blog/`, `404.html`; three `hreflang` links; the switcher; tests `OK`; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add starter examples/Caddyfile
git commit -m "feat: a bilingual starter; 404 per language in the example Caddyfile"
```

---

### Task 8: Documentation

**Files:**
- Create: `docs/languages.md`
- Modify: `docs/theme.md`, `docs/markdown.md`, `README.md`, `AGENTS.md`, `src/build.py` (docstring map), `docs/superpowers/specs/2026-09-26-languages-design.md` (§5: `WebSite` keeps the interface language)

- [ ] **Step 1: `docs/languages.md`**

```markdown
# Languages

A site may be served in several languages. The default language is at the
root; every other declared language has its own prefix (`/fr/`). **Every
declared language is a complete tree**: a page that is not translated is
still served, with the content of the default language, or of any language
that has it.

---

## Declare the languages

```toml
# content/site.toml
[site]
lang = "en"                 # the default language, at the root
languages = ["en", "fr"]    # every language served; absent: one language, no prefix

[languages]                 # names shown by the language switcher
en = "English"
fr = "Français"
```

`content/site.fr.toml` holds what differs in French: `[site] lang`,
`locale`, `manual`, `title_suffix`, `[labels]`, `[[nav]]` (replaced as a
whole), the words of each `[collections.<name>]`, `[dates]`, `[share]`'s
texts. Layers, the last winning:

```
defaults.toml < theme/theme.toml < theme/theme.fr.toml < content/site.toml < content/site.fr.toml
```

A declared language without a `site.fr.toml` gets the default language's
words: a site may start translating one word at a time.

## Translate a page

Put `about.fr.md` next to `about.md`. The same for a folder's index
(`hello/index.fr.md`) and for collection items (`2026-01-01-hello.fr.md`).
To render a page in a language, the build takes, in order:

1. `about.fr.md`;
2. `about.<default>.md`;
3. `about.md`;
4. `about.<other>.md`, the other declared languages in declaration order.

The chosen file's language is the page's **content language**; the layout
gets it as `{{ content_lang }}` for `<main lang="...">`, and screen readers
read a fallback page in its real language.

A suffix that names no declared language stops the build (a typo must not
become a page named `about.xx`). A stem like `v1.2` is a plain name.

## Links

Links are written from the site root, as always (`[events](events)`), and
resolve **inside the language**: in `/fr/about`, `events` is `/fr/events`.
A link that starts with `/` is taken from the site root, so a page can
point at another language: `[in English](/events)`, `[en français](/fr/events)`.

## What the build writes

| | Default language | Other language `fr` |
|---|---|---|
| pages | `events.html` | `fr/events.html` |
| text mirror | `txt/events.txt` | `txt/fr/events.txt` |
| RSS | `blog/feed.xml` | `fr/blog/feed.xml` |
| 404 | `404.html` | `fr/404.html` |
| calendar, sitemap, robots.txt, manifest, icons | once, at the root | - |

Every page carries `<link rel="alternate" hreflang>` for every language and
`x-default`; `og:locale:alternate`; `inLanguage` is the content language.
The sitemap lists every URL with its `xhtml:link` alternates. The calendar
is written once: a calendar has no interface language, and two would show
every event twice.

The text mirror shows the languages after its header: `LANGUAGES: en fr`.

## The theme

Two placeholders (`docs/theme.md`): `{{ content_lang }}`, and
`{{ languages }}`, a `<nav class="languages">` with one link per declared
language, the current one `aria-current="page"`, named from `[languages]`.
The wordmark gains a segment: `~/site/fr/blog/hello`, `fr` linking to the
language's landing page.

## The server

`examples/Caddyfile`: one `@fr path /fr/*` matcher per prefixed language in
`handle_errors`, so `/fr/nothing` gets `/fr/404.html`. An undeclared prefix
is a plain 404; redirect it if you like (`redir /de/* / permanent`). The
text-mirror rewrite (`try_files {path}.txt ...`) follows the prefix on its
own.

## Limits

The text mirror folds to ASCII and assumes one column per character: a
Latin alphabet. The generator knows no language name; every word comes
from the language's file.
```

- [ ] **Step 2: Other documents**

- `docs/theme.md`: placeholders table gains `{{ languages }}` and `{{ content_lang }}` (values as above); the classes table gains `.languages`; a sentence in "The layout must keep": `<main lang="{{ content_lang }}">` recommended for multilingual sites.
- `docs/markdown.md`: in the links section, the `/`-leading rule; in the front matter/file naming section, the `.fr.md` suffix with a pointer to `docs/languages.md`.
- `README.md`: a bullet in "What it gives you" ("Several languages: the default at the root, the others under `/fr/`; untranslated pages fall back; `hreflang`, one sitemap, feeds per language — `docs/languages.md`"); the project layout shows `site.fr.toml` and `index.fr.md`.
- `AGENTS.md`: §2.1 gains "The generator knows no language name: every word of a language comes from the site's `site.<lang>.toml`; the starter's French files are the feature's example, the one place in this repository in another language." §3's map gains `languages.py`. §9 gains the bilingual starter build as a check.
- `src/build.py` docstring map: `languages.py     the declared languages, site.<lang>.toml, the fallback that completes every tree`.
- Spec §5: "`inLanguage` is the content language on the page node; `WebSite` keeps the language of the interface (it is one node per site)."

- [ ] **Step 3: Checks and commit**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | tail -1
SITE="$(cd .. && pwd)"; NAME="$(python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["site"]["name"])' "$SITE/content/site.toml")"
grep -rniE "$NAME|$(basename "$SITE")" --exclude-dir=.git --exclude-dir=.superpowers .; echo "(expected: nothing)"
git add docs README.md AGENTS.md src/build.py
git commit -m "docs: languages"
```

---

### Task 9: Final verification

- [ ] **Step 1**: full suite; reference diff `IDENTICAL`; the bilingual starter builds; AGENTS.md §9 steps 3-5 on `/tmp/starter-out` (75 columns, no escape in `txt/`, `ansi` equals stripped `txt`, one `<h1>`, no script but the theme's and JSON-LD, no foreign request) — on both `/` and `/fr/` pages.
- [ ] **Step 2**: every error of spec §3 by hand on a scratch copy of the fixture, one line and exit 1 each; two at once give two lines.
- [ ] **Step 3**: `curl`-style check of the text mirror: `cat /tmp/starter-out/txt/fr/index.txt | head -5` shows the French header rule and `LANGUAGES: en fr`.
- [ ] **Step 4**: hand over with `superpowers:finishing-a-development-branch`.
