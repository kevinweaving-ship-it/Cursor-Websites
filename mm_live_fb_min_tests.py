"""Smoke checks: MM helpers may exist, but the generic regatta renderer must not inject them."""

import ast
import unittest
from pathlib import Path


class MinimalMmFeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = Path("api.py").read_text(encoding="utf-8")
        ast.parse(cls.src)

    def test_no_facebook_graph_or_schema(self):
        self.assertNotIn("live_videos", self.src)
        self.assertNotIn("mm_live_fb_videos", self.src)
        self.assertNotIn("import mm_live_fb", self.src)
        self.assertNotIn("ALTER TABLE regattas ADD COLUMN mm_live_fb", self.src)

    def test_regatta_renderer_does_not_inject_mm(self):
        self.assertIn("header_html + mm_card + sa_columns_frag", self.src)
        self.assertIn("mm_card = \"\"", self.src)
        self.assertIn("mm_card_js = \"\"", self.src)
        self.assertIn('mm_feed_on = False', self.src)
        self.assertNotIn("{(_MM_LIVE_FB_CSS if mm_feed_on else '')}", self.src)
        serve = self.src[self.src.find("print_btn = "): self.src.find("REGATTA: total route time")]
        self.assertNotIn("mm-live-fb-card.js", serve)
        self.assertNotIn("_mm_live_fb_card_html(str(regatta_id))", serve)
        self.assertIn("onclick=\"window.print()\"", serve)


if __name__ == "__main__":
    unittest.main()
