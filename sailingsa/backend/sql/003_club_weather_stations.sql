-- Club ↔ station many-to-many. One physical station is stored once.
-- weight stays NULL until later learned correlation. Do not average here.

ALTER TABLE weather_stations
    ADD COLUMN IF NOT EXISTS last_observation_at timestamptz,
    ADD COLUMN IF NOT EXISTS last_ingest_at timestamptz,
    ADD COLUMN IF NOT EXISTS last_failure_at timestamptz,
    ADD COLUMN IF NOT EXISTS last_failure_reason text;

CREATE TABLE IF NOT EXISTS club_weather_stations (
    id              bigserial PRIMARY KEY,
    club_code       text NOT NULL,
    club_id         integer,
    station_id      bigint NOT NULL REFERENCES weather_stations(id),
    distance_km     double precision,
    role            text NOT NULL,
    enabled         boolean NOT NULL DEFAULT true,
    weight          double precision,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT club_weather_stations_role_chk
        CHECK (role IN ('venue', 'nearby', 'regional')),
    CONSTRAINT club_weather_stations_uidx
        UNIQUE (club_code, station_id)
);

CREATE INDEX IF NOT EXISTS club_weather_stations_station_idx
    ON club_weather_stations (station_id);

CREATE INDEX IF NOT EXISTS club_weather_stations_club_idx
    ON club_weather_stations (club_code);

GRANT SELECT, INSERT, UPDATE, DELETE ON club_weather_stations TO sailors_user;
GRANT USAGE, SELECT ON SEQUENCE club_weather_stations_id_seq TO sailors_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON weather_stations, weather_readings, weather_forecasts TO sailors_user;
