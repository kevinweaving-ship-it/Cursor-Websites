#!/usr/bin/env python3
"""Index lastmod follows child urlset changes, not only max entity date."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.sitemap_builder import (  # noqa: E402
    _build_urlset_xml,
    _is_reserved_public_slug,
    _sitemap_file_lastmod,
    _xml_unchanged,
)


TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


class SitemapIndexLastmodTests(unittest.TestCase):
    def test_new_file_uses_today(self):
        entries = [("/sailor/old-name", "2024-01-01")]
        xml = _build_urlset_xml("https://sailingsa.co.za", entries)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "sitemap-sailors.xml")
            self.assertEqual(_sitemap_file_lastmod(path, xml, entries, TODAY), TODAY)

    def test_identical_rewrite_keeps_entity_max(self):
        entries = [("/sailor/a", "2026-09-27"), ("/sailor/b", "2026-08-01")]
        xml = _build_urlset_xml("https://sailingsa.co.za", entries)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "sitemap-sailors.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml)
            self.assertTrue(_xml_unchanged(path, xml))
            self.assertEqual(
                _sitemap_file_lastmod(path, xml, entries, TODAY), "2026-09-27"
            )

    def test_added_older_url_bumps_index_to_today(self):
        old = [("/sailor/a", "2026-09-27")]
        new = [("/sailor/a", "2026-09-27"), ("/sailor/new-old-result", "2024-01-01")]
        old_xml = _build_urlset_xml("https://sailingsa.co.za", old)
        new_xml = _build_urlset_xml("https://sailingsa.co.za", new)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "sitemap-sailors.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(old_xml)
            self.assertFalse(_xml_unchanged(path, new_xml))
            self.assertEqual(_sitemap_file_lastmod(path, new_xml, new, TODAY), TODAY)

    def test_urlset_has_no_changefreq(self):
        xml = _build_urlset_xml("https://sailingsa.co.za", [("/", "2026-10-03")])
        self.assertNotIn("changefreq", xml)
        self.assertIn("<lastmod>2026-10-03</lastmod>", xml)

    def test_reserved_placeholder_slugs(self):
        for slug in ("unknown", "none", "na", "n-a", "tbc", "tba", "TBC"):
            self.assertTrue(_is_reserved_public_slug(slug), slug)
        self.assertFalse(_is_reserved_public_slug("aydin-ohara"))
        self.assertFalse(_is_reserved_public_slug("hyc"))


if __name__ == "__main__":
    unittest.main()
