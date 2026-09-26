# Languages - design

Date: 2026-09-26. Status: approved in conversation, awaiting review of this
document. Implementation plan to follow. Builds on the content-types work
(`2026-09-26-content-types-design.md`), whose §13 named this as the next
step.

---

## 1. Goal

A site may be served in several languages: the default language at the
root, every other declared language under its own prefix (`/en/`). **Every
declared language is a complete tree**: four declared languages give four
whole sites, with the same pages. A page is translated by putting a file
with a language suffix next to it (`about.en.md` next to `about.md`); a
page that is not translated in a language is still served there, with the
content of the default language, or failing that of any language that has
it. Every word of the interface comes from a configuration file per
language.

A site that declares one language, or none, changes by not one byte: the
reference site is the regression test, as before.

### Not in this work

- Detecting the visitor's language (a server may redirect on
  `Accept-Language`; the generator does not).
- Non-Latin scripts in the text mirror: the ASCII fold and the 75-column
  grid assume a Latin alphabet. Documented as a limit.
- One language per host or subdomain.
- Automatic translation of anything.

---

## 2. Vocabulary

- **Language**: a code as written by the site (`fr`, `en`, `pt-br`), the
  value of `site.lang`; not validated against a list, the generator knows
  no language name.
- **Default language**: `site.lang` in `content/site.toml`. Served at the
  root, without prefix.
- **Declared languages**: `site.languages`, a list that must contain the
  default. Only these are generated. Absent, or equal to `[default]`: the
  site is monolingual and nothing below applies.
- **Prefix**: `""` for the default language, `"<lang>/"` for the others.
  Every output of a language sits under its prefix.
- **Content language**: the language of the file actually rendered, which
  differs from the page's language when the page is served in fallback.

---

## 3. Files

A page is `<name>.md`, in no particular language, or `<name>.<lang>.md`, in
a declared language. The same for a folder's `index.md` (`index.en.md`)
and for collection items (`2026-01-01-hello.en.md`, `hello/index.en.md`,
`members/ada-lovelace.en.md`). The language suffix is removed before the
dated slug is recognised: `2026-01-01-hello.en.md` is the item
`2026-01-01-hello`.

### Resolution

To render a page in language L, the build takes, in order:

1. `<name>.L.md`;
2. `<name>.<default>.md`;
3. `<name>.md`;
4. `<name>.<other>.md`, for the other declared languages in the order of
   `site.languages`.

The first that exists wins; its language is the page's **content
language** (the file's suffix, or the default language for a file without
one). A page therefore exists in every declared language as soon as it
exists in any form: a `legal.en.md` alone gives `/legal`, `/en/legal` and
`/de/legal`, the first and last with the English content.

### Configuration layers

```
defaults.toml  <  theme/theme.toml  <  theme/theme.L.toml  <  content/site.toml  <  content/site.L.toml
```

`content/site.L.toml` overrides key by key, tables of tables (`[[nav]]`)
replaced as a whole. It usually sets `[site] lang`, `locale`, `manual`,
`title_suffix`, `[labels]`, `[[nav]]`, the words of each
`[collections.<name>]`, `[dates]`, `[share] image_alt` and `card`,
`[calendar]`. A declared language without a `site.L.toml` is allowed: it
has the default language's words (a site that starts translating). The
theme's `theme.L.toml` sits between `theme.toml` and the site's files.

```toml
# content/site.toml
[site]
lang = "fr"
languages = ["fr", "en"]

[languages]           # names shown by {{ languages }}; the code when absent
fr = "Français"
en = "English"
```

### Errors

One shape, gathered per phase, as the content-types work set:

- `content/about.xx.md: "xx" is not a declared language. Declared: fr, en
  ([site] languages in content/site.toml)`;
- `content/site.xx.toml: "xx" is not a declared language. ...`;
- `content/site.toml: [site] languages does not contain the default
  language "fr". Add it, or change [site] lang`;
- `content/site.en.toml: [site] lang is "de", not "en". A language's file
  sets its own lang, or leaves it out`.

---

## 4. URLs, links, navigation, wordmark, text mirror

