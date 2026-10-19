#!/bin/bash
# Unattended Monday job: cluster the weekend, write articles, PDF, cards, publish.
set -euo pipefail
ROOT="${1:-/opt/rea/work/sailing-roundup}"
PY="$ROOT/.venv/bin/python3"
[ -x "$PY" ] || PY=python3
cd "$ROOT"
"$PY" "$ROOT/app/publish_weekend.py" --test-weekend
if [ -x "$ROOT/deploy/publish-to-sailingsa.sh" ]; then
  "$ROOT/deploy/publish-to-sailingsa.sh" "$ROOT/public" || true
fi
echo "monday-job done"
