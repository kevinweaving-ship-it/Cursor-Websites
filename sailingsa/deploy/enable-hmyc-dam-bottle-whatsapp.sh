#!/usr/bin/env bash
# Point Dam Bottle Event Reels at the live HMYC Event Media WhatsApp ingest.
# Does NOT upload or replace live api.py (Master/Gold lock).
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

INGEST_SRC="${1:-/tmp/event_whatsapp_ingest.py}"
ARCHIVE_SRC="${2:-/tmp/event_group_archive.js}"
POC_SRC="${3:-/tmp/poc.js}"
REELS_SRC="${4:-/tmp/mm-lipton-reels-card.js}"

echo "=== 1) Backup WhatsApp ingest + reels (no api.py) ==="
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="/root/backups/hmyc-dam-bottle-whatsapp-${STAMP}"
mkdir -p "$DEST"
cp -a /opt/arial-whatsapp-poc/event_whatsapp_ingest.py \
      /opt/arial-whatsapp-poc/event_group_archive.js \
      /opt/arial-whatsapp-poc/poc.js \
      /var/www/sailingsa/js/mm-lipton-reels-card.js \
      "$DEST/"
echo "backup $DEST"
sha256sum /var/www/sailingsa/api/api.py
REMOTE

echo "=== 2) Upload patched ingest / archive / poc / reels ==="
"${SCP[@]}" "$INGEST_SRC" "root@${SERVER}:/opt/arial-whatsapp-poc/event_whatsapp_ingest.py"
"${SCP[@]}" "$ARCHIVE_SRC" "root@${SERVER}:/opt/arial-whatsapp-poc/event_group_archive.js"
"${SCP[@]}" "$POC_SRC" "root@${SERVER}:/opt/arial-whatsapp-poc/poc.js"
"${SCP[@]}" "$REELS_SRC" "root@${SERVER}:/var/www/sailingsa/js/mm-lipton-reels-card.js"
"${SSH[@]}" "root@${SERVER}" "cp -a /var/www/sailingsa/js/mm-lipton-reels-card.js /var/www/sailingsa/frontend/js/mm-lipton-reels-card.js; chown www-data:www-data /var/www/sailingsa/js/mm-lipton-reels-card.js /var/www/sailingsa/frontend/js/mm-lipton-reels-card.js; chown wapoc:wapoc /opt/arial-whatsapp-poc/event_group_archive.js /opt/arial-whatsapp-poc/poc.js; chown root:root /opt/arial-whatsapp-poc/event_whatsapp_ingest.py"

echo "=== 3) Register HMYC Event Media for Dam Bottle ==="
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
DB_URL=$(grep -E 'Environment="DB_URL=' /etc/systemd/system/sailingsa-api.service | head -1 | sed -E 's/Environment="DB_URL=//; s/"$//')
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO public.event_whatsapp_groups (
  event_id, regatta_id, event_name_snapshot,
  group_jid, group_invite_url, group_name,
  display_number, monitor_number,
  valid_from, valid_until, is_current, notes
)
SELECT
  234806,
  '2026-10-10-hmyc-dam-bottle-sprints',
  'Dam Bottle Sprints',
  NULL,
  NULL,
  'HMYC Event Media',
  '27762639937',
  '27762639937',
  DATE '2026-10-10',
  DATE '2026-10-12',
  true,
  'Lookout group HMYC Event Media. Bind JID when SailingSA monitor is in the group. Photos/videos go to Event Reels.'
WHERE NOT EXISTS (
  SELECT 1 FROM public.event_whatsapp_groups
  WHERE is_current AND regatta_id = '2026-10-10-hmyc-dam-bottle-sprints'
);

UPDATE public.events
SET extras = COALESCE(extras, '{}'::jsonb) || jsonb_build_object(
  'whatsapp', jsonb_build_object(
    'display_number', '27762639937',
    'monitor_number', '27762639937',
    'group_name', 'HMYC Event Media',
    'valid_from', '2026-10-10',
    'valid_until', '2026-10-12',
    'active_only_when_live', true
  )
)
WHERE event_id = 234806
  AND (extras->'whatsapp') IS NULL;

SELECT event_whatsapp_id, regatta_id, group_name, group_jid, valid_from, valid_until
FROM public.event_whatsapp_groups
WHERE regatta_id = '2026-10-10-hmyc-dam-bottle-sprints';
SQL
mkdir -p /var/www/sailingsa/assets/mm-clips/2026-10-10-hmyc-dam-bottle-sprints
chown www-data:www-data /var/www/sailingsa/assets/mm-clips/2026-10-10-hmyc-dam-bottle-sprints
REMOTE

echo "=== 4) Restart ingest + WhatsApp watcher (refresh groups) ==="
"${SSH[@]}" "root@${SERVER}" 'systemctl restart event-whatsapp-ingest.service; systemctl restart arial-whatsapp-poc.service; sleep 8; systemctl is-active event-whatsapp-ingest.service arial-whatsapp-poc.service'

echo "=== 5) Gold lock ==="
"${SSH[@]}" "root@${SERVER}" 'HASH=$(sha256sum /var/www/sailingsa/api/api.py | awk "{print \$1}"); test "$HASH" = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"; test "$(stat -c %s /var/www/sailingsa/api/api.py)" = "3953427"; echo gold api.py unchanged'

echo "Audit: https://sailingsa.co.za/regatta/2026-10-10-hmyc-dam-bottle-sprints"
echo "api.py was not restarted or replaced."
