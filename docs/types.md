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

### The built-in types' settings

The `DEFAULTS` of the built-in types, as `types/<type>.py` lists them. A
collection sets any of them under `[collections.<name>]`, in its own
language. `page` has none.

`post` - lists: `{posts}`, newest first.

| Key | Default | |
|---|---|---|
| `man` | `"SITE-BLOG(7)"` | the items' man-page name, unless one sets its own |
| `nav` | `"blog/"` | the items' nav entry, and the feed's link |
| `empty` | `"No post yet."` | a `{posts}` list with nothing in it |
| `feed` | `""` | RSS path, e.g. `"blog/feed.xml"`; empty for none |
| `feed_title` | `"posts"` | the feed's title |
| `feed_description` | `"Posts."` | the feed's description |

`event` - lists: `{upcoming}`, `{past}`, `{next-event}`, by the build's date.

| Key | Default | |
|---|---|---|
| `man` | `"SITE-EVENTS(7)"` | the items' man-page name, unless one sets its own |
| `nav` | `"events"` | the items' nav entry, and the feed's link |
| `upcoming_tag` | `"upcoming"` | the tag of an upcoming event's card |
| `past_tag` | `"past"` | the tag of a past event's card |
| `none_upcoming` | `"No upcoming event."` | an `{upcoming}` list with nothing in it |
| `none_past` | `"No past event."` | a `{past}` list with nothing in it |
| `link_label` | `"event website ↗"` | the link to the event's own site |
| `map_label` | `"see on OpenStreetMap ↗"` | the link to the place on the map |
| `feed` | `""` | RSS path, e.g. `"events.xml"`; empty for none |
| `feed_title` | `"events"` | the feed's title |
| `feed_description` | `"Upcoming and past events."` | the feed's description |
| `calendar` | `""` | iCalendar path, e.g. `"events.ics"`; empty for none |

`member` - lists: `{members}`, a searchable grid.

| Key | Default | |
|---|---|---|
| `man` | `"SITE-MEMBERS(7)"` | the items' man-page name, unless one sets its own |
| `nav` | `"members"` | the items' nav entry |
| `categories` | `["admin", "member"]` | the categories, in display and sort order |
| `default_category` | `"member"` | a member's category when the front matter sets none |
| `empty` | `"No member listed yet."` | a `{members}` list with nothing in it |
| `search_label` | `"search"` | the search field's label (members.js) |
| `search_placeholder` | `"first or last name"` | the search field's placeholder |
| `all` | `"all"` | the filter that shows every category |
| `one` | `"entry"` | the count's noun, singular |
| `many` | `"entries"` | the count's noun, plural |
| `none` | `"No entry matches."` | a search that finds nothing |
| `full` | `"full"` | a mentor at capacity, said in words |

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
| `SEQUENTIAL` | `False` | the text mirror of an item gets a `previous: ... next: ...` line before the footer (`labels.prev`, `labels.next`) |
| `LOCALIZED_OUTPUTS` | `False` | `outputs()` is called in every language, with that language's items and `conf`; its paths are put under the language's prefix (`fr/`) by the builder. Else once, in the default language |

### Order, groups and navigation

A collection's order is the type's `sort_key`. A theme shows it with
`{{ collection_nav }}`, `{{ prev }}` and `{{ next }}` (`docs/theme.md`).
An item may set `group` in its front matter: the sidebar gathers the items
by group, the groups in the order of their first item, the items without a
group first. A collection may set `nav_label`, the sidebar's accessible
name; else `labels.collection_nav`.

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

An error raised inside a type's function is reported the same way, at the
file being built, naming the module and the function:

```
error: content/talks/2099-03-01-first-talk.md: theme/types/talk.py: entry() failed: KeyError: 'speaker'. Run with --debug for the traceback
```

`--debug` adds the Python traceback of an import failure or of a failed
function. In `--watch`, a change under `theme/types/` restarts the process,
as a change in the generator does.

A theme runs code at build time. The theme, like the generator, is the
site owner's: review one before you use it.
