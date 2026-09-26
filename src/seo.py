"""Search engines and sharing: titles, meta tags, structured data (JSON-LD),
sitemaps, robots.txt, the web manifest, and checks that warn at build time.

Structured data is a <script type="application/ld+json"> element: inert
data that browsers never run and the CSP does not treat as a script. It is
what lets a search engine show an event's date and place, or a post's
author and date, right in its results.
"""

import html as H
import json
import posixpath
import sys

import languages
from config import ASSETS, CFG, CONTENT, STATE, apex, theme_file
from contenttypes import call
from images import image_size
from paths import clean_url


# --- titles ----------------------------------------------------------------

def page_title(meta):
    """The <title>: the page's title, then the site suffix, unless the
    title already names the site."""
    title = meta["title"]
    if CFG["site"]["name"].lower() in title.lower():
        return title
    return title + CFG["site"]["title_suffix"]


def page_heading(meta):
    """The page's name in the <h1> path, ~/<site>/.../<name>: `name:` if set
    (`heading:` is the older spelling), else the title without the site
    suffix."""
    return (meta.get("name") or meta.get("heading")
            or meta["title"].removesuffix(CFG["site"]["title_suffix"]))


def is_landing(meta):
    return meta.get("nav", "-") == ""


def org_ref():
    """The Organization node of the JSON-LD graph, by reference."""
    return {"@id": f"{apex()}/#organization"}


def site_ref():
    """The WebSite node of the JSON-LD graph, by reference."""
    return {"@id": f"{apex()}/#website"}


# --- share image ------------------------------------------------------------

def share_image(meta):
    """(absolute URL, width, height) of the page's preview image: `image:`,
    relative to the page's folder, else [share] image."""
    if meta.get("image"):
        rel = posixpath.normpath(posixpath.join(meta.get("_dir", ""), meta["image"]))
        size = image_size(CONTENT / rel)
    elif theme_file("share.svg").is_file():  # drawn by the build, 1200x630
        rel = CFG["share"]["image"]
        size = image_size(ASSETS / rel) or (1200, 630)
    else:  # no preview template in the theme: the square icon
        rel = CFG["share"]["logo"]
        size = (512, 512)
    return f"{apex()}/{rel}", *(size or (None, None))


# --- <head> ------------------------------------------------------------------

def alternates(item):
    """<link rel="alternate" hreflang> for every declared language, and
    x-default for the default one; nothing in a monolingual site."""
    if not languages.multilingual():
        return []
    path = item["path"]
    out = [f'<link rel="alternate" hreflang="{L}" href="{H.escape(apex() + clean_url(path, L))}">'
           for L in languages.declared()]
    out.append(f'<link rel="alternate" hreflang="x-default" '
               f'href="{H.escape(apex() + clean_url(path, languages.default()))}">')
    return out


def alternate_locales():
    """og:locale:alternate: every other declared language's locale once, in
    declaration order. Two languages may share one, and the current one is
    og:locale already. Nothing in a monolingual site."""
    if not languages.multilingual():
        return []
    out = []
    for L in languages.declared():
        loc = languages.CONFIGS[L]["site"]["locale"]
        if loc != CFG["site"]["locale"] and loc not in out:
            out.append(loc)
    return out


def head_tags(item):
    """Everything search engines and sharing read in <head>, after the
    canonical link: hreflang alternates, robots, the type's name tags, Open
    Graph, the type's property tags, Twitter Card, JSON-LD."""
    meta, module, conf, path = item["meta"], item["type"], item["conf"], item["path"]
    image, width, height = share_image(meta)
    large = bool(width and height and width >= 600 and width > height)
    extra = call(item["src"], module, "meta_tags", item, conf)
    out = alternates(item) + [
        f'<meta name="robots" content="{H.escape(meta.get("robots", CFG["seo"]["robots"]))}">']
    out += [f'<meta name="{k}" content="{H.escape(v)}">' for a, k, v in extra if a == "name"]
    props = [
        ("og:site_name", CFG["site"]["name"]),
        ("og:locale", CFG["site"]["locale"]),
    ]
    props += [("og:locale:alternate", loc) for loc in alternate_locales()]
    props += [
        ("og:type", module.OG_TYPE),
        ("og:title", page_heading(meta)),
        ("og:description", meta["description"]),
        ("og:url", apex() + clean_url(path)),
        ("og:image", image),
        ("og:image:alt", meta.get("image_alt") or CFG["share"]["image_alt"]),
    ]
    if width and height:
        props += [("og:image:width", str(width)), ("og:image:height", str(height))]
    props += [(k, v) for a, k, v in extra if a == "property"]
    out += [f'<meta property="{k}" content="{H.escape(v)}">' for k, v in props]
    out += [f'<meta name="{k}" content="{H.escape(v)}">' for k, v in [
        ("twitter:card", "summary_large_image" if large else "summary"),
        ("twitter:title", page_heading(meta)),
        ("twitter:description", meta["description"]),
        ("twitter:image", image),
    ]]
    out.append(json_ld(item, image))
    return "\n".join(out)


# --- structured data ---------------------------------------------------------

