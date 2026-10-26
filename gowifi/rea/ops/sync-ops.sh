#!/bin/bash
# Incremental copy of ops binaries/config. Does not walk ACLs or restart
# WhatsApp. Restarts openai-rea-tunnel on GoWifi so mux reloads ops-mcp.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/rea_ops.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/ops" >&2
  exit 1
}

if [ -d /opt/rea/ops/bin ]; then
  install -d -m 755 -o rea -g rea /opt/rea/ops/stage/github /opt/rea/ops/stage/migrations /opt/rea/ops/stage/aerialnet
  install -m 755 -o rea -g rea "$SRC_DIR/rea_ops.py" /opt/rea/ops/bin/rea-ops
  install -m 755 -o rea -g rea "$SRC_DIR/rea_ops.py" /opt/rea/ops/bin/rea_ops.py
  install -m 755 -o rea -g rea "$SRC_DIR/ops_mcp_server.py" /opt/rea/ops/bin/ops-mcp
  install -m 644 -o rea -g rea "$SRC_DIR/etc/ops.gowifi.json" /opt/rea/ops/etc/ops.json
  install -m 644 -o rea -g rea "$SRC_DIR/etc/ops.sailingsa.client.json" /opt/rea/ops/etc/ops.sailingsa.client.json
  install -m 755 -o root -g root "$SRC_DIR/ops_helper.py" /usr/local/sbin/rea-ops-helper
  if [ ! -f /opt/rea/.ssh/id_rea_github ]; then
    sudo -u rea -H ssh-keygen -t ed25519 -f /opt/rea/.ssh/id_rea_github -N "" -C "rea-ops-github@gowifi" >/dev/null
    chmod 600 /opt/rea/.ssh/id_rea_github
    chown rea:rea /opt/rea/.ssh/id_rea_github /opt/rea/.ssh/id_rea_github.pub
  fi
  command -v gh >/dev/null 2>&1 || apt-get install -y gh >/dev/null 2>&1 || true
  systemctl restart openai-rea-tunnel.service
  sleep 2
  systemctl is-active openai-rea-tunnel.service
  echo "GOWIFI_OPS_SYNCED"
  echo "GITHUB_PUBKEY=$(tr -d '\n' < /opt/rea/.ssh/id_rea_github.pub)"
fi

if [ -d /opt/rea-ops/bin ]; then
  install -d -m 750 -o rea-ops -g rea-ops /opt/rea-ops/stage/github /opt/rea-ops/stage/migrations
  cat >/opt/rea-ops/stage/migrations/probe.sql <<'SQL'
CREATE TABLE IF NOT EXISTS rea_ops.probe (id int PRIMARY KEY, note text);
DELETE FROM rea_ops.probe;
INSERT INTO rea_ops.probe VALUES (1, 'rea-ops-handover');
SELECT note FROM rea_ops.probe;
DELETE FROM rea_ops.probe;
SQL
  chown rea-ops:rea-ops /opt/rea-ops/stage/migrations/probe.sql
  chmod 640 /opt/rea-ops/stage/migrations/probe.sql
  install -m 755 -o root -g rea-ops "$SRC_DIR/rea_ops.py" /opt/rea-ops/bin/ops-agent
  install -m 755 -o root -g root "$SRC_DIR/ops_helper.py" /usr/local/sbin/rea-ops-helper
  install -m 640 -o root -g rea-ops "$SRC_DIR/etc/ops.sailingsa.json" /opt/rea-ops/etc/ops.json
  if [ ! -f /opt/rea-ops/.ssh/id_rea_github ]; then
    sudo -u rea-ops -H ssh-keygen -t ed25519 -f /opt/rea-ops/.ssh/id_rea_github -N "" -C "rea-ops-github@sailingsa" >/dev/null
    chmod 600 /opt/rea-ops/.ssh/id_rea_github
    chown rea-ops:rea-ops /opt/rea-ops/.ssh/id_rea_github /opt/rea-ops/.ssh/id_rea_github.pub
  fi
  command -v gh >/dev/null 2>&1 || apt-get install -y gh >/dev/null 2>&1 || true
  echo "SAILINGSA_OPS_SYNCED"
  echo "GITHUB_PUBKEY=$(tr -d '\n' < /opt/rea-ops/.ssh/id_rea_github.pub)"
fi
