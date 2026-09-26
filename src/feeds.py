"""RSS for any collection whose type gives feed items; iCalendar, used by the event type."""

import datetime
import html as H
import re

from config import CFG, apex, rfc822
from contenttypes import call
from fold import to_ascii
from paths import clean_url

def rss(title, link, self_href, description, items):
    title, description = H.escape(title), H.escape(description)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
	<title>{title}</title>
	<link>{link}</link>
	<atom:link href="{self_href}" rel="self" type="application/rss+xml"/>
	<description>{description}</description>
	<language>{CFG["site"]["lang"]}</language>
	<generator>builder/build.py</generator>
	<lastBuildDate>{rfc822(CFG["site"]["updated"])}</lastBuildDate>
{items}</channel>
</rss>
"""


def feed(items, conf):
    """A collection's RSS: every item its type puts in a feed, newest first."""
    rows = ""
    for it in reversed(items):
        f = call(it["src"], it["type"], "feed_item", it, conf)
        if f is None:
            continue
        rows += f"""
	<item>
		<title>{H.escape(f['title'])}</title>
		<link>{f['link']}</link>
		<guid isPermaLink="true">{f['link']}</guid>
		<pubDate>{rfc822(f['date'])}</pubDate>
		<description>{H.escape(f['description'])}</description>
	</item>
"""
    a = apex()
    return rss(conf["feed_title"], f"{a}/{conf['nav']}", f"{a}/{conf['feed']}",
               conf["feed_description"], rows)


def fold_ics(line):
    """RFC 5545: 75 octets per line, continuations prefixed by a space."""
    if len(line) <= 75:
        return line
    parts, rest = [line[:74]], line[74:]
    while rest:
        parts.append(" " + rest[:73])
        rest = rest[73:]
    return "\r\n".join(parts)


def ics_text(s):
    """RFC 5545 TEXT: ASCII here, with , ; and \\ escaped."""
    return re.sub(r"([,;\\])", r"\\\1", to_ascii(s))


def calendar(events):
    c = CFG["calendar"]
    stamp = CFG["site"]["updated"].replace("-", "") + "T000000Z"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{c['prodid']}",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{to_ascii(c['name'])}", f"X-WR-TIMEZONE:{c['timezone']}",
             f"X-WR-CALDESC:{to_ascii(c['description'])}"]
    for e in events:
        meta = e["meta"]
        day = datetime.date.fromisoformat(e["date"])
        last = datetime.date.fromisoformat(meta["end"]) if meta.get("end") else day
        end = last + datetime.timedelta(days=1)  # DTEND is exclusive
        lines += ["BEGIN:VEVENT", f"UID:{e['slug']}@{c['uid_domain']}",
                  f"DTSTAMP:{stamp}",
                  f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{end:%Y%m%d}",
                  f"SUMMARY:{ics_text(meta['title'])} - {ics_text(c['name'])}",
                  "LOCATION:" + ics_text(meta.get("place", "")),
                  *([f"GEO:{meta['lat']};{meta['lon']}"]
                    if meta.get("lat") and meta.get("lon") else []),
                  f"URL:{apex()}{clean_url(e['path'])}",
                  "DESCRIPTION:" + ics_text(meta.get("description", "")), "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ics(l) for l in lines) + "\r\n"
