"""Offline security regression tests for SailingSA's REA deployment helpers.

No SSH, production filesystem, services, or database access is required.
"""
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "gowifi" / "rea" / "ops" / "ops_helper.py"
spec = importlib.util.spec_from_file_location("rea_ops_helper_test", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class FrontendZipSafetyTests(unittest.TestCase):
    def test_blocks_traversal_and_preserves_excluded_data(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            archive = root / "release.zip"
            webroot = root / "www"
            webroot.mkdir()
            data = webroot / "data"
            data.mkdir()
            (data / "hub_hero.json").write_text('{"live":true}', encoding="utf-8")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("index.html", "safe")
                zf.writestr("data/hub_hero.json", '{"wrong":true}')
                zf.writestr("../escape.txt", "unsafe")
                zf.writestr("..\\escape2.txt", "unsafe")
                zf.writestr("/absolute.txt", "unsafe")
                zf.writestr("notes.md", "excluded")
                zf.writestr("previous.bak", "excluded")

            result = helper._safe_unzip(archive, webroot)

            self.assertEqual((webroot / "index.html").read_text(), "safe")
            self.assertEqual((data / "hub_hero.json").read_text(), '{"live":true}')
            self.assertFalse((root / "escape.txt").exists())
            self.assertFalse((root / "escape2.txt").exists())
            self.assertEqual(len(result["rejected"]), 3)
            self.assertIn("data/hub_hero.json", result["skipped"])
            self.assertFalse((webroot / "notes.md").exists())
            self.assertFalse((webroot / "previous.bak").exists())

    def test_no_unapproved_api_replacement(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            missing = root / "missing.py"
            denied = helper._api_gate(missing, "0" * 64)
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["error"], "missing_stage")

            small = root / "api.py"
            small.write_text("print('small')\n", encoding="utf-8")
            denied = helper._api_gate(small, "0" * 64)
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["error"], "stale_size")

    def test_approval_is_exact_hash(self):
        with tempfile.TemporaryDirectory() as dirname:
            stage = Path(dirname) / "api.py"
            stage.write_bytes(b"# safe test file\n" + b" " * helper.GOLD_MIN_BYTES)
            for approved, expected in [("", "approval_required"), ("0" * 64, "approval_mismatch")]:
                with self.subTest(expected=expected):
                    denied = helper._api_gate(stage, approved)
                    self.assertFalse(denied["ok"])
                    self.assertEqual(denied["error"], expected)


if __name__ == "__main__":
    unittest.main()
