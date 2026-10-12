"""Contract checks for the TSL admin UI — no second results table, slug-gated."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = (ROOT / "js" / "mac-tsl-admin.js").read_text(encoding="utf-8")
API = (ROOT / "api.py").read_text(encoding="utf-8")


class TestTslAdminContract(unittest.TestCase):
    def test_slug_gated_and_simple_dropdowns(self):
        self.assertIn("2026-10-17-mac-tsl-wc-team-sailing", JS)
        self.assertIn("Add Team", JS)
        self.assertIn("M+", JS)
        self.assertIn("M−", JS)
        self.assertIn("Team Blue", JS)
        self.assertIn("Team Green", JS)
        self.assertIn("Generate schedule", JS)
        self.assertIn("Physical boats", JS)
        self.assertIn("not invented", JS)
        self.assertNotIn("club-score-edit.js", JS)

    def test_one_results_table_transformed(self):
        self.assertIn("applyStandingsTable", JS)
        self.assertNotIn("tsl-results-2", JS)
        self.assertNotIn("id=\"tslOverall2\"", JS)
        self.assertLessEqual(JS.count("createElement(\"table\")"), 0)

    def test_api_mount_is_additive(self):
        self.assertIn("TSL_TEAM_RACING_ROUTES_v1", API)
        self.assertIn("register_tsl_routes", API)


if __name__ == "__main__":
    unittest.main()
