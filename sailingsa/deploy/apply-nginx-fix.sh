#!/bin/bash
# Apply nginx fix for legacy paths - run ON SERVER as root
# ssh root@102.218.215.253 "bash -s" < sailingsa/deploy/apply-nginx-fix.sh

set -e
NGCFG=$(ls /etc/nginx/sites-enabled/sailingsa* /etc/nginx/sites-available/sailingsa* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG="/etc/nginx/sites-available/default"

echo "Editing: $NGCFG"
echo "Step 1: Remove legacy alias blocks..."
sed -i '/location \/sailingsa\/frontend\//,/}/d' "$NGCFG" 2>/dev/null || true
sed -i '/location \/frontend\//,/}/d' "$NGCFG" 2>/dev/null || true
sed -i '/alias.*sailingsa\/frontend/d' "$NGCFG" 2>/dev/null || true
sed -i '/rewrite.*sailingsa\/frontend/d' "$NGCFG" 2>/dev/null || true

echo "Step 2: Add hard-fail blocks before location /..."
# Insert before first "location /" that's not already our block
if ! grep -q 'location \^~ /sailingsa/' "$NGCFG"; then
    sed -i '/location \/ {/i\
    location ^~ /sailingsa/ {\
        return 404;\
    }\
    location ^~ /frontend/ {\
        return 404;\
    }\
' "$NGCFG"
fi

echo "Step 3: Reload nginx..."
nginx -t && systemctl reload nginx
echo "Done. Run verification curls."
