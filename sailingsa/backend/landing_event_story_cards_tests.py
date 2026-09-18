"""Pass C landing card unit tests (no DB)."""
from __future__ import annotations

import unittest
from datetime import date

from landing_event_story_cards import (
    LANDING_CARD_CSS,
    build_facts_html,
    build_story_html,
    countdown_label,
    history_sentence,
    render_card_html,
    results_cta_label,
    returning_line,
    select_hero_events,
)


TODAY = date(2026, 9, 18)


class CountdownTests(unittest.TestCase):
    def test_midmar_tomorrow(self):
        self.assertEqual(
            countdown_label(date(2026, 9, 19), date(2026, 9, 20), today=TODAY),
            "TOMORROW",
        )

    def test_tsc_days_to_go(self):
        self.assertEqual(
            countdown_label(date(2026, 9, 25), date(2026, 9, 27), today=TODAY),
            "7 DAYS TO GO",
        )

    def test_starts_today_and_day_of(self):
        self.assertEqual(
            countdown_label(date(2026, 9, 19), date(2026, 9, 20), today=date(2026, 9, 19)),
            "LIVE · DAY 1 OF 2",
        )
        self.assertEqual(
            countdown_label(date(2026, 9, 19), date(2026, 9, 20), today=date(2026, 9, 20)),
            "LIVE · DAY 2 OF 2",
        )

    def test_final_results(self):
        self.assertEqual(
            countdown_label(
                date(2026, 9, 12),
                date(2026, 9, 13),
                today=TODAY,
                result_status="Final",
            ),
            "FINAL RESULTS",
        )

    def test_no_fabricated_as_at(self):
        lab = countdown_label(date(2026, 9, 19), date(2026, 9, 20), today=TODAY, as_at_time=None)
        self.assertNotIn("17:30", lab)
        self.assertNotIn("Results updated", lab)


class HistoryBoundaryTests(unittest.TestCase):
    def test_bounded_wording_no_first_ever(self):
        s = history_sentence(
            "420 Nationals",
            [{"year": 2021}, {"year": 2024}, {"year": 2025}],
            current_year=2026,
        )
        self.assertEqual(s, "Results on record: 4 editions from 2021–2026")
        self.assertNotIn("SailingSA", s)
        self.assertNotIn("held by", s.lower())
        self.assertNotIn("first ever", s.lower())
        self.assertNotIn("every year", s.lower())
        self.assertNotIn("began in", s.lower())


class SelectHeroTests(unittest.TestCase):
    def test_midmar_then_tsc(self):
        rows = [
            {
                "regatta_id": "2026-09-19-hmyc-midmar-cup",
                "event_name": "The Midmar Cup",
                "start_date": date(2026, 9, 19),
                "end_date": date(2026, 9, 20),
                "result_status": "Provisional",
            },
            {
                "regatta_id": "2026-09-21-tsc-df95",
                "event_name": "TSC DF95",
                "start_date": date(2026, 9, 21),
                "end_date": date(2026, 9, 21),
                "result_status": "Provisional",
            },
            {
                "regatta_id": "2026-09-25-tsc-420-nationals",
                "event_name": "420 Nationals",
                "start_date": date(2026, 9, 25),
                "end_date": date(2026, 9, 27),
                "result_status": "Provisional",
            },
            {
                "regatta_id": "2026-10-24-ullman-sails-womens-series-day-2",
                "start_date": date(2026, 10, 24),
                "end_date": date(2026, 10, 24),
                "result_status": "event_page",
            },
        ]
        a, b = select_hero_events(rows, today=TODAY)
        self.assertEqual(a["regatta_id"], "2026-09-19-hmyc-midmar-cup")
        self.assertEqual(b["regatta_id"], "2026-09-25-tsc-420-nationals")


