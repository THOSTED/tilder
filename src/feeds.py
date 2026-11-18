"""RSS for any collection whose type gives feed items; iCalendar, used by the event type."""

import datetime
import html as H
import re

from config import CFG, apex, rfc822
from contenttypes import call
from dates import hours, moment, sessions
from fold import to_ascii
from paths import absolute, clean_url

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
        # With item_prefix, the guid stays the URL without it, which
        # redirects to the item: a reader that saw an item before the
        # prefix came does not show it again as new.
        guid = f['link'].replace(f"/{conf['dir']}/{conf['item_prefix']}/", f"/{conf['dir']}/", 1) \
            if conf.get("item_prefix") else f['link']
        rows += f"""
	<item>
		<title>{H.escape(f['title'])}</title>
		<link>{f['link']}</link>
		<guid isPermaLink="true">{guid}</guid>
		<pubDate>{rfc822(f['date'])}</pubDate>
		<description>{H.escape(f['description'])}</description>
	</item>
"""
    return rss(conf["feed_title"], absolute(conf["nav"]), absolute(conf["feed"]),
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
        # One VEVENT for the event, or one per session-N when it has some:
        # (UID, summary, first day, last day, hours or None). A session
        # with no day is on the event's first day, or over the whole event
        # when it has no hours either.
        last = meta.get("end", e["date"])
        runs = [(f"{e['slug']}-{n}", title, day or e["date"], day or (e["date"] if span else last), span)
                for n, (day, span, title) in enumerate(sessions(meta), 1)] \
            or [(e["slug"], meta["title"], e["date"], last, hours(meta))]
        for uid, summary, first, final, span in runs:
            lines += vevent(c, stamp, e, uid, summary, first, final, span)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ics(l) for l in lines) + "\r\n"


def vevent(c, stamp, e, uid, summary, first, final, span):
    """One VEVENT: all day from first to final, or timed when span gives
    hours (the start on the first day, the end on the final one)."""
    meta = e["meta"]
    if span:
        # In UTC: no VTIMEZONE to write, nothing for a client to guess.
        utc = datetime.timezone.utc
        when = [f"DTSTART:{moment(first, span[0]).astimezone(utc):%Y%m%dT%H%M%SZ}"]
        if span[1]:
            when.append(f"DTEND:{moment(final, span[1]).astimezone(utc):%Y%m%dT%H%M%SZ}")
    else:
        end = datetime.date.fromisoformat(final) + datetime.timedelta(days=1)  # DTEND is exclusive
        when = [f"DTSTART;VALUE=DATE:{first.replace('-', '')}", f"DTEND;VALUE=DATE:{end:%Y%m%d}"]
    return ["BEGIN:VEVENT", f"UID:{uid}@{c['uid_domain']}", f"DTSTAMP:{stamp}", *when,
            f"SUMMARY:{ics_text(summary)} - {ics_text(c['name'])}",
            "LOCATION:" + ics_text(meta.get("place", "")),
            *([f"GEO:{meta['lat']};{meta['lon']}"] if meta.get("lat") and meta.get("lon") else []),
            f"URL:{apex()}{clean_url(e['path'])}",
            "DESCRIPTION:" + ics_text(meta.get("description", "")), "END:VEVENT"]
