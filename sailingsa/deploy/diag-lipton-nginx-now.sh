#!/bin/bash
set -euo pipefail
echo '=== sites-enabled ==='
ls -la /etc/nginx/sites-enabled
echo '=== running T lipton ==='
nginx -T 2>/dev/null | grep -n 'lipton-challenge-cup' | head -40
echo '=== block ==='
nginx -T 2>/dev/null | awk '/location = \/regatta\/2026-08-29-lipton-challenge-cup \{/,/^    \}/' | head -25
echo '=== html file ==='
ls -la /var/www/sailingsa/lipton-dev.html | head
echo '=== local curl ==='
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o /tmp/loc.html -D /tmp/loc.hdr -w 'local %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup'
python3 - <<'PY'
t=open("/tmp/loc.html",encoding="utf-8",errors="replace").read()
print("playback", "lipton-dev-playback" in t, "weather", "WEATHER" in t, "bytes", len(t))
print(open("/tmp/loc.hdr",encoding="utf-8",errors="replace").read()[:600])
PY
echo '=== lsattr ==='
lsattr /etc/nginx/sites-enabled/sailingsa || true
