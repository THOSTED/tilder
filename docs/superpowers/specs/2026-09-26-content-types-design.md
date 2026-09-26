# Content types, layouts and `theme.toml` - design

Date: 2026-09-26. Status: approved in conversation, awaiting review of this
document. Implementation plan to follow.

The generator gets a name with this work: **tilder** - the `~/` of the
wordmark, the home folder, the terminal. The repositories are renamed later;
the README, the docs and the image carry the name from now on.

---

## 1. Goal

The generator knows three kinds of content by heart - members, posts,
events - and that knowledge is spread over five modules (`members.py`,
`dated.py`, `seo.py`, `page.py`, `feeds.py`, and the path test in
`build.py` that makes `members/` special). A site that needs another kind
of content (talks, projects, a product's documentation pages) cannot have
it without editing the generator.

After this work:

- A **type** is one Python module with a small, documented interface. The
  generator ships four: `page`, `post`, `event`, `member`. A theme adds its
  own in `theme/types/`, and may replace a built-in one by name.
- Every kind of content goes through that one interface: the built-in types
  are ordinary type modules, written exactly as a theme would write them.
  If a theme cannot write a type, the interface is wrong.
- A type produces **nodes** of the existing tree, never HTML: the text
  mirror stays exact for every type, built-in or not.
- A theme can give each type its own **layout**, and carries what is the
  theme's and not the site's in `theme/theme.toml`, so a theme can live in
  its own repository and be reused by another site.
- When the build stops, the message says which file, what is wrong, and
  what to do.

### Not in this work

- **Several languages on one site** (`/fr/`, `/en/`, `page.en.md` falling
  back to `page.md`). Designed later, once every page goes through a type.
- **A documentation type** with a navigation tree in the layout. The type
  system must make it possible; it does not build it. The one hook it would
  need - a type injecting blocks into the layout - is noted in §13.
- A website for tilder itself.

---

## 2. Vocabulary

- **Type**: a module that says what a kind of content is: its fields, its
  card in a list, its page, its structured data, its feed item, its layout.
- **Collection**: a folder under `content/` whose files are items of one
  type, declared as `[collections.<name>]` in `site.toml`. A page outside
  every collection is of type `page`.
- **Item**: one file (or one folder with an `index.md`) of a collection.
- **Entry node**: the tree node a card is made of - title, meta line, tags,
  blocks - rendered by `page.py` to HTML and by `text.py` to text. It exists
  today (`{"k": "entry", ...}`); it is the contract between a type and the
  two renderers.
- **Layout**: a `layout.html`-shaped template a page is filled into.

---

## 3. A type module

Built-in types live in `types/` at the generator's root, one file each:
`page.py`, `post.py`, `event.py`, `member.py`. A theme's live in
`theme/types/`. Same interface, same loader.

Everything is optional except `NAME` and `entry`. Attributes first:

```python
NAME = "event"          # the value of `type =` in [collections.*]
DATED = True            # items are named YYYY-MM-DD-slug; else <slug>
ARTICLE = True          # wrap the body in <article>; og:type "article"
LAYOUT = "event"        # theme/layouts/event.html, falling back to layout.html
SCRIPT = ""             # a theme script to load on pages that list this type,
                        # if the theme ships it ("members.js" for member)
DEFAULTS = {            # the type's words and settings, English and neutral;
    "man": "SITE-EVENTS(7)",     # what [collection_defaults.events] is today.
    "nav": "events",             # A collection merges its own values over them.
    "upcoming_tag": "upcoming",
    ...
}
MARKERS = {             # section markers that list this type's items:
    "upcoming": upcoming,        # {upcoming}, {upcoming:talks}
    "past": past,
    "next-event": next_one,
}
```

Then the functions. `item` is the dict §4 describes, `conf` the
collection's settings (its `DEFAULTS` merged with `[collections.<name>]`).

```python
def defaults(item, conf):
    """Fill what the front matter may leave out: man, nav, tagline..."""

def sort_key(item, conf):
    """Order of the items in lists and feeds. Default: the slug, which for
    a dated type is the date."""

def entry(item, link, conf):
    """The card: an entry node. link=True in a list (the title links to the
    page); link=False for the heading card at the top of the item's own
    page. Nodes only - never HTML."""

def json_ld(item, conf):
    """The item's main schema.org node as a dict, or None. seo.py wraps it
    in the graph (Organization, WebSite, BreadcrumbList) as it does today."""

def feed_item(item, conf):
    """{"title", "link", "description", "date"} for the collection's RSS
    feed, or None to leave the item out. feeds.py writes the feed."""

def outputs(items, conf):
    """Files the type writes for a collection: {"path": str}. The event
    type writes its iCalendar here, with feeds.py's helpers."""

def list_data(conf):
    """data-* attributes for a section that lists this type: {"search_label":
    ...}. The member type hands members.js its words this way."""
```

A marker function selects and orders the items a section lists:

```python
def upcoming(items, conf):
    """-> ([(item, extra_classes)], empty_text). Items to list, in order,
    each with the classes its card gets ("next" on the first upcoming
    event); and the text shown when there is none."""
```

The `page` type has no folder, no markers, no feed: `NAME = "page"`,
`entry` returns `None` (a page has no card), `json_ld` returns the WebPage
node. It is the type of every `.md` outside a collection.

**The contract that holds everything**: `entry` returns a node of the
existing tree (`entry`, with `para`, `profiles`, `empty` blocks and so on).
`page.py` and `text.py` do not change for a new type. A type that needs a
new block kind asks the generator for it - a new block is a Markdown
construct, with its two renderings and its documentation (AGENTS.md §2.4).

---

## 4. Items and collections

### The item dict

```python
{
    "slug": "2026-11-21-campus-du-libre",  # file stem or folder name
    "date": "2026-11-21",                  # DATED types only; else None
    "meta": {...},                         # the front matter, after defaults()
    "src": Path("content/events/2026-11-21-campus-du-libre.md"),
    "path": "events/2026-11-21-campus-du-libre.html",
    "collection": "events",
    "conf": {...},                         # the collection's settings
    "type": <the type module>,
}
```

An item is `<slug>.md` or `<slug>/index.md` in the collection's folder,
whatever the type: a member may keep a file next to their page the way a
post keeps its images. Names starting with `_` are templates and skipped,
as today. A `DATED` type requires the `YYYY-MM-DD-` prefix and a valid date.

### Declaring collections

Everything goes through `[collections.<name>]` in `site.toml`. Type names
are singular: a type names one item.

```toml
[collections.blog]
type = "post"
dir = "blog"                 # default: the collection's name
feed = "blog/feed.xml"

[collections.events]
type = "event"
calendar = "events.ics"

[collections.members]        # members stop being a special case
type = "member"
categories = ["admin", "mentor", "member"]
```

`defaults.toml` keeps declaring `blog`, `events` and `members` with their
folders, inactive until the folder exists, so the starter builds with no
declaration at all. `[collection_defaults.*]` and the `[members]` table
leave `defaults.toml`: a type's defaults are its module's `DEFAULTS`, and a
collection's words are set under the collection, whatever its type. One
place per collection for its words; a theme's type is configured exactly
like a built-in one.

A page's type is no longer read from its path: `build.py` asks the
collections, and a `.md` no collection claims is a `page`. The front matter
may set `layout:` (§6); it may not set `type:` - content worth a type is
worth a folder.

### Bare and named markers

`{upcoming}` lists the page's own collection of the marker's type - the
page in the collection's folder, or the page named like the folder
(`events.md` for `events/`) - else the first collection of that type.
`{upcoming:talks}` names one. This is today's `_target` rule, kept, made
generic: a marker belongs to the type that declares it.

---

## 5. Loading types

`src/types.py` loads and validates:

1. Every `*.py` in the generator's `types/`, then every `*.py` in
   `theme/types/` (a copy in `assets/types/` does **not** override: types
   are code, not assets). A theme module whose `NAME` matches a built-in
   one **replaces** it.
2. Each module is checked: `NAME` present, a valid identifier, unique among
   loaded modules; `entry` present and callable; every other attribute of
   the interface, if present, of the right kind; `MARKERS` keys not claimed
   by another loaded type; `DEFAULTS` a dict of TOML-able values.
3. Every `[collections.*].type` names a loaded type; `dir` folders do not
   overlap (a folder belongs to one collection).

All errors of steps 1-3 are gathered and reported together (§9) before the
build stops: one run shows every problem, not the first.

Modules are imported with `importlib` under a private package name so a
theme type called `event.py` does not shadow anything on `sys.path`. A type
module imports what it needs from `src/` (`config`, `feeds`, `fold`...) the
way built-in modules do; that surface is documented in `docs/types.md` and
is the public API of the generator toward themes.

Trust: a theme runs code at build time. The theme belongs to the site's
owner, as the generator does; `docs/theme.md` says so in one sentence.

---

## 6. Layouts

A theme keeps `theme/layout.html`, required, and may add
`theme/layouts/<name>.html`. The layout of a page is chosen in this order:

1. `layout:` in the front matter, if set (`layout: landing`);
2. the type's `LAYOUT`, if the theme has that file;
3. `layout.html`.

A `layout:` that names no file stops the build: silence would hide a typo.
Layouts share the placeholders and the "unknown placeholder stops the
build" rule of `layout.html` (`docs/theme.md`). `layouts/` joins
`layout.html` and `share.svg` among the files read by the build and never
served. A copy in the site's `assets/` wins over the theme's, as for any
theme file.

The layout gets one new placeholder, `{{ type }}`, the type's name (computed
by the build, not a front-matter value), so a theme can hang a class on
`<body>`.

