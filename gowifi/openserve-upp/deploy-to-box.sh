#!/bin/bash
# Copy this tree onto box.gowifi.co.za and install the dash.
# Live https://gowifi.co.za only changes after this runs on the box.
set -euo pipefail
BOX="${GOWIFI_BOX:-root@102.209.119.186}"
SRC=$(cd "$(dirname "$0")" && pwd)
SSH=(ssh -o StrictHostKeyChecking=accept-new)
SCP=(scp -o StrictHostKeyChecking=accept-new)
if [ -n "${GOWIFI_SSH_KEY:-}" ]; then
  SSH+=(-i "$GOWIFI_SSH_KEY")
  SCP+=(-i "$GOWIFI_SSH_KEY")
fi
if [ -n "${SSHPASS:-}" ] && command -v sshpass >/dev/null; then
  SSH=(sshpass -e "${SSH[@]}")
  SCP=(sshpass -e "${SCP[@]}")
fi

echo "copy $SRC -> $BOX:/root/gowifi-upp"
"${SSH[@]}" "$BOX" "mkdir -p /root/gowifi-upp /home/user-data/www/default/dash /home/user-data/www/default/legal"
"${SCP[@]}" -r \
  "$SRC/dash/clients.html" \
  "$SRC/dash/accounts.html" \
  "$SRC/dash/invoice.html" \
  "$SRC/dash/invoices.html" \
  "$BOX:/home/user-data/www/default/dash/"
"${SCP[@]}" -r "$SRC/legal/." "$BOX:/home/user-data/www/default/legal/"
"${SCP[@]}" \
  "$SRC/clients.py" "$SRC/compliance.py" "$SRC/site_lines.py" \
  "$SRC/billing.py" "$SRC/books.py" "$SRC/packages.py" \
  "$SRC/customers.py" "$SRC/invoice_list.py" "$SRC/statements.py" "$SRC/netcash.py" \
  "$SRC/audit_export.py" "$SRC/hook_dash_index.py" "$SRC/invoice_import.py" \
  "$SRC/mail_forwards.py" "$SRC/ensure_go_wifi_mail.sh" \
  "$SRC/upp_emails.py" "$SRC/upp_set_password.py" \
  "$SRC/qb_oauth.py" \
  "$SRC/install-on-box.sh" "$SRC/company.py" "$SRC/invoice_canned.py" "$SRC/recon.py" \
  "$BOX:/root/gowifi-upp/"
"${SCP[@]}" -q \
  "$SRC/dash/clients.html" "$SRC/dash/accounts.html" "$SRC/dash/invoice.html" \
  "$SRC/dash/invoices.html" \
  "$BOX:/root/gowifi-upp/dash/" 2>/dev/null || "${SSH[@]}" "$BOX" "mkdir -p /root/gowifi-upp/dash"
"${SCP[@]}" \
  "$SRC/dash/clients.html" "$SRC/dash/accounts.html" "$SRC/dash/invoice.html" \
  "$SRC/dash/invoices.html" \
  "$BOX:/root/gowifi-upp/dash/"
"${SSH[@]}" "$BOX" "mkdir -p /root/gowifi-upp/data"
"${SCP[@]}" -r "$SRC/data/." "$BOX:/root/gowifi-upp/data/"

echo "install + refresh accounts.json"
"${SSH[@]}" "$BOX" "bash /root/gowifi-upp/install-on-box.sh && python3 /root/gowifi-upp/audit_export.py"
echo "done — hard-refresh https://gowifi.co.za/dash/clients.html /dash/invoices.html /dash/accounts.html"
