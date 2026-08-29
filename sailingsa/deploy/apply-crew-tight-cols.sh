#!/bin/bash
set -euo pipefail
API=/var/www/sailingsa/api/api.py
BAK="/root/api.py.bak_crew_tight_$(date +%Y%m%d_%H%M%S)"
cp -a "$API" "$BAK"
echo "backup $BAK"
chattr -i "$API" 2>/dev/null || true
python3 /tmp/patch_crew_tight_cols.py
if ! python3 -m py_compile "$API"; then
  echo "ERROR: api.py compile failed — restoring $BAK"
  cp -a "$BAK" "$API"
  chattr +i "$API" 2>/dev/null || true
  exit 1
fi
chattr +i "$API" 2>/dev/null || true
systemctl restart sailingsa-api
sleep 5
systemctl is-active sailingsa-api

if [ -f /tmp/force_lipton_nginx_alias.py ]; then
  chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
  python3 /tmp/force_lipton_nginx_alias.py || true
  nginx -t && nginx -s reload || true
  chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
elif [ -f /root/force_lipton_nginx_alias.py ]; then
  chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
  python3 /root/force_lipton_nginx_alias.py || true
  nginx -t && nginx -s reload || true
  chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
fi

python3 - <<'PY'
import re, subprocess
html = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck",
     "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup/class-j22"],
    text=True, errors="replace",
)
need = ["Trevor Spilhaus", "Thomas Henshilwood", "Scarlet Celliers", "Matthew Trautman"]
for n in need:
    print(("OK" if n in html else "MISS"), n)
if "Trevor Spilhaus" not in html:
    raise SystemExit("FAIL crew2 not in class-j22")
if "Scarlet Celliers" not in html:
    raise SystemExit("FAIL crew3 not in class-j22")
pub = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck",
     "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup"],
    text=True, errors="replace",
)
print("public_len", len(pub), "playback", 'data-lipton-dev="1"' in pub, "weather", "WEATHER" in pub)
if 'data-lipton-dev="1"' not in pub or "WEATHER" in pub or len(pub) > 50000:
    raise SystemExit("FAIL public URL not playback")
print("OK crew2/3 + public still playback")
PY
