"""Offline tests for the surgical production API hotfix preparer."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "sailingsa/performance/prepare_club_search_hotfix.py"
spec = importlib.util.spec_from_file_location("club_hotfix", MODULE)
hotfix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hotfix)

SOURCE = """def api_search_clubs():
    rows = q(sql, params)
    for r in rows or []:
        name = (r.get("name") or r.get("code") or "").strip()
    return rows

@app.get("/api/member/search")
def downstream():
    return None
"""


class ClubSearchHotfixTests(unittest.TestCase):
    def test_surgical_stage_and_preserve_original(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "api.py"
            dst = Path(td) / "stage.py"
            src.write_text(SOURCE, encoding="utf-8")
            digest = hashlib.sha256(src.read_bytes()).hexdigest()
            new_digest = hotfix.prepare(src, dst, expected_sha256=digest)
            self.assertEqual(src.read_text(), SOURCE)
            self.assertNotEqual(new_digest, digest)
            self.assertIn("cur.execute(sql, params)", dst.read_text())
            self.assertIn("RealDictCursor", dst.read_text())
            self.assertEqual(dst.read_text().count("cur.execute(sql, params)"), 1)

    def test_refuses_unknown_or_same_source(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "api.py"
            src.write_text(SOURCE, encoding="utf-8")
            with self.assertRaises(ValueError):
                hotfix.prepare(src, Path(td) / "out.py", expected_sha256="0" * 64)
            with self.assertRaises(ValueError):
                hotfix.prepare(src, src, expected_sha256=hashlib.sha256(src.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
