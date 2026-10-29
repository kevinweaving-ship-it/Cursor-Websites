#!/usr/bin/env python3
from datetime import date
import unittest

from sailingsa.backend.event_page_seo import (
    build_regatta_pass_b,
    class_results_json_ld,
    countdown_label,
    derive_event_lifecycle,
    event_document_title,
    is_near_term_upcoming,
    match_event_news,
    sports_event_json_ld,
    upcoming_event_body_html,
)

TODAY = date(2026, 10, 18)


class EventLifecycleTests(unittest.TestCase):
    def test_future_event_is_upcoming_even_if_status_final(self):
        state = derive_event_lifecycle(
            start_date=date(2026, 10, 24),
            end_date=date(2026, 10, 24),
            result_status="Final",
            as_at_time=None,
            raced_count=0,
            today=TODAY,
        )
        self.assertEqual(state, "upcoming")
        title = event_document_title(
            "2026 Ullman Sails Women's Series — Day 2",
            state,
            date(2026, 10, 24),
            date(2026, 10, 24),
        )
        self.assertNotIn("Final Results", title)
        self.assertIn("Ullman", title)

    def test_started_final_stays_final(self):
        state = derive_event_lifecycle(
            start_date=date(2026, 10, 17),
            end_date=date(2026, 10, 18),
            result_status="Final",
            as_at_time=None,
            raced_count=0,
            today=TODAY,
        )
        self.assertEqual(state, "final")


class NearTermWindowTests(unittest.TestCase):
    def test_ullman_six_days_out_is_near_term(self):
        self.assertTrue(is_near_term_upcoming(date(2026, 10, 24), today=TODAY))
        self.assertEqual(
            countdown_label(date(2026, 10, 24), date(2026, 10, 24), today=TODAY),
            "6 DAYS TO GO",
        )

    def test_cape_classic_2027_is_too_far(self):
        # 118 days — should not have been created / featured yet.
        self.assertFalse(is_near_term_upcoming(date(2027, 2, 13), today=TODAY))
        self.assertEqual(
            countdown_label(date(2027, 2, 13), date(2027, 2, 14), today=TODAY),
            "118 DAYS TO GO",
        )


class UpcomingBodyTests(unittest.TestCase):
    def test_body_has_countdown_about_news_and_links(self):
        html = upcoming_event_body_html(
            display_name="2026 Ullman Sails Women's Series — Day 2",
            start_date=date(2026, 10, 24),
            end_date=date(2026, 10, 24),
            host_club="RCYC - Royal Cape Yacht Club",
            host_club_href="/club/rcyc",
            extra_urls=[
                {
                    "url": "https://rcyc.co.za/event/2026-ladies-race-day-2/",
                    "label": "RCYC event page",
                }
            ],
            previous_editions=[
                {
                    "url": "/regatta/2026-05-23-ullman-sails-womens-series-day-1",
                    "year": 2026,
                    "label": "Day 1",
                }
            ],
            today=TODAY,
        )
        self.assertIn("6 DAYS TO GO", html)
        self.assertIn("About", html)
        self.assertIn("News", html)
        self.assertIn("No news yet", html)
        self.assertIn("/club/rcyc", html)
        self.assertIn("rcyc.co.za/event/2026-ladies-race-day-2", html)
        self.assertIn("/events", html)
        self.assertIn('class="card"', html)
        self.assertIn("section-title", html)

    def test_news_match_keeps_only_related_items(self):
        hits = match_event_news(
            "2026 Ullman Sails Women's Series — Day 2",
            [
                {
                    "title": "Ullman Sails Women's Series preview",
                    "url": "https://example.com/ullman",
                    "excerpt": "Royal Cape",
                    "source": "Local",
                },
                {
                    "title": "Blessington Fireball Open",
                    "url": "https://www.sail-world.com/news/300200/",
                    "excerpt": "Fireballs",
                    "source": "Sail-World",
                },
            ],
        )
        self.assertEqual(len(hits), 1)
        self.assertIn("Ullman", hits[0]["title"])

    def test_pass_b_upcoming_html_and_status_countdown(self):
        bits = build_regatta_pass_b(
            display_name="2026 Ullman Sails Women's Series — Day 2",
            canonical_url="https://sailingsa.co.za/regatta/2026-10-24-ullman-sails-womens-series-day-2",
            base_url="https://sailingsa.co.za",
            start_date=date(2026, 10, 24),
            end_date=date(2026, 10, 24),
            result_status="event_page",
            as_at_time=None,
            host_club="RCYC - Royal Cape Yacht Club",
            host_club_href="/club/rcyc",
            extra_urls=[
                {
                    "url": "https://rcyc.co.za/event/2026-ladies-race-day-2/",
                    "label": "RCYC event page",
                }
            ],
            today=TODAY,
        )
        self.assertEqual(bits["state"], "upcoming")
        self.assertIn("6 DAYS TO GO", bits["status_visible"])
        self.assertNotIn("Final Results", bits["title"])
        self.assertIn("6 DAYS TO GO", bits["upcoming_html"])
        self.assertIn("News", bits["upcoming_html"])


class EventJsonLdTests(unittest.TestCase):
    def test_required_fields_and_no_nested_event(self):
        data = sports_event_json_ld(
            name="2026 Zeekoe Vlei Cape Classic",
            canonical_url="https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic",
            state="final",
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 13),
            host_club="ZVYC - Zeekoe Vlei Yacht Club",
            host_club_url="https://sailingsa.co.za/club/zvyc",
            province="Western Cape",
            series_name="ZVYC Cape Classic",
            series_url="https://sailingsa.co.za/yearly-events",
        )
        self.assertEqual(data["@type"], "SportsEvent")
        self.assertEqual(data["startDate"], "2026-09-12")
        self.assertEqual(data["location"]["@type"], "Place")
        self.assertEqual(data["location"]["address"]["addressCountry"], "ZA")
        self.assertEqual(data["eventStatus"], "https://schema.org/EventScheduled")
        self.assertEqual(data["organizer"]["url"], "https://sailingsa.co.za/club/zvyc")
        self.assertNotIn("superEvent", data)
        self.assertNotIn("offers", data)
        self.assertNotIn("performer", data)

    def test_slug_date_and_country_fallback(self):
        data = sports_event_json_ld(
            name="Tour de Vlei",
            canonical_url="https://sailingsa.co.za/regatta/2026-10-24-vyc-tour-de-vlei",
            state="upcoming",
            start_date=None,
            end_date=None,
        )
        self.assertEqual(data["startDate"], "2026-10-24")
        self.assertEqual(data["endDate"], "2026-10-24")
        self.assertEqual(data["location"]["name"], "South Africa")
        self.assertEqual(data["organizer"]["name"], "SailingSA")

    def test_no_event_without_date(self):
        data = sports_event_json_ld(
            name="Nameless",
            canonical_url="https://sailingsa.co.za/regatta/lipton",
            state="upcoming",
            start_date=None,
            end_date=None,
        )
        self.assertEqual(data, {})

    def test_class_sheet_is_not_an_event(self):
        data = class_results_json_ld(
            event_name="2026 Zeekoe Vlei Cape Classic",
            class_name="420",
            canonical_url="https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic/class-420",
            event_url="https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic",
            base_url="https://sailingsa.co.za",
        )
        self.assertEqual(data["@type"], "BreadcrumbList")
        blob = str(data)
        self.assertNotIn("SportsEvent", blob)
        self.assertNotIn("Event", blob.replace("Events", ""))


if __name__ == "__main__":
    unittest.main()
