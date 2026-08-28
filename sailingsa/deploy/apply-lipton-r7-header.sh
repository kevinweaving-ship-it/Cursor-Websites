#!/bin/bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_r7_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/js/lipton-dev-playback.js \
  /var/www/sailingsa/js/lipton-dev-races.json \
  /var/www/sailingsa/css/lipton-dev.css 2>/dev/null || true
ls -la "/root/backup_lipton_r7_${TS}.tar.gz" 2>/dev/null || echo "WARN: no backup tarball"
cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dt.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-ds.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dq.js
cp /tmp/lipton-dev-races.json /var/www/sailingsa/js/lipton-dev-races.json
test -f /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
# keep public slug on playback
if test -s /tmp/kill-all-lipton-watches.sh; then
  bash /tmp/kill-all-lipton-watches.sh
else
  curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
    'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
  python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("dt", "playback-dt.js" in t)
print("weather", "WEATHER" in t)
PY
fi
grep -n '"n": 7' /var/www/sailingsa/js/lipton-dev-races.json | head
