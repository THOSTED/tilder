"""Pages: every .md outside a collection. No card, no list, a WebPage node."""

from seo import page_title, site_ref

NAME = "page"


def entry(item, link, conf):
    """A page has no card."""
    return None


def json_ld(item, conf):
    return {"@type": "WebPage", "name": page_title(item["meta"]),
            "description": item["meta"]["description"], "isPartOf": site_ref()}
