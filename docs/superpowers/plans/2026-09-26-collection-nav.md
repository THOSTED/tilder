# Collection navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give themes a collection sidebar (`{{ collection_nav }}`), previous/next links (`{{ prev }}`, `{{ next }}`, and a line in the text mirror for `SEQUENTIAL` types), and let a type write files in every language (`LOCALIZED_OUTPUTS`).

**Architecture:** A new module `src/sequence.py` holds everything about order, groups and neighbours, as pure functions (HTML fragments and the text line). `page.render_html` and `text.render_txt` call it; `build.py` passes each language pass's items along and, for `LOCALIZED_OUTPUTS` types, calls `outputs()` in every pass with the language prefix. Two new type flags join `contenttypes.FLAGS`.

**Tech Stack:** Python 3.11+ standard library only; `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-26-collection-nav-design.md`

## Global Constraints

- Standard library only; no new dependency (AGENTS.md §2.2).
- Everything in English: code, comments, docs, commit messages, defaults (AGENTS.md).
- The builder holds no user-facing text: new words go in `defaults.toml`, English, neutral, commented (AGENTS.md §2.1).
- The builder never writes an inline `style`, a colour or a font (AGENTS.md §5).
- Text mirror: 75 columns (`config.WIDTH`), ASCII only in `txt/` (`fold.to_ascii`), `ansi/` stripped of escapes equals `txt/` (AGENTS.md §4).
- A new class or placeholder: update `docs/theme.md` **and** `starter/theme/` (AGENTS.md §5).
- A theme that uses none of the placeholders and types that set neither flag: output unchanged.
- Commits: Conventional Commits, author `Théau TROVA <theau@thosted.fr>`, **no** `Co-Authored-By` trailer.
- Tests: `python3 -m unittest discover -s tests -t .` from the repository root, all green after every task.
- Work on branch `feat/collection-nav` (already created).

## Review Focus

- A title with HTML characters (`<`, `&`) in the sidebar or a prev/next link: escaped, never raw HTML (Task 2 test `test_titles_are_escaped`).
- A page served in fallback (French pass, English file): the sidebar and neighbours use the title of the file actually served in that language (Task 3 test `test_french_pass_uses_served_titles`).
- A page outside any collection whose layout uses the placeholders: all three empty, build succeeds (Task 3 test `test_outside_collections_is_empty`).
- Very long titles in the text line: never over 75 columns, cut with `...` (Task 2 test `test_line_cuts_long_titles`).
- A type flag set to a wrong kind (`SEQUENTIAL = "yes"`): a load error naming the attribute, not a crash (Task 1 test `test_flag_kind_is_checked`).

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/sequence.py` | create | order, groups, neighbours; the nav/prev/next HTML; the text line |
| `src/contenttypes.py` | modify `FLAGS` | `SEQUENTIAL`, `LOCALIZED_OUTPUTS` defaults and kind checks |
| `src/build.py` | modify the pass loop | pass `items` to rendering; per-language outputs; module map |
| `src/page.py` | modify `render_html` | three new computed placeholders |
| `src/text.py` | modify `render_txt` | the optional line before the footer rule |
| `defaults.toml` | modify `[labels]` | `collection_nav`, `prev`, `next` |
| `tests/site/...` | fixture | a `guide` theme type, a `guides` collection, `layouts/guide.html` |
| `tests/test_sequence.py` | create | unit tests of `sequence.py` |
| `tests/test_collection_nav.py` | create | build-level tests |
| `tests/test_collections.py`, `tests/test_theme_type.py` | modify | summaries now list the `guide` type and `guides` collection |
| `starter/content/site.fr.toml`, `starter/theme/layout.html`, `starter/theme/style.css` | modify | French labels, prev/next in the layout, the new classes styled |
| `docs/theme.md`, `docs/types.md`, `docs/markdown.md`, `README.md` | modify | the contract |

---

### Task 1: Type flags, per-language outputs, and the fixture

**Files:**
- Modify: `src/contenttypes.py` (`FLAGS`, near line 30)
- Modify: `src/build.py:124-130` (the collections loop at the end of a pass)
- Create: `tests/site/theme/types/guide.py`
- Create: `tests/site/content/guides/index.md`, `intro.md`, `setup.md`, `setup.fr.md`, `deploy.md`, `tuning.md`
- Modify: `tests/site/content/site.toml`, `tests/site/content/site.fr.toml`
- Modify: `tests/test_collections.py:169-171`, `tests/test_theme_type.py`
- Create: `tests/test_collection_nav.py`

**Interfaces:**
- Produces: every loaded type module has `SEQUENTIAL: bool` and `LOCALIZED_OUTPUTS: bool` (default `False`). The fixture has a collection `guides` of type `guide`, items in order `intro` (Introduction), `setup` (Setup, group Basics; French: Installation), `deploy` (Deployment, group Advanced), `tuning` (Tuning, group Basics). The guide type writes `guides/index.json`, a JSON list of titles, per language.

- [ ] **Step 1: Add the fixture type**

`tests/site/theme/types/guide.py`:

```python
"""A guide: one page of a sequence, in order, optionally grouped. A theme
type that uses collection navigation (SEQUENTIAL) and writes a file in
every language (LOCALIZED_OUTPUTS)."""

import json

