#!/usr/bin/env bash
# Run from your machine before editing frontend or API (or run the remote block on the server as root).
# 1) Archives live docroot on the server
# 2) Appends local repo git status to a log file
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
KEY="${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SERVER="${BACKUP_SSH:-root@102.218.215.253}"
TS="$(date +%Y%m%d_%H%M%S)"
REMOTE_ARCHIVE="/root/backup_${TS}.tar.gz"
LOG="${PRE_CHANGE_BACKUP_LOG:-$SCRIPT_DIR/pre_change_backup.log}"

log_section() {
  {
    echo ""
    echo "=== $(date -Is) $* ==="
  } >>"$LOG"
}

if [[ -f "$KEY" ]]; then
  log_section "remote tar start -> ${SERVER}:${REMOTE_ARCHIVE}"
  ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" \
    "tar -czf ${REMOTE_ARCHIVE} /var/www/sailingsa && test -s ${REMOTE_ARCHIVE} && ls -la ${REMOTE_ARCHIVE}"
  log_section "remote tar OK"
  ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" "test -s ${REMOTE_ARCHIVE}"
  echo "Backup confirmed on server: ${REMOTE_ARCHIVE}"
else
  echo "WARN: SSH key not found at $KEY — skipping remote tar (set SSH_KEY or place sailingsa_live_key)."
fi

log_section "local git status (repo: $REPO_ROOT)"
git -C "$REPO_ROOT" status >>"$LOG"
echo "Logged git status to $LOG"
echo "Done."
