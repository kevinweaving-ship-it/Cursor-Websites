#!/usr/bin/env python3
"""MM Facebook token keeper: mint never-expiring Page token, never save explorer sessions."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("MM_FB_APP_ID", "1614644650032287")
os.environ.setdefault("MM_FB_APP_SECRET", "test-secret")
os.environ["MM_FB_APP_ENV"] = "/tmp/does-not-exist-mm-fb.env"

import mm_fb_graph_live as mod  # noqa: E402


class TokenKeepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MM_FB_DATA_DIR"] = self.tmp.name
        os.environ["MM_FB_APP_ID"] = "1614644650032287"
        os.environ["MM_FB_APP_SECRET"] = "test-secret"
        os.environ["MM_FB_APP_ENV"] = str(Path(self.tmp.name) / "missing.env")
        os.environ.pop("FACEBOOK_APP_ID", None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_app_id_does_not_use_sailor_facebook_app(self):
        os.environ["FACEBOOK_APP_ID"] = "885045914172033"
        os.environ["MM_FB_APP_ID"] = "1614644650032287"
        self.assertEqual(mod.app_id(), "1614644650032287")

    def test_pick_mm_page_by_id(self):
        row = mod.pick_mm_page(
            [{"id": "159493827253568", "name": "Marine Megastore", "access_token": "PAGE"}]
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["access_token"], "PAGE")

    def test_inspect_never_expires(self):
        with mock.patch.object(
            mod,
            "graph",
            return_value={"data": {"is_valid": True, "type": "PAGE", "expires_at": 0, "app_id": "1614644650032287"}},
        ):
            dbg = mod.inspect_token("PAGE")
        self.assertTrue(dbg["never_expires"])
        self.assertTrue(dbg["is_valid"])

    def test_mint_saves_user_and_page(self):
        calls = []

        def fake_graph(path, token, params=None, method="GET"):
            calls.append(path)
            if path == "oauth/access_token":
                return {"access_token": "LONG_USER"}
            if path == "me/accounts":
                self.assertEqual(token, "LONG_USER")
                return {
                    "data": [
                        {
                            "id": "159493827253568",
                            "name": "Marine Megastore",
                            "access_token": "NEVER_PAGE",
                            "username": "marin.megastoresa",
                        }
                    ]
                }
            if path == "debug_token":
                return {"data": {"is_valid": True, "type": "PAGE", "expires_at": 0}}
            if path.endswith("/subscribed_apps") or path.endswith("/subscriptions"):
                return {"success": True}
            return {}

        with mock.patch.object(mod, "graph", side_effect=fake_graph), mock.patch.object(
            mod, "commit_graph_now", return_value={"ok": True, "live": []}
        ):
            res = mod.mint_page_from_user("SHORT_USER")
        self.assertTrue(res["ok"])
        self.assertTrue(res["never_expires"])
        self.assertEqual(Path(self.tmp.name, "mm_fb_user.token").read_text().strip(), "LONG_USER")
        self.assertEqual(Path(self.tmp.name, "mm_fb_page.token").read_text().strip(), "NEVER_PAGE")
        self.assertIn("oauth/access_token", calls)

    def test_mint_refuses_when_exchange_fails(self):
        with mock.patch.object(mod, "exchange_user_token", return_value=""):
            res = mod.mint_page_from_user("SHORT_USER")
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "exchange_failed")
        self.assertFalse(Path(self.tmp.name, "mm_fb_page.token").exists())

    def test_keep_remints_when_user_valid_page_dead(self):
        Path(self.tmp.name, "mm_fb_user.token").write_text("USER\n")
        Path(self.tmp.name, "mm_fb_page.token").write_text("DEAD_PAGE\n")

        def inspect(tok):
            if tok == "USER":
                return {"is_valid": True, "type": "USER", "expires_at": 9999999999, "never_expires": False}
            if tok == "NEVER_PAGE":
                return {"is_valid": True, "type": "PAGE", "expires_at": 0, "never_expires": True}
            return {"is_valid": False, "type": "PAGE", "expires_at": 1, "never_expires": False, "error": "expired"}

        with mock.patch.object(mod, "inspect_token", side_effect=inspect), mock.patch.object(
            mod,
            "mint_page_from_user",
            return_value={
                "ok": True,
                "never_expires": True,
                "page_id": "159493827253568",
                "page_name": "Marine Megastore",
                "page": {"is_valid": True, "type": "PAGE", "expires_at": 0, "never_expires": True},
            },
        ):
            st = mod.keep_tokens(force=True)
        self.assertTrue(st["ok"])
        self.assertFalse(st["needs_login"])
        self.assertEqual(st["action"], "minted")

    def test_keep_needs_login_when_both_dead(self):
        Path(self.tmp.name, "mm_fb_user.token").write_text("DEAD_USER\n")
        Path(self.tmp.name, "mm_fb_page.token").write_text("DEAD_PAGE\n")
        dead = {"is_valid": False, "type": "PAGE", "expires_at": 1, "never_expires": False, "error": "expired", "error_code": 190}
        with mock.patch.object(mod, "inspect_token", return_value=dead):
            st = mod.keep_tokens(force=True)
        self.assertTrue(st["needs_login"])
        self.assertEqual(st["action"], "dead")
        self.assertFalse(st["ok"])

    def test_keep_ok_when_page_never_expires_and_user_dead(self):
        Path(self.tmp.name, "mm_fb_page.token").write_text("NEVER_PAGE\n")

        def inspect(tok):
            if tok == "NEVER_PAGE":
                return {"is_valid": True, "type": "PAGE", "expires_at": 0, "never_expires": True}
            return {"is_valid": False, "type": "USER", "expires_at": 1, "never_expires": False}

        with mock.patch.object(mod, "inspect_token", side_effect=inspect), mock.patch.object(
            mod, "subscribe_page", return_value={"success": True}
        ):
            st = mod.keep_tokens(force=True)
        self.assertTrue(st["ok"])
        self.assertFalse(st["needs_login"])
        self.assertEqual(st["action"], "page_never_expires")

    def test_status_json_has_no_token_values(self):
        Path(self.tmp.name, "mm_fb_page.token").write_text("SECRETTOKENVALUE\n")
        dead = {"is_valid": False, "type": "PAGE", "expires_at": 1, "never_expires": False, "error": "expired", "error_code": 190}
        with mock.patch.object(mod, "inspect_token", return_value=dead):
            mod.keep_tokens(force=True)
        blob = Path(self.tmp.name, "mm_fb_token_status.json").read_text()
        self.assertNotIn("SECRETTOKENVALUE", blob)
        data = json.loads(blob)
        self.assertIn("needs_login", data)


if __name__ == "__main__":
    unittest.main()
