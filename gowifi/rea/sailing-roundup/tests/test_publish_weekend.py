#!/usr/bin/env python3
import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from events_weekend import overlaps, saturday_sunday, skip_event, weekend_events
from publish_weekend import (
    event_terms,
    issue_mondays,
    last_monday,
    scrape_slugs,
    skip_event_name,
    weekend_bounds,
    weekend_feature,
)
from sailor_mentions import filter_for_event, parse_day


class PublishHelpers(unittest.TestCase):
    def test_monday_window(self):
        monday = dt.date(2026, 10, 19)
        self.assertEqual(last_monday(monday), monday)
        self.assertEqual(weekend_bounds(monday), (dt.date(2026, 10, 15), dt.date(2026, 10, 18)))
        self.assertEqual(issue_mondays(monday, 2), [dt.date(2026, 10, 19), dt.date(2026, 10, 12)])

    def test_skip_courses(self):
        self.assertTrue(skip_event_name("SA Sailing Instructor Course - ITYC"))
        self.assertFalse(skip_event_name("Dam Bottle Sprints"))

    def test_event_terms(self):
        terms = event_terms("2026 420 Nationals", "TSC")
        self.assertIn("420", terms)
        self.assertIn("nationals", terms)
        self.assertIn("tsc", terms)

    def test_scrape_slugs(self):
        html = '<a href="/regatta/2026-10-17-mac-tsl-wc-team-sailing">x</a>'
        self.assertEqual(scrape_slugs(html), {"2026-10-17-mac-tsl-wc-team-sailing"})

    def test_filter_mentions(self):
        items = [
            {"published_at": "2026-10-18", "headline": "Dam Bottle Sprints at HMYC", "url": "https://a"},
            {"published_at": "2024-01-01", "headline": "Dam Bottle Sprints at HMYC", "url": "https://old"},
            {"headline": "Unrelated football", "url": "https://b"},
        ]
        kept = filter_for_event(items, dt.date(2026, 10, 10), dt.date(2026, 10, 11), ["dam", "bottle", "hmyc"])
        self.assertEqual([k["url"] for k in kept], ["https://a"])

    def test_parse_day(self):
        self.assertEqual(parse_day("2026-10-19T08:00:00+02:00"), dt.date(2026, 10, 19))
        self.assertIsNone(parse_day("soon"))

    def test_sep_26_27_events_table(self):
        monday = dt.date(2026, 9, 28)
        self.assertEqual(saturday_sunday(monday), (dt.date(2026, 9, 26), dt.date(2026, 9, 27)))
        rows = [
            {"event_name": "420 Nationals", "start_date": "2026-09-26", "end_date": "2026-09-27", "regatta_id": "2026-09-25-tsc-420-nationals", "entries": 16, "races_sailed": 8, "category": "National Championships"},
            {"event_name": "Dart 18 Nationals incorporating the KZN provincials", "start_date": "2026-09-24", "end_date": "2026-09-27", "regatta_id": "2026-09-24-hmyc-dart-18-nationals", "entries": 0, "races_sailed": 8, "category": "National Championships"},
            {"event_name": "SA Sailing Designated Safeguarding Officer", "start_date": "2026-05-25", "end_date": "2029-05-31", "category": "Meetings"},
            {"event_name": "Instructor Course", "start_date": "2026-09-26", "end_date": "2026-09-27", "category": "Training"},
        ]
        picked = weekend_events(monday, rows)
        self.assertEqual(
            [e["regatta_id"] for e in picked],
            ["2026-09-24-hmyc-dart-18-nationals", "2026-09-25-tsc-420-nationals"],
        )
        self.assertTrue(skip_event(rows[2]))
        self.assertTrue(overlaps(dt.date(2026, 9, 24), dt.date(2026, 9, 27), dt.date(2026, 9, 26), dt.date(2026, 9, 27)))
        feature = weekend_feature("2026-09-28", monday, picked, [])
        self.assertEqual(feature["type"], "feature")
        self.assertIn("26 September", feature["deck"])


if __name__ == "__main__":
    unittest.main()
