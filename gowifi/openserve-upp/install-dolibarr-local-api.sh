#!/bin/bash
# Enable on-box Dolibarr REST + dash books API. No outbound calls.
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
WWWCONF=/home/user-data/www/gowifi.co.za.conf
ENV=/root/secrets/dolibarr.env

# API key on the dash Dolibarr user (same secret file).
# shellcheck disable=SC1090
source "$ENV"
if [ -z "${DOLIBARR_API_KEY:-}" ]; then
  DOLIBARR_API_KEY=$(openssl rand -hex 16)
  echo "DOLIBARR_API_KEY=$DOLIBARR_API_KEY" >> "$ENV"
fi
mysql --protocol=socket -u root -e \
  "UPDATE dolibarr.llx_user SET api_key='${DOLIBARR_API_KEY}' WHERE login='dash';"

cp -f "$SRC/dolibarr_local.py" "$SRC/books_api.py" "$SRC/publish_dolibarr_books.py" \
  "$SRC/hook_dash_books.py" /root/gowifi-upp/
chmod +x /root/gowifi-upp/dolibarr_local.py /root/gowifi-upp/books_api.py \
  /root/gowifi-upp/publish_dolibarr_books.py /root/gowifi-upp/hook_dash_books.py

cp -f "$SRC/nginx-dolibarr-local.conf" /etc/nginx/conf.d/gowifi-dolibarr-local.conf
if [ -f "$SRC/nginx-dash-books.conf" ] && [ -f "$WWWCONF" ]; then
  if ! grep -q 'location = /dash/api/books' "$WWWCONF"; then
    printf '\n' >> "$WWWCONF"
    cat "$SRC/nginx-dash-books.conf" >> "$WWWCONF"
  fi
fi
nginx -t
systemctl reload nginx

cp -f "$SRC/gowifi-books-api.service" /etc/systemd/system/gowifi-books-api.service
systemctl daemon-reload
systemctl enable --now gowifi-books-api.service
systemctl restart gowifi-books-api.service

python3 /root/gowifi-upp/hook_dash_books.py
python3 /root/gowifi-upp/publish_dolibarr_books.py
echo "dolibarr-local-api-ready"
