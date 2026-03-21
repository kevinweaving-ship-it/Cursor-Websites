#!/bin/bash
# Run ON THE SERVER at /root/deploy_api_verified.sh
# One-time: scp sailingsa/deploy/deploy_api_verified.sh root@102.218.215.253:/root/deploy_api_verified.sh && ssh ... chmod +x /root/deploy_api_verified.sh
#
# Expects: /root/incoming/api.py already updated (scp from project root).
# Copies to /var/www/sailingsa/api/api.py, restarts API, prints hashes/timestamp/process/version.

set -e

INCOMING=/root/incoming/api.py
LIVE=/var/www/sailingsa/api/api.py

echo "===== DEPLOY START ====="
date

if [ ! -f "$INCOMING" ]; then
  echo "ERROR: $INCOMING not found. Run: scp api.py root@server:/root/incoming/api.py"
  exit 1
fi

echo "Incoming file:"
ls -lh "$INCOMING"

echo "Hash incoming:"
sha256sum "$INCOMING"

echo "Removing immutable flag (if set)"
chattr -i "$LIVE" 2>/dev/null || true

echo "Live hash BEFORE:"
sha256sum "$LIVE" 2>/dev/null || true

echo "Copy new API"
cp "$INCOMING" "$LIVE"

INCOMING_H=/root/incoming/regatta_host_code.py
LIVE_H=/var/www/sailingsa/api/regatta_host_code.py
if [ -f "$INCOMING_H" ]; then
  echo "Copy regatta_host_code.py (host club code helper)"
  cp "$INCOMING_H" "$LIVE_H"
  chown www-data:www-data "$LIVE_H" 2>/dev/null || true
fi

echo "Live hash AFTER:"
sha256sum "$LIVE"

echo "Restart API"
systemctl restart sailingsa-api

sleep 2

echo "Service status:"
systemctl status sailingsa-api --no-pager || true

echo "Checking live API file timestamp:"
ls -lh "$LIVE"

echo "Running process info:"
ps aux | grep sailingsa-api | grep -v grep || true

echo "Checking API version endpoint:"
curl -s "https://sailingsa.co.za/admin/api/version" || true

echo "===== DEPLOY COMPLETE ====="
