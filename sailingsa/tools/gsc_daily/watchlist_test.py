"""Watchlist must inspect current event URLs, not oldest sitemap rows."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sailingsa.tools.gsc_daily.watchlist import build_watchlist


def _sm(*paths: str) -> set[str]:
    return {f"https://sailingsa.co.za{p}" for p in paths}


class WatchlistPriorityTests(unittest.TestCase):
    def test_dated_2026_regattas_beat_old_numeric_ids(self):
        sitemap = _sm(
            "/regatta/10-2018-youth-nationals-ilca-4-7",
            "/regatta/2017-12-15-sa-youth-nationals",
            "/regatta/2026-08-29-lipton-challenge-cup",
            "/regatta/2026-09-13-zvyc-cape-classic",
            "/events",
        )
        with tempfile.TemporaryDirectory() as td:
            urls = build_watchlist(Path(td), sitemap, budget=20)
        joined = " ".join(urls)
        self.assertIn("2026-09-13-zvyc-cape-classic", joined)
        self.assertIn("2026-08-29-lipton-challenge-cup", joined)
        i_new = next(i for i, u in enumerate(urls) if "2026-09-13" in u)
        i_old = next((i for i, u in enumerate(urls) if "2017-12-15" in u), 99)
        self.assertLess(i_new, i_old)

    def test_seed_dead_prior_real_dropped_when_absent_from_sitemap(self):
        sitemap = _sm("/", "/events", "/regatta/2026-09-13-zvyc-cape-classic")
        with tempfile.TemporaryDirectory() as td:
            urls = build_watchlist(Path(td), sitemap, budget=20)
        self.assertFalse(any("live-2026-wc-dinghy" in u for u in urls))
        self.assertFalse(any("/test/class/7" in u for u in urls))
