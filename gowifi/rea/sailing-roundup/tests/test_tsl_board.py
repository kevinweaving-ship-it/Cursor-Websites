#!/usr/bin/env python3
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from tsl_board import apply_parent_tsl_board, gold_built, overlay_tsl_rows

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "mac-tsl-state.json"


def _state():
    return json.loads(FIXTURE.read_text())


class ParentTslBoard(unittest.TestCase):
    def test_gold_built_matches_parent_sheet(self):
        board = gold_built(_state())
        names = [item["team_name"] for item in board]
        self.assertEqual(
            names,
            [
                "RCYCA A",
                "Eden District",
                "MAC",
                "MATIES",
                "University of Cape Town Yacht Club",
            ],
        )
        self.assertEqual([item["rank"] for item in board], [1, 2, 3, 4, 5])
        self.assertEqual([item["wins"] for item in board], [4, 3, 2, 1, 0])
        self.assertEqual([item["points"] for item in board], [34, 50, 51, 67, 65])
        self.assertEqual(board[0]["flights"][15], "6")
        self.assertEqual(board[1]["flights"][15], "15")

    def test_overlay_stamps_regatta_rows(self):
        rows = [
            {"boat_name": "MAC", "result_id": 21336, "rank": None, "helm_name": "Maddison Smit"},
            {"boat_name": "RCYCA A", "result_id": 21342, "rank": None, "helm_name": "Hayden Miller"},
            {"boat_name": "izivungu", "result_id": 21368, "rank": None},
        ]
        out = apply_parent_tsl_board(rows, _state())
        self.assertEqual(out[0]["boat_name"], "RCYCA A")
        self.assertEqual(out[0]["rank"], 1)
        self.assertEqual(out[0]["team_wins"], 4)
        self.assertEqual(out[1]["boat_name"], "MAC")
        self.assertEqual(out[1]["rank"], 3)
        self.assertIsNone(out[2]["rank"])

    def test_overlay_skips_non_team_cards(self):
        rows = [{"scoring_system": "Appendix A", "rank": 1, "helm_name": "Dale Rae"}]
        self.assertEqual(overlay_tsl_rows("2026-09-25-tsc-420-nationals", rows, state=_state()), rows)


if __name__ == "__main__":
    unittest.main()
