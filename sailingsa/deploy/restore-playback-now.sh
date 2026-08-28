#!/bin/bash
set -euo pipefail
# Kill the weather-page watch again, restore playback lock, keep rank-freeze files.
mkdir -p /root/disabled-lipton-not-dev
for f in \
  /etc/cron.d/sailingsa-lipton-public-not-dev \
  /var/www/sailingsa/deploy/lipton_public_not_dev_watch.py \
  /tmp/lipton_public_not_dev_watch.py \
  /tmp/lipton_install_watch.sh \
  /tmp/lipton_reinstall_watch.sh \
  /tmp/patch_lipton_nginx_public_not_dev_v2.py
 do
  if test -e "$f"; then
    mv "$f" /root/disabled-lipton-not-dev/ || true
    echo "moved $f"
  fi
 done
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
chattr -i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true
cat > /usr/local/sbin/lipton_public_not_dev_watch.py <<'PY'
#!/usr/bin/python3
raise SystemExit(0)
PY
chmod 755 /usr/local/sbin/lipton_public_not_dev_watch.py
chattr +i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true

GOLD=/root/lipton-nginx-golden.conf
NEW=/tmp/nginx-sailingsa-playback-lock.conf
if test -s "$NEW"; then GOLD_SRC="$NEW"; elif test -s "$GOLD"; then GOLD_SRC="$GOLD"; else echo "no gold nginx"; exit 1; fi
chattr -i /etc/nginx/sites-enabled/sailingsa 2>/dev/null || true
cp "$GOLD_SRC" /etc/nginx/sites-enabled/sailingsa
cp "$GOLD_SRC" /etc/nginx/sites-available/sailingsa
cp "$GOLD_SRC" "$GOLD"
if ! grep -q 'location = /regatta/2026-08-29-lipton-challenge-cup {' /etc/nginx/sites-enabled/sailingsa; then
  echo "ERROR public lock missing after copy"; exit 1
fi
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa
lsattr /etc/nginx/sites-enabled/sailingsa

# playback files
test -s /tmp/lipton-dev.html && cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
test -s /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
if test -s /tmp/lipton-dev-playback.js; then
  cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
  cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dq.js
fi

curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
python3 - <<'PY'
t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("dq", "lipton-dev-playback-dq.js" in t)
print("weather", "WEATHER" in t or "Live cam" in t)
print("bytes", len(t))
PY
ls /etc/cron.d | grep -i lipton || true
