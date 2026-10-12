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

    def test_event_logo_uses_event_logo_folder(self):
        self.assertIn('/artwork/Event Logo/TSL-Team-Sailing.png', API)
        self.assertIn('MAC_TSL_WC_2026_EVENT_LOGO', API)

    def test_results_table_team_not_club_duplicate(self):
        self.assertIn('thead += "<th>Team</th>" if is_mac_tsl else "<th>Boat Name</th>"', API)
        self.assertIn("if _pref_on(\"club\") and not is_mac_tsl:", API)
        self.assertIn("tsl-team-club", API)


class TestTslLiveCardsStd(unittest.TestCase):
    def test_media_brand_is_std_hmyc_slot(self):
        cards = (ROOT / "js" / "mac-tsl-live-cards.js").read_text(encoding="utf-8")
        self.assertNotIn("2014/780", cards)
        self.assertNotIn("sizeMacBrand", cards)
        self.assertIn("mm-lipton-reels--compact", cards)
        self.assertIn("20261012j", cards)


if __name__ == "__main__":
    unittest.main()
