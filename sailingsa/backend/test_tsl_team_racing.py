"""Unit tests for TSL team racing — no live deploy, no invented sailors."""
from __future__ import annotations

import unittest

from sailingsa.backend.tsl_team_racing import (
    MAC_SEEDED_SAS,
    boat_points,
    is_tsl_regatta,
    match_does_not_use_current_roster,
    rank_standings,
    require_championship_teams,
    sailor_allowed_for_club,
    score_match,
    validate_roster_boats,
)


class TestRosterRules(unittest.TestCase):
    def test_duplicate_sailor_on_same_team_rejected(self):
        boats = [
            {"boat_no": 1, "helm_sas_id": "13516", "crew_sas_id": "21052"},
            {"boat_no": 2, "helm_sas_id": "13516", "crew_sas_id": "8612"},
        ]
        err = validate_roster_boats(boats)
        self.assertTrue(any("13516" in e for e in err))

    def test_helm_and_crew_same_person_rejected(self):
        err = validate_roster_boats([{"boat_no": 1, "helm_sas_id": "13516", "crew_sas_id": "13516"}])
        self.assertTrue(err)

    def test_six_distinct_mac_sailors_ok(self):
        boats = [
            {"boat_no": 1, "helm_sas_id": "13516", "crew_sas_id": "21052"},
            {"boat_no": 2, "helm_sas_id": "8612", "crew_sas_id": "29414"},
            {"boat_no": 3, "helm_sas_id": "13517", "crew_sas_id": "22974"},
        ]
        self.assertEqual(validate_roster_boats(boats), [])
        self.assertEqual(set(MAC_SEEDED_SAS), {"13516", "21052", "8612", "29414", "13517", "22974"})

    def test_missing_membership_not_excluded(self):
        sailor = {"sas_id": "29414", "name": "Thandokazi Sibanyoni", "primary_club": "", "club_1": ""}
        self.assertTrue(sailor_allowed_for_club(sailor, "MAC", "Milnerton Aquatic Club"))

    def test_verified_other_club_excluded(self):
        sailor = {"sas_id": "1", "name": "Other", "primary_club": "RCYC", "club_1": ""}
        self.assertFalse(sailor_allowed_for_club(sailor, "MAC", "Milnerton Aquatic Club"))

    def test_matching_club_included(self):
        sailor = {"sas_id": "13516", "name": "Kamva", "primary_club": "MAC", "club_1": ""}
        self.assertTrue(sailor_allowed_for_club(sailor, "MAC", "Milnerton Aquatic Club"))

    def test_slug_gated(self):
        self.assertTrue(is_tsl_regatta("2026-10-17-mac-tsl-wc-team-sailing"))
        self.assertFalse(is_tsl_regatta("2026-09-25-tsc-420-nationals"))
        self.assertFalse(is_tsl_regatta("hyc-cape-classic-2026"))

    def test_schedule_waits_for_eight_teams(self):
        with self.assertRaises(ValueError):
            require_championship_teams([1, 2, 3])
        require_championship_teams(list(range(1, 9)))


