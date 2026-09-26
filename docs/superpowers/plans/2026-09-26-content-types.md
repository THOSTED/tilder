# Content Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every kind of content - page, post, event, member, and whatever a theme adds - go through one Python type interface, with per-type layouts, a `theme.toml` layer, one shape of error message, and a runtime image built by CI.

**Architecture:** A type is a Python module (`types/<name>.py` in the generator, `theme/types/<name>.py` in a theme) that returns nodes of the existing tree, so `page.py` and `text.py` render every type without change. `src/contenttypes.py` loads and validates the modules, declares the collections of `site.toml`, reads their items and fills the lists. Every page becomes an item of a type (a plain page is an item of `page`), so `seo.py`, `feeds.py` and `page.py` ask the item's type instead of switching on a kind.

**Tech Stack:** Python 3.11+ standard library only (`tomllib`, `importlib`, `unittest`). No dependency. GitHub Actions and Docker for the image.

**Spec:** `docs/superpowers/specs/2026-09-26-content-types-design.md` - read it first; this plan argues from it.

## Global Constraints

- Python standard library only; no `pip install`, no framework (AGENTS.md §2.2).
- Everything in this repository is English: code, comments, docs, defaults, commit messages, this plan's commits.
- No site's name, domain or words in this repository: `grep -rni` for the reference site's name must find nothing (AGENTS.md §2.1). The reference site is referred to as `$SITE`, the folder that holds this `builder/` as a submodule.
- The reference site must build **byte-identical** before and after every task, once its `site.toml` is migrated in Task 6 (`diff -r` prints nothing). The baseline is made in Task 0.
- A type module returns nodes of the tree, never HTML. No inline style, colour or font from the code.
- Two renderings per construct: nothing this plan adds may render in HTML without its text mirror.
- Commit messages in Conventional Commits style (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `build:`, `ci:`). No AI co-author trailer.
- Tests: `python3 -m unittest discover -s tests -v` from the repository root, green at the end of every task.
- Error messages follow one shape: `error: <file>[:<line>]: <what is wrong>. <what to do>` (spec §9).

## Review Focus

Inputs the spec implies but no acceptance line names, most likely to bite first; each has its test in the task that owns the code:

1. **A theme type that fails to import** (a syntax error in `theme/types/talk.py`): one `error:` line naming the file, no traceback unless `--debug`, build stops. Pinned in Task 3.
2. **A declared collection whose folder does not exist** (`[collections.news]` with no `content/news/`): no page, no feed, no calendar, no error. Pinned in Task 6.
3. **A non-dated item as a folder** (`members/alan-turing/index.md` with `notes.txt` beside it): renders at `members/alan-turing.html`, the file is copied next to it, the folder's index is not also a page. Pinned in Task 6.
4. **`layout:` naming a missing file**: the error names the content file, the key and the expected theme path; a type's `LAYOUT` with no file falls back silently. Pinned in Task 10.
5. **A key set in both `theme.toml` and `site.toml`**: the site wins; a key set only in `theme.toml` reaches the page. Pinned in Task 11.

---

## File structure

```
types/                    NEW  built-in types, no __init__.py (must not become a package)
  page.py                 NEW  every .md outside a collection
  post.py                 NEW  from src/dated.py (posts) and seo.py (BlogPosting)
  event.py                NEW  from src/dated.py (events), seo.py (Event), feeds.py (calendar)
  member.py               NEW  from src/members.py and seo.py (ProfilePage)
src/contenttypes.py       NEW  load(), collections(), load_items(), page_item(), fill_lists(), summary()
src/report.py             NEW  BuildError, error(), warning(), fail(), report(), rel(), DEBUG
src/dates.py              NEW  human_date(), from dated.py
src/members.py            DELETED in Task 6
src/dated.py              DELETED in Task 6
src/build.py              types, collections, items; --debug, --version; summary; BuildError handling
src/config.py             theme.toml layer; layout(name, asked_by); UNSERVED, UNSERVED_DIRS
src/paths.py              ITEM_FOLDERS for non-dated item folders
src/page.py               render_html(item, ...); ARTICLE; scripts and data-* from sections; layout choice; {{ type }}
src/seo.py                head_tags(item); json_ld(item, image) asks the type; org_ref(), site_ref()
src/feeds.py              feed(items, conf) from feed_item(); calendar(events) uses item["date"]
src/watch.py              restart on theme/types/ changes
defaults.toml             no [collection_defaults.*], no [members]; [collections.members]
tests/                    NEW  unittest suite and a fixture site
  __init__.py             sys.path and SITE_ROOT
  helpers.py              build_site() cached
  site/                   the fixture: content/, theme/, assets/
  test_*.py
docs/types.md             NEW  the type contract
docs/theme.md, README.md, AGENTS.md, docs/markdown.md   updated
Dockerfile, .dockerignore, .github/workflows/image.yml, examples/compose.yaml
```

---

### Task 0: Baseline build and test harness

**Files:**
- Create: `tests/__init__.py`, `tests/helpers.py`, `tests/test_smoke.py`
- Create: `tests/site/content/site.toml`, `tests/site/content/index.md`, `tests/site/content/404.md`, `tests/site/content/events.md`, `tests/site/content/members.md`, `tests/site/content/blog/index.md`, `tests/site/content/blog/2026-01-01-hello.md`, `tests/site/content/events/2000-01-01-past-meetup.md`, `tests/site/content/events/2099-01-01-future-meetup.md`, `tests/site/content/members/ada-lovelace.md`, `tests/site/content/members/alan-turing/index.md`, `tests/site/content/members/alan-turing/notes.txt`, `tests/site/theme/layout.html`, `tests/site/assets/logo.svg`
- Modify: `.gitignore` (add `__pycache__/` if missing)

**Interfaces:**
- Produces: `tests.helpers.build_site() -> dict[str, str]` (output path -> text, decoded UTF-8 with `errors="replace"`), cached per process; `tests.helpers.rebuild() -> dict[str, str]` (uncached). Environment fixed by `tests/__init__.py`: `SITE_ROOT=tests/site`, `BUILD_TODAY=2026-06-15`.

- [ ] **Step 1: Build the baseline of the reference site, before any change**

Run, from this repository's root (`builder/` inside the site):

```bash
SITE="$(cd .. && pwd)"                      # the site that holds this builder/
export BUILD_TODAY=2026-09-26               # fixed: upcoming/past must not move under us
python3 build.py --root "$SITE" --out /tmp/tilder-before
ls /tmp/tilder-before | head
```

Expected: a `public`-like tree with `index.html`, `txt/`, `ansi/`, `sitemap.xml`. Keep `/tmp/tilder-before` for the whole plan. Every task's last step diffs against it.

- [ ] **Step 2: Write the fixture site's configuration**

`tests/site/content/site.toml`:

```toml
# The fixture site of the tests. English, neutral, no real person or site.

[site]
name = "test site"
url = "https://test.example"
lang = "en"
locale = "en_GB"
manual = "Test Site Manual"
updated = 2026-06-01
title_suffix = " - test site"

[footer]
left = "TESTS"
left_link = ""
right = "TEST(1)"

[[nav]]
label = "home"
href = ""

[[nav]]
label = "events"
href = "events"

[[nav]]
label = "blog"
href = "blog/"

[[nav]]
label = "members"
href = "members"

[seo]
organization = "Test Site"

[share]
image_alt = "~/test site"
card = ["a fixture"]
short_name = "test"
background_color = "#ABCDEF"

[collections.blog]
type = "posts"
feed = "blog/feed.xml"

[collections.events]
type = "events"
feed = "events.xml"
calendar = "events.ics"

# Declared, no folder: must produce nothing and fail nothing.
[collections.news]
type = "posts"
dir = "news"

[members]
categories = ["admin", "mentor", "member"]
```

