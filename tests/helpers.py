"""build_site(): the fixture site as {output path: text}, built once."""

import build

_CACHE = {}


def rebuild():
    """Build the fixture site now. {path: str}, bytes decoded as UTF-8."""
    out = build.build()
    return {k: v.decode("utf-8", errors="replace") for k, v in out.items()}


def build_site():
    """The fixture site, built once per test run."""
    if not _CACHE:
        _CACHE.update(rebuild())
    return _CACHE
