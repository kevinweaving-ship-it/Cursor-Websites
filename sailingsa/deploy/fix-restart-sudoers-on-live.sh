#!/usr/bin/env bash
# Run this script ON THE LIVE SERVER after SSH (as root).
# Fixes sudo so the sailingsa-api service user can run: systemctl restart sailingsa-api
#
# Usage on server:
#   bash /path/to/fix-restart-sudoers-on-live.sh
#
# Or from your machine (piped over SSH):
#   ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 'bash -s' < sailingsa/deploy/fix-restart-sudoers-on-live.sh

set -e
LIVE_HOST="vm103zuex.yourlocaldomain.com"

echo "=== 1. Confirm hostname ==="
H=$(hostname)
echo "hostname: $H"
if [ "$H" != "$LIVE_HOST" ]; then
  echo "ERROR: hostname must be $LIVE_HOST. Aborting."
  exit 1
fi

echo ""
echo "=== 2. Service user ==="
SERVICE_USER=$(systemctl show -p User sailingsa-api --value)
echo "Service user: $SERVICE_USER"

echo ""
echo "=== 3. Create sudoers entry ==="
echo "${SERVICE_USER} ALL=NOPASSWD: /bin/systemctl restart sailingsa-api" > /etc/sudoers.d/sailingsa-api
echo "Created /etc/sudoers.d/sailingsa-api"

echo ""
echo "=== 4. Permissions ==="
chmod 440 /etc/sudoers.d/sailingsa-api
ls -la /etc/sudoers.d/sailingsa-api

echo ""
echo "=== 5. Test: sudo -u $SERVICE_USER sudo systemctl restart sailingsa-api ==="
sudo -u "$SERVICE_USER" sudo systemctl restart sailingsa-api
sleep 2

echo ""
echo "=== 6. Verify PID change ==="
echo "MainPID now:"
systemctl show -p MainPID sailingsa-api --value

echo ""
echo "=== REPORT ==="
echo "Service user: $SERVICE_USER"
echo "Run again to confirm PID changes after another restart:"
echo "  systemctl show -p MainPID sailingsa-api --value"
echo "  sudo systemctl restart sailingsa-api"
echo "  systemctl show -p MainPID sailingsa-api --value"
echo "Done."
