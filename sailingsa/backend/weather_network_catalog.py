"""Station catalog for the generic weather network.

Adding a station is a catalog change, not a new fetch adapter.
PWS ingest always goes through weather_pws.ingest_pws_network.
"""
from __future__ import annotations

# Club sailing-area pins used only to compute distance_km / role. Not truth.
CLUBS = [
    {"code": "HBYC", "club_id": 8, "name": "Hout Bay Yacht Club", "lat": -34.0500, "lon": 18.3440, "radius_km": 25},
    {"code": "ZVYC", "club_id": 3, "name": "Zeekoe Vlei Yacht Club", "lat": -34.0650, "lon": 18.5080, "radius_km": 20},
    {"code": "HYC", "club_id": 10, "name": "Hermanus Yacht Club", "lat": -34.4330, "lon": 19.2240, "radius_km": 40},
    {"code": "TSC", "club_id": 6, "name": "Theewater Sports Club", "lat": -34.0780, "lon": 19.2890, "radius_km": 40},
    {"code": "FBYC", "club_id": 18, "name": "False Bay Yacht Club", "lat": -34.1930, "lon": 18.4320, "radius_km": 20},
    {"code": "RCYC", "club_id": 11, "name": "Royal Cape Yacht Club", "lat": -33.9210, "lon": 18.4430, "radius_km": 25},
    {"code": "HMYC", "club_id": 98, "name": "Henley Midmar Yacht Club", "lat": -29.4940, "lon": 30.1940, "radius_km": 20},
    {"code": "LDYC", "club_id": 85, "name": "Lake Deneys Yacht Club", "lat": -26.9000, "lon": 28.1000, "radius_km": 45},
    {"code": "SBYC", "club_id": 17, "name": "Saldanha Bay Yacht Club", "lat": -33.0080, "lon": 17.9580, "radius_km": 40},
]

PWS_META = {
    "network": "weather_company_pws",
    "feed": "https://api.weather.com/v2/pws/observations/current",
    "poll_enabled": False,
    "poll_blocked_reason": "no_api_key",
    "independent": True,
}

