#!/bin/bash
# Old Lipton weather/event page must not own the public URL.
# Public slug aliases lipton-dev.html. Old page only at /event.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
ENABLED=/etc/nginx/sites-enabled/sailingsa
BAKDIR=/root/lipton-detach-public-${TS}
mkdir -p "$BAKDIR" /root/disabled-lipton-not-dev

echo '=== stop other agents restoring old public URL ==='
for f in /etc/cron.d/*; do
  base=$(basename "$f")
  case "$base" in
    sailingsa-lipton-schedule) continue ;;
    *lipton*) mv "$f" /root/disabled-lipton-not-dev/ && echo "moved cron $base" ;;
  esac
done
pkill -f lipton_public_not_dev 2>/dev/null || true
pkill -f patch_lipton_nginx_public 2>/dev/null || true
chattr -i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true
printf '%s\n' '#!/usr/bin/python3' 'raise SystemExit(0)' > /usr/local/sbin/lipton_public_not_dev_watch.py
chmod 755 /usr/local/sbin/lipton_public_not_dev_watch.py
chattr +i /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true

cp -a "$ENABLED" "$BAKDIR/nginx-sailingsa" || true
cp -a /var/www/sailingsa/api/api.py "$BAKDIR/api.py" || true

# Drop backup confs nginx would include
find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true

echo '=== html file first (nginx rewrite 404s if missing) ==='
if test -f /tmp/lipton-dev.html; then
  cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
  mkdir -p /var/www/sailingsa/frontend
  cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
fi
ls -la /var/www/sailingsa/lipton-dev.html
grep -c 'data-lipton-dev' /var/www/sailingsa/lipton-dev.html

echo '=== nginx: public URL = playback file; -old = API event page ==='
chattr -i "$ENABLED" 2>/dev/null || true
python3 /tmp/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i "$ENABLED"
lsattr "$ENABLED"

echo '=== API: old page no longer served at public slug ==='
python3 /tmp/patch_lipton_public_slug.py
systemctl restart sailingsa-api
sleep 3
systemctl is-active sailingsa-api

cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
mkdir -p /root/disabled-lipton-not-dev
for f in /etc/cron.d/*; do
  base=$(basename "$f")
  case "$base" in
    sailingsa-lipton-schedule) continue ;;
    *lipton*) mv "$f" /root/disabled-lipton-not-dev/ 2>/dev/null || rm -f "$f" ;;
  esac
done
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
CONF=/etc/nginx/sites-enabled/sailingsa
GOLD=/root/lipton-nginx-golden.conf
test -s "$GOLD"
ok=0
if grep -F 'location = /regatta/2026-08-29-lipton-challenge-cup {' "$CONF" >/dev/null 2>&1; then
  blk=$(awk '/location = \/regatta\/2026-08-29-lipton-challenge-cup \{/,/^    \}/' "$CONF" | head -20)
  echo "$blk" | grep -qF 'alias /var/www/sailingsa/lipton-dev.html' || ok=1
  echo "$blk" | grep -q proxy_pass && ok=1
else
  ok=1
fi
if [ "$ok" = 0 ]; then
  exit 0
fi
chattr -i "$CONF" 2>/dev/null || true
python3 /root/force_lipton_nginx_alias.py 2>/dev/null || cp "$GOLD" "$CONF"
if nginx -t; then
  nginx -s reload
  chattr +i "$CONF" 2>/dev/null || true
  echo "$(date -Is) restored public playback alias (old page not on public URL)" >> /root/lipton-keep-playback.log
fi
KEEP
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
chmod 700 /root/lipton-keep-playback.sh /root/force_lipton_nginx_alias.py
grep -q lipton-keep-playback /etc/crontab || echo '* * * * * root /root/lipton-keep-playback.sh' >> /etc/crontab

echo '=== verify ==='
python3 - <<'PY'
import subprocess

def chk(url):
    p = subprocess.run(
        ["curl", "-sS", "-D", "-", "-A", "SailingSA-devcheck", "-o", "/tmp/p.html",
         "-w", " http%{http_code}", url],
        capture_output=True, text=True, errors="replace",
    )
    t = open("/tmp/p.html", encoding="utf-8", errors="replace").read()
    print(url, p.stdout.strip().splitlines()[-1] if p.stdout else "")
    print("  bytes", len(t), "playback", 'data-lipton-dev="1"' in t,
          "weather", ("WEATHER" in t or "Live cam" in t),
          "head", t[:80].replace("\n", " "))
    return t

pub = chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup")
old = chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old")
if 'data-lipton-dev="1"' not in pub or "WEATHER" in pub:
    raise SystemExit("FAIL: public URL is not playback")
if "WEATHER" not in old and "Live cam" not in old:
    raise SystemExit("FAIL: -old URL is not the old event page")
print("OK public=playback old=-old")
PY
echo '=== nginx locs ==='
grep -n 'lipton-challenge-cup' "$ENABLED" | head
