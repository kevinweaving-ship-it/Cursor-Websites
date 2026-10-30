# REA ops_* tools

ChatGPT should call these instead of `capture_process_scenario`.
Refresh the custom MCP connector after install, then start a new chat.

| Tool | Purpose |
| --- | --- |
| `ops_whatsapp_status` | Arial queue/connection/retry/log tails. No send. |
| `ops_inventory` | Services, timers, cron.d, docker, cert names |
| `ops_read_file` / `ops_write_file` | Allowlisted application files |
| `ops_logs` | Allowlisted journal units |
| `ops_service` | status / restart / reload of allowlisted units |
| `ops_nginx` | `nginx -t` or reload |
| `ops_db` | SELECT or constrained DML |
| `ops_run` | Allowlisted compile/check commands |
| `ops_git` | Local git; push only if remotes already work |
| `ops_backup` / `ops_rollback` | Scoped backup/restore |
| `ops_http_check` | GET-only allowlisted hosts |
| `ops_jobs` | Start/poll/cancel long allowlisted commands |
| `ops_health` | sailingsa-api / WhatsApp UP / nginx -t |
| `ops_deploy` | Existing api/frontend/static/whatsapp/aerialnet deploy |
| `ops_migrate` | `rea_ops` probe SQL only |
| `ops_deps` | compile/check or stage-venv pip |
| `ops_transfer` | Local copy or GoWifi → SailingSA stage |
| `ops_gh` | REA GitHub key/clone/probe-push (no private keys) |

Tunnel deadline is about 120 seconds. Use `ops_jobs` for longer work.

## Deploy kinds

| kind | Box | What it does |
| --- | --- | --- |
| `plan-api` | SailingSA | Live/staged/Gold hashes and whether a named revision would be allowed |
| `stage-api` | SailingSA | Copies live `api.py` into `/opt/rea-ops/stage` |
| `api` | SailingSA | Requires `approved_sha256` matching the staged file. Still honours the live Gold lock (size, known-stale hashes). Sets `ALLOW_API_REPLACE=1` only after that gate. Same-hash as live is a no-op (no restart). Recovery restart only if live actually changed and health failed. |
| `api-dry` | SailingSA | Same gate, then copy/compile/rollback under `/opt/rea-ops/stage/api-sandbox` only |
| `static` | SailingSA | Publishes `/opt/rea-ops/stage/rea-ops-probe.html` |
| `static-clean` | SailingSA | Removes the probe file |
| `frontend` | SailingSA | Safe unzip to the live web root, excludes `data/hub_hero.json`, blocks `..` paths |
| `frontend-sandbox` | SailingSA | Fixture ZIP extract under `/opt/rea-ops/stage/frontend-sandbox` (exclusions, zip-slip, ownership, rollback) |
| `whatsapp-code` | GoWifi | Copies staged `.py`/`.js` over existing WhatsApp files. Does not restart. |
| `aerialnet` | GoWifi | Copies staged aerialnet files. Does not restart. |

`arial-whatsapp-poc` restart is denied on GoWifi while the live session is UP.

## Safe management interface (ChatGPT / REA process tool)

No connector refresh required. Call as `rea` (NoNewPrivileges). This is
not a general root shell. Tokens are validated; destructive and
lockout-prone operations stay blocked.

```text
/opt/rea/ops/bin/rea-admin gowifi -- capabilities
/opt/rea/ops/bin/rea-admin gowifi -- status arial-whatsapp-poc
/opt/rea/ops/bin/rea-admin sailingsa -- capabilities
/opt/rea/ops/bin/rea-admin sailingsa -- inspect-arial
/opt/rea/ops/bin/rea-admin sailingsa -- status sailingsa-whatsapp-poc
/opt/rea/ops/bin/rea-admin sailingsa -- can-control arial-whatsapp-poc
/opt/rea/ops/bin/rea-admin sailingsa -- nginx test
```

Authenticated localhost/root ForceCommand on GoWifi; `ssh sailingsa-ops`
ForceCommand on SailingSA. Private keys stay on the boxes. `exec-b64`,
`sudo ALL`, and extra root SSH aliases are not installed.

## Arial leftover lifecycle (SailingSA)

ChatGPT / REA CLI (as `rea` via `ssh sailingsa-ops`):

```text
ssh -o BatchMode=yes sailingsa-ops inspect-arial
ssh -o BatchMode=yes sailingsa-ops status arial-whatsapp-poc
ssh -o BatchMode=yes sailingsa-ops journal arial-whatsapp-poc 80
ssh -o BatchMode=yes sailingsa-ops status sailingsa-whatsapp-poc
ssh -o BatchMode=yes sailingsa-ops retarget-ingest
ssh -o BatchMode=yes sailingsa-ops backup sailingsa-arial-leftover
ssh -o BatchMode=yes sailingsa-ops stop arial-whatsapp-poc
ssh -o BatchMode=yes sailingsa-ops disable arial-whatsapp-poc
ssh -o BatchMode=yes sailingsa-ops decommission arial-whatsapp-poc
```

Protected (denied): `sailingsa-whatsapp-poc`, `event-whatsapp-ingest`.
Bing/Stanford stay running until a GoWifi install is verified. Auth/session dirs are never copied.
