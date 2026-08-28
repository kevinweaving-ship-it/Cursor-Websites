#!/bin/bash
# Restore stubbed Lipton public-URL watchdog copies, then run one.
set -euo pipefail
COPIES=(
  /usr/local/lib/lipton_public_not_dev_watch.py
  /var/lib/sailingsa-lipton/watch.py
  /usr/local/sbin/lipton_public_not_dev_watch.py
)
good=""
for f in "${COPIES[@]}"; do
  if [[ -f "$f" ]]; then
    sz=$(wc -c < "$f" | tr -d ' ')
    if [[ "$sz" -gt 500 ]]; then
      good=$f
      break
    fi
  fi
done
if [[ -z "$good" ]]; then
  echo "lipton watch: no good copy" >&2
  exit 1
fi
for f in "${COPIES[@]}"; do
  sz=0
  if [[ -f "$f" ]]; then
    sz=$(wc -c < "$f" | tr -d ' ')
  fi
  if [[ "$sz" -lt 500 ]]; then
    chattr -i "$f" 2>/dev/null || true
    mkdir -p "$(dirname "$f")"
    cp "$good" "$f"
    chmod 755 "$f"
    chattr +i "$f" 2>/dev/null || true
  fi
done
exec /usr/bin/python3 "$good" "$@"
