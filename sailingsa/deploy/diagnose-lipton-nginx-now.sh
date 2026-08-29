#!/bin/bash
set -euo pipefail
echo '=== nginx -t ==='
nginx -t 2>&1 || true
echo '=== enabled/available sizes ==='
wc -l -c /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa 2>/dev/null || true
echo '=== ls enabled ==='
ls -la /etc/nginx/sites-enabled/ /etc/nginx/sites-available/
echo '=== file types ==='
file /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa
echo '=== enabled server/location lines ==='
grep -nE 'server |location |listen |lipton' /etc/nginx/sites-enabled/sailingsa | head -100
echo '=== available server/location lines ==='
grep -nE 'server |location |listen |lipton' /etc/nginx/sites-available/sailingsa | head -100
echo '=== api/nginx active ==='
systemctl is-active sailingsa-api nginx || true
echo '=== public curl ==='
curl -sS -A SailingSA-devcheck -o /tmp/lipton-public.html -w 'http=%{http_code} bytes=%{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?live=1' || true
python3 - <<'PY'
t = open("/tmp/lipton-public.html", encoding="utf-8", errors="replace").read()
print("playback", "lipton-dev-playback" in t)
print("dnjs", "lipton-dev-playback-dn.js" in t)
print("old_weather", any(x in t for x in ("WEATHER", "Live cam", "DELAYED")))
i = t.find("<title>")
j = t.find("</title>")
print("title", t[i:j+8] if i >= 0 else t[:180])
PY