---

## 7. `theme/theme.toml`

A third configuration layer, optional, merged in this order:

```
defaults.toml  <  theme/theme.toml  <  content/site.toml
```

It holds what is the theme's and not the site's. For now that is the
colours of `[share]` (`theme_color`, `background_color`, `text_color`,
`muted_color`, `rule_color`). Everything else in `site.toml` - name, URL,
language, navigation, labels, SEO, dates, robots - is identity and language,
and stays with the site, which has the last word on every key.

Four lines in `config.load_config()`. What it buys: a theme is
self-contained (layouts, styles, fonts, icons, scripts, types, colours) and
can live in its own repository, as a git submodule of a site, like the
generator.

---

## 8. Scripts

Today `page.py` loads `members.js` when it sees `{members}`. That becomes
the type's `SCRIPT`: loaded on every page whose sections list the type, if
the theme ships the file, with the type's `list_data` words as `data-*`
attributes on the listing section. `code.js` is unchanged: it belongs to a
Markdown construct, not to a type. AGENTS.md §6 is reworded: the generator
knows `code.js`, and whatever scripts the loaded types name.

---

## 9. Errors and logs

The generator stops on a problem it cannot build around. When it does, the
message says what, where, and what to do. This is the policy for everything
this work touches, and the standard for what comes after.

