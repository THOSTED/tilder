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
texts. The brand is not translated: `site.fr.toml` normally keeps
`title_suffix` with the same name as `site.toml` (the starter shows it,
with a comment saying so). Layers, the last winning:

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

A suffix that names no declared language stops the build, wherever it
appears under `content/`: a page (`about.xx.md`) or a `site.xx.toml`. The
same rule applies to `theme.xx.toml` under `theme/`. A typo must not
silently become a page, or a configuration file, that the build ignores.
A stem like `v1.2` or `notes.final` is a plain name, but a stem ending in
a two- or three-letter word - `readme.txt.md` - is read as a language
suffix.

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

Configuration files (`site.toml`, `site.<lang>.toml`, `theme.toml`,
`theme.<lang>.toml`) are read at build time and never served.

Every page carries `<link rel="alternate" hreflang>` for every language and
`x-default`; `og:locale:alternate`. `inLanguage` is the content language,
on the page's own node; `WebSite` keeps the language of the interface - it
is one node per site, not per page. The sitemap lists every URL with its
`xhtml:link` alternates. The calendar is written once: a calendar has no
interface language, and two would show every event twice.

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
