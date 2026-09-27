# The content format

Every page of the site is one Markdown file under `content/`. The format is a
small, strict dialect of Markdown with a few additions for the man-page
layout. It is **not** CommonMark: anything not listed here is rendered as
plain text, not interpreted.

Each construct has two renderings: HTML for the site, and ASCII text for the
terminal mirror (`curl example.org`, or a plain-text host such as
`man.example.org`). Both are produced by
`builder/build.py` from the same source, so they cannot drift apart.

- [Site-wide content: `site.toml`](#site-wide-content-sitetoml)
- [A page, end to end](#a-page-end-to-end)
- [Files and URLs](#files-and-urls)
- [Front matter](#front-matter)
- [Sections](#sections)
- [Entries](#entries)
- [Blocks](#blocks)
- [Inline markup](#inline-markup)
- [Links](#links)
- [Collections](#collections)
- [Images](#images)
- [Members](#members)
- [What is not supported](#what-is-not-supported)
- [Quick reference](#quick-reference)

Every construct below is also shown live, source then rendering, in the blog
post `content/blog/2026-09-26-comment-ce-site-est-construit.md`
(`/blog/2026-09-26-comment-ce-site-est-construit`).

---

## Site-wide content: `site.toml`

`content/site.toml` holds every site-wide value and string: name, canonical
URL, language, footer date, navigation, header and footer rules, labels,
sharing defaults, feed and calendar texts, blog and event defaults, how
dates are written, member categories and search wording, `robots.txt` rules.
It is TOML, read with Python's standard library; each key is commented in
the file.

The HTML skeleton around every page (`<head>`, header rule, navigation,
wordmark, footer) is not content: it is the site theme's `layout.html`
(`docs/theme.md`), filled from `site.toml`. The text mirror's header and
footer rules come from `site.manual`, `footer.left`, `site.updated` and
`footer.right`.

The build also writes, from `site.toml`: `site.webmanifest`, `robots.txt`
(from `[robots]`, plus the sitemap URL) and `txt/robots.txt`, which is the
`robots.txt` of the plain-text host (from `[robots_man]`).

The coloured text mirror (`ansi/`) takes two keys from `[text]`:
`commands`, the words that start a command line in a code block, and
`accent`, its one accent colour - links, `[ tags ]`, list markers, inline
`code`, command lines and the INFO box. `accent` is one of the eight colour
names `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan` (the
default), `white`, or a 256-colour index from 16 to 255, such as `208` for
orange; a `site.<lang>.toml` may set its own. Anything else stops the
build. Warnings stay yellow and errors red.

```toml
[text]
commands = ["curl"]
accent = 208
```

---

## A page, end to end

```markdown
---
man: MYSITE-EVENTS(7)
title: events
description: Upcoming and past meetups, with iCalendar and RSS feeds.
tagline: meetups · feeds
nav: events
feed: events
---

## Name

events - meetups, upcoming and past {mono}

## Upcoming {upcoming}

Regular meetups are being prepared. {small muted}

## Past {past}
```

And an event, `content/events/2026-05-16-spring-meetup.md`:

```markdown
---
title: Spring meetup
description: Talks and demos around free software, open to everyone.
place: Main hall, 1 Example Street, Exampleville
link: https://meetup.example.org/
---

## Description

Three talks and a hands-on workshop.
```

The page chrome - man-page header and footer rules, navigation, wordmark,
tagline - comes from the builder and `content/site.toml`. The event's card
appears under `Upcoming` by itself, with its date written out, its place and
an `upcoming` tag. A source file holds only the front matter and the sections.

---

## Files and URLs

| Source | Page | URL | Text mirror |
|---|---|---|---|
| `content/index.md` | `index.html` | `/` | `txt/index.txt` |
| `content/events.md` | `events.html` | `/events` | `txt/events.txt` |
| `content/blog/index.md` | `blog/index.html` | `/blog/` | `txt/blog.txt` |
| `content/blog/YYYY-MM-DD-slug.md` | `blog/YYYY-MM-DD-slug.html` | `/blog/YYYY-MM-DD-slug` | `txt/blog/YYYY-MM-DD-slug.txt` |
| `content/blog/YYYY-MM-DD-slug/index.md` | the same | the same | the same |
| `content/events/YYYY-MM-DD-slug.md` (or `/index.md`) | `events/YYYY-MM-DD-slug.html` | `/events/YYYY-MM-DD-slug` | `txt/events/YYYY-MM-DD-slug.txt` |
| `content/members/<slug>.md` | `members/<slug>.html` | `/members/<slug>` | `txt/members/<slug>.txt` |

- File names are English, lowercase, ASCII, with hyphens: `code-of-conduct.md`,
  not `code-de-conduite.md`. The text inside is in the site's language.
- On a site with several declared languages, a file may carry a language
  suffix before `.md` (`about.fr.md`, `2026-01-01-hello.fr.md`): see
  `docs/languages.md`.
- A file or folder whose name starts with `_` is **never rendered** (the
  templates, `content/*/_template.md`).
- Any other file in `content/` that is not Markdown (an image, a PDF) is
  copied to the site at the same path.
- Every rendered page is added to `sitemap.txt`, except `404`.

---

## Front matter

Between two `---` lines at the very top of the file, one `key: value` per
line. Values are plain text, not quoted.

| Key | Required | Meaning |
|---|---|---|
| `man` | yes* | Man-page name in the header rule, e.g. `MYSITE-EVENTS(7)`. |
| `title` | yes | The page's title. The `<title>` adds `site.title_suffix` (` - my site`) unless the title already names the site. |
| `name` | no | The page's name in the `<h1>` path, `~/my site/<name>`. Default: the title without the suffix. On a folder's page (`events.md`, `blog/index.md`), it also names that folder's segment on every page inside: `~/my site/<name>/<title>`, so the path reads the same on the list and on its pages. |
| `description` | yes | `<meta name="description">`, one sentence. Also the blog feed summary. |
| `tagline` | yes* | The line under the wordmark. |
| `nav` | yes* | Which nav entry is marked current: `""` (landing), `events`, `blog/`, `members`, or `-` for none. |
| `feed` | no | Adds `<link rel="alternate">` for `events`, `blog` or `all`. |
| `text` | no | `text: no` skips the text mirror for this page (the 404 does). |
| `image` | no | Preview image for link sharing, relative to the page's folder. Default: `share.image`. |
| `group` | no | In a collection: the item's group in the theme's collection sidebar (`docs/types.md`). |

\* Items of a collection (posts, events) may leave `man`, `nav` and
`tagline` out: `man` and `nav` come from their collection in `site.toml`,
the tagline is the date. They have fields of their own too (see
[Collections](#collections)).

`title`, `description` and `image` also feed the page's sharing tags - Open
Graph (`og:*`) and Twitter Card (`twitter:*`) - so a link pasted into
Mastodon, LinkedIn, Slack, Discord and the like shows a preview. Blog posts
are typed `article` with their publication date; other pages are `website`.
Social platforms mostly ignore SVG, so a custom `image` should be a PNG or
JPEG, ideally 1200x630 (a square works with the default `summary` card).

---

## Sections

A section is a `##` heading. It renders as the man-page row: the name in the
left gutter, the content indented on the right. In the text mirror the name
is printed in capitals at column 0 and the body is indented five spaces.

```markdown
## Nom
## Contribuer {#contribuer}
## Membres {grid}
## Gabarit {text}
```

Markers go at the end of the heading, in braces, any number of them:

| Marker | Effect |
|---|---|
| `{#id}` | `id="id"` on the section, so it can be linked as `page#id`. Without it, the id comes from the title (`## Le principe` -> `#le-principe`). |
| `{html}` | HTML only: skipped in the text mirror. |
| `{text}` | Text only: skipped in the HTML page. |
| `{grid}` | Lays the section's entries out as a grid of cards. |
| `{members}` | Fills the section with one card per member, from `content/members/*.md` (see [Members](#members)). |
| anything else | Added as a class on the section body. |

Everything before the first `##` is rendered in the HTML page, outside any
section, and ignored by the text mirror. Pages normally start straight with
`## Nom`.

---

## Entries

An entry is a `###` heading inside a section: an event, a member, a mentor,
a post.

```markdown
### Spring meetup {next}

  - 2026-05-16 | Saturday 16 May 2026
  - Main hall, 1 Example Street, Exampleville
  - `upcoming`

  Talks and demos around free software.

  [meetup.example.org ↗](https://meetup.example.org/) {small}
```

**The meta line.** A list that directly follows the heading is the entry's
meta line, not a bullet list. Each item is one of:

| Item | HTML | Text |
|---|---|---|
| `` `tag` `` | a tag badge | `[ tag ]`, right-aligned on the title line |
| `YYYY-MM-DD \| human date` | `<time datetime="YYYY-MM-DD">human date</time>` | the human date only |
| anything else | a plain span | one line |

Items are separated by `·` in HTML. Only the first tag goes on the text title
line.

**The body.** Blocks that belong to the entry are **indented two spaces**. The
first block that is not indented closes the entry and goes back to the
section.

**Markers** on the heading become classes: `{next}` puts the entry's tag in
the accent colour (the next event) - the card itself looks like any other;
`{full}` marks a mentor at capacity. Any other marker becomes
`entry--<marker>`.

---

## Blocks

Blocks are separated by a blank line. Headings (`##`, `###`) always stand on
their own, blank line or not.

### Paragraph

Consecutive lines are joined into one paragraph. Classes go at the end, in
braces:

```markdown
Les articles sont des comptes rendus techniques. {small muted}
```

Available classes: `small`, `muted`, `faint`, `mono`, `warn`. They affect the
HTML only; the text mirror prints the paragraph plain.

### Empty state

A paragraph wrapped entirely in single asterisks is an empty state - the
muted monospace line that says something does not exist yet:

```markdown
*Aucun article publié pour l'instant.*
```

The asterisks must enclose the **whole** paragraph. `*À compléter.* Autre
texte.` prints the asterisks literally.

### List

An item starts with `- ` (or `* `) for a bulleted list, with `1. ` (or
`1) `) for a numbered one; a numbered list starts at its first number.
Indent an item further than the one above to nest a list inside it. An
indented line that is not an item continues the item above.

```markdown
1. Cloner le dépôt
2. Lancer la pile, avec une phrase
   qui continue ici
   - `docker compose up -d`
   - vérifier avec `curl`
3. Écrire du contenu
```

A `[ ]` or `[x]` right after the marker makes a task: an empty or a
checked box. Screen readers hear `labels.task_todo` / `labels.task_done`
("à faire", "fait").

```markdown
- [x] migrer le blog en dossiers
- [ ] écrire le premier compte rendu
```

In text: `  1. item`, `  - item`, `  - [x] item`; wrapped lines and nested
lists align under the item's text.

Right after a `###` heading, a list is the entry's meta line instead (see
[Entries](#entries)).

### Table of contents

`[TOC]` alone on a line lists the page's sections, each linking to its
anchor. Put it where the contents should appear - near the top of a long
post. In HTML it is a `<nav>` named by `labels.toc`, **folded by default**
(`<details>`: `[+]` opens it, no script needed); in text, a numbered list
of the section names. Sections shown in one output only are listed
only in that output.

```markdown
[TOC]
```

### Horizontal rule

`---` (or `***`, `___`) alone on a line draws a rule: `<hr>`, a line of
dashes in text. At the top of a file, `---` still opens the front matter.

### Inset

Every line starts with `>`. Rendered as a boxed note in HTML, indented in
text. A line that is only `>` separates two paragraphs.

```markdown
> **Note:** the [archive ↗](https://archive.example.org/) keeps older posts.
>
> Un second paragraphe.
```

### Callout

An inset whose first line is `[!INFO]`, `[!WARNING]` or `[!ERROR]` is a
callout - GitHub's syntax. Text may follow the marker on the same line.

```markdown
> [!WARNING]
> Ne modifiez jamais `public/` à la main.
```

| Marker | Kind | Label shown | Colour |
|---|---|---|---|
| `[!INFO]` (`[!NOTE]`, `[!TIP]`) | info | `labels.info` | accent |
| `[!WARNING]` (`[!IMPORTANT]`, `[!CAUTION]`) | warning | `labels.warning` | `--warn` |
| `[!ERROR]` (`[!DANGER]`) | error | `labels.error` | `--error` |

The labels come from `[labels]` in `content/site.toml` (`INFO`,
`ATTENTION`, `ERREUR`). In HTML: a box with a coloured left rule and the
label; errors carry `role="alert"`, the others `role="note"`. In text: a box
drawn in ASCII, the label in its top rule, coloured by kind in the ANSI
mirror:

```text
+- ATTENTION ------------------------------------------------------+
| Ne modifiez jamais public/ a la main.                            |
+------------------------------------------------------------------+
```

### Code block

Fenced with three backticks. A language name right after the fence turns on
syntax highlighting, computed at build time (`src/highlight.py`, no
JavaScript), and shows the language in the block's corner.

If the theme ships `code.js`, every code block gets a **copy** button
(loaded only on pages with code): it copies the code as plain text, without the
highlighting. The button and the language float over the code, top right,
faded until the block is hovered or focused. Without JavaScript there is no button, and the code is
selected by hand as usual. The wording is `labels.copy` / `labels.copied`.

````markdown
```python
def plier(texte, largeur=75):
    return textwrap.wrap(texte, largeur)
```
````

| Language | Also accepted |
|---|---|
| `sh` | `bash`, `shell`, `zsh` |
| `console` | `terminal`, `shell-session` - `$ ` and `# ` lines are commands, the rest output |
| `python` | `py` |
| `js` | `javascript`, `ts`, `typescript`, `node` |
| `c` | `h`, `cpp`, `c++` |
| `go` | `golang` |
| `rust` | `rs` |
| `sql` | `postgres`, `postgresql` |
| `json` | |
| `yaml` | `yml` |
| `ini` | `toml`, `cfg`, `systemd` |
| `conf` | `caddy`, `caddyfile`, `nginx` |
| `dockerfile` | `docker`, `containerfile` |
| `html` | `xml`, `svg` |
| `css` | |
| `make` | `makefile` |
| `diff` | `patch` - `+` lines in the accent, `-` lines in `--error` |
| `text` | `plain`, `txt` - no highlighting, but labelled |

An unknown language prints a build warning and leaves the block plain. No
language means no label and no highlighting. Highlighting is approximate by
design - keywords, strings, comments, numbers - and uses the site's palette
only: weight for keywords, the accent for strings, the muted tone for
comments.

A long line never widens the page: the block scrolls horizontally. In the
text mirror the block is framed by two rules, the language in the top one,
the code indented inside - nothing is added to the code's own lines, so it
copies clean from a terminal:

```text
.-- python ---------------------------------------------------------------.
  def plier(texte, largeur=75):
      return textwrap.wrap(texte, largeur)
'-------------------------------------------------------------------------'
```

The `.` corners open the block, the `'` corners close it: the two rules
cannot be mistaken for each other, nor for a horizontal rule.

Spacing is kept exactly, and a line past the 75th column is cut and
continued on the next line, the cut marked with `\` - which a shell reads
as a continuation. In the coloured mirror, the rules are dim and command
lines (`[text] commands`) are in the accent (`[text] accent`); inline
`code` is coloured exactly as far as its backquotes go, even across a line
break.

To show a fence inside a code block, open the outer block with more
backticks: a fence of N backticks closes only on a line of at least N.

### Table

Pipes separate the cells; the second line separates the header. Colons set
the alignment: `:---` left (default), `:---:` centred, `---:` right. Inline
markup works in cells; write `\|` for a literal pipe.

```markdown
| Sortie | Format | Largeur |
|:-------|:------:|--------:|
| page   | HTML   |   libre |
| miroir | ASCII  |      75 |
```

In HTML, the table sits in a wrapper that scrolls horizontally when it is
wider than the column. In text, it becomes padded columns, like
`column -t`; if that does not fit in 75 columns, each row becomes a record
of `Header: value` lines instead.

### Comment

A block starting with `<!--` is copied into the HTML as-is and skipped in the
text mirror. Use it for notes to editors. The convention for a missing fact
is:

```markdown
<!-- TO FILL: host name, address and phone number. -->

*Hébergeur : à compléter.*
```

The comment says what is missing; the empty state tells the reader.

---

## Inline markup

Five constructs, no nesting:

| Source | HTML | Text |
|---|---|---|
| `[label](target)` | `<a href="...">label</a>` | `label (target)` if absolute, else `label` |
| `` `code` `` | `<code>code</code>` | `code` |
| `**bold**` | `<b>bold</b>` | `bold` |
| `*italic*` or `_italic_` | `<em>italic</em>` | `italic` |
| `~~struck~~` | `<del>struck</del>` | `~~struck~~` - dropping the marks would change the sense |
| `++underlined++` | `<u>`, dotted | `underlined` |

`*italic*` must not touch a space on the inside, so `2 * 3 * 4` stays text;
`_italic_` works only around whole words, so `snake_case` stays text;
`++underlined++` likewise, so `C++` stays text. Underlining is dotted: on
the web a plain underline reads as a link. A
paragraph wrapped **entirely** in single asterisks is still an empty state
(see [Empty state](#empty-state)), not an italic paragraph.

Everything else is literal text and is HTML-escaped: no image inside a
sentence, no raw inline HTML.

In the text mirror, accents and typographic characters are folded to ASCII
(`é` -> `e`, `-` -> `-`, `«` -> `"`, `↗` removed), and lines are wrapped at
75 columns.

---

## Links

Write internal targets **from the site root, without a leading slash and
without `.html`**. The renderer makes them relative to the page they appear
on, so the same source works on `/events` and on `/blog/some-post`.

| Target | Means |
|---|---|
| `./` or empty | the landing page |
| `events` | `/events` |
| `blog/` | `/blog/` (keep the trailing slash for a directory index) |
| `members/jane-doe` | `/members/jane-doe` |
| `./#contribuer` | the landing page, at `{#contribuer}` |
| `#id` | an anchor on the current page |
| `events.xml`, `calendar.ics` | files, served with their extension |
| `https://...` | external, left untouched |

On a site with several declared languages, a target resolves **inside the
current language**: `events` from a French page is `/fr/events`. A target
that starts with `/` is taken from the site root instead, without the
language: `/events` from a French page is the English page, `[en
français](/fr/events)` from an English page is the French one
(`docs/languages.md`). A target with a file extension (`events.ics`,
`logo.svg`) is a file, written once at the site root, and resolves from
there in every language; a feed linked from content is the default
language's unless the link names the prefix (`/fr/blog/feed.xml`).

Whether an external link opens in a new tab is set once, in `site.toml`:
`[links] new_tab = true` sends every `https://` link to a new tab, except
the hosts listed in `same_tab` (and their subdomains). Screen readers are
told: "(external site, opens in a new tab)", from `labels.external` and
`labels.new_tab`.

Mark an external link with `↗` in its label: `[archive ↗](https://archive.example.org/)`.
In the text mirror, an internal link keeps only its label (it is visited with
`curl`, not copied), while an absolute one prints its URL in parentheses.

---

## Collections

A **collection** is a folder whose files are items of one **type**; the
types are `post`, `event`, `member`, and whatever the theme adds
(`docs/types.md`). An item is `<slug>.md` or `<slug>/index.md` (a folder,
to keep images next to it); for posts and events the slug starts with the
date, `YYYY-MM-DD-slug`.

Collections are declared in `site.toml`:

| Type | Items | Lists | Feeds | Structured data |
|---|---|---|---|---|
| `post` | articles, notes, news | newest first | RSS | `BlogPosting` |
| `event` | meetups, talks, releases | upcoming and past, by the date of the build | RSS and iCalendar | `Event` |
| `member` | people | category order, then last name | - | `ProfilePage` |

```toml
[collections.blog]          # the name, used by markers and `feed:`
type = "post"
dir = "blog"                # content/blog/, served at /blog/...
feed = "blog/feed.xml"

[collections.talks]
type = "event"
dir = "talks"
nav = "talks"               # the nav entry of its items, and its feed's link
feed = "talks.xml"
calendar = "talks.ics"
upcoming_tag = "soon"

[collections.members]
type = "member"
categories = ["admin", "member"]
```

Every key a type needs has a default in its module, `types/<type>.py`
(`DEFAULTS`, listed in `docs/types.md`): man-page name, nav, empty-list
texts, tags, link labels, feed titles, member words. A collection sets only
what differs. `defaults.toml` declares `blog`, `events` and `members`; each
stays inactive - no page, no feed - until its folder exists.

| Field | Posts | Events |
|---|---|---|
| `title` | the post's title | the event's name |
| `description` | one sentence: card text, feed summary | the same |
| `author` | a named author | - |
| `tag` | one word, the card's tag | - (set by the date: `upcoming_tag` / `past_tag`) |
| `place` | - | where; the iCalendar `LOCATION` |
| `link` | - | the event's own site |
| `end` | - | `YYYY-MM-DD`, for an event over several days |
| `lat`, `lon` | - | coordinates, for an exact OpenStreetMap marker and the iCalendar `GEO` |

Member fields are documented in [Members](#members).

On an event's page, its card links to the event's own site (`link`) and to
the place on **OpenStreetMap**: a marker at `lat`/`lon` when given, else a
search for `place`. It is a link, not an embedded map: an iframe would make
every visitor's browser call openstreetmap.org. Do not look up coordinates
you are not given. The text mirror leaves the map link out: the address is
on the card, and the URL would not fit in 75 columns.

In a list, an item's card is clickable as a whole: its title's link covers
the card.

Nothing else is written by hand. From these files the build makes:

- each item's page, with its card (date, author or place, tag; a member's
  profile links) at the end of its first section;
- the lists, in the sections that carry these markers:

| Marker | Fills the section with |
|---|---|
| `{posts}` | every post, newest first |
| `{upcoming}` | events dated today or later, nearest first, the first highlighted |
| `{past}` | events before today, latest first |
| `{next-event}` | the next event only |
| `{members}` | every member, a grid, category order then last name |

  Each marker may name its collection: `{posts:news}`, `{upcoming:meetups}`,
  `{next-event:meetups}`. A bare marker lists the page's own collection -
  the one whose folder the page is in, or is named like (`events.md` for
  `events/`) - else the first collection of the marker's type. An empty
  list shows the collection's empty-state text. Blocks written under the
  heading stay, after the cards.
- per collection, its `feed` (RSS) and, for events, its `calendar`
  (iCalendar): every item, with its own URL. Leave either empty for none.
  A page's `feed:` front-matter key names a collection (or `all`) to
  advertise its RSS in `<link rel="alternate">`.

"Upcoming" and "past" depend on the date of the build. The site is built at
every start, on every change, and again each midnight, so an event moves to
the past list the day after it ends without anyone touching it.

---

## Images

An image stands alone on its line:

```markdown
![Schéma du chemin d'une page](pipeline.svg "Le chemin d'une page.")
```

- The path is **relative to the Markdown file's folder**: put the image next
  to the page, typically in a post's or an event's folder. Unlike links,
  which are written from the site root.
- The alt text is required - it is what a screen reader says and what the
  terminal shows. The build warns when it is empty, or when the file is
  missing.
- The quoted text, optional, becomes the caption.
- An absolute `https://` URL works too, but the CSP only allows images from
  the site itself: a remote image will not display.

In HTML: a `<figure>` with the image at its natural size (never wider than
the column), `width` and `height` read from the file (PNG, JPEG, GIF, WebP,
SVG) so the page does not jump, lazy loading, and the caption. In text:

```text
[ image ] Schéma du chemin d'une page
  Le chemin d'une page.
  /blog/2026-09-26-comment-ce-site-est-construit/pipeline.svg
```

Prefer SVG for diagrams: line art, readable in both themes if it carries a
`@media (prefers-color-scheme: dark)` block. SVG files are served with a
policy that lets them style themselves, never run scripts.

---

## Members

Each member is one file, `content/members/<slug>.md`, and is described
**once**, in its front matter. Start from `content/members/_template.md`
(never rendered), which documents every field.

```markdown
---
man: MYSITE-MEMBERS(7)
title: Jane Doe
description: Jane Doe, who runs the project.
tagline: admin
nav: members
first_name: Jane
last_name: Doe
pronouns: she/her
category: admin
affiliation: Example Corp
---
```

| Field | Meaning |
|---|---|
| `first_name`, `last_name` | The person's names. `last_name` sorts the list. |
| `display_name` | The name to show, when it differs from first + last (chosen name, pseudonym, single name). When set, it is the only name displayed; the others stay searchable. |
| `pronouns` | Written as the person writes them (`il/lui`, `elle`, `iel`...). Ask, never guess; leave empty if they prefer. |
| `category` | one of the collection's `categories` (`admin` and `member` by default; a site lists its own under `[collections.members]`). Shown as the card's tag and used by the filter. |
| `affiliation` | Company, school or project, if they want one shown. |
| `capacity` | A note on remaining capacity, e.g. `2 per term` - for any category that tracks one, such as a site's own `mentor` category. |
| `full` | `yes` when the capacity above is reached (the tag turns to the warning colour, and "full" is said in words). |
| `linkedin`, `github`, `gitlab`, `mastodon`, `bluesky`, `website` | Public profile URLs: a row of logos on the card and the page, `rel="me"`, `sameAs` in structured data, `Network: url` in text. Several URLs for one network go on one line, separated by spaces (`github: https://github.com/me https://github.com/my-company`); each is then named with its handle. |

Empty fields are omitted. There is deliberately no gender, age or photo
field.

From these fields the build makes:

- a card in every section marked `{members}` - on `/members`, the grid of
  all members, ordered by category (in the order of `categories`, unknown
  categories last), then by last name, each card linking to the member's
  page;
- the same card, without the link, at the end of the first section of the
  member's own page;
- the text mirror of both.

```markdown
## Membres {members}
```

A `{members}` section may be written empty: the cards come first, then any
blocks written below the heading. With no member file, it shows an empty
state.

**Search and filter.** A page with a `{members}` section loads
the theme's `members.js`, if it ships one. It adds a search box
(first, last and display name, accent- and case-insensitive, every word
must match) and one button per category. It is progressive enhancement:
without JavaScript, the full list is simply shown. Each card carries its
data as `data-search` and `data-category`, written by the build.

---

## What is not supported

On purpose, because every construct costs two renderings (HTML and text):

- headings other than `##` and `###`;
- footnotes, definition lists, reference-style links, bare URLs;
- inline images (an image is a block of its own) and raw inline HTML;
- escaping (`\*`) - rephrase instead;
- scripts in content: the site's two scripts are attached by the build
  (`members.js` by `{members}`, `code.js` by a code block).

Adding a construct means teaching it to **both** outputs in `src/`
and documenting it here.

---

## Quick reference

| Source | HTML | Text |
|---|---|---|
| `## Title {#id} {html} {text} {grid} {members} {posts} {upcoming:name} {past} {next-event}` | `<section class="s">` + `<h2>` | `TITLE` at column 0 |
| `### Title {next} {full}` | `.entry`, `.entry--next` | indented title, `[ tag ]` right-aligned |
| a list right after `###` | `.meta` spans | one line each |
| `- YYYY-MM-DD \| date` in meta | `<time>` | the human date |
| `- item`, `1. item`, nested by indent | `<ul>`, `<ol>` | `  - item`, `  1. item` |
| `- [ ] task`, `- [x] done` | `.tasks`, a box | `  - [ ] task` |
| `---` alone on a line | `<hr>` | a line of dashes |
| `> text` | `.inset` | indented |
| `> [!INFO]` / `[!WARNING]` / `[!ERROR]` | `.callout` | ASCII box, label in the rule |
| ` ```lang ` | `<pre class="code">`, highlighted | verbatim, long lines continued with `\` |
| `\| a \| b \|` + `\|---\|---\|` | `<table>` in a scrolling wrapper | padded columns, or records |
| `![alt](file "caption")` alone on a line | `<figure>` + `<img>` | `[ image ] alt`, caption, URL |
| `*text*` (whole paragraph) | `.empty` | plain |
| `text {small muted}` | `<p class="small muted">` | plain |
| `<!-- ... -->` | passthrough | skipped |
| `[t](u)`, `` `c` ``, `**b**` | `<a>`, `<code>`, `<b>` | `t (u)` if absolute, else `t` |
| `*i*`, `_i_`, `~~s~~` | `<em>`, `<del>` | `i`, `~~s~~` |
