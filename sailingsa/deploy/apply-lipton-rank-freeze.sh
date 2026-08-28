#!/bin/bash
set -euo pipefail
cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dn.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dq.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/frontend/js/lipton-dev-playback.js
grep -n 'playback-dq\|20260828dq\|20260828dp' /var/www/sailingsa/lipton-dev.html | head
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
python3 - <<'PY'
t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
print("dq", "lipton-dev-playback-dq.js" in t)
print("dp", "20260828dp" in t)
print("playback", "lipton-dev-playback" in t)
print("weather", "WEATHER" in t or "Live cam" in t)
PY
curl -sS -o /dev/null -w 'js %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/js/lipton-dev-playback-dq.js'
