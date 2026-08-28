#!/bin/bash
set -euo pipefail
echo '=== enabled mtime ==='
ls -la /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa
echo '=== sites-enabled ==='
ls -la /etc/nginx/sites-enabled/
echo '=== lipton locs ==='
grep -n 'lipton\|2026-08-29-lipton\|sailor' /etc/nginx/sites-enabled/sailingsa | head -40
echo '=== nginx -T lipton/sailor ==='
nginx -T 2>/dev/null | grep -n '2026-08-29-lipton\|location ~ \^/sailor\|alias /var/www/sailingsa/lipton-dev' | head -40
echo '=== 00-timadvisor ==='
head -40 /etc/nginx/sites-enabled/00-timadvisor
echo '=== curls ==='
for u in \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1' \
  'https://www.sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup/'
 do
  curl -sS -o /tmp/chk.html -w "$u -> %{http_code} %{size_download}\n" -L --max-redirs 2 "$u" || true
  python3 -c 't=open("/tmp/chk.html",encoding="utf-8",errors="replace").read(); print(" playback", "lipton-dev-playback" in t, " weather", any(x in t for x in ("WEATHER","Live cam DELAYED","Live cam")))'
 done
echo '=== api slug hook ==='
grep -n 'LIPTON_PUBLIC_SLUG\|serve_lipton_dev_playback\|2026-08-29-lipton-challenge-cup' /var/www/sailingsa/api/api.py | head -30
echo '=== live.py holding ==='
grep -c holding_last /var/www/sailingsa/scripts/lipton_dev_live.py /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py || true
echo '=== live api ==='
curl -sS -o /tmp/live.json -w 'live %{http_code} %{size_download}\n' https://sailingsa.co.za/api/lipton-dev/live || true
python3 - <<'PY'
import json
t=open("/tmp/live.json",encoding="utf-8",errors="replace").read()
try:
    d=json.loads(t)
    print({k:d.get(k) for k in ("waiting","race_number","stage","gun_sast","holding_last")})
    print("boats", len(d.get("boats") or {}))
except Exception as e:
    print("live err", e, t[:200])
PY
