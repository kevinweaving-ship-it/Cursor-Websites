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
    "$SRC/netcash.py" "$SRC/fnb_api.py" "$SRC/fnb_statement.py" "$SRC/ledger.py" "$SRC/billing.py" "$SRC/packages.py" "$SRC/invoice_canned.py" "$SRC/company.py" \
    "$SRC/compliance.py" "$SRC/clients.py" \
    "$SRC/customers.py" "$SRC/invoice_list.py" "$SRC/statements.py" "$SRC/recon.py" \
    "$SRC/checksum_accounts_mail.py" "$SRC/mail_forwards.py" \
    "$SRC/ensure_go_wifi_mail.sh" "$SRC/upp_emails.py" \
    "$SRC/upp_set_password.py" \
    "$SRC/MAC_CURSOR_OPENSERVE_MAIL.md" \
    "$SRC/README.md" "$DEST/"
  mkdir -p "$DEST/data"
  if [ -d "$SRC/data" ]; then
    cp -a "$SRC/data/." "$DEST/data/"
  fi
fi
chmod 755 "$DEST/sync.py" "$DEST/checksum_accounts_mail.py" \
  "$DEST/audit_export.py" "$DEST/status_events.py" "$DEST/invoice_import.py" \
  "$DEST/site_lines.py" "$DEST/client_stories.py" "$DEST/books.py" \
  "$DEST/qb_import.py" "$DEST/qb_oauth.py" "$DEST/qb_api.py" \
  "$DEST/netcash.py" "$DEST/fnb_api.py" "$DEST/fnb_statement.py" "$DEST/ledger.py" "$DEST/billing.py" "$DEST/packages.py" "$DEST/invoice_canned.py" "$DEST/company.py" \
  "$DEST/compliance.py" "$DEST/clients.py" \
  "$DEST/customers.py" "$DEST/invoice_list.py" "$DEST/statements.py" "$DEST/recon.py" \
  "$DEST/mail_forwards.py" "$DEST/ensure_go_wifi_mail.sh" \
  "$DEST/upp_emails.py" "$DEST/upp_set_password.py"
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
if [ -f "$SRC/dash/clients.html" ]; then
  if [ "$SRC/dash/clients.html" != "$DEST/dash/clients.html" ]; then
    cp -a "$SRC/dash/clients.html" "$DEST/dash/clients.html"
  fi
  cp -a "$SRC/dash/clients.html" "$DASH/clients.html"
fi
if [ -f "$SRC/dash/invoices.html" ]; then
  if [ "$SRC/dash/invoices.html" != "$DEST/dash/invoices.html" ]; then
    cp -a "$SRC/dash/invoices.html" "$DEST/dash/invoices.html"
  fi
  cp -a "$SRC/dash/invoices.html" "$DASH/invoices.html"
fi
HOOK="$SRC/hook_dash_index.py"
[ -f "$HOOK" ] || HOOK="$DEST/hook_dash_index.py"
if [ -f "$HOOK" ]; then
  [ "$HOOK" = "$DEST/hook_dash_index.py" ] || cp -a "$HOOK" "$DEST/hook_dash_index.py"
  python3 "$DEST/hook_dash_index.py" || true
fi
touch /root/secrets/upp.token
chmod 600 /root/secrets/upp.token
if [ ! -f /root/secrets/fnb.env ]; then
  printf '%s\n' \
    'FNB_USERNAME=' \
    'FNB_PASSWORD=' \
    'FNB_CLIENT_ID=' \
    'FNB_CLIENT_SECRET=' \
    'FNB_ACCOUNT_NUMBER=62860060278' \
    > /root/secrets/fnb.env
  chmod 600 /root/secrets/fnb.env
fi
if [ ! -f /root/secrets/qbo.env ]; then
  printf '%s\n' \
    'QBO_KEYSET=production' \
    'QBO_APP_ID=29bf4b87-d9b1-438f-9e35-52362429db57' \
    'QBO_DEV_CLIENT_ID=ABs2E5POp4qzGRxLNEmMvP0LC2fGgXKzcHzYs1RUl4bsBhhvjD' \
    'QBO_DEV_CLIENT_SECRET=' \
    'QBO_PROD_CLIENT_ID=ABuRsGyeZTQuOqil7wEeIWsIjzSQU6UQv4hOg1R0vXzPDVEjXL' \
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
  elif ! grep -q 'location = /legal/qb-callback.html' "$WWWCONF"; then
    printf '%s\n' \
      'location = /legal/qb-callback.html {' \
      '	proxy_pass http://127.0.0.1:8799/callback;' \
      '	proxy_set_header Host $host;' \
      '}' >> "$WWWCONF"
    nginx -t && systemctl reload nginx || true
  fi
fi
if [ -f "$SRC/gowifi-qb-oauth.service" ]; then
  cp -a "$SRC/gowifi-qb-oauth.service" /etc/systemd/system/gowifi-qb-oauth.service
  systemctl daemon-reload
  systemctl enable --now gowifi-qb-oauth.service || true
fi
if [ -f "$SRC/nginx-fnb.conf" ] && [ -f "$WWWCONF" ]; then
  python3 - "$WWWCONF" "$SRC/nginx-fnb.conf" <<'PY'
from pathlib import Path
import re
import sys
conf, block = Path(sys.argv[1]), Path(sys.argv[2]).read_text()
text = conf.read_text()
pat = re.compile(
    r"(?:# Included from[^\n]*\n)?(?:location = /legal/fnb-[a-z]+ \{.*?\n\}\n*)+",
    re.S,
)
if pat.search(text):
    text = pat.sub(block.strip(), text)
    conf.write_text(text)
elif "location = /legal/fnb-status" not in text:
    conf.write_text(text.rstrip() + "\n" + block)
PY
  nginx -t && systemctl reload nginx || true
fi
if [ -f "$SRC/gowifi-fnb-api.service" ]; then
  cp -a "$SRC/gowifi-fnb-api.service" /etc/systemd/system/gowifi-fnb-api.service
  systemctl daemon-reload
  systemctl enable --now gowifi-fnb-api.service || true
  systemctl restart gowifi-fnb-api.service || true
fi
# every 15 minutes; no-op until /root/secrets/upp.token has a JWT
CRON_LINE='*/15 * * * * UPP_DB=/root/gowifi-upp/upp.db /usr/bin/python3 /root/gowifi-upp/sync.py >> /var/log/gowifi-upp-sync.log 2>&1'
CRON_FNB='*/30 * * * * UPP_DB=/root/gowifi-upp/upp.db /usr/bin/python3 /root/gowifi-upp/fnb_api.py pull >> /var/log/gowifi-fnb-fetch.log 2>&1'
(crontab -l 2>/dev/null | grep -v 'gowifi-upp/sync.py' | grep -v 'fnb_api.py pull' | grep -v 'fnb_statement.py pull' || true; echo "$CRON_LINE"; echo "$CRON_FNB") | crontab -
apt-get install -y -qq xvfb >/dev/null 2>&1 || true
python3 -m pip install -q playwright >/dev/null 2>&1 || true
python3 -m playwright install-deps chromium >/dev/null 2>&1 || true
python3 -m playwright install chromium >/dev/null 2>&1 || true
if [ -f "$DEST/ensure_go_wifi_mail.sh" ]; then
  bash "$DEST/ensure_go_wifi_mail.sh"
fi
echo "installed $DEST"
