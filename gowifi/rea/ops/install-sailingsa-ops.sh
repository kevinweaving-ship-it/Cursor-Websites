#!/bin/bash
# Run as root on SailingSA. Adds write-capable REA ops identity.
# Keeps rea-ro ForceCommand inspect unchanged. Does not restart
# sailingsa-api or nginx.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on SailingSA" >&2; exit 1; }

PREFIX=/opt/rea-ops
PUBKEY="${REA_OPS_PUBKEY:-}"
[ -n "$PUBKEY" ] || { echo "set REA_OPS_PUBKEY to the GoWifi rea public key" >&2; exit 1; }
SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/rea_ops.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/ops" >&2
  exit 1
}

id rea-ops >/dev/null 2>&1 || useradd --system --home "$PREFIX" --shell /bin/sh --comment "REA application ops" rea-ops
usermod -s /bin/sh rea-ops
usermod -aG adm,systemd-journal,www-data rea-ops || true

install -d -m 750 -o rea-ops -g rea-ops "$PREFIX" "$PREFIX/bin" "$PREFIX/etc" "$PREFIX/audit" "$PREFIX/stage" "$PREFIX/stage/github" "$PREFIX/stage/migrations" "$PREFIX/backups" "$PREFIX/jobs" "$PREFIX/.ssh"
install -m 755 -o root -g rea-ops "$SRC_DIR/rea_ops.py" "$PREFIX/bin/ops-agent"
install -m 755 -o root -g root "$SRC_DIR/ops_helper.py" /usr/local/sbin/rea-ops-helper
install -m 640 -o root -g rea-ops "$SRC_DIR/etc/ops.sailingsa.json" "$PREFIX/etc/ops.json"
if [ -f "$SRC_DIR/etc/probe.sql" ]; then
  install -m 640 -o rea-ops -g rea-ops "$SRC_DIR/etc/probe.sql" "$PREFIX/stage/migrations/probe.sql"
fi

# ACLs: keep www-data ownership, let rea-ops read/write application trees.
# Some live files are immutable (chattr +i, e.g. api.py). Skip those.
setfacl -d -m u:rea-ops:rwX,g:www-data:rwX /var/www/sailingsa /var/www/timadvisor || true
setfacl -m u:rea-ops:rwX,g:www-data:rwX /var/www/sailingsa /var/www/timadvisor || true
find /var/www/sailingsa /var/www/timadvisor \( -type d -o -type f \) \
  ! -path '*/.git/*' \
  -print0 2>/dev/null | while IFS= read -r -d '' p; do
    setfacl -m u:rea-ops:rwX "$p" 2>/dev/null || true
  done
setfacl -R -m u:rea-ops:rX /etc/nginx /var/log/nginx 2>/dev/null || true

# PostgreSQL application role: DML + SELECT, no DDL superuser.
sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rea-ops') THEN
    CREATE ROLE "rea-ops" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT;
  END IF;
END
$$;
GRANT CONNECT ON DATABASE sailors_master TO "rea-ops";
SQL
sudo -u postgres psql -d sailors_master -v ON_ERROR_STOP=1 <<'SQL'
GRANT USAGE ON SCHEMA public TO "rea-ops";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "rea-ops";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "rea-ops";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "rea-ops";
CREATE SCHEMA IF NOT EXISTS rea_ops;
GRANT ALL ON SCHEMA rea_ops TO "rea-ops";
SQL
sudo -u rea-ops psql -d sailors_master -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS rea_ops.probe (id int PRIMARY KEY, note text);
DELETE FROM rea_ops.probe;
INSERT INTO rea_ops.probe VALUES (1, 'rea-ops');
SELECT note FROM rea_ops.probe;
DELETE FROM rea_ops.probe;
SQL

cat >/etc/sudoers.d/rea-ops <<'SUDO'
Cmnd_Alias REAOPS_STATUS = /bin/systemctl status sailingsa-api, /bin/systemctl status nginx, /bin/systemctl status postgresql, /bin/systemctl is-active *, /bin/systemctl is-enabled *, /bin/systemctl show *
Cmnd_Alias REAOPS_JOURNAL = /bin/journalctl -u sailingsa-api *, /bin/journalctl -u nginx *
Cmnd_Alias REAOPS_CTRL = /bin/systemctl restart sailingsa-api, /bin/systemctl reload nginx, /usr/sbin/nginx -t, /usr/local/sbin/rea-ops-helper
rea-ops ALL=(root) NOPASSWD: REAOPS_STATUS, REAOPS_JOURNAL, REAOPS_CTRL
SUDO
chmod 440 /etc/sudoers.d/rea-ops
visudo -cf /etc/sudoers.d/rea-ops

AUTH="$PREFIX/.ssh/authorized_keys"
RESTRICT="restrict,command=\"/opt/rea-ops/bin/ops-agent\""
LINE="$RESTRICT $PUBKEY"
touch "$AUTH"
chmod 600 "$AUTH"
chown rea-ops:rea-ops "$AUTH"
if ! grep -Fq "$PUBKEY" "$AUTH"; then
  printf '%s\n' "$LINE" >> "$AUTH"
fi

# Expand read-only inspect allowlist (rea-ro stays ForceCommand inspect-only).
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/opt/rea-ro/etc/inspect.json")
if p.is_file():
    data = json.loads(p.read_text())
    logs = data.setdefault("logs", {})
    logs["sailingsa-api"] = {"kind": "journal", "unit": "sailingsa-api"}
    p.write_text(json.dumps(data, indent=2) + "\n")
    print("SA_INSPECT_JSON_OK")
PY

if [ ! -f "$PREFIX/.ssh/id_rea_github" ]; then
  sudo -u rea-ops -H ssh-keygen -t ed25519 -f "$PREFIX/.ssh/id_rea_github" -N "" -C "rea-ops-github@sailingsa" >/dev/null
fi
chmod 600 "$PREFIX/.ssh/id_rea_github"
chown rea-ops:rea-ops "$PREFIX/.ssh/id_rea_github" "$PREFIX/.ssh/id_rea_github.pub"
if ! command -v gh >/dev/null 2>&1; then
  apt-get install -y gh >/dev/null 2>&1 || true
fi

sudo -u rea-ops git config --global --add safe.directory /var/www/sailingsa || true
sudo -u rea-ops git config --global --add safe.directory /var/www/timadvisor || true
echo "SAILINGSA_OPS_INSTALLED"
echo "GITHUB_PUBKEY=$(tr -d '\n' < "$PREFIX/.ssh/id_rea_github.pub")"
