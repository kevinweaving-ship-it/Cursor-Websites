#!/usr/bin/env bash
# ONE SCRIPT — FULL PARITY FIX (RUN AS ROOT on server)
# Assumes: canonical api.py at /root/Project 6/api.py, DB restored, nginx has /api/ and /auth/ proxy
set -e

echo "=== STEP 1: Stop existing API and kill uvicorn ==="
systemctl stop sailingsa-api || true
pkill -f uvicorn || true

echo "=== STEP 2: Deploy canonical api.py ==="
cp /root/Project\ 6/api.py /var/www/sailingsa/api/api.py
chown www-data:www-data /var/www/sailingsa/api/api.py

echo "=== STEP 3: Write systemd service ==="
cat >/etc/systemd/system/sailingsa-api.service <<'EOF'
[Unit]
Description=SailingSA API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/sailingsa/api
Environment="DB_URL=postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master"
ExecStart=/usr/bin/python3 -m uvicorn api:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo "=== STEP 4: Start API ==="
systemctl start sailingsa-api
systemctl status sailingsa-api --no-pager

echo "=== STEP 5: Verify API locally (NO nginx) ==="
curl -f http://127.0.0.1:8000/api/search?q=smith
curl -f http://127.0.0.1:8000/api/regattas/with-counts

echo "=== STEP 6: Reload nginx ==="
nginx -t
systemctl reload nginx

echo "=== STEP 7: Verify externally ==="
curl -f https://sailingsa.co.za/api/search?q=smith
curl -f https://sailingsa.co.za/api/regattas/with-counts
curl -i -X POST https://sailingsa.co.za/auth/login \
  -H "Content-Type: application/json" \
  -d '{"provider":"username","username":"21172","password":"test"}'

echo "=== DONE: Cloud now matches Mac ==="
