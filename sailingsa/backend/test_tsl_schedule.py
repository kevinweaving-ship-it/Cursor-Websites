"""Schedule tests — 28 RR, 16 flights, colour balance, sail-offs. Synthetic teams only."""
from __future__ import annotations

import unittest

from sailingsa.backend.tsl_schedule import (
    FORMAT_FLIGHTS16,
    FORMAT_RR28,
    all_unique_pairings,
    changeover_stays,
    championship_from_sailoffs,
    color_counts,
    generate_flights16,
    generate_rr_matches,
    preview_format_switch,
    resolve_sailoff_teams,
    validate_schedule,
)


class TestRoundRobin28(unittest.TestCase):
    def setUp(self):
        self.ids = list(range(1, 9))
        self.matches = generate_rr_matches(self.ids)

    def test_twenty_eight_unique_pairings(self):
        self.assertEqual(len(self.matches), 28)
        pairs = [frozenset((m["blue_team_id"], m["green_team_id"])) for m in self.matches]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertEqual(set(pairs), set(all_unique_pairings(self.ids)))

    def test_each_team_plays_seven(self):
        counts = color_counts(self.matches, self.ids)
        for t, c in counts.items():
            self.assertEqual(c["blue"] + c["green"], 7, t)

    def test_blue_green_is_four_three(self):
        counts = color_counts(self.matches, self.ids)
        for t, c in counts.items():
            self.assertIn(sorted((c["blue"], c["green"])), ([3, 4],), t)

    def test_no_team_on_both_sides(self):
        for m in self.matches:
            self.assertNotEqual(m["blue_team_id"], m["green_team_id"])

    def test_stay_on_boats_happens(self):
        self.assertGreaterEqual(changeover_stays(self.matches), 10)

    def test_validate_clean(self):
        self.assertEqual(validate_schedule(self.matches, self.ids, FORMAT_RR28), [])

    def test_fewer_than_eight_still_unique(self):
        ids = [1, 2, 3]
        ms = generate_rr_matches(ids)
        self.assertEqual(len(ms), 3)


class TestFlights16(unittest.TestCase):
    def setUp(self):
        self.a = [1, 2, 3, 4]
        self.b = [5, 6, 7, 8]
        self.matches = generate_flights16(self.a, self.b)

    def test_sixteen_matches(self):
        self.assertEqual(len(self.matches), 16)
        self.assertEqual(len([m for m in self.matches if m["phase"] == "flight_a"]), 6)
        self.assertEqual(len([m for m in self.matches if m["phase"] == "flight_b"]), 6)
        self.assertEqual(len([m for m in self.matches if m["phase"] == "sailoff"]), 4)

    def test_flight_pairings_unique(self):
        fa = [m for m in self.matches if m["phase"] == "flight_a"]
        pairs = [frozenset((m["blue_team_id"], m["green_team_id"])) for m in fa]
        self.assertEqual(set(pairs), set(all_unique_pairings(self.a)))

    def test_sailoffs_are_placeholders(self):
        so = [m for m in self.matches if m["phase"] == "sailoff"]
        self.assertEqual([m["match_no"] for m in so], [13, 14, 15, 16])
        self.assertEqual([m["sailoff_slot"] for m in so], [1, 2, 3, 4])
        for m in so:
            self.assertIsNone(m["blue_team_id"])

    def test_no_overlap_between_flights(self):
        with self.assertRaises(ValueError):
            generate_flights16([1, 2, 3, 4], [4, 5, 6, 7])

    def test_sailoff_resolution_and_places(self):
        a_rank = [{"team_id": i, "rank": n} for n, i in enumerate([1, 2, 3, 4], start=1)]
        b_rank = [{"team_id": i, "rank": n} for n, i in enumerate([5, 6, 7, 8], start=1)]
        slots = resolve_sailoff_teams(a_rank, b_rank)
        self.assertEqual(slots[1], (1, 5))
        self.assertEqual(slots[4], (4, 8))
        sailoffs = [
            {"sailoff_slot": 1, "status": "complete", "winner_team_id": 1, "loser_team_id": 5},
            {"sailoff_slot": 2, "status": "complete", "winner_team_id": 6, "loser_team_id": 2},
            {"sailoff_slot": 3, "status": "complete", "winner_team_id": 3, "loser_team_id": 7},
            {"sailoff_slot": 4, "status": "complete", "winner_team_id": 8, "loser_team_id": 4},
        ]
        places = championship_from_sailoffs(sailoffs)
        self.assertEqual(places[1], 1)
        self.assertEqual(places[5], 2)
        self.assertEqual(places[6], 3)
        self.assertEqual(places[2], 4)
        self.assertEqual(places[8], 7)
        self.assertEqual(places[4], 8)

    def test_format_switch_keeps_completed(self):
        existing = [
            {"match_no": 1, "label": "M1", "status": "complete", "team_a_id": 1, "team_b_id": 2},
            {"match_no": 2, "label": "M2", "status": "open", "team_a_id": 3, "team_b_id": 4},
        ]
        incoming = generate_rr_matches(list(range(1, 9)))
        prev = preview_format_switch(existing, incoming)
        self.assertEqual(prev["keep_completed"], 1)
        self.assertEqual(prev["replace_open"], 1)
        self.assertTrue(prev["needs_confirm"])


if __name__ == "__main__":
    unittest.main()
