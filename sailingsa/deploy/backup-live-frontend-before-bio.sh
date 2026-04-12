#!/usr/bin/env bash
# Backup live frontend (https://sailingsa.co.za/) BEFORE bio insert. Run from project root.
# Creates timestamped backup on server + proof so you can restore without breaking the whole site.
# Usage: bash sailingsa/deploy/backup-live-frontend-before-bio.sh
# Restore: see PROOF file or sailingsa/deploy/BIO_BACKUP_RESTORE.md

set -e
SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
KEY="${HOME}/.ssh/sailingsa_live_key"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="sailingsa_frontend_BEFORE_BIO_${STAMP}"
BACKUP_DIR="/root/backups/${BACKUP_NAME}"
PROOF_FILE="/root/backups/PROOF_${BACKUP_NAME}.txt"

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY"
  exit 1
fi

echo "=== 1. Create backup of $WEB_ROOT on live server ==="
ssh -i "$KEY" -o StrictHostKeyChecking=no root@${SERVER} "
  set -e
  mkdir -p /root/backups
  echo \"Copying $WEB_ROOT -> $BACKUP_DIR ...\"
  cp -a $WEB_ROOT $BACKUP_DIR
  echo \"Backup created: $BACKUP_DIR\"
"

echo "=== 2. Proof (file list + checksums of key HTML) ==="
ssh -i "$KEY" -o StrictHostKeyChecking=no root@${SERVER} "
  echo \"Backup: $BACKUP_NAME\" > $PROOF_FILE
  echo \"At: $(date -Iseconds)\" >> $PROOF_FILE
  echo \"Path: $BACKUP_DIR\" >> $PROOF_FILE
  echo \"\" >> $PROOF_FILE
  echo \"--- Key files in backup ---\" >> $PROOF_FILE
  ls -la $BACKUP_DIR/index.html $BACKUP_DIR/about.html 2>/dev/null >> $PROOF_FILE || true
  echo \"\" >> $PROOF_FILE
  echo \"--- MD5 (index.html, about.html) ---\" >> $PROOF_FILE
  md5sum $BACKUP_DIR/index.html $BACKUP_DIR/about.html 2>/dev/null >> $PROOF_FILE || true
  echo \"\" >> $PROOF_FILE
  echo \"--- Restore command (run on server as root) ---\" >> $PROOF_FILE
  echo \"  rm -rf $WEB_ROOT/* ; cp -a $BACKUP_DIR/* $WEB_ROOT/ ; chown -R www-data:www-data $WEB_ROOT ; systemctl restart sailingsa-api\" >> $PROOF_FILE
  cat $PROOF_FILE
"

echo ""
echo "=== Done ==="
echo "Backup on server: $BACKUP_DIR"
echo "Proof on server:  $PROOF_FILE"
echo ""
echo "To restore if bio insert breaks the site (run from your machine):"
echo "  ssh -i $KEY root@${SERVER} 'rm -rf $WEB_ROOT/* ; cp -a $BACKUP_DIR/* $WEB_ROOT/ ; chown -R www-data:www-data $WEB_ROOT ; systemctl restart sailingsa-api'"
echo ""
echo "Or copy backup path and run the restore command from PROOF on the server."
