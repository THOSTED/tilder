"""Dated collections: posts and events, declared in site.toml, their lists
and cards.

A collection is `[collections.<name>]` in site.toml: a `type` (posts or
events), a `dir` under content/, and its words, feed and calendar. The
keys a type needs default from `[collection_defaults.<type>]`, so a site
declares only what differs. A collection whose folder does not exist is
simply empty: no page, no feed.
"""

import copy
import datetime
import urllib.parse

from config import CFG, CONTENT, DATED, STATE
from dates import human_date
from markdown import front_matter

POSTS, EVENTS = "posts", "events"
# Section markers that list a collection: {posts}, {upcoming:talks}...
LIST_MARKERS = {"posts": POSTS, "upcoming": EVENTS, "past": EVENTS, "next-event": EVENTS}


def collections():
    """{name: settings} of every declared collection, each with its type's
    defaults under it. In declaration order."""
    out = {}
    for name, conf in CFG.get("collections", {}).items():
        kind = conf.get("type", POSTS)
        if kind not in (POSTS, EVENTS):
            raise SystemExit(f"collection {name}: type must be {POSTS} or {EVENTS}, not {kind}")
        merged = copy.deepcopy(CFG["collection_defaults"][kind])
        merged.update(conf)
        merged.setdefault("dir", name)
        merged["type"] = kind
        out[name] = merged
    return out


def load_items(name, conf):
    """Every dated item of the collection, oldest first. An item is
    NAME.md or NAME/index.md in content/<dir>/, NAME being YYYY-MM-DD-slug."""
    base, items = CONTENT / conf["dir"], []
    for f in sorted(base.iterdir()) if base.is_dir() else []:
        slug = f.stem if f.suffix == ".md" else f.name
        m = DATED.match(slug)
        src = f if f.suffix == ".md" else f / "index.md"
        if f.name.startswith("_") or not m or not src.is_file():
            continue
        datetime.date.fromisoformat(m.group(1))  # a bad date stops the build
        meta, _ = front_matter(src.read_text())
        items.append({"iso": m.group(1), "slug": slug, "meta": meta, "src": src,
                      "collection": name, "type": conf["type"], "conf": conf,
                      "path": f"{conf['dir']}/{slug}.html"})
    return items


def item_defaults(it):
    """What an item's front matter may leave out."""
    c, meta = it["conf"], it["meta"]
    meta.setdefault("man", c["man"])
    meta.setdefault("nav", c["nav"])
    meta.setdefault("tagline", human_date(it["iso"]))
    meta.setdefault("description", "")


def item_entry(it, link, cls=()):
    """An item as an entry node: a card in a list (link=True), or the
    heading card on its own page."""
    meta, c, events = it["meta"], it["conf"], it["type"] == EVENTS
    items = [f"{it['iso']} | {human_date(it['iso'])}"]
    if events and meta.get("end"):
        items[0] += " - " + human_date(meta["end"])
    for key in (("place",) if events else ("author",)):
        if meta.get(key):
            items.append(meta[key])
    if events:
        tag = c["upcoming_tag" if it["iso"] >= STATE["today"] else "past_tag"]
    else:
        tag = meta.get("tag", "")
    if tag:
        items.append(f"`{tag}`")
    blocks = []
    if link and meta.get("description"):
        blocks.append({"k": "para", "text": meta["description"], "cls": []})
    if not link and events:
        links = []
        if meta.get("link"):
            links.append(f"[{c['link_label']}]({meta['link']})")
        site = " · ".join(links)
        if osm_url(meta):
            links.append(f"[{c['map_label']}]({osm_url(meta)})")
        if links:
            # The text mirror leaves the map link out: the address is on
            # the card already, and the URL cannot fit in 75 columns.
            blocks.append({"k": "para", "cls": ["small"],
                           "text": " · ".join(links), "txt": site})
    if link:
        cls = list(cls) + ["link"]  # the whole card is clickable (CSS)
    return {"k": "entry", "id": None, "cls": list(cls), "meta": items, "blocks": blocks,
            "own": not link,
            "title": f"[{meta['title']}]({it['path'][:-5]})" if link else meta["title"]}


def osm_url(meta):
    """A link to the place on OpenStreetMap: a marker when the event gives
    lat and lon, else a search for its address. A link, not an embedded
    map: an iframe would make every visitor's browser call another host."""
    if meta.get("lat") and meta.get("lon"):
        lat, lon = meta["lat"], meta["lon"]
        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"
    if meta.get("place"):
        return "https://www.openstreetmap.org/search?query=" + urllib.parse.quote(meta["place"])
    return None


def _target(marker, path, colls):
    """The collection a marker lists: {posts:blog} names it; a bare {posts}
    is the page's own collection (its folder, or the page named like the
    folder: events.md for events/), else the first of the marker's type."""
    word, _, name = marker.partition(":")
    kind = LIST_MARKERS[word]
    if name:
        if name not in colls or colls[name]["type"] != kind:
            raise SystemExit(f"{path}: {{{marker}}} names no {kind} collection")
        return name
    folder = path[:-5].removesuffix("/index")
    own = [n for n, c in colls.items() if c["type"] == kind
           and (folder == c["dir"] or folder.startswith(c["dir"] + "/"))]
    same = [n for n, c in colls.items() if c["type"] == kind]
    return (own or same or [None])[0]


def fill_collections(sections, path, colls, items):
    """Fill the sections marked {posts}, {upcoming}, {past} or {next-event}
    (each may name a collection: {upcoming:talks}) with cards, and put an
    item's heading card on its own page. items: {name: [item]}."""
    today = STATE["today"]
    for s in sections:
        for marker in list(s["cls"]):
            if marker.partition(":")[0] not in LIST_MARKERS:
                continue
            name = _target(marker, path, colls)
            conf, its = colls.get(name, {}), items.get(name, [])
            word = marker.partition(":")[0]
            if word == "posts":
                cards, empty = [item_entry(i, True) for i in reversed(its)], conf.get("empty", "")
            else:
                upcoming = [e for e in its if e["iso"] >= today]
                if word == "past":
                    chosen = [e for e in reversed(its) if e["iso"] < today]
                    cards = [item_entry(e, True) for e in chosen]
                    empty = conf.get("none_past", "")
                else:
                    chosen = upcoming[:1] if word == "next-event" else upcoming
                    cards = [item_entry(e, True, ["next"] if n == 0 else [])
                             for n, e in enumerate(chosen)]
                    empty = conf.get("none_upcoming", "")
            s["blocks"] = (cards or [{"k": "empty", "text": empty}]) + s["blocks"]
    for its in items.values():
        for it in its:
            if it["path"] == path and sections:
                sections[0]["blocks"].append(item_entry(it, False))
