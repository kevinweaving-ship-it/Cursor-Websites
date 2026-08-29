#!/bin/bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
tar -czf "/root/backup_lipton_r7_${TS}.tar.gz" \
  /var/www/sailingsa/lipton-dev.html \
  /var/www/sailingsa/js/lipton-dev-playback.js \
  /var/www/sailingsa/js/lipton-dev-races.json \
  /var/www/sailingsa/css/lipton-dev.css 2>/dev/null || true
ls -la "/root/backup_lipton_r7_${TS}.tar.gz" 2>/dev/null || echo "WARN: no backup tarball"
cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dt.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-ds.js
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-dq.js
cp /tmp/lipton-dev-races.json /var/www/sailingsa/js/lipton-dev-races.json
test -f /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
if test -s /tmp/kill-all-lipton-watches.sh; then
  bash /tmp/kill-all-lipton-watches.sh
fi
# packed R7 replay/trail after lock restore
cp /tmp/lipton-dev-playback.js /var/www/sailingsa/js/lipton-dev-playback-du.js
cp /tmp/lipton-dev-races.json /var/www/sailingsa/js/lipton-dev-races.json
test -s /tmp/lipton-dev-replay-r7.json && cp /tmp/lipton-dev-replay-r7.json /var/www/sailingsa/js/lipton-dev-replay-r7.json
test -s /tmp/lipton-dev-trail-r7.json && cp /tmp/lipton-dev-trail-r7.json /var/www/sailingsa/js/lipton-dev-trail-r7.json
curl -sS -A SailingSA-devcheck -o /tmp/p.html -w 'page %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?race=7'
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("du", "playback-du.js" in t)
print("weather", "WEATHER" in t)
PY
echo -n "races packed7 "
python3 -c "import json; d=json.load(open('/var/www/sailingsa/js/lipton-dev-races.json')); r=next(x for x in d['races'] if x['n']==7); print(r.get('packed'), 'held', r.get('held_live'))"
ls -l /var/www/sailingsa/js/lipton-dev-replay-r7.json /var/www/sailingsa/js/lipton-dev-trail-r7.json
