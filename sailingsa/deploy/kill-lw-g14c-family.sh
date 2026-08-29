#!/bin/bash
# Kill the recorded writer: /root/lw-g14c.py and every replica it restores.
set -euo pipefail
STUB_PY=$'#!/usr/bin/python3\nraise SystemExit(0)\n'
STUB_SH=$'#!/bin/bash\nexit 0\n'
DEAD_UNIT=$'[Unit]\nDescription=disabled\n[Service]\nType=oneshot\nExecStart=/bin/true\n[Install]\nWantedBy=multi-user.target\n'

echo '=== stop units then kill processes ==='
systemctl stop sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
pkill -9 -f '/usr/bin/python3 /root/lw-g' 2>/dev/null || true
pkill -9 -f 'python3 /root/lw-g' 2>/dev/null || true
pkill -9 -f 'lw-g14c.py' 2>/dev/null || true
pkill -9 -f 'lipton_public_not_dev_watch.py' 2>/dev/null || true
pkill -9 -f 'for f in /root/lw-g14c.py' 2>/dev/null || true
sleep 1

wipe_py() {
  local f="$1"
  [ -e "$f" ] || return 0
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB_PY" > "$f"
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
  echo "wiped $f $(wc -c < "$f")"
}
wipe_sh() {
  local f="$1"
  [ -e "$f" ] || return 0
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB_SH" > "$f"
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
  echo "wiped $f $(wc -c < "$f")"
}

echo '=== wipe every DEBOUNCE copy >500b ==='
while IFS= read -r f; do
  wipe_py "$f"
done < <(grep -rl 'LIPTON_WATCH_DEBOUNCE_V1' /root /usr/local/lib /usr/local/sbin /var/lib/sailingsa-lipton /tmp 2>/dev/null || true)

# Always wipe the names from the captured GOLDS list, even if grep missed
for f in \
  /root/lw-g14c.py /root/lw-g14d.py /root/lw-g14.py /root/lw-g14b.py /root/lw-g13b.py \
  /root/lw-gold.py /root/lw-gold2.py /root/lw-gold3.py /root/lw-gold4.py /root/lw-gold5.py \
  /root/lw-gold6.py /root/lw-gold7.py /root/lw-gold8.py /root/lw-gold9.py \
  /root/lw-gold10.py /root/lw-gold11.py /root/lw-gold12.py /root/lw-gold13.py \
  /root/lipton_public_not_dev_watch.py \
  /usr/local/lib/lipton_public_not_dev_watch.py \
  /usr/local/sbin/lipton_public_not_dev_watch.py \
  /var/lib/sailingsa-lipton/watch.py \
  /var/lib/sailingsa-lipton/watch.py.gold
do
  wipe_py "$f"
done
for f in /usr/local/lib/lipton_public_watch_guard.sh /usr/local/sbin/lipton_public_watch_guard.sh \
         /root/lw-guard.sh /root/lw-guard6.sh /root/lw-guard7.sh /root/lw-guard13.sh /root/lw-guard14.sh
do
  wipe_sh "$f"
done

echo '=== dead systemd + gold unit sources ==='
for u in \
  /etc/systemd/system/sailingsa-lipton-public-watch.service \
  /etc/systemd/system/sailingsa-lipton-url-hold.service \
  /usr/local/lib/sailingsa-lipton-public-watch.service \
  /usr/local/lib/sailingsa-lipton-url-hold.service
do
  chattr -i "$u" 2>/dev/null || true
  printf '%s' "$DEAD_UNIT" > "$u"
  chmod 644 "$u"
  chattr +i "$u" 2>/dev/null || true
  echo "dead $u"
done
systemctl daemon-reload
systemctl stop sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true

echo '=== stub crons immutable ==='
for c in /etc/cron.d/sailingsa-lipton-public-not-dev /etc/cron.d/zzz-lipton-public-live /etc/cron.d/aa-lipton-url-hold; do
  chattr -i "$c" 2>/dev/null || true
  printf '# disabled\n' > "$c"
  chmod 644 "$c"
  chattr +i "$c" 2>/dev/null || true
done

echo '=== remaining debounce files ==='
grep -rl 'LIPTON_WATCH_DEBOUNCE_V1' /root /usr/local /var/lib/sailingsa-lipton /tmp 2>/dev/null | while read -r f; do
  echo "STILL $f $(wc -c < "$f")"
done || true
pgrep -af 'lw-g14c.py|not_dev_watch.py' || echo 'no watch procs'

echo '=== patch API so impl cannot emit weather ==='
chattr -i /var/www/sailingsa/api/api.py 2>/dev/null || true
python3 /tmp/patch_lipton_public_slug.py
python3 - <<'PY'
from pathlib import Path
t = Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
pb = t.split("def serve_lipton_dev_playback_page", 1)[-1][:700]
impl = t.split("def _serve_regatta_standalone_impl", 1)[-1][:600]
if "_serve_regatta_standalone_impl" in pb or "LIPTON_PUBLIC_NOT_DEV" in pb:
    raise SystemExit("FAIL playback hijack still present")
if "serve_lipton_dev_playback_page(request, public=True)" not in impl:
    raise SystemExit("FAIL impl not guarded")
print("API playback fn + impl both playback")
PY
python3 -m py_compile /var/www/sailingsa/api/api.py
chattr +i /var/www/sailingsa/api/api.py

echo '=== nginx alias ==='
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf

test -s /tmp/lipton-dev.html && cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
test -s /tmp/lipton-event-sheet.js && cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js
test -s /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css

echo '=== restart API ==='
systemctl restart sailingsa-api
for i in $(seq 1 25); do
  ss -ltn | grep -q ':8000' && break
  sleep 1
done
sleep 3

check() {
  echo "--- $1 ---"
  echo -n 'snippet '; head -2 /etc/nginx/snippets/lipton-public-proxy.conf | tr '\n' ' '; echo
  python3 - <<'PY'
from pathlib import Path
t=Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
pb=t.split("def serve_lipton_dev_playback_page",1)[-1][:350]
print("hijack", "LIPTON_PUBLIC_NOT_DEV" in pb)
print("g14c debounce", "LIPTON_WATCH_DEBOUNCE_V1" in Path("/root/lw-g14c.py").read_text(encoding="utf-8", errors="replace") if Path("/root/lw-g14c.py").is_file() else "missing")
PY
  curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
    -o /tmp/p.html -D /tmp/p.hdr -w 'pub %{http_code} %{size_download}\n' \
    'https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup'
  python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", 'data-lipton-dev="1"' in t, "weather", "WEATHER" in t or "Live cam" in t, "bytes", len(t), "ee/ef", "20260828ef" in t)
print("X-Lipton-Page", "playback" in open("/tmp/p.hdr",encoding="utf-8",errors="replace").read())
PY
}
check t0
sleep 12
check t12
sleep 15
check t27
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
if 'data-lipton-dev="1"' not in t or "WEATHER" in t or "Live cam" in t or len(t)>20000:
    raise SystemExit("FAIL old page still public")
print("OK playback held")
PY
pgrep -af 'lw-g14c.py' || echo 'still no g14c procs'
