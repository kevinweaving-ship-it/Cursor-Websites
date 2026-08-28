#!/bin/bash
set -euo pipefail
mkdir -p /root/disabled-lipton-not-dev
echo '=== cron.d lipton ==='
ls -la /etc/cron.d | grep -i lipton || true
echo '=== kill watches ==='
# Any cron that restores the old event page
find /etc/cron.d -type f \( -iname '*lipton*public*' -o -iname '*zzz-lipton*' -o -iname '*not-dev*' \) -print \
  | grep -v sailingsa-lipton-schedule || true
for f in /etc/cron.d/*; do
  base=$(basename "$f")
  case "$base" in
    sailingsa-lipton-schedule) continue ;;
    *lipton*) mv "$f" /root/disabled-lipton-not-dev/ && echo "moved cron $base" ;;
  esac
done
pkill -f lipton_public_not_dev 2>/dev/null || true
pkill -f patch_lipton_nginx_public 2>/dev/null || true
pkill -f lipton_install_watch 2>/dev/null || true
find /tmp /usr/local/sbin /var/www/sailingsa/deploy -maxdepth 1 -type f \( \
  -name '*public_not_dev*' -o -name '*nginx_public_not_dev*' -o -name '*lipton_install_watch*' \
  \) -exec mv {} /root/disabled-lipton-not-dev/ \; 2>/dev/null || true

chattr -i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true
printf '%s\n' '#!/usr/bin/python3' 'raise SystemExit(0)' > /usr/local/sbin/lipton_public_not_dev_watch.py
chmod 755 /usr/local/sbin/lipton_public_not_dev_watch.py
chattr +i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true

GOLD_SRC=/tmp/nginx-sailingsa-playback-lock.conf
test -s "$GOLD_SRC"
chattr -i /etc/nginx/sites-enabled/sailingsa 2>/dev/null || true
cp "$GOLD_SRC" /etc/nginx/sites-enabled/sailingsa
cp "$GOLD_SRC" /etc/nginx/sites-available/sailingsa
cp "$GOLD_SRC" /root/lipton-nginx-golden.conf
grep -n 'location = /regatta/2026-08-29-lipton-challenge-cup' /etc/nginx/sites-enabled/sailingsa
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa
lsattr /etc/nginx/sites-enabled/sailingsa

cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dq.js

# keep-playback also deletes renamed crons
cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
mkdir -p /root/disabled-lipton-not-dev
for f in /etc/cron.d/*; do
  base=$(basename "$f")
  case "$base" in
    sailingsa-lipton-schedule) continue ;;
    *lipton*) mv "$f" /root/disabled-lipton-not-dev/ 2>/dev/null || rm -f "$f" ;;
  esac
done
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
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
fi
KEEP
chmod 700 /root/lipton-keep-playback.sh
grep -q lipton-keep-playback /etc/crontab || echo '* * * * * root /root/lipton-keep-playback.sh' >> /etc/crontab

sleep 1
echo '=== verify ==='
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1'
python3 - <<'PY'
t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("dr", "20260828dr" in t)
print("dq", "playback-dq.js" in t)
print("weather", "WEATHER" in t or "Live cam" in t)
print("bytes", len(t))
PY
echo '=== remaining cron ==='
ls /etc/cron.d
echo '=== nginx public loc ==='
grep -n '2026-08-29-lipton-challenge-cup' /etc/nginx/sites-enabled/sailingsa | head
