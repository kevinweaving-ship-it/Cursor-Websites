#!/bin/bash
# Apply official Lipton 2026 R1–R7 scores to live results table.
set -euo pipefail
SRC="/tmp/lipton_r7_official_update.py"
if [[ ! -f "$SRC" ]]; then
  echo "MISSING $SRC"
  exit 1
fi
cp "$SRC" /root/lipton_r7_official_update.py
DB_URL="$(python3 - <<'PY'
import re
from pathlib import Path

def clean(v: str) -> str:
    return v.strip().strip('"').strip("'")

candidates = [
    Path("/var/www/sailingsa/.env"),
    Path("/etc/systemd/system/sailingsa-api.service"),
    Path("/root/.env"),
]
for p in candidates:
    if not p.is_file():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Environment="):
            s = s.split("=", 1)[1]
            s = clean(s)
        if s.startswith("DB_URL=") or s.startswith("DATABASE_URL="):
            print(clean(s.split("=", 1)[1]))
            raise SystemExit(0)
print("postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master")
PY
)"
export DB_URL
echo "DB_URL host=$(python3 - <<'PY'
import os
from urllib.parse import urlparse
u = urlparse(os.environ["DB_URL"])
print(f"{u.hostname}:{u.port}/{u.path.lstrip('/')}")
PY
)"
echo "=== BEFORE ==="
psql "$DB_URL" -c "SELECT rank, sail_number, club_raw, races_sailed, nett_points_raw, race_scores FROM results WHERE regatta_id='2026-08-29-lipton-challenge-cup' ORDER BY rank;"
echo "=== WRITE official R1-R7 ==="
python3 /root/lipton_r7_official_update.py
echo "=== RECHECK ==="
python3 /root/lipton_r7_official_update.py --check
