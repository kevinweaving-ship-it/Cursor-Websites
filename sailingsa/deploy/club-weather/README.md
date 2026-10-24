# Club weather + cameras (SailingSA box)

Club weather is **not** Tuya and not the aerialnet Olarm stack. It runs on sailingsa.co.za.

## What must stay on sailingsa

| Club | Weather | Camera |
|------|---------|--------|
| HMYC | UKZN Agromet Midmar (`agromet-midmar`) | still `hmyccam1.nwsza.net` via `/api/club-cam/hmyc` |
| ZVYC | Wind2Speed Zeekoevlei | Skyline webcam proxy in `api.py` |
| HYC | Weather Underground PWS (needs `WU_API_KEY`) | Hikvision via `/opt/hycnvr` + `hikpoc-go2rtc` → `/api/club-cam/hyc` |
| Other clubs | WU PWS catalog | — |

Voelklip/HOME Hikvision alarm cams live on **aerialnet**. HYC club cam stays on sailingsa `hikpoc-go2rtc` (stream `hyc`).

## Install / restore

```bash
install -m 0755 ingest_club_weather.py /opt/sailingsa-weather-ingest/ingest_club_weather.py
install -m 0644 sailingsa-club-weather-ingest.service /etc/systemd/system/
install -m 0644 sailingsa-club-weather-ingest.timer /etc/systemd/system/
install -m 0644 hyc-cam-visible.conf /etc/systemd/system/sailingsa-api.service.d/
# put DB_URL=... and optionally WU_API_KEY=... in /etc/sailingsa/weather.env
systemctl daemon-reload
systemctl enable --now hikpoc-go2rtc sailingsa-club-weather-ingest.timer
systemctl restart sailingsa-api
```

Without a working WU key, Agromet + Wind2Speed still ingest. WU PWS (HYC IOVERS2 and catalog)
auto-discovers the browser key from the live dashboard when env keys are missing or rotated.

## WU site watch + autofix

`weather_wu_discover.py` knows the scrape contract (`REQUIRED_SCRAPE`): dashboard URL, browser
`apiKey`, current/1-day observation endpoints, and observation fields (`obsTimeUtc`, wind, temp…).

| Trigger | Action |
|---------|--------|
| Missing / dead key | Scrape dashboard → probe keys → cache working one |
| API 401/403 mid-fetch | Re-scrape + retry once (`fetch_with_autofix`) |
| Every ingest (5 min) | Probe cached key (`watch_site_and_autofix`) |
| Every 30 min soft watch | Re-fetch dashboard HTML fingerprint; rediscover if site redesign changed keys/paths |

- Used by `weather_hyc.py` (`/api/weather/hyc/history`), `weather_pws.wu_api_key()`, and
  `ingest_club_weather.py` (watch runs first each cycle).
- Cache: `/var/www/sailingsa/data/wu_discover_cache.json`
- Install modules into `/var/www/sailingsa/api/` (`weather_wu_discover.py`, `weather_hyc.py`) and
  ingest into `/opt/sailingsa-weather-ingest/`.
