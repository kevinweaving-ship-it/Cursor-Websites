#!/bin/bash
set -euo pipefail
echo '=== page ==='
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'http=%{http_code} bytes=%{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
python3 - <<'PY'
t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("dnjs", "lipton-dev-playback-dn.js" in t)
print("old_weather", any(x in t for x in ("WEATHER", "Live cam", "DELAYED")))
print("race_label", "lipton-dev-race-label" in t)
PY
echo '=== live ==='
curl -sS -A SailingSA-devcheck -o /tmp/live.json -w 'http=%{http_code} bytes=%{size_download}\n' \
  'https://sailingsa.co.za/api/lipton-dev/live'
python3 - <<'PY'
import json
t = open("/tmp/live.json", encoding="utf-8", errors="replace").read()
print("live_head", t[:400].replace("\n"," "))
try:
    d = json.loads(t)
except Exception as e:
    print("live_json_error", e)
else:
    print({k: d.get(k) for k in ("ok","waiting","race_number","stage","gun_sast","holding_last")})
    print("boats", len(d.get("boats") or {}))
PY
echo '=== nginx t ==='
nginx -t
echo '=== services ==='
systemctl is-active sailingsa-api nginx
