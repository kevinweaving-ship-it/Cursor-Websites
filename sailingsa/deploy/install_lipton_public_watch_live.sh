#!/bin/bash
set -euo pipefail
chattr -i /usr/local/sbin/lipton_public_not_dev_watch.py \
  /usr/local/lib/lipton_public_not_dev_watch.py \
  /var/lib/sailingsa-lipton/watch.py \
  /usr/local/lib/lipton_public_watch_guard.sh \
  /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py \
  /etc/systemd/system/sailingsa-lipton-public-watch.service \
  /etc/systemd/system/sailingsa-lipton-url-hold.service \
  /etc/systemd/system/nginx.service.d/lipton-public-proxy.conf \
  /etc/nginx/sites-enabled/sailingsa 2>/dev/null || true
mkdir -p /usr/local/lib /var/lib/sailingsa-lipton
cp /tmp/lipton_public_not_dev_watch.py /usr/local/sbin/lipton_public_not_dev_watch.py
cp /tmp/lipton_public_not_dev_watch.py /usr/local/lib/lipton_public_not_dev_watch.py
cp /tmp/lipton_public_not_dev_watch.py /var/lib/sailingsa-lipton/watch.py
cp /tmp/lipton_public_not_dev_watch.py /var/lib/sailingsa-lipton/watch.py.gold
cp /tmp/lipton_public_not_dev_watch.py /root/lipton_public_not_dev_watch.py
cp /tmp/lipton_public_not_dev_watch.py /root/lw-gold7.py
cp /tmp/lipton_public_not_dev_watch.py /root/lw-gold6.py
cp /tmp/lipton_public_not_dev_watch.py /root/lw-gold5.py
chmod 755 /usr/local/sbin/lipton_public_not_dev_watch.py \
  /usr/local/lib/lipton_public_not_dev_watch.py \
  /var/lib/sailingsa-lipton/watch.py
cp /tmp/lipton_public_watch_guard.sh /usr/local/lib/lipton_public_watch_guard.sh
chmod 755 /usr/local/lib/lipton_public_watch_guard.sh
cp /tmp/lipton_apply_nginx_public_proxy_once.py /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py
chmod 755 /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py
cp /tmp/sailingsa-lipton-public-watch.service /etc/systemd/system/sailingsa-lipton-public-watch.service
cp /tmp/sailingsa-lipton-public-watch.service /usr/local/lib/sailingsa-lipton-public-watch.service
cp /tmp/sailingsa-lipton-url-hold.service /etc/systemd/system/sailingsa-lipton-url-hold.service
cp /tmp/sailingsa-lipton-url-hold.service /usr/local/lib/sailingsa-lipton-url-hold.service
mkdir -p /etc/systemd/system/nginx.service.d
cp /tmp/nginx-lipton-public-proxy.service.d.conf /etc/systemd/system/nginx.service.d/lipton-public-proxy.conf
cp /tmp/cron.d-sailingsa-lipton-public-not-dev /etc/cron.d/sailingsa-lipton-public-not-dev
chmod 644 /etc/cron.d/sailingsa-lipton-public-not-dev
printf '%s\n' '* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1' > /etc/cron.d/zzz-lipton-public-live
chmod 644 /etc/cron.d/zzz-lipton-public-live
systemctl unmask sailingsa-lipton-public-watch.service 2>/dev/null || true
systemctl unmask sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl daemon-reload
python3 /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py || true
/usr/bin/python3 /usr/local/lib/lipton_public_not_dev_watch.py
systemctl enable --now sailingsa-lipton-public-watch.service
systemctl enable --now sailingsa-lipton-url-hold.service
chattr +i /usr/local/sbin/lipton_public_not_dev_watch.py \
  /usr/local/lib/lipton_public_not_dev_watch.py \
  /var/lib/sailingsa-lipton/watch.py \
  /usr/local/lib/lipton_public_watch_guard.sh \
  /etc/systemd/system/sailingsa-lipton-public-watch.service \
  /etc/systemd/system/sailingsa-lipton-url-hold.service \
  /usr/local/lib/sailingsa-lipton-public-watch.service \
  /usr/local/lib/sailingsa-lipton-url-hold.service \
  /etc/nginx/sites-enabled/sailingsa \
  /etc/nginx/snippets/lipton-public-proxy.conf \
  /etc/systemd/system/nginx.service.d/lipton-public-proxy.conf
echo "SVC $(systemctl is-active sailingsa-lipton-public-watch.service)"
echo "HOLD $(systemctl is-active sailingsa-lipton-url-hold.service)"
echo "CRON $(ls /etc/cron.d | tr '\n' ' ')"
lsattr /etc/nginx/sites-enabled/sailingsa /usr/local/lib/lipton_public_not_dev_watch.py
