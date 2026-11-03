#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from seo_head import (  # noqa: E402
    HUB,
    inject_seo_head,
    issue_head,
    issue_meta,
    patch_web_root,
    strip_seo_head,
)


class SeoHeadTests(unittest.TestCase):
    def _data(self) -> dict:
        return {
            "title": "Weekly Roundup",
            "edition_date": "2026-10-19",
            "articles": [
                {
                    "type": "feature",
                    "headline": "Weekly Roundup",
                    "deck": "17–18 October 2026",
                    "published_at": "2026-10-19",
                    "hero_image": {"url": "media/mirror-hero.jpg"},
                },
                {
                    "type": "regatta_report",
                    "headline": "Mark Flack and Ila Gebuza dominate KZN Mirror Regionals at PYC",
                    "event_id": "2026-10-17-pyc-kzn-mirror-regionals",
                },
            ],
        }

    def test_issue_head_has_canonical_robots_og_and_newsarticle(self) -> None:
        block = issue_head("2026-10-19", self._data())
        self.assertIn('rel="canonical" href="https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/"', block)
        self.assertIn('name="robots" content="index, follow"', block)
        self.assertIn("og:title", block)
        self.assertIn("og:image", block)
        self.assertIn("NewsArticle", block)
        self.assertIn("media/mirror-hero.jpg", block)
        self.assertIn("Mark Flack", issue_meta("2026-10-19", self._data())["title"])

    def test_latest_canonical_points_at_issue(self) -> None:
        block = issue_head(
            "2026-10-19",
            self._data(),
            canonical="https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/",
        )
        self.assertIn(
            'rel="canonical" href="https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/"',
            block,
        )
        self.assertEqual(block.count("rel=\"canonical\""), 1)

    def test_inject_is_idempotent_and_leaves_body(self) -> None:
        html = (
            "<html><head><title>Weekly Roundup — 2026-10-19</title></head>"
            "<body class='weekly-roundup-edition'><h2>Keep me</h2></body></html>"
        )
        once = inject_seo_head(html, issue_head("2026-10-19", self._data()))
        twice = inject_seo_head(once, issue_head("2026-10-19", self._data()))
        self.assertEqual(once.count("ssa-gsc"), twice.count("ssa-gsc"))
        self.assertIn("<h2>Keep me</h2>", twice)
        self.assertNotIn("ssa-gsc", strip_seo_head(twice))

    def test_patch_web_root_hub_latest_and_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            issue = root / "sailing-roundup" / "issues" / "2026-10-19"
            issue.mkdir(parents=True)
            (issue / "issue.json").write_text(json.dumps(self._data()), encoding="utf-8")
            (issue / "index.html").write_text(
                "<html><head><title>Weekly Roundup — 2026-10-19</title></head>"
                "<body><h2>Story</h2></body></html>",
                encoding="utf-8",
            )
            (root / "sailing-roundup" / "index.html").write_text(
                "<html><head><title>Weekly Roundup — SailingSA</title></head><body><h1>Weekly Roundup</h1></body></html>",
                encoding="utf-8",
            )
            latest = root / "sailing-roundup" / "latest"
            latest.mkdir()
            (latest / "index.html").write_text((issue / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
            stats = patch_web_root(root)
            hub = (root / "sailing-roundup" / "index.html").read_text(encoding="utf-8")
            latest_html = (latest / "index.html").read_text(encoding="utf-8")
            issue_html = (issue / "index.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(stats["patched"], 3)
        self.assertIn(f'rel="canonical" href="{HUB}"', hub)
        self.assertIn("CollectionPage", hub)
        self.assertIn('rel="canonical" href="https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/"', latest_html)
        self.assertIn("NewsArticle", issue_html)
        self.assertIn("<h2>Story</h2>", issue_html)


if __name__ == "__main__":
    unittest.main()