**One error, one line, one shape:**

```
error: <file>[:<line>]: <what is wrong>. <what to do>
```

```
error: content/site.toml: collection "talks" has type "talk", which no
type defines. Types loaded: page, post, event, member (types/), doc
(theme/types/doc.py).
error: theme/types/doc.py: MARKERS["posts"] is already claimed by type
"post" (types/post.py). Rename the marker, or replace the post type
by naming yours "post".
error: content/events/2026-13-01-meetup.md: "2026-13-01" is not a date.
Name the file YYYY-MM-DD-slug.md with the event's date.
```

**Rules:**

- Paths are relative to the site root, the way the user typed them.
- A front-matter error names the key, and the line when it can.
- An error inside a theme type is reported with the module's path and the
  attribute or function that failed; the Python traceback is shown only
  with `--debug`.
- Type loading and collection reading gather every error and report them
  together, then stop. Content errors (a bad date, a missing field) still
  stop at once, with file and line: they are found one page at a time.
- Warnings keep the `warning:` prefix and never stop the build.
- **The build says what it understood**, two lines at start:
  ```
  types: page, post, event, member; from theme: doc
  collections: blog (post, 1 item), events (event, 1), members (member, 3)
  ```
- In `--watch`, the waiting message says what it waits for: a change in
  `content/`, `theme/` or `assets/`; or a restart, when `builder/` or
  `theme/types/` change (the process still runs the code that failed).

A small `src/report.py` gives `error(path, what, hint)`, `warning(...)`,
and `fail(errors)`; modules stop calling `raise SystemExit(f"...")` with
ad-hoc wording as they are touched.

---

## 10. What changes in `src/`

```
types/            NEW  the built-in types: page.py, post.py, event.py, member.py
src/types.py      NEW  load, validate and index the types; resolve markers
src/report.py     NEW  errors and warnings, one shape
src/members.py    GONE -> types/member.py
src/dated.py      GONE -> types/post.py, types/event.py, and src/types.py (loading items)
src/build.py      knows no content kind: types, collections, items, pages
src/seo.py        drops its four JSON-LD branches; asks item["type"].json_ld
src/feeds.py      one generic RSS from feed_item(); iCalendar helpers, called by types/event.py
src/page.py       <article> from ARTICLE; scripts and data-* from the type; layout choice
src/config.py     theme.toml layer; layouts/ among TEMPLATES; theme/types/ path
src/watch.py      restart when theme/types/ changes
defaults.toml     loses [collection_defaults.*] and [members]; keeps the three default collections
```

`human_date` (words from `[dates]`) moves to a small `src/dates.py`: types
need it, and it is not a type's business.

