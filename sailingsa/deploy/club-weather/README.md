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

Without `WU_API_KEY`, Agromet + Wind2Speed still ingest; all `weather_underground` stations stay empty.
