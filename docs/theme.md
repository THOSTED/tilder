# Themes

The builder writes HTML; a **theme** decides how it looks. A theme is a
site's `theme/` folder, next to `content/`. The builder ships none of its
own: `starter/theme/` is a minimal one to copy and grow.

A file of the same name in the site's `assets/` wins over the theme's.

---

## Files

| File | | Used for |
|---|---|---|
| `layout.html` | **required** | the page around the content, filled with `{{ placeholders }}` |
| `style.css` | expected | copied to the site root; the layout links it |
| `members.js` | optional | search and filter on a `{members}` page; loaded only there |
| `code.js` | optional | a copy button on code blocks; loaded only on pages with code |
| `fonts/` | optional | web fonts; `*.woff2` are also used to draw `share.png` |
| `icons/<network>.svg` | optional | logos of member profiles (`linkedin`, `github`...); else the network's name is shown |
| `share.svg` | optional | the link preview, drawn to `share.png` (1200x630); without it, `og:image` is the icon |
| `share-page.svg` | optional | the link preview of each page, drawn to `previews/<key>.png` with the page's fields ("Share previews"); without it, every page shows `share.png` |
| `share-<type>.svg` | optional | the same for the pages of one type (`share-event.svg`), over `share-page.svg` |
| `layouts/<name>.html` | optional | a layout for the pages of a type (`docs/types.md`), or asked for by `layout:` in a page's front matter; same placeholders as `layout.html` |
| `types/<name>.py` | optional | a content type the theme adds, or a built-in one it replaces (`docs/types.md`) |
| `mermaid.json` | optional | Mermaid's configuration for diagrams, its colours written `var(--token)` ("Diagrams") |
| `theme.toml` | optional | the theme's own configuration values, merged under the site's `site.toml`: the `[share]` colours, and `[check]` for `build.py --check` ("Checking a theme") |
| `theme.<lang>.toml` | optional | `theme.toml`'s per-language twin, between it and the site's `site.toml` (`docs/languages.md`); ignored when the site does not declare `<lang>`, so a theme may ship languages a site lacks |

Everything in `theme/` but `layout.html`, `layouts/`, `share.svg`,
`share-*.svg`, `icons/`, `types/`, `mermaid.json` and `theme.toml` (and its
`theme.<lang>.toml` twins) is copied to the site as it is. Like `site.toml`, `theme.toml` and its twins
are read at build time and never served. A theme kept in its own repository may carry a `README.md`, a `LICENSE` and git files (`.git`, `.gitignore`): they are never served either. Nor are hidden files and editors' leftovers, here as in `content/` and `assets/`: a name that starts with a dot (but `.well-known/`), `*~`, `*.swp`, `*.swo`, `*.swx`, `#name#` (`docs/markdown.md`, "Files and URLs").

---

## `layout.html`

`{{ name }}` is replaced at build time. An unknown name stops the build.

| Placeholder | Value |
|---|---|
| `{{ title }}` | the `<title>`: the page's title and `site.title_suffix` |
| `{{ type }}` | the page's type: `page`, `post`, `event`, `member`, or a theme's |
| `{{ page.<key> }}` | a front-matter value: `page.description`, `page.man`, `page.tagline`... |
| `{{ <section>.<key> }}` | a `site.toml` value: `site.lang`, `site.manual`, `footer.left`, `labels.skip`... |
| `{{ root }}` | the relative path to the site root (`./`, `../`), for `style.css`, the icons, the manifest, fonts: the site root even on a page under `/fr/` |
| `{{ home }}` | the relative path to the language's landing page, for links to pages (`{{ home }}{{ footer.left_link }}`); equal to `root` in a monolingual site |
| `{{ canonical }}` | the page's absolute URL |
| `{{ feeds }}` | `<link rel="alternate">` for the page's RSS feeds |
| `{{ head }}` | robots, author, Open Graph, Twitter Card, JSON-LD |
| `{{ brand }}` | the `<h1>`: the wordmark as a path, `~/<site>/<section>/<title>` |
| `{{ nav }}` | the navigation links, the current one marked `aria-current="page"` |
| `{{ languages }}` | the language switcher: one link per declared language, the current one marked `aria-current="page"`; empty in a monolingual site (`docs/languages.md`) |
| `{{ collection_nav }}` | the items of the page's collection, in the type's order, grouped by their `group:`, the current one marked `aria-current="page"`; on the collection's own page (`<dir>/index.md` or `<dir>.md`) the same list, nothing marked; empty elsewhere (`docs/types.md`). A recursive collection's sections are nested: `<li class="collection-section">`, its label, its own `<ul>`; the one holding the page is also `collection-section--open` |
| `{{ prev }}`, `{{ next }}` | links to the page's neighbours in that order, groups ignored, labelled `labels.prev` and `labels.next`; empty at an end, on the collection's own page and elsewhere |
| `{{ content_lang }}` | the content language of the page: equal to `site.lang` unless the page is served as a fallback |
| `{{ body }}` | the sections of the page |
| `{{ script }}` | the `<script>` tags the page needs, if the theme has the files |

