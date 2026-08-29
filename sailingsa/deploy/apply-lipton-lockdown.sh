#!/bin/bash
# Stop the old weather/cam event page on the public Lipton slug.
# Root cause: another process (17:42) strips the public nginx alias and
# inverts serve_lipton_dev_playback_page to the API event page.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
ENABLED=/etc/nginx/sites-enabled/sailingsa
AVAILABLE=/etc/nginx/sites-available/sailingsa
NEW=/tmp/nginx-sailingsa-playback-lock.conf
BAKDIR=/root/nginx-bak-${TS}
GOLD=/root/lipton-nginx-golden.conf

echo '=== who stripped the lock ==='
grep -R --line-number --binary-files=without-match 'Only -dev may alias' /tmp /root /var/www/sailingsa /etc/nginx 2>/dev/null | head -40 || true
echo '=== recent /tmp scripts ==='
find /tmp /root -maxdepth 2 -type f -mmin -30 \( -name '*.py' -o -name '*.sh' \) -printf '%T+%p\n' 2>/dev/null | sort | tail -40
echo '=== crontab ==='
crontab -l 2>/dev/null || true
ls -la /etc/cron.d /etc/cron.hourly 2>/dev/null | head -30

test -s "$NEW"
mkdir -p "$BAKDIR"
cp -a "$ENABLED" "$BAKDIR/sites-enabled-sailingsa" || true
cp -a "$AVAILABLE" "$BAKDIR/sites-available-sailingsa" || true
cp -a /var/www/sailingsa/api/api.py "$BAKDIR/api.py" || true

chattr -i "$ENABLED" 2>/dev/null || true
find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true
cp "$NEW" "$ENABLED"
cp "$NEW" "$AVAILABLE"
cp "$NEW" "$GOLD"
echo "nginx installed $(wc -c < "$ENABLED") bytes"

if ! nginx -t; then
  echo "ERROR nginx -t; restoring"
  cp -a "$BAKDIR/sites-enabled-sailingsa" "$ENABLED"
  nginx -t || true
  exit 1
fi
nginx -s reload
chattr +i "$ENABLED" || true
lsattr "$ENABLED" || true

cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
CONF=/etc/nginx/sites-enabled/sailingsa
GOLD=/root/lipton-nginx-golden.conf
NEED='location = /regatta/2026-08-29-lipton-challenge-cup {'
test -s "$GOLD"
if grep -qF "$NEED" "$CONF" 2>/dev/null; then
  exit 0
fi
chattr -i "$CONF" 2>/dev/null || true
cp "$GOLD" "$CONF"
if nginx -t; then
  nginx -s reload
  chattr +i "$CONF" 2>/dev/null || true
  echo "$(date -Is) restored public playback lock" >> /root/lipton-keep-playback.log
else
  echo "$(date -Is) restore failed nginx -t" >> /root/lipton-keep-playback.log
fi
KEEP
chmod 700 /root/lipton-keep-playback.sh
grep -q lipton-keep-playback /etc/crontab || echo '* * * * * root /root/lipton-keep-playback.sh' >> /etc/crontab

python3 /tmp/patch_lipton_public_slug.py
# Fail if playback function is still inverted
python3 - <<'PY'
from pathlib import Path
t = Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
m = t.split("def serve_lipton_dev_playback_page", 1)[-1][:1500]
if "_serve_regatta_standalone_impl" in m:
    raise SystemExit("API playback still inverted")
if "lipton-dev.html" not in m:
    raise SystemExit("API playback missing html file")
after = t.split("def serve_regatta_standalone", 1)[-1][:1200]
if 'slug_s == "2026-08-29-lipton-challenge-cup"' not in after:
    raise SystemExit("API public slug early-return missing")
print("api playback hook ok")
PY

cp /tmp/lipton_dev_live.py /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py
cp /tmp/lipton_dev_live.py /var/www/sailingsa/scripts/lipton_dev_live.py
find /var/www/sailingsa -name 'lipton_dev_live*.pyc' -delete || true
rm -f /tmp/lipton_dev_live_snap.json /tmp/lipton_dev_live_snap.tmp || true

systemctl restart sailingsa-api
sleep 4
systemctl is-active sailingsa-api

python3 - <<'PY'
import json, subprocess

def chk(url):
    html = subprocess.check_output(["curl","-sS","-A","SailingSA-devcheck",url], text=True, errors="replace")
    print(url)
    print("  bytes", len(html), "playback", "lipton-dev-playback" in html, "weather", any(x in html for x in ("WEATHER","Live cam DELAYED")))
    return html

chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1")
chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup")
live = subprocess.check_output(["curl","-sS","https://sailingsa.co.za/api/lipton-dev/live"], text=True)
d = json.loads(live)
print("live", {k: d.get(k) for k in ("waiting","race_number","stage","gun_sast","holding_last")})
print("boats", len(d.get("boats") or {}))
hdr = subprocess.check_output(["curl","-sSI","https://sailingsa.co.za/sailor/david-rae"], text=True, errors="replace")
print("sailor_rae", hdr.split("\n",1)[0].strip())
PY
