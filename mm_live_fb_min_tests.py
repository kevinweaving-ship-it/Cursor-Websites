"""Smoke checks for manual-URL MM card (no Graph, no schema)."""

import ast
import json
import unittest
from pathlib import Path


class MinimalMmFeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = Path("api.py").read_text(encoding="utf-8")
        ast.parse(cls.src)
        cls.feed = json.loads(Path("sailingsa/deploy/event_fb_feeds.json").read_text(encoding="utf-8"))

    def test_no_facebook_graph_or_schema(self):
        self.assertNotIn("live_videos", self.src)
        self.assertNotIn("mm_live_fb_videos", self.src)
        self.assertNotIn("import mm_live_fb", self.src)
        self.assertNotIn("ALTER TABLE regattas ADD COLUMN mm_live_fb", self.src)

    def test_insert_point_and_compact_card(self):
        self.assertIn("header_html + mm_card + sa_columns_frag", self.src)
        self.assertIn('id="mmLiveFbCard"', self.src)
        self.assertIn("mm-live-fb-card--compact", self.src)
        self.assertIn("data-mm-hide", self.src)
        self.assertIn("data-mm-fs", self.src)
        self.assertIn("/js/mm-live-fb-card.js", self.src)
        self.assertIn("2026-08-29-lipton-challenge-cup", self.src)
        self.assertIn("2026-09-13-zvyc-cape-classic", self.src)

    def test_seeded_manual_urls(self):
        self.assertTrue(self.feed["2026-08-29-lipton-challenge-cup"]["enabled"])
        self.assertTrue(self.feed["2026-09-13-zvyc-cape-classic"]["enabled"])
        self.assertEqual(self.feed["2026-08-29-lipton-challenge-cup"]["feed_source"], "marine-megastore")
        self.assertIn("https://www.facebook.com/share/v/1957ykQ9qA/", json.dumps(self.feed))


if __name__ == "__main__":
    unittest.main()
