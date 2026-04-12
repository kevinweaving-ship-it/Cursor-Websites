#!/bin/bash
# HARD PARITY RESET — run ON server
set -e
API_DIR=/var/www/sailingsa/api

echo "=== STEP 1 — Kill any wrong API ==="
systemctl stop sailingsa-api 2>/dev/null || true
pkill -f uvicorn 2>/dev/null || true
sleep 2

echo ""
echo "=== STEP 2 — Confirm api.py exists ==="
ls -la "$API_DIR/api.py"

echo ""
echo "=== STEP 3 — Fix sailingsa-api.service ==="
# Use venv if it exists, else system python
VENV_UVICORN="/var/www/sailingsa/api/venv/bin/uvicorn"
EXEC_START="uvicorn api:app --host 127.0.0.1 --port 8000"
[ -x "$VENV_UVICORN" ] && EXEC_START="$VENV_UVICORN api:app --host 127.0.0.1 --port 8000" || EXEC_START="/usr/bin/python3 -m uvicorn api:app --host 127.0.0.1 --port 8000"

cat > /etc/systemd/system/sailingsa-api.service << SVCEOF
[Unit]
Description=SailingSA API Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/sailingsa/api
Environment="DB_URL=postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master"
ExecStart=$EXEC_START
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF
systemctl daemon-reload
systemctl start sailingsa-api
sleep 3
systemctl status sailingsa-api --no-pager | head -15

echo ""
echo "=== STEP 4 — Verify API directly (no nginx) ==="
curl -s -o /dev/null -w "  /api/search?q=smith  %{http_code}\n" "http://127.0.0.1:8000/api/search?q=smith"
curl -s -o /dev/null -w "  /api/regattas/with-counts  %{http_code}\n" "http://127.0.0.1:8000/api/regattas/with-counts"
curl -s -o /dev/null -w "  /openapi.json  %{http_code}\n" "http://127.0.0.1:8000/openapi.json"
if [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/search?q=smith)" != "200" ]; then
  echo "  ERROR: API not returning 200"
  exit 1
fi

echo ""
echo "=== STEP 5 — nginx must proxy /api/ and /auth/ ==="
echo "Ensure nginx has: location /api/ { proxy_pass http://127.0.0.1:8000; ... }"
echo "Ensure nginx has: location /auth/ { proxy_pass http://127.0.0.1:8000; ... }"
nginx -t && systemctl reload nginx && echo "nginx reloaded"

echo ""
echo "=== STEP 6 — External verification ==="
curl -s -o /dev/null -w "  https://sailingsa.co.za/api/search  %{http_code}\n" "https://sailingsa.co.za/api/search?q=smith"
curl -s -o /dev/null -w "  https://sailingsa.co.za/api/regattas/with-counts  %{http_code}\n" "https://sailingsa.co.za/api/regattas/with-counts"
AUTH_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST https://sailingsa.co.za/auth/login -H "Content-Type: application/json" -d '{"provider":"username","username":"21172","password":"test"}')
echo "  https://sailingsa.co.za/auth/login POST  $AUTH_CODE"
if [ "$AUTH_CODE" = "405" ]; then
  echo "  ERROR: 405 = nginx not proxying /auth/"
fi

echo ""
echo "=== DONE ==="