STATIONS = [
    # Already seeded by 001; listed so club maps can reference the slug.
    {
        "slug": "w2s-zeekoevlei",
        "display_name": "Zeekoevlei Wind2Speed",
        "provider": "wind2speed",
        "provider_station_id": "35",
        "kind": "observation",
        "lat": -34.065,
        "lon": 18.508,
        "native_interval_sec": 180,
        "meta": {"code": "W2SZEEKOE01", "feed": "https://wind2speed.africa/apidata/wsdata/35", "independent": True},
    },
    # HYC / Overberg PWS (operator-verified)
    {"slug": "pws-iherma37", "display_name": "Hermanus IHERMA37", "provider": "weather_underground", "provider_station_id": "IHERMA37", "kind": "observation", "lat": -34.42, "lon": 19.24, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHERMA37", "coords_source": "operator_approx"}},
    {"slug": "pws-iherma44", "display_name": "Hermanus IHERMA44", "provider": "weather_underground", "provider_station_id": "IHERMA44", "kind": "observation", "lat": -34.43, "lon": 19.22, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHERMA44", "coords_source": "operator_approx"}},
    {"slug": "pws-ionrus12", "display_name": "Onrus IONRUS12", "provider": "weather_underground", "provider_station_id": "IONRUS12", "kind": "observation", "lat": -34.41, "lon": 19.17, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IONRUS12", "coords_source": "operator_approx"}},
    {"slug": "pws-ionrus13", "display_name": "Vermont/Onrus IONRUS13", "provider": "weather_underground", "provider_station_id": "IONRUS13", "kind": "observation", "lat": -34.42, "lon": 19.15, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IONRUS13", "coords_source": "operator_approx"}},
    {"slug": "pws-iovers2", "display_name": "Hermanus Yacht Club IOVERS2", "provider": "weather_underground", "provider_station_id": "IOVERS2", "kind": "observation", "lat": -34.41, "lon": 19.35, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IOVERS2", "coords_source": "wu_public_dashboard", "venue": "hermanus_yacht_club", "note": "WU published GPS is east of HYC harbour pin"}},
    {"slug": "pws-istanf10", "display_name": "Stanford ISTANF10", "provider": "weather_underground", "provider_station_id": "ISTANF10", "kind": "observation", "lat": -34.44, "lon": 19.46, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ISTANF10", "coords_source": "operator_approx"}},
    # HBYC
    {"slug": "pws-ihoutbay3", "display_name": "Hout Bay Beach Estate IHOUTBAY3", "provider": "weather_underground", "provider_station_id": "IHOUTBAY3", "kind": "observation", "lat": -34.04, "lon": 18.35, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHOUTBAY3", "coords_source": "wu_public_dashboard", "anchor_candidate": True, "not_authoritative": True}},
    {"slug": "pws-ihoutb4", "display_name": "Hout Bay Ruyteplaats IHOUTB4", "provider": "weather_underground", "provider_station_id": "IHOUTB4", "kind": "observation", "lat": -34.01, "lon": 18.36, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHOUTB4", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-ihoutb8", "display_name": "Hout Bay Tarragona IHOUTB8", "provider": "weather_underground", "provider_station_id": "IHOUTB8", "kind": "observation", "lat": -34.01, "lon": 18.38, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHOUTB8", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-ihoutb10", "display_name": "Hout Bay Stoney IHOUTB10", "provider": "weather_underground", "provider_station_id": "IHOUTB10", "kind": "observation", "lat": -34.010, "lon": 18.384, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHOUTB10", "coords_source": "wu_public_dashboard"}},
    # ZVYC regional PWS
    {"slug": "pws-iwestern505", "display_name": "Zeekoevlei IWESTERN505", "provider": "weather_underground", "provider_station_id": "IWESTERN505", "kind": "observation", "lat": -34.065, "lon": 18.510, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IWESTERN505", "coords_source": "wu_public_dashboard", "often_offline": True}},
    {"slug": "pws-icapet148", "display_name": "Plumstead ICAPET148", "provider": "weather_underground", "provider_station_id": "ICAPET148", "kind": "observation", "lat": -34.02, "lon": 18.47, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ICAPET148", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-icapet141", "display_name": "Rondebosch Abbots Lane ICAPET141", "provider": "weather_underground", "provider_station_id": "ICAPET141", "kind": "observation", "lat": -33.97, "lon": 18.49, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ICAPET141", "coords_source": "wu_public_dashboard"}},
    # TSC
    {"slug": "pws-itheew10", "display_name": "Theewaterskloof EGCC ITHEEW10", "provider": "weather_underground", "provider_station_id": "ITHEEW10", "kind": "observation", "lat": -34.128, "lon": 19.024, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ITHEEW10", "coords_source": "operator_approx"}},
    # FBYC / False Bay
    {"slug": "pws-ikingedw2", "display_name": "Simons Kloof IKINGEDW2", "provider": "weather_underground", "provider_station_id": "IKINGEDW2", "kind": "observation", "lat": -34.196, "lon": 18.435, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IKINGEDW2", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-isimon8", "display_name": "Simon’s Town Pete’s Weather ISIMON8", "provider": "weather_underground", "provider_station_id": "ISIMON8", "kind": "observation", "lat": -34.20, "lon": 18.43, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ISIMON8", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-iwestern273", "display_name": "Fish Hoek Fishermans Watch IWESTERN273", "provider": "weather_underground", "provider_station_id": "IWESTERN273", "kind": "observation", "lat": -34.14, "lon": 18.43, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IWESTERN273", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-icapet132", "display_name": "Kalk Bay ICAPET132", "provider": "weather_underground", "provider_station_id": "ICAPET132", "kind": "observation", "lat": -34.125, "lon": 18.449, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ICAPET132", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-ifishh7", "display_name": "Fish Hoek IFISHH7", "provider": "weather_underground", "provider_station_id": "IFISHH7", "kind": "observation", "lat": -34.14, "lon": 18.43, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IFISHH7", "coords_source": "wu_public_dashboard", "discovered": True, "note": "dashboard reports rain/wind sensors failed; keep registered"}},
    # RCYC / Table Bay
    {"slug": "metar-fact", "display_name": "FACT METAR Cape Town Intl", "provider": "aviationweather_metar", "provider_station_id": "FACT", "kind": "observation", "lat": -33.9647, "lon": 18.6017, "native_interval_sec": 1800, "meta": {"feed": "https://aviationweather.gov/api/data/metar", "independent": True, "not_harbour": True}},
    {"slug": "open-meteo-table-bay-atm", "display_name": "Open-Meteo Table Bay atmosphere", "provider": "open_meteo", "provider_station_id": "table-bay-atm", "kind": "forecast_point", "lat": -33.8603685, "lon": 18.3622621, "native_interval_sec": 900, "meta": {"feed": "https://api.open-meteo.com/v1/forecast", "independent": True, "model_point": True, "pin": "table_bay_race"}},
    {"slug": "open-meteo-table-bay-marine", "display_name": "Open-Meteo Table Bay marine", "provider": "open_meteo_marine", "provider_station_id": "table-bay-marine", "kind": "forecast_point", "lat": -33.8603685, "lon": 18.3622621, "native_interval_sec": 900, "meta": {"feed": "https://marine-api.open-meteo.com/v1/marine", "independent": True, "model_point": True, "pin": "table_bay_race"}},
    {"slug": "pws-imilne23", "display_name": "Century City Bridges IMILNE23", "provider": "weather_underground", "provider_station_id": "IMILNE23", "kind": "observation", "lat": -33.896, "lon": 18.504, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IMILNE23", "coords_source": "wu_public_dashboard"}},
    {"slug": "pws-imilne4", "display_name": "Edgemead WJ2000 IMILNE4", "provider": "weather_underground", "provider_station_id": "IMILNE4", "kind": "observation", "lat": -33.87, "lon": 18.55, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IMILNE4", "coords_source": "wu_public_dashboard"}},
    # HMYC / Howick — South Africa only (not Howick NZ)
    {"slug": "pws-imidma1", "display_name": "Henley Midmar IMIDMA1", "provider": "weather_underground", "provider_station_id": "IMIDMA1", "kind": "observation", "lat": -29.494, "lon": 30.194, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IMIDMA1", "coords_source": "operator_approx", "country": "ZA", "often_offline": True}},
    {"slug": "pws-ihowic41", "display_name": "Howick HathornMet IHOWIC41", "provider": "weather_underground", "provider_station_id": "IHOWIC41", "kind": "observation", "lat": -29.48, "lon": 30.22, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHOWIC41", "coords_source": "wu_public_dashboard", "country": "ZA"}},
    {"slug": "pws-ihowic40", "display_name": "Howick AAG IHOWIC40", "provider": "weather_underground", "provider_station_id": "IHOWIC40", "kind": "observation", "lat": -29.47, "lon": 30.22, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IHOWIC40", "coords_source": "wu_public_dashboard", "country": "ZA"}},
    {"slug": "pws-ikwazulu107", "display_name": "Howick Amber Glades IKWAZULU107", "provider": "weather_underground", "provider_station_id": "IKWAZULU107", "kind": "observation", "lat": -29.47, "lon": 30.25, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IKWAZULU107", "coords_source": "wu_public_dashboard", "country": "ZA"}},
    # LDYC / Vaal
    {"slug": "pws-ideneysv2", "display_name": "Deneysville LDYC IDENEYSV2", "provider": "weather_underground", "provider_station_id": "IDENEYSV2", "kind": "observation", "lat": -26.90, "lon": 28.10, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IDENEYSV2", "coords_source": "operator_approx", "often_offline": True}},
    {"slug": "pws-imidva3", "display_name": "Midvaal NU / Three Rivers IMIDVA3", "provider": "weather_underground", "provider_station_id": "IMIDVA3", "kind": "observation", "lat": -26.665, "lon": 28.017, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IMIDVA3", "coords_source": "wu_public_dashboard"}},
    # SBYC / West Coast
    {"slug": "pws-isalda19", "display_name": "Saldanha Hennie ISALDA19", "provider": "weather_underground", "provider_station_id": "ISALDA19", "kind": "observation", "lat": -33.00, "lon": 17.95, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ISALDA19", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-isalda21", "display_name": "Saldanha Sardine ISALDA21", "provider": "weather_underground", "provider_station_id": "ISALDA21", "kind": "observation", "lat": -33.01, "lon": 17.95, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ISALDA21", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-isalda8", "display_name": "Saldanha Bay NU ISALDA8", "provider": "weather_underground", "provider_station_id": "ISALDA8", "kind": "observation", "lat": -32.94, "lon": 18.09, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ISALDA8", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-ilange504", "display_name": "Langebaan Roode Vos ILANGE504", "provider": "weather_underground", "provider_station_id": "ILANGE504", "kind": "observation", "lat": -33.09, "lon": 18.04, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ILANGE504", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-ilange219", "display_name": "Langebaan AMB5000 ILANGE219", "provider": "weather_underground", "provider_station_id": "ILANGE219", "kind": "observation", "lat": -33.07, "lon": 18.05, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ILANGE219", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-icapet66", "display_name": "Vredehoek ICAPET66", "provider": "weather_underground", "provider_station_id": "ICAPET66", "kind": "observation", "lat": -33.940, "lon": 18.422, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ICAPET66", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-icapemet5", "display_name": "Blouberg ICAPEMET5", "provider": "weather_underground", "provider_station_id": "ICAPEMET5", "kind": "observation", "lat": -33.79, "lon": 18.48, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ICAPEMET5", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-icapet47", "display_name": "Tokai ICAPET47", "provider": "weather_underground", "provider_station_id": "ICAPET47", "kind": "observation", "lat": -34.07, "lon": 18.44, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "ICAPET47", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-igpvaalm2", "display_name": "Vaal Dam / Vaal Marina IGPVAALM2", "provider": "weather_underground", "provider_station_id": "IGPVAALM2", "kind": "observation", "lat": -26.87, "lon": 28.20, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IGPVAALM2", "coords_source": "wu_public_dashboard", "discovered": True}},
    {"slug": "pws-iveree6", "display_name": "Vereeniging Unitaspark IVEREE6", "provider": "weather_underground", "provider_station_id": "IVEREE6", "kind": "observation", "lat": -26.634, "lon": 27.916, "native_interval_sec": 300, "meta": {**PWS_META, "pws_id": "IVEREE6", "coords_source": "wu_public_dashboard", "discovered": True}},
]

# Explicit many-to-many. Same physical station may appear under several clubs.
# role: venue | nearby | regional. weight left null for later learning.
LINKS = [
    # HBYC
    ("HBYC", "pws-ihoutbay3", "nearby"),
    ("HBYC", "pws-ihoutb4", "nearby"),
    ("HBYC", "pws-ihoutb8", "nearby"),
    ("HBYC", "pws-ihoutb10", "nearby"),
    # ZVYC
    ("ZVYC", "w2s-zeekoevlei", "venue"),
    ("ZVYC", "pws-iwestern505", "venue"),
    ("ZVYC", "pws-icapet148", "nearby"),
    ("ZVYC", "pws-icapet141", "nearby"),
    ("ZVYC", "pws-iwestern273", "nearby"),
    # HYC
    ("HYC", "pws-iovers2", "venue"),
    ("HYC", "pws-iherma44", "nearby"),
    ("HYC", "pws-iherma37", "nearby"),
    ("HYC", "pws-ionrus12", "nearby"),
    ("HYC", "pws-ionrus13", "nearby"),
    ("HYC", "pws-istanf10", "regional"),
    # TSC
    ("TSC", "pws-itheew10", "regional"),
    # FBYC
    ("FBYC", "pws-ikingedw2", "venue"),
    ("FBYC", "pws-isimon8", "venue"),
    ("FBYC", "pws-iwestern273", "nearby"),
    ("FBYC", "pws-icapet132", "nearby"),
    ("FBYC", "pws-ifishh7", "nearby"),
    ("FBYC", "pws-icapet148", "regional"),
    # RCYC — keep Table Bay sources distinct
    ("RCYC", "open-meteo-table-bay-atm", "venue"),
    ("RCYC", "open-meteo-table-bay-marine", "venue"),
    ("RCYC", "metar-fact", "regional"),
    ("RCYC", "pws-imilne23", "nearby"),
    ("RCYC", "pws-imilne4", "nearby"),
    ("RCYC", "pws-icapet141", "nearby"),
    # HMYC
    ("HMYC", "pws-imidma1", "venue"),
    ("HMYC", "pws-ihowic41", "nearby"),
    ("HMYC", "pws-ihowic40", "nearby"),
    ("HMYC", "pws-ikwazulu107", "nearby"),
    # LDYC
    ("LDYC", "pws-ideneysv2", "venue"),
    ("LDYC", "pws-imidva3", "regional"),
    # SBYC
    ("SBYC", "pws-isalda21", "nearby"),
    ("SBYC", "pws-isalda19", "nearby"),
    ("SBYC", "pws-isalda8", "nearby"),
    ("SBYC", "pws-ilange504", "nearby"),
    ("SBYC", "pws-ilange219", "nearby"),
    ("ZVYC", "pws-icapet47", "nearby"),
    ("FBYC", "pws-icapet47", "nearby"),
    ("RCYC", "pws-icapet66", "nearby"),
    ("RCYC", "pws-icapemet5", "regional"),
    ("LDYC", "pws-igpvaalm2", "nearby"),
    ("LDYC", "pws-iveree6", "regional"),
]