**Prefix.** Pages (`en/events.html`), the text mirror (`txt/en/events.txt`,
`ansi/en/...`), the feeds (`en/blog/feed.xml`) and `404.html` (one per
language) take the prefix. The sitemap, `robots.txt`, the manifest, the
icons and the calendar (§5) do not.

**Links in content** are written from the site root, as today
(`[events](events)`), and resolve **from the root of the language**: in
`/en/about`, `events` is `/en/events`. A writer never knows which language
their page will be served in, and a fallback page stays inside its
language. A link that starts with `/` is taken from the site root, without
prefix: `[en français](/events)` from an English page. That is the one new
piece of syntax. Absolute links and anchors are unchanged. Links written
by the generator (cards, nav, feeds, `to_top`, the wordmark) follow the same
rule.

**Navigation** comes from the language's configuration; entries are
resolved in the language, the current one marked as today.

**Wordmark.** `~/<site>/en/blog/hello` in English: the language segment
links to the language's landing page and reads as its code; the default
language shows no segment. Screen readers hear "site, en, blog, hello".

**Language switcher.** A new layout placeholder, `{{ languages }}`: every
declared language, each a link to this page's sibling with `hreflang` and
`lang` attributes, the current one marked
`aria-current="page"`, named from `[languages]` or by its code:

```html
<nav class="languages" aria-label="{{ labels.languages }}">
	<a href="../about" hreflang="fr" lang="fr" aria-current="page">Français</a>
	<a href="about" hreflang="en" lang="en">English</a>
</nav>
```

Empty in a monolingual site. A layout may omit it: an absent placeholder
is not an error, only an unknown one is. `labels.languages` is a new
default ("Languages"). The theme styles `.languages`; the starter shows it.

**Text mirror.** Same tree under `txt/L/` and `ansi/L/`. In a multilingual
site, one line after the header rule, `LANGUAGES: fr en`, so
`curl example.org/about` says that `/en/about` exists. Nothing in a
monolingual site.

---

## 5. `<head>`, structured data, sitemap, feeds

**Resolution table.** Before any rendering, the build computes, for every
page path (without prefix) and every declared language, the source file
chosen and its content language. Everything below reads it.

**Per page:**
- `<link rel="canonical">`: the page's own URL, prefix included. A fallback
  page is a page of its own: no cross-language canonical.
- `<link rel="alternate" hreflang="L" href="...">` for every declared
  language, itself included, plus `hreflang="x-default"` to the default
  language's version. Absent in a monolingual site.
- `<html lang>` stays `site.lang` of the current language: the language of
  the interface. A new placeholder `{{ content_lang }}` gives the content
  language, for `<main id="contenu" lang="{{ content_lang }}">`; it equals
  `site.lang` when the page is not a fallback, so existing layouts stay
  valid and unchanged output stays unchanged.
- `og:locale` of the current language; `og:locale:alternate` for each
  sibling. `<link rel="alternate" type="application/rss+xml">` points at
  the language's feeds.

**Structured data.** `inLanguage` is the content language on the page node
and on `WebSite`. `Organization` and `WebSite` keep one `@id` per site, at
the root. The `BreadcrumbList` follows the visible wordmark: the
language's landing page, the section, the page.

**Sitemap.** One `sitemap.xml`, each URL carrying `xhtml:link
rel="alternate" hreflang` entries for its siblings and `x-default`;
`sitemap.txt` lists every URL. `noindex` pages are left out as today.

**Feeds.** One RSS per language and collection, under the prefix, with the
language's titles and `<language>`, listing the items as resolved in that
language (an untranslated post appears with its fallback text, so every
feed lists the same items). The **calendar is produced once**, in the
default language, at the root: a calendar has no interface language and
subscribing to two would show every event twice. The other languages'
pages link to it.

**Dates and words.** `human_date` reads `[dates]` of the current language,
by construction of the per-language pass.

**Checks.** The SEO checks run per language; a duplicate description
between `/about` and `/en/about` served in fallback is not reported (same
content, different languages, intended).

---

## 6. Mechanics

