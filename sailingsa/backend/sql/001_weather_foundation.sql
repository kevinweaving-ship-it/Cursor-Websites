-- SailingSA generic weather foundation.
-- Observations and forecasts are separate. Missing measures stay NULL.
-- Cardinal direction is never stored as source-of-truth.

CREATE TABLE IF NOT EXISTS weather_stations (
    id                      bigserial PRIMARY KEY,
    slug                    text NOT NULL UNIQUE,
    display_name            text NOT NULL,
    provider                text NOT NULL,
    provider_station_id     text NOT NULL,
    kind                    text NOT NULL,
    latitude                double precision NOT NULL,
    longitude               double precision NOT NULL,
    elevation_m             double precision,
    timezone                text NOT NULL DEFAULT 'Africa/Johannesburg',
    native_interval_sec     integer,
    is_active               boolean NOT NULL DEFAULT true,
    club_id                 integer,
    event_regatta_id        text,
    meta                    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT weather_stations_kind_chk
        CHECK (kind IN ('observation', 'forecast_point', 'mobile_platform')),
    CONSTRAINT weather_stations_provider_sid_uidx
        UNIQUE (provider, provider_station_id)
);

CREATE TABLE IF NOT EXISTS weather_readings (
    id                      bigserial PRIMARY KEY,
    station_id              bigint NOT NULL REFERENCES weather_stations(id),
    observed_at             timestamptz NOT NULL,
    ingested_at             timestamptz NOT NULL DEFAULT now(),
    period_sec              integer,
    wind_kt                 double precision,
    wind_avg_kt             double precision,
    wind_gust_kt            double precision,
    wind_min_kt             double precision,
    wind_dir_deg            double precision,
    wind_dir_avg_deg        double precision,
    wind_dir_min_deg        double precision,
    wind_dir_max_deg        double precision,
    temp_c                  double precision,
    feels_like_c            double precision,
    dewpoint_c              double precision,
    pressure_hpa            double precision,
    humidity_pct            double precision,
    rain_rate_mm_h          double precision,
    rain_mm_period          double precision,
    rain_mm_24h             double precision,
    uv_index                double precision,
    solar_wm2               double precision,
    battery_pct             double precision,
    wave_height_m           double precision,
    wave_period_s           double precision,
    wave_dir_deg            double precision,
    latitude                double precision,
    longitude               double precision,
    extras                  jsonb NOT NULL DEFAULT '{}'::jsonb,
    raw                     jsonb,
    payload_hash            text
);

CREATE UNIQUE INDEX IF NOT EXISTS weather_readings_station_obs_period_uidx
    ON weather_readings (station_id, observed_at, (COALESCE(period_sec, -1)));

CREATE INDEX IF NOT EXISTS weather_readings_station_obs_desc_idx
    ON weather_readings (station_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS weather_readings_observed_at_idx
    ON weather_readings (observed_at);

CREATE INDEX IF NOT EXISTS weather_readings_payload_hash_idx
    ON weather_readings (payload_hash)
    WHERE payload_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS weather_forecasts (
    id                      bigserial PRIMARY KEY,
    forecast_source         text NOT NULL,
    model                   text NOT NULL,
    station_id              bigint REFERENCES weather_stations(id),
    forecast_lat            double precision NOT NULL,
    forecast_lon            double precision NOT NULL,
    issued_at               timestamptz NOT NULL,
    target_at               timestamptz NOT NULL,
    lead_seconds            integer NOT NULL,
    wind_kt                 double precision,
    wind_gust_kt            double precision,
    wind_dir_deg            double precision,
    temp_c                  double precision,
    pressure_hpa            double precision,
    rain                    double precision,
    cloud                   double precision,
    extras                  jsonb NOT NULL DEFAULT '{}'::jsonb,
    raw                     jsonb,
    ingested_at             timestamptz NOT NULL DEFAULT now()
);

-- Keep every issued run. Later updates must INSERT a new row, never overwrite.
CREATE UNIQUE INDEX IF NOT EXISTS weather_forecasts_run_uidx
    ON weather_forecasts (
        forecast_source,
        model,
        issued_at,
        target_at,
        COALESCE(station_id, 0),
        ROUND(forecast_lat::numeric, 5),
        ROUND(forecast_lon::numeric, 5)
    );

CREATE INDEX IF NOT EXISTS weather_forecasts_target_idx
    ON weather_forecasts (target_at);

CREATE INDEX IF NOT EXISTS weather_forecasts_station_target_idx
    ON weather_forecasts (station_id, target_at)
    WHERE station_id IS NOT NULL;

INSERT INTO weather_stations (
    slug, display_name, provider, provider_station_id, kind,
    latitude, longitude, timezone, native_interval_sec, is_active,
    event_regatta_id, meta
) VALUES (
    'w2s-zeekoevlei',
    'Zeekoevlei',
    'wind2speed',
    '35',
    'observation',
    -34.065,
    18.508,
    'Africa/Johannesburg',
    180,
    true,
    '2026-09-13-zvyc-cape-classic',
    jsonb_build_object(
        'code', 'W2SZEEKOE01',
        'widget', 'https://wind2speed.africa/widgetPage/35',
        'feed', 'https://wind2speed.africa/apidata/wsdata/35'
    )
)
ON CONFLICT (provider, provider_station_id) DO UPDATE SET
    slug = EXCLUDED.slug,
    display_name = EXCLUDED.display_name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    native_interval_sec = EXCLUDED.native_interval_sec,
    event_regatta_id = EXCLUDED.event_regatta_id,
    meta = weather_stations.meta || EXCLUDED.meta,
    updated_at = now();

GRANT SELECT, INSERT, UPDATE, DELETE ON weather_stations, weather_readings, weather_forecasts TO sailors_user;
GRANT USAGE, SELECT ON SEQUENCE weather_stations_id_seq, weather_readings_id_seq, weather_forecasts_id_seq TO sailors_user;
