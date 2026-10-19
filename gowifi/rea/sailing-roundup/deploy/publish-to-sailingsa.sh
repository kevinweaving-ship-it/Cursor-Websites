#!/bin/bash
# Copy the generated weekend-roundup public files onto SailingSA.
# Generation can stay on GoWifi; the public URL is https://sailingsa.co.za/sailing-roundup/
set -euo pipefail
SRC="${1:-}"
[ -n "$SRC" ] && [ -d "$SRC" ] || {
  echo "usage: $0 /path/to/sailing-roundup/public" >&2
  exit 1
}
[ -f "$SRC/issues/2026-09-28/index.html" ] || [ -f "$SRC/index.html" ] || {
  echo "no published issues in $SRC" >&2
  exit 1
}
DEST_DIR=/var/www/sailingsa/sailing-roundup
if [ -d /var/www/sailingsa ]; then
  mkdir -p "$DEST_DIR"
  rsync -az --delete \
    --exclude '.venv' \
    --exclude '__pycache__' \
    "$SRC"/ "$DEST_DIR/"
  chown -R www-data:www-data "$DEST_DIR"
  find "$DEST_DIR" -type d -exec chmod 755 {} \;
  find "$DEST_DIR" -type f -exec chmod 644 {} \;
  echo "published local $DEST_DIR"
  exit 0
fi
DEST_HOST="${SAILINGSA_SSH_HOST:-root@102.218.215.253}"
RSYNC_RSH="${RSYNC_RSH:-ssh -o StrictHostKeyChecking=no}"
ssh -o StrictHostKeyChecking=no "$DEST_HOST" "mkdir -p '$DEST_DIR' && chown www-data:www-data '$DEST_DIR'"
rsync -az --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  -e "$RSYNC_RSH" \
  "$SRC"/ "$DEST_HOST:$DEST_DIR/"
ssh -o StrictHostKeyChecking=no "$DEST_HOST" "chown -R www-data:www-data '$DEST_DIR' && find '$DEST_DIR' -type d -exec chmod 755 {} \; && find '$DEST_DIR' -type f -exec chmod 644 {} \;"
echo "published $DEST_HOST:$DEST_DIR"
