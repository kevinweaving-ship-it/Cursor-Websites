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
p = "/etc/systemd/system/sailingsa-api.service"
text = open(p, encoding="utf-8", errors="replace").read()
m = re.search(r"(?im)^Environment=DB_URL=(.+)$", text)
if not m:
    m = re.search(r"(?im)^Environment=DATABASE_URL=(.+)$", text)
if not m:
    raise SystemExit("DB_URL not in sailingsa-api.service")
print(m.group(1).strip().strip('"').strip("'"))
PY
)"
export DB_URL
echo "=== WRITE official R1-R7 ==="
python3 /root/lipton_r7_official_update.py
echo "=== RECHECK ==="
python3 /root/lipton_r7_official_update.py --check
