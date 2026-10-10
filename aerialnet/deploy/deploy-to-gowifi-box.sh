#!/bin/bash
# Copy this aerialnet keypad tree onto box.gowifi.co.za and install.
set -euo pipefail
BOX="${GOWIFI_BOX:-root@102.209.119.186}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
SSH=(ssh -o StrictHostKeyChecking=accept-new)
SCP=(scp -o StrictHostKeyChecking=accept-new)
if [ -n "${GOWIFI_SSH_KEY:-}" ]; then
  SSH+=(-i "$GOWIFI_SSH_KEY")
  SCP+=(-i "$GOWIFI_SSH_KEY")
fi
if [ -n "${SSHPASS:-}" ] && command -v sshpass >/dev/null; then
  SSH=(sshpass -e "${SSH[@]}")
  SCP=(sshpass -e "${SCP[@]}")
fi

echo "copy $SRC -> $BOX:/root/aerialnet-keypads"
"${SSH[@]}" "$BOX" "mkdir -p /root/aerialnet-keypads"
"${SCP[@]}" -r \
  "$SRC/hansekop" \
  "$SRC/voelklip" \
  "$SRC/arial" \
  "$SRC/api" \
  "$SRC/deploy" \
  "$BOX:/root/aerialnet-keypads/"
"${SSH[@]}" "$BOX" "bash /root/aerialnet-keypads/deploy/install-on-gowifi-box.sh"
