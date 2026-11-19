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
if grep -q '_fleet_label_to_catalogue_class_name' "$API" && ! grep -q '_fleet_label_to_catalogue_class_name' "$IN"; then
  echo "REFUSE: incoming api.py is not the production lineage. Live api.py will not be replaced."
  if [ ! -f /root/ilca4_keep_live_api.sh ]; then
    echo "ERROR: /root/ilca4_keep_live_api.sh is missing. Upload sailingsa/deploy/ilca4_keep_live_api.sh first."
    chattr +i $API
    exit 1
  fi
  # shellcheck source=/dev/null
  source /root/ilca4_keep_live_api.sh
  rc=0
  ilca4_preserve_live "$API" || rc=$?
  chattr +i $API 2>/dev/null || true
  if [ "$rc" = 10 ]; then
    systemctl restart sailingsa-api
    systemctl is-active sailingsa-api
    exit 0
  fi
  if [ "$rc" != 0 ]; then
    exit "$rc"
  fi
  echo "Live production api.py left unchanged. No restart."
  exit 0
fi
cp $IN $API
chown www-data:www-data $API
chattr +i $API
# Optional helper next to api.py (host club code sync); same incoming pattern as api.py
INH="/root/incoming/regatta_host_code.py"
if [ -f "$INH" ]; then
  cp "$INH" "$(dirname "$API")/regatta_host_code.py"
  chown www-data:www-data "$(dirname "$API")/regatta_host_code.py" || true
fi
INI="/root/incoming/ilca4_canonical.py"
if [ -f "$INI" ]; then
  cp "$INI" "$(dirname "$API")/ilca4_canonical.py"
  chown www-data:www-data "$(dirname "$API")/ilca4_canonical.py" || true
fi
systemctl restart sailingsa-api
systemctl is-active sailingsa-api
