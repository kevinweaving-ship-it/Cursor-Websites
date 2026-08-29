#!/bin/bash
# Point -dev ?live=gps at official R8 live GPS. Do not replace api.py.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_r8_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/js/lipton-dev-playback.js \
  /var/www/sailingsa/js/lipton-dev-playback-du.js \
  /var/www/sailingsa/js/lipton-dev-races.json \
  /var/www/sailingsa/js/lipton-dev-live-history.json 2>/dev/null || true
ls -la "/root/backup_lipton_r8_${TS}.tar.gz" 2>/dev/null || echo "WARN: no backup tarball"

cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
mkdir -p /var/www/sailingsa/frontend /var/www/sailingsa/js
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-races.json /var/www/sailingsa/js/lipton-dev-races.json
test -d /var/www/sailingsa/frontend/js && cp /tmp/lipton-dev-races.json /var/www/sailingsa/frontend/js/lipton-dev-races.json
test -d /var/www/sailingsa/frontend/js && cp /tmp/lipton-dev-playback.js /var/www/sailingsa/frontend/js/lipton-dev-playback.js

# Stale R7 history must not overwrite R8 after a refresh.
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/var/www/sailingsa/js/lipton-dev-live-history.json")
if p.is_file():
    try:
        d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        d = {}
    n = d.get("race_number")
    if n is None or int(n) < 8:
        p.unlink()
        print("dropped stale history race", n)
    else:
        print("history already", n)
else:
    print("no history file")
PY
rm -f /tmp/lipton_dev_live_snap.json /tmp/lipton_dev_live_snap.tmp /tmp/lipton_dev_live_state.json || true

echo "=== races last ==="
python3 -c "import json; d=json.load(open('/var/www/sailingsa/js/lipton-dev-races.json')); print([(r['n'], r.get('packed'), r.get('held_live'), r.get('stage')) for r in d['races']])"
echo "=== page ==="
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev?live=gps'
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("r8bust", "20260829r8" in t)
print("weather", "WEATHER" in t)
print("dev", 'data-lipton-dev="1"' in t)
PY
echo "=== live api ==="
curl -sS -A SailingSA-devcheck https://sailingsa.co.za/api/lipton-dev/live | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:d.get(k) for k in ("race_number","stage","waiting","holding_last","gun_sast")}); print("boats", len(d.get("boats") or {}))'
