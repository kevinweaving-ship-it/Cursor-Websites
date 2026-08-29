#!/bin/bash
set -euo pipefail
cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
grep -n '20260828dp' /var/www/sailingsa/lipton-dev.html
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
python3 - <<'PY'
t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
print("dp", "20260828dp" in t)
print("playback", "lipton-dev-playback" in t)
print("weather", "WEATHER" in t or "Live cam" in t)
PY
