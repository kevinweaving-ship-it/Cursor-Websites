#!/bin/bash
# Rebuild drifted Monday issues to the 2026-09-28 gold default and publish them.
# Never touches 2026-09-28. Run on GoWifi as root or rea.
set -euo pipefail

ROOT="${1:-/opt/rea/work/sailing-roundup}"
PY="$ROOT/.venv/bin/python3"
[ -x "$PY" ] || PY=python3
ISSUES="${ROUNDUP_RESTYLE_ISSUES:-2026-10-05 2026-10-12 2026-10-19}"

cd "$ROOT"
for issue in $ISSUES; do
  if [ "$issue" = "2026-09-28" ]; then
    echo "skip gold default $issue"
    continue
  fi
  echo "restyle $issue"
  "$PY" "$ROOT/app/restyle_to_gold.py" --issue "$issue"
  bash "$ROOT/deploy/publish-to-sailingsa.sh" "$ROOT/public" "$issue"
done
echo "rebuilt non-gold issues: $ISSUES"
