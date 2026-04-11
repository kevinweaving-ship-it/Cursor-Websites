#!/bin/bash
# Daily sitemap rebuild for cron. Loads DB_URL from sailingsa-api systemd environment.
# Uses API venv (psycopg2). Does not change sitemap XML logic — calls utils.sitemap_builder.build_sitemap only.
set -euo pipefail
umask 022

WEB_ROOT="${SAILINGS_WEB_ROOT:-/var/www/sailingsa}"
PY="${SAILINGS_VENV_PYTHON:-$WEB_ROOT/api/venv/bin/python3}"
INDEX_OUT="${SITEMAP_OUTPUT:-$WEB_ROOT/sitemap.xml}"

if [[ ! -x "$PY" ]]; then
  echo "[$(date -Is)] ERROR: venv python not found: $PY" >&2
  exit 1
fi

EV=$(systemctl show sailingsa-api -p Environment --value 2>/dev/null || true)
export DB_URL=$(echo "$EV" | tr ' ' '\n' | sed -n 's/^DB_URL=//p' | head -1)
if [[ -z "${DB_URL:-}" ]]; then
  echo "[$(date -Is)] ERROR: DB_URL not set (check sailingsa-api systemd Environment)" >&2
  exit 1
fi

export PYTHONPATH="$WEB_ROOT"
export SAILINGS_WEB_ROOT="$WEB_ROOT"
export SITEMAP_OUTPUT="$INDEX_OUT"
export BASE_URL="${BASE_URL:-https://sailingsa.co.za}"

echo "[$(date -Is)] sitemap refresh start → $INDEX_OUT"

"$PY" - <<'PY'
import os
import sys
import psycopg2

sys.path.insert(0, os.environ["PYTHONPATH"])

from utils.sitemap_builder import build_sitemap

out = os.environ["SITEMAP_OUTPUT"]
base = os.environ.get("BASE_URL", "https://sailingsa.co.za")

conn = psycopg2.connect(os.environ["DB_URL"])
try:
    stats = build_sitemap(conn, output_path=out, base_url=base)
    if not stats or not stats.get("ok"):
        print("[sitemap] build_sitemap returned failure", file=sys.stderr)
        sys.exit(1)
    print("[sitemap] OK total_urls=%s files=%s" % (stats.get("total_urls"), stats.get("by_file")))
finally:
    conn.close()
PY

# Nginx serves files as www-data
chown www-data:www-data "$WEB_ROOT"/sitemap.xml "$WEB_ROOT"/sitemap-*.xml 2>/dev/null || true

echo "[$(date -Is)] sitemap refresh done"
