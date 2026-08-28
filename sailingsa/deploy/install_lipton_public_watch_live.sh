#!/bin/bash
set -euo pipefail
chattr -i /usr/local/sbin/lipton_public_not_dev_watch.py \
  /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py \
  /etc/systemd/system/sailingsa-lipton-public-watch.service \
  /etc/nginx/sites-enabled/sailingsa 2>/dev/null || true
cp /tmp/lipton_public_not_dev_watch.py /usr/local/sbin/lipton_public_not_dev_watch.py
chmod 755 /usr/local/sbin/lipton_public_not_dev_watch.py
cp /tmp/lipton_apply_nginx_public_proxy_once.py /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py
chmod 755 /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py
cp /tmp/sailingsa-lipton-public-watch.service /etc/systemd/system/sailingsa-lipton-public-watch.service
mkdir -p /etc/systemd/system/nginx.service.d
cp /tmp/nginx-lipton-public-proxy.service.d.conf /etc/systemd/system/nginx.service.d/lipton-public-proxy.conf
cp /tmp/cron.d-sailingsa-lipton-public-not-dev /etc/cron.d/sailingsa-lipton-public-not-dev
chmod 644 /etc/cron.d/sailingsa-lipton-public-not-dev
printf '%s\n' '* * * * * root /usr/bin/python3 /usr/local/sbin/lipton_public_not_dev_watch.py >/dev/null 2>&1' > /etc/cron.d/zzz-lipton-public-live
chmod 644 /etc/cron.d/zzz-lipton-public-live
systemctl unmask sailingsa-lipton-public-watch.service 2>/dev/null || true
systemctl daemon-reload
python3 /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py
systemctl enable --now sailingsa-lipton-public-watch.service
systemctl restart sailingsa-lipton-public-watch.service
chattr +i /usr/local/sbin/lipton_public_not_dev_watch.py \
  /etc/systemd/system/sailingsa-lipton-public-watch.service \
  /etc/nginx/sites-enabled/sailingsa \
  /etc/systemd/system/nginx.service.d/lipton-public-proxy.conf
echo "SVC $(systemctl is-active sailingsa-lipton-public-watch.service)"
echo "CRON $(ls /etc/cron.d | tr '\n' ' ')"
lsattr /etc/nginx/sites-enabled/sailingsa /usr/local/sbin/lipton_public_not_dev_watch.py
