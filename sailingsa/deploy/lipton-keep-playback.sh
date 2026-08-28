#!/bin/bash
set -euo pipefail
CONF=/etc/nginx/sites-enabled/sailingsa
GOLD=/root/lipton-nginx-golden.conf
NEED='location = /regatta/2026-08-29-lipton-challenge-cup {'
# Never let the weather-page watch come back.
if test -e /etc/cron.d/sailingsa-lipton-public-not-dev; then
  mkdir -p /root/disabled-lipton-not-dev
  mv /etc/cron.d/sailingsa-lipton-public-not-dev /root/disabled-lipton-not-dev/ || rm -f /etc/cron.d/sailingsa-lipton-public-not-dev
  echo "$(date -Is) removed public-not-dev cron" >> /root/lipton-keep-playback.log
fi
pkill -f 'lipton_public_not_dev_watch.py' 2>/dev/null || true
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