(The plural `posts`/`events` and the `[members]` table are today's form. Task 6 migrates this file.)

- [ ] **Step 3: Write the fixture pages**

`tests/site/content/index.md`:

```markdown
---
man: TEST(1)
title: test site
description: A fixture site for the generator's tests: pages, posts, events, members and one theme type.
tagline: fixtures
nav:
---

## Name

test - a site built by the tests {mono}

## Next {next-event}

## About

One paragraph, so the page has a body.
```

`tests/site/content/404.md`:

```markdown
---
man: TEST(1)
title: 404
description: Page not found.
tagline: 404 - page not found
nav: -
text: no
robots: noindex
---

## Error

Not found. [home](./) {small}
```

`tests/site/content/events.md`:

```markdown
---
man: TEST-EVENTS(7)
title: events
description: Upcoming and past meetups of the fixture site, with feeds.
tagline: meetups
nav: events
feed: events
---

## Name

events - meetups, upcoming and past {mono}

## Upcoming {upcoming}

## Past {past}
```

`tests/site/content/members.md`:

```markdown
---
man: TEST-MEMBERS(7)
title: members
description: The people of the fixture site, one card each, searchable.
tagline: who is here
nav: members
---

## Name

members - the people {mono}

## Members {members}
```

`tests/site/content/blog/index.md`:

```markdown
---
man: TEST-BLOG(7)
title: blog
description: Posts of the fixture site, newest first, with an RSS feed.
tagline: posts
nav: blog/
feed: blog
---

## Name

blog - the posts {mono}

## Posts {posts}
```

- [ ] **Step 4: Write the fixture items**

`tests/site/content/blog/2026-01-01-hello.md`:

```markdown
---
title: Hello
description: The first post of the fixture site, to test cards, feeds and structured data.
author: Ada Lovelace
tag: note
---

## Name

hello - the first post {mono}

## Body

A paragraph.

```console
$ echo hello
hello
```
```

`tests/site/content/events/2000-01-01-past-meetup.md`:

```markdown
---
title: Past meetup
description: A meetup long past, to test the past list and its tag.
place: Town hall, Springfield
---

## Name

past-meetup - a meetup long past {mono}

## Description

It happened.
```

`tests/site/content/events/2099-01-01-future-meetup.md`:

```markdown
---
title: Future meetup
description: A meetup far ahead, to test the upcoming list, the next-event card and the calendar.
place: Library, Springfield
link: https://example.org/meetup
end: 2099-01-02
lat: 45.75
lon: 4.85
---

## Name

future-meetup - a meetup far ahead {mono}

## Description

It will happen.
```

`tests/site/content/members/ada-lovelace.md`:

```markdown
---
man: TEST-MEMBERS(7)
title: Ada Lovelace
description: Ada Lovelace, admin of the fixture site, to test the member card and profile page.
tagline: admin
nav: members
first_name: Ada
last_name: Lovelace
category: admin
github: https://github.com/ada
website: https://ada.example
---

## Name

Ada Lovelace - writes the first programs {mono}

## Role

Administers the fixture.
```

`tests/site/content/members/alan-turing/index.md` (a member as a folder, with a file beside it):

```markdown
---
man: TEST-MEMBERS(7)
title: Alan Turing
description: Alan Turing, member of the fixture site, kept as a folder with a file beside the page.
tagline: member
nav: members
first_name: Alan
last_name: Turing
category: member
affiliation: Bletchley
---

## Name

Alan Turing - decides {mono}

## Role

Member of the fixture.
```

`tests/site/content/members/alan-turing/notes.txt`:

```
a file kept next to a member's page
```

- [ ] **Step 5: Write the fixture theme and assets**

`tests/site/theme/layout.html` - copy the starter's, it has every required element:

```bash
cp starter/theme/layout.html tests/site/theme/layout.html
cp starter/assets/logo.svg tests/site/assets/logo.svg
```

- [ ] **Step 6: Write the test package and helpers**

`tests/__init__.py`:

```python
"""The test suite: `python3 -m unittest discover -s tests -v` from the
repository root. Every test builds the fixture site in tests/site/, with
a fixed date, and looks at the files the build returns."""

import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
os.environ["SITE_ROOT"] = str(HERE / "site")
os.environ["BUILD_TODAY"] = "2026-06-15"
# src/ first, so `import build` is src/build.py, not the entry point at the root.
sys.path.insert(0, str(HERE.parent / "src"))
```

`tests/helpers.py`:

```python
"""build_site(): the fixture site as {output path: text}, built once."""

import build

_CACHE = {}


def rebuild():
    """Build the fixture site now. {path: str}, bytes decoded as UTF-8."""
    out = build.build()
    return {k: v.decode("utf-8", errors="replace") for k, v in out.items()}


def build_site():
    """The fixture site, built once per test run."""
    if not _CACHE:
        _CACHE.update(rebuild())
    return _CACHE
```

- [ ] **Step 7: Write the smoke test**

`tests/test_smoke.py`:

```python
import unittest

from tests.helpers import build_site


class Smoke(unittest.TestCase):
    def test_pages_are_built_twice(self):
        out = build_site()
        for page in ("index", "events", "members", "blog/index",
                     "blog/2026-01-01-hello", "events/2099-01-01-future-meetup",
                     "members/ada-lovelace", "members/alan-turing"):
            self.assertIn(f"{page}.html", out, page)
        self.assertIn("txt/index.txt", out)
        self.assertIn("ansi/index.txt", out)
        self.assertNotIn("txt/404.txt", out)  # text: no

    def test_upcoming_and_past_follow_the_fixed_date(self):
        out = build_site()
        events = out["events.html"]
        self.assertIn("Future meetup", events)
        self.assertIn("Past meetup", events)
        self.assertIn('class="tag tag--next">upcoming<', events)
        self.assertIn('class="tag">past<', events)

    def test_a_file_beside_a_member_page_is_copied(self):
        out = build_site()
        self.assertIn("members/alan-turing/notes.txt", out)
```

- [ ] **Step 8: Run the tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: 3 tests. `test_pages_are_built_twice` and `test_upcoming_and_past_follow_the_fixed_date` PASS. `test_a_file_beside_a_member_page_is_copied` may PASS already (files next to pages are copied by the generic loop in `build.py`); `members/alan-turing/index.md` currently renders as `members/alan-turing/index.html` - that is today's behaviour, fixed in Task 6. If the smoke test fails on `members/alan-turing.html`, change that one assertion to `members/alan-turing/index.html` for now and leave a comment `# Task 6 makes this members/alan-turing.html`.

- [ ] **Step 9: Commit**

```bash
git add tests .gitignore
git commit -m "test: a fixture site and a smoke test"
```

---

### Task 1: `src/report.py` - one shape of error

**Files:**
- Create: `src/report.py`
- Modify: `src/build.py` (`main()`: `--debug`, catch `BuildError`; the two `except Exception` blocks)
- Modify: `src/watch.py:38-44` (`except Exception` -> `report.report(e)`)
- Test: `tests/test_report.py`

**Interfaces:**
- Produces:
  - `class BuildError(Exception)`: `.items: list[tuple[str, BaseException | None]]` - one `(message, cause)` per problem; `str(e)` joins the messages with newlines.
  - `error(path, what, hint="", line=None, exc=None) -> BuildError` (builds, does not raise).
  - `warning(path, what, hint="") -> None`: prints `warning: <message>` to stderr.
  - `fail(errors: list[BuildError]) -> NoReturn`: raises one `BuildError` holding every item.
  - `report(exc: BaseException) -> None`: prints `error: <message>` per item to stderr, tracebacks when `DEBUG`.
  - `rel(path) -> str`: the path relative to `ROOT` when under it, else as given.
  - `DEBUG: bool`, set by `--debug`.

- [ ] **Step 1: Write the failing tests**

`tests/test_report.py`:

```python
import contextlib
import io
import pathlib
import unittest

import report
from config import ROOT


class Report(unittest.TestCase):
    def test_message_shape(self):
        e = report.error(ROOT / "content" / "site.toml", 'collection "talks" has type "talk", which no type defines',
                         "Types loaded: page, post")
        self.assertEqual(e.items[0][0],
                         'content/site.toml: collection "talks" has type "talk", which no type defines. '
                         "Types loaded: page, post")

    def test_line_and_no_hint(self):
        e = report.error(ROOT / "content" / "x.md", "bad key", line=3)
        self.assertEqual(str(e), "content/x.md:3: bad key")

    def test_path_outside_root_is_kept(self):
        e = report.error(pathlib.Path("/elsewhere/t.py"), "boom")
        self.assertEqual(str(e), "/elsewhere/t.py: boom")

    def test_fail_gathers(self):
        with self.assertRaises(report.BuildError) as cm:
            report.fail([report.error("a", "one"), report.error("b", "two", "fix it")])
        self.assertEqual([m for m, _ in cm.exception.items], ["a: one", "b: two. fix it"])

    def test_report_prints_one_line_per_item(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            report.report(report.BuildError([("a: one", None), ("b: two", None)]))
        self.assertEqual(err.getvalue(), "error: a: one\nerror: b: two\n")

    def test_report_hides_traceback_without_debug(self):
        err = io.StringIO()
        cause = ValueError("inner")
        with contextlib.redirect_stderr(err):
            report.report(report.error("t.py", "cannot be imported", exc=cause))
        self.assertNotIn("Traceback", err.getvalue())
        report.DEBUG = True
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                report.report(report.error("t.py", "cannot be imported", exc=cause))
            self.assertIn("ValueError: inner", err.getvalue())
        finally:
            report.DEBUG = False

    def test_report_any_exception(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            report.report(KeyError("title"))
        self.assertEqual(err.getvalue(), "error: KeyError: 'title'\n")

    def test_warning(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            report.warning("content/x.md", "image has no alt text", "Write one")
        self.assertEqual(err.getvalue(), "warning: content/x.md: image has no alt text. Write one\n")
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m unittest tests.test_report -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'report'`.

- [ ] **Step 3: Write `src/report.py`**

```python
"""Errors and warnings, one shape.

    error: <file>[:<line>]: <what is wrong>. <what to do>

A problem the build cannot work around is a BuildError; it may hold several
messages, so one run shows every problem of a phase, not the first. The
Python traceback is shown only with --debug: the message is meant to be
enough.
"""

import sys
import traceback

from config import ROOT

DEBUG = False  # --debug: tracebacks after the messages


class BuildError(Exception):
    """One or more problems: items is [(message, cause or None)]."""

    def __init__(self, items):
        self.items = [(m, None) if isinstance(m, str) else tuple(m) for m in items]
        super().__init__("\n".join(m for m, _ in self.items))


def rel(path):
    """A path as the user knows it: relative to the site root when under it."""
    try:
        return str(path.relative_to(ROOT))
    except (AttributeError, ValueError):
        return str(path)


def message(path, what, hint="", line=None):
    where = rel(path) if path else ""
    if where and line:
        where += f":{line}"
    text = f"{where}: {what}" if where else what
    return f"{text}. {hint}" if hint else text


def error(path, what, hint="", line=None, exc=None):
    """A BuildError with one item. Build it, then raise it or gather it."""
    return BuildError([(message(path, what, hint, line), exc)])


def fail(errors):
    """Raise every gathered error at once."""
    raise BuildError([item for e in errors for item in e.items])


def warning(path, what, hint=""):
    print(f"warning: {message(path, what, hint)}", file=sys.stderr, flush=True)


def report(exc):
    """Print an exception the way the build reports errors."""
    if isinstance(exc, BuildError):
        for text, cause in exc.items:
            print(f"error: {text}", file=sys.stderr, flush=True)
            if DEBUG and cause is not None:
                traceback.print_exception(cause, file=sys.stderr)
    else:
        print(f"error: {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
        if DEBUG:
            traceback.print_exception(exc, file=sys.stderr)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python3 -m unittest tests.test_report -v`
Expected: 8 tests PASS.

- [ ] **Step 5: Wire `--debug` and `BuildError` into the driver**

In `src/build.py`, add `import report` next to the other imports, and change `main()`:

```python
def main():
    args = sys.argv[1:]
    dest = ROOT / "public"
    if args[:1] and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    report.DEBUG = "--debug" in args
    if "--out" in args:
        dest = pathlib.Path(args[args.index("--out") + 1]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if "--watch" in args:
        interval = float(os.environ.get("BUILD_INTERVAL", "1"))
        own_code = lambda: {k: v for k, v in snapshot().items()
                            if k.startswith(str(BUILDER))}
        code = own_code()
        while True:
            try:
                build_into(dest)
                break
            except Exception as e:
                # Wait for a fix. If it is in builder/, restart to load it:
                # this process still runs the code that failed.
                report.report(e)
                print("build failed: waiting for a change in content/, theme/ or assets/ "
                      "(a change in builder/ restarts)", flush=True)
                time.sleep(interval * 5)
                if own_code() != code:
                    print("builder/ changed, restarting", flush=True)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
        watch(dest, interval, build_into)
    else:
        try:
            build_into(dest)
        except report.BuildError as e:
            report.report(e)
            return 1
    return 0
```

Add `--debug` to the module docstring's usage lines:

```
    python3 builder/build.py --debug         show Python tracebacks after error messages
```

In `src/watch.py`, add `import report` and replace both `print(f"build failed, previous output kept: {e!r}", flush=True)` with:

```python
                    report.report(e)
                    print("build failed, previous output kept", flush=True)
```

- [ ] **Step 6: Run everything and diff the reference site**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: all tests PASS; `IDENTICAL`.

- [ ] **Step 7: Commit**

```bash
git add src/report.py src/build.py src/watch.py tests/test_report.py
git commit -m "feat: report errors in one shape, tracebacks behind --debug"
```

---

### Task 2: `src/dates.py`

**Files:**
- Create: `src/dates.py`
- Modify: `src/dated.py:629-634` (remove `human_date`, import it)
- Test: `tests/test_dates.py`

**Interfaces:**
- Produces: `dates.human_date(iso: str) -> str`, words from `CFG["dates"]`.

- [ ] **Step 1: Write the failing test**

`tests/test_dates.py`:

```python
import unittest

from config import CFG, load_config
from dates import human_date


class Dates(unittest.TestCase):
    def test_words_from_config(self):
        load_config()
        self.assertEqual(human_date("2026-06-15"), "Monday 15 June 2026")

    def test_first_of_month_word(self):
        load_config()
        CFG["dates"]["first"] = "1st"
        try:
            self.assertEqual(human_date("2026-06-01"), "Monday 1st June 2026")
        finally:
            load_config()
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest tests.test_dates -v`
Expected: FAIL, `No module named 'dates'`.

- [ ] **Step 3: Create `src/dates.py` and point `dated.py` at it**

`src/dates.py`:

```python
"""Dates written out in words, from [dates] in site.toml."""

import datetime

from config import CFG


def human_date(iso):
    """2026-11-21 -> "Saturday 21 November 2026", words from [dates]."""
    d, day = CFG["dates"], datetime.date.fromisoformat(iso)
    return d["format"].format(
        weekday=d["weekdays"][day.weekday()], month=d["months"][day.month - 1],
        day=d["first"] if day.day == 1 else day.day, year=day.year)
```

In `src/dated.py`: delete the `human_date` function, add `from dates import human_date` to the imports.

- [ ] **Step 4: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 5: Commit**

```bash
git add src/dates.py src/dated.py tests/test_dates.py
git commit -m "refactor: human_date in its own module"
```

---

### Task 3: `src/contenttypes.py` - the loader

**Files:**
- Create: `src/contenttypes.py` (the loading half; collections and items come in Task 6)
- Create: `types/.keep` (an empty file so the folder exists; removed in Task 4)
- Test: `tests/test_types_loader.py`

**Interfaces:**
- Produces:
  - `contenttypes.load(dirs=None) -> dict[str, module]`: loads `*.py` from each dir in order (default `[BUILTIN, THEME / "types"]`), later dirs replacing earlier by `NAME`; validates; fills missing attributes and hooks with defaults; raises `BuildError` with every problem. Updates `contenttypes.TYPES` after each dir (so a theme type can read a built-in at import) and `contenttypes.MARKERS` (`{word: type name}`) at the end.
  - `contenttypes.BUILTIN = BUILDER / "types"`.
  - Module attributes after `load()`: `NAME`, `DATED` (False), `ARTICLE` (False), `OG_TYPE` ("website"), `LAYOUT` (= NAME), `SCRIPT` (""), `DEFAULTS` ({}), `MARKERS` ({}), `HAS_FEED` (True iff the module defined `feed_item`), `PATH` (the file); hooks `defaults(item, conf)`, `sort_key(item, conf)`, `entry(item, link, conf)`, `json_ld(item, conf)`, `feed_item(item, conf)`, `meta_tags(item, conf)`, `outputs(items, conf)`, `list_data(conf)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_types_loader.py`:

```python
import contextlib
import io
import pathlib
import tempfile
import textwrap
import unittest

import contenttypes
import report


def write(folder, name, body):
    p = pathlib.Path(folder) / f"{name}.py"
    p.write_text(textwrap.dedent(body))
    return p


class Loader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_minimal_module_gets_defaults(self):
        write(self.dir, "note", 'NAME = "note"\ndef entry(item, link, conf): return None\n')
        types = contenttypes.load([self.dir])
        m = types["note"]
        self.assertFalse(m.DATED)
        self.assertFalse(m.ARTICLE)
        self.assertEqual(m.OG_TYPE, "website")
        self.assertEqual(m.LAYOUT, "note")
        self.assertEqual(m.SCRIPT, "")
        self.assertEqual(m.DEFAULTS, {})
        self.assertEqual(m.MARKERS, {})
        self.assertFalse(m.HAS_FEED)
        item = {"slug": "s", "meta": {}}
        self.assertEqual(m.sort_key(item, {}), "s")
        self.assertIsNone(m.json_ld(item, {}))
        self.assertIsNone(m.feed_item(item, {}))
        self.assertEqual(m.meta_tags(item, {}), [])
        self.assertEqual(m.outputs([], {}), {})
        self.assertEqual(m.list_data({}), {})
        self.assertIsNone(m.defaults(item, {}))

    def test_later_dir_replaces_by_name(self):
        a, b = self.dir / "a", self.dir / "b"
        a.mkdir(); b.mkdir()
        write(a, "member", 'NAME = "member"\nDATED = False\ndef entry(item, link, conf): return "a"\n')
        write(b, "mine", 'NAME = "member"\ndef entry(item, link, conf): return "b"\n')
        types = contenttypes.load([a, b])
        self.assertEqual(list(types), ["member"])
        self.assertEqual(types["member"].entry(None, True, {}), "b")

    def test_theme_type_can_build_on_a_builtin(self):
        a, b = self.dir / "a", self.dir / "b"
        a.mkdir(); b.mkdir()
        write(a, "event", 'NAME = "event"\nDEFAULTS = {"x": 1}\ndef entry(item, link, conf): return None\n')
        write(b, "talk", '''
            from contenttypes import TYPES
            NAME = "talk"
            DEFAULTS = {**TYPES["event"].DEFAULTS, "y": 2}
            def entry(item, link, conf): return None
        ''')
        types = contenttypes.load([a, b])
        self.assertEqual(types["talk"].DEFAULTS, {"x": 1, "y": 2})

    def test_underscore_files_are_skipped(self):
        write(self.dir, "_draft", "raise RuntimeError('never imported')\n")
        self.assertEqual(contenttypes.load([self.dir]), {})

    def errors(self, *dirs):
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.load(list(dirs))
        return [m for m, _ in cm.exception.items]

    def test_missing_name_and_entry(self):
        p = write(self.dir, "bad", "X = 1\n")
        msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 2)
        self.assertTrue(all(m.startswith(f"{p}: ") for m in msgs), msgs)
        self.assertIn("NAME must be a string", msgs[0])
        self.assertIn("entry(item, link, conf) is missing", msgs[1])

    def test_import_failure_is_one_line_and_names_the_file(self):
        p = write(self.dir, "broken", "def entry(item, link, conf)\n")  # SyntaxError
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 1)
        self.assertIn(f"{p}: cannot be imported: SyntaxError", msgs[0])
        self.assertIn("--debug", msgs[0])
        self.assertNotIn("Traceback", err.getvalue())

    def test_wrong_attribute_types(self):
        write(self.dir, "bad", 'NAME = "bad"\nDATED = "yes"\nMARKERS = ["x"]\ndef entry(item, link, conf): return None\n')
        msgs = self.errors(self.dir)
        self.assertTrue(any("DATED must be a bool" in m for m in msgs), msgs)
        self.assertTrue(any("MARKERS must be a dict" in m for m in msgs), msgs)

    def test_marker_clash_names_both(self):
        write(self.dir, "post", 'NAME = "post"\nMARKERS = {"posts": lambda items, conf: {}}\ndef entry(item, link, conf): return None\n')
        write(self.dir, "news", 'NAME = "news"\nMARKERS = {"posts": lambda items, conf: {}}\ndef entry(item, link, conf): return None\n')
        msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 1)
        self.assertIn('MARKERS["posts"] is already claimed by type "news"', msgs[0])
        self.assertIn('naming yours "news"', msgs[0])

    def test_same_name_in_one_dir_is_an_error(self):
        write(self.dir, "a", 'NAME = "dup"\ndef entry(item, link, conf): return None\n')
        write(self.dir, "b", 'NAME = "dup"\ndef entry(item, link, conf): return None\n')
        msgs = self.errors(self.dir)
        self.assertEqual(len(msgs), 1)
        self.assertIn('NAME "dup" is also the name of', msgs[0])

    def test_all_errors_are_gathered(self):
        write(self.dir, "one", "X = 1\n")
        write(self.dir, "two", "def entry(item, link, conf)\n")
        self.assertEqual(len(self.errors(self.dir)), 3)

    def test_markers_index(self):
        write(self.dir, "ev", 'NAME = "ev"\nMARKERS = {"upcoming": lambda i, c: {}, "past": lambda i, c: {}}\ndef entry(item, link, conf): return None\n')
        contenttypes.load([self.dir])
        self.assertEqual(contenttypes.MARKERS, {"upcoming": "ev", "past": "ev"})
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m unittest tests.test_types_loader -v`
Expected: FAIL, `No module named 'contenttypes'`.

- [ ] **Step 3: Write the loader**

`src/contenttypes.py`:

```python
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
```

Create the empty built-in folder so `load()` finds it: `touch types/.keep`.

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest tests.test_types_loader -v`
Expected: 12 tests PASS. Note `test_marker_clash_names_both`: modules load in sorted file order (`news.py` before `post.py`), so `news` claims `posts` first and the error is on `post.py`, naming `news`.

- [ ] **Step 5: Run everything and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL` (nothing calls the loader yet).

- [ ] **Step 6: Commit**

```bash
git add src/contenttypes.py types/.keep tests/test_types_loader.py
git commit -m "feat: load and validate content type modules"
```

---

### Task 4: `types/post.py` and `types/event.py`

**Files:**
- Create: `types/post.py`, `types/event.py`
- Delete: `types/.keep`
- Modify: `src/seo.py` (add `org_ref()`, `site_ref()`; nothing else yet)
- Test: `tests/test_type_post.py`, `tests/test_type_event.py`, `tests/test_stdlib.py`

**Interfaces:**
- Consumes: `dates.human_date`, `config.STATE["today"]`, `seo.page_heading`, `seo.share_image`, `seo.org_ref`, `seo.site_ref`, `paths.clean_url`, `config.apex`, `feeds.calendar` (Task 8 changes its item key; until then `event.outputs` is exercised only by its test through a shim - see Step 5).
- Produces: `seo.org_ref() -> {"@id": "<apex>/#organization"}`, `seo.site_ref() -> {"@id": "<apex>/#website"}`. Two type modules with the interface of Task 3. Item dicts as in the spec §4: `slug, date, meta, src, path, collection, conf, type`.

- [ ] **Step 1: Write the failing tests**

`tests/test_stdlib.py` (pins that the `types/` folder never shadows the standard library):

```python
import unittest


class Stdlib(unittest.TestCase):
    def test_types_folder_does_not_shadow_stdlib(self):
        import types
        self.assertTrue(hasattr(types, "ModuleType"), "types/ at the root became a package: remove its __init__.py")
```

`tests/test_type_post.py`:

```python
import unittest

import contenttypes
from config import STATE, load_config

CONF = None


def setUpModule():
    global CONF
    load_config()
    STATE["today"] = "2026-06-15"
    post = contenttypes.load([contenttypes.BUILTIN])["post"]
    CONF = {**post.DEFAULTS, "dir": "blog", "type": "post", "feed": "blog/feed.xml"}


def item(**meta):
    m = {"title": "Hello", "description": "One sentence."}
    m.update(meta)
    return {"slug": "2026-01-01-hello", "date": "2026-01-01", "meta": m, "src": None,
            "path": "blog/2026-01-01-hello.html", "collection": "blog", "conf": CONF,
            "type": contenttypes.TYPES["post"]}


class Post(unittest.TestCase):
    def setUp(self):
        self.post = contenttypes.TYPES["post"]

    def test_flags(self):
        self.assertEqual(self.post.NAME, "post")
        self.assertTrue(self.post.DATED)
        self.assertTrue(self.post.ARTICLE)
        self.assertEqual(self.post.OG_TYPE, "article")
        self.assertEqual(self.post.LAYOUT, "post")
        self.assertEqual(set(self.post.MARKERS), {"posts"})
        self.assertTrue(self.post.HAS_FEED)

    def test_defaults_fill_the_front_matter(self):
        it = item()
        self.post.defaults(it, CONF)
        self.assertEqual(it["meta"]["man"], "SITE-BLOG(7)")
        self.assertEqual(it["meta"]["nav"], "blog/")
        self.assertEqual(it["meta"]["tagline"], "Thursday 1 January 2026")

    def test_card_in_a_list(self):
        node = self.post.entry(item(author="Ada", tag="note"), True, CONF)
        self.assertEqual(node, {
            "k": "entry", "id": None, "cls": ["link"], "own": False,
            "title": "[Hello](blog/2026-01-01-hello)",
            "meta": ["2026-01-01 | Thursday 1 January 2026", "Ada", "`note`"],
            "blocks": [{"k": "para", "text": "One sentence.", "cls": []}],
        })

    def test_card_on_its_own_page(self):
        node = self.post.entry(item(), False, CONF)
        self.assertEqual(node["title"], "Hello")
        self.assertTrue(node["own"])
        self.assertEqual(node["cls"], [])
        self.assertEqual(node["blocks"], [])

    def test_posts_marker_lists_newest_first(self):
        a, b = item(), item()
        b["slug"], b["date"] = "2026-02-01-later", "2026-02-01"
        r = self.post.MARKERS["posts"]([a, b], CONF)
        self.assertEqual([it["slug"] for it, _ in r["items"]], ["2026-02-01-later", "2026-01-01-hello"])
        self.assertEqual(r["empty"], "No post yet.")

    def test_json_ld(self):
        node = self.post.json_ld(item(author="Ada"), CONF)
        self.assertEqual(node["@type"], "BlogPosting")
        self.assertEqual(node["datePublished"], "2026-01-01")
        self.assertEqual(node["author"], {"@type": "Person", "name": "Ada"})
        self.assertEqual(node["publisher"], {"@id": "https://test.example/#organization"})

    def test_meta_tags(self):
        self.assertEqual(self.post.meta_tags(item(author="Ada", tag="note"), CONF), [
            ("name", "author", "Ada"),
            ("property", "article:published_time", "2026-01-01"),
            ("property", "article:tag", "note"),
        ])
        self.assertEqual(self.post.meta_tags(item(), CONF),
                         [("property", "article:published_time", "2026-01-01")])

    def test_feed_item(self):
        self.assertEqual(self.post.feed_item(item(), CONF), {
            "title": "Hello", "link": "https://test.example/blog/2026-01-01-hello",
            "description": "One sentence.", "date": "2026-01-01"})
```

`tests/test_type_event.py`:

```python
import unittest

import contenttypes
from config import STATE, load_config

CONF = None


def setUpModule():
    global CONF
    load_config()
    STATE["today"] = "2026-06-15"
    event = contenttypes.load([contenttypes.BUILTIN])["event"]
    CONF = {**event.DEFAULTS, "dir": "events", "type": "event", "calendar": "events.ics"}


def item(slug="2099-01-01-future", **meta):
    m = {"title": "Future", "description": "One sentence."}
    m.update(meta)
    return {"slug": slug, "date": slug[:10], "meta": m, "src": None,
            "path": f"events/{slug}.html", "collection": "events", "conf": CONF,
            "type": contenttypes.TYPES["event"]}


class Event(unittest.TestCase):
    def setUp(self):
        self.event = contenttypes.TYPES["event"]

    def test_flags(self):
        self.assertTrue(self.event.DATED)
        self.assertTrue(self.event.ARTICLE)
        self.assertEqual(self.event.OG_TYPE, "website")
        self.assertEqual(set(self.event.MARKERS), {"upcoming", "past", "next-event"})
        self.assertTrue(self.event.HAS_FEED)

    def test_upcoming_card_with_place_and_end(self):
        node = self.event.entry(item(place="Library", end="2099-01-02"), True, CONF)
        self.assertEqual(node["meta"], [
            "2099-01-01 | Thursday 1 January 2099 - Friday 2 January 2099", "Library", "`upcoming`"])
        self.assertEqual(node["cls"], ["link"])
        self.assertEqual(node["title"], "[Future](events/2099-01-01-future)")

    def test_past_tag(self):
        node = self.event.entry(item("2000-01-01-past"), True, CONF)
        self.assertIn("`past`", node["meta"])

    def test_own_page_links(self):
        node = self.event.entry(item(place="Library", link="https://example.org/m", lat="45.75", lon="4.85"),
                                False, CONF)
        self.assertEqual(node["blocks"], [{
            "k": "para", "cls": ["small"],
            "text": "[event website ↗](https://example.org/m) · "
                    "[see on OpenStreetMap ↗](https://www.openstreetmap.org/?mlat=45.75&mlon=4.85#map=17/45.75/4.85)",
            "txt": "[event website ↗](https://example.org/m)",
        }])

    def test_osm_search_without_coordinates(self):
        node = self.event.entry(item(place="Town hall, Springfield"), False, CONF)
        self.assertIn("openstreetmap.org/search?query=Town%20hall%2C%20Springfield", node["blocks"][0]["text"])
        self.assertEqual(node["blocks"][0]["txt"], "")

    def test_markers(self):
        past, soon, later = item("2000-01-01-past"), item("2099-01-01-soon"), item("2099-02-01-later")
        items = [past, soon, later]
        up = self.event.MARKERS["upcoming"](items, CONF)
        self.assertEqual([(it["slug"], cls) for it, cls in up["items"]],
                         [("2099-01-01-soon", ["next"]), ("2099-02-01-later", [])])
        self.assertEqual(up["empty"], "No upcoming event.")
        nxt = self.event.MARKERS["next-event"](items, CONF)
        self.assertEqual([it["slug"] for it, _ in nxt["items"]], ["2099-01-01-soon"])
        pst = self.event.MARKERS["past"](items, CONF)
        self.assertEqual([it["slug"] for it, _ in pst["items"]], ["2000-01-01-past"])
        self.assertEqual(pst["empty"], "No past event.")

    def test_json_ld(self):
        node = self.event.json_ld(item(place="Library", lat="45.75", lon="4.85", end="2099-01-02"), CONF)
        self.assertEqual(node["@type"], "Event")
        self.assertEqual(node["startDate"], "2099-01-01")
        self.assertEqual(node["endDate"], "2099-01-02")
        self.assertEqual(node["location"]["geo"], {"@type": "GeoCoordinates", "latitude": "45.75", "longitude": "4.85"})
        self.assertEqual(node["organizer"], {"@id": "https://test.example/#organization"})

    def test_feed_item(self):
        self.assertEqual(self.event.feed_item(item(), CONF)["link"], "https://test.example/events/2099-01-01-future")

    def test_outputs_calendar_only_when_asked(self):
        self.assertEqual(self.event.outputs([], {**CONF, "calendar": ""}), {})
        out = self.event.outputs([item(place="Library")], CONF)
        self.assertEqual(list(out), ["events.ics"])
        self.assertIn("SUMMARY:Future - events", out["events.ics"])
        self.assertIn("LOCATION:Library", out["events.ics"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_type_post tests.test_type_event tests.test_stdlib -v`
Expected: `test_stdlib` PASS; the two others FAIL with `KeyError: 'post'` / `'event'` (the folder has no module).

- [ ] **Step 3: Add the two reference helpers to `seo.py`**

In `src/seo.py`, after `is_landing`:

```python
def org_ref():
    """The Organization node of the JSON-LD graph, by reference."""
    return {"@id": f"{apex()}/#organization"}


def site_ref():
    """The WebSite node of the JSON-LD graph, by reference."""
    return {"@id": f"{apex()}/#website"}
```

- [ ] **Step 4: Write `types/post.py`**

```python
"""Posts: dated articles, newest first, with an RSS feed. The built-in
`post` type, written as any theme type is (docs/types.md)."""

from config import apex
from dates import human_date
from paths import clean_url
from seo import org_ref, page_heading, share_image

NAME = "post"
DATED = True
ARTICLE = True          # Reader mode and read-aloud tools look for one
OG_TYPE = "article"
DEFAULTS = {
    "man": "SITE-BLOG(7)",          # items' man-page name, unless they set one
    "nav": "blog/",                 # items' nav entry, and the feed's link
    "empty": "No post yet.",        # a {posts} list with nothing in it
    "feed": "",                     # RSS path, e.g. "blog/feed.xml"; empty for none
    "feed_title": "posts",
    "feed_description": "Posts.",
}


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("tagline", human_date(item["date"]))
    meta.setdefault("description", "")


def entry(item, link, conf):
    """The card: date, author, tag; the description in a list."""
    meta = item["meta"]
    line = [f"{item['date']} | {human_date(item['date'])}"]
    if meta.get("author"):
        line.append(meta["author"])
    if meta.get("tag"):
        line.append(f"`{meta['tag']}`")
    blocks = []
    if link and meta.get("description"):
        blocks.append({"k": "para", "text": meta["description"], "cls": []})
    return {"k": "entry", "id": None, "cls": ["link"] if link else [], "meta": line,
            "blocks": blocks, "own": not link,
            "title": f"[{meta['title']}]({item['path'][:-5]})" if link else meta["title"]}


def posts(items, conf):
    """{posts}: every post, newest first."""
    return {"items": [(it, []) for it in reversed(items)], "empty": conf.get("empty", "")}


MARKERS = {"posts": posts}


def json_ld(item, conf):
    meta = item["meta"]
    node = {"@type": "BlogPosting", "headline": page_heading(meta),
            "description": meta["description"], "datePublished": item["date"],
            "dateModified": meta.get("updated", item["date"]),
            "publisher": org_ref(), "image": share_image(meta)[0]}
    if meta.get("author"):
        node["author"] = {"@type": "Person", "name": meta["author"]}
    return node


def meta_tags(item, conf):
    meta, tags = item["meta"], []
    if meta.get("author"):
        tags.append(("name", "author", meta["author"]))
    tags.append(("property", "article:published_time", item["date"]))
    if meta.get("tag"):
        tags.append(("property", "article:tag", meta["tag"]))
    return tags


def feed_item(item, conf):
    return {"title": item["meta"]["title"], "link": apex() + clean_url(item["path"]),
            "description": item["meta"]["description"], "date": item["date"]}
```

- [ ] **Step 5: Write `types/event.py`**

```python
"""Events: dated, upcoming or past by the date of the build, with a place,
an RSS feed and an iCalendar. The built-in `event` type (docs/types.md)."""

import urllib.parse

from config import STATE, apex
from dates import human_date
from feeds import calendar
from paths import clean_url
from seo import org_ref, page_heading, share_image

NAME = "event"
DATED = True
ARTICLE = True
DEFAULTS = {
    "man": "SITE-EVENTS(7)",
    "nav": "events",
    "upcoming_tag": "upcoming",
    "past_tag": "past",
    "none_upcoming": "No upcoming event.",
    "none_past": "No past event.",
    "link_label": "event website ↗",
    "map_label": "see on OpenStreetMap ↗",
    "feed": "",                     # RSS path, e.g. "events.xml"; empty for none
    "feed_title": "events",
    "feed_description": "Upcoming and past events.",
    "calendar": "",                 # iCalendar path, e.g. "events.ics"; empty for none
}


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("tagline", human_date(item["date"]))
    meta.setdefault("description", "")


def osm_url(meta):
    """A link to the place on OpenStreetMap: a marker when the event gives
    lat and lon, else a search for its address. A link, not an embedded
    map: an iframe would make every visitor's browser call another host."""
    if meta.get("lat") and meta.get("lon"):
        lat, lon = meta["lat"], meta["lon"]
        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"
    if meta.get("place"):
        return "https://www.openstreetmap.org/search?query=" + urllib.parse.quote(meta["place"])
    return None


def entry(item, link, conf):
    """The card: date (range), place, upcoming/past tag; the description in
    a list; the event's site and map links on its own page."""
    meta = item["meta"]
    line = [f"{item['date']} | {human_date(item['date'])}"]
    if meta.get("end"):
        line[0] += " - " + human_date(meta["end"])
    if meta.get("place"):
        line.append(meta["place"])
    tag = conf["upcoming_tag" if item["date"] >= STATE["today"] else "past_tag"]
    if tag:
        line.append(f"`{tag}`")
    blocks = []
    if link and meta.get("description"):
        blocks.append({"k": "para", "text": meta["description"], "cls": []})
    if not link:
        links = []
        if meta.get("link"):
            links.append(f"[{conf['link_label']}]({meta['link']})")
        site = " · ".join(links)
        if osm_url(meta):
            links.append(f"[{conf['map_label']}]({osm_url(meta)})")
        if links:
            # The text mirror leaves the map link out: the address is on the
            # card already, and the URL cannot fit in 75 columns.
            blocks.append({"k": "para", "cls": ["small"], "text": " · ".join(links), "txt": site})
    return {"k": "entry", "id": None, "cls": ["link"] if link else [], "meta": line,
            "blocks": blocks, "own": not link,
            "title": f"[{meta['title']}]({item['path'][:-5]})" if link else meta["title"]}


def upcoming(items, conf):
    """{upcoming}: today or later, nearest first, the first marked next."""
    chosen = [e for e in items if e["date"] >= STATE["today"]]
    return {"items": [(e, ["next"] if n == 0 else []) for n, e in enumerate(chosen)],
            "empty": conf.get("none_upcoming", "")}


def next_event(items, conf):
    """{next-event}: the next one only."""
    r = upcoming(items, conf)
    r["items"] = r["items"][:1]
    return r


def past(items, conf):
    """{past}: before today, latest first."""
    return {"items": [(e, []) for e in reversed(items) if e["date"] < STATE["today"]],
            "empty": conf.get("none_past", "")}


MARKERS = {"upcoming": upcoming, "past": past, "next-event": next_event}


def json_ld(item, conf):
    meta = item["meta"]
    place = {"@type": "Place", "name": meta.get("place", ""), "address": meta.get("place", "")}
    if meta.get("lat") and meta.get("lon"):
        place["geo"] = {"@type": "GeoCoordinates", "latitude": meta["lat"], "longitude": meta["lon"]}
    return {"@type": "Event", "name": page_heading(meta),
            "description": meta["description"], "startDate": item["date"],
            "endDate": meta.get("end", item["date"]),
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "location": place, "organizer": org_ref(), "image": share_image(meta)[0]}


def feed_item(item, conf):
    return {"title": item["meta"]["title"], "link": apex() + clean_url(item["path"]),
            "description": item["meta"]["description"], "date": item["date"]}


def outputs(items, conf):
    """The collection's iCalendar, when `calendar` names a path."""
    return {conf["calendar"]: calendar(items)} if conf.get("calendar") else {}
```

Until Task 8, `feeds.calendar` reads `e["iso"]`, and items now carry `date`. Make `calendar` accept both now, so the event test passes and the reference build stays identical: in `src/feeds.py`, in `calendar()`, change `day = datetime.date.fromisoformat(e["iso"])` to `day = datetime.date.fromisoformat(e.get("date") or e["iso"])`. Task 8 removes the fallback.

Then `git rm types/.keep`.

- [ ] **Step 6: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 7: Commit**

```bash
git add types/post.py types/event.py src/seo.py src/feeds.py tests/test_type_post.py tests/test_type_event.py tests/test_stdlib.py
git rm -q types/.keep
git commit -m "feat: post and event as type modules"
```

---

### Task 5: `types/member.py` and `types/page.py`

**Files:**
- Create: `types/member.py`, `types/page.py`
- Test: `tests/test_type_member.py`, `tests/test_type_page.py`

**Interfaces:**
- Consumes: `fold.to_ascii`, `config.CFG["labels"]["website"]`, `seo.page_heading`, `seo.page_title`, `seo.org_ref`, `seo.site_ref`.
- Produces: the `member` type (`SCRIPT = "members.js"`, marker `members`, `list_data`), the `page` type (`entry` returns `None`, `json_ld` a WebPage node).

- [ ] **Step 1: Write the failing tests**

`tests/test_type_member.py`:

```python
import unittest

import contenttypes
from config import load_config

CONF = None


def setUpModule():
    global CONF
    load_config()
    member = contenttypes.load([contenttypes.BUILTIN])["member"]
    CONF = {**member.DEFAULTS, "dir": "members", "type": "member",
            "categories": ["admin", "mentor", "member"]}


def item(slug="ada-lovelace", **meta):
    m = {"title": "Ada Lovelace", "description": "One sentence.", "first_name": "Ada", "last_name": "Lovelace"}
    m.update(meta)
    return {"slug": slug, "date": None, "meta": m, "src": None, "path": f"members/{slug}.html",
            "collection": "members", "conf": CONF, "type": contenttypes.TYPES["member"]}


class Member(unittest.TestCase):
    def setUp(self):
        self.member = contenttypes.TYPES["member"]

    def test_flags(self):
        self.assertFalse(self.member.DATED)
        self.assertFalse(self.member.ARTICLE)
        self.assertEqual(self.member.SCRIPT, "members.js")
        self.assertEqual(set(self.member.MARKERS), {"members"})
        self.assertFalse(self.member.HAS_FEED)

    def test_card_in_the_grid(self):
        node = self.member.entry(item(category="admin", pronouns="she/her", affiliation="Analytical Engines",
                                      github="https://github.com/ada https://github.com/engines",
                                      website="https://ada.example"), True, CONF)
        self.assertEqual(node["title"], "[Ada Lovelace](members/ada-lovelace)")
        self.assertEqual(node["cls"], [])
        self.assertEqual(node["meta"], ["she/her", "Analytical Engines", "`admin`"])
        self.assertEqual(node["data"], {"category": "admin", "search": "ada lovelace"})
        self.assertEqual(node["blocks"], [{"k": "profiles", "items": [
            ("github", "GitHub (ada)", "https://github.com/ada"),
            ("github", "GitHub (engines)", "https://github.com/engines"),
            ("website", "website", "https://ada.example"),
        ]}])

    def test_full_mentor_says_so(self):
        node = self.member.entry(item(category="mentor", capacity="2 per term", full="yes"), True, CONF)
        self.assertEqual(node["meta"], ["2 per term", "full", "`mentor`"])
        self.assertEqual(node["cls"], ["full"])

    def test_display_name_and_default_category(self):
        node = self.member.entry(item(display_name="Ada"), False, CONF)
        self.assertEqual(node["title"], "Ada")
        self.assertTrue(node["own"])
        self.assertEqual(node["meta"], ["`member`"])
        self.assertEqual(node["data"]["search"], "ada lovelace")

    def test_sort_key_category_then_last_name(self):
        admin = item("z", category="admin", last_name="Zuse")
        member = item("a", category="member", last_name="Émile")
        stray = item("q", category="guest", last_name="Q")
        keys = sorted([self.member.sort_key(it, CONF) for it in (stray, member, admin)])
        self.assertEqual([k[2] for k in keys], ["z", "a", "q"])
        self.assertEqual(self.member.sort_key(member, CONF)[1], "emile")

    def test_defaults(self):
        it = item()
        del it["meta"]["description"]
        self.member.defaults(it, CONF)
        self.assertEqual(it["meta"]["man"], "SITE-MEMBERS(7)")
        self.assertEqual(it["meta"]["nav"], "members")
        self.assertEqual(it["meta"]["description"], "")

    def test_grid_marker(self):
        r = self.member.MARKERS["members"]([item()], CONF)
        self.assertEqual(r["cls"], ["grid"])
        self.assertEqual(r["empty"], "No member listed yet.")
        self.assertEqual(len(r["items"]), 1)

    def test_list_data(self):
        self.assertEqual(self.member.list_data(CONF), {
            "search_label": "search", "search_placeholder": "first or last name",
            "all": "all", "one": "entry", "many": "entries", "none": "No entry matches."})

    def test_json_ld(self):
        node = self.member.json_ld(item(github="https://github.com/ada", affiliation="Engines"), CONF)
        self.assertEqual(node["@type"], "ProfilePage")
        self.assertEqual(node["mainEntity"]["sameAs"], ["https://github.com/ada"])
        self.assertEqual(node["mainEntity"]["affiliation"], {"@type": "Organization", "name": "Engines"})
        self.assertEqual(node["mainEntity"]["memberOf"], {"@id": "https://test.example/#organization"})
```

`tests/test_type_page.py`:

```python
import unittest

import contenttypes
from config import load_config


class Page(unittest.TestCase):
    def setUp(self):
        load_config()
        self.page = contenttypes.load([contenttypes.BUILTIN])["page"]

    def test_a_page_has_no_card(self):
        item = {"slug": "index", "date": None, "meta": {"title": "t", "description": "d"},
                "path": "index.html", "collection": None, "conf": {}, "type": self.page}
        self.assertIsNone(self.page.entry(item, False, {}))
        self.assertFalse(self.page.DATED)
        self.assertEqual(self.page.MARKERS, {})

    def test_web_page_node(self):
        item = {"meta": {"title": "about", "description": "d"}, "path": "about.html", "conf": {}}
        node = self.page.json_ld(item, {})
        self.assertEqual(node, {"@type": "WebPage", "name": "about - test site", "description": "d",
                                "isPartOf": {"@id": "https://test.example/#website"}})
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_type_member tests.test_type_page -v`
Expected: FAIL with `KeyError: 'member'` / `'page'`.

- [ ] **Step 3: Write `types/member.py`**

```python
"""Members: one page each, a searchable grid, a profile card with the
person's public links. The built-in `member` type (docs/types.md)."""

from config import CFG
from fold import to_ascii
from seo import org_ref, page_heading, page_title

NAME = "member"
SCRIPT = "members.js"   # search and filter on a {members} page, if the theme ships it
DEFAULTS = {
    "man": "SITE-MEMBERS(7)",
    "nav": "members",
    "categories": ["admin", "member"],   # display and sort order
    "default_category": "member",
    "empty": "No member listed yet.",
    "search_label": "search",
    "search_placeholder": "first or last name",
    "all": "all",
    "one": "entry",
    "many": "entries",
    "none": "No entry matches.",
    "full": "full",                      # a mentor at capacity, said in words
}

# Profiles a member may list, in display order: front-matter key, and the
# name read by screen readers and shown in the text mirror. `website` is
# named by labels.website.
NETWORKS = (("linkedin", "LinkedIn"), ("github", "GitHub"), ("gitlab", "GitLab"),
            ("mastodon", "Mastodon"), ("bluesky", "Bluesky"), ("website", None))


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("description", "")


def member_name(meta):
    """The name shown: the chosen name if given, else first and last."""
    return meta.get("display_name") or " ".join(
        n for n in (meta.get("first_name", ""), meta.get("last_name", "")) if n)


def profiles(meta):
    """[(key, label, url)] of the member's public profiles. A key may hold
    several URLs, separated by spaces (a personal and a company GitHub):
    each is then named with its handle, "GitHub (ada)"."""
    out = []
    for key, label in NETWORKS:
        urls = meta.get(key, "").split()
        name = label or CFG["labels"]["website"]
        for url in urls:
            handle = url.rstrip("/").rsplit("/", 1)[-1]
            out.append((key, f"{name} ({handle})" if len(urls) > 1 else name, url))
    return out


def sort_key(item, conf):
    """Category order, then last name (ASCII, lower), then slug."""
    meta, order = item["meta"], conf["categories"]
    category = meta.get("category", conf["default_category"])
    rank = (order.index(category) if category in order else len(order), category)
    return (rank, to_ascii(meta.get("last_name", "")).lower(), item["slug"])


def entry(item, link, conf):
    """The card: name, pronouns, affiliation, capacity, category tag, the
    profile links; and the words members.js searches."""
    meta = item["meta"]
    name = member_name(meta)
    line = [meta[k] for k in ("pronouns", "affiliation", "capacity") if meta.get(k)]
    category = meta.get("category", conf["default_category"])
    if meta.get("full") == "yes":
        line.append(conf["full"])  # said in words, not only by the tag's colour
    line.append(f"`{category}`")
    names = [name, meta.get("first_name", ""), meta.get("last_name", "")]
    links = profiles(meta)
    return {
        "k": "entry", "id": None, "own": not link,
        "blocks": [{"k": "profiles", "items": links}] if links else [],
        "meta": line,
        "title": f"[{name}]({item['path'][:-5]})" if link else name,
        "cls": ["full"] if meta.get("full") == "yes" else [],
        "data": {"category": category,
                 "search": " ".join(dict.fromkeys(to_ascii(" ".join(names)).lower().split()))},
    }


def grid(items, conf):
    """{members}: every member, in load order, as a grid."""
    return {"items": [(it, []) for it in items], "empty": conf.get("empty", ""), "cls": ["grid"]}


MARKERS = {"members": grid}


def list_data(conf):
    """The search's wording, for members.js: it holds no text itself."""
    return {k: conf[k] for k in ("search_label", "search_placeholder", "all", "one", "many", "none")}


def json_ld(item, conf):
    meta = item["meta"]
    person = {"@type": "Person", "name": page_heading(meta), "memberOf": org_ref()}
    same = [url for key, _ in NETWORKS for url in meta.get(key, "").split()]
    if same:
        person["sameAs"] = same  # links the profiles to the person
    if meta.get("affiliation"):
        person["affiliation"] = {"@type": "Organization", "name": meta["affiliation"]}
    return {"@type": "ProfilePage", "name": page_title(meta), "mainEntity": person}
```

- [ ] **Step 4: Write `types/page.py`**

```python
"""Pages: every .md outside a collection. No card, no list, a WebPage node."""

from seo import page_title, site_ref

NAME = "page"


def entry(item, link, conf):
    """A page has no card."""
    return None


def json_ld(item, conf):
    return {"@type": "WebPage", "name": page_title(item["meta"]),
            "description": item["meta"]["description"], "isPartOf": site_ref()}
```

- [ ] **Step 5: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add types/member.py types/page.py tests/test_type_member.py tests/test_type_page.py
git commit -m "feat: member and page as type modules"
```

---

### Task 6: Collections, items and lists through the types

This is the switch: `build.py` stops knowing members, posts and events; `dated.py` and `members.py` go; `defaults.toml` and the fixture's `site.toml` take the new form; the reference site's `site.toml` is migrated. `seo.py`, `feeds.py` and `page.py` still run on `meta["_kind"]` and `it["iso"]` for one more task each, fed by a compatibility shim in `build.py` that this task installs and Tasks 7-9 remove.

**Files:**
- Modify: `src/contenttypes.py` (add `collections`, `load_items`, `page_item`, `fill_lists`, `summary`)
- Modify: `src/paths.py` (`ITEM_FOLDERS`, `rendered`, `page_path`)
- Modify: `src/build.py` (`build()`, docstring map)
- Modify: `defaults.toml`
- Delete: `src/dated.py`, `src/members.py`
- Modify: `tests/site/content/site.toml`, `$SITE/content/site.toml` (the reference site, outside this repository)
- Test: `tests/test_collections.py`, `tests/test_smoke.py` (fix the Task 0 assertion if it was relaxed)

**Interfaces:**
- Consumes: `contenttypes.load`, the four types, `report.error/fail`, `markdown.front_matter`, `config.CONFIG`, `config.DATED`.
- Produces:
  - `contenttypes.collections() -> dict[str, dict]`: `{name: conf}` in declaration order; `conf` = type `DEFAULTS` deep-copied, updated with `[collections.<name>]`, `dir` defaulting to the name, `type` the type's NAME. Errors gathered: old plural type, unknown type, `[members]` table, overlapping `dir`.
  - `contenttypes.load_items(name, conf) -> list[dict]`: items sorted by the type's `sort_key`; `defaults()` applied; registers non-dated item folders in `paths.ITEM_FOLDERS`.
  - `contenttypes.page_item(src, meta) -> dict`: an item of type `page` for a `.md` outside every collection.
  - `contenttypes.fill_lists(sections, src, path, colls, items) -> None`: fills marked sections (`s["blocks"]`, `s["cls"]`, `s["data"]`, `s["script"]`) and appends the item's own card to its first section.
  - `contenttypes.summary(colls, items) -> str`: the two lines of spec §9.
  - `paths.ITEM_FOLDERS: set[str]` - `content/`-relative folders of items kept as folders.

- [ ] **Step 1: Write the failing tests**

`tests/test_collections.py`:

```python
import unittest

import contenttypes
import paths
import report
from config import CFG, CONTENT, load_config
from tests.helpers import build_site, rebuild


class Collections(unittest.TestCase):
    def setUp(self):
        load_config()
        contenttypes.load()

    def test_declared_collections_merge_type_defaults(self):
        colls = contenttypes.collections()
        self.assertEqual(list(colls), ["blog", "events", "members", "news"])
        self.assertEqual(colls["blog"]["type"], "post")
        self.assertEqual(colls["blog"]["dir"], "blog")
        self.assertEqual(colls["blog"]["feed"], "blog/feed.xml")
        self.assertEqual(colls["blog"]["empty"], "No post yet.")          # from post.DEFAULTS
        self.assertEqual(colls["members"]["categories"], ["admin", "mentor", "member"])
        self.assertEqual(colls["members"]["search_label"], "search")     # from member.DEFAULTS

    def test_missing_folder_is_an_empty_collection(self):
        colls = contenttypes.collections()
        self.assertEqual(contenttypes.load_items("news", colls["news"]), [])
        out = build_site()
        self.assertFalse(any(k.startswith("news") for k in out), [k for k in out if k.startswith("news")])

    def test_items_are_sorted_by_the_type(self):
        colls = contenttypes.collections()
        events = contenttypes.load_items("events", colls["events"])
        self.assertEqual([e["slug"] for e in events], ["2000-01-01-past-meetup", "2099-01-01-future-meetup"])
        self.assertEqual(events[0]["date"], "2000-01-01")
        self.assertEqual(events[0]["path"], "events/2000-01-01-past-meetup.html")
        self.assertIs(events[0]["type"], contenttypes.TYPES["event"])
        self.assertEqual(events[0]["meta"]["man"], "SITE-EVENTS(7)")   # defaults() applied
        members = contenttypes.load_items("members", colls["members"])
        self.assertEqual([m["slug"] for m in members], ["ada-lovelace", "alan-turing"])  # admin first
        self.assertIsNone(members[0]["date"])

    def test_member_folder_registers_and_renders_flat(self):
        colls = contenttypes.collections()
        contenttypes.load_items("members", colls["members"])
        self.assertIn("members/alan-turing", paths.ITEM_FOLDERS)
        self.assertTrue(paths.rendered(CONTENT / "members/alan-turing/index.md"))
        self.assertFalse(paths.rendered(CONTENT / "members/alan-turing/notes.txt"))
        self.assertEqual(paths.page_path(CONTENT / "members/alan-turing/index.md"), "members/alan-turing.html")
        out = build_site()
        self.assertIn("members/alan-turing.html", out)
        self.assertNotIn("members/alan-turing/index.html", out)
        self.assertIn("members/alan-turing/notes.txt", out)

    def fails_with(self, *fragments):
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.collections()
        text = "\n".join(m for m, _ in cm.exception.items)
        for f in fragments:
            self.assertIn(f, text)
        return text

    def test_plural_type_is_refused_with_the_fix(self):
        CFG["collections"]["blog"]["type"] = "posts"
        self.fails_with('collection "blog" has type "posts"; types are singular', 'Write type = "post"')

    def test_unknown_type_lists_the_loaded_ones(self):
        CFG["collections"]["talks"] = {"type": "talk"}
        text = self.fails_with('collection "talks" has type "talk", which no type defines', "Types loaded:")
        self.assertIn("event, member, page, post (types/)", text)   # load order: file names

    def test_old_members_table_is_refused(self):
        CFG["members"] = {"categories": ["a"]}
        self.fails_with("[members] is no longer read", "[collections.members]")

    def test_overlapping_dirs(self):
        CFG["collections"]["also"] = {"type": "post", "dir": "blog"}
        self.fails_with('collections "blog" and "also" share the folder content/blog')

    def test_errors_are_gathered(self):
        CFG["collections"]["blog"]["type"] = "posts"
        CFG["collections"]["talks"] = {"type": "talk"}
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.collections()
        self.assertEqual(len(cm.exception.items), 2)


class Lists(unittest.TestCase):
    def test_upcoming_past_next_and_own_card(self):
        out = build_site()
        events = out["events.html"]
        self.assertIn('class="entry entry--next entry--link"', events)
        self.assertIn('class="b upcoming"', events)
        self.assertIn('class="b past"', events)
        self.assertIn(">Past meetup</a>", events)
        self.assertIn("Future meetup", out["index.html"])            # {next-event}
        self.assertNotIn("Past meetup", out["index.html"])
        own = out["events/2099-01-01-future-meetup.html"]
        self.assertIn('class="entry"', own)                          # the heading card, no link
        self.assertIn("see on OpenStreetMap", own)

    def test_members_grid_and_search_words(self):
        out = build_site()
        members = out["members.html"]
        self.assertIn('class="b members grid" data-search-label="search" data-search-placeholder="first or last name" '
                      'data-all="all" data-one="entry" data-many="entries" data-none="No entry matches."', members)
        self.assertIn('data-category="admin" data-search="ada lovelace"', members)
        self.assertNotIn("members.js", members)                      # the fixture theme ships none
        self.assertIn('class="entry" data-category="member"', out["members/alan-turing.html"])

    def test_posts_list_and_text_mirror(self):
        out = build_site()
        self.assertIn(">Hello</a>", out["blog/index.html"])
        self.assertIn("[ note ]", out["txt/blog/2026-01-01-hello.txt"])
        self.assertIn("[ upcoming ]", out["txt/events.txt"])
        self.assertIn("GitHub: https://github.com/ada", out["txt/members/ada-lovelace.txt"])

    def test_named_marker_must_exist(self):
        load_config()
        contenttypes.load()
        colls = contenttypes.collections()
        sections = [{"k": "section", "title": "x", "cls": ["upcoming:nope"], "id": None, "blocks": []}]
        with self.assertRaises(report.BuildError) as cm:
            contenttypes.fill_lists(sections, CONTENT / "index.md", "index.html", colls, {})
        self.assertIn("content/index.md: {upcoming:nope} names no event collection", str(cm.exception))
        self.assertIn("Collections of that type: events", str(cm.exception))

    def test_summary(self):
        load_config()
        contenttypes.load()
        colls = contenttypes.collections()
        items = {n: contenttypes.load_items(n, c) for n, c in colls.items()}
        self.assertEqual(contenttypes.summary(colls, items),
                         "types: event, member, page, post\n"
                         "collections: blog (post, 1 item), events (event, 2 items), "
                         "members (member, 2 items), news (post, no folder)")
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_collections -v`
Expected: FAIL, `AttributeError: module 'contenttypes' has no attribute 'collections'`.

- [ ] **Step 3: Add `ITEM_FOLDERS` to `paths.py`**

In `src/paths.py`, after the imports:

```python
# content/-relative folders that are one item each (a member kept as a
# folder with a file beside its page): only their index.md is a page, and
# it is served next to the folder. Filled by contenttypes.load_items.
ITEM_FOLDERS = set()


def item_folder(rel_parent):
    """Is this content/-relative folder one item?"""
    return bool(DATED.match(rel_parent.name)) or str(rel_parent) in ITEM_FOLDERS
```

Change `rendered` and `page_path` to use it:

```python
def rendered(path):
    """A Markdown file is a page unless a part of its path starts with `_`
    (templates), or it sits in an item's folder without being its index.md."""
    rel = path.relative_to(CONTENT)
    if any(part.startswith("_") for part in rel.parts):
        return False
    return rel.name == "index.md" or not item_folder(rel.parent)


def page_path(src):
    """content/blog/X/index.md -> blog/X.html: an item folder's page sits
    next to the folder, so the URL does not change with the layout."""
    rel = src.relative_to(CONTENT)
    if rel.name == "index.md" and item_folder(rel.parent):
        return str(rel.parent) + ".html"
    return str(rel.with_suffix(".html"))
```

- [ ] **Step 4: Add collections, items and lists to `contenttypes.py`**

Append to `src/contenttypes.py` (and extend its imports):

```python
import datetime

import paths
from config import CFG, CONFIG, CONTENT, DATED
from markdown import front_matter
```

```python
def _loaded():
    """"page, post, event, member (types/), doc (theme/types/doc.py)"."""
    builtin = [n for n, m in TYPES.items() if m.PATH.parent == BUILTIN]
    theme = [f"{n} ({rel(m.PATH)})" for n, m in TYPES.items() if m.PATH.parent != BUILTIN]
    parts = [", ".join(builtin) + " (types/)"] if builtin else []
    return ", ".join(parts + theme)


def collections():
    """{name: settings} of every [collections.<name>] in site.toml, each
    over its type's DEFAULTS, in declaration order. Every problem is
    reported before the build stops."""
    out, errs = {}, []
    if "members" in CFG:
        errs.append(error(CONFIG, "[members] is no longer read",
                          'Move its keys under [collections.members], with type = "member"'))
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
    if errs:
        fail(errs)
    return out


def load_items(name, conf):
    """Every item of a collection, in the type's order. An item is <slug>.md
    or <slug>/index.md in content/<dir>/; for a DATED type the slug starts
    with YYYY-MM-DD. Names starting with _ are templates."""
    module, base, items = TYPES[conf["type"]], CONTENT / conf["dir"], []
    for f in sorted(base.iterdir()) if base.is_dir() else []:
        slug = f.stem if f.suffix == ".md" else f.name
        src = f if f.suffix == ".md" else f / "index.md"
        if f.name.startswith("_") or not src.is_file() or slug == "index":
            continue
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
        elif f.is_dir():
            paths.ITEM_FOLDERS.add(str(f.relative_to(CONTENT)))
        meta, _ = front_matter(src.read_text())
        items.append({"slug": slug, "date": date, "meta": meta, "src": src,
                      "path": f"{conf['dir']}/{slug}.html", "collection": name,
                      "conf": conf, "type": module})
    for it in items:
        module.defaults(it, conf)
    return sorted(items, key=lambda it: module.sort_key(it, conf))


def page_item(src, meta):
    """A .md outside every collection, as an item of type page."""
    return {"slug": src.stem, "date": None, "meta": meta, "src": src,
            "path": paths.page_path(src), "collection": None, "conf": {}, "type": TYPES["page"]}


def _target(marker, src, path, colls):
    """The collection a marker lists: {upcoming:talks} names it; a bare
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
    """Fill every section carrying a list marker ({posts}, {upcoming:talks},
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
            chosen = module.MARKERS[word](its, conf)
            cards = []
            for it, extra in chosen["items"]:
                node = module.entry(it, True, conf)
                node["cls"] = list(extra) + node["cls"]
                cards.append(node)
            s["cls"].extend(chosen.get("cls", []))
            s["blocks"] = (cards or [{"k": "empty", "text": chosen.get("empty", "")}]) + s["blocks"]
            s["data"] = module.list_data(conf) if name else {}
            s["script"] = module.SCRIPT
    for its in items.values():
        for it in its:
            if it["path"] == path and sections:
                card = it["type"].entry(it, False, it["conf"])
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
```

Also make `load()` clear `paths.ITEM_FOLDERS` at its start (`paths.ITEM_FOLDERS.clear()` next to `TYPES.clear()`), so a watch rebuild does not keep folders that were removed.

- [ ] **Step 5: Rewrite `build()` in `src/build.py`**

Replace the imports of `dated` and `members`, and the body of `build()`:

```python
import contenttypes
import report
from config import (ASSETS, BUILDER, CFG, CONFIG, CONTENT, EXTRA, ROOT, STATE, TEMPLATES,
                    THEME, apex, load_config)
from icons import generated
from fold import to_ascii
from feeds import calendar, events_feed, posts_feed
from markdown import parse, site_path
from page import render_html
from paths import clean_url, rendered, txt_name
from seo import check, manifest, robots, sitemap_xml
from text import plain, render_txt
from watch import snapshot, watch
```

```python
def build():
    """Every output file, as {relative path: bytes}."""
    load_config()
    inline.EXTERNAL = CFG["labels"]["external"]
    inline.NEW_TAB_LABEL = CFG["labels"]["new_tab"]
    inline.NEW_TAB = CFG["links"]["new_tab"]
    inline.SAME_TAB = tuple(CFG["links"]["same_tab"])
    ansify_module.COMMANDS = CFG["text"]["commands"]
    ansify_module.BOXES = {
        to_ascii(CFG["labels"][kind]): colour for kind, colour in
        (("info", ansify_module.CYAN), ("warning", ansify_module.YELLOW),
         ("error", ansify_module.RED))}
    STATE["today"] = os.environ.get("BUILD_TODAY") or datetime.date.today().isoformat()
    contenttypes.load()
    colls = contenttypes.collections()
    items = {name: contenttypes.load_items(name, conf) for name, conf in colls.items()}
    by_src = {it["src"]: it for its in items.values() for it in its}
    STATE["summary"] = contenttypes.summary(colls, items)
    out, pages = {}, []  # pages: every item that is an HTML page, for sitemap and SEO checks
    for src in sorted(p for p in CONTENT.rglob("*.md") if rendered(p)):
        meta, sections, preamble = parse(src)
        it = by_src[src] if src in by_src else contenttypes.page_item(src, meta)
        meta = it["meta"]
        meta["_dir"] = site_path(src)
        _compat(it)  # Tasks 7-9 remove this
        pages.append(it)
        contenttypes.fill_lists(sections, src, it["path"], colls, items)
        out[it["path"]] = render_html(meta, sections, it["path"], preamble, colls)
        if meta.get("text", "yes") != "no":
            marked = render_txt(meta, sections)
            out[f"txt/{txt_name(it['path'])}.txt"] = plain(marked)
            out[f"ansi/{txt_name(it['path'])}.txt"] = ansify(marked)
    # Feeds and the type's own files, for the collections whose folder exists.
    for name, conf in colls.items():
        if not (CONTENT / conf["dir"]).is_dir():
            continue
        if conf["type"] == "post" and conf.get("feed"):
            out[conf["feed"]] = posts_feed(items[name], conf)
        if conf["type"] == "event":
            if conf.get("feed"):
                out[conf["feed"]] = events_feed(items[name], conf)
            if conf.get("calendar"):
                out[conf["calendar"]] = calendar(items[name])
    a = apex()
    meta_pages = [(it["path"], it["meta"]) for it in pages]
    indexed = [(p, m) for p, m in meta_pages if "noindex" not in m.get("robots", "")]
    out["sitemap.xml"] = sitemap_xml(indexed)
    out["sitemap.txt"] = "".join(f"{a}{clean_url(p)}\n" for p, _ in
                                 sorted(indexed, key=lambda p: clean_url(p[0])))
    out["robots.txt"] = robots(CFG["robots"], f"{a}/sitemap.xml")
    check(meta_pages)
    # txt/ is the root of the plain-text host: this is its /robots.txt.
    out["txt/robots.txt"] = robots(CFG["robots_man"])
    out["site.webmanifest"] = manifest()
    out = {k: v.encode("utf-8") for k, v in out.items()}
    # ... the copy loops for content/, theme/, assets/, generated(), EXTRA: unchanged ...
    return out


def _compat(it):
    """Until seo.py, feeds.py and page.py ask the type (Tasks 7-9): the
    old keys they read."""
    it["meta"]["_kind"] = it["type"].NAME
    if it["date"]:
        it["meta"]["_date"] = it["date"]
        it["iso"] = it["date"]
```

Keep the copy loops at the end of `build()` exactly as they are. Print the summary once, in `build_into`:

```python
_SAID = False


def build_into(dest):
    global _SAID
    changed = write(build(), dest)
    if not _SAID:
        print(STATE["summary"], flush=True)
        _SAID = True
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] built {dest}: " + (", ".join(changed) or "no change"), flush=True)
```

In `src/feeds.py`, `events_feed` and `posts_feed` read `e['iso']` / `it["iso"]`: `_compat` sets `it["iso"]`, so they keep working until Task 8.

Update the module map in the docstring of `src/build.py`: remove `members.py` and `dated.py`, add:

```
    contenttypes.py the types (types/, theme/types/), collections, items, lists
    report.py     errors and warnings, one shape
    dates.py      dates in words, from [dates]
```

and after the map: `types/ holds the built-in content types, one module each (docs/types.md).`

Delete `src/dated.py` and `src/members.py`: `git rm src/dated.py src/members.py`. Remove `from dated import human_date`-style imports anywhere left (`grep -rn "dated\|members" src/` must show only comments and the `members.js` string in `page.py`).

- [ ] **Step 6: Rewrite `defaults.toml`'s collection part**

Replace everything from the comment block `# Dated collections: folders of YYYY-MM-DD-slug items...` down to and including the `[collections.events]` table, and the whole `[members]` table, with:

```toml
# Collections: a folder under content/ whose files are items of one type.
# A site declares its own as [collections.<name>]: a `type` (page, post,
# event, member, or one the theme adds in theme/types/), a `dir` under
# content/ (default: the name), and whatever differs from the type's
# defaults - every type's words and settings are listed in its module,
# types/<type>.py (DEFAULTS), and documented in docs/types.md. A collection
# whose folder does not exist is simply empty: no page, no feed. Lists are
# shown by section markers: {posts}, {upcoming}, {past}, {next-event},
# {members}, each with an optional collection name - {upcoming:talks}.
#
# The three collections most sites have. Inactive until content/blog/,
# content/events/ or content/members/ exists.

[collections.blog]
type = "post"
dir = "blog"
feed = "blog/feed.xml"

[collections.events]
type = "event"
dir = "events"
nav = "events"
feed = "events.xml"
calendar = "calendar.ics"

[collections.members]
type = "member"
dir = "members"
```

Keep `[dates]`, `[calendar]`, `[text]`, `[robots]`, `[robots_man]` as they are. The header comment of the file says "every key the builder reads": amend it to "every key the builder reads, except a type's own (types/<type>.py)".

- [ ] **Step 7: Migrate the fixture's `site.toml` and the reference site's**

In `tests/site/content/site.toml`: `type = "posts"` -> `type = "post"` (twice), `type = "events"` -> `type = "event"`, and replace the `[members]` table with:

```toml
[collections.members]
type = "member"
categories = ["admin", "mentor", "member"]
```

In `$SITE/content/site.toml` (the reference site, its own repository): the same two renames, and move every key of its `[members]` table under `[collections.members]` with `type = "member"` as its first key, keeping the comments. Do **not** commit that file from here: it belongs to the site's repository and is committed there when the submodule is bumped (spec §15). Leave it modified in the working tree for the diffs of this plan.

- [ ] **Step 8: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: every test PASS (fix the Task 0 smoke assertion back to `members/alan-turing.html` if it was relaxed); `IDENTICAL`. The reference site has no member kept as a folder, so its output cannot move; if the diff shows anything, it is a real regression in this task.

Also check the summary and the old-form messages by hand:

```bash
python3 build.py --root "$SITE" --out /tmp/tilder-after | head -3
git -C "$SITE" stash -q -- content/site.toml && python3 build.py --root "$SITE" --out /tmp/tilder-old; git -C "$SITE" stash pop -q
```

Expected: the two summary lines, then the `built` line; with the old `site.toml`, three `error:` lines (two plural types, the `[members]` table), exit status 1.

- [ ] **Step 9: Commit**

```bash
git add src/contenttypes.py src/paths.py src/build.py defaults.toml tests/
git rm -q src/dated.py src/members.py
git commit -m "feat!: collections, items and lists go through the content types

Members stop being a special case: [collections.members], type member.
Type names are singular (post, event). A type's defaults live in its
module; [collection_defaults.*] and [members] leave defaults.toml."
```

---

### Task 7: `seo.py` asks the type

**Files:**
- Modify: `src/seo.py` (`head_tags`, `json_ld`, `sitemap_xml`, `check`; remove the kind constants)
- Modify: `src/page.py` (`render_html(item, ...)`, `<article>` from `ARTICLE`, `head_tags(item)`)
- Modify: `src/build.py` (call sites; `_compat` loses `_kind`/`_date`)
- Test: `tests/test_seo.py`

**Interfaces:**
- Produces: `seo.head_tags(item) -> str`; `seo.json_ld(item, image) -> str`; `seo.sitemap_xml(items) -> str`; `seo.check(items) -> list[str]`; `page.render_html(item, sections, preamble=(), colls=None) -> str`.

- [ ] **Step 1: Write the failing tests**

`tests/test_seo.py`:

```python
import json
import re
import unittest

from tests.helpers import build_site


def graph(html):
    data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return json.loads(data.replace("<\\/", "</"))["@graph"]


class Seo(unittest.TestCase):
    def test_each_type_has_its_node(self):
        out = build_site()
        kinds = {t["@type"] for t in graph(out["blog/2026-01-01-hello.html"])}
        self.assertIn("BlogPosting", kinds)
        kinds = {t["@type"] for t in graph(out["events/2099-01-01-future-meetup.html"])}
        self.assertIn("Event", kinds)
        kinds = {t["@type"] for t in graph(out["members/ada-lovelace.html"])}
        self.assertIn("ProfilePage", kinds)
        kinds = {t["@type"] for t in graph(out["index.html"])}
        self.assertIn("WebPage", kinds)

    def test_og_type_and_article_tags_only_for_posts(self):
        out = build_site()
        post = out["blog/2026-01-01-hello.html"]
        self.assertIn('<meta property="og:type" content="article">', post)
        self.assertIn('<meta name="author" content="Ada Lovelace">', post)
        self.assertIn('<meta property="article:published_time" content="2026-01-01">', post)
        self.assertIn('<meta property="article:tag" content="note">', post)
        event = out["events/2099-01-01-future-meetup.html"]
        self.assertIn('<meta property="og:type" content="website">', event)
        self.assertNotIn("article:published_time", event)

    def test_article_wrapper_for_posts_and_events_only(self):
        out = build_site()
        self.assertIn("<article>", out["blog/2026-01-01-hello.html"])
        self.assertIn("<article>", out["events/2099-01-01-future-meetup.html"])
        self.assertNotIn("<article>", out["members/ada-lovelace.html"])
        self.assertNotIn("<article>", out["index.html"])

    def test_sitemap_lastmod_is_the_item_date(self):
        out = build_site()
        self.assertIn("<loc>https://test.example/blog/2026-01-01-hello</loc>\n\t\t<lastmod>2026-01-01</lastmod>",
                      out["sitemap.xml"])
        self.assertIn("<loc>https://test.example/</loc>\n\t\t<lastmod>2026-06-01</lastmod>", out["sitemap.xml"])
        self.assertNotIn("/404", out["sitemap.xml"])
```

- [ ] **Step 2: Run them**

Run: `python3 -m unittest tests.test_seo -v`
Expected: PASS already (the shim keeps the old behaviour). These tests guard the next steps; keep going.

- [ ] **Step 3: Make `seo.py` ask the type**

Remove the line `POST, EVENT, MEMBER, PAGE = "post", "event", "member", "page"` and its comment. Rewrite `head_tags` and `json_ld`:

```python
def head_tags(item):
    """Everything search engines and sharing read in <head>, after the
    canonical link: robots, the type's name tags, Open Graph, the type's
    property tags, Twitter Card, JSON-LD."""
    meta, module, conf, path = item["meta"], item["type"], item["conf"], item["path"]
    image, width, height = share_image(meta)
    large = bool(width and height and width >= 600 and width > height)
    extra = module.meta_tags(item, conf)
    out = [f'<meta name="robots" content="{H.escape(meta.get("robots", CFG["seo"]["robots"]))}">']
    out += [f'<meta name="{k}" content="{H.escape(v)}">' for a, k, v in extra if a == "name"]
    props = [
        ("og:site_name", CFG["site"]["name"]),
        ("og:locale", CFG["site"]["locale"]),
        ("og:type", module.OG_TYPE),
        ("og:title", page_heading(meta)),
        ("og:description", meta["description"]),
        ("og:url", apex() + clean_url(path)),
        ("og:image", image),
        ("og:image:alt", meta.get("image_alt") or CFG["share"]["image_alt"]),
    ]
    if width and height:
        props += [("og:image:width", str(width)), ("og:image:height", str(height))]
    props += [(k, v) for a, k, v in extra if a == "property"]
    out += [f'<meta property="{k}" content="{H.escape(v)}">' for k, v in props]
    out += [f'<meta name="{k}" content="{H.escape(v)}">' for k, v in [
        ("twitter:card", "summary_large_image" if large else "summary"),
        ("twitter:title", page_heading(meta)),
        ("twitter:description", meta["description"]),
        ("twitter:image", image),
    ]]
    out.append(json_ld(item, image))
    return "\n".join(out)


def json_ld(item, image):
    """The graph: Organization, WebSite, the type's node (a WebPage when
    the type gives none), BreadcrumbList."""
    meta, path = item["meta"], item["path"]
    a, lang = apex(), CFG["site"]["lang"]
    url = a + clean_url(path)
    org = {"@type": "Organization", "@id": org_ref()["@id"],
           "name": CFG["seo"]["organization"], "url": f"{a}/",
           "logo": f"{a}/{CFG['share']['logo']}"}
    site = {"@type": "WebSite", "@id": site_ref()["@id"], "name": CFG["site"]["name"],
            "url": f"{a}/", "inLanguage": lang, "publisher": org_ref()}
    node = item["type"].json_ld(item, item["conf"]) or {
        "@type": "WebPage", "name": page_title(meta),
        "description": meta["description"], "isPartOf": site_ref()}
    node.update({"@id": f"{url}#page", "url": url, "inLanguage": lang})
    graph = [org, site, node]
    crumbs = breadcrumbs(meta, path)
    if len(crumbs) > 1:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": n, "name": name, "item": link}
            for n, (name, link) in enumerate(crumbs, 1)]})
    data = json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, separators=(",", ":"))
    # "</" would close the element early; JSON allows "<\/" for it.
    data = data.replace("</", "<\\/")
    return f'<script type="application/ld+json">{data}</script>'
```

`sitemap_xml` and `check` take items:

```python
def sitemap_xml(items):
    """lastmod: `updated:`, else an item's date, else [site] updated."""
    rows = []
    for it in sorted(items, key=lambda it: clean_url(it["path"])):
        lastmod = it["meta"].get("updated") or it["date"] or CFG["site"]["updated"]
        rows.append(f"\t<url>\n\t\t<loc>{H.escape(apex() + clean_url(it['path']))}</loc>\n"
                    f"\t\t<lastmod>{lastmod}</lastmod>\n\t</url>\n")
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(rows) + "</urlset>\n")


def check(items):
    """Warn, without failing the build, about what search engines penalise
    or truncate: titles past 60 characters, descriptions outside 50-160,
    duplicates. The 404 and pages marked noindex are skipped."""
    limits = CFG["seo"]
    seen_t, seen_d, warnings = {}, {}, []
    for it in items:
        path, meta = it["path"], it["meta"]
        if "noindex" in meta.get("robots", ""):
            continue
        title, desc = page_title(meta), meta.get("description", "")
        if len(title) > limits["title_max"]:
            warnings.append(f"{path}: title is {len(title)} characters (max {limits['title_max']})")
        if not limits["description_min"] <= len(desc) <= limits["description_max"]:
            warnings.append(f"{path}: description is {len(desc)} characters "
                            f"({limits['description_min']}-{limits['description_max']})")
        for value, seen, what in ((title, seen_t, "title"), (desc, seen_d, "description")):
            if value in seen:
                warnings.append(f"{path}: same {what} as {seen[value]}")
            seen.setdefault(value, path)
    for w in warnings:
        print(f"seo: {w}", file=sys.stderr)
    return warnings
```

- [ ] **Step 4: Make `page.py` take the item**

`render_html(item, sections, preamble=(), colls=None)`: at the top, `meta, path, module = item["meta"], item["path"], item["type"]`; `head_tags(item)`; and the body wrapper:

```python
        "body": ("<article>\n" + "\n".join(body) + "</article>\n"
                 if module.ARTICLE else "\n".join(body)),
```

- [ ] **Step 5: Update `build.py`**

`out[it["path"]] = render_html(it, sections, preamble, colls)`; `indexed = [it for it in pages if "noindex" not in it["meta"].get("robots", "")]`; `sitemap_xml(indexed)`; `sitemap.txt` from `clean_url(it["path"])`; `check(pages)`; drop `meta_pages`. In `_compat`, remove the `_kind` and `_date` lines (keep `it["iso"]` for Task 8).

- [ ] **Step 6: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
grep -rn "_kind\|_date\b" src/ types/ ; echo "(expected: nothing)"
```

Expected: PASS; `IDENTICAL`; no `_kind`/`_date` left.

- [ ] **Step 7: Commit**

```bash
git add src/seo.py src/page.py src/build.py tests/test_seo.py
git commit -m "refactor: structured data and head tags come from the item's type"
```

---

### Task 8: One RSS feed function; the calendar is the event type's

**Files:**
- Modify: `src/feeds.py` (`feed(items, conf)` replaces `posts_feed` and `events_feed`; `calendar` reads `e["date"]`)
- Modify: `src/build.py` (generic feed and `outputs` loop; `_compat` removed)
- Test: `tests/test_feeds.py`

**Interfaces:**
- Produces: `feeds.feed(items, conf) -> str` (RSS, newest first, from each item's `type.feed_item`; items whose `feed_item` returns `None` are left out); `feeds.calendar(events) -> str` unchanged but on `e["date"]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_feeds.py`:

```python
import unittest

from tests.helpers import build_site


class Feeds(unittest.TestCase):
    def test_rss_per_collection_with_feed(self):
        out = build_site()
        self.assertIn("<title>Hello</title>", out["blog/feed.xml"])
        self.assertIn("<link>https://test.example/blog/2026-01-01-hello</link>", out["blog/feed.xml"])
        self.assertIn("<title>Future meetup</title>", out["events.xml"])
        self.assertLess(out["events.xml"].index("Future meetup"), out["events.xml"].index("Past meetup"))
        self.assertNotIn("news.xml", out)
        self.assertFalse([k for k in out if "members" in k and k.endswith(".xml")])

    def test_calendar_from_the_event_type(self):
        out = build_site()
        ics = out["events.ics"]
        self.assertIn("UID:2099-01-01-future-meetup@example.org", ics)
        self.assertIn("DTSTART;VALUE=DATE:20990101", ics)
        self.assertIn("DTEND;VALUE=DATE:20990103", ics)   # end 2099-01-02, exclusive
        self.assertIn("GEO:45.75;4.85", ics)
        self.assertIn("LOCATION:Library\\, Springfield", ics)
```

- [ ] **Step 2: Run them**

Run: `python3 -m unittest tests.test_feeds -v`
Expected: PASS (guarding tests). Continue.

- [ ] **Step 3: Rewrite `feeds.py`'s RSS**

Replace `events_feed` and `posts_feed` with:

```python
def feed(items, conf):
    """A collection's RSS: every item its type puts in a feed, newest first."""
    rows = ""
    for it in reversed(items):
        f = it["type"].feed_item(it, conf)
        if f is None:
            continue
        rows += f"""
	<item>
		<title>{H.escape(f['title'])}</title>
		<link>{f['link']}</link>
		<guid isPermaLink="true">{f['link']}</guid>
		<pubDate>{rfc822(f['date'])}</pubDate>
		<description>{H.escape(f['description'])}</description>
	</item>
"""
    a = apex()
    return rss(conf["feed_title"], f"{a}/{conf['nav']}", f"{a}/{conf['feed']}",
               conf["feed_description"], rows)
```

Update the module docstring: `"""RSS for any collection whose type gives feed items; iCalendar, used by the event type."""`. In `calendar()`, `day = datetime.date.fromisoformat(e["date"])` (drop the `iso` fallback of Task 4).

- [ ] **Step 4: Update `build.py`**

Imports: `from feeds import feed`. The feed loop:

```python
    # Feeds and the types' own files (an iCalendar), for the collections
    # whose folder exists.
    for name, conf in colls.items():
        if not (CONTENT / conf["dir"]).is_dir():
            continue
        module = contenttypes.TYPES[conf["type"]]
        if conf.get("feed") and module.HAS_FEED:
            out[conf["feed"]] = feed(items[name], conf)
        out.update(module.outputs(items[name], conf))
```

Delete `_compat` and its call.

- [ ] **Step 5: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
grep -rn '"iso"\|\[.iso.\]' src/ types/; echo "(expected: nothing)"
```

Expected: PASS; `IDENTICAL`; no `iso` left.

- [ ] **Step 6: Commit**

```bash
git add src/feeds.py src/build.py tests/test_feeds.py
git commit -m "refactor: one RSS feed from the types' items; the calendar is the event type's"
```

---

### Task 9: Scripts and list data from the sections

**Files:**
- Modify: `src/page.py:262-275` (scripts) and `:281-290` (section `data-*`)
- Test: `tests/test_scripts.py`

**Interfaces:**
- Consumes: `s["script"]` and `s["data"]` set by `contenttypes.fill_lists` (Task 6).

- [ ] **Step 1: Write the failing test**

`tests/test_scripts.py`:

```python
import pathlib
import unittest

from config import THEME
from tests.helpers import rebuild


class Scripts(unittest.TestCase):
    def test_type_script_only_where_it_lists_and_only_if_shipped(self):
        js = THEME / "members.js"
        js.write_text("/* fixture */\n")
        try:
            out = rebuild()
        finally:
            js.unlink()
        self.assertIn('<script src="members.js" defer></script>', out["members.html"])
        self.assertNotIn("members.js", out["members/ada-lovelace.html"])
        self.assertNotIn("members.js", out["index.html"])
        self.assertIn("members.js", out)  # the theme file is served
        without = rebuild()
        self.assertNotIn("members.js", without["members.html"])
        self.assertNotIn("members.js", without)

    def test_code_js_is_not_a_type_script(self):
        js = THEME / "code.js"
        js.write_text("/* fixture */\n")
        try:
            out = rebuild()
        finally:
            js.unlink()
        self.assertIn('<script src="../code.js" defer data-copy="copy" data-copied="copied"></script>',
                      out["blog/2026-01-01-hello.html"])
        self.assertNotIn("code.js", out["members.html"])
```

- [ ] **Step 2: Run it**

Run: `python3 -m unittest tests.test_scripts -v`
Expected: PASS on today's hard-coded `members.js` rule. Continue: the change is to stop `page.py` knowing the name.

- [ ] **Step 3: Rewrite the script and data lines of `render_html`**

Replace the block from `script = ""` to the `code.js` `if` with:

```python
    # Scripts, each loaded where it serves and only if the theme ships the
    # file: the ones the listed types name, then code.js on pages with
    # code. The page is complete without them (AGENTS.md §6).
    named = []
    for s in sections:
        sc = s.get("script")
        if sc and sc not in named and theme_file(sc).is_file():
            named.append(sc)
    script = "".join(f'<script src="{res(sc)}" defer></script>\n' for sc in named)
    if has_code(list(preamble) + sections) and theme_file("code.js").is_file():
        labels = CFG["labels"]
        script += (f'<script src="{res("code.js")}" defer'
                   f' data-copy="{H.escape(labels["copy"])}"'
                   f' data-copied="{H.escape(labels["copied"])}"></script>\n')
```

And the section loop's `data`:

```python
        data = "".join(f' data-{k}="{H.escape(str(v))}"' for k, v in s.get("data", {}).items())
```

Remove the `if "members" in s["cls"]:` block and the `m = CFG["members"]` line. `grep -n "members" src/page.py` must find nothing.

- [ ] **Step 4: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 5: Commit**

```bash
git add src/page.py tests/test_scripts.py
git commit -m "refactor: a type names its script; the page knows none"
```

---

### Task 10: Layouts per type

**Files:**
- Modify: `src/config.py` (`layout(name=None, asked_by=None) -> (path, text)`, `UNSERVED`, `UNSERVED_DIRS`; drop `TEMPLATES`)
- Modify: `src/page.py` (layout choice, `{{ type }}`, `fill(..., path)` error)
- Modify: `src/build.py` (theme copy loop uses `UNSERVED`/`UNSERVED_DIRS`; imports)
- Create: `tests/site/theme/layouts/event.html`
- Test: `tests/test_layouts.py`

**Interfaces:**
- Produces: `config.layout(name=None, asked_by=None) -> tuple[Path, str]`: `theme/layouts/<name>.html` if it exists (through `theme_file`, so `assets/` wins); else, when `asked_by` (a content path) is given, raise `BuildError`; else `layout.html`. `config.UNSERVED = ("layout.html", "share.svg", "theme.toml")`, `config.UNSERVED_DIRS = ("icons/", "layouts/", "types/")`.

- [ ] **Step 1: Write the fixture layout and the failing tests**

`tests/site/theme/layouts/event.html`: copy `tests/site/theme/layout.html` and change the `<body>` line to `<body class="layout-event {{ type }}">`.

`tests/test_layouts.py`:

```python
import unittest

import report
from config import CONTENT, layout
from tests.helpers import build_site


class Layouts(unittest.TestCase):
    def test_type_layout_when_the_theme_has_it(self):
        out = build_site()
        self.assertIn('<body class="layout-event event">', out["events/2099-01-01-future-meetup.html"])
        self.assertIn("<body>", out["blog/2026-01-01-hello.html"])          # post: no layouts/post.html, falls back
        self.assertIn("<body>", out["members/ada-lovelace.html"])
        self.assertNotIn("layouts/event.html", out)                          # never served

    def test_front_matter_layout_wins(self):
        # The event layout, asked for by a plain page.
        page = CONTENT / "special.md"
        page.write_text("---\nman: TEST(1)\ntitle: special\ndescription: A page that asks for the event layout.\n"
                        "tagline: t\nnav: -\nlayout: event\n---\n\n## Name\n\nspecial {mono}\n")
        try:
            from tests.helpers import rebuild
            out = rebuild()
        finally:
            page.unlink()
        self.assertIn('<body class="layout-event page">', out["special.html"])

    def test_unknown_layout_asked_for_is_an_error(self):
        with self.assertRaises(report.BuildError) as cm:
            layout("nope", asked_by=CONTENT / "x.md")
        self.assertEqual(str(cm.exception),
                         'content/x.md: layout "nope" names no theme/layouts/nope.html. '
                         "Add that file to the theme, or drop `layout:`")

    def test_unknown_type_layout_falls_back_silently(self):
        path, text = layout("nope")
        self.assertEqual(path.name, "layout.html")

    def test_unknown_placeholder_names_the_layout_file(self):
        import page
        with self.assertRaises(report.BuildError) as cm:
            page.fill("<p>{{ nothing.here }}</p>", {}, {}, CONTENT.parent / "theme" / "layout.html")
        self.assertIn("theme/layout.html: unknown placeholder {{ nothing.here }}", str(cm.exception))
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest tests.test_layouts -v`
Expected: FAIL (`layout()` takes no arguments; `<body>` in the event page).

- [ ] **Step 3: Change `config.py`**

Replace `TEMPLATES` and `layout()`:

```python
# Files of the theme (and of assets/, which may override them) read by the
# build and never served.
UNSERVED = ("layout.html", "share.svg", "theme.toml")
UNSERVED_DIRS = ("icons/", "layouts/", "types/")


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
```

- [ ] **Step 4: Change `page.py`**

`fill(template, computed, meta, path)`: the unknown-placeholder branch raises `error(path, f"unknown placeholder {{{{ {name} }}}}", "The placeholders are listed in docs/theme.md")` (import `from report import error`; the `{{{{` doubles print as `{{`). At the end of `render_html`:

```python
    if meta.get("layout"):
        lay_path, template = layout(meta["layout"], asked_by=item["src"])
    else:
        lay_path, template = layout(module.LAYOUT)
    return fill(template, {
        "title": H.escape(page_title(meta)),
        "type": module.NAME,
        ...  # the other computed values unchanged
    }, meta, lay_path)
```

- [ ] **Step 5: Change the copy loop in `build.py`**

```python
    for base in (THEME, ASSETS):
        for f in sorted(base.rglob("*")) if base.is_dir() else []:
            rel = str(f.relative_to(base))
            if f.is_file() and served(rel):
                out[rel] = f.read_bytes()
```

Import `served` from `config`; remove `TEMPLATES` from the import list.

- [ ] **Step 6: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL` (the reference theme has no `layouts/`).

- [ ] **Step 7: Commit**

```bash
git add src/config.py src/page.py src/build.py tests/site/theme/layouts tests/test_layouts.py
git commit -m "feat: a layout per type, theme/layouts/<name>.html, and layout: in front matter"
```

---

### Task 11: `theme/theme.toml`

**Files:**
- Modify: `src/config.py` (`THEME_TOML`, `load_config`)
- Create: `tests/site/theme/theme.toml`
- Test: `tests/test_theme_toml.py`

- [ ] **Step 1: Write the fixture and the failing test**

`tests/site/theme/theme.toml`:

```toml
# What is the theme's, not the site's: its colours. The site's site.toml
# wins on every key it sets.

[share]
theme_color = "#123456"
background_color = "#000000"   # the fixture site overrides this one
```

`tests/test_theme_toml.py`:

```python
import unittest

from tests.helpers import build_site


class ThemeToml(unittest.TestCase):
    def test_theme_values_reach_the_page_and_the_site_wins(self):
        out = build_site()
        self.assertIn('<meta name="theme-color" content="#123456">', out["index.html"])
        self.assertIn('"theme_color": "#123456"', out["site.webmanifest"])
        self.assertIn('"background_color": "#ABCDEF"', out["site.webmanifest"])   # site.toml over theme.toml
        self.assertNotIn("theme.toml", out)                                         # never served
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest tests.test_theme_toml -v`
Expected: FAIL on `#123456`.

- [ ] **Step 3: Add the layer**

In `src/config.py`: `THEME_TOML = THEME / "theme.toml"` after `THEME`, and:

```python
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
```

Update the `CFG` comment above it: "content/site.toml over theme/theme.toml over builder/defaults.toml".

- [ ] **Step 4: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/site/theme/theme.toml tests/test_theme_toml.py
git commit -m "feat: theme/theme.toml, a configuration layer between the defaults and the site"
```

---

### Task 12: Watch mode knows `theme/types/`; `--version`

**Files:**
- Modify: `src/watch.py` (`restarts(moved) -> bool`, messages)
- Modify: `src/build.py` (`main`: use `watch.restarts`; `--version`)
- Test: `tests/test_watch.py`

**Interfaces:**
- Produces: `watch.restarts(moved: set[str]) -> bool` - True when a moved path is under `BUILDER` or `THEME / "types"`. `build.py --version` prints `TILDER_VERSION` from the environment, else `dev`.

- [ ] **Step 1: Write the failing test**

`tests/test_watch.py`:

```python
import os
import subprocess
import sys
import unittest

import watch
from config import BUILDER, CONTENT, THEME


class Watch(unittest.TestCase):
    def test_restart_predicate(self):
        self.assertTrue(watch.restarts({str(BUILDER / "src" / "page.py")}))
        self.assertTrue(watch.restarts({str(THEME / "types" / "talk.py")}))
        self.assertFalse(watch.restarts({str(THEME / "style.css"), str(CONTENT / "index.md")}))

    def test_version_flag(self):
        entry = str(BUILDER / "build.py")
        env = {**os.environ, "TILDER_VERSION": "v1.2.3"}
        self.assertEqual(subprocess.run([sys.executable, entry, "--version"], capture_output=True,
                                        text=True, env=env).stdout.strip(), "v1.2.3")
        env.pop("TILDER_VERSION")
        self.assertEqual(subprocess.run([sys.executable, entry, "--version"], capture_output=True,
                                        text=True, env=env).stdout.strip(), "dev")
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest tests.test_watch -v`
Expected: FAIL, `module 'watch' has no attribute 'restarts'`.

- [ ] **Step 3: Change `watch.py`**

```python
CODE = (str(BUILDER), str(THEME / "types"))


def restarts(moved):
    """Did the code itself change - the generator, or a theme type? The
    process still runs the old code: it must restart to load the new."""
    return any(k.startswith(CODE) for k in moved)
```

In `watch()`, replace `code = str(BUILDER)` and `if any(k.startswith(code) for k in moved):` with `if restarts(moved):`, and the message with `print("builder/ or theme/types/ changed, restarting", flush=True)`.

- [ ] **Step 4: Change `build.py`'s `main()`**

```python
    if "--version" in args:
        print(os.environ.get("TILDER_VERSION", "dev"))
        return 0
```

before `report.DEBUG = ...`; and in the first-build loop, `own_code = lambda: {k: v for k, v in snapshot().items() if k.startswith(watch_module.CODE)}` with `import watch as watch_module` (the function `watch` is already imported by name), the waiting message `"(a change in builder/ or theme/types/ restarts)"`, and the restart message `"builder/ or theme/types/ changed, restarting"`. Add `--version` to the docstring usage.

- [ ] **Step 5: Run the tests and diff**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: PASS; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add src/watch.py src/build.py tests/test_watch.py
git commit -m "feat: watch restarts on theme/types/ changes; --version"
```

---

### Task 13: A theme type, end to end

The acceptance test of the whole design: a `talk` type in the fixture theme, an event with a speaker, that lists, renders in HTML and text, feeds and validates like a built-in one. It stays as the example `docs/types.md` points to.

**Files:**
- Create: `tests/site/theme/types/talk.py`, `tests/site/content/talks.md`, `tests/site/content/talks/2099-03-01-first-talk.md`
- Modify: `tests/site/content/site.toml` (`[collections.talks]`), `tests/test_collections.py` (summary and order assertions)
- Test: `tests/test_theme_type.py`

- [ ] **Step 1: Write the type, the content and the failing tests**

`tests/site/theme/types/talk.py`:

```python
"""A talk: an event with a speaker. A theme type, built on the built-in
event type, which is loaded first and reachable through contenttypes.TYPES."""

from contenttypes import TYPES

event = TYPES["event"]

NAME = "talk"
DATED = True
ARTICLE = True
DEFAULTS = {**event.DEFAULTS, "man": "SITE-TALKS(7)", "nav": "talks",
            "speaker_label": "speaker", "feed_title": "talks", "feed_description": "Talks."}
MARKERS = {"talks": event.MARKERS["upcoming"]}   # {talks}: upcoming talks, nearest first

defaults = event.defaults
json_ld = event.json_ld
feed_item = event.feed_item
outputs = event.outputs


def entry(item, link, conf):
    """The event card, with the speaker after the date."""
    node = event.entry(item, link, conf)
    if item["meta"].get("speaker"):
        node["meta"].insert(1, f"{conf['speaker_label']}: {item['meta']['speaker']}")
    return node
```

`tests/site/content/talks.md`:

```markdown
---
man: SITE-TALKS(7)
title: talks
description: Talks of the fixture site, given by their speakers, with a feed.
tagline: talks
nav: talks
feed: talks
---

## Name

talks - who speaks, when {mono}

## Upcoming {talks}
```

`tests/site/content/talks/2099-03-01-first-talk.md`:

```markdown
---
title: First talk
description: The first talk of the fixture site, to test a type the theme adds.
place: Auditorium, Springfield
speaker: Grace Hopper
---

## Name

first-talk - a talk {mono}

## Abstract

Compilers.
```

Add to `tests/site/content/site.toml`:

```toml
[collections.talks]
type = "talk"
feed = "talks.xml"
```

`tests/test_theme_type.py`:

```python
import json
import re
import unittest

import contenttypes
from config import load_config
from tests.helpers import build_site


class ThemeType(unittest.TestCase):
    def test_loaded_from_the_theme(self):
        load_config()
        types = contenttypes.load()
        self.assertEqual(list(types), ["event", "member", "page", "post", "talk"])
        self.assertEqual(types["talk"].PATH.parent.name, "types")
        self.assertEqual(contenttypes.MARKERS["talks"], "talk")

    def test_lists_renders_twice_feeds_and_validates(self):
        out = build_site()
        page = out["talks.html"]
        self.assertIn('class="entry entry--next entry--link"', page)
        self.assertIn("<span>speaker: Grace Hopper</span>", page)
        self.assertIn("speaker: Grace Hopper", out["txt/talks.txt"])
        own = out["talks/2099-03-01-first-talk.html"]
        self.assertIn("<article>", own)
        self.assertIn("speaker: Grace Hopper", own)
        self.assertIn("<title>First talk</title>", out["talks.xml"])
        data = re.search(r'<script type="application/ld\+json">(.*?)</script>', own, re.S).group(1)
        self.assertIn("Event", {n["@type"] for n in json.loads(data)["@graph"]})
        self.assertIn("SITE-TALKS(7)", out["txt/talks/2099-03-01-first-talk.txt"])
        self.assertNotIn("types/talk.py", out)                     # never served

    def test_summary_names_the_theme_type(self):
        load_config()
        contenttypes.load()
        colls = contenttypes.collections()
        items = {n: contenttypes.load_items(n, c) for n, c in colls.items()}
        self.assertTrue(contenttypes.summary(colls, items).startswith(
            "types: event, member, page, post; from theme: talk\n"))
```

Types are listed everywhere in load order: file names sorted within a folder, folders in load order. Update `tests/test_collections.py`: `test_declared_collections_merge_type_defaults` now expects `["blog", "events", "members", "news", "talks"]`; `test_summary` expects `"types: event, member, page, post; from theme: talk\n"` and `..., news (post, no folder), talks (talk, 1 item)`.

- [ ] **Step 2: Run the tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: all PASS, with no code change - this is the point. If something fails, it is a defect in Tasks 3-12: fix it there (with its own test) before going on.

- [ ] **Step 3: Diff the reference site**

```bash
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

Expected: `IDENTICAL`.

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: a theme type, end to end"
```

---

### Task 14: Documentation

**Files:**
- Create: `docs/types.md`
- Modify: `docs/theme.md`, `docs/markdown.md:500-580`, `README.md`, `AGENTS.md`, `src/build.py` (docstring)

- [ ] **Step 1: Write `docs/types.md`**

```markdown
# Content types

A **type** says what a kind of content is: its fields, its card in a list,
its page, its structured data, its feed item, its layout. tilder ships four
- `page`, `post`, `event`, `member` - and a theme adds its own in
`theme/types/`, written exactly the same way. A theme module with the same
`NAME` as a built-in type replaces it.

A type produces **nodes** of the page tree, never HTML: the builder renders
the nodes twice, HTML and text, so a type is exact in the text mirror
without doing anything for it.

---

## A collection binds content to a type

```toml
[collections.talks]      # content/talks/, listed by {talks}
type = "talk"
feed = "talks.xml"
speaker_label = "speaker"
```

An item is `<slug>.md` or `<slug>/index.md` in the folder (a folder, to keep
images or files next to the page). For a `DATED` type the slug starts with
`YYYY-MM-DD-`. Names starting with `_` are templates and skipped. A `.md`
outside every collection is a `page`. The keys a collection may set are
the type's `DEFAULTS`, plus `dir` (default: the collection's name).

---

## The module

`theme/types/talk.py`, complete - a talk is an event with a speaker:

```python
from contenttypes import TYPES

event = TYPES["event"]           # built-in types load first

NAME = "talk"
DATED = True
ARTICLE = True
DEFAULTS = {**event.DEFAULTS, "man": "SITE-TALKS(7)", "nav": "talks",
            "speaker_label": "speaker"}
MARKERS = {"talks": event.MARKERS["upcoming"]}

defaults = event.defaults
json_ld = event.json_ld
feed_item = event.feed_item
outputs = event.outputs

def entry(item, link, conf):
    node = event.entry(item, link, conf)
    if item["meta"].get("speaker"):
        node["meta"].insert(1, f"{conf['speaker_label']}: {item['meta']['speaker']}")
    return node
```

### Attributes

| Name | Default | |
|---|---|---|
| `NAME` | required | the value of `type =` in `[collections.*]`; a valid identifier |
| `DATED` | `False` | items are `YYYY-MM-DD-slug`; `item["date"]` is set |
| `ARTICLE` | `False` | the page body is wrapped in `<article>` |
| `OG_TYPE` | `"website"` | Open Graph `og:type` (`"article"` for posts) |
| `LAYOUT` | `NAME` | `theme/layouts/<LAYOUT>.html`, if the theme has it, else `layout.html` |
| `SCRIPT` | `""` | a theme script loaded on pages that list the type, if the theme ships it |
| `DEFAULTS` | `{}` | the type's words and settings, English and neutral; a collection overrides them |
| `MARKERS` | `{}` | `{"word": function}`: section markers that list the type's items |

### Functions

Only `entry` is required. `item` is the dict below; `conf` the collection's
settings (`DEFAULTS` under `[collections.<name>]`).

```python
def defaults(item, conf): ...      # fill what the front matter may leave out
def sort_key(item, conf): ...      # order in lists and feeds; default: the slug
def entry(item, link, conf): ...   # the card (an entry node), or None for no card
def json_ld(item, conf): ...       # the schema.org node (dict), or None -> WebPage
def meta_tags(item, conf): ...     # [("name" | "property", key, value)]
def feed_item(item, conf): ...     # {"title", "link", "description", "date"}, or None
def outputs(items, conf): ...      # {"path": text} files of the collection (an iCalendar)
def list_data(conf): ...           # data-* on a section that lists the type
```

A marker function takes `(items, conf)` and returns:

```python
{"items": [(item, ["next"]), (item, [])],   # in order, with extra card classes
 "empty": conf.get("none_upcoming", ""),    # shown when there is nothing
 "cls": ["grid"]}                            # optional: classes for the section body
```

`{word}` lists the page's own collection of the type, else the first one;
`{word:name}` names one.

### The item

```python
{"slug": "2099-03-01-first-talk", "date": "2099-03-01",   # date: None unless DATED
 "meta": {...},                    # the front matter, after defaults()
 "src": Path("content/talks/2099-03-01-first-talk.md"),
 "path": "talks/2099-03-01-first-talk.html",
 "collection": "talks", "conf": {...}, "type": <the module>}
```

### The entry node

What `entry` returns; `page.py` and `text.py` render it:

```python
{"k": "entry", "id": None,
 "title": "[First talk](talks/2099-03-01-first-talk)",  # a link in a list; the bare title on its own page
 "meta": ["2099-03-01 | Sunday 1 March 2099", "Auditorium", "`upcoming`"],
      # "iso | words" becomes <time>; `word` becomes a tag
 "cls": ["link"],                  # entry--link: the card is clickable as a whole
 "blocks": [{"k": "para", "text": "...", "cls": []}],   # any block kind of docs/markdown.md
 "own": False,                     # True on the item's own page: no <h3>, the <h1> is the title
 "data": {"category": "admin"}}    # optional data-* attributes
```

Blocks a type may use: `para` (with an optional `"txt"`, the text mirror's
wording), `empty`, `list`, `code`, `table`, `image`, `profiles`
(`{"k": "profiles", "items": [(key, label, url)]}`). A new kind of block is
a Markdown construct: it is added to the builder with both renderings.

### What a type may import

`config` (`CFG`, `STATE["today"]`, `apex`), `dates.human_date`,
`paths.clean_url`, `fold.to_ascii`, `seo` (`page_heading`, `page_title`,
`share_image`, `org_ref`, `site_ref`), `feeds.calendar`, and the built-in
types through `contenttypes.TYPES`. Nothing else is promised to stay.

---

## Checks and errors

At load, the builder checks each module (`NAME`, `entry`, the attributes'
kinds, marker words claimed once) and each collection (`type` names a loaded
type, folders do not overlap), and reports **every** problem before it
stops:

```
error: theme/types/talk.py: MARKERS["upcoming"] is already claimed by type "event" (types/event.py). Rename the marker, or replace that type by naming yours "event"
error: content/site.toml: collection "talks" has type "tlak", which no type defines. Types loaded: event, member, page, post (types/), talk (theme/types/talk.py)
```

`--debug` adds the Python traceback of an import failure. In `--watch`, a
change under `theme/types/` restarts the process, as a change in the
generator does.

A theme runs code at build time. The theme, like the generator, is the
site owner's: review one before you use it.
```

- [ ] **Step 2: Update `docs/theme.md`**

In the files table, add rows:

```
| `layouts/<name>.html` | optional | a layout for the pages of a type (`docs/types.md`), or asked for by `layout:` in a page's front matter; same placeholders as `layout.html` |
| `types/<name>.py` | optional | a content type the theme adds, or a built-in one it replaces (`docs/types.md`) |
| `theme.toml` | optional | the theme's own configuration values, merged under the site's `site.toml`: for now the `[share]` colours |
```

Change "Everything in `theme/` but `layout.html`, `share.svg` and `icons/` is copied to the site as it is." to "... but `layout.html`, `layouts/`, `share.svg`, `icons/`, `types/` and `theme.toml` is copied ...". In the placeholders table, add `| `{{ type }}` | the page's type: `page`, `post`, `event`, `member`, or a theme's |`. After the placeholders section, add:

```markdown
## Layouts

The layout of a page is, in order: `layout:` in its front matter (the file
must exist), the type's `LAYOUT` (`theme/layouts/event.html` for events, if
the theme has it), else `layout.html`.

## Trust

A theme's `types/` are Python, run at build time. The theme, like the
generator, is the site owner's: review one before you use it.
```

- [ ] **Step 3: Update `docs/markdown.md`, the collections section**

Rewrite the section from `## Collections: posts and events` to the end of the marker table:

- Title: `## Collections`.
- First paragraph: "A **collection** is a folder whose files are items of one **type**; the types are `post`, `event`, `member`, and whatever the theme adds (`docs/types.md`). An item is `<slug>.md` or `<slug>/index.md` (a folder, to keep images next to it); for posts and events the slug starts with the date, `YYYY-MM-DD-slug`."
- The type table: rows `post`, `event`, add `| `member` | people | category order, then last name | - | `ProfilePage` |`.
- The TOML example: `type = "post"`, `type = "event"`; add `[collections.members]` with `type = "member"` and `categories = ["admin", "member"]`.
- Replace the `[collection_defaults.*]` paragraph with: "Every key a type needs has a default in its module, `types/<type>.py` (`DEFAULTS`, listed in `docs/types.md`): man-page name, nav, empty-list texts, tags, link labels, feed titles, member words. A collection sets only what differs. `defaults.toml` declares `blog`, `events` and `members`; each stays inactive - no page, no feed - until its folder exists."
- Add a `Members` column to the fields table? No: point to the `Members` section that already documents the member fields, and in that section replace any mention of the `[members]` table with `[collections.members]`.
- The markers table: add `| `{members}` | every member, a grid, category order then last name |`; keep the sentence on bare and named markers.

Also `nav` in the front-matter table (line 134): unchanged.

- [ ] **Step 4: Update `README.md`**

- Title: `# tilder - a man-page site builder`, first sentence: "**tilder** is a static site generator for websites that read like a man page." Keep the rest of the intro.
- In "What it gives you", the collections bullet: "Collections of content, declared in `site.toml`, each of a **type** - posts, events, members, or a type your theme adds in ten lines of Python (`docs/types.md`) - with their lists, RSS feeds and iCalendar feeds."
- In "Layout of a project", under `theme/`: `layouts/, types/, theme.toml (docs/theme.md)`.
- After "Configuration": "Three layers: `builder/defaults.toml`, then the theme's `theme.toml` if it has one, then `content/site.toml`. A type's own words default from its module."
- In the Docker paragraph, add: "The image is also published by CI at `ghcr.io/thosted/tilder` (`latest`, and one tag per release): with it a site needs no submodule - see `examples/compose.yaml`." (Task 15 makes this true; write it here, in one pass.)
- Under "The code": "`tests/`: `python3 -m unittest discover -s tests` builds a fixture site and checks it."
- The RSS `<generator>` string stays `builder/build.py`: renaming outputs is not this work's.

- [ ] **Step 5: Update `AGENTS.md`**

- §2.1: after "A new key goes in `defaults.toml` with an English, neutral default and a comment.", add "A key that belongs to one content type goes in that type's `DEFAULTS` (`types/<type>.py`), English and neutral too."
- §3 layout: add `types/` ("the built-in content types, one module each - no `__init__.py`, ever: the folder must not become a package"), `tests/`; in `src/`: replace `members.py` and `dated.py` lines with `contenttypes.py`, `report.py`, `dates.py` and their one-line roles.
- §6: "The builder knows `code.js`, and whatever script a loaded type names (`SCRIPT`, `docs/types.md`): `members.js` for the member type. Each tag is added only where it serves and only if the theme ships the file."
- §9: add step 0: `python3 -m unittest discover -s tests` must be green.
- §10: add "Add a content type without its entry in `docs/types.md`, its `DEFAULTS`, and a test of its card in HTML and text." and "Put an `__init__.py` in `types/`."
- Add a short §"Errors": "When the build stops, one line per problem: `error: <file>[:<line>]: <what is wrong>. <what to do>` (`src/report.py`). Gather the problems of a phase and report them together. Tracebacks only under `--debug`."

- [ ] **Step 6: Finish the module map in `src/build.py`'s docstring**, then run the checks

```bash
python3 -m unittest discover -s tests -v
NAME="$(python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["site"]["name"])' "$SITE/content/site.toml")"
grep -rniE "$NAME|$(basename "$SITE")" --exclude-dir=.git .; echo "(expected: nothing)"
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

The image name carries the GitHub organisation, which is not a site's name.

- [ ] **Step 7: Commit**

```bash
git add docs/types.md docs/theme.md docs/markdown.md README.md AGENTS.md src/build.py
git commit -m "docs: content types, layouts, theme.toml; the name tilder"
```

---

### Task 15: The runtime image and its CI

**Files:**
- Modify: `Dockerfile`
- Create: `.dockerignore`, `.github/workflows/image.yml`
- Modify: `examples/compose.yaml`

- [ ] **Step 1: Write the `Dockerfile`**

```dockerfile
# tilder's image: Python, an SVG renderer that uses the theme's fonts for
# the icons and the share preview (woff2_decompress: the renderer shapes
# text with HarfBuzz, which reads TTF, not WOFF2), and the generator itself
# at this version, under /tilder. Everything else is the standard library.
#
#   docker run --rm -v "$PWD:/site" -v "$PWD/public:/out" ghcr.io/thosted/tilder \
#     python3 -B /tilder/build.py --root /site --out /out
FROM python:3-alpine
RUN apk add --no-cache rsvg-convert fontconfig woff2
ARG VERSION=dev
ENV TILDER_VERSION=$VERSION
COPY build.py defaults.toml /tilder/
COPY src/ /tilder/src/
COPY types/ /tilder/types/
WORKDIR /site
CMD ["python3", "-B", "/tilder/build.py", "--root", "/site", "--out", "/out", "--watch"]
```

`.dockerignore`:

```
.git
.github
docs
tests
starter
examples
**/__pycache__
```

- [ ] **Step 2: Write the workflow**

`.github/workflows/image.yml`:

```yaml
# Build the runtime image and push it to GitHub's registry: `latest` from
# main, and the version tags from every v* tag (v1.2.3 -> 1.2.3, 1.2, 1).
name: image

on:
  push:
    branches: [main]
    tags: ["v*"]

permissions:
  contents: read
  packages: write

jobs:
  image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/thosted/tilder
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          build-args: VERSION=${{ github.ref_name }}
```

- [ ] **Step 3: Show both ways in `examples/compose.yaml`**

Replace the `build:` service with two commented alternatives, the image first:

```yaml
services:
  build:
    # The published image holds the generator: no submodule needed. Pin a
    # major (`:1`) or a version (`:1.2.3`).
    image: ghcr.io/thosted/tilder:1
    volumes:
      - ./content:/site/content:ro
      - ./theme:/site/theme:ro
      - ./assets:/site/assets:ro
      - site:/out
    # With the generator as a submodule in ./builder instead, build the
    # image locally and mount the code:
    #   build: ./builder
    #   command: ["python3", "-B", "/site/builder/build.py", "--root", "/site", "--out", "/out", "--watch"]
    #   volumes: the four above, plus ./builder:/site/builder:ro
    healthcheck:
      test: ["CMD", "test", "-f", "/out/index.html"]
      interval: 30s
      start_period: 30s
      start_interval: 1s
```

`web`'s volume becomes `site:/srv:ro` as before (the named volume is the same).

- [ ] **Step 4: Try the image locally, if Docker is available**

```bash
docker build -t tilder:test --build-arg VERSION=test . && docker run --rm tilder:test python3 -B /tilder/build.py --version
SITE="$(cd .. && pwd)"; rm -rf /tmp/tilder-img && mkdir /tmp/tilder-img
docker run --rm -e BUILD_TODAY=2026-09-26 -v "$SITE:/site:ro" -v /tmp/tilder-img:/out tilder:test \
  python3 -B /tilder/build.py --root /site --out /out
diff -r /tmp/tilder-before /tmp/tilder-img
```

Expected: `test`; a full build; the diff shows at most the PNG icons and `share.png` (a different `rsvg-convert` version), nothing textual. Without Docker, note it in the commit and rely on the reference-site checks of the next task.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile .dockerignore .github/workflows/image.yml examples/compose.yaml
git commit -m "ci: build and publish the runtime image, with the generator inside"
```

---

### Task 16: Final verification

- [ ] **Step 1: The full test suite and the reference site**

```bash
python3 -m unittest discover -s tests -v
SITE="$(cd .. && pwd)"; BUILD_TODAY=2026-09-26 python3 build.py --root "$SITE" --out /tmp/tilder-after && diff -r /tmp/tilder-before /tmp/tilder-after && echo IDENTICAL
```

- [ ] **Step 2: The starter from nothing**

```bash
rm -rf /tmp/starter && cp -r starter /tmp/starter && python3 build.py --root /tmp/starter --out /tmp/starter-out
```

Expected: the two summary lines (`collections: blog (post, 1 item), events (event, no folder), members (member, no folder)`), then `built`.

- [ ] **Step 3: AGENTS.md §9 checks on the reference build**

Run every command of AGENTS.md §9 steps 3-5 in `/tmp/tilder-after`. Expected: max line 75, no escape in `txt/`, `ansi` equals stripped `txt`, one `<h1>` per page, no script but the theme's two and JSON-LD, no foreign request.

- [ ] **Step 4: Every error path, by hand**

In a scratch copy of the fixture (`cp -r tests/site /tmp/errsite`), provoke each and read the message:

| Provoke | Expect one `error:` line saying |
|---|---|
| `type = "posts"` in site.toml | types are singular. Write type = "post" |
| `type = "nope"` | which no type defines. Types loaded: ... |
| a `[members]` table | is no longer read. Move its keys under [collections.members] |
| `events/2026-13-01-x.md` | "2026-13-01" is not a date. Name the file YYYY-MM-DD-slug.md |
| `layout: nope` in a page | names no theme/layouts/nope.html. Add that file ... |
| `{{ nope }}` in layout.html | theme/layout.html: unknown placeholder {{ nope }} |
| a `theme/types/x.py` with a syntax error | cannot be imported: SyntaxError ... Run with --debug |
| two of the above at once | two lines, then exit 1 |

```bash
python3 build.py --root /tmp/errsite --out /tmp/errsite-out; echo "exit $?"
```

- [ ] **Step 5: Hand over**

Use the `superpowers:finishing-a-development-branch` skill: the branch is `feat/types`, the reference site's `content/site.toml` migration is pending in its own repository and goes with the submodule bump there.
