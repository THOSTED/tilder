# man-page site builder

A static site generator for websites that read like a man page. Markdown
in, two outputs out: HTML for browsers, and plain ASCII for terminals
(`curl example.org`). Python standard library only; one optional tool,
`rsvg-convert`, to draw the icons and the link preview.

It knows nothing of any particular site: every name, word and value comes
from the project's `content/site.toml`. Copy this `builder/` folder into
your project, or keep it as a git submodule.

---

## What it gives you

- Pages from `content/*.md`, in a small Markdown dialect with man-page
  sections, entries, callouts, tables, task lists, highlighted code
  (`docs/markdown.md`).
- A text mirror of every page, 75 columns, plain and ANSI-coloured, for
  terminals and braille displays.
- Blog posts and events as dated files or folders, their lists, RSS feeds
  and an iCalendar feed; members with a searchable grid.
- SEO: one `<h1>` per page, canonical URLs, Open Graph and Twitter Card,
  JSON-LD structured data, `sitemap.xml`, `robots.txt`, build-time checks
  (`docs/seo.md`).
- Accessibility: WCAG 2.2 AA contrast in both themes, screen-reader
  details, keyboard, reduced motion, forced colours.
- Icons (`favicon.ico`, PNGs) and a 1200x630 share image, drawn at every
  build from your `assets/logo.svg`. Nothing generated is committed.
- A watch mode that rebuilds on every change, and at midnight.

## Layout of a project

```
my-site/
  content/
    site.toml         your settings and words (see defaults.toml)
    index.md          the landing page
    404.md
    blog/             optional: YYYY-MM-DD-slug.md, or YYYY-MM-DD-slug/index.md with images
    events/           optional, the same way
    members/          optional: one <slug>.md per member
  assets/
    logo.svg          the source of every icon and of the share image
    ...               anything else is served as-is; a file named like a
                      theme file (style.css, layout.html, share.svg...)
                      replaces it
  builder/            this folder
```

Start from the starter site:

```sh
cp -r builder/starter/* my-site/     # content/ and assets/
cd my-site
python3 builder/build.py             # -> public/
```

## Running it

```sh
python3 builder/build.py                    # build once into public/
python3 builder/build.py --watch            # rebuild on every change
python3 builder/build.py --root DIR         # build another project
python3 builder/build.py --out DIR          # write somewhere else
```

`--root` defaults to the current directory when it has a `content/` folder,
else to the folder that holds `builder/`.

With Docker, `builder/Dockerfile` is Python plus `rsvg-convert` and
`woff2_decompress`: the icons and the share image then use the theme's own
font. Without them, the build falls back to ImageMagick, or skips the
images with a warning.

To serve the result, any static server works. `Caddyfile.example` gives
the whole contract, for Caddy: clean URLs, the text mirror served to `curl`
directly, a plain-text host, the CSP (same-origin scripts only), caching
and compression. Copy it next to your compose file and set the hosts
through the environment.

## Configuration

`content/site.toml` is merged over `builder/defaults.toml`, which lists
every key with a comment: the site's name and URL, the man-page header and
footer, the navigation, every label a reader sees (in your language), feed
and calendar texts, how dates are written, SEO limits, colours of the share
image, member categories. The builder holds no user-facing text.

## The theme

`builder/theme/` is the man-page theme: `layout.html` (the page
skeleton), `style.css` (Solarized, one accent), two small scripts
(`code.js`, the copy button; `members.js`, the member search), JetBrains
Mono, and `share.svg` (the link preview template). Replace any of them by
putting a file of the same name in your `assets/`.

## The code

One concern per module; the map is at the top of `build.py`. Everything is
the standard library. `docs/markdown.md` is the format; keep it in step
with `markdown.py`, `page.py` and `text.py`, since every construct is
rendered twice.

## Fonts

`theme/fonts/JetBrainsMono-{Regular,Bold}.woff2` are Latin subsets of
[JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) v2.304, made
with `pyftsubset` (`fonttools`), 60 KB together. For the share image, the
build decompresses them to TTF on the fly (`woff2_decompress`): the
renderer's text shaping does not read WOFF2.

## Why 75 columns

The text mirror targets an 80-column terminal, the default since the VT100
and still what `man` assumes. The 5 spare columns absorb a scrollbar, a
`less` or diff gutter, or an email quote (`> `) without wrapping. The
derivation runs one way: the source keeps its accents and links, the text
folds them.

## Contributing

`AGENTS.md` holds the rules - for agents and humans alike.

## Licence

AGPL-3.0-or-later, like the site it comes from. JetBrains Mono: OFL 1.1
(`theme/fonts/OFL.txt`).
