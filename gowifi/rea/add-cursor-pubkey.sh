#!/bin/bash
# Append a Cursor/Mac SSH public key for the isolated `rea` user on the GoWifi box.
# Does not change production users, nginx, or services.
#
# Usage (from a machine that can SSH as root):
#   ssh root@box.gowifi.co.za 'bash -s' < add-cursor-pubkey.sh
#   # or, after copying a .pub file to the box:
#   REA_SSH_PUBKEY="$(cat ~/.ssh/id_ed25519.pub)" bash add-cursor-pubkey.sh
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run as root on the GoWifi box" >&2; exit 1; }
[ -n "${REA_SSH_PUBKEY:-}" ] || { echo "set REA_SSH_PUBKEY to a single ssh public-key line" >&2; exit 1; }

auth=/opt/rea/.ssh/authorized_keys
mkdir -p /opt/rea/.ssh
chmod 700 /opt/rea/.ssh
touch "$auth"
chmod 600 "$auth"
if grep -Fqx "$REA_SSH_PUBKEY" "$auth"; then
  echo "key already present"
else
  printf '%s\n' "$REA_SSH_PUBKEY" >> "$auth"
  echo "key added"
fi
chown -R rea:rea /opt/rea/.ssh
