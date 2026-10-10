#!/bin/bash
# Refuse GitHub / repo / dated / undersized api.py.
# The old ~1.4MB file serves the 4–5 month EVENTS/SAILORS club layout.
# Live and restore are Master/Gold only.
#
# Usage:
#   bash sailingsa/deploy/refuse_stale_local_api.sh /path/to/api.py
#   . sailingsa/deploy/refuse_stale_local_api.sh && refuse_stale_incoming_api "$IN"
#
# On the live box the same check is /root/backups/API_MASTER_GOLD/refuse_stale_incoming_api.sh

GOLD_HASH="9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"
GOLD_MIN_BYTES=3900000
GOLD_BYTES=3953427
GOLD_PATH="/root/backups/API_MASTER_GOLD/api.py"

refuse_stale_incoming_api() {
  local incoming="$1"
  if [ -z "$incoming" ] || [ ! -f "$incoming" ]; then
    echo "REFUSED: api.py missing: ${incoming:-<empty>}"
    echo "Live API is Master/Gold only. Do not deploy this GitHub repo api.py."
    echo "Restore: cp $GOLD_PATH /var/www/sailingsa/api/api.py"
    return 1
  fi
  local bytes hash
  bytes=$(wc -c < "$incoming")
  hash=$(sha256sum "$incoming" | awk '{print $1}')
  echo "api.py check bytes=$bytes hash=$hash"
  if [ "$bytes" -lt "$GOLD_MIN_BYTES" ]; then
    echo "REFUSED: $incoming is $bytes bytes (min $GOLD_MIN_BYTES)."
    echo "That is the old GitHub/repo API (EVENTS/SAILORS club layout)."
    echo "Only Master/Gold ($GOLD_HASH, $GOLD_BYTES bytes) may be installed on live."
    echo "Restore: cp $GOLD_PATH /var/www/sailingsa/api/api.py"
    return 1
  fi
  case "$hash" in
    3c7d67404338f7bedbde33f865616c8e509af13aa184a8f193db8d8da3b6b584|\
    8788a6cd32407dc1bd4faab4a108140451d48e0ccd6ffe63ceb4d098946331ca|\
    cf6356c72d6b8a66d1ec200b4e8d3aabe998f837adbfa594fb57f0c334b8ad75)
      echo "REFUSED: $hash is a known stale GitHub/repo api.py"
      return 1
      ;;
  esac
  if [ "$hash" != "$GOLD_HASH" ] && [ "${ALLOW_API_REPLACE:-}" != "1" ]; then
    echo "REFUSED: hash $hash is not Master/Gold $GOLD_HASH"
    echo "Only Master/Gold may be installed. Do not deploy this repo api.py."
    echo "Restore: cp $GOLD_PATH /var/www/sailingsa/api/api.py"
    return 1
  fi
  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  refuse_stale_incoming_api "${1:-}"
  exit $?
fi
