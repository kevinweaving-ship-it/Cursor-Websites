-- Public Weather Underground / Weather Company PWS stations (Overberg).
-- Independent observation sources. Poll stays off until an API key is configured.
-- GPS is required on every station.

INSERT INTO weather_stations (
    slug, display_name, provider, provider_station_id, kind,
    latitude, longitude, timezone, native_interval_sec, is_active, meta
) VALUES
(
    'pws-iherma37', 'Hermanus IHERMA37', 'weather_underground', 'IHERMA37',
    'observation', -34.42, 19.24, 'Africa/Johannesburg', 300, true,
    '{"network":"weather_company_pws","pws_id":"IHERMA37","feed":"https://api.weather.com/v2/pws/observations/current","poll_enabled":false,"poll_blocked_reason":"no_api_key","independent":true,"coords_source":"operator_approx"}'::jsonb
),
(
    'pws-iherma44', 'Hermanus IHERMA44', 'weather_underground', 'IHERMA44',
    'observation', -34.43, 19.22, 'Africa/Johannesburg', 300, true,
    '{"network":"weather_company_pws","pws_id":"IHERMA44","feed":"https://api.weather.com/v2/pws/observations/current","poll_enabled":false,"poll_blocked_reason":"no_api_key","independent":true,"coords_source":"operator_approx"}'::jsonb
),
(
    'pws-ionrus12', 'Onrus IONRUS12', 'weather_underground', 'IONRUS12',
    'observation', -34.41, 19.17, 'Africa/Johannesburg', 300, true,
    '{"network":"weather_company_pws","pws_id":"IONRUS12","feed":"https://api.weather.com/v2/pws/observations/current","poll_enabled":false,"poll_blocked_reason":"no_api_key","independent":true,"coords_source":"operator_approx"}'::jsonb
),
(
    'pws-ionrus13', 'Vermont/Onrus IONRUS13', 'weather_underground', 'IONRUS13',
    'observation', -34.42, 19.15, 'Africa/Johannesburg', 300, true,
    '{"network":"weather_company_pws","pws_id":"IONRUS13","feed":"https://api.weather.com/v2/pws/observations/current","poll_enabled":false,"poll_blocked_reason":"no_api_key","independent":true,"coords_source":"operator_approx"}'::jsonb
),
(
    'pws-iovers2', 'Hermanus Yacht Club IOVERS2', 'weather_underground', 'IOVERS2',
    'observation', -34.41, 19.35, 'Africa/Johannesburg', 300, true,
    '{"network":"weather_company_pws","pws_id":"IOVERS2","feed":"https://api.weather.com/v2/pws/observations/current","poll_enabled":false,"poll_blocked_reason":"no_api_key","independent":true,"coords_source":"wu_public_dashboard_approx","venue":"hermanus_yacht_club"}'::jsonb
),
(
    'pws-istanf10', 'Stanford ISTANF10', 'weather_underground', 'ISTANF10',
    'observation', -34.44, 19.46, 'Africa/Johannesburg', 300, true,
    '{"network":"weather_company_pws","pws_id":"ISTANF10","feed":"https://api.weather.com/v2/pws/observations/current","poll_enabled":false,"poll_blocked_reason":"no_api_key","independent":true,"coords_source":"operator_approx"}'::jsonb
)
ON CONFLICT (provider, provider_station_id) DO UPDATE SET
    slug = EXCLUDED.slug,
    display_name = EXCLUDED.display_name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    native_interval_sec = EXCLUDED.native_interval_sec,
    is_active = EXCLUDED.is_active,
    meta = weather_stations.meta || EXCLUDED.meta,
    updated_at = now();
