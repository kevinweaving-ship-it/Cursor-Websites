"""Smoke checks: MM helpers may exist, but only Lipton 2026 injects the Event Reels card."""

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

    def test_regatta_renderer_injects_mm_on_lipton_only(self):
        self.assertIn("header_html + mm_card + sa_columns_frag", self.src)
        self.assertIn("mm_card = \"\"", self.src)
        self.assertIn('mm_feed_on = False', self.src)
        self.assertNotIn("{(_MM_LIVE_FB_CSS if mm_feed_on else '')}", self.src)
        serve = self.src[self.src.find("print_btn = "): self.src.find("REGATTA: total route time")]
        self.assertNotIn("mm-live-fb-card.js", serve)
        self.assertNotIn("_mm_live_fb_card_html(str(regatta_id))", serve)
        self.assertIn("_lipton_mm_reels_card_html(str(regatta_id))", serve)
        self.assertIn('2026-08-29-lipton-challenge-cup', serve)
        self.assertIn("mm-lipton-reels-card.js", serve)
        self.assertIn("onclick=\"window.print()\"", serve)
        self.assertNotIn("2026-09-13-zvyc-cape-classic", serve)


class LiptonMmCardUnitTest(unittest.TestCase):
    def test_helper_is_hard_scoped(self):
        src = Path("api.py").read_text(encoding="utf-8")
        start = src.find("def _lipton_mm_reels_card_html")
        end = src.find("@app.patch(\"/api/super-admin/regatta/{regatta_id}/mm-live-fb-feed\")")
        fn = src[start:end]
        seed = src[src.find("_LIPTON_MM_REELS_VIDEOS"): src.find("_LIPTON_MM_REELS_CSS")]
        self.assertIn('_LIPTON_MM_REGATTA_ID = "2026-08-29-lipton-challenge-cup"', src)
        self.assertIn('if str(regatta_id or "").strip() != _LIPTON_MM_REGATTA_ID:', fn)
        self.assertIn("mmLiptonReels", fn)
        self.assertEqual(fn.count("mm-powered-by-event-reels.png"), 1)
        self.assertNotIn("LIVE VIDEO", fn)
        self.assertNotIn("Fullscreen", fn)
        self.assertNotIn("DEFENDER", fn)
        self.assertNotIn("timadvisor", seed.lower())
        self.assertIn("marin.megastoresa", seed)
        self.assertNotIn("data-mm-hide", fn)
        self.assertNotIn("mm-lipton-reels-hide", fn)
        self.assertNotIn("data-mm-expanded", fn)
        self.assertIn("data-mm-compact", fn)
        self.assertIn("data-mm-rail-prev", fn)
        self.assertIn("data-mm-rail-next", fn)
        self.assertIn("2622643364847262", seed)
        css = src[src.find("_LIPTON_MM_REELS_CSS"): src.find("def _lipton_mm_reels_payload")]
        self.assertNotIn("mm-lipton-reels-stamp", css)
        self.assertIn(".mm-lipton-reels-hero-ui", css)
        self.assertIn("mm-lipton-reels-stage--playing", css)
        self.assertIn("width:44px", css)
        self.assertIn("margin:auto", css)
        self.assertIn("flex-direction:column", css)
        self.assertIn("#00B4FF", css)
        self.assertIn("background:transparent", css)
        self.assertNotIn("#50C0F8", css)
        self.assertIn("-webkit-line-clamp:2", css)
        self.assertIn("max-width:14ch", css)
        self.assertIn(".mm-lipton-reels-clip-chrome", css)
        self.assertIn("fb-page-marine-megastore.jpg", seed)
        self.assertIn("Lipton  Race 7 1st downwind", seed)
        self.assertIn(".regatta-page>.regatta-header-wrap{order:1}", css)
        self.assertIn(".regatta-page>.mm-lipton-reels{order:2}", css)
        self.assertIn(".regatta-page>.fleet-section{order:3}", css)
        self.assertIn(".regatta-page>.action-buttons{order:10}", css)
        self.assertIn(".header.header--lipton{display:grid!important", css)
        self.assertIn(".header.header--lipton .regatta-lipton-venue-cohost .regatta-lipton-host-logo", css)
        self.assertIn("max-height:24px!important", css)
        self.assertIn("#dce6ef", css)
        self.assertNotIn("mm-lipton-reels-fb-label", css)
        self.assertIn("display:none!important", css)
        js = Path("js/mm-lipton-reels-card.js").read_text(encoding="utf-8")
        self.assertNotIn("Marine Megastore was live", js)
        self.assertNotIn("mm-lipton-reels-fb-label", js)
        self.assertNotIn("fbLabelHtml", js)
        self.assertIn("data-mm-hide", js)
        self.assertIn("expandedHtml", js)
        self.assertIn("compactTilesHtml", js)
        self.assertIn("scrollRail", js)
        self.assertIn("thumbsThatFit", js)
        self.assertIn("play_url", js)
        self.assertIn("data-mm-hero-video", js)
        self.assertIn("video.play()", js)
        self.assertIn("startHeroPlayback", js)
        self.assertNotIn("data-mm-hero-play", js)
        self.assertNotIn("facebook.com/plugins/video.php", js)
        self.assertIn("playsinline", js)
        src = Path("api.py").read_text(encoding="utf-8")
        self.assertIn('row["play_url"]', src)
        self.assertIn("mmr21", src)
        self.assertIn("mm-lipton-reels-thumb-hit", js)
        self.assertIn("latestThumbHtml", js)
        self.assertIn("mm-lipton-reels-thumb--latest", js)
        self.assertIn("latestChromeHtml", js)
        self.assertIn("fb_owner_logo", js)
        self.assertNotIn("requestFullscreen", js)
        self.assertNotIn("mm-lipton-reels-stamp", js)
        self.assertNotIn("Latest Reel", js)


if __name__ == "__main__":
    unittest.main()
