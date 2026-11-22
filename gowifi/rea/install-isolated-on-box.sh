#!/bin/bash
# Isolated REA (Reverse Engineer Anything) install for the GoWifi box.
# Official sources: https://github.com/morluto/rea  and  https://rea.tools/get-started/
#
# Isolation rules:
#   - Installs only under /opt/rea as system user `rea`
#   - Own Node 24 LTS tree (does not use /opt/arial-whatsapp-poc/node or Playwright)
#   - Does not read or write GoWifi/Aerialnet/Mail-in-a-Box paths, DBs, nginx, or secrets
#   - Does not install Hopper/Ghidra/IDA or register systemd listeners
#   - Does not restart production services
#
# Run on the box as root:
#   bash /opt/rea-install/install-isolated-on-box.sh
set -euo pipefail

REA_USER="rea"
REA_HOME="/opt/rea"
NODE_VERSION="v24.21.0"
NODE_URL="https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz"
INSTALL_SH_URL="https://raw.githubusercontent.com/morluto/rea/main/install.sh"
PROTECTED_PATHS=(
  /root/gowifi-upp
  /root/secrets
  /home/user-data
  /opt/aerialnet-arial
  /opt/arial-whatsapp-poc
  /var/www/aerialnet
  /etc/nginx
  /etc/mysql
  /var/lib/mysql
)

log() { printf '[rea-isolated] %s\n' "$*"; }
die() { printf '[rea-isolated] ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run as root"

for p in "${PROTECTED_PATHS[@]}"; do
  [ -e "$p" ] || continue
  case "$REA_HOME" in
    "$p"|"$p"/*) die "refusing to install under protected path $p" ;;
  esac
done

# Refuse if someone pointed REA_HOME at a production tree.
case "$REA_HOME" in
  /root/gowifi-upp*|/root/secrets*|/home/user-data*|/opt/aerialnet*|/opt/arial-whatsapp-poc*|/var/www/*|/etc/nginx*)
    die "REA_HOME $REA_HOME is a production path"
    ;;
esac

log "creating isolated user and prefix"
if ! id "$REA_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$REA_HOME" --shell /bin/bash \
    --comment "REA isolated analysis (no production access)" "$REA_USER"
fi
# Keep the home even if useradd already existed with a different home.
usermod --home "$REA_HOME" --shell /bin/bash "$REA_USER" >/dev/null
mkdir -p "$REA_HOME" "$REA_HOME/bin" "$REA_HOME/samples/demo-app" "$REA_HOME/.ssh"
chmod 750 "$REA_HOME"
chmod 700 "$REA_HOME/.ssh"
chown -R "$REA_USER:$REA_USER" "$REA_HOME"

# No password, no sudo, no production groups.
passwd -l "$REA_USER" >/dev/null
if getent group sudo >/dev/null; then
  gpasswd -d "$REA_USER" sudo >/dev/null 2>&1 || true
fi

if [ -n "${REA_SSH_PUBKEY:-}" ]; then
  log "installing Cursor SSH public key for user $REA_USER"
  auth="$REA_HOME/.ssh/authorized_keys"
  touch "$auth"
  chmod 600 "$auth"
  if ! grep -Fqx "$REA_SSH_PUBKEY" "$auth"; then
    printf '%s\n' "$REA_SSH_PUBKEY" >> "$auth"
  fi
  chown "$REA_USER:$REA_USER" "$auth"
fi

if [ ! -x "$REA_HOME/node/bin/node" ]; then
  log "installing isolated Node.js ${NODE_VERSION} into ${REA_HOME}/node"
  tmp=$(mktemp -d /tmp/rea-node.XXXXXX)
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL "$NODE_URL" -o "$tmp/node.tar.xz"
  tar -xJf "$tmp/node.tar.xz" -C "$tmp"
  rm -rf "$REA_HOME/node"
  mv "$tmp/node-${NODE_VERSION}-linux-x64" "$REA_HOME/node"
  chown -R "$REA_USER:$REA_USER" "$REA_HOME/node"
  rm -rf "$tmp"
  trap - EXIT
else
  log "isolated Node already present: $("$REA_HOME/node/bin/node" -v)"
fi

"$REA_HOME/node/bin/node" -v | grep -Eq '^v(22\.(1[9-9]|[2-9][0-9])|24\.(1[1-9]|[2-9][0-9])|2[6-9]|[3-9])' \
  || die "isolated Node $($REA_HOME/node/bin/node -v) does not meet REA 22.19+/24.11+/26+"

log "running official REA installer (no agent setup, no Hopper)"
# Official install.sh writes to $HOME/.local on Linux and skips setup with --no-setup.
sudo -u "$REA_USER" -H env \
  HOME="$REA_HOME" \
  PATH="$REA_HOME/node/bin:/usr/bin:/bin" \
  npm_config_prefix="$REA_HOME/.local" \
  bash -c 'curl -fsSL "'"$INSTALL_SH_URL"'" | bash -s -- --no-setup'

[ -x "$REA_HOME/.local/bin/rea" ] || die "official installer did not produce $REA_HOME/.local/bin/rea"

cat > "$REA_HOME/bin/rea" <<'WRAP'
#!/bin/bash
# Isolated wrapper: own Node + own npm prefix only. Never inherit production PATH first.
set -euo pipefail
export HOME="${HOME:-/opt/rea}"
export PATH="/opt/rea/node/bin:/opt/rea/.local/bin:/usr/bin:/bin"
exec /opt/rea/.local/bin/rea "$@"
WRAP
chmod 755 "$REA_HOME/bin/rea"
chown "$REA_USER:$REA_USER" "$REA_HOME/bin/rea"

cat > "$REA_HOME/samples/demo-app/package.json" <<'JSON'
{
  "name": "rea-isolated-demo",
  "version": "1.0.0",
  "private": true,
  "description": "Harmless sample owned by this install; used only to verify REA JS analysis."
}
JSON

cat > "$REA_HOME/samples/demo-app/index.js" <<'JS'
'use strict';

function greet(name) {
  return 'hello ' + String(name || 'world');
}

function add(a, b) {
  return Number(a) + Number(b);
}

module.exports = { greet, add };

if (require.main === module) {
  process.stdout.write(greet('rea') + ' ' + add(2, 3) + '\n');
}
JS
chown -R "$REA_USER:$REA_USER" "$REA_HOME/samples"

cat > "$REA_HOME/README.BOX.md" <<'MD'
# Isolated REA on this box

- User: `rea` (no password, no sudo)
- Prefix: `/opt/rea` only
- CLI: `/opt/rea/bin/rea`
- Official package: `rea-agents` from npm / morluto/rea
- Do not point REA at `/root/secrets`, `/root/gowifi-upp`, `/home/user-data`, or Aerialnet trees
MD
chown "$REA_USER:$REA_USER" "$REA_HOME/README.BOX.md"

log "installed $($REA_HOME/bin/rea --version) as user $REA_USER"
log "isolation prefix: $REA_HOME"
