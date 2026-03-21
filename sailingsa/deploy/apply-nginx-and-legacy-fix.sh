#!/bin/bash
# Run ON the server: legacy dirs removal, nginx fix, re-extract, restart
# Or run via: expect apply-nginx-and-legacy-fix.exp (which scps and runs this)

set -e
WEB_ROOT=/var/www/sailingsa

echo "=== 1. DELETE LEGACY DIRECTORIES ==="
rm -rf "$WEB_ROOT/sailingsa" "$WEB_ROOT/frontend"
ls -la "$WEB_ROOT"

echo ""
echo "=== 2. FIND NGINX CONFIG ==="
NGCFG=""
for f in /etc/nginx/sites-enabled/sailingsa* /etc/nginx/sites-enabled/default \
         /etc/nginx/sites-available/sailingsa* /etc/nginx/sites-available/sailingsa.co.za*; do
  [ -f "$f" ] && grep -l sailingsa "$f" 2>/dev/null && NGCFG="$f" && break
done
[ -z "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=/etc/nginx/sites-available/default
echo "Using: $NGCFG"
cp "$NGCFG" "${NGCFG}.bak.$(date +%Y%m%d%H%M)"

echo ""
echo "=== 3. EDIT NGINX (remove legacy, add 404 + /auth/ proxy) ==="
# Remove old sailingsa/frontend and sailingsa location blocks (multi-line)
sed -i '/location \/sailingsa\/frontend\//,/^[[:space:]]*}/d' "$NGCFG" 2>/dev/null || true
sed -i '/location \/sailingsa\//,/^[[:space:]]*}/d' "$NGCFG" 2>/dev/null || true
sed -i '/alias.*sailingsa/d' "$NGCFG" 2>/dev/null || true
sed -i '/rewrite.*sailingsa/d' "$NGCFG" 2>/dev/null || true

# Ensure we have the 404 block and /auth/ proxy (insert before first "location /" in server block)
if ! grep -q 'location ^~ /sailingsa/' "$NGCFG"; then
  BLOCKFILE=$(mktemp)
  cat >> "$BLOCKFILE" << 'BLOCKEOF'
    location ^~ /sailingsa/ {
        return 404;
    }

    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

BLOCKEOF
  # Insert before "location /" block
  awk -v blockfile="$BLOCKFILE" '
    /^[[:space:]]*location[[:space:]]+\/[[:space:]]/ {
      if (!done) { while ((getline line < blockfile) > 0) print line; close(blockfile); done=1 }
    }
    { print }
  ' "$NGCFG" > "${NGCFG}.new" && mv "${NGCFG}.new" "$NGCFG"
  rm -f "$BLOCKFILE"
fi

echo ""
echo "=== 4. RELOAD NGINX ==="
nginx -t && systemctl reload nginx

echo ""
echo "=== 5. RE-EXTRACT FRONTEND ==="
cd "$WEB_ROOT"
[ -f /tmp/sailingsa-frontend.zip ] && unzip -o /tmp/sailingsa-frontend.zip || echo "WARN: /tmp/sailingsa-frontend.zip not found - skip unzip"
chown -R www-data:www-data "$WEB_ROOT"
ls -la index.html login.html 2>/dev/null || true

echo ""
echo "=== 6. RESTART API ==="
systemctl restart sailingsa-api
sleep 2
systemctl status sailingsa-api --no-pager | head -8

echo ""
echo "=== 7. VERIFICATION CURLS ==="
echo "Legacy (must 404):"
curl -sI -o /dev/null -w "%{http_code}\n" https://sailingsa.co.za/sailingsa/frontend/login.html
curl -sI -o /dev/null -w "%{http_code}\n" https://sailingsa.co.za/sailingsa/frontend/index.html
echo "Root (must 200):"
curl -sI -o /dev/null -w "%{http_code}\n" https://sailingsa.co.za/login.html
curl -sI -o /dev/null -w "%{http_code}\n" https://sailingsa.co.za/index.html
echo "Auth POST (must 200 or 401, not 405):"
curl -sI -o /dev/null -w "%{http_code}\n" -X POST https://sailingsa.co.za/auth/login -H "Content-Type: application/json" -d '{"provider":"username","username":"21172","password":"test"}'

echo ""
echo "=== DONE ==="
