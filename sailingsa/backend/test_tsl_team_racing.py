"""Unit tests for TSL team racing — no live deploy, no invented sailors."""
from __future__ import annotations

import unittest

from sailingsa.backend.tsl_team_racing import (
    MAC_SEEDED_SAS,
    apply_flight_sheet_action,
    apply_official_flights_12_15,
    boat_points,
    empty_flight_sheet,
    is_tsl_regatta,
    match_does_not_use_current_roster,
    rank_standings,
    require_championship_teams,
    sailor_allowed_for_club,
    score_match,
    stamp_tsl_final,
    stamp_tsl_provisional,
    validate_roster_boats,
    _cell,
    _norm_flight_sheet,
    ROSTER_LINES,
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

    def test_roster_line_four_is_valid_empty_pair(self):
        self.assertEqual(ROSTER_LINES, 4)
        boats = [
            {"boat_no": 1, "helm_sas_id": "13516", "crew_sas_id": "21052"},
            {"boat_no": 2, "helm_sas_id": "8612", "crew_sas_id": "29414"},
            {"boat_no": 3, "helm_sas_id": "13517", "crew_sas_id": "22974"},
            {"boat_no": 4, "helm_sas_id": "", "crew_sas_id": ""},
        ]
        self.assertEqual(validate_roster_boats(boats), [])
        cell = _cell({"colour": "Blue", "team_id": 8, "rank": 1, "boat_no": 4})
        self.assertEqual(cell["boat_no"], 4)
        self.assertIsNone(_cell({"colour": "Blue", "team_id": 8, "boat_no": 5})["boat_no"])

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


class TestFlightSheetActions(unittest.TestCase):
    def _filled(self, n=3):
        sheet = empty_flight_sheet()
        for fl in ("1", "2", "3", "4"):
            sheet[fl] = {
                str(b): {"colour": "Blue", "team_id": n, "rank": b, "boat_no": 1}
                for b in range(1, 7)
            }
            sheet.setdefault("boats_per_team", {})[fl] = 3
        return sheet

    def test_clear_wipes_one_flight(self):
        out = apply_flight_sheet_action(self._filled(), action="clear", flight=1)
        self.assertEqual(out["1"]["1"]["team_id"], None)
        self.assertEqual(out["2"]["1"]["team_id"], 3)
        self.assertIn("3", out)

    def test_remove_later_keeps_first_pair(self):
        out = apply_flight_sheet_action(self._filled(), action="remove", flight=1)
        self.assertIn("1", out)
        self.assertIn("2", out)
        self.assertNotIn("3", out)
        self.assertNotIn("4", out)
        self.assertEqual(out["1"]["1"]["team_id"], 3)

    def test_remove_pair_drops_from_that_pair(self):
        out = apply_flight_sheet_action(self._filled(), action="remove", flight=3)
        self.assertIn("1", out)
        self.assertIn("2", out)
        self.assertNotIn("3", out)
        self.assertNotIn("4", out)

    def test_reset_empty_one_and_two_only(self):
        out = apply_flight_sheet_action(self._filled(), action="reset")
        self.assertEqual(sorted(k for k in out if k.isdigit()), ["1", "2"])
        self.assertIsNone(out["1"]["1"]["team_id"])
        self.assertIsNone(out["2"]["6"]["rank"])

    def test_score_adjust_survives_norm_and_drops_on_clear(self):
        sheet = self._filled()
        sheet["score_adjust"] = {
            "3": {"3": {"delta": 1, "reason": "Officials' scoresheet"}},
            "4": {"1": {"delta": 1, "reason": "Officials' scoresheet"}},
        }
        kept = _norm_flight_sheet(sheet)
        self.assertEqual(kept["3"]["2"]["rank"], 2)
        self.assertEqual(kept["score_adjust"]["3"]["3"]["delta"], 1)
        self.assertEqual(kept["score_adjust"]["3"]["3"]["reason"], "Officials' scoresheet")
        cleared = apply_flight_sheet_action(kept, action="clear", flight=3)
        self.assertNotIn("3", cleared.get("score_adjust") or {})
        self.assertEqual(cleared["score_adjust"]["4"]["1"]["delta"], 1)
        removed = apply_flight_sheet_action(kept, action="remove", flight=3)
        self.assertNotIn("score_adjust", removed)

    def test_official_flights_12_15_from_scoresheet(self):
        sheet = self._filled()
        sheet["score_adjust"] = {
            "3": {"3": {"delta": 1, "reason": "Officials' scoresheet"}},
            "4": {"1": {"delta": 1, "reason": "Officials' scoresheet"}},
        }
        out = apply_official_flights_12_15(sheet)
        self.assertEqual(out["1"]["1"]["team_id"], 3)
        self.assertEqual(out["score_adjust"]["3"]["3"]["delta"], 1)
        want = {
            "12": ([8, 15], [1, 4, 2, 3, 6, 5], (7, 14)),
            "13": ([1, 12], [1, 4, 3, 6, 2, 5], (8, 13)),
            "14": ([3, 15], [3, 5, 6, 2, 4, 1], (14, 7)),
            "15": ([4, 8], [4, 5, 6, 3, 1, 2], (15, 6)),
        }
        for fl, (teams, ranks, scores) in want.items():
            blue = [out[fl][str(b)] for b in (1, 2, 3)]
            green = [out[fl][str(b)] for b in (4, 5, 6)]
            self.assertEqual([c["team_id"] for c in blue], [teams[0]] * 3)
            self.assertEqual([c["team_id"] for c in green], [teams[1]] * 3)
            self.assertEqual([c["rank"] for c in blue + green], ranks)
            self.assertEqual(sum(c["rank"] for c in blue), scores[0])
            self.assertEqual(sum(c["rank"] for c in green), scores[1])
            self.assertEqual(out["boats_per_team"][fl], 3)


class _FakeCur:
    def __init__(self, status=""):
        self.status = status
        self.sql = []
        self._last = ""

    def execute(self, sql, args=None):
        self.sql.append(" ".join(str(sql).split()))
        self._last = self.sql[-1]
        self.args = args

    def fetchone(self):
        if "information_schema.columns" in self._last:
            return {"column_name": "result_status"}
        return {"result_status": self.status}


class TestStampTslProvisional(unittest.TestCase):
    def test_sets_provisional_when_blank(self):
        cur = _FakeCur("")
        stamp_tsl_provisional(cur, "2026-10-17-mac-tsl-wc-team-sailing")
        joined = "\n".join(cur.sql)
        self.assertIn("result_status = 'Provisional'", joined)
        self.assertIn("as_at_time = NOW()", joined)
        self.assertIn("UPDATE public.results", joined)

    def test_does_not_overwrite_final(self):
        cur = _FakeCur("Final")
        stamp_tsl_provisional(cur, "2026-10-17-mac-tsl-wc-team-sailing")
        joined = "\n".join(cur.sql)
        self.assertNotIn("UPDATE public.regattas", joined)
        self.assertNotIn("UPDATE public.results", joined)

    def test_ignores_other_regattas(self):
        cur = _FakeCur("")
        stamp_tsl_provisional(cur, "2026-09-19-hmyc-midmar-cup")
        self.assertEqual(cur.sql, [])


class TestStampTslFinal(unittest.TestCase):
    def test_sets_final(self):
        cur = _FakeCur("Provisional")
        stamp_tsl_final(cur, "2026-10-17-mac-tsl-wc-team-sailing")
        joined = "\n".join(cur.sql)
        self.assertIn("result_status = 'Final'", joined)
        self.assertIn("as_at_time = NOW()", joined)
        self.assertIn("UPDATE public.results", joined)

    def test_ignores_other_regattas(self):
        cur = _FakeCur("Provisional")
        stamp_tsl_final(cur, "2026-09-19-hmyc-midmar-cup")
        self.assertEqual(cur.sql, [])


if __name__ == "__main__":
    unittest.main()
