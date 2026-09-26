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

from config import ASSETS, CFG, CONTENT, apex, theme_file
from images import image_size
from paths import clean_url

# The kinds of page the build knows: set as meta["_kind"] by build.py.
POST, EVENT, MEMBER, PAGE = "post", "event", "member", "page"


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

def head_tags(meta, path):
    """Everything search engines and sharing read in <head>, after the
    canonical link: robots, author, Open Graph, Twitter Card, JSON-LD."""
    kind = meta.get("_kind", PAGE)
    image, width, height = share_image(meta)
    large = bool(width and height and width >= 600 and width > height)
    out = [f'<meta name="robots" content="{H.escape(meta.get("robots", CFG["seo"]["robots"]))}">']
    if kind == POST and meta.get("author"):
        out.append(f'<meta name="author" content="{H.escape(meta["author"])}">')
    props = [
        ("og:site_name", CFG["site"]["name"]),
        ("og:locale", CFG["site"]["locale"]),
        ("og:type", "article" if kind == POST else "website"),
        ("og:title", page_heading(meta)),
        ("og:description", meta["description"]),
        ("og:url", apex() + clean_url(path)),
        ("og:image", image),
        ("og:image:alt", meta.get("image_alt") or CFG["share"]["image_alt"]),
    ]
    if width and height:
        props += [("og:image:width", str(width)), ("og:image:height", str(height))]
    if kind == POST:
        props.append(("article:published_time", meta["_date"]))
        if meta.get("tag"):
            props.append(("article:tag", meta["tag"]))
    out += [f'<meta property="{k}" content="{H.escape(v)}">' for k, v in props]
    out += [f'<meta name="{k}" content="{H.escape(v)}">' for k, v in [
        ("twitter:card", "summary_large_image" if large else "summary"),
        ("twitter:title", page_heading(meta)),
        ("twitter:description", meta["description"]),
        ("twitter:image", image),
    ]]
    out.append(json_ld(meta, path, image))
    return "\n".join(out)


# --- structured data ---------------------------------------------------------

def json_ld(meta, path, image):
    a, kind = apex(), meta.get("_kind", PAGE)
    url = a + clean_url(path)
    lang = CFG["site"]["lang"]
    org = {"@type": "Organization", "@id": f"{a}/#organization",
           "name": CFG["seo"]["organization"], "url": f"{a}/",
           "logo": f"{a}/{CFG['share']['logo']}"}
    site = {"@type": "WebSite", "@id": f"{a}/#website", "name": CFG["site"]["name"],
            "url": f"{a}/", "inLanguage": lang, "publisher": {"@id": org["@id"]}}
    graph = [org, site]
    ref = lambda node: {"@id": node["@id"]}

    if kind == POST:
        node = {"@type": "BlogPosting", "headline": page_heading(meta),
                "description": meta["description"], "datePublished": meta["_date"],
                "dateModified": meta.get("updated", meta["_date"]),
                "publisher": ref(org), "image": image}
        if meta.get("author"):
            node["author"] = {"@type": "Person", "name": meta["author"]}
    elif kind == EVENT:
        place = {"@type": "Place", "name": meta.get("place", ""),
                 "address": meta.get("place", "")}
        if meta.get("lat") and meta.get("lon"):
            place["geo"] = {"@type": "GeoCoordinates",
                            "latitude": meta["lat"], "longitude": meta["lon"]}
        node = {"@type": "Event", "name": page_heading(meta),
                "description": meta["description"], "startDate": meta["_date"],
                "endDate": meta.get("end", meta["_date"]),
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "location": place, "organizer": ref(org), "image": image}
    elif kind == MEMBER:
        person = {"@type": "Person", "name": page_heading(meta), "memberOf": ref(org)}
        same = [url for k in ("linkedin", "github", "gitlab", "mastodon", "bluesky",
                              "website") for url in meta.get(k, "").split()]
        if same:
            person["sameAs"] = same  # links the profiles to the person
        if meta.get("affiliation"):
            person["affiliation"] = {"@type": "Organization", "name": meta["affiliation"]}
        node = {"@type": "ProfilePage", "name": page_title(meta), "mainEntity": person}
    else:
        node = {"@type": "WebPage", "name": page_title(meta),
                "description": meta["description"], "isPartOf": ref(site)}
    node.update({"@id": f"{url}#page", "url": url, "inLanguage": lang})
    graph.append(node)

    crumbs = breadcrumbs(meta, path)
    if len(crumbs) > 1:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": n, "name": name, "item": item}
            for n, (name, item) in enumerate(crumbs, 1)]})
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
    out = [(home["label"], f"{a}/")]
    section = next((n for n in CFG["nav"] if n["href"] == meta.get("nav")
                    and n["href"] and not n["href"].startswith("http")), None)
    url = a + clean_url(path)
    if section:
        s_url = a + "/" + section["href"]
        if s_url != url:
            out.append((section["label"], s_url))
    out.append((page_heading(meta), url))
    return out


# --- sitemaps, robots, manifest ----------------------------------------------

def sitemap_xml(pages):
    """pages: (path, meta). lastmod: `updated:`, else an item's date, else
    [site] updated."""
    rows = []
    for path, meta in sorted(pages, key=lambda p: clean_url(p[0])):
        lastmod = meta.get("updated") or meta.get("_date") or CFG["site"]["updated"]
        rows.append(f"\t<url>\n\t\t<loc>{H.escape(apex() + clean_url(path))}</loc>\n"
                    f"\t\t<lastmod>{lastmod}</lastmod>\n\t</url>\n")
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
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

def check(pages):
    """Warn, without failing the build, about what search engines penalise
    or truncate: titles past 60 characters, descriptions outside 50-160,
    duplicates. The 404 and pages marked noindex are skipped."""
    limits = CFG["seo"]
    seen_t, seen_d, warnings = {}, {}, []
    for path, meta in pages:
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
    for w in warnings:
        print(f"seo: {w}", file=sys.stderr)
    return warnings