Values are HTML-escaped, except the ones the builder computes (`type`,
`root`, `home`, `canonical`, `brand`, `nav`, `languages`, `collection_nav`,
`prev`, `next`, `content_lang`, `feeds`, `head`, `body`, `script`).
The starter's `layout.html` is a complete example.

The layout must keep: `lang="{{ site.lang }}"`, one `{{ brand }}` (it is
the page's only `<h1>`), a `<main id="contenu">` or equivalent target for
the skip link, and `<link rel="canonical">`. On a multilingual site,
`<main lang="{{ content_lang }}">` is recommended, so a fallback page keeps
its own language.

## Layouts

The layout of a page is, in order: `layout:` in its front matter (the file
must exist), the type's `LAYOUT` (`theme/layouts/event.html` for events, if
the theme has it), else `layout.html`.

## Trust

A theme's `types/` are Python, run at build time. The theme, like the
generator, is the site owner's: review one before you use it.

---

## The HTML the builder writes

A theme styles these. The starter's `style.css` covers them all.
`src/contract.py` holds the same list (`CLASSES`), which `build.py --check`
reads; a test keeps the two equal.

| Class | What |
|---|---|
| `.sr-only` | **required**: text for screen readers only (visually hidden) |
| `.wordmark`, `.tilde`, `.slash`, `.here`, `.cursor` | the `<h1>`: `~/`, separators, the page's own segment, a cursor |
| `.nav`, `.sep` | navigation and its separators |
| `.languages` | the language switcher (`<nav class="languages">`, `docs/languages.md`) |
| `.collection-nav`, `.collection-group`, `.collection-group-label` | the collection sidebar (`<nav class="collection-nav">`), a group (`<li>`) and its label (`<span>`, not a heading) |
| `.collection-section`, `.collection-section--open`, `.collection-section-label` | a section of a recursive collection in the sidebar (`<li>`), the one holding the current page, and its label (an `<a>` to the section's own page, else a `<span>`: the folder's name) |
| `.prev`, `.prev-label`, `.next`, `.next-label` | the neighbour links (`rel="prev"`, `rel="next"`) and their label |
| `.s`, `.b` | a section (`<section class="s">`, its `<h2>`, its body `<div class="b">`) |
| `.b.grid`, `.members`, `.posts`, `.upcoming`, `.past`, `.next-event` | markers on a section body |
| `.entry`, `.entry--next`, `.entry--full`, `.entry--link` | an entry (`<h3>`); `--link` is a card whose title link covers it |
| `.meta`, `.tag`, `.tag--next`, `.tag--full` | an entry's meta line and tags |
| `.small`, `.muted`, `.faint`, `.mono`, `.warn`, `.empty` | paragraph classes, and the empty state |
| `.inset`, `.callout`, `.callout--info`, `--warning`, `--error`, `.callout-label` | boxes |
| `pre.code[data-lang]`, `.hl-k` `.hl-s` `.hl-c` `.hl-b` `.hl-n` `.hl-v` `.hl-p` `.hl-t` `.hl-gi` `.hl-gd` `.hl-gh` | code blocks and highlighting tokens |
| `.table`, `th.center`, `th.right`, `td.center`, `td.right` | a scrolling table wrapper, alignment |
| `.tasks`, `.task`, `.task--done`, `.task--todo` | task lists |
| `.figure` | an image and its caption |
| `.map` | with `.figure`: an event's static map (`<a>` around its `<img>`, the attribution in `<figcaption>`), `docs/markdown.md` |
| `.toc`, `.toc-label` | a `[TOC]`, a `<details>` in a `<nav>` |
| `.profiles`, `.icon` | a member's profile links and their logos |
| `u.u` | `++underlined++` |

