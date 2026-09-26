"""Dated collections: blog posts and events, their lists and cards."""

import datetime
import urllib.parse

from config import CFG, CONTENT, DATED, STATE
from markdown import front_matter

def human_date(iso):
    """2026-11-21 -> "samedi 21 novembre 2026", words from [dates]."""
    d, day = CFG["dates"], datetime.date.fromisoformat(iso)
    return d["format"].format(
        weekday=d["weekdays"][day.weekday()], month=d["months"][day.month - 1],
        day=d["first"] if day.day == 1 else day.day, year=day.year)


def load_items(collection):
    """Every dated item of content/<collection>/, oldest first. An item is
    NAME.md or NAME/index.md, NAME being YYYY-MM-DD-slug."""
    base, items = CONTENT / collection, []
    for f in sorted(base.iterdir()) if base.is_dir() else []:
        name = f.stem if f.suffix == ".md" else f.name
        m = DATED.match(name)
        src = f if f.suffix == ".md" else f / "index.md"
        if f.name.startswith("_") or not m or not src.is_file():
            continue
        datetime.date.fromisoformat(m.group(1))  # a bad date stops the build
        meta, _ = front_matter(src.read_text())
        items.append({"iso": m.group(1), "slug": name, "meta": meta, "src": src,
                      "collection": collection,
                      "path": f"{collection}/{name}.html"})
    return items


def item_defaults(it):
    """What an item's front matter may leave out."""
    c, meta = CFG[it["collection"]], it["meta"]
    meta.setdefault("man", c["man"])
    meta.setdefault("nav", c["nav"])
    meta.setdefault("tagline", human_date(it["iso"]))
    meta.setdefault("description", "")


def item_entry(it, link, cls=()):
    """An item as an entry node: a card in a list (link=True), or the
    heading card on its own page."""
    meta, events = it["meta"], it["collection"] == "events"
    items = [f"{it['iso']} | {human_date(it['iso'])}"]
    if events and meta.get("end"):
        items[0] += " - " + human_date(meta["end"])
    for key in (("place",) if events else ("author",)):
        if meta.get(key):
            items.append(meta[key])
    if events:
        tag = CFG["events"]["upcoming_tag" if it["iso"] >= STATE["today"] else "past_tag"]
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
            links.append(f"[{CFG['events']['link_label']}]({meta['link']})")
        site = " · ".join(links)
        if osm_url(meta):
            links.append(f"[{CFG['events']['map_label']}]({osm_url(meta)})")
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


def fill_collections(sections, path, posts, events):
    """Fill the sections marked {posts}, {upcoming}, {past} or {next-event}
    with cards, and put an item's heading card on its own page."""
    upcoming = [e for e in events if e["iso"] >= STATE["today"]]
    past = [e for e in reversed(events) if e["iso"] < STATE["today"]]
    lists = {
        "posts": ([item_entry(i, True) for i in reversed(posts)], CFG["blog"]["empty"]),
        "upcoming": ([item_entry(e, True, ["next"] if n == 0 else [])
                      for n, e in enumerate(upcoming)], CFG["events"]["none_upcoming"]),
        "past": ([item_entry(e, True) for e in past], CFG["events"]["none_past"]),
        "next-event": ([item_entry(e, True, ["next"]) for e in upcoming[:1]],
                       CFG["events"]["none_upcoming"]),
    }
    for s in sections:
        for marker, (cards, empty) in lists.items():
            if marker in s["cls"]:
                s["blocks"] = (cards or [{"k": "empty", "text": empty}]) + s["blocks"]
    for it in posts + events:
        if it["path"] == path and sections:
            sections[0]["blocks"].append(item_entry(it, False))
