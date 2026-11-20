# REA ops access (Arial / GoWifi + SailingSA)

Gives ChatGPT + REA scoped operational access on both boxes without
unrestricted root. The existing isolated REA 6.4.0 install and
`rea-ro` inspect path stay in place. A later request for a general
root shell was superseded: `rea-admin` only forwards validated helper
verbs through the existing ForceCommand path.

```text
ChatGPT
  └── OpenAI Secure MCP Tunnel (User=rea, NoNewPrivileges=yes)
        └── /opt/rea/inspect/bin/mcp-mux
              ├── REA 6.4.0
              ├── audit_*   (read-only inspect)
              └── ops_*     (scoped writes, checks, backups, service control)
                    ├── local ACL / journal group / probe DBs
                    ├── localhost ForceCommand helper (GoWifi privileged ops)
                    └── ssh sailingsa-ops → rea-ops ForceCommand (SailingSA)
```

Tunnel `NoNewPrivileges=yes` blocks sudo and setuid from ChatGPT's process.
Privileged actions reuse the existing localhost SSH ForceCommand pattern
(`/usr/local/sbin/rea-ops-helper`), same idea as `roundup-timer-ctl`.

## Identities

| Box | Identity | Role |
| --- | --- | --- |
| Arial / GoWifi `102.209.119.186` | `rea` (UID 996) | ChatGPT execution account |
| SailingSA `102.218.215.253` | `rea-ro` (UID 987) | unchanged read-only inspect |
| SailingSA | `rea-ops` | write/deploy/git/db DML via ForceCommand |

## Persistence

ACL, sudoers, systemd, SSH keys, and group membership survive reboot.
After a connector or tunnel update, ChatGPT must refresh the custom MCP
plugin and start a new chat.

## Recovery

See `docs/REA_CHATGPT_ACCESS.md`.

## Graphify (preferred code discovery)

Graphify is the preferred REA/agent path for code discovery on both boxes
**before** bulk `Read`/`Grep` of large sources. Keep normal source inspection
as fallback when the graph is missing or a query is insufficient.

### Approved project roots

| Box | Roots |
| --- | --- |
| GoWifi | `/opt/arial-whatsapp-poc`, `/opt/aerialnet-arial`, `/opt/rea/work/sailing-roundup` |
| SailingSA | `/var/www/sailingsa`, `/var/www/timadvisor` |

Each root should have `<root>/graphify-out/graph.json` (AST extract). Rebuild
with `graphify extract <root> --code-only` when needed (install is separate;
do not reinstall casually).

### Allowed via `ops_run` only

`run_allowlist` permits only:

- `graphify query`
- `graphify path`
- `graphify explain`

Always pass an absolute graph under an approved root (REA does not chdir):

```text
ops_run argv=["graphify","query","<question>","--graph","/var/www/sailingsa/graphify-out/graph.json","--budget","2000"]
ops_run argv=["graphify","path","A","B","--graph","/opt/arial-whatsapp-poc/graphify-out/graph.json"]
ops_run argv=["graphify","explain","symbol","--graph","/opt/aerialnet-arial/graphify-out/graph.json"]
```

`ops_run` still enforces `allow_read_paths` on absolute `--graph` arguments.

### Denied via `ops_jobs` (Option B)

All Graphify invocations through `ops_jobs` are fail-closed denied
(`graphify_denied_via_jobs`), including absolute binary paths and
`python -m graphify[y]`. Non-Graphify jobs are unchanged.

Also denied on `ops_run` (not allowlisted): `extract`, `update`, `cursor`,
`hook`, and any other Graphify write/install subcommands.

### Agent rule of thumb

1. Prefer `graphify query|path|explain` with `--graph` for architecture /
   dependency questions.
2. Fall back to targeted file reads when the graph has no match or you must
   edit specific lines.
3. Never use `ops_jobs` for Graphify.

## Sync after code changes

On each box, as root:

```bash
bash /path/to/gowifi/rea/ops/sync-ops.sh /path/to/gowifi/rea/ops
```

This copies binaries/config only. It restarts `openai-rea-tunnel` on
GoWifi so ChatGPT rediscovers tools. It does not restart WhatsApp or
`sailingsa-api`. Then refresh the ChatGPT connector.
