#!/bin/bash
# Run as root on GoWifi. Adds scoped REA ops access. Does not restart
# WhatsApp or other customer services. Restarts openai-rea-tunnel once
# so ChatGPT rediscovers ops_* tools.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on GoWifi" >&2; exit 1; }
id rea >/dev/null

SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/rea_ops.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/ops" >&2
  exit 1
}

PREFIX=/opt/rea/ops
install -d -m 755 -o rea -g rea "$PREFIX" "$PREFIX/bin" "$PREFIX/etc" "$PREFIX/audit" "$PREFIX/stage" "$PREFIX/stage/github" "$PREFIX/stage/migrations" "$PREFIX/stage/aerialnet" "$PREFIX/backups" "$PREFIX/jobs"
install -m 755 -o rea -g rea "$SRC_DIR/rea_ops.py" "$PREFIX/bin/rea-ops"
install -m 755 -o rea -g rea "$SRC_DIR/rea_ops.py" "$PREFIX/bin/rea_ops.py"
install -m 755 -o rea -g rea "$SRC_DIR/ops_mcp_server.py" "$PREFIX/bin/ops-mcp"
install -m 644 -o rea -g rea "$SRC_DIR/etc/ops.gowifi.json" "$PREFIX/etc/ops.json"
install -m 644 -o rea -g rea "$SRC_DIR/etc/ops.sailingsa.client.json" "$PREFIX/etc/ops.sailingsa.client.json"
install -m 755 -o root -g root "$SRC_DIR/ops_helper.py" /usr/local/sbin/rea-ops-helper

# Journal/log group — takes effect on new sessions and after tunnel restart.
usermod -aG adm,systemd-journal rea

# Scoped sudo for interactive/SSH sessions (tunnel has NoNewPrivileges, so
# ChatGPT uses the localhost ForceCommand helper instead).
cat >/etc/sudoers.d/rea-ops <<'SUDO'
Cmnd_Alias REA_STATUS = /bin/systemctl status arial-whatsapp-poc, /bin/systemctl status arial-whatsapp-watcher, /bin/systemctl status nginx, /bin/systemctl status openai-rea-tunnel, /bin/systemctl status sailing-roundup, /bin/systemctl is-active *, /bin/systemctl is-enabled *, /bin/systemctl show *
Cmnd_Alias REA_JOURNAL = /bin/journalctl -u arial-whatsapp-poc *, /bin/journalctl -u arial-whatsapp-watcher *, /bin/journalctl -u nginx *, /bin/journalctl -u openai-rea-tunnel *, /bin/journalctl -u sailing-roundup *
Cmnd_Alias REA_CTRL = /bin/systemctl restart arial-whatsapp-poc, /bin/systemctl restart arial-whatsapp-watcher, /bin/systemctl reload nginx, /usr/sbin/nginx -t, /usr/local/sbin/rea-ops-helper
rea ALL=(root) NOPASSWD: REA_STATUS, REA_JOURNAL, REA_CTRL
SUDO
chmod 440 /etc/sudoers.d/rea-ops
visudo -cf /etc/sudoers.d/rea-ops

# Application ACLs. Keep existing owners. Do not 777.
setfacl -m u:rea:rx,d:u:rea:rx /opt/arial-whatsapp-poc
find /opt/arial-whatsapp-poc \
  -path '/opt/arial-whatsapp-poc/state/auth' -prune -o \
  -path '/opt/arial-whatsapp-poc/state/event-whatsapp' -prune -o \
  -path '/opt/arial-whatsapp-poc/node_modules' -prune -o \
  -path '/opt/arial-whatsapp-poc/node' -prune -o \
  -exec setfacl -m u:rea:rX {} +
