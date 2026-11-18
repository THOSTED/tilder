"""Dates written out in words, from [dates] in site.toml; an event's
hours, in the [calendar] timezone."""

import datetime
import re
import zoneinfo

from config import CFG

# An event's `time:`: a start, or a start and an end, on a 24-hour clock.
TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(?:-([01]\d|2[0-3]):([0-5]\d))?$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# An event's own entries in the iCalendar: session-1, session-2...
SESSION_KEY = re.compile(r"^session-(\d+)$")


def human_date(iso):
    """2026-11-21 -> "Saturday 21 November 2026", words from [dates]."""
    d, day = CFG["dates"], datetime.date.fromisoformat(iso)
    return d["format"].format(
        weekday=d["weekdays"][day.weekday()], month=d["months"][day.month - 1],
        day=d["first"] if day.day == 1 else day.day, year=day.year)


def hours(meta):
    """`time: 14:00-15:00` (or `14:00`) -> ("14:00", "15:00") (or
    ("14:00", None)); None for an event that lasts the whole day. The
    front matter is checked by the event type: this trusts it."""
    m = TIME.match(meta.get("time", "").replace(" ", ""))
    if not m:
        return None
    return f"{m[1]}:{m[2]}", (f"{m[3]}:{m[4]}" if m[3] else None)


def session(value):
    """"[YYYY-MM-DD] [HH:MM[-HH:MM]] title" -> (day or None, hours or None,
    title). No day: the event's; no hours: the whole day."""
    words = value.split()
    day = words.pop(0) if words and DAY.match(words[0]) else None
    span = None
    if words and TIME.match(words[0]):
        t = TIME.match(words.pop(0))
        span = (f"{t[1]}:{t[2]}", f"{t[3]}:{t[4]}" if t[3] else None)
    return day, span, " ".join(words)


def sessions(meta):
    """The event's session-N keys, parsed, in the order of N."""
    keys = sorted((int(m[1]), k) for k in meta for m in [SESSION_KEY.match(k)] if m)
    return [session(meta[k]) for _, k in keys]


def moment(iso, hm):
    """A date and an hour, local to [calendar] timezone, as an aware
    datetime: what iCalendar (in UTC) and structured data (with its
    offset) are written from."""
    zone = zoneinfo.ZoneInfo(CFG["calendar"]["timezone"])
    return datetime.datetime.fromisoformat(f"{iso}T{hm}").replace(tzinfo=zone)
