#!/usr/bin/env bash
# BLOCKED. This script used to scp this GitHub repo api.py over live and
# brought back the 4–5 month EVENTS/SAILORS club layout.
#
# Live api.py is Master/Gold only:
#   /root/backups/API_MASTER_GOLD/api.py
#   sha256 9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b
#   3953427 bytes
#
# See docs/API_MASTER_GOLD.md (PR for lock: cursor/api-master-gold-lock-a65f).
# HMYC Dev must be a new file or thin route beside gold — never replace
# /var/www/sailingsa/api/api.py with this repo.
set -euo pipefail

echo "BLOCKED: deploy-hmyc-club-event-dev.sh will not upload this repo api.py."
echo "Live is Master/Gold only. See docs/API_MASTER_GOLD.md"
echo "Restore if needed:"
echo "  cp /root/backups/API_MASTER_GOLD/api.py /var/www/sailingsa/api/api.py"
exit 1
