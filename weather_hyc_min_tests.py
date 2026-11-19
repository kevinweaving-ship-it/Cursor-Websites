#!/usr/bin/env python3
"""HYC WU PWS IOVERS2 wind maps into knots for the generic weather card."""
from sailingsa.backend.weather_hyc import (
    KMH_TO_KT,
    MPH_TO_KT,
    PROVIDER_ID,
    SLUG,
    STATIONS_URL,
    kmh_to_kt,
    mph_to_kt,
    reading_from_wu_obs,
)


def test_mph_to_knots():
    # Live WU imperial sample: 14.8 mph → knots
    assert abs(mph_to_kt(14.8) - round(14.8 * MPH_TO_KT, 2)) < 0.001
    assert mph_to_kt(14.8) == 12.86
    assert kmh_to_kt(23.8) == round(23.8 * KMH_TO_KT, 2)
    assert mph_to_kt(-1) is None
    assert mph_to_kt(None) is None


def test_wu_obs_to_reading_knots():
    obs = {
        "obsTimeUtc": "2026-09-17T11:53:04Z",
        "winddir": 178,
        "humidity": 58,
        "realtimeFrequency": 60,
        "imperial": {"temp": 62.6, "windSpeed": 14.8, "windGust": 17.2},
    }
    row = reading_from_wu_obs(obs)
    assert row["station_slug"] == SLUG
    assert row["provider_station_id"] == PROVIDER_ID
    assert row["wind_kt"] == 12.86
    assert row["wind_avg_kt"] == 12.86
    assert row["wind_gust_kt"] == round(17.2 * MPH_TO_KT, 2)
    assert row["wind_dir_deg"] == 178
    assert row["period_sec"] == 60
    assert row["observed_at"] == "2026-09-17T11:53:04Z"


def test_metric_obs_converts_kmh_to_knots():
    obs = {
        "obsTimeUtc": "2026-09-17T11:53:04Z",
        "winddir": 178,
        "metric": {"temp": 17.0, "windSpeed": 23.8, "windGust": 27.7},
    }
    row = reading_from_wu_obs(obs)
    assert abs(row["wind_kt"] - kmh_to_kt(23.8)) < 0.001
    assert abs(row["wind_kt"] - 12.85) < 0.02


def test_wu_1day_obs_uses_windspeed_avg():
    obs = {
        "obsTimeUtc": "2026-09-17T00:39:56Z",
        "winddirAvg": 140,
        "humidityAvg": 80,
        "imperial": {
            "tempAvg": 56.3,
            "windspeedAvg": 4.3,
            "windgustHigh": 14.8,
        },
    }
    row = reading_from_wu_obs(obs)
    assert row["wind_kt"] == mph_to_kt(4.3)
    assert row["wind_gust_kt"] == mph_to_kt(14.8)
    assert row["wind_dir_deg"] == 140
    assert row["temp_c"] == round((56.3 - 32.0) * 5.0 / 9.0, 2)


def test_catalog_url_is_hyc_stations():
    assert STATIONS_URL.endswith("/api/weather/clubs/HYC/stations")
    assert PROVIDER_ID == "IOVERS2"


if __name__ == "__main__":
    test_mph_to_knots()
    test_wu_obs_to_reading_knots()
    test_metric_obs_converts_kmh_to_knots()
    test_wu_1day_obs_uses_windspeed_avg()
    test_catalog_url_is_hyc_stations()
    print("weather_hyc_min_tests: ok")
