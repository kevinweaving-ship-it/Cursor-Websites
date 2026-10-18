#!/bin/bash
# Run as root on SailingSA / TimAdvisor (102.218.215.253).
# Adds a restricted read-only inspect user for REA. Does not change nginx,
# sailingsa-api, or application files.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on SailingSA" >&2; exit 1; }

PREFIX=/opt/rea-ro
PUBKEY="${REA_INSPECT_PUBKEY:-}"
[ -n "$PUBKEY" ] || { echo "set REA_INSPECT_PUBKEY to the GoWifi rea public key" >&2; exit 1; }

SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/inspect_agent.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/inspect" >&2
  exit 1
}

id rea-ro >/dev/null 2>&1 || useradd --system --home "$PREFIX" --shell /bin/sh --comment "REA read-only inspect" rea-ro
usermod -s /bin/sh rea-ro
usermod -aG adm,systemd-journal rea-ro || true

install -d -m 750 -o rea-ro -g rea-ro "$PREFIX" "$PREFIX/bin" "$PREFIX/etc" "$PREFIX/audit" "$PREFIX/.ssh"
install -m 755 -o root -g rea-ro "$SRC_DIR/inspect_agent.py" "$PREFIX/bin/inspect-agent"
install -m 640 -o root -g rea-ro "$SRC_DIR/etc/inspect.sailingsa.json" "$PREFIX/etc/inspect.json"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rea-ro') THEN
    CREATE ROLE "rea-ro" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END
$$;
GRANT CONNECT ON DATABASE sailors_master TO "rea-ro";
SQL
sudo -u postgres psql -d sailors_master -v ON_ERROR_STOP=1 <<'SQL'
GRANT USAGE ON SCHEMA public TO "rea-ro";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "rea-ro";
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO "rea-ro";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "rea-ro";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO "rea-ro";
SQL

AUTH="$PREFIX/.ssh/authorized_keys"
RESTRICT="restrict,command=\"/opt/rea-ro/bin/inspect-agent\""
LINE="$RESTRICT $PUBKEY"
touch "$AUTH"
chmod 600 "$AUTH"
chown rea-ro:rea-ro "$AUTH"
if ! grep -Fq "$PUBKEY" "$AUTH"; then
  printf '%s\n' "$LINE" >> "$AUTH"
fi

echo "SAILINGSA_INSPECT_INSTALLED"
