"""A guide: one page of a sequence, in order, optionally grouped. A theme
type that uses collection navigation (SEQUENTIAL) and writes a file in
every language (LOCALIZED_OUTPUTS)."""

import json

NAME = "guide"
SEQUENTIAL = True
LOCALIZED_OUTPUTS = True
DEFAULTS = {"man": "SITE-GUIDES(7)", "nav": "guides/", "index": "guides/index.json"}


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("tagline", "")
    meta.setdefault("description", "")


def sort_key(item, conf):
    return (int(item["meta"].get("order", 1000)), item["slug"])


def entry(item, link, conf):
    return None


def outputs(items, conf):
    """The titles, in order: a stand-in for a search index."""
    return {conf["index"]: json.dumps([it["meta"]["title"] for it in items])}
