import unittest

from tests.helpers import build_site


class Feeds(unittest.TestCase):
    def test_rss_per_collection_with_feed(self):
        out = build_site()
        self.assertIn("<title>Hello</title>", out["blog/feed.xml"])
        self.assertIn("<link>https://test.example/blog/2026-01-01-hello</link>", out["blog/feed.xml"])
        self.assertIn("<title>Future meetup</title>", out["events.xml"])
        self.assertLess(out["events.xml"].index("Future meetup"), out["events.xml"].index("Past meetup"))
        self.assertNotIn("news.xml", out)
        self.assertFalse([k for k in out if "members" in k and k.endswith(".xml")])

    def test_calendar_from_the_event_type(self):
        out = build_site()
        ics = out["events.ics"]
        self.assertIn("UID:2099-01-01-future-meetup@example.org", ics)
        self.assertIn("DTSTART;VALUE=DATE:20990101", ics)
        self.assertIn("DTEND;VALUE=DATE:20990103", ics)   # end 2099-01-02, exclusive
        self.assertIn("GEO:45.75;4.85", ics)
        self.assertIn("LOCATION:Library\\, Springfield", ics)
