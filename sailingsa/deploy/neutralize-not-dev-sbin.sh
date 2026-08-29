#!/bin/bash
set -euo pipefail
echo '=== sbin watch ==='
ls -la /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || echo 'no sbin watch'
echo '=== history ==='
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/var/www/sailingsa/js/lipton-dev-live-history.json")
if not p.is_file():
    print("no history file"); raise SystemExit
d=json.loads(p.read_text())
print("hist", {k:d.get(k) for k in ("waiting","race_number","stage","gun_sast","holding_last")})
print("hist_boats", len(d.get("boats") or {}))
PY
mkdir -p /root/disabled-lipton-not-dev
if test -e /usr/local/sbin/lipton_public_not_dev_watch.py; then
  mv /usr/local/sbin/lipton_public_not_dev_watch.py /root/disabled-lipton-not-dev/lipton_public_not_dev_watch.py.sbin
fi
# no-op stub so a reinstalled cron cannot strip the lock
cat > /usr/local/sbin/lipton_public_not_dev_watch.py <<'PY'
#!/usr/bin/python3
"""Disabled: this watch restored the old Lipton weather/cam event page on the public slug."""
raise SystemExit(0)
PY
chmod 755 /usr/local/sbin/lipton_public_not_dev_watch.py
chattr +i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true
test ! -e /etc/cron.d/sailingsa-lipton-public-not-dev && echo 'cron.d watch gone'
lsattr /etc/nginx/sites-enabled/sailingsa
curl -sS -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1
python3 -c 't=open("/tmp/p.html",encoding="utf-8",errors="replace").read(); print("playback", "lipton-dev-playback" in t, "weather", "WEATHER" in t)'
curl -sS https://sailingsa.co.za/api/lipton-dev/live | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:d.get(k) for k in ("waiting","race_number","holding_last","gun_sast")}); print("boats", len(d.get("boats") or {}))'
