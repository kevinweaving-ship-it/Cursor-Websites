#!/usr/bin/env bash
# Patch Dam Bottle Event Reels + WhatsApp history backfill. Does NOT replace api.py.
set -euo pipefail

SERVER="102.218.215.253"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SSH_OPTS=(-o StrictHostKeyChecking=no)
SSH=(ssh "${SSH_OPTS[@]}")
SCP=(scp "${SSH_OPTS[@]}")
if [ -f "$KEY" ]; then
  SSH_OPTS+=(-i "$KEY")
  SSH=(ssh "${SSH_OPTS[@]}")
  SCP=(scp "${SSH_OPTS[@]}")
elif [ -n "${SSHPASS:-}" ]; then
  SSH=(sshpass -e ssh "${SSH_OPTS[@]}")
  SCP=(sshpass -e scp "${SSH_OPTS[@]}")
fi

echo "=== backup (no api.py) ==="
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="/root/backups/hmyc-dam-bottle-media-backfill-${STAMP}"
mkdir -p "$DEST"
cp -a /opt/arial-whatsapp-poc/event_group_archive.js \
      /opt/arial-whatsapp-poc/poc.js \
      /var/www/sailingsa/js/mm-lipton-reels-card.js \
      /var/www/sailingsa/js/midmar-live-media.js \
      /var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js \
      /var/www/sailingsa/js/regatta-pdf-share.js \
      "$DEST/"
echo "backup $DEST"
sha256sum /var/www/sailingsa/api/api.py
REMOTE

echo "=== upload + patch ==="
"${SCP[@]}" "$SCRIPT_DIR/patch_hmyc_dam_bottle_media_backfill.py" \
  "$SCRIPT_DIR/whatsapp-event/event_group_archive.js" \
  "$SCRIPT_DIR/../frontend/js/hmyc-dam-bottle-live-boot.js" \
  "root@${SERVER}:/tmp/"
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
cp -a /tmp/event_group_archive.js /opt/arial-whatsapp-poc/event_group_archive.js
cp -a /tmp/hmyc-dam-bottle-live-boot.js /var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js
cp -a /tmp/hmyc-dam-bottle-live-boot.js /var/www/sailingsa/frontend/js/hmyc-dam-bottle-live-boot.js || true
python3 /tmp/patch_hmyc_dam_bottle_media_backfill.py
chown wapoc:wapoc /opt/arial-whatsapp-poc/event_group_archive.js /opt/arial-whatsapp-poc/poc.js
chown www-data:www-data \
  /var/www/sailingsa/js/mm-lipton-reels-card.js \
  /var/www/sailingsa/js/midmar-live-media.js \
  /var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js \
  /var/www/sailingsa/js/regatta-pdf-share.js
systemctl restart arial-whatsapp-poc.service event-whatsapp-ingest.service
sleep 8
systemctl is-active arial-whatsapp-poc.service event-whatsapp-ingest.service
HASH=$(sha256sum /var/www/sailingsa/api/api.py | awk '{print $1}')
test "$HASH" = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"
test "$(stat -c %s /var/www/sailingsa/api/api.py)" = "3953427"
echo gold api.py unchanged
REMOTE
echo "done"
