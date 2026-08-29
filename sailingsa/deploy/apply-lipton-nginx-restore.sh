#!/bin/bash
# Restore Lipton playback lock. Backups MUST NOT live in sites-enabled.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
ENABLED=/etc/nginx/sites-enabled/sailingsa
AVAILABLE=/etc/nginx/sites-available/sailingsa
NEW=/tmp/nginx-sailingsa-playback-lock.conf
BAKDIR=/root/nginx-bak-${TS}

test -s "$NEW"
test -s "$ENABLED"
mkdir -p "$BAKDIR"

cp -a "$ENABLED" "$BAKDIR/sites-enabled-sailingsa"
cp -a "$AVAILABLE" "$BAKDIR/sites-available-sailingsa"
# nginx include sites-enabled/* — never leave .bak files here
find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true
rm -f /etc/nginx/sites-enabled/sailingsa.bak* || true

cp "$NEW" "$ENABLED"
cp "$NEW" "$AVAILABLE"
echo "installed nginx conf $(wc -c < "$ENABLED") bytes backup $BAKDIR"
echo "sites-enabled files:"
ls -la /etc/nginx/sites-enabled/

if ! nginx -t; then
  echo "ERROR: nginx -t failed; restoring previous enabled conf"
  cp -a "$BAKDIR/sites-enabled-sailingsa" "$ENABLED"
  find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true
  nginx -t || true
  exit 1
fi

nginx -s reload
echo "nginx reloaded"

mkdir -p /var/www/sailingsa/js /var/www/sailingsa/css /var/www/sailingsa/frontend/js /var/www/sailingsa/sailingsa/scripts
cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dk.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dl.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dm.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dn.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/frontend/js/lipton-dev-playback.js
cp /tmp/lipton_dev_catchup.py /tmp/lipton_dev_live.py /var/www/sailingsa/sailingsa/scripts/
python3 /tmp/patch_lipton_public_slug.py

systemctl restart sailingsa-api
sleep 3
systemctl is-active sailingsa-api

cd /var/www/sailingsa/sailingsa/scripts
PYTHONPATH=/var/www/sailingsa/sailingsa/scripts python3 lipton_dev_catchup.py || true

python3 - <<'PY'
from pathlib import Path
import subprocess, json
url = "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1"
html = subprocess.check_output(["curl","-sS","-A","SailingSA-devcheck",url], text=True, errors="replace")
print("playback", "lipton-dev-playback" in html)
print("dnjs", "lipton-dev-playback-dn.js" in html)
print("old_weather", any(x in html for x in ("WEATHER", "Live cam DELAYED", "Live cam")))
live = subprocess.check_output(["curl","-sS","-A","SailingSA-devcheck","https://sailingsa.co.za/api/lipton-dev/live"], text=True)
d = json.loads(live)
print("live", {k: d.get(k) for k in ("waiting","race_number","stage","gun_sast","holding_last")})
print("boats", len(d.get("boats") or {}))
hist = Path("/var/www/sailingsa/js/lipton-dev-live-history.json")
if hist.is_file():
    h = json.loads(hist.read_text())
    print("hist", {k: h.get(k) for k in ("waiting","race_number","stage","gun_sast")})
    print("hist_boats", len(h.get("boats") or {}))
PY
