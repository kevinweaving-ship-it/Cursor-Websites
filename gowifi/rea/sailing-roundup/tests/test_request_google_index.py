#!/usr/bin/env python3
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from request_google_index import _quota_hit, request_until_quota  # noqa: E402


class RequestGoogleIndexTests(unittest.TestCase):
    def test_quota_exhausted_stops(self) -> None:
        responses = [
            {"ok": True, "url": "https://sailingsa.co.za/sailing-roundup/"},
            {"ok": False, "status": 429, "detail": "Quota exceeded for quota metric"},
            {"ok": True, "url": "should-not-run"},
        ]

        def fake(url):
            return responses.pop(0)

        with patch("request_google_index.notify_url_updated", side_effect=fake):
            with patch("request_google_index.time.sleep"):
                stats = request_until_quota(
                    [
                        "https://sailingsa.co.za/sailing-roundup/",
                        "https://sailingsa.co.za/sailing-roundup/latest/",
                        "https://sailingsa.co.za/",
                    ],
                    pause=0,
                )
        self.assertEqual(stats["stop_reason"], "quota_exhausted")
        self.assertEqual(stats["submitted"], 1)
        self.assertEqual(stats["urls_submitted"], ["https://sailingsa.co.za/sailing-roundup/"])

    def test_quota_marker_on_403(self) -> None:
        self.assertTrue(
            _quota_hit({"ok": False, "status": 403, "detail": "dailyLimitExceeded"})
        )
        self.assertFalse(_quota_hit({"ok": False, "status": 403, "detail": "URL ownership"}))

    def test_missing_credentials_stops(self) -> None:
        with patch(
            "request_google_index.notify_url_updated",
            return_value={"ok": False, "skipped": True, "reason": "no_credentials"},
        ):
            stats = request_until_quota(["https://sailingsa.co.za/sailing-roundup/"], pause=0)
        self.assertEqual(stats["stop_reason"], "no_credentials")
        self.assertEqual(stats["submitted"], 0)


if __name__ == "__main__":
    unittest.main()
