import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import contenttypes
from config import CFG, STATE, load_config

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

    def test_timed_card(self):
        node = self.event.entry(item(time="14:00-15:00"), True, CONF)
        self.assertEqual(node["meta"][0], "2099-01-01T14:00 | Thursday 1 January 2099, 14:00-15:00")
        node = self.event.entry(item(time="9:00"), True, CONF)   # not HH:MM: left as an all-day event
        self.assertEqual(node["meta"][0], "2099-01-01 | Thursday 1 January 2099")

    def test_time_is_checked(self):
        for bad in ("9h", "14:00-13:00", "25:00"):
            with self.assertRaises(Exception, msg=bad):
                self.event.defaults(item(time=bad), CONF)
        self.event.defaults(item(time="14:00 - 15:00"), CONF)   # spaces are fine

    def test_timed_json_ld_and_calendar_in_the_site_timezone(self):
        saved = CFG["calendar"]["timezone"]
        CFG["calendar"]["timezone"] = "Europe/Paris"
        try:
            node = self.event.json_ld(item(time="14:00-15:00"), CONF)
            self.assertEqual(node["startDate"], "2099-01-01T14:00:00+01:00")
            self.assertEqual(node["endDate"], "2099-01-01T15:00:00+01:00")
            ics = self.event.outputs([item(time="14:00-15:00")], CONF)["events.ics"]
            self.assertIn("DTSTART:20990101T130000Z", ics)
            self.assertIn("DTEND:20990101T140000Z", ics)
            self.assertNotIn("VALUE=DATE", ics)
            ics = self.event.outputs([item(time="14:00")], CONF)["events.ics"]
            self.assertNotIn("DTEND", ics)
        finally:
            CFG["calendar"]["timezone"] = saved

    def test_sessions_are_vevents(self):
        saved = CFG["calendar"]["timezone"]
        CFG["calendar"]["timezone"] = "Europe/Paris"
        try:
            ev = item(end="2099-01-02", **{"session-2": "14:00-15:00 Workshop",
                                          "session-1": "Stand", "session-3": "2099-01-02 Day two"})
            self.event.defaults(ev, CONF)
            ics = self.event.outputs([ev], CONF)["events.ics"]
            self.assertEqual(ics.count("BEGIN:VEVENT"), 3)
            self.assertNotIn("UID:2099-01-01-future@", ics)
            stand, workshop, two = ics.split("BEGIN:VEVENT")[1:]
            self.assertIn("UID:2099-01-01-future-1@", stand)
            self.assertIn("SUMMARY:Stand - events", stand)
            self.assertIn("DTSTART;VALUE=DATE:20990101", stand)
            self.assertIn("DTEND;VALUE=DATE:20990103", stand)      # the whole event
            self.assertIn("DTSTART:20990101T130000Z", workshop)    # its first day
            self.assertIn("DTEND:20990101T140000Z", workshop)
            self.assertIn("DTSTART;VALUE=DATE:20990102", two)
            self.assertIn("DTEND;VALUE=DATE:20990103", two)
        finally:
            CFG["calendar"]["timezone"] = saved

    def test_timed_event_over_several_days(self):
        ics = self.event.outputs([item(end="2099-01-03", time="09:00-18:00")], CONF)["events.ics"]
        self.assertIn("DTSTART:20990101T090000Z", ics)
        self.assertIn("DTEND:20990103T180000Z", ics)

    def test_session_is_checked(self):
        for bad in ("", "2098-12-31 Before", "15:00-14:00 Backwards"):
            with self.assertRaises(Exception, msg=bad):
                self.event.defaults(item(**{"session-1": bad}), CONF)

    def test_feed_item(self):
        self.assertEqual(self.event.feed_item(item(), CONF)["link"], "https://test.example/events/2099-01-01-future")

    def test_outputs_calendar_only_when_asked(self):
        self.assertEqual(self.event.outputs([], {**CONF, "calendar": ""}), {})
        out = self.event.outputs([item(place="Library")], CONF)
        self.assertEqual(list(out), ["events.ics"])
        self.assertIn("SUMMARY:Future - events", out["events.ics"])
        self.assertIn("LOCATION:Library", out["events.ics"])
