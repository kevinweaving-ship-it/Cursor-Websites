"""Unit tests for Marine Megastore Live FB feed helpers."""

import unittest
from datetime import datetime, timezone

import mm_live_fb as mm


class TimestampTest(unittest.TestCase):
    def test_stamp_sast(self):
        dt = datetime(2026, 9, 13, 12, 20, tzinfo=timezone.utc)
        self.assertEqual(mm.format_mm_timestamp(dt), "13 Sep · 14:20")

    def test_parse_z(self):
        dt = mm.parse_ts("2026-09-13T08:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)


class WindowTest(unittest.TestCase):
    def test_in_window(self):
        self.assertTrue(
            mm.video_in_event_window("2026-09-13T10:00:00+02:00", "2026-09-13", "2026-09-14")
        )

    def test_outside_window(self):
        self.assertFalse(
            mm.video_in_event_window("2026-08-01T10:00:00+02:00", "2026-09-13", "2026-09-14")
        )


class MergeStageTest(unittest.TestCase):
    def test_live_becomes_primary_prior_kept_as_replay(self):
        existing = [
            {
                "id": "111",
                "url": "https://www.facebook.com/marin.megastoresa/videos/111/",
                "title": "Race 1",
                "started_at": "2026-09-13T08:00:00+02:00",
                "is_live": False,
            }
        ]
        incoming = [
            {
                "id": "222",
                "permalink_url": "https://www.facebook.com/marin.megastoresa/videos/222/",
                "title": "Race 2 LIVE",
                "created_time": "2026-09-13T11:00:00+02:00",
                "is_live": True,
            }
        ]
        merged = mm.merge_mm_videos(
            existing, incoming, start_date="2026-09-13", end_date="2026-09-14"
        )
        primary, replays = mm.pick_mm_stage(merged)
        self.assertIsNotNone(primary)
        self.assertEqual(primary["id"], "222")
        self.assertTrue(primary["is_live"])
        self.assertEqual([r["id"] for r in replays], ["111"])
        self.assertEqual(replays[0]["stamp"], "13 Sep · 08:00")
        self.assertIn("plugins/video.php", primary["embed_url"])

    def test_old_unrelated_video_dropped(self):
        incoming = [
            {
                "id": "999",
                "url": "https://www.facebook.com/marin.megastoresa/videos/999/",
                "title": "Last month shop clip",
                "started_at": "2026-08-01T10:00:00+02:00",
                "is_live": False,
            }
        ]
        merged = mm.merge_mm_videos([], incoming, start_date="2026-09-13", end_date="2026-09-14")
        self.assertEqual(merged, [])

    def test_live_accepted_even_if_just_started(self):
        incoming = [
            {
                "id": "333",
                "url": "https://www.facebook.com/marin.megastoresa/videos/333/",
                "title": "Going live",
                "started_at": "2026-09-13T07:55:00+02:00",
                "is_live": True,
            }
        ]
        merged = mm.merge_mm_videos([], incoming, start_date="2026-09-13", end_date="2026-09-14")
        primary, replays = mm.pick_mm_stage(merged)
        self.assertEqual(primary["id"], "333")
        self.assertEqual(replays, [])

    def test_no_live_means_waiting_all_replays(self):
        videos = [
            {
                "id": "111",
                "url": "https://www.facebook.com/marin.megastoresa/videos/111/",
                "started_at": "2026-09-13T08:00:00+02:00",
                "is_live": False,
            }
        ]
        primary, replays = mm.pick_mm_stage(videos)
        self.assertIsNone(primary)
        self.assertEqual(len(replays), 1)
        self.assertEqual(replays[0]["stamp"], "13 Sep · 08:00")

    def test_title_match_keeps_named_clip(self):
        incoming = [
            {
                "id": "444",
                "url": "https://www.facebook.com/marin.megastoresa/videos/444/",
                "title": "ZVYC Cape Classic preview",
                "started_at": "2026-09-10T18:00:00+02:00",
                "is_live": False,
            }
        ]
        merged = mm.merge_mm_videos(
            [],
            incoming,
            start_date="2026-09-13",
            end_date="2026-09-14",
            event_name="ZVYC Cape Classic 2026",
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], "444")


if __name__ == "__main__":
    unittest.main()
