"""Queue processor unit tests — no Chrome, no GSC UI."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sailingsa.tools.gsc_daily.chrome_gsc import classify_text
from sailingsa.tools.gsc_daily.manual_index_worker import acquire_lock
from sailingsa.tools.gsc_daily.manual_queue import (
    connect,
    enqueue,
    next_urls,
    priority_rank,
    quota_pause,
    record_request,
    set_quota,
    set_state,
    snapshot,
)


class ClassifyTextTests(unittest.TestCase):
    def test_indexing_requested(self):
        self.assertEqual(classify_text("Indexing requested"), "indexing_requested")

    def test_quota(self):
        self.assertEqual(
            classify_text("You've reached the maximum daily limit for indexing requests"),
            "quota",
        )

    def test_unknown_to_google(self):
        self.assertEqual(
            classify_text("URL is unknown to Google\nRequest indexing"),
            "not_indexed",
        )


class QueuePriorityTests(unittest.TestCase):
    def test_imminent_regatta_and_new_roundup_outrank_sailor(self):
        now = datetime(2026, 11, 24, tzinfo=timezone.utc)
        self.assertEqual(
            priority_rank("https://sailingsa.co.za/regatta/2026-11-28-tsc-cape-classic", now),
            0,
        )
        self.assertEqual(
            priority_rank("https://sailingsa.co.za/sailing-roundup/issues/2026-11-23/", now),
            0,
        )
        self.assertEqual(priority_rank("https://sailingsa.co.za/sailor/jane-doe", now), 2)

    def test_starved_old_url_jumps_the_queue(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = "https://sailingsa.co.za/sailor/old-entry"
            fresh = "https://sailingsa.co.za/regatta/2026-11-28-tsc-cape-classic"
            enqueue(root, [old])
            with connect(root) as db:
                db.execute(
                    "UPDATE queue SET seen=? WHERE url=?",
                    ((datetime.now(timezone.utc) - timedelta(hours=40)).isoformat(), old),
                )
            enqueue(root, [fresh])
            nxt = next_urls(root, 2)
            self.assertEqual(nxt[0], old)
            self.assertIn(fresh, nxt)


class QueuePersistTests(unittest.TestCase):
    def test_pending_survives_reconnect_and_lock_release(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = "https://sailingsa.co.za/regatta/2026-11-28-tsc-cape-classic"
            b = "https://sailingsa.co.za/sailing-roundup/issues/2026-11-23/"
            enqueue(root, [a, b])
            first = next_urls(root, 10)
            self.assertEqual(set(first), {a, b})
            lock = acquire_lock(root)
            self.assertIsNotNone(lock)
            self.assertIsNone(acquire_lock(root))
            lock.close()
            # Reopen DB as a restarted worker would.
            again = next_urls(root, 10)
            self.assertEqual(set(again), {a, b})
            snap = snapshot(root)
            self.assertEqual(snap["counts"].get("pending"), 2)

    def test_quota_blocks_then_resumes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            enqueue(root, ["https://sailingsa.co.za/regatta/2026-11-28-tsc-cape-classic"])
            set_quota(root, (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(), "daily limit")
            self.assertTrue(quota_pause(root))
            self.assertEqual(next_urls(root, 10), [])
            set_quota(root, (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), "expired")
            self.assertFalse(quota_pause(root))
            self.assertTrue(next_urls(root, 10))

    def test_accepted_is_not_indexed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            url = "https://sailingsa.co.za/regatta/2026-11-28-tsc-cape-classic"
            enqueue(root, [url])
            record_request(root, url, "Indexing requested", accepted=True)
            with connect(root) as db:
                row = db.execute("SELECT state FROM queue WHERE url=?", (url,)).fetchone()
            self.assertEqual(row["state"], "accepted")
            set_state(root, url, "indexed", coverage="Submitted and indexed")
            with connect(root) as db:
                row = db.execute("SELECT state FROM queue WHERE url=?", (url,)).fetchone()
            self.assertEqual(row["state"], "indexed")


if __name__ == "__main__":
    unittest.main()
