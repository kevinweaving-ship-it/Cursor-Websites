#!/bin/bash
# Run on LIVE via: ssh root@102.218.215.253 'bash -s' < sailingsa/deploy/live-uvicorn-diag.sh
# Or: ssh root@102.218.215.253 "$(cat sailingsa/deploy/live-uvicorn-diag.sh)"
set -e
API=/var/www/sailingsa/api/api.py

echo "=== SHA256 of api.py uvicorn uses ==="
sha256sum "$API"

echo ""
echo "=== 40 lines surrounding _format_regatta_status_line ==="
n=$(grep -n "def _format_regatta_status_line" "$API" | head -1 | cut -d: -f1)
if [ -n "$n" ]; then
  start=$((n - 20))
  [ "$start" -lt 1 ] && start=1
  end=$((start + 39))
  sed -n "${start},${end}p" "$API"
else
  echo "(not found)"
fi

echo ""
echo "=== First 60 lines of serve_regatta_standalone ==="
n=$(grep -n "def serve_regatta_standalone" "$API" | head -1 | cut -d: -f1)
if [ -n "$n" ]; then
  end=$((n + 59))
  sed -n "${n},${end}p" "$API"
else
  echo "(not found)"
fi

echo ""
echo "=== Full uvicorn process command ==="
ps aux | grep uvicorn | grep -v grep
