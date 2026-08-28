#!/bin/bash
set -euo pipefail
STUB=$'#!/usr/bin/python3\nraise SystemExit(0)\n'
DEAD=$'[Unit]\nDescription=disabled\n[Service]\nType=oneshot\nExecStart=/bin/true\n'
pkill -9 -f '/usr/bin/python3 /root/lw-g' 2>/dev/null || true
pkill -9 -f 'lw-g16.py' 2>/dev/null || true
pkill -9 -f 'START_FIX' 2>/dev/null || true
for f in /root/lw-g16.py /root/lw-g14c.py /root/lw-g14d.py /root/lw-g14e.py /root/lw-g14f.py \
  /root/lw-g14.py /root/lw-g13b.py /root/lw-gold13.py /root/lw-gold7.py /root/lw-gold6.py \
  /usr/local/lib/lipton_public_not_dev_watch.py /usr/local/sbin/lipton_public_not_dev_watch.py \
  /var/lib/sailingsa-lipton/watch.py /var/lib/sailingsa-lipton/watch.py.gold
do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB" > "$f"
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
done
for f in /root/lw-guard16.sh /root/lw-watch16.service /root/lw-hold16.service \
  /usr/local/lib/lipton_public_watch_guard.sh \
  /usr/local/lib/sailingsa-lipton-public-watch.service \
  /usr/local/lib/sailingsa-lipton-url-hold.service \
  /etc/systemd/system/sailingsa-lipton-public-watch.service \
  /etc/systemd/system/sailingsa-lipton-url-hold.service
do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  case "$f" in
    *.service) printf '%s' "$DEAD" > "$f" ;;
    *) printf '%s\n' '#!/bin/bash' 'exit 0' > "$f" ;;
  esac
  chattr +i "$f" 2>/dev/null || true
done
systemctl daemon-reload
systemctl stop sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
chattr -i /etc/nginx/snippets/lipton-public-proxy.conf /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t && nginx -s reload
chattr +i /etc/nginx/snippets/lipton-public-proxy.conf /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa
echo 'g16' $(wc -c < /root/lw-g16.py 2>/dev/null || echo missing)
echo 'g14c' $(wc -c < /root/lw-g14c.py 2>/dev/null || echo missing)
pgrep -af 'lw-g16.py|START_FIX' || echo 'no g16/START_FIX'
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck -o /tmp/p.html -w 'pub %{http_code} %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
python3 -c 't=open("/tmp/p.html",encoding="utf-8",errors="replace").read(); print("playback","data-lipton-dev" in t,"weather","WEATHER" in t or "Live cam" in t,"n",len(t))'
head -3 /etc/nginx/snippets/lipton-public-proxy.conf
crontab -l 2>/dev/null | head -20 || true
ls /root/lw-g16.py /root/lw-watch16.service /root/lw-guard16.sh 2>/dev/null || true