The four built-in types carry the code they replace, reshaped to the
interface, with the same output: the member card's meta line, search data
and profiles; the post card's date, author and tag; the event card's date
range, place, upcoming/past tag, site and OpenStreetMap links; the three
JSON-LD nodes; the RSS items; the iCalendar.

---

## 11. Documentation

- `docs/types.md`, **new**: the type contract of §3-§4, the loader's rules,
  the API a type may import, `types/event.py` as the complete example, and
  how to write a theme type in ten lines (a `talk` that is an `event` with
  a speaker).
- `docs/theme.md`: `layouts/`, `theme.toml`, `types/`, `{{ type }}`,
  the sentence on trust.
- `README.md`: the name, the four types, the theme's new folders, the
  image (§12).
- `AGENTS.md`: §2.1 admits a type module's `DEFAULTS` next to
  `defaults.toml` (English, neutral, commented); §3 gets the new layout;
  §6 scripts; §10 "do not add a type without its docs entry and its two
  renderings". The `grep -rni` rule for a site's name stands: this
  document names none.
- The starter keeps no type of its own: it must build with the defaults.

---

## 12. Repository and image

**A theme in its own repository.** Nothing in the generator changes for
that: it reads `theme/` and does not know where it comes from. A site that
moves its theme out does what it did for the generator: a repository with
a README and a licence, a submodule at `theme/`. §7 is what makes the theme
whole enough to move.

**The runtime image, built by CI.** `.github/workflows/image.yml` builds
the `Dockerfile` on every push to `main` and every `v*` tag, and pushes to
`ghcr.io/thosted/tilder` with the tags `latest`, `<major>`, `<major.minor>`
and `<version>`. The image ships **the runtime and the generator** at that
version: Python, `rsvg-convert`, `woff2`, and `build.py`, `defaults.toml`,
`src/`, `types/` under `/tilder`. Its entry point is
`python3 -B /tilder/build.py --root /site`, so a site can drop the
submodule:

```yaml
services:
  build:
    image: ghcr.io/thosted/tilder:1
    command: ["--out", "/out", "--watch"]
    volumes:
      - ./content:/site/content:ro
      - ./theme:/site/theme:ro
      - ./assets:/site/assets:ro
      - site:/out
```

The submodule stays for a site that pins a commit or works on the
generator; mounting `./builder` over `/tilder` gives the current behaviour.
`examples/compose.yaml` shows both. The version is the git tag; the code
carries none (`--version` prints the tag baked into the image at build,
`dev` otherwise).

---

## 13. Later, made possible by this work

- **Layout blocks from a type**: `layout_blocks(item, conf) -> {name:
  [nodes]}` exposed as `{{ type.<name> }}`, rendered by `page.py`, so a
  `doc` type can put a navigation tree in its layout. Nodes, not HTML, so
  the text mirror may show it too.
- **Languages**: `/fr/`, `/en/`, a default language, `page.en.md` falling
  back to `page.md`; per-language config overlay, `hreflang`, feeds and
  mirror per language.
- **Renaming** the repositories and the `builder/` folder to `tilder`.

---

## 14. Acceptance

1. **Byte-identical output.** The reference site, built before and after,
   gives the same `public/`, once its `site.toml` is migrated (§15):
   `diff -r` prints nothing. This is the regression test of the whole
   work, and every step of the plan ends with it.
2. **The starter builds** from the defaults alone, with no type of its own.
3. **A theme type works**: a throwaway `theme/types/talk.py` (an event
   with a speaker) lists, renders, feeds and validates like a built-in one,
   in HTML and in text - then is deleted, or kept as the example in
   `docs/types.md`.
4. **Replacing a built-in**: a theme `member.py` with `NAME = "member"`
   takes over without a warning.
5. **Every error path of §9** produces its one line: unknown type, marker
   clash, bad date, unknown layout, unknown placeholder, old `site.toml`
   form.
6. AGENTS.md §9 checks pass: 75 columns, no escape in `txt/`, `ansi` equals
   `txt` stripped, one `<h1>`, no foreign request, no script but the
   theme's and JSON-LD.

---

## 15. Migration of an existing site

One file, `content/site.toml`:

- `type = "posts"` becomes `type = "post"`, `type = "events"` becomes
  `type = "event"`;
- the `[members]` table moves under `[collections.members]`, next to
  `type = "member"`.

Pages, content and theme are untouched. The old form is refused with the
message that says what to move:

```
error: content/site.toml: collection "blog" has type "posts"; types are
singular. Write type = "post".
error: content/site.toml: [members] is no longer read. Move its keys under
[collections.members], with type = "member".
```

Moving the theme to its own repository, and switching `compose.yaml` to the
image, are the site's own steps and happen in the site's repository after
the generator is released.
