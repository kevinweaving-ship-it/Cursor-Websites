#!/bin/bash
# Run on Kevin's Mac Mini / Cursor Desktop only.
# Creates ~/.ssh/rea_gowifi if missing, merges rea-gowifi into ~/.cursor/mcp.json
# without removing other servers, then verifies REA 6.4.0 over SSH.
# Does not install rea-agents locally. Does not touch production.
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This script is for macOS Cursor Desktop. Refusing to run on $(uname -s)." >&2
  exit 1
fi

KEY="$HOME/.ssh/rea_gowifi"
MCP="$HOME/.cursor/mcp.json"
BAK="$HOME/.cursor/mcp.json.rea-gowifi.bak"

mkdir -p "$HOME/.ssh" "$HOME/.cursor"
chmod 700 "$HOME/.ssh"

if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "cursor-rea-gowifi@$(hostname)"
  echo "created $KEY"
else
  echo "reusing $KEY"
fi
chmod 600 "$KEY"

echo "PUBLIC_KEY=$(cat "$KEY.pub")"

python3 - "$MCP" "$BAK" "$KEY" <<'PY'
import json, os, shutil, sys
mcp_path, bak_path, key_path = sys.argv[1:4]
entry = {
    "command": "ssh",
    "args": [
        "-i", key_path,
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
        "rea@box.gowifi.co.za",
        "/opt/rea/bin/rea",
        "mcp",
    ],
}
data = {"mcpServers": {}}
if os.path.exists(mcp_path):
    shutil.copy2(mcp_path, bak_path)
    with open(mcp_path, "r", encoding="utf-8") as f:
        raw = f.read().strip() or "{}"
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise SystemExit("mcp.json is not a JSON object")
    servers = parsed.get("mcpServers")
    if servers is None:
        parsed["mcpServers"] = {}
    elif not isinstance(servers, dict):
        raise SystemExit("mcpServers is not an object; refusing to overwrite")
    data = parsed
else:
    open(bak_path, "w", encoding="utf-8").write("{}\n")

existing = list((data.get("mcpServers") or {}).keys())
data.setdefault("mcpServers", {})
data["mcpServers"]["rea-gowifi"] = entry
tmp = mcp_path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, mcp_path)
print("backup", bak_path)
print("kept_servers", ",".join(existing) or "(none)")
print("now_servers", ",".join(data["mcpServers"].keys()))
PY

echo "Testing SSH as rea (BatchMode, key only)..."
ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=20 \
  rea@box.gowifi.co.za '/opt/rea/bin/rea --version'

echo "Fully quit Cursor Desktop and reopen so rea-gowifi is loaded."
echo "If SSH failed with Permission denied, add the PUBLIC_KEY line to /opt/rea/.ssh/authorized_keys on the box (add-cursor-pubkey.sh)."
