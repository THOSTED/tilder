# AGENTS.md - man-page site builder

Instructions for any coding agent working on this generator. They override
default habits. When in doubt, do less and ask.

This repository is **the generator only**. It is used by sites that keep it
in a `builder/` folder (a git submodule) next to their `content/` and
`assets/`. Whatever a site says, shows or decides lives in that site's
repository - never here. Everything in this repository is **English**:
code, comments, docs, commit messages, defaults.

---

## 1. What this is

A static site generator for websites that read like a man page. Markdown
in; out, for every page, **two renderings**: HTML for browsers, and plain
ASCII for terminals (`curl example.org`), with a coloured twin. Plus the
feeds, the sitemaps, `robots.txt`, the web manifest, the icons and the
share image. `README.md` is the user's manual; `docs/markdown.md` is the
content format; `docs/seo.md` is what the build does for search engines.

---

## 2. Principles - non-negotiable

1. **The builder only builds.** It holds no user-facing text and no
   site-wide value: no name, no URL, no date, no label, no language. Every
   such value comes from the site's `content/site.toml`, merged over
   `defaults.toml`. A new key goes in `defaults.toml` with an English,
   neutral default and a comment. A key that belongs to one content type
   goes in that type's `DEFAULTS` (`types/<type>.py`), English and neutral
   too. `grep -rni` for a real site's name, domain or organisation in this
   repository must find nothing. The generator knows no language name:
   every word of a language comes from the site's `site.<lang>.toml`; the
   starter's French files are the feature's example, the one place in this
   repository in another language.
2. **Python's standard library only.** No `pip install`, no npm, no
   framework, no preprocessor. The only outside tools are optional and used
   for images: `rsvg-convert` and `woff2_decompress` (the `Dockerfile` has
   them), else ImageMagick, else the images are skipped with a warning.
3. **Nothing generated is committed**, here or in a site: pages, mirrors,
   feeds, icons, `share.png` are made at every build.
4. **Two renderings per construct.** A Markdown construct is not done until
   it renders in HTML **and** in text, is documented in `docs/markdown.md`,
   and is shown in the starter or the site's showcase. The text rendering
   is not an afterthought: it is half the product.
5. **The builder has no theme.** A site brings its own, in `theme/`
   (`docs/theme.md`); `starter/theme/` is a minimal one to copy. The
   builder writes semantic HTML with stable class names - the contract -
   and never depends on how a theme draws them. Every theme file but
   `layout.html` is optional, and the build degrades cleanly without it.
6. **No third-party request** from a built page: no CDN, no font service,
   no analytics, no iframe, no remote image. Links to other sites are fine;
   loading from them is not.
7. **No server-side code, no forms, no cookies, no tracking.** The output is
   static files.

---

## 3. Layout

```
build.py        the entry point: `python3 builder/build.py`, hands over to src/
defaults.toml   every key of site.toml, with neutral defaults
src/
  build.py        the driver and CLI: once, --watch, --out DIR, --root DIR
  config.py       paths, site.toml over defaults.toml, what a build shares
  languages.py    the declared languages, site.<lang>.toml, the fallback that completes every tree
  markdown.py     Markdown -> a tree of nodes
  inline.py       inline markup, for both outputs (and the link rules)
  page.py         the tree -> HTML, inside the site's theme/layout.html
  text.py         the tree -> the marked text mirror (75 columns)
  ansify.py       the marked text -> its coloured twin
  highlight.py    syntax highlighting of code blocks
  contenttypes.py the types (types/, theme/types/), collections, items, lists
  report.py       errors and warnings, one shape
  dates.py        dates in words, from [dates]
  seo.py          titles, meta, JSON-LD, sitemaps, robots.txt, SEO checks
  feeds.py        RSS and iCalendar
  icons.py        icons and share.png from the site's assets/logo.svg
  images.py       image sizes, rasterising, .ico packing
  paths.py, fold.py, watch.py
types/          the built-in content types, one module each - no
                `__init__.py`, ever: the folder must not become a package
docs/           markdown.md (the format), theme.md (the theme contract),
                types.md (the content-type contract), seo.md, screenshots/
starter/        a minimal site to copy: content/, assets/, theme/ (a minimal theme)
examples/       Caddyfile, compose.yaml: serving a site
tests/          the suite: `python3 -m unittest discover -s tests -t . -v`
Dockerfile      Python + rsvg-convert + woff2_decompress
```

