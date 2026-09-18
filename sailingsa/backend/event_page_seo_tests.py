"""Pass B lifecycle / title / JSON-LD tests (no DB)."""
from __future__ import annotations

import unittest
from datetime import date, datetime

from event_page_seo import (
    compact_event_date_range,
    count_event_entries_by_fleet,
    derive_event_lifecycle,
    event_context_footer_html,
    event_document_title,
    event_meta_description,
    event_schema_status,
    event_visible_status_text,
    sports_event_json_ld,
)


TODAY = date(2026, 9, 18)


class LifecycleTests(unittest.TestCase):
    def test_tsc_upcoming_zero_results_not_provisional(self):
        st = derive_event_lifecycle(
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 27),
            result_status="Provisional",
            as_at_time=None,
            raced_count=0,
            today=TODAY,
        )
        self.assertEqual(st, "upcoming")
        title = event_document_title("2026 420 Nationals", st, date(2026, 9, 25), date(2026, 9, 27))
        self.assertEqual(title, "2026 420 Nationals — 25–27 Sep 2026 | SailingSA")
        self.assertNotIn("Provisional Results", title)
        vis = event_visible_status_text(st, date(2026, 9, 25), date(2026, 9, 27))
        self.assertTrue(vis.startswith("Upcoming Event"))
        self.assertNotIn("17:30", vis)
        self.assertNotIn("Provisional", vis)

    def test_midmar_upcoming_despite_entries_and_null_as_at(self):
        st = derive_event_lifecycle(
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 20),
            result_status="Provisional",
            as_at_time=None,
            raced_count=8,
            today=TODAY,
        )
        self.assertEqual(st, "upcoming")
        vis = event_visible_status_text(st, date(2026, 9, 19), date(2026, 9, 20))
        self.assertEqual(vis, "Upcoming Event — 19–20 Sep 2026")
        self.assertNotIn("17:30", vis)

    def test_midmar_becomes_live_on_start_date(self):
        st = derive_event_lifecycle(
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 20),
            result_status="Provisional",
            as_at_time=None,
            raced_count=8,
            today=date(2026, 9, 19),
        )
        self.assertEqual(st, "live")
        title = event_document_title("2026 The Midmar Cup", st, date(2026, 9, 19), date(2026, 9, 20))
        self.assertIn("Live", title)

    def test_zvyc_final_not_scheduled(self):
        st = derive_event_lifecycle(
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 13),
            result_status="Final",
            as_at_time=datetime(2026, 9, 13, 18, 3),
            raced_count=52,
            today=TODAY,
        )
        self.assertEqual(st, "final")
        self.assertIsNone(event_schema_status(st))
        title = event_document_title(
            "2026 Zeekoe Vlei Cape Classic", st, date(2026, 9, 12), date(2026, 9, 13)
        )
        self.assertIn("Final Results", title)
        ld = sports_event_json_ld(
            name="2026 Zeekoe Vlei Cape Classic",
            canonical_url="https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic",
            state=st,
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 13),
        )
        self.assertNotIn("eventStatus", ld)

    def test_vulcan_provisional_past(self):
        st = derive_event_lifecycle(
            start_date=date(2026, 9, 13),
            end_date=date(2026, 9, 13),
            result_status="Provisional",
            as_at_time=datetime(2026, 9, 14, 19, 40),
            raced_count=15,
            today=TODAY,
        )
        self.assertEqual(st, "provisional")
        self.assertIsNone(event_schema_status(st))

    def test_upcoming_uses_eventscheduled(self):
        self.assertEqual(
            event_schema_status("upcoming"), "https://schema.org/EventScheduled"
        )
        self.assertEqual(event_schema_status("live"), "https://schema.org/EventScheduled")

    def test_meta_does_not_claim_results_for_tsc(self):
        d = event_meta_description(
            display_name="2026 420 Nationals",
            state="upcoming",
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 27),
            host_club="TSC - Theewater Sports Club",
            class_names=["420"],
            entries=0,
            raced_count=0,
        )
        self.assertNotIn("Provisional", d)
        self.assertNotIn("results", d.lower())
        self.assertIn("Theewater", d)

    def test_vulcan_event_total_sums_all_fleets(self):
        fleets = [
            {"class_canonical": "Hobie 16", "rows": [{}] * 4, "entries_raced": 4},
            {"class_canonical": "Hunter 19", "rows": [{}] * 10, "entries_raced": 10},
            {"fleet_label": "Keelboat Fleet", "class_original": "Keelboat", "rows": [{}] * 3, "entries_raced": 3},
        ]
        raced, total, per = count_event_entries_by_fleet(fleets)
        self.assertEqual(total, 17)
        self.assertEqual(sum(n for _name, n in per), 17)
        self.assertNotEqual(total, 10)

    def test_compact_dates(self):
        self.assertEqual(
            compact_event_date_range(date(2026, 9, 25), date(2026, 9, 27)),
            "25–27 Sep 2026",
        )
        self.assertEqual(
            compact_event_date_range(date(2026, 9, 19), date(2026, 9, 20)),
            "19–20 Sep 2026",
        )


class FooterAdditiveTests(unittest.TestCase):
    def test_midmar_primary_facts_do_not_repeat(self):
        html = event_context_footer_html(
            display_name="2026 The Midmar Cup",
            state="upcoming",
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 20),
            host_club="HMYC - Henley Midmar Yacht Club",
            host_club_href="/club/hmyc",
            venue="Henley Midmar Yacht Club KZN",
            class_names=["Hunter 19"],
            entries=8,
        )
        self.assertEqual(html, "")
        self.assertNotIn("Host:", html)
        self.assertNotIn("Entries:", html)
        self.assertNotIn("Upcoming Event", html)
        self.assertNotIn("Venue:", html)
        self.assertNotIn("Classes:", html)

    def test_series_previous_editions_remain(self):
        html = event_context_footer_html(
            display_name="420 Nationals",
            state="upcoming",
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 27),
            series_name="420 Nationals",
            series_href="/events-logos/420-nationals",
            edition_year=2026,
            previous_editions=[
                {"url": "/regatta/2025-10-04-420-national-championship", "year": 2025}
            ],
        )
        self.assertIn("/events-logos/420-nationals", html)
        self.assertIn("/regatta/2025-10-04-420-national-championship", html)
        self.assertNotIn("Host:", html)
        self.assertNotIn("Entries:", html)


if __name__ == "__main__":
    unittest.main()
