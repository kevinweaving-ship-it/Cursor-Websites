#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from write_google_sitemaps import (  # noqa: E402
    BASE,
    HUB,
    LATEST,
    ensure_index,
    ensure_robots,
    news_urls,
    public_urls,
    published_issues,
    write_web_root,
)


class WriteGoogleSitemapsTests(unittest.TestCase):
    def _issue(self, root: pathlib.Path, monday: str, title: str) -> None:
        dest = root / "sailing-roundup" / "issues" / monday
        dest.mkdir(parents=True)
        (dest / "index.html").write_text(f"<html><title>{title}</title></html>\n", encoding="utf-8")
        (dest / "issue.json").write_text(
            json.dumps({"title": title, "edition_date": monday}),
            encoding="utf-8",
        )

    def test_public_urls_include_hub_latest_and_every_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self._issue(root, "2026-10-19", "October 19 weekend")
            self._issue(root, "2026-09-28", "Gold weekend")
            issues = published_issues(root)
            urls = [u for u, _ in public_urls(issues)]
        self.assertEqual(urls[0], HUB)
        self.assertEqual(urls[1], LATEST)
        self.assertIn(f"{BASE}/sailing-roundup/issues/2026-10-19/", urls)
        self.assertIn(f"{BASE}/sailing-roundup/issues/2026-09-28/", urls)
        self.assertEqual(len(urls), 4)

    def test_news_sitemap_keeps_only_last_48h(self) -> None:
        now = dt.datetime(2026, 10, 20, 10, 0, tzinfo=dt.timezone.utc)
        items = [
            {"monday": "2026-10-19", "url": f"{BASE}/sailing-roundup/issues/2026-10-19/", "lastmod": "2026-10-19", "title": "New"},
            {"monday": "2026-09-28", "url": f"{BASE}/sailing-roundup/issues/2026-09-28/", "lastmod": "2026-09-28", "title": "Gold"},
        ]
        kept = news_urls(items, now=now)
        self.assertEqual([i["monday"] for i in kept], ["2026-10-19"])

    def test_write_web_root_patches_index_and_robots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            monday = dt.date.today().isoformat()
            self._issue(root, monday, "This Monday weekend")
            (root / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                "  <sitemap>\n"
                f"    <loc>{BASE}/sitemap-core.xml</loc>\n"
                "    <lastmod>2026-10-01</lastmod>\n"
                "  </sitemap>\n"
                "</sitemapindex>\n",
                encoding="utf-8",
            )
            (root / "robots.txt").write_text(
                "User-agent: *\nAllow: /\nDisallow: /api/\n"
                f"Sitemap: {BASE}/sitemap.xml\n",
                encoding="utf-8",
            )
            stats = write_web_root(root, ping=False)
            roundups = (root / "sitemap-roundups.xml").read_text(encoding="utf-8")
            news = (root / "sitemap-news.xml").read_text(encoding="utf-8")
            index = (root / "sitemap.xml").read_text(encoding="utf-8")
            robots = (root / "robots.txt").read_text(encoding="utf-8")
        self.assertTrue(stats["ok"])
        self.assertEqual(stats["issues"], 1)
        self.assertIn(HUB, roundups)
        self.assertIn(LATEST, roundups)
        self.assertIn(f"{BASE}/sailing-roundup/issues/{monday}/", roundups)
        self.assertIn("<changefreq>weekly</changefreq>", roundups)
        self.assertIn("news:publication_date", news)
        self.assertIn(f"{BASE}/sitemap-roundups.xml", index)
        self.assertIn(f"{BASE}/sitemap-news.xml", index)
        self.assertIn(f"{BASE}/sitemap-core.xml", index)
        self.assertIn("Disallow: /api/", robots)
        self.assertIn(f"Sitemap: {BASE}/sitemap-roundups.xml", robots)
        self.assertIn(f"Sitemap: {BASE}/sitemap-news.xml", robots)

    def test_ensure_index_and_robots_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            ensure_index(root / "sitemap.xml", today="2026-10-24")
            ensure_robots(root / "robots.txt")
            first_index = (root / "sitemap.xml").read_text(encoding="utf-8")
            first_robots = (root / "robots.txt").read_text(encoding="utf-8")
            ensure_index(root / "sitemap.xml", today="2026-10-24")
            ensure_robots(root / "robots.txt")
            self.assertEqual(first_index.count("sitemap-roundups.xml"), 1)
            self.assertEqual((root / "robots.txt").read_text(encoding="utf-8"), first_robots)
            self.assertEqual(first_robots.count("sitemap-roundups.xml"), 1)


if __name__ == "__main__":
    unittest.main()
