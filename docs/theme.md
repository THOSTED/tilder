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

Everything in `theme/` but `layout.html`, `share.svg` and `icons/` is
copied to the site as it is.

---

## `layout.html`

`{{ name }}` is replaced at build time. An unknown name stops the build.

| Placeholder | Value |
|---|---|
| `{{ title }}` | the `<title>`: the page's title and `site.title_suffix` |
| `{{ page.<key> }}` | a front-matter value: `page.description`, `page.man`, `page.tagline`... |
| `{{ <section>.<key> }}` | a `site.toml` value: `site.lang`, `site.manual`, `footer.left`, `labels.skip`... |
| `{{ root }}` | the relative path to the site root (`./`, `../`), for assets and links |
| `{{ canonical }}` | the page's absolute URL |
| `{{ feeds }}` | `<link rel="alternate">` for the page's RSS feeds |
| `{{ head }}` | robots, author, Open Graph, Twitter Card, JSON-LD |
| `{{ brand }}` | the `<h1>`: the wordmark as a path, `~/<site>/<section>/<title>` |
| `{{ nav }}` | the navigation links, the current one marked `aria-current="page"` |
| `{{ body }}` | the sections of the page |
| `{{ script }}` | the `<script>` tags the page needs, if the theme has the files |

Values are HTML-escaped, except the ones the builder computes (`brand`,
`nav`, `feeds`, `head`, `body`, `script`). The starter's `layout.html` is a
complete example.

The layout must keep: `lang="{{ site.lang }}"`, one `{{ brand }}` (it is
the page's only `<h1>`), a `<main id="contenu">` or equivalent target for
the skip link, and `<link rel="canonical">`.

---

## The HTML the builder writes

A theme styles these. The starter's `style.css` covers them all.

| Class | What |
|---|---|
| `.sr-only` | **required**: text for screen readers only (visually hidden) |
| `.wordmark`, `.tilde`, `.slash`, `.here`, `.cursor` | the `<h1>`: `~/`, separators, the page's own segment, a cursor |
| `.nav`, `.sep` | navigation and its separators |
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
