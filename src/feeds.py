"""RSS for posts and events, iCalendar for events."""

import datetime
import html as H
import re

from config import CFG, apex, rfc822
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


def events_feed(events, c):
    """An events collection's RSS: every event, the latest date first."""
    a = apex()
    items = "".join(f"""
	<item>
		<title>{H.escape(e['meta']['title'])}</title>
		<link>{a}{clean_url(e['path'])}</link>
		<guid isPermaLink="true">{a}{clean_url(e['path'])}</guid>
		<pubDate>{rfc822(e['iso'])}</pubDate>
		<description>{H.escape(e['meta']['description'])}</description>
	</item>
""" for e in reversed(events))
    return rss(c["feed_title"], f"{a}/{c['nav']}", f"{a}/{c['feed']}", c["feed_description"], items)


def posts_feed(posts, c):
    """A posts collection's RSS: every post, newest first."""
    a = apex()
    items = ""
    for it in reversed(posts):
        iso, url, meta, title = it["iso"], clean_url(it["path"]), it["meta"], it["meta"]["title"]
        items += f"""
	<item>
		<title>{H.escape(title)}</title>
		<link>{a}{url}</link>
		<guid isPermaLink="true">{a}{url}</guid>
		<pubDate>{rfc822(iso)}</pubDate>
		<description>{H.escape(meta['description'])}</description>
	</item>
"""
    return rss(c["feed_title"], f"{a}/{c['nav']}", f"{a}/{c['feed']}", c["feed_description"], items)


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
        day = datetime.date.fromisoformat(e.get("date") or e["iso"])
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
