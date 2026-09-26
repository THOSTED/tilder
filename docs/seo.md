# SEO

What the build and the server do for search engines, what contributors
control, and what is left outside the repository.

---

## What contributors control

Everything a search engine shows comes from a page's front matter:

| Field | Becomes | Aim for |
|---|---|---|
| `title` | `<title>` (with `site.title_suffix`), `<h1>`, `og:title` | under 60 characters with the suffix; says what the page is |
| `name` | the page's segment in the `<h1>` path, `~/<site>/.../<name>`; a parent page's `name` also names its segment on child pages | when the title is too long for the path |
| `description` | `<meta name="description">`, `og:description`, feeds | 50-160 characters, one sentence, specific |
| `image` | the share preview (`og:image`) | 1200x630 PNG or JPEG, relative to the page's folder |
| `image_alt` | `og:image:alt` | what the image shows |
| `updated` | `<lastmod>` in `sitemap.xml`, `dateModified` of a post | set it when a page changes in substance |
| `robots` | `<meta name="robots">` | `noindex` for a page that must stay out of results |

The build **warns** (`seo: ...`) when a title is too long, a description is
out of bounds, or two pages share a title or a description. Fix the
warning: a truncated title or a duplicate description costs clicks.

Write for people first: a title that says what the page is, a description
that says why to click. Name what the site is about - its subject, its
city, its audience - where it is true, not everywhere.

---

## What the build does

- **One `<h1>` per page**: the wordmark, as a path - `~/<site>` on the
  landing page, `~/<site>/<title>` elsewhere. Screen readers and search
  engines read "<site>, <title>". Sections are `<h2>`, entries `<h3>`.
- **Canonical URL** on every page, on the apex, without `.html`.
- **Structured data** (JSON-LD, `seo.py`): `Organization` and `WebSite` on
  every page, plus:
  - `BlogPosting` for posts - headline, dates, author, image;
  - `Event` for events - dates, place, geo when `lat`/`lon` are given,
    status, organiser: what search engines use for event results;
  - `ProfilePage` + `Person` for members;
  - `BreadcrumbList` (accueil > section > page).
- **Sharing**: Open Graph and Twitter Card, with a 1200x630 image
  (`share.png`, drawn at every build, `summary_large_image`).
- **`sitemap.xml`** with `<lastmod>`, and `sitemap.txt`. `robots.txt` points
  to `sitemap.xml`. The 404 and `noindex` pages are left out.
- **Feeds**: RSS for posts and events, iCalendar for events.
- **Performance**: the main font is preloaded; images carry their size, so
  the page does not jump.

## What the server does (`Caddyfile`)

- `zstd` / `gzip` compression.
- Cache headers: fonts a year, other assets a day, pages five minutes.
- One URL per page: `www` -> apex, `.html` -> clean URL, `/index` -> `/`,
  `/blog` -> `/blog/` (301).
- The text mirrors (`/txt/`, `/ansi/`, the plain-text host) are `noindex` and
  disallowed in `robots.txt`: they duplicate the pages.
- A real 404 status for missing pages.

---

## Outside the repository

- Register the site in **Google Search Console** and **Bing Webmaster
  Tools**, submit `https://<your site>/sitemap.xml`, and watch coverage and
  structured-data reports there.
- Check a page's structured data with Google's Rich Results Test and the
  Schema.org validator after changing `seo.py`.
- Links from elsewhere (event listings, partners' sites, directories)
  matter more than anything above; list the events there.