def json_ld(item, image):
    """The graph: Organization, WebSite, the type's node (a WebPage when
    the type gives none), BreadcrumbList."""
    meta, path = item["meta"], item["path"]
    a, lang = apex(), CFG["site"]["lang"]
    url = a + clean_url(path)
    org = {"@type": "Organization", "@id": org_ref()["@id"],
           "name": CFG["seo"]["organization"], "url": f"{a}/",
           "logo": f"{a}/{CFG['share']['logo']}"}
    site = {"@type": "WebSite", "@id": site_ref()["@id"], "name": CFG["site"]["name"],
            "url": f"{a}/", "inLanguage": lang, "publisher": org_ref()}
    node = call(item["src"], item["type"], "json_ld", item, item["conf"]) or {
        "@type": "WebPage", "name": page_title(meta),
        "description": meta["description"], "isPartOf": site_ref()}
    node.update({"@id": f"{url}#page", "url": url, "inLanguage": item["content_lang"]})
    graph = [org, site, node]

    crumbs = breadcrumbs(meta, path)
    if len(crumbs) > 1:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": n, "name": name, "item": link}
            for n, (name, link) in enumerate(crumbs, 1)]})
    data = json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, separators=(",", ":"))
    # "</" would close the element early; JSON allows "<\/" for it.
    data = data.replace("</", "<\\/")
    return f'<script type="application/ld+json">{data}</script>'


def breadcrumbs(meta, path):
    """Landing > section (from the nav) > page."""
    a = apex()
    if is_landing(meta):
        return []
    home = CFG["nav"][0]
    out = [(home["label"], a + clean_url("index.html"))]
    section = next((n for n in CFG["nav"] if n["href"] == meta.get("nav")
                    and n["href"] and not n["href"].startswith("http")), None)
    url = a + clean_url(path)
    if section:
        s_url = f"{a}/{languages.prefix()}{section['href']}"
        if s_url != url:
            out.append((section["label"], s_url))
    out.append((page_heading(meta), url))
    return out


# --- sitemaps, robots, manifest ----------------------------------------------

def sitemap_xml(items):
    """One sitemap for every language. lastmod: `updated:`, else an item's
    date, else [site] updated. In a multilingual site each URL lists its
    siblings as xhtml:link alternates, x-default included."""
    multi = languages.multilingual()
    rows = []
    for it in sorted(items, key=lambda it: clean_url(it["path"], it["lang"])):
        lastmod = it["meta"].get("updated") or it["date"] or CFG["site"]["updated"]
        row = (f"\t<url>\n\t\t<loc>{H.escape(apex() + clean_url(it['path'], it['lang']))}</loc>\n"
               f"\t\t<lastmod>{lastmod}</lastmod>\n")
        if multi:
            for L in languages.declared():
                row += (f'\t\t<xhtml:link rel="alternate" hreflang="{L}" '
                        f'href="{H.escape(apex() + clean_url(it["path"], L))}"/>\n')
            row += (f'\t\t<xhtml:link rel="alternate" hreflang="x-default" '
                    f'href="{H.escape(apex() + clean_url(it["path"], languages.default()))}"/>\n')
        rows.append(row + "\t</url>\n")
    ns = ' xmlns:xhtml="http://www.w3.org/1999/xhtml"' if multi else ""
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"{ns}>\n'
            + "".join(rows) + "</urlset>\n")


def robots(rules, sitemap=None):
    lines = ["User-agent: *"]
    lines += [f"Disallow: {d}" for d in rules.get("disallow", [])] or ["Allow: /"]
    if sitemap:
        lines += ["", f"Sitemap: {sitemap}"]
    return "\n".join(lines) + "\n"


def manifest():
    site, share = CFG["site"], CFG["share"]
    icons = [
        {"src": "logo.svg", "type": "image/svg+xml", "sizes": "any"},
        {"src": "icon-192.png", "type": "image/png", "sizes": "192x192"},
        {"src": "icon-512.png", "type": "image/png", "sizes": "512x512"},
    ]
    return json.dumps({
        "name": site["name"], "short_name": share["short_name"],
        "lang": site["lang"], "start_url": "./", "display": "browser",
        "background_color": share["background_color"],
        "theme_color": share["theme_color"], "icons": icons,
    }, ensure_ascii=False, indent="\t") + "\n"


# --- checks ------------------------------------------------------------------

def check(items):
    """Warn, without failing the build, about what search engines penalise
    or truncate: titles past 60 characters, descriptions outside 50-160,
    duplicates. The 404 and pages marked noindex are skipped. On a
    multilingual site each line names the language of the pass."""
    limits = CFG["seo"]
    seen_t, seen_d, warnings = {}, {}, []
    for it in items:
        path, meta = it["path"], it["meta"]
        if "noindex" in meta.get("robots", ""):
            continue
        title, desc = page_title(meta), meta.get("description", "")
        if len(title) > limits["title_max"]:
            warnings.append(f"{path}: title is {len(title)} characters (max {limits['title_max']})")
        if not limits["description_min"] <= len(desc) <= limits["description_max"]:
            warnings.append(f"{path}: description is {len(desc)} characters "
                            f"({limits['description_min']}-{limits['description_max']})")
        for value, seen, what in ((title, seen_t, "title"), (desc, seen_d, "description")):
            if value in seen:
                warnings.append(f"{path}: same {what} as {seen[value]}")
            seen.setdefault(value, path)
    lang = f"[{STATE['lang']}] " if languages.multilingual() else ""
    for w in warnings:
        print(f"seo: {lang}{w}", file=sys.stderr)
    return warnings
