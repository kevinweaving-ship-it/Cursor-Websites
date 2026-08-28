#!/bin/bash
set -euo pipefail
echo '=== snippet ==='
cat /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null | head -25
echo '=== api hook ==='
python3 - <<'PY'
from pathlib import Path
t = Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8", errors="replace")
i = t.find("def serve_regatta_standalone")
print(t[i:i+1200])
print("--- playback fn ---")
j = t.find("def serve_lipton_dev_playback_page")
print(t[j:j+700])
PY
echo '=== restorers ==='
grep -R --line-number --binary-files=without-match 'LIPTON_NGINX_PUBLIC_PROXY' /tmp /root /usr/local/sbin /var/www/sailingsa/deploy /etc 2>/dev/null | head -40 || true
echo '=== ps ==='
ps aux | grep -Ei 'lipton|public_proxy|public_not|keep-playback' | grep -v grep || true
echo '=== cron ==='
grep -i lipton /etc/crontab || true
ls /etc/cron.d
echo '=== lsattr ==='
lsattr /etc/nginx/snippets/lipton-public-proxy.conf /etc/nginx/sites-enabled/sailingsa 2>/dev/null || true
