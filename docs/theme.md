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
| `layouts/<name>.html` | optional | a layout for the pages of a type (`docs/types.md`), or asked for by `layout:` in a page's front matter; same placeholders as `layout.html` |
| `types/<name>.py` | optional | a content type the theme adds, or a built-in one it replaces (`docs/types.md`) |
| `theme.toml` | optional | the theme's own configuration values, merged under the site's `site.toml`: for now the `[share]` colours |
| `theme.<lang>.toml` | optional | `theme.toml`'s per-language twin, between it and the site's `site.toml` (`docs/languages.md`); ignored when the site does not declare `<lang>`, so a theme may ship languages a site lacks |

Everything in `theme/` but `layout.html`, `layouts/`, `share.svg`,
`icons/`, `types/` and `theme.toml` (and its `theme.<lang>.toml` twins) is
copied to the site as it is. Like `site.toml`, `theme.toml` and its twins
are read at build time and never served. A theme kept in its own repository may carry a `README.md`, a `LICENSE` and git files (`.git`, `.gitignore`): they are never served either.

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
| `{{ collection_nav }}` | the items of the page's collection, in the type's order, grouped by their `group:`, the current one marked `aria-current="page"`; on the collection's own page (`<dir>/index.md` or `<dir>.md`) the same list, nothing marked; empty elsewhere (`docs/types.md`) |
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

| Class | What |
|---|---|
| `.sr-only` | **required**: text for screen readers only (visually hidden) |
| `.wordmark`, `.tilde`, `.slash`, `.here`, `.cursor` | the `<h1>`: `~/`, separators, the page's own segment, a cursor |
| `.nav`, `.sep` | navigation and its separators |
| `.languages` | the language switcher (`<nav class="languages">`, `docs/languages.md`) |
| `.collection-nav`, `.collection-group`, `.collection-group-label` | the collection sidebar (`<nav class="collection-nav">`), a group (`<li>`) and its label (`<span>`, not a heading) |
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
| `.toc`, `.toc-label` | a `[TOC]`, a `<details>` in a `<nav>` |
| `.profiles`, `.icon` | a member's profile links and their logos |
| `u.u` | `++underlined++` |

Accessibility the theme is responsible for: contrast (4.5:1 for text), a
visible focus outline, `.sr-only`, reduced motion. The builder takes care
of the markup: headings, alt text, labels, `aria-*`.
