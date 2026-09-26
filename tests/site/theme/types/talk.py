"""A talk: an event with a speaker. A theme type, built on the built-in
event type, which is loaded first and reachable through contenttypes.TYPES."""

from contenttypes import TYPES

event = TYPES["event"]

NAME = "talk"
DATED = True
ARTICLE = True
DEFAULTS = {**event.DEFAULTS, "man": "SITE-TALKS(7)", "nav": "talks",
            "speaker_label": "speaker", "feed_title": "talks", "feed_description": "Talks."}
MARKERS = {"talks": event.MARKERS["upcoming"]}   # {talks}: upcoming talks, nearest first

defaults = event.defaults
json_ld = event.json_ld
feed_item = event.feed_item
outputs = event.outputs


def entry(item, link, conf):
    """The event card, with the speaker after the date."""
    node = event.entry(item, link, conf)
    if item["meta"].get("speaker"):
        node["meta"].insert(1, f"{conf['speaker_label']}: {item['meta']['speaker']}")
    return node
