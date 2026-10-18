#!/bin/bash
# Run ON LIVE as root. Soft 404 404s + sitemap rebuild. Does not touch api.py.
set -euo pipefail

SNIPPET_SRC="${1:-/tmp/sailingsa-soft404.conf}"
BUILDER_SRC="${2:-/tmp/sitemap_builder.py}"
SNIPPET_DST="/etc/nginx/snippets/sailingsa-soft404.conf"
BUILDER_DST="/var/www/sailingsa/utils/sitemap_builder.py"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p /root/backups

echo "=== 1. nginx snippet ==="
test -f "$SNIPPET_SRC" || { echo "MISSING $SNIPPET_SRC"; exit 1; }
cp -a "$SNIPPET_SRC" "$SNIPPET_DST"
chmod 644 "$SNIPPET_DST"
echo "wrote $SNIPPET_DST"

SITE=""
for c in /etc/nginx/sites-enabled/sailingsa /etc/nginx/sites-available/sailingsa; do
  if [[ -f "$c" ]]; then SITE="$c"; break; fi
done
[[ -n "$SITE" ]] || { echo "NO nginx site file"; exit 1; }
echo "site=$SITE"

if grep -q 'sailingsa-soft404.conf' "$SITE"; then
  echo "include already present"
else
  cp -a "$SITE" "/root/backups/nginx-sailingsa.${STAMP}"
  lsattr "$SITE" || true
  chattr -i "$SITE" 2>/dev/null || true
  if grep -q 'sailingsa-swarm-deny.conf' "$SITE"; then
    sed -i '/sailingsa-swarm-deny.conf/a\    include /etc/nginx/snippets/sailingsa-soft404.conf;' "$SITE"
  elif grep -q 'include /etc/nginx/snippets/' "$SITE"; then
    sed -i '0,/include \/etc\/nginx\/snippets\//{s||include /etc/nginx/snippets/sailingsa-soft404.conf;\n    &|}' "$SITE"
  else
    sed -i '0,/server {/{s//server {\n    include \/etc\/nginx\/snippets\/sailingsa-soft404.conf;/}' "$SITE"
  fi
  echo "include inserted"
fi

echo "=== 2. nginx -t + reload ==="
nginx -t
systemctl reload nginx
echo "NGINX_RELOADED"
lsattr "$SITE" || true
# restore immutable if it was set before
if [[ -f "/root/backups/nginx-sailingsa.${STAMP}" ]] || lsattr "$SITE" 2>/dev/null | grep -q -- '-i-'; then
  chattr +i "$SITE" 2>/dev/null || true
fi
# If we unlocked it, lock it again (site is normally +i)
chattr +i "$SITE" 2>/dev/null || true
echo "site lsattr=$(lsattr "$SITE" 2>/dev/null || true)"

echo "=== 3. sitemap builder (not api.py) ==="
if [[ -f "$BUILDER_SRC" ]]; then
  if [[ -f "$BUILDER_DST" ]]; then
    cp -a "$BUILDER_DST" "/root/backups/sitemap_builder.py.${STAMP}"
  fi
  chattr -i "$BUILDER_DST" 2>/dev/null || true
  cp -a "$BUILDER_SRC" "$BUILDER_DST"
  chown www-data:www-data "$BUILDER_DST" 2>/dev/null || true
  echo "wrote $BUILDER_DST"
else
  echo "WARN: no builder src, skip copy"
fi

echo "=== 4. rebuild sitemap ==="
if [[ -x /var/www/sailingsa/sailingsa/deploy/refresh-sitemap-cron.sh ]]; then
  bash /var/www/sailingsa/sailingsa/deploy/refresh-sitemap-cron.sh
elif [[ -x /var/www/sailingsa/deploy/refresh-sitemap-cron.sh ]]; then
  bash /var/www/sailingsa/deploy/refresh-sitemap-cron.sh
else
  EV=$(systemctl show sailingsa-api -p Environment --value 2>/dev/null || true)
  export DB_URL
  DB_URL=$(echo "$EV" | tr ' ' '\n' | sed -n 's/^DB_URL=//p' | head -1)
  export PYTHONPATH=/var/www/sailingsa
  export SITEMAP_OUTPUT=/var/www/sailingsa/sitemap.xml
  export BASE_URL=https://sailingsa.co.za
  /var/www/sailingsa/api/venv/bin/python3 - <<'PY'
import os, sys, psycopg2
sys.path.insert(0, os.environ["PYTHONPATH"])
from utils.sitemap_builder import build_sitemap
conn = psycopg2.connect(os.environ["DB_URL"])
try:
    stats = build_sitemap(conn, output_path=os.environ["SITEMAP_OUTPUT"], base_url=os.environ["BASE_URL"])
    print("[sitemap]", stats)
    if not stats or not stats.get("ok"):
        raise SystemExit(1)
finally:
    conn.close()
PY
  chown www-data:www-data /var/www/sailingsa/sitemap.xml /var/www/sailingsa/sitemap-*.xml 2>/dev/null || true
fi

echo "=== 5. local verify ==="
for u in \
  /sailor/unknown /sailor/none /sailor/na /sailor/tbc /sailor/tba \
  /class/unknown /boat/unknown /club/none /club/NONE \
  /sailor/aydin-ohara /club/hyc /class/505; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' "http://127.0.0.1$u" || echo ERR)
  echo "$code $u"
done
echo "SOFT404_APPLY_DONE"