NAME = "guide"
SEQUENTIAL = True
LOCALIZED_OUTPUTS = True
DEFAULTS = {"man": "SITE-GUIDES(7)", "nav": "guides/", "index": "guides/index.json"}


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("tagline", "")
    meta.setdefault("description", "")


def sort_key(item, conf):
    return (int(item["meta"].get("order", 1000)), item["slug"])


def entry(item, link, conf):
    return None


def outputs(items, conf):
    """The titles, in order: a stand-in for a search index."""
    return {conf["index"]: json.dumps([it["meta"]["title"] for it in items])}
```

- [ ] **Step 2: Add the fixture content**

`tests/site/content/guides/index.md`:

```markdown
---
man: TEST-GUIDES(7)
title: Guides
description: The guides of the fixture site, a sequence to test collection navigation.
tagline: in order
nav: -
---

## Name

guides - a sequence {mono}
```

`tests/site/content/guides/intro.md`:

```markdown
---
title: Introduction
description: The first guide of the fixture, with no group, to test the loose items.
order: 1
---

## Name

introduction - the first guide {mono}
```

`tests/site/content/guides/setup.md`:

```markdown
---
title: Setup
description: The second guide of the fixture, in the Basics group, translated to French.
order: 2
group: Basics
---

## Name

setup - the second guide {mono}
```

`tests/site/content/guides/setup.fr.md`:

```markdown
---
title: Installation
description: Le deuxième guide du site de test, dans le groupe Basics, traduit en français.
order: 2
group: Basics
---

## Nom

installation - le deuxième guide {mono}
```

`tests/site/content/guides/deploy.md`:

```markdown
---
title: Deployment
description: The third guide of the fixture, alone in the Advanced group, between two Basics.
order: 3
group: Advanced
---

## Name

deployment - the third guide {mono}
```

`tests/site/content/guides/tuning.md`:

```markdown
---
title: Tuning
description: The fourth guide of the fixture, back in the Basics group, the last of the order.
order: 4
group: Basics
---

## Name

tuning - the fourth guide {mono}
```

Append to `tests/site/content/site.toml`:

```toml

[collections.guides]
type = "guide"
nav_label = "Guide contents"
```

Append to `tests/site/content/site.fr.toml`:

```toml

[collections.guides]
nav_label = "Sommaire du guide"
```

- [ ] **Step 3: Write the failing tests**

`tests/test_collection_nav.py`:

```python
import json
import pathlib
import shutil
import tempfile
import textwrap
import unittest

from tests.helpers import build_site
import contenttypes
from config import load_config


