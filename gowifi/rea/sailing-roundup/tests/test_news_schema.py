#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from news_schema import news_article_jsonld, sports_event  # noqa: E402


class NewsSchemaTests(unittest.TestCase):
    def test_sportsevent_requires_startdate_and_location(self) -> None:
        event = sports_event(
            {
                "type": "regatta_report",
                "event_id": "2026-10-17-pyc-kzn-mirror-regionals",
                "headline": "KZN Mirror Regionals at PYC",
                "club": "PYC",
                "start_date": "2026-10-17",
                "end_date": "2026-10-18",
            }
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["@type"], "SportsEvent")
        self.assertEqual(event["startDate"], "2026-10-17")
        self.assertEqual(event["endDate"], "2026-10-18")
        self.assertEqual(event["location"]["@type"], "Place")
        self.assertEqual(event["location"]["name"], "PYC")
        self.assertEqual(event["location"]["address"]["addressCountry"], "ZA")
        self.assertEqual(event["description"], "KZN Mirror Regionals at PYC")

    def test_sportsevent_fills_from_slug_when_fields_missing(self) -> None:
        event = sports_event(
            {
                "type": "regatta_report",
                "event_id": "2026-09-25-tsc-420-nationals",
                "headline": "Dale Rae wins 420 Nationals",
            }
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["startDate"], "2026-09-25")
        self.assertEqual(event["location"]["name"], "TSC")

    def test_sportsevent_omits_incomplete_markup(self) -> None:
        self.assertIsNone(sports_event({"type": "regatta_report", "headline": "No slug"}))
        self.assertIsNone(sports_event({"type": "regatta_report", "event_id": "not-a-dated-slug"}))
        self.assertIsNone(sports_event({"type": "regatta_report", "event_id": "2026-99-99-pyc-bad"}))

    def test_newsarticle_about_only_complete_events(self) -> None:
        payload = news_article_jsonld(
            "2026-10-19",
            {
                "title": "The Weekend Roundup",
                "articles": [
                    {"type": "feature", "headline": "The Weekend Roundup", "byline": "SailingSA"},
                    {
                        "type": "regatta_report",
                        "event_id": "2026-10-17-pyc-kzn-mirror-regionals",
                        "headline": "Mirror at PYC",
                        "club": "PYC",
                        "start_date": "2026-10-17",
                    },
                    {"type": "regatta_report", "headline": "Unlinked mention"},
                ],
            },
        )
        self.assertEqual(payload["@type"], "NewsArticle")
        self.assertEqual(len(payload["about"]), 1)
        self.assertEqual(payload["about"][0]["startDate"], "2026-10-17")
        self.assertIn("location", payload["about"][0])


if __name__ == "__main__":
    unittest.main()
