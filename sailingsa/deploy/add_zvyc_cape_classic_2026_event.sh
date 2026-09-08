#!/usr/bin/env bash
# Upsert ZVYC Cape Classic 12–13 Sep 2026 into events + parent regatta
# /regatta/2026-09-13-zvyc-cape-classic (SAS listing pending).
# Live:
#   bash /var/www/sailingsa/deploy/add_zvyc_cape_classic_2026_event.sh --on-server
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ON_SERVER=false
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --on-server) ON_SERVER=true ;;
    --dry-run) DRY_RUN=true ;;
  esac
done

if [ -n "${DB_URL:-}" ]; then
  export DB_URL
elif [ -n "${DATABASE_URL:-}" ]; then
  export DB_URL="$DATABASE_URL"
elif [ "$ON_SERVER" = true ]; then
  export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
fi

if [ -z "${DB_URL:-}" ] && [ "$DRY_RUN" != true ]; then
  echo "ERROR: Set DB_URL or DATABASE_URL, or pass --on-server on the live host." >&2
  exit 1
fi

PY_ARGS=()
[ "$DRY_RUN" = true ] && PY_ARGS+=(--dry-run)
exec python3 "$SCRIPT_DIR/add_zvyc_cape_classic_2026_event.py" "${PY_ARGS[@]}"
