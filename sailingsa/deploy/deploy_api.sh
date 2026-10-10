#!/bin/bash
# Run ON THE SERVER (e.g. /root/deploy_api.sh).
# Copies api.py from /root/incoming/api.py to live, with backup and immutable handling.
set -e
API="/var/www/sailingsa/api/api.py"
BACK="/root/backups"
IN="/root/incoming/api.py"

# MASTER/GOLD lock — refuse stale/repo api.py (old EVENTS/SAILORS club layout)
if [ -f /root/backups/API_MASTER_GOLD/refuse_stale_incoming_api.sh ]; then
  . /root/backups/API_MASTER_GOLD/refuse_stale_incoming_api.sh
  if ! refuse_stale_incoming_api "$IN"; then
    exit 1
  fi
fi

# Do NOT write dated api.py.$TS copies. Those became restore bait.
# The only allowed restore is /root/backups/API_MASTER_GOLD/api.py
mkdir -p $BACK
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
