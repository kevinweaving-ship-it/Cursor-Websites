#!/bin/bash
# DEV only: public results-table look on -dev ?live=gps. Do not replace api.py.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_dev_pubtbl_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/css/lipton-dev.css \
  /var/www/sailingsa/js/lipton-event-sheet.js \
  /var/www/sailingsa/js/lipton-dev-playback-du.js 2>/dev/null || true
ls -la "/root/backup_lipton_dev_pubtbl_${TS}.tar.gz"

cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
mkdir -p /var/www/sailingsa/frontend /var/www/sailingsa/css /var/www/sailingsa/js \
  /var/www/sailingsa/frontend/css /var/www/sailingsa/frontend/js
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-dev.css /var/www/sailingsa/frontend/css/lipton-dev.css
cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js
cp /tmp/lipton-event-sheet.js /var/www/sailingsa/frontend/js/lipton-event-sheet.js
cp /tmp/lipton-dev-playback-du.js /var/www/sailingsa/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-playback-du.js /var/www/sailingsa/frontend/js/lipton-dev-playback-du.js

echo "=== page ==="
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'dev %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev?live=gps'
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("dev", 'data-lipton-dev="1"' in t)
print("pubtbl", "20260829pubtbl" in t)
print("sheetjs", "lipton-event-sheet.js?v=20260829pubtbl" in t)
print("hide-race-sheet", 'data-lipton-race-mode="1"] .lipton-event-sheet' not in open("/var/www/sailingsa/css/lipton-dev.css",encoding="utf-8").read())
print("no70", "font-size:70%" not in open("/var/www/sailingsa/js/lipton-event-sheet.js",encoding="utf-8").read())
print("boat-name", "Boat Name" in t)
PY
