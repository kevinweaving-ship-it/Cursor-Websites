"""Unit tests for honest Upcoming→Live sitemap lastmod (no DB)."""
from __future__ import annotations

import sys
import types
import unittest
from datetime import date, datetime

# sitemap_builder imports psycopg2 at module load; stub it for local tests.
if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    sys.modules["psycopg2.extras"] = extras

from sitemap_builder import (  # noqa: E402
    _honest_regatta_lastmod,
    _is_public_regatta_id,
)


class PublicRegattaIdTests(unittest.TestCase):
    def test_permanent_public_slugs(self):
        self.assertTrue(_is_public_regatta_id("2026-09-25-tsc-420-nationals"))
        self.assertTrue(_is_public_regatta_id("2026-09-19-hmyc-midmar-cup"))
        self.assertTrue(_is_public_regatta_id("2026-08-29-lipton-challenge-cup"))

    def test_excludes_admin_test_dev(self):
        self.assertFalse(_is_public_regatta_id("live-scratch"))
        self.assertFalse(_is_public_regatta_id("test-foo"))
        self.assertFalse(_is_public_regatta_id("foo-dev2"))
        self.assertFalse(_is_public_regatta_id("tracking-dev-1"))
        self.assertFalse(_is_public_regatta_id("has/slash"))
        self.assertFalse(_is_public_regatta_id("has space"))
        self.assertFalse(_is_public_regatta_id(""))


class HonestLastmodTests(unittest.TestCase):
    today = "2026-09-18"

    def test_as_at_wins_when_not_future(self):
        lm, src = _honest_regatta_lastmod(
            as_at_time=datetime(2026, 8, 29, 15, 24),
            created_at=datetime(2026, 8, 1, 10, 0),
            start_date=date(2026, 8, 27),
            end_date=date(2026, 8, 29),
            today=self.today,
        )
        self.assertEqual((lm, src), ("2026-08-29", "as_at_time"))

    def test_future_as_at_falls_back_to_created_at(self):
        lm, src = _honest_regatta_lastmod(
            as_at_time=datetime(2026, 10, 24, 17, 30),
            created_at=datetime(2026, 9, 16, 8, 0),
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 20),
            today=self.today,
        )
        self.assertEqual((lm, src), ("2026-09-16", "created_at"))

    def test_midmar_null_as_at_uses_created_at_not_floor(self):
        lm, src = _honest_regatta_lastmod(
            as_at_time=None,
            created_at=datetime(2026, 9, 16, 12, 0),
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 20),
            today=self.today,
        )
        self.assertEqual((lm, src), ("2026-09-16", "created_at"))
        self.assertNotEqual(lm, "2000-01-01")

    def test_tsc_upcoming_zero_results_uses_created_at(self):
        lm, src = _honest_regatta_lastmod(
            as_at_time=None,
            created_at=datetime(2026, 9, 10, 9, 0),
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 27),
            today=self.today,
        )
        self.assertEqual((lm, src), ("2026-09-10", "created_at"))

    def test_historical_fallback_start_end(self):
        lm, src = _honest_regatta_lastmod(
            as_at_time=None,
            created_at=None,
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 3),
            today=self.today,
        )
        self.assertEqual((lm, src), ("2024-03-03", "end_date"))

    def test_never_emits_future_or_floor_when_real_date_exists(self):
        lm, src = _honest_regatta_lastmod(
            as_at_time="2000-01-01 00:00:00",
            created_at=datetime(2026, 9, 16, 1, 0),
            start_date=date(2026, 9, 19),
            end_date=date(2026, 9, 20),
            today=self.today,
        )
        self.assertEqual((lm, src), ("2026-09-16", "created_at"))


if __name__ == "__main__":
    unittest.main()
