#!/usr/bin/env bash
# Apply Class PY column (after Class) on live Dam Bottle parent + PDF sanitizer.
# Does not change gold api.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${LIVE_HOST:-root@102.218.215.253}"
if [[ -n "${SSHPASS:-}" ]]; then
  SSH=(sshpass -e ssh -o StrictHostKeyChecking=no "$HOST")
  SCP=(sshpass -e scp -o StrictHostKeyChecking=no)
elif [[ -f "${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}" ]]; then
  KEY="${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
  SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST")
  SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no)
else
  echo "Set SSHPASS or SSH_KEY" >&2
  exit 1
fi

"${SCP[@]}" \
  "$ROOT/sailingsa/frontend/js/hmyc-dam-bottle-live-boot.js" \
  "$HOST:/var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js"
"${SCP[@]}" \
  "$ROOT/sailingsa/backend/regatta_pdf_public_sheet.py" \
  "$HOST:/var/www/sailingsa/sailingsa/backend/regatta_pdf_public_sheet.py"

"${SSH[@]}" 'python3 - << "PY"
from pathlib import Path
p = Path("/var/www/sailingsa/js/regatta-pdf-share.js")
t = p.read_text()
t2 = t.replace("hmyc-dam-bottle-live-boot.js?v=dbs46", "hmyc-dam-bottle-live-boot.js?v=dbs48")
t2 = t2.replace("hmyc-dam-bottle-live-boot.js?v=dbs47", "hmyc-dam-bottle-live-boot.js?v=dbs48")
if "hmyc-dam-bottle-live-boot.js?v=dbs48" not in t2:
    raise SystemExit("boot cache bust failed")
p.write_text(t2)
print("boot query dbs48")
PY'

echo "Applied Class PY column files."