class Flags(unittest.TestCase):
    def test_defaults_and_theme_values(self):
        load_config()
        types = contenttypes.load()
        for name in ("page", "post", "event", "member", "talk"):
            self.assertFalse(types[name].SEQUENTIAL, name)
            self.assertFalse(types[name].LOCALIZED_OUTPUTS, name)
        self.assertTrue(types["guide"].SEQUENTIAL)
        self.assertTrue(types["guide"].LOCALIZED_OUTPUTS)

    def test_flag_kind_is_checked(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            (tmp / "odd.py").write_text(textwrap.dedent('''
                NAME = "odd"
                SEQUENTIAL = "yes"
                def entry(item, link, conf):
                    return None
            '''))
            load_config()
            contenttypes.load([contenttypes.BUILTIN, tmp])
            messages = [str(e) for e in contenttypes.ERRORS]
        finally:
            shutil.rmtree(tmp)
        self.assertTrue(any("SEQUENTIAL must be a bool, not a str" in m for m in messages), messages)
        self.assertNotIn("odd", contenttypes.TYPES)


class LocalizedOutputs(unittest.TestCase):
    def test_one_file_per_language(self):
        out = build_site()
        self.assertEqual(json.loads(out["guides/index.json"]),
                         ["Introduction", "Setup", "Deployment", "Tuning"])
        self.assertEqual(json.loads(out["fr/guides/index.json"]),
                         ["Introduction", "Installation", "Deployment", "Tuning"])

    def test_other_outputs_stay_once(self):
        out = build_site()
        self.assertIn("events.ics", out)
        self.assertNotIn("fr/events.ics", out)
```

- [ ] **Step 4: Run them to see them fail**

Run: `python3 -m unittest tests.test_collection_nav -v`
Expected: FAIL. `test_defaults_and_theme_values` fails with `AttributeError: module ... has no attribute 'SEQUENTIAL'`, `test_flag_kind_is_checked` finds no such error, and `test_one_file_per_language` raises `KeyError: 'fr/guides/index.json'`.

- [ ] **Step 5: Add the flags**

In `src/contenttypes.py`, extend `FLAGS`:

```python
FLAGS = {"DATED": False, "ARTICLE": False, "OG_TYPE": "website", "SCRIPT": "",
         "LAYOUT": None, "DEFAULTS": {}, "MARKERS": {},
         "SEQUENTIAL": False, "LOCALIZED_OUTPUTS": False}
```

`_check` already checks each flag's kind against its default (`bool`) and `_complete` fills the missing ones: nothing else to change there.

- [ ] **Step 6: Call `outputs()` per language when asked**

In `src/build.py`, replace the two lines

```python
            if lang == langs[0]:
                out.update(contenttypes.call(CONTENT / conf["dir"], module, "outputs", items[name], conf))
```

with

```python
            # LOCALIZED_OUTPUTS: the type's files in every language, under
            # its prefix (a search index); else once, in the default.
            if module.LOCALIZED_OUTPUTS:
                files = contenttypes.call(CONTENT / conf["dir"], module, "outputs", items[name], conf)
                out.update({prefix + p: text for p, text in files.items()})
            elif lang == langs[0]:
                out.update(contenttypes.call(CONTENT / conf["dir"], module, "outputs", items[name], conf))
```

and update the comment above the loop ("the types' own files (an iCalendar) once, in the default language") to add ", unless the type sets LOCALIZED_OUTPUTS".

- [ ] **Step 7: Run the new tests**

Run: `python3 -m unittest tests.test_collection_nav -v`
Expected: PASS (4 tests)

- [ ] **Step 8: Update the summaries the fixture changed**

Run the whole suite: `python3 -m unittest discover -s tests -t .`

The known failures come from the new type and collection. Fix them as follows.

- `tests/test_theme_type.py`, `test_loaded_from_the_theme`:
  `["event", "member", "page", "post", "guide", "talk"]`.
- `tests/test_theme_type.py`, `test_summary_names_the_theme_type`:
  `"types: event, member, page, post; from theme: guide, talk\n"`.
- `tests/test_theme_type.py`, `test_theme_member_replaces_the_builtin_silently`:
  `"types: event, page, post; from theme: member, guide, talk"`. A replaced
  key keeps its place in the `TYPES` dict, so `member` stays where it was.
- `tests/test_collections.py:169-171`: the same types line, and the
  collections line gains `, guides (guide, 4 items)` at the end, in
  declaration order.

Any other failure is a real regression: investigate it, and don't adjust
the test. Run again.
Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/contenttypes.py src/build.py tests/
git commit -m "feat: SEQUENTIAL and LOCALIZED_OUTPUTS type flags; outputs per language"
```

---

### Task 2: `sequence.py` and the labels

**Files:**
- Create: `src/sequence.py`
- Modify: `defaults.toml` (`[labels]`)
- Modify: `tests/site/content/site.fr.toml` (`[labels]`)
- Modify: `src/build.py` (the module map in the docstring)
- Create: `tests/test_sequence.py`

**Interfaces:**
- Consumes: items as `load_items` returns them (dicts with `"path"`, `"meta"`, `"type"`), `colls` as `contenttypes.collections()` returns it, `items` as `{collection name: [item]}`.
- Produces:
  - `shown(path: str, colls: dict, items: dict) -> tuple[str | None, list]`: the collection name and its items, for an item's page or the collection's own page; `(None, [])` otherwise.
  - `groups(items: list) -> list[tuple[str | None, list]]`
  - `neighbours(items: list, path: str) -> tuple[dict | None, dict | None]`
  - `title(item: dict) -> str`
  - `nav_html(items: list, path: str, conf: dict, res) -> str`, where `res` is `callable(str) -> str`, resolving a root-relative page target.
  - `link_html(kind: str, item: dict | None, res) -> str`, where `kind` is `"prev"` or `"next"`.
  - `line(prev: str | None, nxt: str | None) -> str`
  - `txt_line(item: dict, colls: dict, items: dict) -> str`

- [ ] **Step 1: Add the labels**

In `defaults.toml`, after the `languages = "Languages"` line of `[labels]`:

```toml
collection_nav = "In this section"  # names the {{ collection_nav }} sidebar; a collection may set nav_label
prev = "previous"                   # {{ prev }}, and the text mirror's line of a sequential type
next = "next"                       # {{ next }}
```

In `tests/site/content/site.fr.toml`, under `[labels]`:

```toml
collection_nav = "Dans cette section"
prev = "précédent"
next = "suivant"
```

- [ ] **Step 2: Write the failing tests**

`tests/test_sequence.py`:

```python
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import sequence
from config import load_config


def it(path, title, group=None, **meta):
    m = {"title": title, **meta}
    if group is not None:
        m["group"] = group
    return {"path": path, "meta": m}


A = it("docs/a.html", "Alpha")
B = it("docs/b.html", "Beta", "Basics")
C = it("docs/c.html", "Gamma", "Advanced")
D = it("docs/d.html", "Delta", "Basics")
ITEMS = [A, B, C, D]
COLLS = {"docs": {"dir": "docs", "type": "doc"}, "blog": {"dir": "blog", "type": "post"}}
ALL = {"docs": ITEMS, "blog": [it("blog/x.html", "X")]}
same = lambda u: u


class Order(unittest.TestCase):
    def test_shown(self):
        self.assertEqual(sequence.shown("docs/c.html", COLLS, ALL), ("docs", ITEMS))
        self.assertEqual(sequence.shown("docs/index.html", COLLS, ALL), ("docs", ITEMS))
        self.assertEqual(sequence.shown("docs.html", COLLS, ALL), ("docs", ITEMS))
        self.assertEqual(sequence.shown("about.html", COLLS, ALL), (None, []))
        self.assertEqual(sequence.shown("blog/index.html", COLLS, {}), ("blog", []))

    def test_groups_first_appearance_loose_first(self):
        self.assertEqual(sequence.groups(ITEMS), [(None, [A]), ("Basics", [B, D]), ("Advanced", [C])])
        self.assertEqual(sequence.groups([A]), [(None, [A])])
        self.assertEqual(sequence.groups([]), [])
        self.assertEqual(sequence.groups([it("p.html", "P", 2024)]), [("2024", [it("p.html", "P", 2024)])])

    def test_neighbours_ignore_groups(self):
        self.assertEqual(sequence.neighbours(ITEMS, "docs/a.html"), (None, B))
        self.assertEqual(sequence.neighbours(ITEMS, "docs/c.html"), (B, D))
        self.assertEqual(sequence.neighbours(ITEMS, "docs/d.html"), (C, None))
        self.assertEqual(sequence.neighbours(ITEMS, "docs/index.html"), (None, None))
        self.assertEqual(sequence.neighbours([A], "docs/a.html"), (None, None))

    def test_title_falls_back_to_the_slug(self):
        self.assertEqual(sequence.title({"path": "docs/x.html", "meta": {}, "slug": "x"}), "x")


class Html(unittest.TestCase):
    def setUp(self):
        load_config()

    def test_nav(self):
        self.assertEqual(sequence.nav_html(ITEMS, "docs/b.html", {}, same), "\n".join([
            '<nav class="collection-nav" aria-label="In this section">',
            "<ul>",
            '\t<li><a href="docs/a">Alpha</a></li>',
            '\t<li class="collection-group"><span class="collection-group-label">Basics</span>',
            "\t<ul>",
            '\t\t<li><a href="docs/b" aria-current="page">Beta</a></li>',
            '\t\t<li><a href="docs/d">Delta</a></li>',
            "\t</ul>",
            "\t</li>",
            '\t<li class="collection-group"><span class="collection-group-label">Advanced</span>',
            "\t<ul>",
            '\t\t<li><a href="docs/c">Gamma</a></li>',
            "\t</ul>",
            "\t</li>",
            "</ul>",
            "</nav>"]))

    def test_nav_label_and_empty(self):
        self.assertIn('aria-label="Doc pages"', sequence.nav_html([A], "", {"nav_label": "Doc pages"}, same))
        self.assertEqual(sequence.nav_html([], "docs/a.html", {}, same), "")

    def test_links(self):
        self.assertEqual(sequence.link_html("prev", A, same),
                         '<a class="prev" rel="prev" href="docs/a"><span class="prev-label">previous</span> Alpha</a>')
        self.assertEqual(sequence.link_html("next", D, same),
                         '<a class="next" rel="next" href="docs/d"><span class="next-label">next</span> Delta</a>')
        self.assertEqual(sequence.link_html("next", None, same), "")

    def test_titles_are_escaped(self):
        odd = it("docs/o.html", "A <b> & c", "x < y")
        self.assertIn(">A &lt;b&gt; &amp; c</a>", sequence.nav_html([odd], "", {}, same))
        self.assertIn(">x &lt; y</span>", sequence.nav_html([odd], "", {}, same))
        self.assertIn(" A &lt;b&gt; &amp; c</a>", sequence.link_html("prev", odd, same))


class Line(unittest.TestCase):
    def setUp(self):
        load_config()

    def test_both_sides(self):
        self.assertEqual(sequence.line("Introduction", "Deployment"),
                         "previous: Introduction" + " " * 37 + "next: Deployment")

    def test_one_side(self):
        self.assertEqual(sequence.line(None, "Setup"), " " * 64 + "next: Setup")
        self.assertEqual(sequence.line("Tuning", None), "previous: Tuning")
        self.assertEqual(sequence.line(None, None), "")

    def test_line_cuts_long_titles(self):
        both = sequence.line("A" * 60, "B" * 60)
        self.assertEqual(both, "previous: " + "A" * 23 + "..." + "  " + "next: " + "B" * 28 + "...")
        self.assertEqual(len(both), 75)
        short_long = sequence.line("Intro", "B" * 80)
        self.assertEqual(short_long, "previous: Intro  next: " + "B" * 49 + "...")
        self.assertEqual(len(short_long), 75)
        self.assertEqual(len(sequence.line(None, "B" * 90)), 75)

    def test_ascii(self):
        self.assertEqual(sequence.line("Étape à suivre", None), "previous: Etape a suivre")

    def test_txt_line_only_for_sequential_types(self):
        seq = type("T", (), {"SEQUENTIAL": True})
        flat = type("T", (), {"SEQUENTIAL": False})
        items = {"docs": [dict(x, type=seq) for x in ITEMS]}
        self.assertEqual(sequence.txt_line(items["docs"][0], COLLS, items), " " * 65 + "next: Beta")
        plain = [dict(x, type=flat) for x in ITEMS]
        self.assertEqual(sequence.txt_line(plain[0], COLLS, {"docs": plain}), "")
```

- [ ] **Step 3: Run them to see them fail**

Run: `python3 -m unittest tests.test_sequence -v`
Expected: ERROR `ModuleNotFoundError: No module named 'sequence'`

- [ ] **Step 4: Write `src/sequence.py`**

```python
"""Collection navigation: a collection's items in order as a sidebar
({{ collection_nav }}), a page's neighbours ({{ prev }}, {{ next }}), and
their line in the text mirror, for a SEQUENTIAL type. The order is the one
load_items returns (the type's sort_key); groups come from the items'
`group:`. docs/theme.md is the contract."""

import html as H

from config import CFG, WIDTH
from fold import to_ascii

GAP = 2  # the least space between the two sides of the text line


def shown(path, colls, items):
    """(name, items) of the collection a page shows: the one it is an item
    of, or the one whose own page it is (<dir>/index.html, or <dir>.html
    beside the folder: a bare list marker's rule). (None, []) else."""
    for name, its in items.items():
        if any(it["path"] == path for it in its):
            return name, its
    folder = path[:-5].removesuffix("/index")
    for name, conf in colls.items():
        if folder == conf["dir"]:
            return name, items.get(name, [])
    return None, []


def groups(items):
    """[(label or None, [item])]: the items without a group first, then each
    group in the order of its first item."""
    loose, named = [], {}
    for it in items:
        g = it["meta"].get("group")
        if g is None or g == "":
            loose.append(it)
        else:
            named.setdefault(str(g), []).append(it)
    return ([(None, loose)] if loose else []) + list(named.items())


def neighbours(items, path):
    """(previous item, next item) of the page in the order, groups ignored;
    None at an end, or both when the page is not one of the items."""
    paths = [it["path"] for it in items]
    if path not in paths:
        return None, None
    i = paths.index(path)
    return (items[i - 1] if i > 0 else None,
            items[i + 1] if i + 1 < len(items) else None)


def title(item):
    return item["meta"].get("title") or item.get("slug", "")


def nav_html(items, path, conf, res):
    """{{ collection_nav }}: every item, grouped, the page's own marked.
    `res` resolves a root-relative page target from the page."""
    if not items:
        return ""
    label = H.escape(conf.get("nav_label") or CFG["labels"]["collection_nav"])

    def li(it, ind):
        current = ' aria-current="page"' if it["path"] == path else ""
        return f'{ind}<li><a href="{res(it["path"][:-5])}"{current}>{H.escape(title(it))}</a></li>'

    out = [f'<nav class="collection-nav" aria-label="{label}">', "<ul>"]
    for group, its in groups(items):
        if group is None:
            out += [li(it, "\t") for it in its]
            continue
        out.append(f'\t<li class="collection-group"><span class="collection-group-label">'
                   f'{H.escape(group)}</span>')
        out.append("\t<ul>")
        out += [li(it, "\t\t") for it in its]
        out += ["\t</ul>", "\t</li>"]
    out += ["</ul>", "</nav>"]
    return "\n".join(out)


def link_html(kind, item, res):
    """{{ prev }} or {{ next }} (kind "prev" or "next"): a link to the
    neighbour, labelled from [labels]; empty without one."""
    if item is None:
        return ""
    label = H.escape(CFG["labels"][kind])
    return (f'<a class="{kind}" rel="{kind}" href="{res(item["path"][:-5])}">'
            f'<span class="{kind}-label">{label}</span> {H.escape(title(item))}</a>')


def clip(text, width):
    return text if len(text) <= width else text[:width - 3] + "..."


def line(prev, nxt):
    """The text mirror's line: `previous: <title>` on the left, `next:
    <title>` on the right, ASCII, WIDTH columns at most, a title cut with
    ... when both do not fit. Empty when there is neither."""
    left = f"{to_ascii(CFG['labels']['prev'])}: {to_ascii(prev)}" if prev else ""
    right = f"{to_ascii(CFG['labels']['next'])}: {to_ascii(nxt)}" if nxt else ""
    if left and right and len(left) + len(right) > WIDTH - GAP:
        room = WIDTH - GAP
        half = room // 2
        if len(left) <= half:
            right = clip(right, room - len(left))
        elif len(right) <= half:
            left = clip(left, room - len(right))
        else:
            left, right = clip(left, half), clip(right, room - half)
    left, right = clip(left, WIDTH), clip(right, WIDTH)
    if not left and not right:
        return ""
    if left and right:
        return left + " " * (WIDTH - len(left) - len(right)) + right
    return left or " " * (WIDTH - len(right)) + right


def txt_line(item, colls, items):
    """The line for an item's text mirror: only for a SEQUENTIAL type."""
    if not item["type"].SEQUENTIAL:
        return ""
    _, its = shown(item["path"], colls, items)
    prev, nxt = neighbours(its, item["path"])
    return line(prev and title(prev), nxt and title(nxt))
```

Note: the `test_one_side` expectation for `line("Tuning", None)` has no
trailing spaces: the single-left case returns `left` alone.

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest tests.test_sequence -v`
Expected: PASS (13 tests)

- [ ] **Step 6: Add the module to the map**

In the docstring of `src/build.py`, after the `contenttypes.py` line:

```
    sequence.py      a collection's order: sidebar, previous/next, the text line
```

In `AGENTS.md` §3, after the `contenttypes.py` line:

```
  sequence.py     a collection's order: the sidebar, previous/next, their text line
```

- [ ] **Step 7: Run the whole suite and commit**

Run: `python3 -m unittest discover -s tests -t .`
Expected: all pass.

```bash
git add src/sequence.py src/build.py defaults.toml AGENTS.md tests/test_sequence.py tests/site/content/site.fr.toml
git commit -m "feat: sequence.py, a collection's order, sidebar and neighbours"
```

---

### Task 3: The three placeholders in the layout

**Files:**
- Modify: `src/page.py` (`render_html`, from line 242)
- Modify: `src/build.py:108` (the `render_html` call)
- Create: `tests/site/theme/layouts/guide.html`
- Modify: `tests/test_collection_nav.py`

**Interfaces:**
- Consumes: `sequence.shown`, `sequence.neighbours`, `sequence.nav_html`, `sequence.link_html` (Task 2).
- Produces: `render_html(item, sections, preamble=(), colls=None, items=None)`, and the layout placeholders `collection_nav`, `prev`, `next`.

- [ ] **Step 1: Add the fixture layout**

In `tests/site/content/guides/index.md`, add `layout: guide` as the last
front-matter line (after `nav: -`): the collection's own page uses the
layout too.

`tests/site/theme/layouts/guide.html`, the fixture's `layout.html` with a
body class, the sidebar and the neighbours:

```html
<!DOCTYPE html>
<html lang="{{ site.lang }}">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<meta name="description" content="{{ page.description }}">
<link rel="stylesheet" href="{{ root }}style.css">
<link rel="canonical" href="{{ canonical }}">{{ feeds }}
{{ head }}
</head>
<body class="layout-guide {{ type }}">
<a class="skip" href="#contenu">{{ labels.skip }}</a>
<nav class="nav" aria-label="{{ labels.nav }}">
{{ nav }}
</nav>
{{ languages }}
{{ brand }}
{{ collection_nav }}
<main id="contenu" lang="{{ content_lang }}">
{{ body }}
{{ prev }}
{{ next }}
</main>
{{ script }}</body>
</html>
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_collection_nav.py`:

```python
from tests.helpers import rebuild
from config import CONTENT

SETUP_NAV = "\n".join([
    '<nav class="collection-nav" aria-label="Guide contents">',
    "<ul>",
    '\t<li><a href="intro">Introduction</a></li>',
    '\t<li class="collection-group"><span class="collection-group-label">Basics</span>',
    "\t<ul>",
    '\t\t<li><a href="setup" aria-current="page">Setup</a></li>',
    '\t\t<li><a href="tuning">Tuning</a></li>',
    "\t</ul>",
    "\t</li>",
    '\t<li class="collection-group"><span class="collection-group-label">Advanced</span>',
    "\t<ul>",
    '\t\t<li><a href="deploy">Deployment</a></li>',
    "\t</ul>",
    "\t</li>",
    "</ul>",
    "</nav>"])


class Placeholders(unittest.TestCase):
    def test_sidebar_on_an_item(self):
        page = build_site()["guides/setup.html"]
        self.assertIn(SETUP_NAV, page)
        self.assertEqual(SETUP_NAV.count("aria-current"), 1)

    def test_neighbours_ignore_groups(self):
        out = build_site()
        deploy = out["guides/deploy.html"]
        self.assertIn('<a class="prev" rel="prev" href="setup"><span class="prev-label">previous</span> Setup</a>', deploy)
        self.assertIn('<a class="next" rel="next" href="tuning"><span class="next-label">next</span> Tuning</a>', deploy)
        self.assertNotIn('rel="prev"', out["guides/intro.html"])
        self.assertNotIn('rel="next"', out["guides/tuning.html"])

    def test_collection_page_shows_the_sidebar_only(self):
        index = build_site()["guides/index.html"]
        self.assertIn('<nav class="collection-nav" aria-label="Guide contents">', index)
        nav = index[index.index('<nav class="collection-nav"'):]
        nav = nav[:nav.index("</nav>")]
        self.assertNotIn("aria-current", nav)
        self.assertNotIn('rel="prev"', index)
        self.assertNotIn('rel="next"', index)

    def test_french_pass_uses_served_titles(self):
        deploy = build_site()["fr/guides/deploy.html"]
        self.assertIn('<nav class="collection-nav" aria-label="Sommaire du guide">', deploy)
        self.assertIn('<a href="setup">Installation</a>', deploy)
        self.assertIn('<a class="prev" rel="prev" href="setup"><span class="prev-label">précédent</span> Installation</a>', deploy)
        self.assertIn('<span class="next-label">suivant</span> Tuning</a>', deploy)

    def test_outside_collections_is_empty(self):
        page = CONTENT / "loose.md"
        page.write_text("---\nman: TEST(1)\ntitle: loose\ndescription: A page of the fixture outside every collection, with the guide layout.\n"
                        "tagline: t\nnav: -\nlayout: guide\n---\n\n## Name\n\nloose {mono}\n")
        try:
            out = rebuild()
        finally:
            page.unlink()
        self.assertIn('<body class="layout-guide page">', out["loose.html"])
        self.assertNotIn("collection-nav", out["loose.html"])
        self.assertNotIn('rel="prev"', out["loose.html"])

    def test_layouts_without_the_placeholders_are_unchanged(self):
        post = build_site()["blog/2026-01-01-hello.html"]
        self.assertNotIn("collection-nav", post)
        self.assertNotIn('rel="prev"', post)
        self.assertNotIn('rel="next"', post)
```

- [ ] **Step 3: Run them to see them fail**

Run: `python3 -m unittest tests.test_collection_nav -v`
Expected: the build fails with `theme/layouts/guide.html: unknown placeholder {{ collection_nav }}`, so every build test ERRORs.

- [ ] **Step 4: Compute the placeholders**

In `src/page.py`, add `import sequence` to the imports (alphabetically,
after `import languages`), and change the signature and the `fill` call:

```python
def render_html(item, sections, preamble=(), colls=None, items=None):
```

Just before `if meta.get("layout"):`, add:

```python
    # A collection's order: the sidebar, and the page's neighbours.
    coll, its = sequence.shown(path, colls or {}, items or {})
    prev, nxt = sequence.neighbours(its, path)
    conf = (colls or {}).get(coll, {})
```

and in the dict passed to `fill`, after `"languages": switcher(item, res),`:

```python
        "collection_nav": sequence.nav_html(its, path, conf, res),
        "prev": sequence.link_html("prev", prev, res),
        "next": sequence.link_html("next", nxt, res),
```

In `src/build.py`, pass the items:

```python
                out[prefix + it["path"]] = render_html(it, sections, preamble, colls, items)
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest tests.test_collection_nav -v`
Expected: PASS (10 tests)

- [ ] **Step 6: Run the whole suite and commit**

Run: `python3 -m unittest discover -s tests -t .`
Expected: all pass.

```bash
git add src/page.py src/build.py tests/
git commit -m "feat: {{ collection_nav }}, {{ prev }} and {{ next }} placeholders"
```

---

### Task 4: The line in the text mirror

**Files:**
- Modify: `src/text.py:207-222` (`render_txt`)
- Modify: `src/build.py:113` (the `render_txt` call)
- Modify: `tests/test_collection_nav.py`

**Interfaces:**
- Consumes: `sequence.txt_line(item, colls, items)` (Task 2).
- Produces: `render_txt(meta, sections, around="")`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_collection_nav.py`:

```python
import re

ESC = re.compile(r"\x1b\[[0-9;]*m")


class TextLine(unittest.TestCase):
    def test_before_the_footer(self):
        lines = build_site()["txt/guides/setup.txt"].splitlines()
        self.assertEqual(lines[-3], "previous: Introduction" + " " * 37 + "next: Deployment")
        self.assertEqual(lines[-2], "")
        self.assertTrue(lines[-1].startswith("TESTS"))

    def test_ends(self):
        out = build_site()
        self.assertEqual(out["txt/guides/intro.txt"].splitlines()[-3], " " * 64 + "next: Setup")
        self.assertEqual(out["txt/guides/tuning.txt"].splitlines()[-3], "previous: Deployment")

    def test_french_is_folded(self):
        lines = build_site()["txt/fr/guides/tuning.txt"].splitlines()
        self.assertEqual(lines[-3], "precedent: Deployment")

    def test_only_sequential_types(self):
        out = build_site()
        self.assertNotIn("next:", out["txt/guides/index.txt"])
        self.assertNotIn("previous:", out["txt/blog/2026-01-01-hello.txt"])

    def test_ansi_matches_txt(self):
        out = build_site()
        for page in ("guides/setup", "fr/guides/tuning"):
            self.assertEqual(ESC.sub("", out[f"ansi/{page}.txt"]), out[f"txt/{page}.txt"], page)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_collection_nav.TextLine -v`
Expected: FAIL. `lines[-3]` is the page's last content line, not the navigation line.

- [ ] **Step 3: Add the line**

In `src/text.py`:

```python
def render_txt(meta, sections, around=""):
    """The page's text mirror. `around`: the line of a sequential type's
    neighbours (sequence.txt_line), set before the footer rule."""
    man = meta["man"]
    out = [rule(man, to_ascii(CFG["site"]["manual"]), man)]
    if languages.multilingual():
        out += ["", "LANGUAGES: " + " ".join(languages.declared())]
    for s in sections:
        if "html" in s["cls"]:
            continue
        out.append("")
        out.append(to_ascii(s["title"]).upper())
        out.extend(txt_blocks(s["blocks"], " " * INDENT))
    if around:
        out += ["", around]
    out.append("")
    foot = CFG["footer"]
    out.append(rule(to_ascii(foot["left"]), CFG["site"]["updated"], to_ascii(foot["right"])))
    text = "\n".join(l.rstrip() for l in out) + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)
```

In `src/build.py`, add `import sequence` next to the other imports, and replace

```python
                    marked = render_txt(meta, sections)
```

with

```python
                    marked = render_txt(meta, sections, sequence.txt_line(it, colls, items))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest tests.test_collection_nav -v`
Expected: PASS (15 tests)

- [ ] **Step 5: Run the whole suite and commit**

Run: `python3 -m unittest discover -s tests -t .`
Expected: all pass.

```bash
git add src/text.py src/build.py tests/test_collection_nav.py
git commit -m "feat: previous/next line in the text mirror of sequential types"
```

---

### Task 5: The starter and the contract docs

**Files:**
- Modify: `starter/content/site.fr.toml`, `starter/theme/layout.html`, `starter/theme/style.css`
- Modify: `docs/theme.md`, `docs/types.md`, `docs/markdown.md`, `README.md`
- Modify: `tests/test_collection_nav.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_collection_nav.py`:

```python
import subprocess
import sys
from config import BUILDER


class Starter(unittest.TestCase):
    def test_styles_the_new_classes(self):
        css = (BUILDER / "starter" / "theme" / "style.css").read_text()
        for cls in (".collection-nav", ".collection-group-label", ".prev", ".next",
                    ".prev-label", ".next-label"):
            self.assertIn(cls, css, cls)

    def test_layout_places_prev_and_next(self):
        layout = (BUILDER / "starter" / "theme" / "layout.html").read_text()
        self.assertIn("{{ prev }}", layout)
        self.assertIn("{{ next }}", layout)

    def test_builds(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            r = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(BUILDER / "starter"),
                                "--out", str(tmp / "out")], capture_output=True, text=True,
                               env={"BUILD_TODAY": "2026-06-15", "PATH": "/usr/bin:/bin"})
        finally:
            shutil.rmtree(tmp)
        self.assertEqual(r.returncode, 0, r.stderr)


class Docs(unittest.TestCase):
    def test_contract_names_everything(self):
        theme = (BUILDER / "docs" / "theme.md").read_text()
        for name in ("{{ collection_nav }}", "{{ prev }}", "{{ next }}", "`.collection-nav`",
                     "`.collection-group`", "`.collection-group-label`", "`.prev`", "`.next`"):
            self.assertIn(name, theme, name)
        types = (BUILDER / "docs" / "types.md").read_text()
        for name in ("`SEQUENTIAL`", "`LOCALIZED_OUTPUTS`", "`nav_label`", "`group`"):
            self.assertIn(name, types, name)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_collection_nav.Starter tests.test_collection_nav.Docs -v`
Expected: `test_styles_the_new_classes`, `test_layout_places_prev_and_next` and `test_contract_names_everything` FAIL. `test_builds` should already PASS. If it fails, report it: that is a pre-existing starter problem.

- [ ] **Step 3: Update the starter**

`starter/content/site.fr.toml`, under `[labels]`:

```toml
collection_nav = "Dans cette section"
prev = "précédent"
next = "suivant"
```

`starter/theme/layout.html`: replace

```html
{{ body }}
</main>
```

with

```html
{{ body }}
{{ prev }}
{{ next }}
</main>
```

`starter/theme/style.css`, append:

```css

/* A collection's order: {{ collection_nav }}, {{ prev }}, {{ next }}. */
.collection-nav ul { list-style: none; padding-left: 0; margin: 0; }
.collection-nav ul ul { padding-left: 1.5ch; }
.collection-nav a[aria-current="page"] { color: var(--accent); font-weight: 700; }
.collection-group-label { display: block; margin-top: 0.6rem; font: 700 0.75rem var(--mono); color: var(--fg-muted); text-transform: uppercase; }
.prev, .next { display: block; margin: 0.4rem 0; font-family: var(--mono); }
.next { text-align: right; }
.prev-label, .next-label { margin-right: 1ch; font-size: 0.8rem; color: var(--fg-muted); }
```

- [ ] **Step 4: Update the contract**

`docs/theme.md`, placeholders table, after the `{{ languages }}` row:

```markdown
| `{{ collection_nav }}` | the items of the page's collection, in the type's order, grouped by their `group:`, the current one marked `aria-current="page"`; on the collection's own page (`<dir>/index.md` or `<dir>.md`) the same list, nothing marked; empty elsewhere (`docs/types.md`) |
| `{{ prev }}`, `{{ next }}` | links to the page's neighbours in that order, groups ignored, labelled `labels.prev` and `labels.next`; empty at an end, on the collection's own page and elsewhere |
```

In the sentence after the table, add `collection_nav`, `prev`, `next` to the
list of computed values that are not escaped.

Classes table, after the `.languages` row:

```markdown
| `.collection-nav`, `.collection-group`, `.collection-group-label` | the collection sidebar (`<nav class="collection-nav">`), a group (`<li>`) and its label (`<span>`, not a heading) |
| `.prev`, `.prev-label`, `.next`, `.next-label` | the neighbour links (`rel="prev"`, `rel="next"`) and their label |
```

`docs/types.md`, attributes table, after `MARKERS`:

```markdown
| `SEQUENTIAL` | `False` | the text mirror of an item gets a `previous: ... next: ...` line before the footer (`labels.prev`, `labels.next`) |
| `LOCALIZED_OUTPUTS` | `False` | `outputs()` is called in every language, with that language's items and `conf`; its paths are put under the language's prefix (`fr/`) by the builder. Else once, in the default language |
```

Then a new subsection before `### Functions`:

```markdown
### Order, groups and navigation

A collection's order is the type's `sort_key`. A theme shows it with
`{{ collection_nav }}`, `{{ prev }}` and `{{ next }}` (`docs/theme.md`).
An item may set `group` in its front matter: the sidebar gathers the items
by group, the groups in the order of their first item, the items without a
group first. A collection may set `nav_label`, the sidebar's accessible
name; else `labels.collection_nav`.
```

`docs/markdown.md`, front-matter table, after the `image` row:

```markdown
| `group` | no | In a collection: the item's group in the theme's collection sidebar (`docs/types.md`). |
```

`README.md`, "What it gives you" list, after the Collections item:

```markdown
- A collection's order for themes: a sidebar, previous/next links, and
  per-language files a type writes (a search index) - `docs/theme.md`.
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest discover -s tests -t .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add starter/ docs/theme.md docs/types.md docs/markdown.md README.md tests/test_collection_nav.py
git commit -m "docs: collection navigation in the theme and type contracts; starter"
```

---

### Task 6: Release preparation

- [ ] **Step 1: Check the whole branch**

Run: `python3 -m unittest discover -s tests -t . -v 2>&1 | tail -5`
Expected: `OK`

Run: `grep -rn "SEQUENTIAL\|LOCALIZED_OUTPUTS\|collection_nav" --include=*.py --include=*.md --include=*.toml . | grep -v superpowers | wc -l`
Expected: a non-zero count, showing the code and the docs agree on the names.

- [ ] **Step 2: Hand over**

Stop here. Merging into `main`, tagging `v1.1.0` and pushing (which
publishes `ghcr.io/thosted/tilder:1.1.0` through CI) are outward-facing:
ask Théau, using superpowers:finishing-a-development-branch.
