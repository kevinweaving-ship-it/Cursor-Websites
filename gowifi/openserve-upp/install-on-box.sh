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
    "$SRC/qb_import.py" "$SRC/invoice_canned.py" "$SRC/company.py" \
    "$SRC/checksum_accounts_mail.py" "$SRC/README.md" "$DEST/"
fi
chmod 755 "$DEST/sync.py" "$DEST/checksum_accounts_mail.py" \
  "$DEST/audit_export.py" "$DEST/status_events.py" "$DEST/invoice_import.py" \
  "$DEST/site_lines.py" "$DEST/client_stories.py" "$DEST/books.py" \
  "$DEST/qb_import.py" "$DEST/invoice_canned.py" "$DEST/company.py"
DASH=/home/user-data/www/default/dash
mkdir -p "$DASH"
mkdir -p "$DEST/dash"
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
# every 15 minutes; no-op until /root/secrets/upp.token has a JWT
CRON_LINE='*/15 * * * * UPP_DB=/root/gowifi-upp/upp.db /usr/bin/python3 /root/gowifi-upp/sync.py >> /var/log/gowifi-upp-sync.log 2>&1'
(crontab -l 2>/dev/null | grep -v gowifi-upp-sync.py || true; echo "$CRON_LINE") | crontab -
echo "installed $DEST"
