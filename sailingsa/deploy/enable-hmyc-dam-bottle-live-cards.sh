#!/usr/bin/env bash
# Enable Dart-identical HMYC Wind / Media / Live Cam cards on Dam Bottle Sprints.
# Does NOT upload or replace live api.py (Master/Gold lock).
set -euo pipefail

SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
RID="2026-10-10-hmyc-dam-bottle-sprints"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOOT_SRC="$SCRIPT_DIR/../frontend/js/hmyc-dam-bottle-live-boot.js"
PATCH_SRC="$SCRIPT_DIR/patch_hmyc_dam_bottle_live_cards.py"
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

if [ ! -f "$BOOT_SRC" ] || [ ! -f "$PATCH_SRC" ]; then
  echo "ERROR: missing $BOOT_SRC or $PATCH_SRC"
  exit 1
fi

echo "=== 1) Backup live JS (no api.py) ==="
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="/root/backups/hmyc-dam-bottle-live-cards-${STAMP}"
mkdir -p "$DEST"
for f in \
  /var/www/sailingsa/js/midmar-live-media.js \
  /var/www/sailingsa/js/midmar-leaderboard.js \
  /var/www/sailingsa/js/midmar-media-rotate.js \
  /var/www/sailingsa/js/club-score-edit.js \
  /var/www/sailingsa/js/mm-lipton-reels-card.js \
  /var/www/sailingsa/js/regatta-pdf-share.js
do
  cp -a "$f" "$DEST/"
done
echo "backup $DEST"
sha256sum /var/www/sailingsa/api/api.py
REMOTE

echo "=== 2) Boot script ==="
"${SCP[@]}" "$BOOT_SRC" "root@${SERVER}:${WEB_ROOT}/js/hmyc-dam-bottle-live-boot.js"
"${SSH[@]}" "root@${SERVER}" "cp -a '${WEB_ROOT}/js/hmyc-dam-bottle-live-boot.js' '${WEB_ROOT}/frontend/js/hmyc-dam-bottle-live-boot.js' 2>/dev/null || true; chown www-data:www-data '${WEB_ROOT}/js/hmyc-dam-bottle-live-boot.js'"

echo "=== 2b) ET + corrected-time store (not api.py) ==="
"${SSH[@]}" "root@${SERVER}" "mkdir -p /opt/hmyc-dam-bottle-et /var/www/sailingsa/assets"
"${SCP[@]}" "$SCRIPT_DIR/hmyc_dam_bottle_et_store.py" "root@${SERVER}:/opt/hmyc-dam-bottle-et/store.py"
"${SCP[@]}" "$SCRIPT_DIR/hmyc-dam-bottle-et.service" "root@${SERVER}:/etc/systemd/system/hmyc-dam-bottle-et.service"
"${SCP[@]}" "$SCRIPT_DIR/hmyc-dam-bottle-et.nginx.conf" "root@${SERVER}:/etc/nginx/snippets/hmyc-dam-bottle-et.conf"
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
chmod 755 /opt/hmyc-dam-bottle-et/store.py
chown -R www-data:www-data /opt/hmyc-dam-bottle-et
if ! grep -q "hmyc-dam-bottle-et.conf" /etc/nginx/snippets/sailingsa-soft404.conf; then
  cp -a /etc/nginx/snippets/sailingsa-soft404.conf "/root/backups/sailingsa-soft404.conf.$(date +%Y%m%d_%H%M%S)"
  printf "\n# Dam Bottle ET + corrected times (not api.py)\ninclude /etc/nginx/snippets/hmyc-dam-bottle-et.conf;\n" >> /etc/nginx/snippets/sailingsa-soft404.conf
  echo "soft404 include added"
fi
systemctl daemon-reload
systemctl enable --now hmyc-dam-bottle-et.service
systemctl is-active hmyc-dam-bottle-et.service
nginx -t
systemctl reload nginx
REMOTE

echo "=== 3) Add Dam Bottle slug to existing HMYC card JS ==="
"${SCP[@]}" "$PATCH_SRC" "root@${SERVER}:/tmp/patch_hmyc_dam_bottle_live_cards.py"
"${SSH[@]}" "root@${SERVER}" "python3 /tmp/patch_hmyc_dam_bottle_live_cards.py"

echo "=== 4) Gold lock + page check (no API restart) ==="
"${SSH[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
HASH=$(sha256sum /var/www/sailingsa/api/api.py | awk '{print $1}')
test "$HASH" = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"
test "$(stat -c %s /var/www/sailingsa/api/api.py)" = "3953427"
echo "gold api.py unchanged"
chown www-data:www-data \
  /var/www/sailingsa/js/midmar-live-media.js \
  /var/www/sailingsa/js/midmar-leaderboard.js \
  /var/www/sailingsa/js/club-score-edit.js \
  /var/www/sailingsa/js/mm-lipton-reels-card.js \
  /var/www/sailingsa/js/regatta-pdf-share.js \
  /var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js
REMOTE

curl -sS -o /tmp/dam-bottle.html -w "DAM HTTP %{http_code} bytes %{size_download}\n" \
  "https://sailingsa.co.za/regatta/${RID}"
curl -sS -o /dev/null -w "DART HTTP %{http_code}\n" \
  "https://sailingsa.co.za/regatta/2026-09-24-hmyc-dart-18-nationals"
curl -sS -o /dev/null -w "HYC HTTP %{http_code}\n" \
  "https://sailingsa.co.za/club/hyc"
curl -sS -o /dev/null -w "HOME HTTP %{http_code}\n" \
  "https://sailingsa.co.za/"
curl -sS "https://sailingsa.co.za/js/hmyc-dam-bottle-live-boot.js?v=dbs38" | head -c 200 || true
echo
python3 - <<'PY'
from pathlib import Path
h = Path("/tmp/dam-bottle.html").read_text(encoding="utf-8", errors="replace")
for n in ("Dam Bottle Sprints", "Dam-Bottle-Sprints.png", "regatta-pdf-share.js"):
    print(n, "OK" if n in h else "MISSING")
PY

echo ""
echo "Audit: https://sailingsa.co.za/regatta/${RID}"
echo "api.py was not restarted or replaced."
