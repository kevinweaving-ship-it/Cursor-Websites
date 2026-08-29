#!/bin/bash
# Finish: strip public=True hijack, lock nginx to playback, verify.
set -euo pipefail

echo '=== hijack files (narrow) ==='
grep -l 'LIPTON_PUBLIC_NOT_DEV' \
  /root/*.py /root/*.sh /usr/local/sbin/* /usr/local/lib/* /tmp/*.py /tmp/*.sh \
  /etc/cron.d/* /var/www/sailingsa/deploy/*.py /var/www/sailingsa/deploy/*.sh \
  2>/dev/null || true
echo '=== processes ==='
ps aux | grep -E 'lipton|lw-gold|not_dev|public_not' | grep -v grep || true
echo '=== lsattr api ==='
lsattr /var/www/sailingsa/api/api.py || true

echo '=== stub gold/watch ==='
bash /tmp/kill-lipton-public-watch-forever.sh || true

echo '=== re-patch API ==='
chattr -i /var/www/sailingsa/api/api.py 2>/dev/null || true
python3 /tmp/patch_lipton_public_slug.py
python3 - <<'PY'
from pathlib import Path
t = Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
pb = t.split("def serve_lipton_dev_playback_page", 1)[-1][:800]
print(pb)
if "_serve_regatta_standalone_impl" in pb:
    raise SystemExit("FAIL playback fn still hijacked")
if "LIPTON_PUBLIC_NOT_DEV" in pb:
    raise SystemExit("FAIL playback fn still NOT_DEV")
print("playback fn clean")
PY
python3 -m py_compile /var/www/sailingsa/api/api.py
chattr +i /var/www/sailingsa/api/api.py
lsattr /var/www/sailingsa/api/api.py

echo '=== copy sheet ==='
test -s /tmp/lipton-dev.html && cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
test -s /tmp/lipton-event-sheet.js && cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js
test -s /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css

echo '=== nginx ==='
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf

echo '=== restart API ==='
systemctl restart sailingsa-api
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS -m 2 -o /dev/null -w '%{http_code}' -H 'Host: sailingsa.co.za' \
      http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
sleep 2
systemctl is-active sailingsa-api

echo '=== FastAPI with Host ==='
curl -sS -m 15 -H 'Host: sailingsa.co.za' -A SailingSA-devcheck \
  -o /tmp/fa.html -w 'fastapi %{http_code} %{size_download}\n' \
  'http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup'
curl -sS -m 15 -H 'Host: sailingsa.co.za' -A SailingSA-devcheck \
  -o /tmp/fa-old.html -w 'fastapi-old %{http_code} %{size_download}\n' \
  'http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup-old'

sleep 3
echo '=== nginx public ==='
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o /tmp/p.html -D /tmp/p.hdr -w 'pub %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup'
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
  -o /tmp/o.html -w 'old %{http_code} %{size_download}\n' \
  'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old'

python3 - <<'PY'
from pathlib import Path
def chk(label, path):
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    weather = ("WEATHER" in t) or ("Live cam" in t)
    play = 'data-lipton-dev="1"' in t
    print(label, "bytes", len(t), "playback", play, "weather", weather)
    return play, weather, len(t)

fa_p, fa_w, fa_n = chk("fastapi", "/tmp/fa.html")
fo_p, fo_w, fo_n = chk("fastapi-old", "/tmp/fa-old.html")
p_p, p_w, p_n = chk("nginx-pub", "/tmp/p.html")
o_p, o_w, o_n = chk("nginx-old", "/tmp/o.html")
js = Path("/var/www/sailingsa/js/lipton-event-sheet.js").read_text(encoding="utf-8")
print("crew wrap gone", "white-space:normal!important" not in js)
print("crew nowrap", "white-space:nowrap!important" in js)
print("hdr", "X-Lipton-Page: playback" in Path("/tmp/p.hdr").read_text(encoding="utf-8", errors="replace"))
snip = Path("/etc/nginx/snippets/lipton-public-proxy.conf").read_text()
print("snip proxy", "proxy_pass" in snip, "snip alias", "alias /var/www/sailingsa/lipton-dev.html" in snip)
if fa_w or fo_w:
    raise SystemExit("FAIL FastAPI still weather")
if not fa_p or not fo_p:
    raise SystemExit("FAIL FastAPI not playback")
if p_w or not p_p or p_n > 20000:
    raise SystemExit("FAIL nginx public not playback")
if o_w:
    raise SystemExit("FAIL nginx -old still weather")
print("OK")
PY
echo '=== snippet ==='
cat /etc/nginx/snippets/lipton-public-proxy.conf
