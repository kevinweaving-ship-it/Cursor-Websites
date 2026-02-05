#!/usr/bin/env bash
# Auto-snapshot: zip entire project with timestamp. Store OUTSIDE project directory.
# No IDE dependency — run from terminal or cron.
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SNAPSHOT_BASE="${SNAPSHOT_BASE:-$(dirname "$PROJECT_ROOT")}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-$SNAPSHOT_BASE/snapshots}"
mkdir -p "$SNAPSHOT_DIR"
ZIP_NAME="${PROJECT_NAME}_snapshot_${TIMESTAMP}.zip"
ZIP_PATH="$SNAPSHOT_DIR/$ZIP_NAME"
(cd "$(dirname "$PROJECT_ROOT")" && zip -r "$ZIP_PATH" "$PROJECT_NAME" -x "*.git/*" -x "*node_modules/*" -x "*__pycache__/*" -x "*.pyc" -x "*.zip")
echo "Snapshot: $ZIP_PATH"