Accessibility the theme is responsible for: contrast (4.5:1 for text), a
visible focus outline, `.sr-only`, reduced motion. The builder takes care
of the markup: headings, alt text, labels, `aria-*`.

---

## Share previews

`share.svg` is the site's card: drawn once, `share.png`, the preview of
the landing page. With `share-page.svg`, every other page gets its own
card, drawn at every build from the page's fields into
`previews/<key>.png` (1200x630; the key is a hash of the filled template
and the fonts, so a page that does not change keeps its file and its
URL), and named by `og:image`, `twitter:image` and a post's or an
event's JSON-LD `image`. `share-<type>.svg` (`share-event.svg`) wins for
the pages of that type. A page keeps the site's card when it is marked
`noindex` (the 404), and shows its own image when its front matter sets
`image:`. `og:image:alt` is then the card's text, unless the page sets
`image_alt:`.

The template is an SVG with `{{ placeholders }}`, XML-escaped: every
`share.svg` one (`logo`, `manual_upper`, `wordmark`, `domain`, `card_1`,
`card_2`, any `site.toml` key such as `{{ share.text_color }}`), and the
page's own:

| Placeholder | Value |
|---|---|
| `{{ man }}` | the page's `man:` (a collection's items: the collection's), else `footer.right` |
| `{{ path }}` | where the page sits, as `~/<site>` continues: `/events` for an event (its collection's folder), `/mentoring` for a page, `/blog` for the blog's own page |
| `{{ url }}` | the address of that place, without the scheme: `example.org/events`, `example.org/fr/events` |
| `{{ title_1 }}`, `{{ title_2 }}` (`{{ title_3 }}`...) | the page's `share_title:`, else its `title`, wrapped on `[share] title_lines` lines of `title_columns` characters |
| `{{ title_shift }}` | `-title_line_height` times the title lines left empty: a `translate` for what follows the title, so it moves up under a short title |
| `{{ detail_1 }}` | the page's `tagline` (a post's or an event's default: its date in words) |
| `{{ detail_2 }}` | the page's `share_detail:`, else an event's `place`, else a post's `author` |
| `{{ tags }}` | SVG: the post's `tag`, then the page's `share_tags:` (comma-separated), each in an outlined box, laid out from (0, 0) - place them with a `transform` on the enclosing group, which also gives the font and, as `color`, the colour (boxes and text draw in `currentColor`) |

Text is fitted by **character count**, so the template is meant for a
monospace face: lines break at spaces, a word longer than a line is
split, and the last line that does not fit is cut, with `...` (three
dots, never the ellipsis character). Each detail line is cut at
`[share] detail_columns`. Tags go left to right, as many on a line as
`tag_room` pixels hold (a box is its characters times `tag_advance`, plus
`tag_padding` on each side; `tag_gap` between two), on up to `tag_lines`
lines - a second line only when the title leaves its second line empty,
the room `{{ title_shift }}` gives back. A tag longer than a line is cut
with `...`; a tag that no longer fits is left out, with the ones after
it: a card never overflows. Set the columns in `theme.toml` for the
font sizes the template uses (at 0.6 em per character, a 60px title in
832px holds 23).

| `[share]` key | Default | |
|---|---|---|
| `pages` | `true` | a site sets `false` to show `share.png` on every page |
| `title_columns` | `23` | characters per title line |
| `title_lines` | `2` | title lines |
| `title_line_height` | `68` | the step of `{{ title_shift }}` |
| `detail_columns` | `48` | characters per detail line |
| `tag_advance` | `14.4` | px per character of a tag |
| `tag_padding` | `16` | px inside a box, on each side of its text |
| `tag_height` | `48` | px, a box |
| `tag_baseline` | `33` | px from a box's top to its text's baseline |
| `tag_gap` | `14` | px between two boxes |
| `tag_line_gap` | `12` | px between two lines of boxes |
| `tag_lines` | `2` | lines of boxes, at most |
| `tag_room` | `830` | px, the width of a line of boxes |

The cards are drawn by the rasteriser of `share.png` (`rsvg-convert`,
with the theme's fonts), and cached like diagrams: in memory for
`--watch`, in `TILDER_CACHE` (else a folder of the system's temporary
directory), and in the previous output. Without a rasteriser, every page
shows the site's card.

---

## Diagrams

A ```` ```mermaid ```` block is drawn by the Mermaid CLI into an SVG file
(`docs/markdown.md`, "Diagrams"), shown as `<img>` in a `.figure`, like
an image. The theme gives its look, in three places:

- **`mermaid.json`**: Mermaid's configuration - `theme`, `look`,
  `themeVariables`, the settings of each kind of diagram. Write a colour
  as `var(--token)`, a custom property of `style.css` whose value is a
  `#hex` colour: the build replaces it with the token's light value,
  since Mermaid computes with real colours. A token `style.css` lacks
  stops the build. Without the file, Mermaid's own defaults.
- **`style.css`**: the palette. Each colour of the drawing that is the
  light value of a token becomes `var(--token)` again, and the SVG
  defines those tokens, light and under `@media (prefers-color-scheme:
  dark)` with the dark values: the drawing follows the reader's scheme,
  inside its `<img>`, as the page does. When two tokens share a light
  value, the first in `style.css` wins.
- **`theme.toml`, `[diagrams]`**:

  | Key | Default | |
  |---|---|---|
  | `fold` | `{}` | Mermaid's own colours, which no `themeVariables` reaches, mapped to tokens: `{ "#ECECFF" = "--bg" }` |
  | `sharp` | `true` | square corners: every `rx` and `ry` set to 0 |
  | `shadow` | `false` | `true` keeps Mermaid's drop shadows; `false` drops its filters |

  A colour that is neither a token's nor folded is left as it is, and
  the build warns once, naming it: fold it.

The labels are measured with the theme's `fonts/` (decompressed to TTF,
as for `share.png`), so a box fits its text in the theme's typeface;
inside an `<img>` the SVG cannot load the page's web fonts, so name a
fallback in Mermaid's `fontFamily`. `starter/theme/mermaid.json` and its
`[diagrams]` are a complete example.

---

## Checking a theme

```sh
python3 builder/build.py --check              # 0: fine, 1: a check failed
python3 builder/build.py --check --markdown   # and the contrast table, as Markdown
```

`--check` builds nothing: it checks the site's theme against the tilder
that runs it, prints one `error:` line per problem, and one summary line
per check.

- **classes**: every class of the table above appears in a selector of
  `style.css` (the site's `assets/style.css` if it has one), comments
  aside; `.toc` does not count for `.toc-label`. Without `style.css`,
  skipped with a note.
- **contrast**: each pair the theme declares reaches the minimum WCAG 2
  contrast ratio, in the light scheme (the custom properties of `:root`)
  and in the dark one (those of the `:root` inside `@media
  (prefers-color-scheme: dark)`, over the light ones). Only a rule whose
  selector is exactly `:root` counts: not `:root, .dark`, not one inside
  `@supports` or `@layer`. A value used by a pair must be a hex colour (`#rgb`,
  `#rrggbb`), else it is an error naming the property. Without pairs,
  skipped.

A theme declares both in its `theme.toml`, under `[check]`:

```toml
[check]
unstyled = ["icon"]                              # classes left unstyled on purpose
contrast = [["--text", "--bg"], ["--muted", "--bg"]]
contrast_min = 4.5                               # WCAG AA for text; the default
```

With `--markdown`, the contrast table goes to standard output, for the
theme's README, and the summary lines to standard error. The starter
passes both checks; `starter/theme/theme.toml` declares its pairs.
