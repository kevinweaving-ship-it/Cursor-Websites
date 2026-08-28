#!/bin/bash
# Restore /sailor/* proxy. Keep Lipton playback lock. Backups never in sites-enabled.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
ENABLED=/etc/nginx/sites-enabled/sailingsa
AVAILABLE=/etc/nginx/sites-available/sailingsa
NEW=/tmp/nginx-sailingsa-playback-lock.conf
BAKDIR=/root/nginx-bak-${TS}

test -s "$NEW"
mkdir -p "$BAKDIR"
cp -a "$ENABLED" "$BAKDIR/sites-enabled-sailingsa"
cp -a "$AVAILABLE" "$BAKDIR/sites-available-sailingsa"
find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true

cp "$NEW" "$ENABLED"
cp "$NEW" "$AVAILABLE"
echo "installed $(wc -c < "$ENABLED") bytes; sailor_regex=$(grep -c 'location ~ ^/sailor/' "$ENABLED" || true); lipton_lock=$(grep -c 'location = /regatta/2026-08-29-lipton-challenge-cup {' "$ENABLED" || true)"
ls -la /etc/nginx/sites-enabled/

if ! nginx -t; then
  echo "ERROR: nginx -t failed; restoring"
  cp -a "$BAKDIR/sites-enabled-sailingsa" "$ENABLED"
  find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true
  nginx -t || true
  exit 1
fi
nginx -s reload
echo "nginx reloaded"

if test -s /tmp/lipton_dev_live.py; then
  cp /tmp/lipton_dev_live.py /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py
  cp /tmp/lipton_dev_live.py /var/www/sailingsa/scripts/lipton_dev_live.py
  find /var/www/sailingsa -name 'lipton_dev_live*.pyc' -delete || true
fi

python3 - <<'PY'
import json, subprocess, urllib.request

def curl(url, follow=False):
    cmd = ["curl","-sS","-A","SailingSA-devcheck","-o","/tmp/chk.html","-w","%{http_code} %{size_download} %{redirect_url}","-D","/tmp/chk.hdr"]
    if follow:
        cmd.append("-L")
    cmd.append(url)
    out = subprocess.check_output(cmd, text=True, errors="replace").strip()
    html = open("/tmp/chk.html", encoding="utf-8", errors="replace").read()
    i, j = html.find("<title>"), html.find("</title>")
    title = html[i:j+8] if i >= 0 else html[:80].replace("\n"," ")
    print(url, out, title)
    return html

print("=== sailors ===")
curl("https://sailingsa.co.za/sailor/sean-kavangh")
curl("https://sailingsa.co.za/sailor/sean-kavangh", follow=True)
curl("https://sailingsa.co.za/sailor/david-rae")
print("=== lipton ===")
html = curl("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1")
print("playback", "lipton-dev-playback" in html)
print("old_weather", any(x in html for x in ("WEATHER", "Live cam DELAYED")))
PY
