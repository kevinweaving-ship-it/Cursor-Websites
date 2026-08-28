#!/bin/bash
set -euo pipefail
cp /tmp/lipton_dev_live.py /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py
cp /tmp/lipton_dev_live.py /var/www/sailingsa/scripts/lipton_dev_live.py
cp /tmp/lipton_dev_catchup.py /var/www/sailingsa/sailingsa/scripts/lipton_dev_catchup.py
cp /tmp/lipton_dev_catchup.py /var/www/sailingsa/scripts/lipton_dev_catchup.py
find /var/www/sailingsa -name 'lipton_dev_live*.pyc' -delete
find /var/www/sailingsa -path '*__pycache__*lipton_dev_live*' -delete || true
echo 'holding_last copies:'
grep -c holding_last /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py /var/www/sailingsa/scripts/lipton_dev_live.py
systemctl restart sailingsa-api
sleep 4
systemctl is-active sailingsa-api
cd /var/www/sailingsa/scripts
PYTHONPATH=/var/www/sailingsa/scripts python3 - <<'PY'
from lipton_dev_live import live_snapshot
d = live_snapshot(history=False)
print("direct", {k: d.get(k) for k in ("waiting","race_number","stage","gun_sast","holding_last")})
print("boats", len(d.get("boats") or {}))
PY
curl -sS -A SailingSA-devcheck -o /tmp/live.json -w 'live_http=%{http_code} bytes=%{size_download}\n' \
  https://sailingsa.co.za/api/lipton-dev/live
python3 - <<'PY'
import json
d=json.loads(open("/tmp/live.json").read())
print("api", {k: d.get(k) for k in ("ok","waiting","race_number","stage","gun_sast","holding_last")})
print("boats", len(d.get("boats") or {}))
PY
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page_http=%{http_code} bytes=%{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("old_weather", any(x in t for x in ("WEATHER","Live cam","DELAYED")))
PY
