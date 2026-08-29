#!/bin/bash
# Rewrite STATUS every 60s and scp to live. Phone: cat /root/lipton-vakaros-archive/STATUS.txt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
while true; do
  python3 "$ROOT/sailingsa/scripts/lipton_archive_status.py" || true
  expect "$ROOT/sailingsa/deploy/push-lipton-archive-status.exp" || true
  sleep 60
done
