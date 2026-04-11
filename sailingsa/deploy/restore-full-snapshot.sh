#!/usr/bin/env bash
# Restore from backups/full_snapshot_* created by backup-full-snapshot.sh.
# Removes each scoped path in the repo, then copies from the snapshot (100% match;
# files created after the snapshot under those paths are removed).
#
# Usage (from project root):
#   bash sailingsa/deploy/restore-full-snapshot.sh backups/full_snapshot_YYYYMMDD_HHMMSS
#
# Same BACKUP_FULL_SCOPE as when the snapshot was taken (defaults match backup script).

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SNAP="${1:?Usage: $0 backups/full_snapshot_YYYYMMDD_HHMMSS}"
if [ ! -d "$SNAP" ]; then
  echo "Not a directory: $SNAP" >&2
  exit 1
fi

SCOPE_STR="${BACKUP_FULL_SCOPE:-api.py sailingsa/frontend sailingsa/utils sailingsa/deploy docs}"
read -r -a SCOPE <<< "$SCOPE_STR"

echo "WARNING: This deletes and replaces these paths from:"
echo "  $SNAP"
echo "Paths: $SCOPE_STR"
read -r -p "Type RESTORE and press Enter: " confirm
if [ "$confirm" != "RESTORE" ]; then
  echo "Aborted."
  exit 1
fi

for p in "${SCOPE[@]}"; do
  [ -z "$p" ] && continue
  if [ -e "$SNAP/$p" ]; then
    rm -rf "$p"
    mkdir -p "$(dirname "$p")"
    cp -a "$SNAP/$p" "$p"
    echo "restored $p"
  else
    echo "skip (not in snapshot): $p"
  fi
done

echo "Done. Verify with git status and your smoke tests."