**`src/languages.py`, new**, holds everything the feature adds: the
declared languages and the default (`declared()`, `default()`), the suffix
split (`split("about.en.md") -> ("about", "en")`), the resolution of one
page for one language (`resolve(folder, name, lang)`), the resolution
table (`table()`), the siblings of a page (`siblings(path)`, one per
declared language) and the
prefix of a language (`prefix(lang)`). In a monolingual site every
function answers "one language, no prefix, no siblings".

**What changes elsewhere.**
- `config.py`: `load_config(lang=None)` adds the `theme.L.toml` and
  `site.L.toml` layers; `STATE["lang"]`, `STATE["content_lang"]` (per
  page) and `STATE["prefix"]` are what one pass shares.
- `build.py`: `build()` computes the table once, then runs one pass per
  declared language producing that language's pages, mirror and feeds
  under the prefix; then the sitemap, the calendar and `robots.txt` once.
  The start-up summary gains a line: `languages: fr (default), en`.
- `paths.py`: `page_path` and `txt_name` take the prefix; `relative()`
  resolves from the language root, and a `/`-leading target from the site
  root; `rendered()` recognises language suffixes.
- `contenttypes.py`: `load_items` resolves each item in the current
  language with the same fallback; the dated slug is recognised without
  suffix; an item's `path` carries the prefix.
- `page.py`: `{{ languages }}`, `{{ content_lang }}`, the language segment
  of the wordmark, links resolved in the language.
- `seo.py`: `hreflang`, `og:locale:alternate`, `inLanguage`, the sitemap
  with `xhtml:link`.
- `text.py`: the `LANGUAGES:` line in multilingual sites.
- `feeds.py`: unchanged; it reads the current configuration. Only the
  calendar's path is produced once.

**Server.** `examples/Caddyfile`: the `404.html` of the requested language
prefix (`/fr/*` → `/fr/404.html`), and the text-mirror rewrite checked with
a prefix (`try_files {path}.txt {path} {path}/index.txt` already follows
it). Documented as optional, off by default: redirecting an undeclared
two-letter prefix to the root. By default such a URL is a 404.

---

## 7. Documentation

- `docs/languages.md`, **new**: the file convention, the fallback order,
  the configuration layers, the two placeholders, links across languages,
  the sitemap and feeds, the text mirror, the Caddy rules, with the starter
  as the example.
- The starter declares `languages = ["en", "fr"]`, gains `site.fr.toml`
  and two `.fr.md` pages (its landing page and one post), so the feature is
  visible on `python3 build.py --root starter`; English stays its default.
- `docs/theme.md` (the two placeholders, `.languages`), `docs/markdown.md`
  (suffixes, `/`-leading links), `README.md`, `AGENTS.md` (§2: the
  generator knows no language name; every word of a language comes from
  `site.L.toml`).

---

## 8. Acceptance

1. **Byte-identical output** for the reference site, monolingual, before
   and after (rasters excluded on this machine).
2. **The starter, bilingual**: `/` and `/fr/`, every page in both
   languages, crossed `hreflang`, one sitemap with `xhtml:link`, two RSS
   feeds, one calendar; an untranslated page served in fallback with
   `<main lang="en">` and `<html lang="fr">`.
3. **Links**: `[x](events)` in a French page points at `/fr/events`;
   `[x](/events)` at `/events`; a card in `/fr/blog/` links to
   `/fr/blog/<slug>`.
4. **Text mirror**: `curl site/fr/events` is the French mirror; the
   `LANGUAGES:` line appears; nothing of the kind in a monolingual site.
5. **Every error of §3** gives one line and exit status 1.
6. **AGENTS.md §9 checks** pass on the bilingual starter build (75 columns,
   one `<h1>`, no foreign request, `ansi` equals `txt`).
7. **Tests**: the fixture site gains a second language and the suite
   covers resolution order, prefixes, links, `hreflang`, the sitemap, the
   feeds, the calendar produced once, the placeholders, the errors.

---

## 9. Later

- A per-language `share.png` (the card's lines already come from the
  language's `[share]`; the image is drawn once today).
- A `hreflang` sitemap index if a site grows past one sitemap.
- Redirecting on `Accept-Language`, in the example Caddyfile, if a site
  asks for it.
