"""Dates written out in words, from [dates] in site.toml."""

import datetime

from config import CFG


def human_date(iso):
    """2026-11-21 -> "Saturday 21 November 2026", words from [dates]."""
    d, day = CFG["dates"], datetime.date.fromisoformat(iso)
    return d["format"].format(
        weekday=d["weekdays"][day.weekday()], month=d["months"][day.month - 1],
        day=d["first"] if day.day == 1 else day.day, year=day.year)