The root holds what a visitor looks for; code goes in `src/`. One concern
per module; the map is repeated at the top of `src/build.py`. A module
name must not shadow the standard library (`html`, `site`,
`collections`...).

---

## 4. The text mirror

- **75 columns**, always, code included (a long code line is continued
  after a `\`). 80 is the default terminal; 75 leaves room for a scrollbar,
  a `less` or diff gutter, an email quote.
- **ASCII only** in `txt/`: accents and typographic characters are folded
  (`fold.py`). The source keeps them; the derivation runs one way.
- **No escape sequence in `txt/`**: it must survive `curl > file`.
- **Colour follows the markup, never a guess from the words.** `text.py`
  puts invisible marks (control characters `\x02`-`\x07`) around inline
  code, list markers, code-block lines and their frame; `plain()` drops them
  for `txt/`, `ansify.py` turns them into colour for `ansi/`, across line
  breaks. Widths are measured without them (`vlen`, `fill`). Stripped of its
  escapes, `ansi/` must equal `txt/` byte for byte.
- **Code blocks are framed**: `.-- lang ---.` above, `'------'` below; the
  code's lines carry nothing, so they copy clean from a terminal.
- Eight-colour SGR, never a background; one accent (cyan); callouts in their
  kind's colour.

---

## 5. Themes

The contract between the builder and a theme is `docs/theme.md`: the
files a theme may provide, the placeholders of `layout.html`, and every
class the builder writes. Keep it true:

- A new class, a renamed class, a new placeholder: update
  `docs/theme.md` **and** `starter/theme/`, which must style every class the
  builder writes.
- The builder never writes an inline `style`, a colour, or a font: those
  are the theme's.
- The `<h1>` is the wordmark as a path, `~/<site>/<section>/<title>`, each
  segment linking to its page and named like it (`name:`); the builder
  writes it, the theme draws it.
- The starter theme stays minimal: system fonts, no script, no web font,
  readable in light and dark, WCAG AA contrast.

## 6. Scripts

Scripts belong to themes. The builder knows `code.js`, and whatever script
a loaded type names (`SCRIPT`, `docs/types.md`): `members.js` for the
member type. Each tag is added only where it serves and only if the theme
ships the file. A theme's scripts follow these rules:
- ES5, no dependency, a same-origin file - never inline, never a CDN.
- Progressive enhancement: the page is complete without it; the script
  creates its own controls.
- No network, no storage, no cookie. No text of its own: wording arrives
  from `site.toml` through `data-*` attributes.
- The CSP (`examples/Caddyfile`) grants `script-src 'self'` and nothing
  more.
- The builder writes the markup they rely on (`data-*` attributes, class
  names) as documented in `docs/theme.md`. JSON-LD (`<script type="application/ld+json">`) is inert data, the
  only inline `<script>` allowed.

---

## 7. Accessibility - WCAG 2.2 AA

The builder's part - the markup - is below; contrast, focus outlines and
motion are the theme's (`docs/theme.md`), and the starter theme meets them.

- **Never colour alone**: every meaning the builder marks with a class also
  has a word or a shape (a full mentor says "full", callouts carry a
  label, diff lines keep `+`/`-`, task boxes are named).
- One `<h1>`; `<h2>` for sections, `<h3>` for entries.
- Hidden from screen readers: the header rule, the `~/` of the wordmark,
  the `↗` of external links (replaced by `labels.external`, plus
  `labels.new_tab` when the link opens a tab).
- Alt text required on images (the build warns); scrollable code and
  tables focusable (`tabindex`, a named region); links opening a new tab
  announced.

---

## 8. SEO

`seo.py` and `docs/seo.md`: canonical link, description, robots meta, Open
Graph and Twitter Card, JSON-LD (Organization, WebSite, BlogPosting, Event,
ProfilePage, BreadcrumbList), `sitemap.xml` with `lastmod`, `robots.txt`,
and build-time warnings on titles and descriptions. Never drop a page's
canonical link, description or structured data.

---

## 9. Before handing back

```bash
# 0. The test suite must be green.
python3 -m unittest discover -s tests -t .

# 1. The output does not change unless the change meant it to. Build the
#    site you work with before and after, and compare.
python3 builder/build.py --out /tmp/before   # before the change
python3 builder/build.py --out /tmp/after    # after
diff -r /tmp/before /tmp/after

# 2. The starter builds from nothing, with the defaults only. It declares
#    two languages: the build must summarise them, write a fr/ tree, and
#    warn about no seo: issue (a fallback page's duplicate title or
#    description with its own-language original is not one).
cp -r builder/starter /tmp/starter
python3 builder/build.py --root /tmp/starter --out /tmp/starter-out 2>/tmp/starter-seo.log \
  | grep '^languages:'
ls /tmp/starter-out/fr
grep '^seo:' /tmp/starter-seo.log; echo "(expected: nothing)"
#    Every relative link of a prefixed tree resolves to a written file
#    (style.css from fr/blog/... is ../../style.css): the suite's
#    test_every_relative_link_of_the_french_tree_resolves checks it on the
#    bilingual fixture.
grep -o 'href="[^"]*style.css"' /tmp/starter-out/fr/blog/2026-01-01-hello.html

# 3. The text mirror: 75 columns, no escape in txt/, ansi == txt once stripped.
cd /tmp/after
find txt -name '*.txt' -exec awk '{if(length($0)>m)m=length($0)}END{print m}' {} +
grep -rlP '\033' txt/
python3 - <<'PY'
import pathlib, re
for a in pathlib.Path("ansi").rglob("*.txt"):
    t = pathlib.Path("txt") / a.relative_to("ansi")
    assert re.sub(r"\x1b\[[0-9;]*m", "", a.read_text()) == t.read_text(), a
PY

# 4. One <h1> per page; no script but the two files and JSON-LD.
for f in $(find . -name '*.html'); do [ "$(grep -c '<h1[ >]' $f)" = 1 ] || echo "h1: $f"; done
grep -rniE '<script|<form|<input|\son[a-z]+="' --include='*.html' . \
  | grep -vE '<script src="(\.\./)*(members|code)\.js" defer[^>]*></script>|<script type="application/ld\+json">'

# 5. No request to another host.
grep -rnE '(src|srcset)="https?://|url\(["'"'"']?https?://' --include='*.html' --include='*.css' .
```

A refactor must produce a byte-identical site. A feature must change only
what it is about.

---

## 10. Do not, without asking

- Put a site's name, domain, words or decisions in this repository.
- Add a dependency, a build tool, or a framework.
- Add a Markdown construct without its text rendering, its documentation
  and an example.
- Add JavaScript beyond `members.js` and `code.js`, inline a script, or
  give one network or storage access.
- Load anything from another host; embed an iframe.
- Ship a theme, write a style, a colour or a font from the code, or change
  a class name without `docs/theme.md` and `starter/theme/`.
- Carry a meaning by a class alone, without a word or a shape.
- Commit generated files.
- Write anything in this repository in a language other than English.
- Add a content type without its entry in `docs/types.md`, its `DEFAULTS`,
  and a test of its card in HTML and text.
- Put an `__init__.py` in `types/`.

---

## 11. Errors

When the build stops, one line per problem: `error: <file>[:<line>]: <what
is wrong>. <what to do>` (`src/report.py`). Gather the problems of a phase
and report them together. Tracebacks only under `--debug`.
