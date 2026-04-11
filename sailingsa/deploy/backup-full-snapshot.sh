#!/usr/bin/env bash
# Full point-in-time copy of defined paths (entire trees). Use when you need
# restore to match *exactly* what was on disk — not only "git dirty" files.
#
# Usage (from project root):
#   bash sailingsa/deploy/backup-full-snapshot.sh
#
# Override paths (space-separated):
#   BACKUP_FULL_SCOPE="api.py sailingsa/frontend" bash sailingsa/deploy/backup-full-snapshot.sh
#
# Creates: backups/full_snapshot_YYYYMMDD_HHMMSS/ mirroring those paths + _SNAPSHOT_META.txt
#
# Restore (destructive — removes target paths then copies from snapshot):
#   bash sailingsa/deploy/restore-full-snapshot.sh backups/full_snapshot_YYYYMMDD_HHMMSS

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="backups/full_snapshot_${STAMP}"
mkdir -p "$DEST"

# Default: hub / landing scope + API (adjust as needed)
SCOPE_STR="${BACKUP_FULL_SCOPE:-api.py sailingsa/frontend sailingsa/utils sailingsa/deploy docs}"
read -r -a SCOPE <<< "$SCOPE_STR"

N=0
for p in "${SCOPE[@]}"; do
  [ -z "$p" ] && continue
  if [ -e "$p" ]; then
    mkdir -p "$DEST/$(dirname "$p")"
    cp -a "$p" "$DEST/$p"
    N=$((N + 1))
  fi
done

{
  echo "full_snapshot_${STAMP}"
  echo "created_at_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host_pwd=$ROOT"
  echo "--- git ---"
  git rev-parse HEAD 2>/dev/null || true
  git status 2>/dev/null || true
  echo "--- scope ---"
  echo "$SCOPE_STR"
} > "$DEST/_SNAPSHOT_META.txt"

echo "Full snapshot: $N path(s) -> $DEST"
echo "$DEST"
