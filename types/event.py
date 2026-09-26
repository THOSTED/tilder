"""Events: dated, upcoming or past by the date of the build, with a place,
an RSS feed and an iCalendar. The built-in `event` type (docs/types.md)."""

import urllib.parse

from config import STATE, apex
from dates import human_date
from feeds import calendar
from paths import clean_url
from seo import org_ref, page_heading, share_image

NAME = "event"
DATED = True
ARTICLE = True
DEFAULTS = {
    "man": "SITE-EVENTS(7)",
    "nav": "events",
    "upcoming_tag": "upcoming",
    "past_tag": "past",
    "none_upcoming": "No upcoming event.",
    "none_past": "No past event.",
    "link_label": "event website ↗",
    "map_label": "see on OpenStreetMap ↗",
    "feed": "",                     # RSS path, e.g. "events.xml"; empty for none
    "feed_title": "events",
    "feed_description": "Upcoming and past events.",
    "calendar": "",                 # iCalendar path, e.g. "events.ics"; empty for none
}


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("tagline", human_date(item["date"]))
    meta.setdefault("description", "")


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


def entry(item, link, conf):
    """The card: date (range), place, upcoming/past tag; the description in
    a list; the event's site and map links on its own page."""
    meta = item["meta"]
    line = [f"{item['date']} | {human_date(item['date'])}"]
    if meta.get("end"):
        line[0] += " - " + human_date(meta["end"])
    if meta.get("place"):
        line.append(meta["place"])
    tag = conf["upcoming_tag" if item["date"] >= STATE["today"] else "past_tag"]
    if tag:
        line.append(f"`{tag}`")
    blocks = []
    if link and meta.get("description"):
        blocks.append({"k": "para", "text": meta["description"], "cls": []})
    if not link:
        links = []
        if meta.get("link"):
            links.append(f"[{conf['link_label']}]({meta['link']})")
        site = " · ".join(links)
        if osm_url(meta):
            links.append(f"[{conf['map_label']}]({osm_url(meta)})")
        if links:
            # The text mirror leaves the map link out: the address is on the
            # card already, and the URL cannot fit in 75 columns.
            blocks.append({"k": "para", "cls": ["small"], "text": " · ".join(links), "txt": site})
    return {"k": "entry", "id": None, "cls": ["link"] if link else [], "meta": line,
            "blocks": blocks, "own": not link,
            "title": f"[{meta['title']}]({item['path'][:-5]})" if link else meta["title"]}


def upcoming(items, conf):
    """{upcoming}: today or later, nearest first, the first marked next."""
    chosen = [e for e in items if e["date"] >= STATE["today"]]
    return {"items": [(e, ["next"] if n == 0 else []) for n, e in enumerate(chosen)],
            "empty": conf.get("none_upcoming", "")}


def next_event(items, conf):
    """{next-event}: the next one only."""
    r = upcoming(items, conf)
    r["items"] = r["items"][:1]
    return r


def past(items, conf):
    """{past}: before today, latest first."""
    return {"items": [(e, []) for e in reversed(items) if e["date"] < STATE["today"]],
            "empty": conf.get("none_past", "")}


MARKERS = {"upcoming": upcoming, "past": past, "next-event": next_event}


def json_ld(item, conf):
    meta = item["meta"]
    place = {"@type": "Place", "name": meta.get("place", ""), "address": meta.get("place", "")}
    if meta.get("lat") and meta.get("lon"):
        place["geo"] = {"@type": "GeoCoordinates", "latitude": meta["lat"], "longitude": meta["lon"]}
    return {"@type": "Event", "name": page_heading(meta),
            "description": meta["description"], "startDate": item["date"],
            "endDate": meta.get("end", item["date"]),
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "location": place, "organizer": org_ref(), "image": share_image(meta)[0]}


def feed_item(item, conf):
    return {"title": item["meta"]["title"], "link": apex() + clean_url(item["path"]),
            "description": item["meta"]["description"], "date": item["date"]}


def outputs(items, conf):
    """The collection's iCalendar, when `calendar` names a path."""
    return {conf["calendar"]: calendar(items)} if conf.get("calendar") else {}
