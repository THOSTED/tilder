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
   neutral default and a comment. `grep -rni` for a real site's name,
   domain or organisation in this repository must find nothing.
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
5. **The theme is overridable, not forkable.** A site replaces a theme
   file by putting one with the same name in its `assets/`. Keep theme
   files self-contained so that works.
6. **No third-party request** from a built page: no CDN, no font service,
   no analytics, no iframe, no remote image. Links to other sites are fine;
   loading from them is not.
7. **No server-side code, no forms, no cookies, no tracking.** The output is
   static files.

---

## 3. Layout

```
build.py        the driver and CLI: once, --watch, --out DIR, --root DIR
config.py       paths, site.toml over defaults.toml, what a build shares
markdown.py     Markdown -> a tree of nodes
inline.py       inline markup, for both outputs (and the link rules)
page.py         the tree -> HTML, inside theme/layout.html
text.py         the tree -> the marked text mirror (75 columns)
ansify.py       the marked text -> its coloured twin
highlight.py    syntax highlighting of code blocks
members.py      members: the {members} grid, a card on each page, profiles
dated.py        blog posts and events: lists, cards, dates
seo.py          titles, meta, JSON-LD, sitemaps, robots.txt, SEO checks
feeds.py        RSS and iCalendar
icons.py        icons and share.png from the site's assets/logo.svg
images.py       image sizes, rasterising, .ico packing
paths.py, fold.py, watch.py
defaults.toml   every key of site.toml, with neutral defaults
theme/          layout.html, style.css, code.js, members.js, fonts/, icons/, share.svg
docs/           markdown.md, seo.md
starter/        a minimal site: content/ and assets/, to copy
Caddyfile.example  the server contract, for Caddy
Dockerfile      Python + rsvg-convert + woff2_decompress
```

One concern per module; the map is repeated at the top of `build.py`. A
module name must not shadow the standard library (`html`, `site`,
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

## 5. The theme

### Grammar
A man page: section names in small caps in the left gutter, content
indented to the right, a header rule (`<man>  <manual>  <man>`) and a
footer rule. Not cards, not hero banners, not full-bleed sections.

### Colours - Solarized
CSS variables on `:root`, redefined for `prefers-color-scheme: dark`, for
`prefers-contrast: more` and for print. Never hard-code a colour in a rule.

| Role | Variable | Light | Dark |
|---|---|---|---|
| Background | `--bg` | `#FDF6E3` | `#002B36` |
| Inset background | `--bg-inset` | `#EEE8D5` | `#073642` |
| Text | `--fg` | `#073642` | `#B6C2C2` |
| Muted text | `--fg-muted` | `#506C75` | `#8C9B9B` |
| Faint (decoration only) | `--fg-faint` | `#93A1A1` | `#586E75` |
| Rules | `--rule` | `#DED7C3` | `#0E4653` |
| Accent | `--accent` | `#0F6E68` | `#3EA89E` |
| Accent background | `--accent-bg` | `#D9EBE8` | `#05313B` |
| Warning | `--warn` | `#A5501A` | `#CB8B4B` |
| Error | `--error` | `#B3261E` | `#EF7A74` |

**One accent.** `--warn` and `--error` are status colours (callouts, a
full mentor, removed diff lines), never decoration. Syntax highlighting
stays inside this palette: weight for keywords, the accent for strings, the
muted tone for comments.

### Shapes and motion
- Sharp corners (2px radius at most), 1px rules, no shadow, no gradient.
  The site's own logo may be the only curve.
- Single column, `--measure: 68ch`, gutter `--gutter: 13ch`, left-aligned.
- One motion: the wordmark's cursor blinks four times, then stays (and
  again on hover); never under `prefers-reduced-motion`.
- `{grid}` lays entries out as cards: 1px rule, square corners, no shadow.
  A card whose title is a link is clickable as a whole (a stretched link).
- The only icons are the brand logos of profile links (`theme/icons/`,
  Simple Icons, CC0), single-colour, inline, named for screen readers.

### The wordmark and the `<h1>`
The wordmark is `~/<site name>`, lowercase by CSS. It is the page's single
`<h1>`, as a path: `~/<site>` on the landing page, `~/<site>/<section>/<title>`
elsewhere, each segment linking to its page and named like it (`name:`).

---

## 6. Scripts

Two, and a new one follows the same rules:

- `members.js` (search and filter on a `{members}` page), `code.js` (copy
  button on code blocks); the build adds each `<script>` tag only where it
  serves.
- ES5, no dependency, a same-origin file - never inline, never a CDN.
- Progressive enhancement: the page is complete without it; the script
  creates its own controls.
- No network, no storage, no cookie. No text of its own: wording arrives
  from `site.toml` through `data-*` attributes.
- The CSP (`Caddyfile.example`) grants `script-src 'self'` and nothing
  more. JSON-LD (`<script type="application/ld+json">`) is inert data, the
  only inline `<script>` allowed.

---

## 7. Accessibility - WCAG 2.2 AA

- **Contrast**: every text colour reaches 4.5:1 on `--bg`, `--bg-inset` and
  `--accent-bg`, in both themes. `--fg-faint` is never used for text. After
  any palette change, measure every text colour on every background again.
- **Never colour alone**: every coloured meaning has a word or a shape.
- One `<h1>`; `<h2>` for sections, `<h3>` for entries.
- Hidden from screen readers: the header rule, the `~/` of the wordmark,
  the `↗` of external links (replaced by `labels.external`, plus
  `labels.new_tab` when the link opens a tab).
- Alt text required on images (the build warns); scrollable code and
  tables focusable; targets at least 24px high; sizes in `rem`.
- `prefers-contrast: more` and `forced-colors` handled: wherever a
  background carries meaning, keep a border or a system colour.

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
# 1. The output does not change unless the change meant it to. Build the
#    site you work with before and after, and compare.
python3 builder/build.py --out /tmp/before   # before the change
python3 builder/build.py --out /tmp/after    # after
diff -r /tmp/before /tmp/after

# 2. The starter builds from nothing, with the defaults only.
cp -r builder/starter /tmp/starter
python3 builder/build.py --root /tmp/starter --out /tmp/starter-out

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
- Change the palette, the typefaces or the man-page grammar; round corners;
  add shadows or decorative motion.
- Use `--fg-faint` for text, or carry a meaning by colour alone.
- Commit generated files.
- Write anything in this repository in a language other than English.
