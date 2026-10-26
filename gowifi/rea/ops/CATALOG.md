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

`arial-whatsapp-poc` restart is denied while the live session is UP.