# Source write (not auth/session).
setfacl -m u:rea:rwx /opt/arial-whatsapp-poc
for f in /opt/arial-whatsapp-poc/*.py /opt/arial-whatsapp-poc/*.js /opt/arial-whatsapp-poc/*.md /opt/arial-whatsapp-poc/*.json; do
  [ -f "$f" ] && setfacl -m u:rea:rw "$f" || true
done
# Diagnosis files in state/ (not auth/). Default ACL covers files wapoc rewrites.
setfacl -m u:rea:rx /opt/arial-whatsapp-poc/state
setfacl -d -m u:rea:r /opt/arial-whatsapp-poc/state
setfacl -m u:rea:--- /opt/arial-whatsapp-poc/state/auth 2>/dev/null || true
setfacl -d -m u:rea:--- /opt/arial-whatsapp-poc/state/auth 2>/dev/null || true
for f in /opt/arial-whatsapp-poc/state/health.json \
         /opt/arial-whatsapp-poc/state/link_watch.json \
         /opt/arial-whatsapp-poc/state/alerts_recent.json \
         /opt/arial-whatsapp-poc/state/alerts.jsonl \
         /opt/arial-whatsapp-poc/state/poc.log \
         /opt/arial-whatsapp-poc/state/events.jsonl; do
  [ -f "$f" ] && setfacl -m u:rea:r "$f" || true
done
setfacl -m u:rea:rwX,d:u:rea:rwX /opt/aerialnet-arial
setfacl -R -m u:rea:rwX /opt/aerialnet-arial
if [ -d /var/www/aerialnet/data ]; then
  setfacl -m u:rea:rx /var/www/aerialnet /var/www/aerialnet/data
  setfacl -m u:rea:r /var/www/aerialnet/data/whatsapp_log.jsonl 2>/dev/null || true
fi

# Deny auth dir even if a default ACL appears later.
setfacl -m u:rea:--- /opt/arial-whatsapp-poc/state/auth 2>/dev/null || true
setfacl -m u:rea:--- /opt/arial-whatsapp-poc/state/event-whatsapp 2>/dev/null || true
chmod 600 /etc/arial-whatsapp-poc.env

# Localhost ForceCommand key (same pattern as sailing-roundup-timer).
KEY=/opt/rea/.ssh/id_rea_ops
if [ ! -f "$KEY" ]; then
  sudo -u rea -H ssh-keygen -t ed25519 -f "$KEY" -N "" -C "rea-ops-localhost" >/dev/null
fi
chmod 600 "$KEY"
chown rea:rea "$KEY" "$KEY.pub"
PUB=$(tr -d '\n' < "$KEY.pub")
AUTH=/root/.ssh/authorized_keys
touch "$AUTH"
chmod 600 "$AUTH"
LINE="command=\"/usr/local/sbin/rea-ops-helper\",restrict,from=\"127.0.0.1,::1\" $PUB"
if ! grep -Fq "$PUB" "$AUTH"; then
  printf '%s\n' "$LINE" >> "$AUTH"
fi
sudo -u rea -H ssh-keyscan -H 127.0.0.1 >> /opt/rea/.ssh/known_hosts 2>/dev/null || true
chown rea:rea /opt/rea/.ssh/known_hosts
chmod 600 /opt/rea/.ssh/known_hosts

# REA GitHub deploy key (public half only is shown). Write access still
# requires a human to add the key on GitHub; Cursor cannot.
GH_KEY=/opt/rea/.ssh/id_rea_github
if [ ! -f "$GH_KEY" ]; then
  sudo -u rea -H ssh-keygen -t ed25519 -f "$GH_KEY" -N "" -C "rea-ops-github@gowifi" >/dev/null
fi
chmod 600 "$GH_KEY"
chown rea:rea "$GH_KEY" "$GH_KEY.pub"
# Optional gh CLI for API fallback after a token is added by a human.
if ! command -v gh >/dev/null 2>&1; then
  apt-get install -y gh >/dev/null 2>&1 || true
fi

# SailingSA ops SSH alias.
SSH_CFG=/opt/rea/.ssh/config
if ! grep -q "Host sailingsa-ops" "$SSH_CFG" 2>/dev/null; then
  cat >> "$SSH_CFG" <<'CFG'

Host sailingsa-ops
  HostName 102.218.215.253
  User rea-ops
  IdentityFile /opt/rea/.ssh/id_rea_sailingsa
  IdentitiesOnly yes
  BatchMode yes
  ConnectTimeout 15
CFG
  chown rea:rea "$SSH_CFG"
  chmod 600 "$SSH_CFG"
fi

# MariaDB unix_socket probe DB + read-only Dolibarr.
mysql --batch <<'SQL' || true
CREATE USER IF NOT EXISTS 'rea'@'localhost' IDENTIFIED VIA unix_socket;
CREATE DATABASE IF NOT EXISTS rea_ops;
GRANT ALL PRIVILEGES ON rea_ops.* TO 'rea'@'localhost';
GRANT SELECT ON dolibarr.* TO 'rea'@'localhost';
FLUSH PRIVILEGES;
SQL
sudo -u rea -H mysql --batch -e "CREATE TABLE IF NOT EXISTS probe (id INT PRIMARY KEY, note VARCHAR(64)); DELETE FROM probe; INSERT INTO probe VALUES (1,'rea-ops'); SELECT note FROM probe; DELETE FROM probe;" rea_ops >/tmp/rea-ops-db-probe.out 2>&1 || true

# Expand inspect allowlist so existing audit_* can read WhatsApp code/logs.
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/opt/rea/inspect/etc/inspect.json")
if p.is_file():
    data = json.loads(p.read_text())
    for key, values in {
        "allow_paths": ["/opt/arial-whatsapp-poc", "/var/www/aerialnet/data", "/opt/rea/ops"],
        "allow_logs": ["/var/www/aerialnet/data", "/opt/arial-whatsapp-poc/state"],
        "discover_roots": ["/opt/arial-whatsapp-poc", "/opt/aerialnet-arial"],
    }.items():
        cur = list(data.get(key, []))
        for v in values:
            if v not in cur:
                cur.append(v)
        data[key] = cur
    logs = data.setdefault("logs", {})
    logs["arial-whatsapp-poc"] = {"kind": "journal", "unit": "arial-whatsapp-poc"}
    logs["arial-whatsapp-watcher"] = {"kind": "journal", "unit": "arial-whatsapp-watcher"}
    logs["whatsapp-admin"] = {"kind": "file", "path": "/var/www/aerialnet/data/whatsapp_log.jsonl"}
    p.write_text(json.dumps(data, indent=2) + "\n")
    print("INSPECT_JSON_UPDATED")
PY

# Skip WhatsApp auth dirs in inspect walks if the agent is present.
python3 - <<'PY'
from pathlib import Path
p = Path("/opt/rea/inspect/bin/inspect-agent")
if p.is_file():
    text = p.read_text()
    if '"auth"' not in text:
        text = text.replace(
            'SKIP_DIR_NAMES = {',
            'SKIP_DIR_NAMES = {\n    "auth",\n    "event-whatsapp",',
            1,
        )
        p.write_text(text)
        print("INSPECT_AGENT_SKIP_UPDATED")
PY

# Mux: replace with the version that advertises audit_* and ops_*.
if [ -f "$SRC_DIR/../inspect/mcp_mux.py" ]; then
  install -m 755 -o rea -g rea "$SRC_DIR/../inspect/mcp_mux.py" /opt/rea/inspect/bin/mcp-mux
fi

# Tunnel restart is required so ChatGPT's connector sees ops_* and the
# tunnel process picks up adm/systemd-journal. WhatsApp is not restarted.
systemctl restart openai-rea-tunnel.service
sleep 2
systemctl is-active openai-rea-tunnel.service

echo "GOWIFI_OPS_INSTALLED"
echo "PUBKEY=$(tr -d '\n' < /opt/rea/.ssh/id_rea_sailingsa.pub)"
echo "GITHUB_PUBKEY=$(tr -d '\n' < /opt/rea/.ssh/id_rea_github.pub)"
