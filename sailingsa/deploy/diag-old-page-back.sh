#!/bin/bash
set -euo pipefail
echo '=== public curl ==='
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck -o /tmp/p.html -D /tmp/p.hdr -w 'size %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
python3 - <<'PY'
t=open('/tmp/p.html',encoding='utf-8',errors='replace').read()
print('playback', 'data-lipton-dev="1"' in t, 'weather', 'WEATHER' in t or 'Live cam' in t, 'bytes', len(t))
print(open('/tmp/p.hdr',encoding='utf-8',errors='replace').read()[:400])
PY
echo '=== snippet ==='
lsattr /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
cat /etc/nginx/snippets/lipton-public-proxy.conf
echo '=== site locs ==='
grep -n 'lipton-challenge-cup' /etc/nginx/sites-enabled/sailingsa | head -40
echo '=== units ==='
systemctl is-active sailingsa-lipton-public-watch.service || true
systemctl is-active sailingsa-lipton-url-hold.service || true
systemctl is-enabled sailingsa-lipton-public-watch.service || true
systemctl is-enabled sailingsa-lipton-url-hold.service || true
echo '=== unit files ==='
lsattr /etc/systemd/system/sailingsa-lipton-public-watch.service /etc/systemd/system/sailingsa-lipton-url-hold.service 2>/dev/null || true
head -8 /etc/systemd/system/sailingsa-lipton-public-watch.service 2>/dev/null || true
echo '=== cron ==='
ls -la /etc/cron.d | grep -i lipton || true
cat /etc/cron.d/aa-lipton-url-hold 2>/dev/null || true
cat /etc/cron.d/zzz-lipton-public-live 2>/dev/null || true
cat /etc/cron.d/sailingsa-lipton-public-not-dev 2>/dev/null || true
echo '=== processes ==='
ps aux | grep -Ei 'lipton|lw-gold|lw-g|watch_guard|url-hold' | grep -v grep | head -30
echo '=== api playback fn ==='
python3 - <<'PY'
from pathlib import Path
t=Path('/var/www/sailingsa/api/api.py').read_text(encoding='utf-8', errors='replace')
print('lsattr wait')
i=t.find('def serve_lipton_dev_playback_page')
print(t[i:i+750])
print('--- standalone ---')
j=t.find('def serve_regatta_standalone')
print(t[j:j+700])
print('--- impl start ---')
k=t.find('def _serve_regatta_standalone_impl')
print(t[k:k+500])
print('Live cam count', t.count('Live cam'))
print('NOT_DEV count', t.count('LIPTON_PUBLIC_NOT_DEV'))
PY
lsattr /var/www/sailingsa/api/api.py
echo '=== keep-playback ==='
head -20 /root/lipton-keep-playback.sh
tail -5 /root/lipton-keep-playback.log 2>/dev/null || true
