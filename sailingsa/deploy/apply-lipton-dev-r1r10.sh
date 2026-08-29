#!/bin/bash
# DEV only: R1–R10 replay, no Live. Do not replace api.py.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_dev_r1r10_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/css/lipton-dev.css \
  /var/www/sailingsa/js/lipton-dev-playback-du.js \
  /var/www/sailingsa/js/lipton-dev-races.json \
  /var/www/sailingsa/js/lipton-event-sheet.js 2>/dev/null || true
ls -la "/root/backup_lipton_dev_r1r10_${TS}.tar.gz"

mkdir -p /var/www/sailingsa/frontend /var/www/sailingsa/css /var/www/sailingsa/js \
  /var/www/sailingsa/frontend/css /var/www/sailingsa/frontend/js

cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-dev.css /var/www/sailingsa/frontend/css/lipton-dev.css
cp /tmp/lipton-dev-playback-du.js /var/www/sailingsa/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-playback-du.js /var/www/sailingsa/frontend/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-races.json /var/www/sailingsa/js/lipton-dev-races.json
cp /tmp/lipton-dev-races.json /var/www/sailingsa/frontend/js/lipton-dev-races.json

for n in 6 8 9 10; do
  test -s /tmp/lipton-dev-replay-r${n}.json
  cp /tmp/lipton-dev-replay-r${n}.json /var/www/sailingsa/js/lipton-dev-replay-r${n}.json
  cp /tmp/lipton-dev-replay-r${n}.json /var/www/sailingsa/frontend/js/lipton-dev-replay-r${n}.json
  test -s /tmp/lipton-dev-trail-r${n}.json
  cp /tmp/lipton-dev-trail-r${n}.json /var/www/sailingsa/js/lipton-dev-trail-r${n}.json
  cp /tmp/lipton-dev-trail-r${n}.json /var/www/sailingsa/frontend/js/lipton-dev-trail-r${n}.json
done

echo "=== page ==="
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'dev %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev?race=10'
python3 - <<'PY'
from pathlib import Path
t=Path("/tmp/p.html").read_text(encoding="utf-8", errors="replace")
print("dev", 'data-lipton-dev="1"' in t)
print("r1r10", "20260829r1r10" in t)
print("live-gps-default", "live=gps" not in t or "race=10" in t)
r=Path("/var/www/sailingsa/js/lipton-dev-races.json").read_text(encoding="utf-8")
print("races10", '"n": 10' in r, "no held_live r8", r.count('"held_live": true')==0)
print("replay10", Path("/var/www/sailingsa/js/lipton-dev-replay-r10.json").is_file())
print("trail10", Path("/var/www/sailingsa/js/lipton-dev-trail-r10.json").stat().st_size)
PY
