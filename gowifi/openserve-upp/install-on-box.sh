#!/bin/bash
# Install UPP mirror + accounts-mail checksum on box.gowifi.co.za
set -euo pipefail
DEST=/root/gowifi-upp
SRC=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$DEST"
if [ "$SRC" != "$DEST" ]; then
  cp -a "$SRC/schema.sql" "$SRC/sync.py" "$SRC/checksum_accounts_mail.py" "$SRC/README.md" "$DEST/"
fi
chmod 755 "$DEST/sync.py" "$DEST/checksum_accounts_mail.py"
touch /root/secrets/upp.token
chmod 600 /root/secrets/upp.token
# every 15 minutes; no-op until /root/secrets/upp.token has a JWT
CRON_LINE='*/15 * * * * UPP_DB=/root/gowifi-upp/upp.db /usr/bin/python3 /root/gowifi-upp/sync.py >> /var/log/gowifi-upp-sync.log 2>&1'
(crontab -l 2>/dev/null | grep -v gowifi-upp-sync.py || true; echo "$CRON_LINE") | crontab -
echo "installed $DEST"
