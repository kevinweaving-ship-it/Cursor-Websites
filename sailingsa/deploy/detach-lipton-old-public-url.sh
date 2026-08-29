#!/bin/bash
# Public Lipton URL = playback forever. Old weather page only at -old.
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
ENABLED=/etc/nginx/sites-enabled/sailingsa
BAKDIR=/root/lipton-detach-public-${TS}
mkdir -p "$BAKDIR" /root/disabled-lipton-not-dev

echo '=== kill 1s watch that restores old page ==='
bash /tmp/kill-lipton-public-watch-forever.sh
cp /tmp/kill-lipton-public-watch-forever.sh /root/kill-lipton-public-watch-forever.sh
chmod 700 /root/kill-lipton-public-watch-forever.sh

cp -a "$ENABLED" "$BAKDIR/nginx-sailingsa" || true
cp -a /var/www/sailingsa/api/api.py "$BAKDIR/api.py" || true
find /etc/nginx/sites-enabled -maxdepth 1 -type f ! -name '00-timadvisor' ! -name 'sailingsa' -print -delete || true

echo '=== html ==='
if test -f /tmp/lipton-dev.html; then
  cp /tmp/lipton-dev.html /var/www/sailingsa/lipton-dev.html
  mkdir -p /var/www/sailingsa/frontend
  cp /tmp/lipton-dev.html /var/www/sailingsa/frontend/lipton-dev.html
fi
ls -la /var/www/sailingsa/lipton-dev.html

echo '=== nginx public URL -> lipton-dev.html; -old -> API ==='
chattr -i "$ENABLED" 2>/dev/null || true
chattr -i /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true
python3 /tmp/force_lipton_nginx_alias.py
nginx -t
nginx -s reload
chattr +i "$ENABLED"
chattr +i /etc/nginx/snippets/lipton-public-proxy.conf 2>/dev/null || true

echo '=== API public=playback; -old=weather ==='
python3 /tmp/patch_lipton_public_slug.py
cp /tmp/patch_lipton_public_slug.py /root/patch_lipton_public_slug.py
cp /tmp/force_lipton_nginx_alias.py /root/force_lipton_nginx_alias.py
systemctl restart sailingsa-api
sleep 4
systemctl is-active sailingsa-api

cat > /root/lipton-keep-playback.sh <<'KEEP'
#!/bin/bash
set -euo pipefail
pkill -f lipton_public_watch_guard 2>/dev/null || true
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
if grep -q LIPTON_PUBLIC_NOT_DEV /var/www/sailingsa/api/api.py 2>/dev/null; then
  python3 /root/patch_lipton_public_slug.py && systemctl restart sailingsa-api || true
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
import subprocess, time
time.sleep(1)

def chk(url):
    t = subprocess.check_output(["curl","-sS","-A","SailingSA-devcheck",url], text=True, errors="replace")
    print(url, "bytes", len(t), "playback", 'data-lipton-dev="1"' in t,
          "weather", ("WEATHER" in t or "Live cam" in t))
    return t

pub = chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup")
r7 = chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup?race=7")
old = chk("https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old")
if 'data-lipton-dev="1"' not in pub or "WEATHER" in pub:
    raise SystemExit("FAIL public")
if 'data-lipton-dev="1"' not in r7 or "WEATHER" in r7:
    raise SystemExit("FAIL ?race=7")
if "WEATHER" not in old and "Live cam" not in old:
    raise SystemExit("FAIL -old")
print("OK public=playback including ?race=7; weather only on -old")
PY
ps aux | grep -Ei 'lipton_public_watch_guard|lipton_public_not_dev' | grep -v grep || echo 'watch processes: none'
