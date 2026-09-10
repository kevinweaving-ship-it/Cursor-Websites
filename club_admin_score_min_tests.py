"""Smoke checks: ZVYC club-admin score input and WhatsApp desk login."""

import ast
import hashlib
import re
import unittest
from pathlib import Path
from typing import Optional


class _FakeHTTPException(Exception):
    def __init__(self, status_code=400, detail=""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _load_score_helpers():
    src = Path("api.py").read_text(encoding="utf-8")
    start = src.find("_RACE_PENALTY_CODES =")
    end = src.find("def _lookup_club_id_by_abbrev")
    ns = {
        "re": re,
        "Optional": Optional,
        "HTTPException": _FakeHTTPException,
    }
    exec(src[start:end], ns)
    return ns


class ClubAdminScoreMinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = Path("api.py").read_text(encoding="utf-8")
        ast.parse(cls.src)
        cls.session_js = Path("js/session.js").read_text(encoding="utf-8")
        cls.header_js = Path("js/blank-landing-header.js").read_text(encoding="utf-8")
        cls.club_js = Path("js/club-score-edit.js").read_text(encoding="utf-8")

    def test_club_admin_role_and_host_scope(self):
        self.assertIn("def _session_role_is_club_admin", self.src)
        self.assertIn("def _session_can_edit_regatta_scores", self.src)
        self.assertIn("def _require_regatta_score_edit", self.src)
        self.assertIn("_require_regatta_score_edit(request, result.get(\"regatta_id\"))", self.src)
        self.assertNotIn(
            "_require_super_admin(request)\n    import json",
            self.src[self.src.find("def patch_race_score") : self.src.find("def patch_race_score") + 400],
        )

    def test_zvyc_whatsapp_desk_login(self):
        self.assertIn('_ZVYC_CLUB_WHATSAPP = "0217053373"', self.src)
        self.assertIn('_ZVYC_CLUB_LOGIN_SAS = "ZVYC"', self.src)
        self.assertIn("def _ensure_zvyc_club_whatsapp_admin", self.src)
        self.assertIn("def _ensure_zvyc_club_desk_personal", self.src)
        self.assertIn("_is_zvyc_club_whatsapp(username)", self.src)
        self.assertIn("INSERT INTO public.sas_id_personal", self.src)
        self.assertIn("ZVYC_CLUB_ADMIN_PASSWORD", self.src)
        self.assertEqual(
            hashlib.sha256(b"ZVYC1234").hexdigest(),
            hashlib.sha256(b"ZVYC1234").hexdigest(),
        )

    def test_club_admin_avatar_is_club_logo(self):
        self.assertIn("def _club_admin_avatar_url", self.src)
        self.assertIn('return f"/api/club-logo/{code}"', self.src)
        self.assertIn('"avatar_url": _club_admin_avatar_url(admin_club_abbrev)', self.src)
        self.assertIn("/api/club-logo/ZVYC", self.src)
        self.assertIn("avatarUrl", self.session_js)
        self.assertIn("s.avatar_url", self.header_js)
        self.assertIn("opts.avatarUrl", self.session_js)

    def test_race_score_inputs_not_wc_editor(self):
        self.assertIn("def _club_score_race_cell", self.src)
        self.assertIn("regatta-page--club-score-edit", self.src)
        self.assertIn("race_score_edit=race_score_edit", self.src)
        self.assertIn("/api/result/'+encodeURIComponent(rid)+'/race'", self.src)
        render = self.src[
            self.src.find("def _render_result_sheet_fleet") : self.src.find("_REGATTA_404_HTML")
        ]
        self.assertIn("race_score_edit: bool = False", render)
        self.assertIn("_club_score_race_cell", render)
        self.assertNotIn("regatta-sa-toolbar.js", render)

    def test_no_new_sailor_and_no_facebook_graph(self):
        desk = self.src[
            self.src.find("_ZVYC_CLUB_WHATSAPP") : self.src.find("def _fetch_og_metadata")
        ]
        self.assertIn("INSERT INTO public.sas_id_personal", desk)
        self.assertIn('_ZVYC_CLUB_LOGIN_SAS = "ZVYC"', desk)
        self.assertNotIn("14496", desk)
        self.assertNotIn("live_videos", self.src)
        self.assertIn("mm-lipton-track-overlay.js?v=mmr102", self.src)

    def test_appendix_a_discard_and_rank(self):
        h = _load_score_helpers()
        self.assertEqual(h["_appendix_a_discard_count"](4), 0)
        self.assertEqual(h["_appendix_a_discard_count"](5), 1)
        self.assertEqual(h["_appendix_a_discard_count"](9), 1)
        self.assertEqual(h["_appendix_a_discard_count"](10), 2)
        self.assertEqual(h["_appendix_a_discard_count"](15), 3)

        # ILCA 9 boats: place is the place; OCS / 10 score 10
        self.assertEqual(h["_appendix_a_cell_points"]("1", 9), 1.0)
        self.assertEqual(h["_appendix_a_cell_points"]("ocs", 9), 10.0)
        self.assertEqual(h["_appendix_a_cell_points"]("OCS", 9), 10.0)
        self.assertEqual(h["_appendix_a_cell_points"]("10", 9), 10.0)
        self.assertEqual(h["_appendix_a_cell_points"]("DSQ", 9), 10.0)

        scores, total, nett = h["_appendix_a_apply_series"](
            {"R1": "1", "R2": "2", "R3": "3", "R4": "4", "R5": "9"},
            5,
            9,
        )
        self.assertEqual(total, 19.0)
        self.assertEqual(nett, 10.0)
        self.assertEqual(scores["R5"], "(9)")
        self.assertEqual(scores["R1"], "1")

        # Five-race series with a code: discard the n+1, keep places
        scores, total, nett = h["_appendix_a_apply_series"](
            {"R1": "2", "R2": "OCS", "R3": "1", "R4": "3", "R5": "4"},
            5,
            9,
        )
        self.assertEqual(total, 20.0)
        self.assertEqual(nett, 10.0)
        self.assertEqual(scores["R2"], "(OCS)")

        ranked = h["_appendix_a_rank_entries"](
            [
                {"result_id": 3, "nett": 12},
                {"result_id": 1, "nett": 6},
                {"result_id": 2, "nett": 6},
                {"result_id": 4, "nett": None},
            ]
        )
        self.assertEqual([r["result_id"] for r in ranked], [1, 2, 3, 4])
        self.assertEqual([r["rank"] for r in ranked], [1, 2, 3, 4])
        self.assertIn("_appendix_a_apply_series", self.src)
        self.assertIn("_appendix_a_rank_entries", self.src)
        self.assertIn("rank by lowest nett", self.src)
        self.assertIn("Total and Nett are automatic", self.src)
        self.assertIn("club-score-auto", self.src)
        self.assertIn("total_points_raw", self.src[self.src.find("def _render_result_sheet_fleet") :])
        render = self.src[
            self.src.find("def _render_result_sheet_fleet") : self.src.find("_REGATTA_404_HTML")
        ]
        self.assertIn('td class="total-col club-score-auto', render)
        self.assertIn('td class="nett-col club-score-auto', render)
        self.assertIn("if race_score_edit and not wc_sa_fleet_edit:", render)
        self.assertIn("td.race-col[data-race-key]", self.club_js)
        self.assertIn("Enter = next boat", self.club_js)
        self.assertIn("Total, Nett, Rank auto", self.club_js)
        self.assertIn("function sessionToken", self.club_js)
        self.assertIn("body: JSON.stringify({ race: race, value: v, session: tok })", self.club_js)
        self.assertIn("function ensureR1", self.club_js)
        self.assertIn("function applyFleetRow", self.club_js)
        self.assertIn("function focusOffset", self.club_js)
        self.assertIn("min-height:22px", self.club_js)
        self.assertNotIn("location.reload", self.club_js)
        self.assertNotIn("inp.disabled = true", self.club_js)
        self.assertNotIn("alert(", self.club_js)
        self.assertIn("races_sailed = max(existing_block_rs, filled_races, race_num)", self.src)
        self.assertIn('startswith("2026-09-13-zvyc-cape-classic")', self.src)

    def test_places_unique_codes_repeat(self):
        h = _load_score_helpers()
        self.assertEqual(h["_validate_race_score_value"]("3", 9), "3")
        self.assertEqual(h["_validate_race_score_value"]("10", 9), "10")
        self.assertEqual(h["_validate_race_score_value"]("ocs", 9), "OCS")
        self.assertEqual(h["_race_score_unique_place"]("3", 9), 3)
        self.assertIsNone(h["_race_score_unique_place"]("10", 9))
        self.assertIsNone(h["_race_score_unique_place"]("OCS", 9))
        with self.assertRaises(_FakeHTTPException):
            h["_validate_race_score_value"]("11", 9)


if __name__ == "__main__":
    unittest.main()
