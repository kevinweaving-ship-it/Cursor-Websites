#!/bin/bash
# Landing ONLY: index.html + js/api.js + blank.html sync. No api.py, no Lipton.
set -euo pipefail
SERVER="102.218.215.253"
USER="root"
WEB_ROOT="/var/www/sailingsa"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"

SSH_OPTS=(-o StrictHostKeyChecking=no)
SCP=(scp "${SSH_OPTS[@]}")
SSH=(ssh "${SSH_OPTS[@]}")

if [ -f "$KEY" ]; then
  SCP+=(-i "$KEY")
  SSH+=(-i "$KEY")
elif [ -n "${SSHPASS:-}" ]; then
  SCP=(sshpass -e scp "${SSH_OPTS[@]}")
  SSH=(sshpass -e ssh "${SSH_OPTS[@]}")
else
  echo "ERROR: Need ~/.ssh/sailingsa_live_key or SSHPASS env"
  exit 1
fi

echo "=== Landing-only deploy ==="
"${SCP[@]}" "$PROJECT_ROOT/sailingsa/frontend/index.html" "${USER}@${SERVER}:${WEB_ROOT}/index.html"
"${SCP[@]}" "$PROJECT_ROOT/sailingsa/frontend/js/api.js" "${USER}@${SERVER}:${WEB_ROOT}/js/api.js"
"${SSH[@]}" "${USER}@${SERVER}" "
  TS=\$(date +%Y%m%d_%H%M%S)
  cp -a ${WEB_ROOT}/blank.html ${WEB_ROOT}/blank.html.bak_\${TS} 2>/dev/null || true
  cp ${WEB_ROOT}/index.html ${WEB_ROOT}/blank.html
  chown www-data:www-data ${WEB_ROOT}/index.html ${WEB_ROOT}/blank.html ${WEB_ROOT}/js/api.js
  ls -la ${WEB_ROOT}/index.html ${WEB_ROOT}/blank.html ${WEB_ROOT}/js/api.js
  md5sum ${WEB_ROOT}/index.html ${WEB_ROOT}/blank.html
"
echo "Done."
