# REA read-only inspect (both servers)

Permanent integration so ChatGPT can use the existing REA 6.4.0 MCP tunnel on
GoWifi to inspect live code and data on **both** production boxes.

## Architecture

```text
ChatGPT
  └── OpenAI Secure MCP Tunnel (same tunnel id; main channel only)
        └── /opt/rea/inspect/bin/mcp-mux
              ├── REA 6.4.0 (`/opt/rea/bin/rea mcp`) — all 170 tools
              └── /opt/rea/inspect/bin/audit-mcp — audit_* read-only tools
                    └── /opt/rea/inspect/bin/rea-inspect
                          ├── gowifi  → local inspect-agent
                          └── sailingsa → ssh rea-ro@102.218.215.253
                                          ForceCommand inspect-agent
```

ChatGPT does not merge extra tunnel channels into its tool list, so the
dedicated audit server is multiplexed onto `main` (and also bound as channel
`audit` for tunnel routing). `/opt/rea/.cursor/mcp.json` is unchanged.
The `rea-agents` package is not modified.

## What was missing

REA on GoWifi could already reverse-engineer **local** files and (after the
Chromium repair) launch a browser. It could not:

- reach SailingSA / TimAdvisor files or PostgreSQL
- default a browser executable for MCP callers
- expose a constrained SQL / log / nginx / revision / compare path

## Security controls

| Control | How |
| --- | --- |
| Authentication | Existing OpenAI tunnel key; SailingSA SSH key-only as `rea-ro` |
| Authorization | Path allowlists + SQL keyword denylist |
| Read-only | No sudo; ForceCommand; `GRANT SELECT` only; no production writes |
| Secret redaction | Agent strips passwords, tokens, DB URLs before return |
| Audit | JSONL logs on both boxes (`/opt/rea/inspect/audit`, `/opt/rea-ro/audit`) |
| Isolation | REA package, tunnel profile, nginx, and app services untouched |

Denied: `/root`, TLS private keys, OpenAI runtime key, REA SSH keys,
`sailingsa-api.service` (contains `DB_URL`), `.env` / `.pem` / backup blobs.

## Install (already applied on the boxes)

From a machine that can SSH as root to both servers:

```bash
# GoWifi
bash gowifi/rea/inspect/install-gowifi.sh /path/to/gowifi/rea/inspect
# then use the printed PUBKEY on SailingSA:
REA_INSPECT_PUBKEY='ssh-ed25519 AAAA...' bash gowifi/rea/inspect/install-sailingsa.sh /path/to/gowifi/rea/inspect
```

## Verify

```bash
sudo -u rea -H /opt/rea/bin/rea mcp doctor --json   # 170/170 still
# Mux on main must advertise 170 REA tools plus 9 audit_* tools.
sudo -u rea -H /opt/rea/inspect/bin/rea-inspect sailingsa schema
sudo -u rea -H /opt/rea/inspect/bin/audit-mcp   # stdio MCP; use a JSON-RPC initialize/tools/list probe
```

ChatGPT: refresh/republish the custom MCP connector, then start a new chat
and call `audit_*` (not `capture_process_scenario`).
