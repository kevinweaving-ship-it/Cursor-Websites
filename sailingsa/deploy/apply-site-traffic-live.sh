#!/usr/bin/env bash
# Apply site_traffic_events DDL on LIVE and install nginx traffic beacon inject.
# Requires: ~/.ssh/sailingsa_live_key (see SSH_LIVE.md)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SERVER="${SAILINGSA_SERVER:-102.218.215.253}"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SQL="$ROOT/sailingsa/deploy/site_traffic_events.sql"
NGINX_SNIP="$ROOT/sailingsa/deploy/nginx-site-traffic.conf"
JS="$ROOT/sailingsa/frontend/js/site-traffic.js"
MOD="$ROOT/site_traffic.py"

if [[ ! -f "$KEY" ]]; then
  echo "ERROR: SSH key not found: $KEY"
  exit 1
fi
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no "root@$SERVER")
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no)

echo "== Upload SQL, module, JS, nginx snippet =="
"${SCP[@]}" "$SQL" "root@$SERVER:/tmp/site_traffic_events.sql"
"${SCP[@]}" "$MOD" "root@$SERVER:/var/www/sailingsa/api/site_traffic.py"
"${SCP[@]}" "$JS" "root@$SERVER:/var/www/sailingsa/js/site-traffic.js"
"${SCP[@]}" "$NGINX_SNIP" "root@$SERVER:/etc/nginx/snippets/sailingsa-site-traffic.conf"

echo "== Create table =="
"${SSH[@]}" 'DBURL=$(grep -oP "DATABASE_URL=\K[^\" ]+" /etc/systemd/system/sailingsa-api.service | head -1); if [ -z "$DBURL" ]; then DBURL=$(grep -oP "DB_URL=\K[^\" ]+" /etc/systemd/system/sailingsa-api.service | head -1); fi; psql "$DBURL" -f /tmp/site_traffic_events.sql'

echo "== Ensure nginx include (idempotent) =="
"${SSH[@]}" 'CONF=$(ls /etc/nginx/sites-enabled/*sailingsa* /etc/nginx/sites-enabled/default 2>/dev/null | head -1); if [ -n "$CONF" ] && ! grep -q sailingsa-site-traffic.conf "$CONF"; then sed -i "/server_name.*sailingsa/a\\    include /etc/nginx/snippets/sailingsa-site-traffic.conf;" "$CONF" || true; fi; nginx -t && systemctl reload nginx'

echo "== Restart API (after api.py deploy separately) =="
"${SSH[@]}" 'systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api'

echo "DONE. Deploy api.py with deploy_api_verified / deploy-with-key as usual."
