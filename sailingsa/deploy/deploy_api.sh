#!/bin/bash
# Run ON THE SERVER (e.g. /root/deploy_api.sh).
# Copies api.py from /root/incoming/api.py to live, with backup and immutable handling.
set -e
API="/var/www/sailingsa/api/api.py"
BACK="/root/backups"
IN="/root/incoming/api.py"
TS=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACK
cp $API $BACK/api.py.$TS
chattr -i $API
cp $IN $API
chown www-data:www-data $API
chattr +i $API
# Optional helper next to api.py (host club code sync); same incoming pattern as api.py
INH="/root/incoming/regatta_host_code.py"
if [ -f "$INH" ]; then
  cp "$INH" "$(dirname "$API")/regatta_host_code.py"
  chown www-data:www-data "$(dirname "$API")/regatta_host_code.py" || true
fi
systemctl restart sailingsa-api
systemctl is-active sailingsa-api
