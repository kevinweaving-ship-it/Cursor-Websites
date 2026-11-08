"""Unit tests for SEO health — no GSC API, no site changes."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sailingsa.tools.gsc_daily.seo_health import (
    evaluate_health,
    googlebot_activity,
    indexing_split,
    live_canonical_mismatches,
    performance_trend,
    sitemap_health,
)

SAST = ZoneInfo("Africa/Johannesburg")


def _log_line(ip: str, ts: datetime, path: str, status: int = 200, nbytes: int = 1000) -> str:
    stamp = ts.strftime("%d/%b/%Y:%H:%M:%S %z")
    ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    return (
        f'{ip} - - [{stamp}] "GET {path} HTTP/1.1" {status} {nbytes} "-" "{ua}"\n'
    )


class SitemapHealthTests(unittest.TestCase):
    def test_fresh_download_no_alert(self):
        h = sitemap_health(
            {"count": 1, "errors": 0, "last_downloaded": "2026-10-16", "_auth_ok": True},
            as_of_day=date(2026, 10, 18),
        )
        self.assertFalse(h["alert"])
        self.assertEqual(h["age_days"], 2)

    def test_stale_over_7_days(self):
        h = sitemap_health(
            {"count": 1, "errors": 0, "last_downloaded": "2026-10-01", "_auth_ok": True},
            as_of_day=date(2026, 10, 18),
        )
        self.assertTrue(h["alert"])
        self.assertTrue(h["stale"])

    def test_errors_alert(self):
        h = sitemap_health(
            {"count": 1, "errors": 3, "last_downloaded": "2026-10-18", "_auth_ok": True},
            as_of_day=date(2026, 10, 18),
        )
        self.assertTrue(h["fetch_failure"])

    def test_auth_gap_is_not_stale(self):
        h = sitemap_health(
            {"count": 0, "errors": 0, "last_downloaded": "", "_auth_ok": False},
            as_of_day=date(2026, 10, 18),
        )
        self.assertFalse(h["alert"])


class IndexingSplitTests(unittest.TestCase):
    def test_crawl_versus_index(self):
        inspections = {
            "https://sailingsa.co.za/a": {
                "indexStatusResult": {
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                    "lastCrawlTime": "2026-10-01T00:00:00Z",
                    "userCanonical": "https://sailingsa.co.za/a",
                    "googleCanonical": "https://sailingsa.co.za/a",
                }
            },
            "https://sailingsa.co.za/b": {
                "indexStatusResult": {
                    "verdict": "NEUTRAL",
                    "coverageState": "Crawled - currently not indexed",
                    "lastCrawlTime": "2026-08-01T00:00:00Z",
                    "userCanonical": "https://sailingsa.co.za/b",
                    "googleCanonical": "https://sailingsa.co.za/b",
                }
            },
            "https://sailingsa.co.za/c": {
                "indexStatusResult": {
                    "verdict": "NEUTRAL",
                    "coverageState": "Discovered - currently not indexed",
                }
            },
            "https://sailingsa.co.za/club/abyc": {
                "indexStatusResult": {
                    "verdict": "NEUTRAL",
                    "coverageState": "Duplicate, Google chose different canonical than user",
                    "userCanonical": "https://sailingsa.co.za/club/abyc",
                    "googleCanonical": "https://sailingsa.co.za/club/ABYC",
                    "lastCrawlTime": "2026-09-20T00:00:00Z",
                }
            },
        }
        s = indexing_split(inspections)
        self.assertEqual(s["indexed"], 1)
        self.assertEqual(s["crawled_not_indexed"], 1)
        self.assertEqual(s["not_crawled"], 1)
        self.assertEqual(s["canonical_gsc_mismatch"], 1)


class CanonicalLiveTests(unittest.TestCase):
    def test_301_is_not_a_live_mismatch(self):
        ex = [
            {
                "url": "https://sailingsa.co.za/club/abyc",
                "userCanonical": "https://sailingsa.co.za/club/abyc",
                "googleCanonical": "https://sailingsa.co.za/club/ABYC",
            }
        ]
        mm = live_canonical_mismatches(ex, hop=lambda u: (301, "/club/abyc"))
        self.assertEqual(mm, [])

    def test_dual_200_is_a_live_mismatch(self):
        ex = [
            {
                "url": "https://sailingsa.co.za/club/abyc",
                "userCanonical": "https://sailingsa.co.za/club/abyc",
                "googleCanonical": "https://sailingsa.co.za/club/ABYC",
            }
        ]
        mm = live_canonical_mismatches(ex, hop=lambda u: (200, ""))
        self.assertEqual(len(mm), 1)

    def test_google_correct_user_301_is_not_live(self):
        ex = [
            {
                "url": "https://sailingsa.co.za/club/rcyc",
                "userCanonical": "https://sailingsa.co.za/club/RCYC",
                "googleCanonical": "https://sailingsa.co.za/club/rcyc",
            }
        ]

        def hop(u: str):
            if u.endswith("/RCYC"):
                return 301, "/club/rcyc"
            return 200, ""

        self.assertEqual(live_canonical_mismatches(ex, hop=hop), [])

    def test_google_301_user_200_is_stale(self):
        ex = [
            {
                "url": "https://sailingsa.co.za/regatta/2017-09-25-laser-sa-nationals",
                "userCanonical": "https://sailingsa.co.za/regatta/2017-09-25-laser-sa-nationals",
                "googleCanonical": "https://sailingsa.co.za/regatta/446-2017-laser-sa-nationals",
            }
        ]

        def hop(u: str):
            if "/446-" in u:
                return 301, "/regatta/2017-09-25-laser-sa-nationals"
            return 200, ""

        self.assertEqual(live_canonical_mismatches(ex, hop=hop), [])


class GooglebotLogTests(unittest.TestCase):
    def test_recent_verified_hit_ok(self):
        as_of = datetime(2026, 10, 18, 9, 0, tzinfo=SAST)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "access.log"
            p.write_text(
                _log_line("66.249.69.137", as_of - timedelta(hours=3), "/sailor/aaron-ward")
                + _log_line("1.2.3.4", as_of - timedelta(hours=1), "/sailor/aaron-ward")
            )
            out = googlebot_activity(
                Path(td),
                as_of=as_of,
                verify_ip=lambda ip: ip.startswith("66.249."),
            )
        self.assertFalse(out["alert"])
        self.assertEqual(out["hits_48h"], 1)

    def test_inactive_48h_alerts(self):
        as_of = datetime(2026, 10, 18, 9, 0, tzinfo=SAST)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "access.log"
            p.write_text(
                _log_line(
                    "66.249.69.137",
                    as_of - timedelta(hours=50),
                    "/sailor/aaron-ward",
                )
            )
            out = googlebot_activity(
                Path(td),
                as_of=as_of,
                verify_ip=lambda ip: True,
            )
        self.assertTrue(out["alert"])
        self.assertGreater(out["hours_ago"], 48)

    def test_ignores_timadvisor_robots_404(self):
        as_of = datetime(2026, 10, 18, 9, 0, tzinfo=SAST)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "access.log"
            p.write_text(_log_line("66.249.77.141", as_of - timedelta(hours=1), "/robots.txt", 404, 162))
            out = googlebot_activity(Path(td), as_of=as_of, verify_ip=lambda ip: True)
        self.assertFalse(out["alert"])  # log does not cover 48h — do not false-alert
        self.assertTrue(out["skipped"])
        self.assertEqual(out["hits_48h"], 0)

    def test_covered_window_only_timadvisor_is_inactive(self):
        as_of = datetime(2026, 10, 18, 9, 0, tzinfo=SAST)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "access.log"
            p.write_text(
                _log_line("66.249.77.141", as_of - timedelta(hours=50), "/robots.txt", 404, 162)
                + _log_line("66.249.77.141", as_of - timedelta(hours=1), "/robots.txt", 404, 162)
            )
            out = googlebot_activity(Path(td), as_of=as_of, verify_ip=lambda ip: True)
        self.assertTrue(out["alert"])
        self.assertEqual(out["hits_48h"], 0)


class PerformanceTests(unittest.TestCase):
    def _write(self, root: Path, day: str, clicks, impr):
        d = root / day
        d.mkdir(parents=True, exist_ok=True)
        (d / "report.json").write_text(
            json.dumps({"search_analytics": {"clicks": clicks, "impressions": impr}})
        )

    def test_oct18_like_does_not_alert(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "2026-10-11", 46, 696)
            self._write(root, "2026-10-17", 27, 602)
            self._write(root, "2026-10-18", 29, 610)
            tr = performance_trend(root, "2026-10-18", {"clicks": 29, "impressions": 610})
        self.assertFalse(tr["alert"])  # impr drop is only ~12%

    def test_sustained_dual_drop_alerts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "2026-10-10", 100, 1000)
            self._write(root, "2026-10-11", 100, 1000)
            self._write(root, "2026-10-17", 40, 500)
            self._write(root, "2026-10-18", 40, 500)
            tr = performance_trend(root, "2026-10-18", {"clicks": 40, "impressions": 500})
        self.assertTrue(tr["alert"])
        self.assertGreaterEqual(tr["consecutive_breach_days"], 2)


class EvaluateNoFalseAlertTests(unittest.TestCase):
    def test_historical_oct18_shape_is_healthy_without_logs(self):
        google = {
            "auth": "OK",
            "inspections": {
                "https://sailingsa.co.za/class/ilca-6": {
                    "indexStatusResult": {
                        "verdict": "NEUTRAL",
                        "coverageState": "Crawled - currently not indexed",
                        "lastCrawlTime": "2026-08-28T00:00:00Z",
                        "userCanonical": "https://sailingsa.co.za/class/ilca-6",
                        "googleCanonical": "https://sailingsa.co.za/class/ilca-6",
                    }
                }
            },
        }
        h = evaluate_health(
            day="2026-10-18",
            google=google,
            probes=[{"url": "https://sailingsa.co.za/class/ilca-6", "classification": "INTENTIONAL/CORRECT"}],
            sitemap_summary={"count": 1, "errors": 0, "warnings": 0, "last_downloaded": "2026-10-16"},
            search_analytics={"clicks": 29, "impressions": 610},
            skip_logs=True,
            hop=lambda u: (301, "/club/abyc"),
        )
        self.assertTrue(h["healthy"], h["alerts"])
        self.assertEqual(h["indexing"]["crawled_not_indexed"], 1)

    def test_known_real_is_not_new_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            y = root / "2026-10-17"
            y.mkdir()
            (y / "report.json").write_text(
                json.dumps({"real_urls": ["https://sailingsa.co.za/club/ESC"]})
            )
            h = evaluate_health(
                day="2026-10-18",
                google={"auth": "OK", "inspections": {}},
                probes=[{"url": "https://sailingsa.co.za/club/ESC", "classification": "REAL DEFECT"}],
                sitemap_summary={"count": 1, "errors": 0, "last_downloaded": "2026-10-16"},
                search_analytics={"clicks": 29, "impressions": 610},
                data_root=root,
                skip_logs=True,
            )
        self.assertTrue(h["healthy"], h["alerts"])

    def test_new_real_alerts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            y = root / "2026-10-17"
            y.mkdir()
            (y / "report.json").write_text(json.dumps({"real_urls": []}))
            h = evaluate_health(
                day="2026-10-18",
                google={"auth": "OK", "inspections": {}},
                probes=[{"url": "https://sailingsa.co.za/club/ESC", "classification": "REAL DEFECT"}],
                sitemap_summary={"count": 1, "errors": 0, "last_downloaded": "2026-10-16"},
                search_analytics={"clicks": 29, "impressions": 610},
                data_root=root,
                skip_logs=True,
            )
        self.assertFalse(h["healthy"])
        self.assertTrue(any("new REAL" in a for a in h["alerts"]))


if __name__ == "__main__":
    unittest.main()
