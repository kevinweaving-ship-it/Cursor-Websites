#!/bin/bash
# Enable on-box Dolibarr REST + dash books API. No outbound calls.
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
WWWCONF=/home/user-data/www/gowifi.co.za.conf
ENV=/root/secrets/dolibarr.env

# Unique API key for the dash Dolibarr user (uk_user_api_key is unique).
# shellcheck disable=SC1090
source "$ENV"
DASH_API_KEY=$(mysql --protocol=socket -u root -N -e \
  "SELECT IFNULL(api_key,'') FROM dolibarr.llx_user WHERE login='dash';")
if [ -z "$DASH_API_KEY" ]; then
  DASH_API_KEY=$(openssl rand -hex 16)
  mysql --protocol=socket -u root -e \
    "UPDATE dolibarr.llx_user SET api_key='${DASH_API_KEY}' WHERE login='dash';"
fi
if grep -q '^DOLIBARR_API_KEY=' "$ENV"; then
  sed -i "s/^DOLIBARR_API_KEY=.*/DOLIBARR_API_KEY=${DASH_API_KEY}/" "$ENV"
else
  echo "DOLIBARR_API_KEY=$DASH_API_KEY" >> "$ENV"
fi

DEST=/root/gowifi-upp
if [ "$SRC" != "$DEST" ]; then
  cp -f "$SRC/dolibarr_local.py" "$SRC/books_api.py" "$SRC/publish_dolibarr_books.py" \
    "$SRC/hook_dash_books.py" "$DEST/"
fi
chmod +x "$DEST/dolibarr_local.py" "$DEST/books_api.py" \
  "$DEST/publish_dolibarr_books.py" "$DEST/hook_dash_books.py"

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
