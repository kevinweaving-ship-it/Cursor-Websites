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
    is_major_upcoming_event,
    is_midmar_cup_event,
    render_card_html,
    resolve_podium_hrefs,
    results_cta_label,
    returning_line,
    select_hero_events,
    should_show_on_regatta_list,
    should_show_upcoming_on_landing,
    upcoming_visible_window_days,
)
from card_left_logo import preferred_event_slot_logo, resolve_card_left_logo


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

    def test_window_hides_far_upcoming_keeps_major_14(self):
        self.assertTrue(is_major_upcoming_event("SA Sailing Youth Nationals", "2026-11-01-youth-nationals"))
        self.assertEqual(upcoming_visible_window_days("Youth Nationals", "2026-11-01-youth"), 14)
        self.assertEqual(upcoming_visible_window_days("Ullman Sails Women's Series", "2026-10-24-ullman"), 7)
        self.assertTrue(
            should_show_upcoming_on_landing(
                date(2026, 9, 30), "Youth Nationals", "2026-09-30-youth", today=TODAY
            )
        )
        self.assertFalse(
            should_show_upcoming_on_landing(
                date(2026, 9, 30), "Club Twilight", "2026-09-30-twilight", today=TODAY
            )
        )
        rows = [
            {
                "regatta_id": "2026-09-30-youth-nationals",
                "event_name": "SA Sailing Youth Nationals",
                "start_date": date(2026, 9, 30),
                "end_date": date(2026, 10, 4),
                "result_status": "event_page",
            },
            {
                "regatta_id": "2026-09-30-club-twilight",
                "event_name": "Club Twilight",
                "start_date": date(2026, 9, 30),
                "end_date": date(2026, 9, 30),
                "result_status": "event_page",
            },
            {
                "regatta_id": "2026-10-24-ullman-sails-womens-series-day-2",
                "event_name": "Ullman Sails Women's Series",
                "start_date": date(2026, 10, 24),
                "end_date": date(2026, 10, 24),
                "result_status": "event_page",
            },
        ]
        a, b = select_hero_events(rows, today=TODAY)
        self.assertEqual(a["regatta_id"], "2026-09-30-youth-nationals")
        self.assertIsNone(b)
        self.assertFalse(
            should_show_on_regatta_list(date(2026, 10, 24), today=TODAY, is_live=False)
        )
        self.assertTrue(
            should_show_on_regatta_list(date(2026, 9, 12), today=TODAY, is_live=False)
        )
        self.assertTrue(
            should_show_on_regatta_list(date(2026, 10, 24), today=TODAY, is_live=True)
        )

    def test_ullman_event_logo_matches_list_card(self):
        src = resolve_card_left_logo(
            "2026-10-24 Ullman Sails Women's Series — Day 2",
            "2026-10-24-ullman-sails-womens-series-day-2",
        )
        self.assertEqual(src, "/artwork/Event Logo/Ullman-Sails-Woman-Series.png")
        slot = preferred_event_slot_logo(
            name="Ullman Sails Women's Series",
            regatta_id="2026-10-24-ullman-sails-womens-series-day-2",
        )
        self.assertEqual(slot, "/artwork/Event Logo/Ullman-Sails-Woman-Series.png")
        html = render_card_html(
            {
                "name": "Ullman Sails Women's Series — Day 2",
                "url": "/regatta/2026-10-24-ullman-sails-womens-series-day-2",
                "logo": slot,
                "countdown": "5 DAYS TO GO",
                "state": "upcoming",
                "dates": "24 Oct 2026",
                "entries": 0,
                "host_short": "RCYC",
                "host_full": "Royal Cape Yacht Club",
            },
            slot=1,
        )
        self.assertIn("/artwork/Event Logo/Ullman-Sails-Woman-Series.png", html)
        self.assertIn("sa-home-regatta-event-logo", html)
        self.assertIn("sa-home-regatta-days-pill", html)
        self.assertIn("5 DAYS TO GO", html)
        self.assertIn("Upcoming event", html)
        self.assertIn("sa-home-regatta-btn--upcoming", html)


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
            "podium": [
                {"place": 1, "name": "Dominique Provoyeur", "href": "/sailor/dominique-provoyeur"},
            ],
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
        self.assertIn("sa-home-regatta-days-pill", html)
        self.assertIn("0 Entries", html)
        self.assertIn("25–27 Sep 2026", facts)
        self.assertNotIn("Results on record", story)
        self.assertNotIn("held by SailingSA", story)
        self.assertNotIn("currently held", story)
        self.assertIn('href="/regatta/2025-10-04-420-national-championship"', story)
        self.assertIn("2025 420 Champions", story)
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
        self.assertIn("landing-event-card-open", html)

    def test_midmar_uses_named_entries_not_fake_history(self):
        card = {
            "name": "The Midmar Cup",
            "class_logo": "/artwork/Class Logo/Hunter-19-Class-Logo.png",
            "url": "/regatta/2026-09-19-hmyc-midmar-cup",
            "entered": [
                {"name": "Paul Changuion", "href": "/sailor/paul-changuion"},
                {"name": "Hayden Miller", "href": "/sailor/hayden-miller",
                 "crew_name": "Timothy Weaving", "crew_href": "/sailor/timothy-weaving"},
            ],
        }
        story = build_story_html(card)
        self.assertEqual(story, "")
        self.assertNotIn("2025 RESULTS", story)
        self.assertNotIn("Hunter Nationals", story)
        self.assertNotIn("Grand Slam", story)
        self.assertNotIn("Defending winner", story)

    def test_midmar_cup_identity_rejects_other_hmyc_events(self):
        self.assertTrue(is_midmar_cup_event("The Midmar Cup", "2026-09-19-hmyc-midmar-cup"))
        self.assertFalse(is_midmar_cup_event("2024 Hunter Nationals", "2024-03-24-hunter-nationals"))
        self.assertFalse(is_midmar_cup_event("HMYC Grand Slam", "2025-01-27-hmyc-grand-slam"))
        self.assertFalse(is_midmar_cup_event("Henley Midmar Yacht Club 6&9 Hour", "2024-02-24-hmyc-6hr-race"))

    def test_cta_upcoming_omits_full_results(self):
        self.assertEqual(results_cta_label("upcoming", 0, "Provisional"), "Upcoming event")
        self.assertEqual(results_cta_label("live", 0, "Provisional"), "LIVE RESULTS")
        self.assertEqual(results_cta_label("provisional", 10, "Provisional"), "PARTIAL RESULTS")
        self.assertEqual(results_cta_label("final", 10, "Final"), "FULL RESULTS")

    def test_returning_requires_sailor_id(self):
        podium = [{"place": 1, "name": "Jane Doe", "sailor_id": "99", "href": "/sailor/jane-doe"}]
        self.assertEqual(returning_line(podium, set()), "")
        self.assertIn("Defending winner", returning_line(podium, {"99"}))
        self.assertEqual(returning_line([{"place": 1, "name": "Jane Doe", "sailor_id": ""}], {"99"}), "")

    def test_podium_story_is_one_tiny_logo_line(self):
        card = {
            "name": "420 Nationals",
            "logo": "/artwork/Class Logo/420-Class-Logo.png",
            "class_logo": "/artwork/Class Logo/420-Class-Logo.png",
            "series": {"label": "420 Nationals", "href": "/events-logos/420-nationals"},
            "history": "Results on record: 6 editions from 2018–2026",
            "previous": [{"url": "/regatta/2025-10-04-420-national-championship", "year": 2025}],
            "podium": [
                {"place": 1, "name": "Dominique Provoyeur", "href": "/sailor/dominique-provoyeur"},
                {"place": 2, "name": "Tristan Gress", "href": "/sailor/tristan-gress"},
                {"place": 3, "name": "Abdull Alexander", "href": "/sailor/abdull-alexander"},
            ],
        }
        story = build_story_html(card)
        html = render_card_html(card, slot=2)
        self.assertIn("2025 Champions", story)
        self.assertIn('href="/sailor/dominique-provoyeur"', story)
        self.assertNotIn("Results on record", story)
        self.assertNotIn("Defending winner", story)
        self.assertIn('style="width:78px;height:58px', html)
        self.assertIn("landing-event-card-open", html)
        self.assertIn("color: #3d5a8a", LANDING_CARD_CSS)
        self.assertNotIn("width:100%", html)
        self.assertEqual(resolve_podium_hrefs(None, card["podium"]), card["podium"])

    def test_logo_css_cannot_size_the_card(self):
        self.assertIn("img:not(.landing-event-inline-logo)", LANDING_CARD_CSS)
        self.assertIn("width: 78px !important", LANDING_CARD_CSS)
        self.assertIn("width: 14px !important", LANDING_CARD_CSS)
        self.assertIn("#landing-event-hero-2 {\n    display: block !important;", LANDING_CARD_CSS)
        self.assertIn("#landing-event-hero-2 .sa-home-regatta-top", LANDING_CARD_CSS)


if __name__ == "__main__":
    unittest.main()
