#!/usr/bin/env bash
# Backup changed files before commit. Run from project root.
# Usage: bash sailingsa/deploy/backup-before-commit.sh
# Creates backups/pre_commit_YYYYMMDD_HHMMSS/ with copies of every path that
# differs from HEAD (modified/staged) plus untracked files — not only a broken
# awk on porcelain (fixes paths with spaces; includes all dirty files).
#
# For a *complete tree* copy of hub/API/frontend (true point-in-time, restore
# without stray new files under those dirs), use:
#   bash sailingsa/deploy/backup-full-snapshot.sh

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="backups/pre_commit_${STAMP}"
mkdir -p "$DEST"

COUNT=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if [ -f "$f" ]; then
    mkdir -p "$DEST/$(dirname "$f")"
    cp -f "$f" "$DEST/$f" 2>/dev/null || true
    COUNT=$((COUNT + 1))
  elif [ -d "$f" ]; then
    mkdir -p "$DEST/$(dirname "$f")"
    cp -a "$f" "$DEST/$f" 2>/dev/null || true
    COUNT=$((COUNT + 1))
  fi
done < <(
  {
    git diff --name-only HEAD
    git ls-files -o --exclude-standard
  } | sort -u
)

if [ "$COUNT" -eq 0 ]; then
  echo "No changed files to backup."
  exit 0
fi

{
  echo "pre_commit_${STAMP}"
  echo "created_at_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git rev-parse HEAD 2>/dev/null || true
  git status -sb 2>/dev/null || true
} >"$DEST/_PRE_COMMIT_META.txt"

echo "Backup: $COUNT path(s) -> $DEST"
echo "$DEST"
