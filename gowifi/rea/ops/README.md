# REA ops access (Arial / GoWifi + SailingSA)

Gives ChatGPT + REA scoped operational access on both boxes without
unrestricted root. The existing isolated REA 6.4.0 install and
`rea-ro` inspect path stay in place.

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
