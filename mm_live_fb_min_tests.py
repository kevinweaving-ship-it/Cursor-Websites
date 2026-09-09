"""Smoke checks for the minimal MM ON/OFF + card insert (no Facebook, no schema)."""

import ast
import unittest
from pathlib import Path


class MinimalMmFeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = Path("api.py").read_text(encoding="utf-8")
        ast.parse(cls.src)

    def test_no_facebook_live_or_schema(self):
        self.assertNotIn("live_videos", self.src)
        self.assertNotIn("mm_live_fb_videos", self.src)
        self.assertNotIn("mm_live_fb_feed.json", self.src)
        self.assertNotIn("import mm_live_fb", self.src)
        self.assertNotIn("ALTER TABLE regattas ADD COLUMN mm_live_fb", self.src)

    def test_cape_classic_default_on_and_insert_point(self):
        self.assertIn('"2026-09-13-zvyc-cape-classic"', self.src)
        self.assertIn("header_html + mm_card + sa_columns_frag", self.src)
        self.assertIn('id="mmLiveFbCard"', self.src)
        self.assertIn('id="regattaMmLiveFbFeed"', self.src)
        self.assertIn(">LIVE VIDEO</h2>", self.src)
        self.assertIn('src="/assets/adverts/marine-megastore-logo.png"', self.src)
        self.assertIn('href="https://marinemegastore.co.za"', self.src)
        self.assertIn("https://www.facebook.com/share/v/1957ykQ9qA/", self.src)
        self.assertIn("plugins/video.php", self.src)


if __name__ == "__main__":
    unittest.main()
