#!/bin/bash
# Backup the FastAPI weather/event page, then delete it from API + nginx.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
BK=/root/backup_lipton_old_page_${TS}
mkdir -p "$BK"

echo "=== backup live api.py ==="
chattr -i /var/www/sailingsa/api/api.py 2>/dev/null || true
cp -a /var/www/sailingsa/api/api.py "$BK/api.py"
ls -la "$BK/api.py"

echo "=== backup old weather HTML from FastAPI (before patch) ==="
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o "$BK/public-via-nginx.html" -D "$BK/public-via-nginx.hdr" \
  -w 'nginx-public %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup' || true
curl -sk -A SailingSA-devcheck \
  -o "$BK/fastapi-public.html" -D "$BK/fastapi-public.hdr" \
  -w 'fastapi-public %{http_code} %{size_download}\n' \
  'http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup' || true
curl -sk -A SailingSA-devcheck \
  -o "$BK/fastapi-old.html" -D "$BK/fastapi-old.hdr" \
  -w 'fastapi-old %{http_code} %{size_download}\n' \
  'http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup-old' || true
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o "$BK/nginx-old.html" -D "$BK/nginx-old.hdr" \
  -w 'nginx-old %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old' || true

# Keep a copy of any weather HTML we actually got
python3 - <<PY
from pathlib import Path
bk = Path("$BK")
for name in ("fastapi-public.html", "fastapi-old.html", "nginx-old.html", "public-via-nginx.html"):
    p = bk / name
    if not p.is_file():
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    weather = ("WEATHER" in t) or ("Live cam" in t) or ("regatta-live-board" in t)
    print(name, "bytes", len(t), "weather", weather, "playback", 'data-lipton-dev="1"' in t)
    if weather and len(t) > 50000:
        dest = bk / "OLD_WEATHER_PAGE.html"
        dest.write_text(t, encoding="utf-8")
        print("saved", dest)
PY

tar -czf "${BK}.tar.gz" -C /root "$(basename "$BK")"
ls -la "${BK}.tar.gz"

echo "=== patch API: no old weather page ==="
test -s /tmp/patch_lipton_public_slug.py
python3 /tmp/patch_lipton_public_slug.py
python3 -m py_compile /var/www/sailingsa/api/api.py
chattr +i /var/www/sailingsa/api/api.py 2>/dev/null || true

echo "=== copy playback sheet files ==="
test -s /tmp/lipton-dev.html && cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
test -s /tmp/lipton-dev.html && cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
test -s /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css
test -s /tmp/lipton-event-sheet.js && cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js

echo "=== restart API ==="
systemctl restart sailingsa-api
sleep 3
systemctl is-active sailingsa-api

echo "=== FastAPI after patch must be playback ==="
curl -sk -A SailingSA-devcheck -o /tmp/fa.html -w 'fastapi %{http_code} %{size_download}\n' \
  'http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup'
curl -sk -A SailingSA-devcheck -o /tmp/fa-old.html -w 'fastapi-old %{http_code} %{size_download}\n' \
  'http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup-old'
python3 - <<'PY'
for label, path in (("public", "/tmp/fa.html"), ("old", "/tmp/fa-old.html")):
    t = open(path, encoding="utf-8", errors="replace").read()
    weather = ("WEATHER" in t) or ("Live cam" in t)
    play = 'data-lipton-dev="1"' in t
    print(label, "bytes", len(t), "playback", play, "weather", weather)
    if weather or not play:
        raise SystemExit(f"FAIL FastAPI still serving old page on {label}")
print("API old page gone")
PY

echo "=== nginx alias lock ==="
bash /tmp/kill-lipton-public-watch-forever.sh || true
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf
sleep 3

echo "=== public URL ==="
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o /tmp/p.html -D /tmp/p.hdr -w 'pub %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup'
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o /tmp/o.html -w 'old %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old'
python3 - <<'PY'
t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
o = open("/tmp/o.html", encoding="utf-8", errors="replace").read()
hdr = open("/tmp/p.hdr", encoding="utf-8", errors="replace").read()
print("pub bytes", len(t), "playback", 'data-lipton-dev="1"' in t, "sheet", "lipton-event-sheet.js" in t, "v", "20260828ee" in t)
print("pub weather", "WEATHER" in t or "Live cam" in t)
print("nowrap inject", "white-space:nowrap!important" in open("/var/www/sailingsa/js/lipton-event-sheet.js", encoding="utf-8").read())
print("wrap inject gone", "white-space:normal!important" not in open("/var/www/sailingsa/js/lipton-event-sheet.js", encoding="utf-8").read())
print("old bytes", len(o), "playback", 'data-lipton-dev="1"' in o, "weather", "WEATHER" in o or "Live cam" in o)
print("X-Lipton-Page", "playback" in hdr.lower() or "X-Lipton-Page: playback" in hdr)
if 'data-lipton-dev="1"' not in t or "WEATHER" in t or "Live cam" in t:
    raise SystemExit("FAIL public not playback")
if "WEATHER" in o or "Live cam" in o:
    raise SystemExit("FAIL -old still weather")
print("OK")
PY
echo "backup tarball ${BK}.tar.gz"
