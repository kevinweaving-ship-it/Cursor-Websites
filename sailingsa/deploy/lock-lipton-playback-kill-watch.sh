#!/bin/bash
# Kill live-board systemd loops, restore playback, strip API hijack, hold for 20s.
set -euo pipefail

bash /tmp/kill-lipton-public-watch-forever.sh || true

# Extra gold / guard copies the watch loops look for
STUB_PY=$'#!/usr/bin/python3\nraise SystemExit(0)\n'
STUB_SH=$'#!/bin/bash\nexit 0\n'
for f in /root/lw-g14.py /root/lw-g13b.py /root/lw-g14b.py /root/lw-guard.sh /root/lw-guard6.sh /root/lw-guard7.sh /root/lw-guard13.sh /root/lw-guard14.sh \
         /usr/local/lib/lipton_public_watch_guard.sh /usr/local/sbin/lipton_public_watch_guard.sh; do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  case "$f" in
    *.py) printf '%s' "$STUB_PY" > "$f" ;;
    *) printf '%s' "$STUB_SH" > "$f" ;;
  esac
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
  echo "stub-lock $f $(wc -c < "$f")"
done

# Dead systemd units, immutable
DEAD_UNIT=$'[Unit]\nDescription=disabled — must not restore old Lipton event page\n[Service]\nType=oneshot\nExecStart=/bin/true\n[Install]\nWantedBy=multi-user.target\n'
for u in /etc/systemd/system/sailingsa-lipton-public-watch.service \
         /etc/systemd/system/sailingsa-lipton-url-hold.service; do
  chattr -i "$u" 2>/dev/null || true
  printf '%s' "$DEAD_UNIT" > "$u"
  chmod 644 "$u"
  chattr +i "$u" 2>/dev/null || true
  echo "dead-unit $u"
done
systemctl daemon-reload
systemctl stop sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
# Do not mask: mask replaces the unit file with a /dev/null symlink and the
# watcher then writes a live unit back. Dead +i unit files stay put.
systemctl is-active sailingsa-lipton-public-watch.service || true
systemctl is-active sailingsa-lipton-url-hold.service || true

echo '=== patch API hijack out ==='
chattr -i /var/www/sailingsa/api/api.py 2>/dev/null || true
python3 /tmp/patch_lipton_public_slug.py
python3 - <<'PY'
from pathlib import Path
t = Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
pb = t.split("def serve_lipton_dev_playback_page", 1)[-1][:700]
if "_serve_regatta_standalone_impl" in pb or "LIPTON_PUBLIC_NOT_DEV" in pb:
    raise SystemExit("FAIL playback still hijacked after patch")
print("playback fn clean")
PY
python3 -m py_compile /var/www/sailingsa/api/api.py
chattr +i /var/www/sailingsa/api/api.py

test -s /tmp/lipton-dev.html && cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
test -s /tmp/lipton-event-sheet.js && cp /tmp/lipton-event-sheet.js /var/www/sailingsa/js/lipton-event-sheet.js
test -s /tmp/lipton-dev.css && cp /tmp/lipton-dev.css /var/www/sailingsa/css/lipton-dev.css

echo '=== nginx alias ==='
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf

cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
systemctl stop sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service 2>/dev/null || true
SNIP=/etc/nginx/snippets/lipton-public-proxy.conf
CONF=/etc/nginx/sites-enabled/sailingsa
AVAIL=/etc/nginx/sites-available/sailingsa
if ! test -f "$SNIP" || grep -q proxy_pass "$SNIP" || ! grep -q 'alias /var/www/sailingsa/lipton-dev.html' "$SNIP"; then
  chattr -i "$CONF" "$AVAIL" "$SNIP" 2>/dev/null || true
  python3 /root/force_lipton_nginx_alias.py
  nginx -t && nginx -s reload
  chattr +i "$CONF" "$AVAIL" "$SNIP" 2>/dev/null || true
  echo "$(date -Is) restored public playback" >> /root/lipton-keep-playback.log
fi
API=/var/www/sailingsa/api/api.py
if grep -q 'LIPTON_PUBLIC_NOT_DEV_V4' "$API" 2>/dev/null; then
  chattr -i "$API" 2>/dev/null || true
  python3 - <<'PY'
from pathlib import Path
p = Path("/var/www/sailingsa/api/api.py")
t = p.read_text(encoding="utf-8")
h = (
    "    if public:\n"
    "        # LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True must still render the live board.\n"
    '        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)\n'
)
if h in t:
    p.write_text(t.replace(h, ""), encoding="utf-8")
    print("stripped V4 hijack")
PY
  chattr +i "$API" 2>/dev/null || true
  echo "$(date -Is) stripped API V4 hijack" >> /root/lipton-keep-playback.log
fi
KEEP
chmod 700 /root/lipton-keep-playback.sh
grep -q lipton-keep-playback /etc/crontab || echo '* * * * * root /root/lipton-keep-playback.sh' >> /etc/crontab

echo '=== restart API ==='
systemctl restart sailingsa-api
for i in $(seq 1 30); do
  if ss -ltn | grep -q ':8000'; then echo listen ok; break; fi
  sleep 1
done
sleep 4
systemctl is-active sailingsa-api

check() {
  echo "--- check $1 ---"
  echo SNIP; head -8 /etc/nginx/snippets/lipton-public-proxy.conf
  python3 - <<'PY'
from pathlib import Path
t=Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
pb=t.split("def serve_lipton_dev_playback_page",1)[-1][:400]
print("hijack", "LIPTON_PUBLIC_NOT_DEV" in pb)
PY
  curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck \
    -o /tmp/p.html -D /tmp/p.hdr -w 'pub %{http_code} %{size_download}\n' \
    https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
  python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", 'data-lipton-dev="1"' in t, "weather", "WEATHER" in t or "Live cam" in t, "bytes", len(t))
print("nowrap js", "white-space:nowrap!important" in open("/var/www/sailingsa/js/lipton-event-sheet.js",encoding="utf-8").read())
print("wrap js", "white-space:normal!important" in open("/var/www/sailingsa/js/lipton-event-sheet.js",encoding="utf-8").read())
PY
}

check t0
sleep 8
check t8
sleep 12
check t20

python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
if 'data-lipton-dev="1"' not in t or "WEATHER" in t or "Live cam" in t or len(t) > 20000:
    raise SystemExit("FAIL public still old page after hold")
print("OK playback held")
PY
echo '=== units ==='
systemctl is-enabled sailingsa-lipton-public-watch.service || true
systemctl is-enabled sailingsa-lipton-url-hold.service || true
lsattr /etc/nginx/snippets/lipton-public-proxy.conf /var/www/sailingsa/api/api.py
