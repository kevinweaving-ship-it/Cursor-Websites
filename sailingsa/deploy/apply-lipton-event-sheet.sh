#!/bin/bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_sheet_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/css/lipton-dev.css \
  /var/www/sailingsa/js/lipton-event-sheet.js 2>/dev/null || true
ls -la "/root/backup_lipton_sheet_${TS}.tar.gz" 2>/dev/null || echo "WARN: no backup tarball"
cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js
# do not rewrite nginx / do not restore old event page
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?race=7'
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("sheetjs", "lipton-event-sheet.js" in t)
print("weather", "WEATHER" in t or "Live cam" in t)
print("bytes", len(t))
PY
