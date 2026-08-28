#!/bin/bash
set -euo pipefail
echo '=== disable opposing watch ==='
ls -la /etc/cron.d/sailingsa-lipton-public-not-dev /var/www/sailingsa/deploy/lipton_public_not_dev_watch.py /var/www/sailingsa/deploy/patch_lipton_nginx_public_not_dev_v2.py 2>/dev/null || true
echo '--- cron ---'
cat /etc/cron.d/sailingsa-lipton-public-not-dev 2>/dev/null || true
echo '--- procs ---'
ps aux | grep -E 'public_not_dev|lipton_public_not|lipton_install_watch|lipton_watch' | grep -v grep || true

mkdir -p /root/disabled-lipton-not-dev
for f in \
  /etc/cron.d/sailingsa-lipton-public-not-dev \
  /var/www/sailingsa/deploy/lipton_public_not_dev_watch.py \
  /var/www/sailingsa/deploy/patch_lipton_nginx_public_not_dev_v2.py \
  /var/www/sailingsa/deploy/patch_lipton_nginx_public_not_dev.py \
  /tmp/lipton_public_not_dev_watch.py \
  /tmp/patch_lipton_nginx_public_not_dev_v2.py \
  /tmp/patch_lipton_nginx_public_not_dev.py \
  /tmp/lipton_install_watch.sh \
  /tmp/lipton_reinstall_watch.sh \
  /tmp/lipton_install_proxy.sh
 do
  if test -e "$f"; then
    mv "$f" /root/disabled-lipton-not-dev/ || true
    echo "moved $f"
  fi
 done

pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
pkill -f patch_lipton_nginx_public_not_dev 2>/dev/null || true

# keep our lock immutable
chattr -i /etc/nginx/sites-enabled/sailingsa 2>/dev/null || true
if ! grep -q 'location = /regatta/2026-08-29-lipton-challenge-cup {' /etc/nginx/sites-enabled/sailingsa; then
  cp /root/lipton-nginx-golden.conf /etc/nginx/sites-enabled/sailingsa
  nginx -t && nginx -s reload
fi
chattr +i /etc/nginx/sites-enabled/sailingsa || true
lsattr /etc/nginx/sites-enabled/sailingsa
grep -c 'location = /regatta/2026-08-29-lipton-challenge-cup {' /etc/nginx/sites-enabled/sailingsa

sleep 3
echo '=== verify ==='
python3 - <<'PY'
import json, subprocess, time
for i in range(8):
    raw = subprocess.check_output(["curl","-sS","-o","/tmp/live.json","-w","%{http_code}" ,"https://sailingsa.co.za/api/lipton-dev/live"], text=True, errors="replace")
    print("live_http", raw)
    if raw == "200":
        break
    time.sleep(2)
html = subprocess.check_output(["curl","-sS","https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1"], text=True, errors="replace")
print("page playback", "lipton-dev-playback" in html, "weather", any(x in html for x in ("WEATHER","Live cam DELAYED")), "bytes", len(html))
try:
    d=json.loads(open("/tmp/live.json").read())
    print("live", {k:d.get(k) for k in ("ok","waiting","race_number","stage","gun_sast","holding_last")})
    print("boats", len(d.get("boats") or {}))
except Exception as e:
    print("live parse", e, open("/tmp/live.json").read()[:200])
PY
echo '=== remaining not-dev ==='
ls /etc/cron.d | grep -i lipton || true
grep -l public_not_dev /etc/cron.d/* /var/www/sailingsa/deploy/* 2>/dev/null || true