class TestAppendixDScoring(unittest.TestCase):
    def _boats(self, places):
        return [{"finish_place": p, "penalty_status": ""} for p in places]

    def test_nor_example_10_beats_11(self):
        # NOR: 2+3+5 = 10 beats 1+4+6 = 11
        out = score_match(self._boats([2, 3, 5]), self._boats([1, 4, 6]))
        self.assertEqual(out["score_a"], 10)
        self.assertEqual(out["score_b"], 11)
        self.assertEqual(out["winner"], "A")
        self.assertTrue(out["complete"])

    def test_1_2_3_is_perfect(self):
        out = score_match(self._boats([1, 2, 3]), self._boats([4, 5, 6]))
        self.assertEqual(out["score_a"], 6)
        self.assertEqual(out["score_b"], 15)
        self.assertEqual(out["winner"], "A")

    def test_duplicate_places_block_complete(self):
        out = score_match(self._boats([1, 2, 2]), self._boats([4, 5, 6]))
        self.assertFalse(out["complete"])
        self.assertTrue(any("unique" in e.lower() for e in out["errors"]))

    def test_duplicate_bow_and_sail(self):
        a = [
            {"finish_place": 1, "bow_number": "1", "sail_number": "12"},
            {"finish_place": 2, "bow_number": "2", "sail_number": "13"},
            {"finish_place": 3, "bow_number": "3", "sail_number": "14"},
        ]
        b = [
            {"finish_place": 4, "bow_number": "1", "sail_number": "15"},
            {"finish_place": 5, "bow_number": "5", "sail_number": "12"},
            {"finish_place": 6, "bow_number": "6", "sail_number": "16"},
        ]
        out = score_match(a, b)
        self.assertTrue(any("bow" in e.lower() for e in out["errors"]))
        self.assertTrue(any("sail" in e.lower() for e in out["errors"]))

    def test_dnf_scores_six(self):
        self.assertEqual(boat_points(None, "DNF"), 6)
        self.assertEqual(boat_points(2, "DSQ"), 6)
        a = [
            {"finish_place": 1, "penalty_status": ""},
            {"finish_place": 2, "penalty_status": ""},
            {"finish_place": 3, "penalty_status": ""},
        ]
        b = [
            {"finish_place": 4, "penalty_status": ""},
            {"finish_place": 5, "penalty_status": ""},
            {"finish_place": None, "penalty_status": "DNF"},
        ]
        out = score_match(a, b)
        self.assertEqual(out["score_b"], 15)
        self.assertEqual(out["winner"], "A")

    def test_team_penalty_can_change_winner(self):
        out = score_match(self._boats([1, 2, 3]), self._boats([4, 5, 6]), team_penalty_a=10)
        self.assertEqual(out["score_a"], 16)
        self.assertEqual(out["winner"], "B")

    def test_tied_scores_need_override(self):
        # 1+6+5 = 12 vs 2+4+6-with-penalty making both 12 is forced via team penalty
        out = score_match(self._boats([1, 2, 6]), self._boats([3, 4, 5]), team_penalty_a=3)
        self.assertEqual(out["score_a"], out["score_b"])
        self.assertFalse(out["complete"])
        ov = score_match(
            self._boats([1, 2, 6]),
            self._boats([3, 4, 5]),
            team_penalty_a=3,
            override_winner="B",
        )
        self.assertTrue(ov["complete"])
        self.assertEqual(ov["winner"], "B")

    def test_incomplete_places_not_complete(self):
        a = [{"finish_place": 1}, {"finish_place": 2}, {"finish_place": None}]
        b = self._boats([4, 5, 6])
        out = score_match(a, b)
        self.assertFalse(out["complete"])

    def test_empty_bow_sail_not_validated(self):
        a = [{"finish_place": 1}, {"finish_place": 2}, {"finish_place": 3}]
        b = [{"finish_place": 4}, {"finish_place": 5}, {"finish_place": 6}]
        out = score_match(a, b)
        self.assertTrue(out["complete"])


