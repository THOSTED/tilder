import unittest

import contenttypes
from config import STATE, load_config

CONF = None


def setUpModule():
    global CONF
    load_config()
    STATE["today"] = "2026-06-15"
    event = contenttypes.load([contenttypes.BUILTIN])["event"]
    CONF = {**event.DEFAULTS, "dir": "events", "type": "event", "calendar": "events.ics"}


def item(slug="2099-01-01-future", **meta):
    m = {"title": "Future", "description": "One sentence."}
    m.update(meta)
    return {"slug": slug, "date": slug[:10], "meta": m, "src": None,
            "path": f"events/{slug}.html", "collection": "events", "conf": CONF,
            "type": contenttypes.TYPES["event"]}


class Event(unittest.TestCase):
    def setUp(self):
        self.event = contenttypes.TYPES["event"]

    def test_flags(self):
        self.assertTrue(self.event.DATED)
        self.assertTrue(self.event.ARTICLE)
        self.assertEqual(self.event.OG_TYPE, "website")
        self.assertEqual(set(self.event.MARKERS), {"upcoming", "past", "next-event"})
        self.assertTrue(self.event.HAS_FEED)

    def test_upcoming_card_with_place_and_end(self):
        node = self.event.entry(item(place="Library", end="2099-01-02"), True, CONF)
        self.assertEqual(node["meta"], [
            "2099-01-01 | Thursday 1 January 2099 - Friday 2 January 2099", "Library", "`upcoming`"])
        self.assertEqual(node["cls"], ["link"])
        self.assertEqual(node["title"], "[Future](events/2099-01-01-future)")

    def test_past_tag(self):
        node = self.event.entry(item("2000-01-01-past"), True, CONF)
        self.assertIn("`past`", node["meta"])

    def test_own_page_links(self):
        node = self.event.entry(item(place="Library", link="https://example.org/m", lat="45.75", lon="4.85"),
                                False, CONF)
        self.assertEqual(node["blocks"], [{
            "k": "para", "cls": ["small"],
            "text": "[event website ↗](https://example.org/m) · "
                    "[see on OpenStreetMap ↗](https://www.openstreetmap.org/?mlat=45.75&mlon=4.85#map=17/45.75/4.85)",
            "txt": "[event website ↗](https://example.org/m)",
        }])

    def test_osm_search_without_coordinates(self):
        node = self.event.entry(item(place="Town hall, Springfield"), False, CONF)
        self.assertIn("openstreetmap.org/search?query=Town%20hall%2C%20Springfield", node["blocks"][0]["text"])
        self.assertEqual(node["blocks"][0]["txt"], "")

    def test_markers(self):
        past, soon, later = item("2000-01-01-past"), item("2099-01-01-soon"), item("2099-02-01-later")
        items = [past, soon, later]
        up = self.event.MARKERS["upcoming"](items, CONF)
        self.assertEqual([(it["slug"], cls) for it, cls in up["items"]],
                         [("2099-01-01-soon", ["next"]), ("2099-02-01-later", [])])
        self.assertEqual(up["empty"], "No upcoming event.")
        nxt = self.event.MARKERS["next-event"](items, CONF)
        self.assertEqual([it["slug"] for it, _ in nxt["items"]], ["2099-01-01-soon"])
        pst = self.event.MARKERS["past"](items, CONF)
        self.assertEqual([it["slug"] for it, _ in pst["items"]], ["2000-01-01-past"])
        self.assertEqual(pst["empty"], "No past event.")

    def test_json_ld(self):
        node = self.event.json_ld(item(place="Library", lat="45.75", lon="4.85", end="2099-01-02"), CONF)
        self.assertEqual(node["@type"], "Event")
        self.assertEqual(node["startDate"], "2099-01-01")
        self.assertEqual(node["endDate"], "2099-01-02")
        self.assertEqual(node["location"]["geo"], {"@type": "GeoCoordinates", "latitude": "45.75", "longitude": "4.85"})
        self.assertEqual(node["organizer"], {"@id": "https://test.example/#organization"})

    def test_feed_item(self):
        self.assertEqual(self.event.feed_item(item(), CONF)["link"], "https://test.example/events/2099-01-01-future")

    def test_outputs_calendar_only_when_asked(self):
        self.assertEqual(self.event.outputs([], {**CONF, "calendar": ""}), {})
        out = self.event.outputs([item(place="Library")], CONF)
        self.assertEqual(list(out), ["events.ics"])
        self.assertIn("SUMMARY:Future - events", out["events.ics"])
        self.assertIn("LOCATION:Library", out["events.ics"])
