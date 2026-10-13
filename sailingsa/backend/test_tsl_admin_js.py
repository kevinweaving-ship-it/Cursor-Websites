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
        self.assertIn("Save Team", JS)
        self.assertIn("M+", JS)
        self.assertIn("M−", JS)
        self.assertIn("Team Blue", JS)
        self.assertIn("Team Green", JS)
        self.assertIn("Generate schedule", JS)
        self.assertIn("eight teams", JS)
        self.assertIn("not invented", JS)
        self.assertNotIn("Physical boats", JS)
        self.assertNotIn("bow_number", JS)
        self.assertNotIn("sail_number", JS)
        self.assertNotIn("club-score-edit.js", JS)
        self.assertIn("20261013i", JS)
        self.assertIn("macTslGoldSheet", JS)
        self.assertIn("tslGoldTable", JS)
        self.assertIn("insertGoldRaceTable", JS)
        self.assertIn("goldRaceNos", JS)
        self.assertIn("macTslTeamsCard", JS)
        self.assertIn("insertTeamsCard", JS)
        self.assertIn("tsl-team-card", JS)
        self.assertIn("tsl-team-cards", JS)
        self.assertIn("2px solid #1a2750", JS)
        self.assertIn("gap:8px", JS)
        self.assertIn("Helm Name", JS)
        self.assertIn("localeCompare", JS)
        self.assertIn("closedMatches", JS)
        self.assertIn("wonLast", JS)
        self.assertIn("winner_team_id", JS)
        self.assertIn("syncSheetType", JS)
        self.assertIn("max-height:16px", JS)
        self.assertIn("max-width:28px", JS)
        self.assertIn("white-space:nowrap", JS)
        self.assertIn("club-col", JS)
        self.assertIn("clubCell", JS)
        self.assertIn("class-header", JS)
        self.assertIn("action-button", JS)
        self.assertIn("table-wrapper", JS)
        self.assertIn("fleet-section", JS)
        self.assertNotIn("section-title", JS)
        self.assertNotIn('el.className = "card"', JS)
        self.assertNotIn("0.9rem", JS)
        self.assertNotIn("36px", JS)

    def test_one_results_table_transformed(self):
        self.assertIn("applyStandingsTable", JS)
        self.assertIn("insertGoldRaceTable", JS)
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
        self.assertIn('th.textContent = "W"', JS)
        self.assertNotIn('lab === "team" || lab === "boat name"', JS)


class TestTslLiveCardsStd(unittest.TestCase):
    def test_media_is_hmyc_six_slot_strip(self):
        cards = (ROOT / "js" / "mac-tsl-live-cards.js").read_text(encoding="utf-8")
        self.assertNotIn("sizeMacBrand", cards)
        self.assertNotIn("mac-tsl-reels--logo-only", cards)
        self.assertNotIn("markLogoOnly", cards)
        self.assertNotIn("fillMacLogoTile", cards)
        self.assertNotIn("MAC_ART_W", cards)
        self.assertNotIn("2014 / 780", cards)
        self.assertIn("mm-lipton-reels-card.js?v=mactslmedia3", cards)
        self.assertIn("calc(100% - 4px)", cards)
        self.assertIn("mm-lipton-reels--compact", cards)
        self.assertIn("mm-lipton-reels-rail-wrap", cards)
        self.assertIn("/img/mac-event-reels.jpg", cards)
        self.assertIn("background:#fff!important", cards)
        self.assertIn("20261012o", cards)
        self.assertIn("#eventInfoStrip", cards)
        self.assertIn("hideEventInfoStrip", cards)
        self.assertIn("regatta-entry.js", cards)

    def test_live_patch_skips_eis_for_tsl_only(self):
        patch = (ROOT / "sailingsa" / "deploy" / "patch_live_mac_tsl_wc_event_url.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("EIS_FN_INSERT", patch)
        self.assertIn("EIS_CALL_INSERT", patch)
        self.assertIn('_tsl_no_eis = str(regatta_id) == "2026-10-17-mac-tsl-wc-team-sailing"', patch)
        self.assertIn("2026-09-13-zvyc-cape-classic", patch)
        self.assertIn("mac-tsl-live-cards.js?v=20261012o", patch)
        media = (ROOT / "sailingsa" / "deploy" / "patch_live_mac_tsl_media.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("keep HMYC brand width", media)


if __name__ == "__main__":
    unittest.main()
