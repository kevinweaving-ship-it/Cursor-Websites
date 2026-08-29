#!/bin/bash
# Restore public playback AND keep keelboat column patch. Do not replace api.py.
set -euo pipefail
API=/var/www/sailingsa/api/api.py
ENABLED=/etc/nginx/sites-enabled/sailingsa
SNIP=/etc/nginx/snippets/lipton-public-proxy.conf

echo '=== kill watch ==='
bash /tmp/kill-lipton-public-watch-forever.sh || true

echo '=== nginx rewrite (not proxy) ==='
chattr -i "$ENABLED" "$SNIP" 2>/dev/null || true
python3 /tmp/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i "$ENABLED" "$SNIP" 2>/dev/null || true
grep -n 'rewrite\|proxy_pass' "$SNIP" | head

echo '=== API public=playback; keep keelboat ==='
chattr -i "$API" 2>/dev/null || true
python3 /tmp/patch_lipton_public_slug.py
if ! grep -q 'keelboat = bool(show_boat)' "$API"; then
  echo 'ERROR: keelboat patch lost'
  exit 1
fi
if grep -n LIPTON_PUBLIC_NOT_DEV "$API" | head; then
  echo 'WARN: LIPTON_PUBLIC_NOT_DEV still present somewhere'
fi
python3 -m py_compile "$API"
chattr +i "$API" 2>/dev/null || true
systemctl restart sailingsa-api
sleep 6
systemctl is-active sailingsa-api

# keep-playback cron (same as detach)
cp /tmp/patch_lipton_public_slug.py /root/patch_lipton_public_slug.py
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
pkill -f lipton_public_watch_guard 2>/dev/null || true
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
if grep -q LIPTON_PUBLIC_NOT_DEV /var/www/sailingsa/api/api.py 2>/dev/null; then
  chattr -i /var/www/sailingsa/api/api.py 2>/dev/null || true
  python3 /root/patch_lipton_public_slug.py && systemctl restart sailingsa-api || true
  chattr +i /var/www/sailingsa/api/api.py 2>/dev/null || true
fi
SNIP=/etc/nginx/snippets/lipton-public-proxy.conf
CONF=/etc/nginx/sites-enabled/sailingsa
need=0
if ! test -f "$SNIP" || grep -q proxy_pass "$SNIP" || ! grep -q 'alias /var/www/sailingsa/lipton-dev.html' "$SNIP"; then
  need=1
fi
if [ "$need" = 1 ]; then
  chattr -i "$CONF" "$SNIP" 2>/dev/null || true
  python3 /root/force_lipton_nginx_alias.py
  nginx -t && nginx -s reload
  chattr +i "$CONF" "$SNIP" 2>/dev/null || true
  echo "$(date -Is) restored public playback" >> /root/lipton-keep-playback.log
fi
KEEP
chmod 700 /root/lipton-keep-playback.sh /root/force_lipton_nginx_alias.py /root/patch_lipton_public_slug.py
grep -q lipton-keep-playback /etc/crontab || echo '* * * * * root /root/lipton-keep-playback.sh' >> /etc/crontab

echo '=== verify ==='
python3 - <<'PY'
import re, subprocess, time
time.sleep(1)

def get(url):
    return subprocess.check_output(
        ["curl","-sS","-A","SailingSA-devcheck","-H","Cache-Control: no-cache", url],
        text=True, errors="replace",
    )

pub = get("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup")
r7 = get("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?race=7")
old = get("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old")
sheet = get("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup/class-j22")
print("public", len(pub), "dev", 'data-lipton-dev="1"' in pub, "weather", "WEATHER" in pub)
print("r7", len(r7), "dev", 'data-lipton-dev="1"' in r7)
print("old", len(old), "weather", ("WEATHER" in old or "Live cam" in old))
ths = []
for m in re.finditer(r"<th\b[^>]*>(.*?)</th>", sheet, re.I | re.S):
    label = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    if label:
        ths.append(label)
print("ths", ths[:20])
if 'data-lipton-dev="1"' not in pub or "WEATHER" in pub:
    raise SystemExit("FAIL public")
if 'data-lipton-dev="1"' not in r7:
    raise SystemExit("FAIL ?race=7")
if "WEATHER" not in old and "Live cam" not in old:
    raise SystemExit("FAIL -old")
if ths[:5] != ["Rank", "Bow", "Boat Name", "Club", "Nett"]:
    raise SystemExit("FAIL columns " + str(ths[:12]))
if "R7" in ths and "R1" in ths and ths.index("R7") > ths.index("R1"):
    raise SystemExit("FAIL race order " + str(ths))
print("OK playback + keelboat columns")
PY
echo '=== wait 25s — confirm watchdog stays dead ==='
sleep 25
python3 - <<'PY'
import subprocess
from pathlib import Path
pub = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck","https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup"],
    text=True, errors="replace",
)
snip = Path("/etc/nginx/snippets/lipton-public-proxy.conf").read_text()
print("after25 public", len(pub), "dev", 'data-lipton-dev="1"' in pub)
print("after25 snippet_alias", "alias /var/www/sailingsa/lipton-dev.html" in snip, "proxy", "proxy_pass" in snip)
if 'data-lipton-dev="1"' not in pub or "proxy_pass" in snip:
    raise SystemExit("FAIL watchdog came back")
print("OK still playback after 25s")
PY
ps aux | grep -Ei 'lipton_public_watch_guard|lipton_public_not_dev|lw-gold' | grep -v grep || echo 'watch processes: none'
