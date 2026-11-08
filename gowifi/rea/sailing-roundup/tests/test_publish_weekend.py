#!/usr/bin/env python3
import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from events_weekend import (
    issue_monday_for_end,
    overlaps,
    previous_week,
    saturday_sunday,
    skip_event,
    weekend_events,
    year_issue_mondays,
)
from news_schema import news_article_jsonld
from publish_weekend import (
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
        self.assertEqual(weekend_bounds(monday), (dt.date(2026, 10, 12), dt.date(2026, 10, 18)))
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
        self.assertEqual(feature["layout"], "lead")
        self.assertIn("26–27 September 2026", feature["deck"])
        self.assertEqual(feature["headline"], "South African Sailing — The Weekend Roundup")

    def test_same_weekend_keeps_mirror_with_tsl(self):
        monday = dt.date(2026, 10, 19)
        rows = [
            {
                "event_name": "KZN Mirror Regionals",
                "start_date": "2026-10-17",
                "end_date": "2026-10-18",
                "entries": 0,
                "races_sailed": 0,
            },
            {
                "event_name": "KZN Mirror Regionals",
                "start_date": "2026-10-17",
                "end_date": "2026-10-18",
                "regatta_id": "2026-10-17-pyc-kzn-mirror-regionals",
                "entries": 8,
                "races_sailed": 8,
                "category": "Regional Championships",
            },
            {
                "event_name": "SA Sailing WC Team Sailing Event",
                "start_date": "2026-10-17",
                "end_date": "2026-10-18",
                "regatta_id": "2026-10-17-mac-tsl-wc-team-sailing",
                "entries": 0,
                "races_sailed": 0,
                "category": "Team Sailing Events",
            },
            {
                "event_name": "2026 DF 95 Global Championship",
                "start_date": "2026-10-17",
                "end_date": "2026-10-18",
                "entries": 0,
                "races_sailed": 0,
            },
        ]
        picked = weekend_events(monday, rows)
        slugs = [e["regatta_id"] for e in picked if e.get("regatta_id")]
        self.assertIn("2026-10-17-pyc-kzn-mirror-regionals", slugs)
        self.assertIn("2026-10-17-mac-tsl-wc-team-sailing", slugs)
        mirror = next(e for e in picked if e["event_name"] == "KZN Mirror Regionals")
        self.assertEqual(mirror["regatta_id"], "2026-10-17-pyc-kzn-mirror-regionals")
        self.assertTrue(mirror["has_results"])
        articles = [
            {"type": "regatta_report", "event_id": "2026-10-17-mac-tsl-wc-team-sailing", "class_name": "TSL", "club": "MAC"},
            {"type": "regatta_report", "event_id": "2026-10-17-pyc-kzn-mirror-regionals", "class_name": "Mirror", "club": "PYC"},
        ]
        feature = weekend_feature("2026-10-19", monday, picked, articles)
        blob = " ".join(b["text"] for b in feature["blocks"])
        self.assertIn("Point Yacht Club", blob)
        self.assertNotIn("KZN Mirror Regionals. Results for those events were not available", blob)
        self.assertIn("DF 95", blob)
        half = weekend_feature("2026-10-19", monday, picked, articles[:1])
        half_blob = " ".join(b["text"] for b in half["blocks"])
        self.assertNotIn("KZN Mirror Regionals", half_blob)

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


class YearBackfill(unittest.TestCase):
    def test_issue_monday_is_next_monday_after_finish(self):
        self.assertEqual(issue_monday_for_end(dt.date(2026, 9, 27)), dt.date(2026, 9, 28))
        self.assertEqual(issue_monday_for_end(dt.date(2026, 6, 15)), dt.date(2026, 6, 22))
        self.assertEqual(issue_monday_for_end(dt.date(2026, 4, 15)), dt.date(2026, 4, 20))
        self.assertEqual(previous_week(dt.date(2026, 9, 28)), (dt.date(2026, 9, 21), dt.date(2026, 9, 27)))

    def test_multi_week_event_waits_until_monday_after_it_ended(self):
        # Wed 9 Dec – Tue 15 Dec 2026: finishes in week of 14–20 Dec → Monday 21 Dec.
        rows = [
            {
                "event_name": "2026 USSA Sailing Championships",
                "start_date": "2026-12-09",
                "end_date": "2026-12-15",
                "category": "National Championships",
                "regatta_id": "2026-12-09-ussa-sailing-championships",
                "entries": 40,
                "races_sailed": 8,
            }
        ]
        self.assertEqual(issue_monday_for_end(dt.date(2026, 12, 15)), dt.date(2026, 12, 21))
        self.assertEqual(year_issue_mondays(2026, rows), [dt.date(2026, 12, 21)])
        self.assertEqual(weekend_events(dt.date(2026, 12, 14), rows), [])
        self.assertEqual(
            [e["event_name"] for e in weekend_events(dt.date(2026, 12, 21), rows)],
            ["2026 USSA Sailing Championships"],
        )

    def test_one_monday_per_weekend_skips_empty(self):
        rows = [
            {"event_name": "420 Nationals", "start_date": "2026-09-26", "end_date": "2026-09-27", "regatta_id": "2026-09-25-tsc-420-nationals", "entries": 16, "races_sailed": 8, "category": "National Championships"},
            {"event_name": "Dart 18 Nationals", "start_date": "2026-09-24", "end_date": "2026-09-27", "regatta_id": "2026-09-24-hmyc-dart-18-nationals", "entries": 38, "races_sailed": 7, "category": "National Championships"},
            {"event_name": "Cape Classic", "start_date": "2026-02-13", "end_date": "2026-02-15", "regatta_id": "2026-02-15-hyc-cape-classic", "entries": 11, "races_sailed": 5, "category": "Dinghy Event"},
            {"event_name": "Instructor Course", "start_date": "2026-03-07", "end_date": "2026-03-08", "category": "Training"},
            {"event_name": "KZN 505 Regionals", "start_date": "2026-06-15", "end_date": "2026-06-15", "category": "Regional Championships"},
        ]
        mondays = year_issue_mondays(2026, rows)
        self.assertEqual(mondays, [dt.date(2026, 2, 16), dt.date(2026, 6, 22), dt.date(2026, 9, 28)])
        sep = weekend_events(dt.date(2026, 9, 28), rows)
        self.assertEqual(len(sep), 2)
        midweek = weekend_events(dt.date(2026, 6, 22), rows)
        self.assertEqual([e["event_name"] for e in midweek], ["KZN 505 Regionals"])

    def test_newsarticle_schema(self):
        data = {
            "title": "Weekend Sailing Roundup",
            "edition_date": "2026-09-28",
            "updated_at": "2026-09-28T08:00:00+00:00",
            "articles": [
                {"type": "feature", "headline": "The Weekend Roundup", "byline": "SailingSA", "published_at": "2026-09-28"},
                {"type": "regatta_report", "event_id": "2026-09-25-tsc-420-nationals", "headline": "Dale Rae wins 420 Nationals"},
            ],
        }
        payload = news_article_jsonld("2026-09-28", data)
        self.assertEqual(payload["@type"], "NewsArticle")
        self.assertEqual(payload["headline"], "The Weekend Roundup")
        self.assertTrue(payload["datePublished"].startswith("2026-09-28T06:00:00"))
        self.assertEqual(payload["author"]["name"], "SailingSA")
        self.assertEqual(payload["about"][0]["@type"], "SportsEvent")
        self.assertEqual(payload["about"][0]["sport"], "Sailing")
        self.assertEqual(payload["about"][0]["startDate"], "2026-09-25")
        self.assertEqual(payload["about"][0]["location"]["name"], "TSC")
        self.assertEqual(payload["about"][0]["location"]["address"]["addressCountry"], "ZA")


if __name__ == "__main__":
    unittest.main()
