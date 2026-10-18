#!/bin/bash
# Run as root on GoWifi (box.gowifi.co.za). Installs the REA inspect dispatcher
# under /opt/rea/inspect. Does not change /opt/rea package files or the MCP
# tunnel command.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on GoWifi" >&2; exit 1; }

SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/inspect_agent.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/inspect" >&2
  exit 1
}

PREFIX=/opt/rea/inspect
install -d -m 755 -o rea -g rea "$PREFIX" "$PREFIX/bin" "$PREFIX/etc" "$PREFIX/audit" "$PREFIX/state" "$PREFIX/repo"
install -m 755 -o rea -g rea "$SRC_DIR/inspect_agent.py" "$PREFIX/bin/inspect-agent"
install -m 755 -o rea -g rea "$SRC_DIR/rea_inspect.py" "$PREFIX/bin/rea-inspect"
install -m 755 -o rea -g rea "$SRC_DIR/audit_mcp_server.py" "$PREFIX/bin/audit-mcp"
install -m 755 -o rea -g rea "$SRC_DIR/mcp_mux.py" "$PREFIX/bin/mcp-mux"
install -m 644 -o rea -g rea "$SRC_DIR/etc/inspect.gowifi.json" "$PREFIX/etc/inspect.json"
install -m 644 -o rea -g rea "$SRC_DIR/CATALOG.md" "$PREFIX/CATALOG.md"
install -m 644 -o rea -g rea "$SRC_DIR/README.md" "$PREFIX/README.md"

KEY=/opt/rea/.ssh/id_rea_sailingsa
if [ ! -f "$KEY" ]; then
  sudo -u rea -H ssh-keygen -t ed25519 -f "$KEY" -N "" -C "rea-inspect-sailingsa" >/dev/null
fi
chmod 600 "$KEY"
chown rea:rea "$KEY" "$KEY.pub"

SSH_CFG=/opt/rea/.ssh/config
if ! grep -q "Host sailingsa-inspect" "$SSH_CFG" 2>/dev/null; then
  cat >> "$SSH_CFG" <<'CFG'

Host sailingsa-inspect
  HostName 102.218.215.253
  User rea-ro
  IdentityFile /opt/rea/.ssh/id_rea_sailingsa
  IdentitiesOnly yes
  BatchMode yes
  ConnectTimeout 15
CFG
  chown rea:rea "$SSH_CFG"
  chmod 600 "$SSH_CFG"
fi

# Known host (SailingSA live).
sudo -u rea -H ssh-keyscan -H 102.218.215.253 >> /opt/rea/.ssh/known_hosts 2>/dev/null || true
chmod 600 /opt/rea/.ssh/known_hosts
chown rea:rea /opt/rea/.ssh/known_hosts

install -m 644 /dev/stdin /etc/systemd/system/rea-inspect-discover.service <<'UNIT'
[Unit]
Description=Refresh REA read-only inspect manifest
After=network-online.target

[Service]
Type=oneshot
User=rea
Group=rea
Environment=HOME=/opt/rea
ExecStart=/opt/rea/inspect/bin/rea-inspect both discover
StandardOutput=truncate:/opt/rea/inspect/state/MANIFEST.json
StandardError=append:/opt/rea/inspect/audit/discover.err
UNIT

install -m 644 /dev/stdin /etc/systemd/system/rea-inspect-discover.timer <<'UNIT'
[Unit]
Description=Refresh REA inspect manifest every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now rea-inspect-discover.timer

PROFILE=/opt/openai-tunnel/profiles/rea-box.yaml
if [ -f "$PROFILE" ]; then
  cp -a "$PROFILE" "$PROFILE.bak-pre-audit-$(date +%Y%m%d%H%M%S)"
  python3 - <<'PY'
from pathlib import Path
p = Path("/opt/openai-tunnel/profiles/rea-box.yaml")
text = p.read_text(encoding="utf-8")
old = '''mcp:
  commands:
    - channel: main
      command: "/opt/rea/bin/rea mcp"
'''
new = '''mcp:
  commands:
    - channel: main
      command: "/opt/rea/inspect/bin/mcp-mux"
    - channel: audit
      command: "/opt/rea/inspect/bin/audit-mcp"
'''
if "/opt/rea/inspect/bin/mcp-mux" not in text:
    if old not in text:
        raise SystemExit("unexpected tunnel profile mcp block; not modifying")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("TUNNEL_PROFILE_OK")
PY
  systemctl restart openai-rea-tunnel.service
fi

echo "GOWIFI_INSPECT_INSTALLED"
echo "PUBKEY=$(tr -d '\n' < /opt/rea/.ssh/id_rea_sailingsa.pub)"
