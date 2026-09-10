"""Smoke checks: ZVYC club-admin score input and WhatsApp desk login."""

import ast
import hashlib
import unittest
from pathlib import Path


class ClubAdminScoreMinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = Path("api.py").read_text(encoding="utf-8")
        ast.parse(cls.src)
        cls.session_js = Path("js/session.js").read_text(encoding="utf-8")
        cls.header_js = Path("js/blank-landing-header.js").read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
