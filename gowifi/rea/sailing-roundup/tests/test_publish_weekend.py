#!/usr/bin/env python3
import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from events_weekend import overlaps, saturday_sunday, skip_event, weekend_events
from publish_weekend import (
    discover_slugs,
    event_terms,
    issue_mondays,
    last_monday,
    scrape_slugs,
    skip_event_name,
    weekend_bounds,
    weekend_feature,
)
from event_social_verify import class_slugs_from_event, verify_post
from search_everywhere import (
    catalog_local_urls,
    coverage_window,
    discovery_queries,
    event_query,
    in_coverage_window,
    official_sailingsa_sources,
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

    def test_discover_slugs_unions_table_and_html(self):
        monday = dt.date(2026, 10, 19)
        table = ["2026-10-17-mac-tsl-wc-team-sailing"]
        html = ["2026-10-17-pyc-kzn-mirror-regionals"]
        from unittest.mock import patch
        with patch("publish_weekend.slugs_for_weekend", return_value=table), patch(
            "publish_weekend.html_slugs", return_value=html
        ):
            self.assertEqual(
                discover_slugs(monday),
                [
                    "2026-10-17-mac-tsl-wc-team-sailing",
                    "2026-10-17-pyc-kzn-mirror-regionals",
                ],
            )

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
        self.assertEqual(feature["layout"], "lead")
        self.assertIn("26–27 September 2026", feature["deck"])
        self.assertNotEqual(feature["headline"], "Weekend sailing roundup")

    def test_verify_everywhere_against_event_and_results(self):
        event = {
            "id": "2026-09-25-tsc-420-nationals",
            "title": "420 Nationals",
            "club": "TSC",
            "class_slugs": ["420"],
            "result_names": ["Dale Rae", "Joshua Keytel"],
            "event_url": "https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
        }
        self.assertEqual(class_slugs_from_event("420 Nationals", "2026-09-25-tsc-420-nationals"), ["420"])
        self.assertIn("420", event_query(event))
        ok = verify_post(
            {
                "url": "https://www.facebook.com/Int420Class/posts/1",
                "title": "420 Nationals at TSC — Dale Rae leads",
                "description": "Results on https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
            },
            event,
        )
        self.assertTrue(ok["verified"], ok)
        dart = verify_post(
            {"url": "https://www.facebook.com/hmyc/posts/2", "title": "Dart 18 Nationals Day 2 at HMYC", "description": ""},
            event,
        )
        self.assertFalse(dart["verified"], dart)
        bottle = {
            "id": "2026-10-10-hmyc-dam-bottle-sprints",
            "title": "Dam Bottle Sprints",
            "club": "HMYC",
            "class_slugs": ["dart-18"],
            "result_names": ["Lorrian Wells"],
            "event_url": "https://sailingsa.co.za/regatta/2026-10-10-hmyc-dam-bottle-sprints",
        }
        dart_on_bottle = verify_post(
            {
                "url": "https://www.facebook.com/share/p/1PGpY1pGh1/",
                "title": "Dart 18 Nationals Day 2 at HMYC",
                "description": "Bradley Levin won the Dart 18 Nationals",
            },
            bottle,
        )
        self.assertFalse(dart_on_bottle["verified"], dart_on_bottle)

    def test_discovery_looks_for_class_facebook(self):
        qs = discovery_queries({"title": "505 Nationals", "class_name": "505", "club": "AYC", "club_name": "Aeolians Yacht Club"})
        blob = " ".join(qs).lower()
        self.assertIn("facebook group", blob)
        self.assertIn("505", blob)
        locals_505 = catalog_local_urls({"class_name": "505", "class_slugs": ["505"], "club": "AYC"})
        urls = " ".join(x.get("url") or "" for x in locals_505)
        self.assertIn("230542873685522", urls)
        locals_dart = catalog_local_urls({"class_name": "Dart 18", "class_slugs": ["dart-18"], "club": "HMYC"})
        dart_urls = " ".join(x.get("url") or "" for x in locals_dart)
        self.assertIn("310727125653436", dart_urls)

    def test_search_uses_event_dates_and_rejects_old_posts(self):
        event = {
            "title": "420 Nationals",
            "club_name": "Theewater Sports Club",
            "class_name": "420",
            "start": "2026-09-26",
            "end": "2026-09-27",
        }
        query = event_query(event)
        self.assertIn("September 2026", query)
        blob = " ".join(discovery_queries(event))
        self.assertIn("after:2026-09-24", blob)
        self.assertIn("before:2026-10-12", blob)
        lo, hi = coverage_window(event)
        self.assertEqual(lo, dt.date(2026, 9, 24))
        self.assertEqual(hi, dt.date(2026, 10, 11))
        self.assertTrue(in_coverage_window({"published": "2026-09-30"}, event))
        self.assertTrue(in_coverage_window({"url": "https://novanews.co.za/2026/09/28/hermanus-high/"}, event))
        self.assertFalse(in_coverage_window({"published": "2024-03-01", "url": "https://old.example/420"}, event))
        old = verify_post(
            {
                "url": "https://example.com/2024/03/01/420-nationals",
                "title": "420 Nationals at TSC — Dale Rae leads",
                "description": "https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
                "published": "2024-03-01",
            },
            {
                "id": "2026-09-25-tsc-420-nationals",
                "title": "420 Nationals",
                "club": "TSC",
                "class_slugs": ["420"],
                "result_names": ["Dale Rae"],
                "event_url": "https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
                "start": "2026-09-26",
                "end": "2026-09-27",
            },
        )
        self.assertFalse(old["verified"], old)
        self.assertIn("outside_event_window", old["reasons"])

    def test_sailingsa_is_official_source_in_search(self):
        event = {
            "id": "2026-09-25-tsc-420-nationals",
            "slug": "2026-09-25-tsc-420-nationals",
            "title": "420 Nationals",
            "club": "TSC",
            "club_name": "Theewater Sports Club",
            "class_name": "420",
            "host_club_slug": "tsc",
            "start": "2026-09-26",
            "end": "2026-09-27",
        }
        blob = " ".join(discovery_queries(event))
        self.assertIn("420 Nationals 2026", blob)
        self.assertIn("420 Nationals September 2026", blob)
        self.assertIn("site:sailingsa.co.za", blob)
        self.assertIn("SailingSA", blob)
        urls = [item["url"] for item in official_sailingsa_sources(event)]
        self.assertIn("https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals", urls)
        self.assertIn("https://sailingsa.co.za/club/tsc", urls)
        self.assertIn("https://sailingsa.co.za/class/420", urls)
        self.assertTrue(
            in_coverage_window(
                {"url": "https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals"},
                event,
            )
        )
        official = verify_post(
            {
                "url": "https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
                "title": "420 Nationals — SailingSA results",
                "description": "Official SAS-sanctioned 420 Nationals results",
            },
            event,
        )
        self.assertTrue(official["verified"], official)
        self.assertIn("sailingsa_official", official["reasons"])


if __name__ == "__main__":
    unittest.main()