class StoryLinkTests(unittest.TestCase):
    def test_story_has_crawlable_anchors(self):
        card = {
            "name": "420 Nationals",
            "dates": "25–27 Sep 2026",
            "host": "TSC - Theewater Sports Club",
            "host_short": "TSC",
            "host_full": "Theewater Sports Club",
            "host_href": "/club/tsc",
            "host_logo": "/api/club-logo/TSC",
            "classes": ["420"],
            "class_logo": "/artwork/Class Logo/420-Class-Logo.png",
            "logo": "/artwork/Class Logo/420-Class-Logo.png",
            "entries": 0,
            "url": "/regatta/2026-09-25-tsc-420-nationals",
            "countdown": "7 DAYS TO GO",
            "history": "Results on record: 6 editions from 2018–2026",
            "series": {"label": "420 Nationals", "href": "/events-logos/420-nationals"},
            "previous": [{"url": "/regatta/2025-10-04-420-national-championship", "year": 2025}],
        }
        html = render_card_html(card, slot=2)
        story = build_story_html(card)
        facts = build_facts_html(card)
        self.assertIn("sa-home-regatta-card", html)
        self.assertIn('href="/club/tsc"', html)
        self.assertIn('href="/class/420"', html)
        self.assertIn('href="/regatta/2026-09-25-tsc-420-nationals"', html)
        self.assertIn("/api/club-logo/TSC", html)
        self.assertIn("/artwork/Class Logo/420-Class-Logo.png", html)
        self.assertIn("7 DAYS TO GO", html)
        self.assertIn("0 Entries", html)
        self.assertIn("25–27 Sep 2026", facts)
        self.assertIn("Results on record: 6 editions from 2018–2026", story)
        self.assertNotIn("held by SailingSA", story)
        self.assertNotIn("currently held", story)
        self.assertIn('href="/events-logos/420-nationals"', story)
        self.assertIn('href="/regatta/2025-10-04-420-national-championship"', story)
        self.assertIn("landing-event-inline-logo", story)
        self.assertIn("Previous:", story)
        self.assertNotIn("420 Nationals at TSC", story)
        self.assertNotIn("Hunter 19s are currently entered", html)
        self.assertNotIn("FULL RESULTS", html)
        self.assertNotIn("first ever", html.lower())
        self.assertNotIn("background: #001f3f", LANDING_CARD_CSS)
        self.assertIn("border: 2px solid #8aa2c6", LANDING_CARD_CSS)
        self.assertIn("border-radius: 6px", LANDING_CARD_CSS)
        self.assertIn("background: #fff", LANDING_CARD_CSS)


class AdditiveStoryTests(unittest.TestCase):
    def test_midmar_has_no_entry_filler(self):
        card = {
            "name": "The Midmar Cup",
            "dates": "19–20 Sep 2026",
            "host_short": "HMYC",
            "host_full": "Henley Midmar Yacht Club",
            "host_href": "/club/hmyc",
            "classes": ["Hunter 19"],
            "class_logo": "/artwork/Class Logo/Hunter-19-Class-Logo.png",
            "logo": "/artwork/Class Logo/Hunter-19-Class-Logo.png",
            "entries": 8,
            "url": "/regatta/2026-09-19-hmyc-midmar-cup",
            "countdown": "TOMORROW",
            "state": "upcoming",
            "scored_races": 0,
        }
        html = render_card_html(card, slot=1)
        self.assertEqual(build_story_html(card), "")
        self.assertNotIn("Hunter 19s are currently entered", html)
        self.assertNotIn("FULL RESULTS", html)
        self.assertNotIn("this weekend", html)

    def test_cta_upcoming_omits_full_results(self):
        self.assertEqual(results_cta_label("upcoming", 0, "Provisional"), "")
        self.assertEqual(results_cta_label("live", 0, "Provisional"), "LIVE RESULTS")
        self.assertEqual(results_cta_label("provisional", 10, "Provisional"), "PARTIAL RESULTS")
        self.assertEqual(results_cta_label("final", 10, "Final"), "FULL RESULTS")

    def test_returning_requires_sailor_id(self):
        podium = [{"place": 1, "name": "Jane Doe", "sailor_id": "99", "href": "/sailor/jane-doe"}]
        self.assertEqual(returning_line(podium, set()), "")
        self.assertIn("Defending winner", returning_line(podium, {"99"}))
        self.assertEqual(returning_line([{"place": 1, "name": "Jane Doe", "sailor_id": ""}], {"99"}), "")


if __name__ == "__main__":
    unittest.main()
