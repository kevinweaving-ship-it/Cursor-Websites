#!/bin/bash
# DEV slug only: restore R1–R10 replay HTML/JS. No nginx. No public URL. No api.py.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_dev_tracking_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/css/lipton-dev.css \
  /var/www/sailingsa/js/lipton-dev-playback-du.js \
  /var/www/sailingsa/js/lipton-dev-races.json 2>/dev/null || true
ls -la "/root/backup_lipton_dev_tracking_${TS}.tar.gz"

cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-dev-playback-du.js /var/www/sailingsa/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-races.json /var/www/sailingsa/js/lipton-dev-races.json

# Race 4 is stored as replay.json / trail.json; also publish -r4 aliases.
if test -s /tmp/lipton-dev-replay-r4.json; then
  cp /tmp/lipton-dev-replay-r4.json /var/www/sailingsa/js/lipton-dev-replay-r4.json
  cp /tmp/lipton-dev-replay-r4.json /var/www/sailingsa/js/lipton-dev-replay.json
fi
if test -s /tmp/lipton-dev-trail-r4.json; then
  cp /tmp/lipton-dev-trail-r4.json /var/www/sailingsa/js/lipton-dev-trail-r4.json
  cp /tmp/lipton-dev-trail-r4.json /var/www/sailingsa/js/lipton-dev-trail.json
fi

chown www-data:www-data /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/css/lipton-dev.css \
  /var/www/sailingsa/js/lipton-dev-playback-du.js \
  /var/www/sailingsa/js/lipton-dev-races.json || true

echo "=== DEV page only ==="
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'dev %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev?race=10'
python3 - <<'PY'
from pathlib import Path
t = Path("/tmp/p.html").read_text(encoding="utf-8", errors="replace")
print("dev_flag", 'data-lipton-dev="1"' in t)
print("playback_du", "lipton-dev-playback-du.js" in t)
print("old_playback_js", "lipton-dev-playback.js?" in t)
print("cache", "20260903track" in t)
print("no_live_ticker", "Race 10 — LIVE" not in t)
r = Path("/var/www/sailingsa/js/lipton-dev-races.json").read_text(encoding="utf-8")
print("races", [x for x in range(1, 11) if f'"n": {x}' in r or f'"n":{x}' in r])
PY
