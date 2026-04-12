#!/usr/bin/env bash
# Run ON THE SERVER as root (or via: ssh ... 'bash -s' < this_file).
# Serves 09:07 backup of api.py at /admin/dashboard-restore ONLY. No other URL changed.
# Backup: /root/backups/api.py.20260305_090730

set -e
RESTORE_DIR="/var/www/sailingsa/api_restore_8001"
BACKUP="/root/backups/api.py.20260305_090730"
SVC_NAME="sailingsa-api-restore"
NGINX_CFG="/etc/nginx/sites-enabled/timadvisor"

echo "=== 1. Dir + backup ==="
mkdir -p "$RESTORE_DIR"
cp "$BACKUP" "$RESTORE_DIR/api.py"
chown -R www-data:www-data "$RESTORE_DIR"

echo "=== 2. Systemd service (port 8001) ==="
cat > /etc/systemd/system/${SVC_NAME}.service << 'EOF'
[Unit]
Description=SailingSA API restore (09:07 dashboard on 8001)
After=network.target sailingsa-api.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/sailingsa/api_restore_8001
Environment="PATH=/var/www/sailingsa/api/venv/bin"
Environment="PYTHONPATH=/var/www/sailingsa"
Environment="DB_URL=postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
Environment="STATIC_DIR=/var/www/sailingsa"
ExecStart=/var/www/sailingsa/api/venv/bin/uvicorn api:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SVC_NAME"
systemctl restart "$SVC_NAME"
sleep 2
systemctl is-active "$SVC_NAME" || true

echo "=== 3. Nginx: only /admin/dashboard-restore -> 8001/admin/dashboard ==="
if grep -q "dashboard-restore" "$NGINX_CFG" 2>/dev/null; then
  echo "Location already present."
else
  LINE=$(grep -n 'location ~ \^/admin/' "$NGINX_CFG" | head -1 | cut -d: -f1)
  if [ -n "$LINE" ]; then
    sed -i "${LINE}i\\
    location = /admin/dashboard-restore {\\
        proxy_pass http://127.0.0.1:8001/admin/dashboard;\\
        proxy_set_header Host \\\$host;\\
        proxy_set_header X-Real-IP \\\$remote_addr;\\
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;\\
        proxy_set_header X-Forwarded-Proto \\\$scheme;\\
    }" "$NGINX_CFG"
  fi
  nginx -t && systemctl reload nginx
fi

echo "Done. Only https://sailingsa.co.za/admin/dashboard-restore uses 09:07 backup. All other URLs unchanged."
