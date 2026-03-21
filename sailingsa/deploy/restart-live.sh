#!/usr/bin/env bash
# Restart sailingsa-api on LIVE via SSH. Run from your machine (not from inside the API).
# Usage: bash sailingsa/deploy/restart-live.sh

set -e
SERVER="${SAILINGSA_SERVER:-102.218.215.253}"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"

echo "MainPID before:"
ssh -i "$KEY" -o ConnectTimeout=10 root@"$SERVER" "systemctl show -p MainPID sailingsa-api --value"

ssh -i "$KEY" -o ConnectTimeout=10 root@"$SERVER" "sudo systemctl restart sailingsa-api"
sleep 2

echo "MainPID after:"
ssh -i "$KEY" -o ConnectTimeout=10 root@"$SERVER" "systemctl show -p MainPID sailingsa-api --value"
echo "Done."
