#!/bin/bash
# Finish lock after family wipe. Do not grep this file for watch markers.
set -euo pipefail
STUB=$'#!/usr/bin/python3\nraise SystemExit(0)\n'
for f in /root/lw-g14c.py /root/lw-g14d.py /root/lw-g14e.py /root/lw-g14f.py /root/lw-g14.py /root/lw-g13b.py \
  /root/lw-gold6.py /root/lw-gold7.py /root/lw-gold13.py \
  /usr/local/lib/lipton_public_not_dev_watch.py /usr/local/sbin/lipton_public_not_dev_watch.py \
  /var/lib/sailingsa-lipton/watch.py /var/lib/sailingsa-lipton/watch.py.gold
do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB" > "$f"
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
done
pkill -9 -f '/usr/bin/python3 /root/lw-g' 2>/dev/null || true
pkill -9 -f 'lw-g14c.py' 2>/dev/null || true

DEAD=$'[Unit]\nDescription=disabled\n[Service]\nType=oneshot\nExecStart=/bin/true\n'
for u in /etc/systemd/system/sailingsa-lipton-public-watch.service \
         /etc/systemd/system/sailingsa-lipton-url-hold.service \
         /usr/local/lib/sailingsa-lipton-public-watch.service \
         /usr/local/lib/sailingsa-lipton-url-hold.service
do
  chattr -i "$u" 2>/dev/null || true
  printf '%s' "$DEAD" > "$u"
  chattr +i "$u" 2>/dev/null || true
done
systemctl daemon-reload
systemctl stop sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true

chattr -i /var/www/sailingsa/api/api.py 2>/dev/null || true
python3 /tmp/patch_lipton_public_slug.py
python3 -m py_compile /var/www/sailingsa/api/api.py
chattr +i /var/www/sailingsa/api/api.py

cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf

cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js
cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css

systemctl restart sailingsa-api
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  ss -ltn | grep -q ':8000' && break
  sleep 1
done
sleep 3
echo SNIP; cat /etc/nginx/snippets/lipton-public-proxy.conf
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck -o /tmp/p.html -D /tmp/p.hdr -w 'pub %{http_code} %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
python3 -c 't=open("/tmp/p.html",encoding="utf-8",errors="replace").read(); print("playback", "data-lipton-dev" in t, "weather", "WEATHER" in t or "Live cam" in t, "n", len(t))'
sleep 12
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck -o /tmp/p2.html -w 'pub2 %{http_code} %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
python3 -c 't=open("/tmp/p2.html",encoding="utf-8",errors="replace").read(); print("playback2", "data-lipton-dev" in t, "weather", "WEATHER" in t or "Live cam" in t, "n", len(t));
import pathlib; p=pathlib.Path("/root/lw-g14c.py"); print("g14c bytes", p.stat().st_size if p.exists() else "gone")'
pgrep -af 'lw-g14c.py' || echo 'no g14c proc'