class TestStandings(unittest.TestCase):
    def test_one_match_updates_exactly_two_teams(self):
        teams = [
            {"team_id": 1, "team_name": "MAC", "result_id": 1},
            {"team_id": 2, "team_name": "UCT A", "result_id": 2},
            {"team_id": 3, "team_name": "SU", "result_id": 3},
        ]
        matches = [
            {
                "match_no": 1,
                "status": "complete",
                "team_a_id": 1,
                "team_b_id": 2,
                "score_a": 10,
                "score_b": 11,
                "winner_team_id": 1,
                "loser_team_id": 2,
            }
        ]
        rows = rank_standings(teams, matches)
        by = {r["team_id"]: r for r in rows}
        self.assertEqual(by[1]["cells"]["M1"], "W")
        self.assertEqual(by[2]["cells"]["M1"], "L")
        self.assertEqual(by[3]["cells"]["M1"], "—")
        self.assertEqual(by[1]["wins"], 1)
        self.assertEqual(by[2]["losses"], 1)
        self.assertEqual(by[3]["wins"], 0)
        self.assertEqual(by[1]["rank"], 1)

    def test_head_to_head_breaks_equal_wins(self):
        teams = [
            {"team_id": 1, "team_name": "A", "result_id": 1},
            {"team_id": 2, "team_name": "B", "result_id": 2},
            {"team_id": 3, "team_name": "C", "result_id": 3},
        ]
        matches = [
            {"match_no": 1, "status": "complete", "team_a_id": 1, "team_b_id": 2, "score_a": 10, "score_b": 11, "winner_team_id": 1, "loser_team_id": 2},
            {"match_no": 2, "status": "complete", "team_a_id": 2, "team_b_id": 3, "score_a": 8, "score_b": 13, "winner_team_id": 2, "loser_team_id": 3},
            {"match_no": 3, "status": "complete", "team_a_id": 1, "team_b_id": 3, "score_a": 12, "score_b": 9, "winner_team_id": 3, "loser_team_id": 1},
        ]
        # Each team 1-1. A beat B, B beat C, C beat A — cycle stays as a group
        rows = rank_standings(teams, matches)
        self.assertEqual([r["wins"] for r in rows], [1, 1, 1])

    def test_two_team_last_race_breaks_tie(self):
        teams = [
            {"team_id": 1, "team_name": "A", "result_id": 1},
            {"team_id": 2, "team_name": "B", "result_id": 2},
        ]
        matches = [
            {"match_no": 1, "status": "complete", "team_a_id": 1, "team_b_id": 2, "score_a": 10, "score_b": 11, "winner_team_id": 1, "loser_team_id": 2},
            {"match_no": 2, "status": "complete", "team_a_id": 1, "team_b_id": 2, "score_a": 12, "score_b": 9, "winner_team_id": 2, "loser_team_id": 1},
        ]
        rows = rank_standings(teams, matches)
        # last race winner is B
        self.assertEqual(rows[0]["team_id"], 2)
        self.assertEqual(rows[0]["rank"], 1)

    def test_open_match_is_dash(self):
        teams = [{"team_id": 1, "team_name": "MAC", "result_id": 1}, {"team_id": 2, "team_name": "SU", "result_id": 2}]
        matches = [{"match_no": 1, "status": "open", "team_a_id": 1, "team_b_id": 2}]
        rows = rank_standings(teams, matches)
        self.assertEqual(rows[0]["cells"]["M1"], "—")
        self.assertEqual(rows[1]["cells"]["M1"], "—")


class TestHistoricalRoster(unittest.TestCase):
    def test_completed_match_not_silently_rewritten_by_roster_edit(self):
        roster = [
            {"boat_no": 1, "helm_sas_id": "13516", "crew_sas_id": "21052"},
            {"boat_no": 2, "helm_sas_id": "8612", "crew_sas_id": "29414"},
            {"boat_no": 3, "helm_sas_id": "13517", "crew_sas_id": "22974"},
        ]
        historical = [
            {"pairing_no": 1, "helm_sas_id": "13516", "crew_sas_id": "21052"},
            {"pairing_no": 2, "helm_sas_id": "8612", "crew_sas_id": "99999"},
            {"pairing_no": 3, "helm_sas_id": "13517", "crew_sas_id": "22974"},
        ]
        self.assertTrue(match_does_not_use_current_roster(historical, roster))
        same = [
            {"pairing_no": 1, "helm_sas_id": "13516", "crew_sas_id": "21052"},
            {"pairing_no": 2, "helm_sas_id": "8612", "crew_sas_id": "29414"},
            {"pairing_no": 3, "helm_sas_id": "13517", "crew_sas_id": "22974"},
        ]
        self.assertFalse(match_does_not_use_current_roster(same, roster))


if __name__ == "__main__":
    unittest.main()
