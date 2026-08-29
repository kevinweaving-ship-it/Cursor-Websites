#!/bin/bash
set -euo pipefail
echo '=== PROXY_V1 files ==='
grep -l 'LIPTON_NGINX_PUBLIC_PROXY_V1' /root/* /usr/local/sbin/* /usr/local/lib/* /tmp/* /etc/cron.d/* /var/www/sailingsa/deploy/* /var/lib/sailingsa-lipton/* 2>/dev/null || true
echo '=== crontab ==='
cat /etc/crontab
echo '=== cron.d ==='
ls -la /etc/cron.d
echo '=== systemd timers ==='
systemctl list-timers --all | grep -i lipton || true
systemctl list-units --all | grep -i lipton || true
echo '=== processes ==='
ps aux | grep -E 'lipton|lw-gold|lw-guard|nginx|watch' | grep -v grep | head -40
echo '=== route grep ==='
python3 - <<'PY'
from pathlib import Path
t=Path('/var/www/sailingsa/api/api.py').read_text(encoding='utf-8', errors='replace')
for s in ['/regatta/{slug}','serve_regatta_standalone','LIPTON_PUBLIC_NOT_DEV','LIPTON_NGINX','weather HTML','Live cam']:
    print(s, t.count(s))
# show route defs around regatta slug
import re
for m in re.finditer(r'@app\.(get|api_route)\([^\n]*regatta[^\n]*\n(?:.*\n){0,6}', t):
    s=m.group(0)
    if 'slug' in s and 'class' not in s:
        print('---')
        print(s[:400])
PY
echo '=== lsattr ==='
lsattr /etc/nginx/snippets/lipton-public-proxy.conf /etc/nginx/sites-enabled/sailingsa /var/www/sailingsa/api/api.py 2>/dev/null || true
echo '=== playback fn now ==='
python3 - <<'PY'
from pathlib import Path
t=Path('/var/www/sailingsa/api/api.py').read_text(encoding='utf-8', errors='replace')
i=t.find('def serve_lipton_dev_playback_page')
print(t[i:i+700])
print('--- standalone ---')
j=t.find('def serve_regatta_standalone')
print(t[j:j+600])
PY
