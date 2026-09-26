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
            "speaker_label": "speaker", "feed_title": "talks", "feed_description": "Talks.",
            "none_upcoming": "No upcoming talk.", "none_past": "No past talk."}
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
