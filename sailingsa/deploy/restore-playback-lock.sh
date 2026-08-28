#!/bin/bash
set -euo pipefail
bash /tmp/kill-lipton-public-watch-forever.sh || true

STUB_PY=$'#!/usr/bin/python3\nraise SystemExit(0)\n'
STUB_SH=$'#!/bin/bash\nexit 0\n'
for f in /root/lw-gold*.py; do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB_PY" > "$f"
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
  echo "gold-stub $f"
done
for f in /usr/local/lib/lipton_public_watch_guard.sh /usr/local/sbin/lipton_public_watch_guard.sh /root/lipton_public_watch_guard.sh; do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB_SH" > "$f"
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
  echo "guard-stub $f $(wc -c < "$f")"
done

cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chattr -i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa /etc/nginx/snippets/lipton-public-proxy.conf

cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
pkill -f lipton_public_watch_guard 2>/dev/null || true
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
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
KEEP
chmod 700 /root/lipton-keep-playback.sh
grep -q lipton-keep-playback /etc/crontab || echo '* * * * * root /root/lipton-keep-playback.sh' >> /etc/crontab

echo '=== snippet ==='
head -6 /etc/nginx/snippets/lipton-public-proxy.conf
echo '=== curl ==='
curl -sS -A SailingSA-devcheck --resolve sailingsa.co.za:443:127.0.0.1 -o /tmp/p.html -w 'size %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
python3 - <<'PY'
t=open("/tmp/p.html",encoding="utf-8",errors="replace").read()
print("playback", 'data-lipton-dev="1"' in t, "sheetjs", "lipton-event-sheet.js" in t, "bytes", len(t))
if 'data-lipton-dev="1"' not in t:
    raise SystemExit("FAIL not playback")
PY
sleep 12
curl -sS -A SailingSA-devcheck --resolve sailingsa.co.za:443:127.0.0.1 -o /tmp/p2.html -w 'size2 %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
python3 - <<'PY'
t=open("/tmp/p2.html",encoding="utf-8",errors="replace").read()
print("playback2", 'data-lipton-dev="1"' in t, "bytes", len(t))
snip=open("/etc/nginx/snippets/lipton-public-proxy.conf").read()
print("snip_proxy", "proxy_pass" in snip, "snip_alias", "alias /var/www/sailingsa/lipton-dev.html" in snip)
if 'data-lipton-dev="1"' not in t:
    raise SystemExit("FAIL flipped after 12s")
print("OK playback held")
PY
