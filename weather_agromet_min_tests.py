#!/usr/bin/env python3
"""HMYC Agromet Midmar readings map into the generic weather-card shape."""
from sailingsa.backend.weather_agromet import (
    reading_from_record,
    FIELDS,
    SLUG,
    MS_TO_KT,
    CAM_INTERVAL_SEC,
    CAM_LABEL,
    _format_as_at,
)
from datetime import datetime, timezone


def test_five_minute_record_to_knots():
    rec = {
        "no": 90134,
        "time": "2026-09-17T12:40:00",
        "vals": [11.17, 89.3, 54.35, 26.67119, 0, 0.298, 262.4, 11.78, 1],
    }
    row = reading_from_record(rec, FIELDS)
    assert row["station_slug"] == SLUG
    assert row["observed_at"].startswith("2026-09-17T10:40:00")
    assert abs(row["wind_avg_kt"] - round(0.298 * MS_TO_KT, 2)) < 0.01
    assert abs(row["wind_gust_kt"] - round(1 * MS_TO_KT, 2)) < 0.01
    assert row["wind_dir_deg"] == 262.4
    assert row["temp_c"] == 11.17


def test_bad_time_is_skipped():
    assert reading_from_record({"time": "", "vals": [0] * 9}, FIELDS) is None


def test_hmyc_cam_is_snapshot_not_live():
    assert CAM_INTERVAL_SEC == 60
    assert CAM_LABEL == "Club cam"
    dt = datetime(2026, 9, 17, 11, 1, 1, tzinfo=timezone.utc)
    assert _format_as_at(dt) == "13:01"


if __name__ == "__main__":
    test_five_minute_record_to_knots()
    test_bad_time_is_skipped()
    test_hmyc_cam_is_snapshot_not_live()
    print("weather_agromet_min_tests: ok")
