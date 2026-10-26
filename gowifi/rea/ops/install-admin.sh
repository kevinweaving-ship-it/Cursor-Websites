#!/bin/bash
# Safe REA management install. Run as root on each box.
# Updates the authenticated ForceCommand helper and rea-admin CLI.
# Does not add sudoers ALL, extra root keys, or a public endpoint.
# Does not restart WhatsApp, API, Bing, Stanford, or nginx.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/ops_helper.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/ops" >&2
  exit 1
}

if grep -q "def op_exec" "$SRC_DIR/ops_helper.py"; then
  echo "refusing to install unrestricted op_exec" >&2
  exit 1
fi

install -m 755 -o root -g root "$SRC_DIR/ops_helper.py" /usr/local/sbin/rea-ops-helper

if id rea >/dev/null 2>&1 && [ -d /opt/rea/ops/bin ]; then
  install -m 755 -o rea -g rea "$SRC_DIR/rea_ops.py" /opt/rea/ops/bin/rea-ops
  install -m 755 -o rea -g rea "$SRC_DIR/rea_ops.py" /opt/rea/ops/bin/rea_ops.py
  install -m 755 -o rea -g rea "$SRC_DIR/rea_admin.py" /opt/rea/ops/bin/rea-admin
  install -m 755 -o rea -g rea "$SRC_DIR/ops_mcp_server.py" /opt/rea/ops/bin/ops-mcp
  rm -f /etc/sudoers.d/rea-ops-admin
  if [ -f /opt/rea/.ssh/config ]; then
    python3 - <<'PY'
from pathlib import Path
p = Path("/opt/rea/.ssh/config")
text = p.read_text(encoding="utf-8")
if "Host sailingsa-root" in text:
    lines = text.splitlines(keepends=True)
    out = []
    skip = False
    for line in lines:
        if line.startswith("Host sailingsa-root"):
            skip = True
            continue
        if skip and line.startswith("Host "):
            skip = False
        if not skip:
            out.append(line)
    p.write_text("".join(out), encoding="utf-8")
    print("REMOVED_SAILINGSA_ROOT_HOST")
PY
  fi
  echo "GOWIFI_SAFE_ADMIN_INSTALLED"
fi

if id rea-ops >/dev/null 2>&1 && [ -d /opt/rea-ops/bin ]; then
  install -m 755 -o root -g rea-ops "$SRC_DIR/rea_ops.py" /opt/rea-ops/bin/ops-agent
  rm -f /etc/sudoers.d/rea-ops-admin
  if [ -f /root/.ssh/authorized_keys ]; then
    python3 - <<'PY'
from pathlib import Path
p = Path("/root/.ssh/authorized_keys")
lines = p.read_text(encoding="utf-8").splitlines()
kept = []
removed = 0
for line in lines:
    extra_root = (
        "REA-UNRESTRICTED-ADMIN" in line
        or "sailingsa-root" in line
        or ("rea-ops-helper" in line and "102.209.119.186" in line)
    )
    if extra_root:
        removed += 1
        continue
    kept.append(line)
p.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
print(f"AUTH_KEYS_REMOVED={removed}")
PY
  fi
  echo "SAILINGSA_SAFE_ADMIN_INSTALLED"
fi
