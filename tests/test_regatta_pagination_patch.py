"""Offline invariants for the exact-hash regatta pagination preparer."""
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "sailingsa/performance/prepare_regatta_pagination.py"
spec = importlib.util.spec_from_file_location("regatta_paging_patch", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PagingPatchTests(unittest.TestCase):
    def test_client_offset_is_safely_bounded(self):
        source = """async function getRegattas(params) {
    const sp = new URLSearchParams();
    if (params.limit != null) sp.set('limit', String(params.limit));
        const qs = sp.toString();
    return apiRequest(qs);
}
"""
        patched = mod.patch_api_js(source)
        self.assertIn("sp.set('offset', String(offset));", patched)
        self.assertIn("Math.min(500", patched)
        self.assertEqual(patched.count("sp.set('offset'"), 1)

    def test_exact_source_guard_denies_unexpected_revision(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "input.js"
            target = Path(td) / "output.js"
            source.write_text("something unrelated", encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.prepare("js/api.js", source, target)
            self.assertFalse(target.exists())

    def test_never_overwrite_original(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "same.html"
            src.write_text("safe", encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.prepare("index.html", src, src)

    def test_pager_required_in_live_patch(self):
        src = MODULE.read_text(encoding="utf-8")
        for required in (
            "limit: 30, offset: state.offset",
            "state.seen.has(id)",
            "IntersectionObserver",
            "_stopRegattaPager();",
            "state.offset += rows.length",
            "outputTarget || document.getElementById",
            "return out[_offset:_page_end]",
        ):
            self.assertIn(required, src)


if __name__ == "__main__":
    unittest.main()
