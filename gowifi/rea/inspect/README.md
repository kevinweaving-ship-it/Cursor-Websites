# REA read-only inspect (both servers)

Permanent integration so ChatGPT can use the existing REA 6.4.0 MCP tunnel on
GoWifi to inspect live code and data on **both** production boxes.

## Architecture

```text
ChatGPT
  └── OpenAI Secure MCP Tunnel (unchanged command: /opt/rea/bin/rea mcp)
        └── REA 6.4.0 on box.gowifi.co.za (user rea)
              ├── capture_browser_scenario → /opt/chromium/chrome
              ├── inspect_artifact / analyze_* → local allowlisted trees
              └── capture_process_scenario → /opt/rea/inspect/bin/rea-inspect
                    ├── gowifi  → local inspect-agent
                    └── sailingsa → ssh rea-ro@102.218.215.253
                                    ForceCommand /opt/rea-ro/bin/inspect-agent
                                    (read-only files, logs, SELECT SQL)
```

No second REA install. No public REA port. No change to
`/opt/rea/.cursor/mcp.json`.

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
sudo -u rea -H /opt/rea/bin/rea mcp doctor --json   # 170/170
sudo -u rea -H /opt/chromium/chrome --version
sudo -u rea -H /opt/rea/inspect/bin/rea-inspect sailingsa schema
sudo -u rea -H /opt/rea/inspect/bin/rea-inspect sailingsa sql 'SELECT current_user'
sudo -u rea -H /opt/rea/inspect/bin/rea-inspect gowifi list /opt/aerialnet-arial
```
