#!/usr/bin/env python3
"""Cape Classic MM Facebook jobs only run on event dates."""
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent / "sailingsa" / "deploy"))
from mm_fb_event_window import (  # noqa: E402
    delete_chrome_run_dir,
    event_is_active,
    event_status,
    make_chrome_run_dir,
    skip_payload,
    today_sast,
)

SAST = ZoneInfo("Africa/Johannesburg")


def test_active_on_event_days():
    assert event_is_active(date(2026, 9, 12)) is True
    assert event_is_active(date(2026, 9, 13)) is True
    assert event_status(date(2026, 9, 12)) == "active"


def test_upcoming_before_start():
    assert event_is_active(date(2026, 9, 11)) is False
    assert event_status(date(2026, 9, 11)) == "upcoming"


def test_past_after_end():
    assert event_is_active(date(2026, 9, 14)) is False
    assert event_is_active(date(2026, 9, 15)) is False
    assert event_status(date(2026, 9, 15)) == "past"


def test_sast_date_not_utc():
    # 15 Sep 2026 00:30 SAST is still 14 Sep UTC
    now = datetime(2026, 9, 15, 0, 30, tzinfo=SAST)
    assert today_sast(now) == date(2026, 9, 15)
    assert event_status(now) == "past"


def test_skip_payload_names_regatta():
    payload = skip_payload(date(2026, 9, 15))
    assert payload["ok"] is True
    assert payload["skipped"] == "event_not_active"
    assert payload["status"] == "past"
    assert payload["regatta"] == "2026-09-13-zvyc-cape-classic"
    assert payload["start"] == "2026-09-12"
    assert payload["end"] == "2026-09-13"


def test_chrome_folder_deleted_after_check():
    profile = make_chrome_run_dir()
    junk = profile / "Default" / "Cache" / "data"
    junk.parent.mkdir(parents=True)
    junk.write_bytes(b"not-live-leftover")
    assert profile.is_dir()
    delete_chrome_run_dir(profile)
    assert not profile.exists()


def test_sweep_bins_orphan_chrome_dirs():
    from ssa_headless_chrome import sweep_orphaned_chrome

    orphan = Path("/tmp/scoped_dir_ssa_test_bin")
    orphan.mkdir(exist_ok=True)
    (orphan / "junk").write_text("x")
    try:
        out = sweep_orphaned_chrome(min_age_sec=0)
        assert out["ok"] is True
        assert not orphan.exists()
    finally:
        if orphan.exists():
            delete_chrome_run_dir(orphan)


if __name__ == "__main__":
    test_active_on_event_days()
    test_upcoming_before_start()
    test_past_after_end()
    test_sast_date_not_utc()
    test_skip_payload_names_regatta()
    test_chrome_folder_deleted_after_check()
    test_sweep_bins_orphan_chrome_dirs()
    print("mm_fb_event_window_tests: ok")
