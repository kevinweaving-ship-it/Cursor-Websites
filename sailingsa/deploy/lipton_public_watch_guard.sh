#!/bin/bash
# Restore stubbed or stale Lipton public-URL watchdog copies, then run one.
set -euo pipefail
MARKER="LIPTON_WATCH_DEBOUNCE_V1"
COPIES=(
  /usr/local/lib/lipton_public_not_dev_watch.py
  /var/lib/sailingsa-lipton/watch.py
  /usr/local/sbin/lipton_public_not_dev_watch.py
)
GOLDS=(
  /root/lw-gold4.py
  /root/lw-gold3.py
  /root/lw-gold.py
  /root/lipton_public_not_dev_watch.py
  /var/lib/sailingsa-lipton/watch.py.gold
)

is_good() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  local sz
  sz=$(wc -c < "$f" | tr -d ' ')
  [[ "$sz" -gt 500 ]] || return 1
  grep -q "$MARKER" "$f"
}

good=""
for f in "${GOLDS[@]}" "${COPIES[@]}"; do
  if is_good "$f"; then
    good=$f
    break
  fi
done
if [[ -z "$good" ]]; then
  echo "lipton watch: no good copy" >&2
  exit 1
fi
for f in "${COPIES[@]}"; do
  if ! is_good "$f"; then
    chattr -i "$f" 2>/dev/null || true
    mkdir -p "$(dirname "$f")"
    cp "$good" "$f"
    chmod 755 "$f"
    chattr +i "$f" 2>/dev/null || true
  fi
done
exec /usr/bin/python3 "$good" "$@"
