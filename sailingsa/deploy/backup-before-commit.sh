#!/usr/bin/env bash
# Backup changed files before commit. Run from project root.
# Usage: bash sailingsa/deploy/backup-before-commit.sh
# Creates backups/pre_commit_YYYYMMDD_HHMMSS/ with copies of modified + staged files.

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="backups/pre_commit_${STAMP}"
mkdir -p "$DEST"

# Modified and staged files (tracked by git)
COUNT=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if [ -f "$f" ]; then
    mkdir -p "$DEST/$(dirname "$f")"
    cp "$f" "$DEST/$f" 2>/dev/null || true
    COUNT=$((COUNT + 1))
  fi
done < <(git status --porcelain | awk '{print $2}' | grep -v '^$' || true)

if [ "$COUNT" -eq 0 ]; then
  echo "No changed files to backup."
  exit 0
fi
echo "Backup: $COUNT file(s) -> $DEST"
echo "$DEST"
