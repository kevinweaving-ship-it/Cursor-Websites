#!/bin/bash
# Deploy tracking-dev2 / Lipton-dev assets ONLY.
# NEVER unzip full frontend. NEVER overwrite index.html, blank.html, or api.py by default.
# Run from project root. Requires ~/.ssh/sailingsa_live_key or SSHPASS.
set -euo pipefail

SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FE="$PROJECT_ROOT/sailingsa/frontend"

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
  echo "ERROR: Need ~/.ssh/sailingsa_live_key or SSHPASS"
  exit 1
fi

# Allowlist only — add files here when new *dev* assets are required.
# Do NOT add index.html, blank.html, js/api.js, css/main.css, or anything shared with public URLs.
ALLOWLIST=(
  tracking-dev2.html
  css/tracking-dev2.css
  css/lipton-dev.css
  js/tracking-dev2-playback.js
  js/tracking-dev2-sailfish.js
  js/lipton-dev-playback.js
  js/lipton-dev-races.json
  js/lipton-dev-series-scores.json
  js/lipton-dev-event-logo.png
  js/lipton-dev-replay.json
  js/lipton-dev-replay-r1.json
  js/lipton-dev-replay-r2.json
  js/lipton-dev-replay-r3.json
  js/lipton-dev-replay-r5.json
  js/lipton-dev-replay-r6.json
  js/lipton-dev-replay-r7.json
  js/lipton-dev-replay-r8.json
  js/lipton-dev-replay-r9.json
  js/lipton-dev-replay-r10.json
  js/lipton-dev-trail.json
  js/lipton-dev-trail-r1.json
  js/lipton-dev-trail-r2.json
  js/lipton-dev-trail-r3.json
  js/lipton-dev-trail-r5.json
  js/lipton-dev-trail-r6.json
  js/lipton-dev-trail-r7.json
  js/lipton-dev-trail-r8.json
  js/lipton-dev-trail-r9.json
  js/lipton-dev-trail-r10.json
)

echo "=== PROTECTED DEV DEPLOY (allowlist only) ==="
echo "Will NOT touch: index.html, blank.html, js/api.js, api.py (unless SAILINGSA_ALLOW_API_DEPLOY=1)"
echo ""

MISSING=0
for rel in "${ALLOWLIST[@]}"; do
  if [ ! -f "$FE/$rel" ]; then
    echo "MISSING locally: $rel"
    MISSING=1
  fi
done
if [ "$MISSING" -ne 0 ]; then
  echo "ERROR: allowlist files missing locally — abort"
  exit 1
fi

# Upload allowlisted files only
"${SSH[@]}" "root@${SERVER}" "mkdir -p ${WEB_ROOT}/js ${WEB_ROOT}/css"
for rel in "${ALLOWLIST[@]}"; do
  echo "  scp $rel"
  "${SCP[@]}" "$FE/$rel" "root@${SERVER}:${WEB_ROOT}/$rel"
done

"${SSH[@]}" "root@${SERVER}" "chown -R www-data:www-data ${WEB_ROOT}/tracking-dev2.html ${WEB_ROOT}/js/tracking-dev2* ${WEB_ROOT}/js/lipton-dev* ${WEB_ROOT}/css/tracking-dev2.css ${WEB_ROOT}/css/lipton-dev.css 2>/dev/null || true"

# Optional Sailfish bootstrap module (dev API helper only — not full api.py)
if [ -f "$PROJECT_ROOT/sailingsa/backend/tracking_dev2_sailfish.py" ]; then
  echo "=== bootstrap module (tracking_dev2_sailfish.py only) ==="
  "${SSH[@]}" "root@${SERVER}" "mkdir -p ${WEB_ROOT}/sailingsa/backend"
  "${SCP[@]}" "$PROJECT_ROOT/sailingsa/__init__.py" "root@${SERVER}:${WEB_ROOT}/sailingsa/__init__.py" 2>/dev/null || true
  "${SCP[@]}" "$PROJECT_ROOT/sailingsa/backend/__init__.py" "root@${SERVER}:${WEB_ROOT}/sailingsa/backend/__init__.py" 2>/dev/null || true
  "${SCP[@]}" "$PROJECT_ROOT/sailingsa/backend/tracking_dev2_sailfish.py" \
    "root@${SERVER}:${WEB_ROOT}/sailingsa/backend/tracking_dev2_sailfish.py"
fi

# api.py: OFF by default — deploying a thin-branch api.py gutted public sailor/club/regatta URLs (Sep 2026).
if [ "${SAILINGSA_ALLOW_API_DEPLOY:-}" = "1" ]; then
  echo "=== WARNING: SAILINGSA_ALLOW_API_DEPLOY=1 — deploying api.py ==="
  LIVE_SIZE=$("${SSH[@]}" "root@${SERVER}" "wc -c < ${WEB_ROOT}/api/api.py" | tr -d '[:space:]')
  NEW_SIZE=$(wc -c < "$PROJECT_ROOT/api.py" | tr -d '[:space:]')
  echo "  live api.py=$LIVE_SIZE bytes  local=$NEW_SIZE bytes"
  # Reject if local is < 80% of live (guards against thin-branch wipe)
  if [ -n "$LIVE_SIZE" ] && [ "$LIVE_SIZE" -gt 0 ]; then
    MIN=$(( LIVE_SIZE * 80 / 100 ))
    if [ "$NEW_SIZE" -lt "$MIN" ]; then
      echo "ERROR: local api.py is much smaller than live ($NEW_SIZE < $MIN). Aborting — this is how URLs got gutted."
      exit 1
    fi
  fi
  "${SCP[@]}" "$PROJECT_ROOT/api.py" "root@${SERVER}:/root/incoming/api.py"
  "${SSH[@]}" "root@${SERVER}" "/root/deploy_api_verified.sh"
else
  echo "=== api.py skipped (set SAILINGSA_ALLOW_API_DEPLOY=1 only after explicit user approval) ==="
fi

echo ""
echo "=== Verify public URLs untouched (sizes) ==="
"${SSH[@]}" "root@${SERVER}" "wc -c ${WEB_ROOT}/index.html ${WEB_ROOT}/blank.html ${WEB_ROOT}/api/api.py"

echo ""
echo "=== Verify dev page ==="
curl -sfI "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev2?race=1" | head -3 || true
curl -sfI "https://sailingsa.co.za/tracking-dev2.html" | head -3 || true

echo ""
echo "Dev-only deploy complete. Public index/blank/api.py not overwritten by this script (unless API override)."
