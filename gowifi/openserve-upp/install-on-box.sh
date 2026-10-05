#!/bin/bash
# Install UPP mirror + accounts-mail checksum on box.gowifi.co.za
set -euo pipefail
DEST=/root/gowifi-upp
SRC=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DEST"
if [ "$SRC" != "$DEST" ]; then
  cp -a "$SRC/schema.sql" "$SRC/sync.py" "$SRC/audit_export.py" \
    "$SRC/status_events.py" "$SRC/invoice_import.py" \
    "$SRC/site_lines.py" "$SRC/client_stories.py" "$SRC/books.py" \
    "$SRC/qb_import.py" "$SRC/qb_oauth.py" "$SRC/qb_api.py" \
    "$SRC/netcash.py" "$SRC/ledger.py" "$SRC/invoice_canned.py" "$SRC/company.py" \
    "$SRC/checksum_accounts_mail.py" "$SRC/README.md" "$DEST/"
  mkdir -p "$DEST/data"
  if [ -d "$SRC/data" ]; then
    cp -a "$SRC/data/." "$DEST/data/"
  fi
fi
chmod 755 "$DEST/sync.py" "$DEST/checksum_accounts_mail.py" \
  "$DEST/audit_export.py" "$DEST/status_events.py" "$DEST/invoice_import.py" \
  "$DEST/site_lines.py" "$DEST/client_stories.py" "$DEST/books.py" \
  "$DEST/qb_import.py" "$DEST/qb_oauth.py" "$DEST/qb_api.py" \
  "$DEST/netcash.py" "$DEST/ledger.py" "$DEST/invoice_canned.py" "$DEST/company.py"
WWW=/home/user-data/www/default
DASH="$WWW/dash"
LEGAL="$WWW/legal"
mkdir -p "$DASH" "$LEGAL"
mkdir -p "$DEST/dash" "$DEST/legal"
if [ -d "$SRC/legal" ]; then
  if [ "$SRC/legal" != "$DEST/legal" ]; then
    cp -a "$SRC/legal/." "$DEST/legal/"
  fi
  cp -a "$SRC/legal/." "$LEGAL/"
fi
if [ -f "$SRC/dash/accounts.html" ]; then
  if [ "$SRC/dash/accounts.html" != "$DEST/dash/accounts.html" ]; then
    cp -a "$SRC/dash/accounts.html" "$DEST/dash/accounts.html"
  fi
  cp -a "$SRC/dash/accounts.html" "$DASH/accounts.html"
fi
if [ -f "$SRC/dash/invoice.html" ]; then
  if [ "$SRC/dash/invoice.html" != "$DEST/dash/invoice.html" ]; then
    cp -a "$SRC/dash/invoice.html" "$DEST/dash/invoice.html"
  fi
  cp -a "$SRC/dash/invoice.html" "$DASH/invoice.html"
fi
HOOK="$SRC/hook_dash_index.py"
[ -f "$HOOK" ] || HOOK="$DEST/hook_dash_index.py"
if [ -f "$HOOK" ]; then
  [ "$HOOK" = "$DEST/hook_dash_index.py" ] || cp -a "$HOOK" "$DEST/hook_dash_index.py"
  python3 "$DEST/hook_dash_index.py" || true
fi
touch /root/secrets/upp.token
chmod 600 /root/secrets/upp.token
if [ ! -f /root/secrets/qbo.env ]; then
  printf '%s\n' \
    'QBO_KEYSET=development' \
    'QBO_DEV_CLIENT_ID=' \
    'QBO_DEV_CLIENT_SECRET=' \
    'QBO_PROD_CLIENT_ID=' \
    'QBO_PROD_CLIENT_SECRET=' \
    'QBO_REDIRECT_URI=https://gowifi.co.za/legal/qb-callback.html' \
    > /root/secrets/qbo.env
  chmod 600 /root/secrets/qbo.env
fi
WWWCONF=/home/user-data/www/gowifi.co.za.conf
if [ -f "$SRC/nginx-qb.conf" ] && [ -f "$WWWCONF" ]; then
  if ! grep -q 'location = /legal/qb-start' "$WWWCONF"; then
    cat "$SRC/nginx-qb.conf" >> "$WWWCONF"
    nginx -t && systemctl reload nginx || true
  fi
fi
if [ -f "$SRC/gowifi-qb-oauth.service" ]; then
  cp -a "$SRC/gowifi-qb-oauth.service" /etc/systemd/system/gowifi-qb-oauth.service
  systemctl daemon-reload
  systemctl enable --now gowifi-qb-oauth.service || true
fi
# every 15 minutes; no-op until /root/secrets/upp.token has a JWT
CRON_LINE='*/15 * * * * UPP_DB=/root/gowifi-upp/upp.db /usr/bin/python3 /root/gowifi-upp/sync.py >> /var/log/gowifi-upp-sync.log 2>&1'
(crontab -l 2>/dev/null | grep -v 'gowifi-upp/sync.py' || true; echo "$CRON_LINE") | crontab -
echo "installed $DEST"
