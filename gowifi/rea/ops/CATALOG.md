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

Tunnel deadline is about 120 seconds. Use `ops_jobs` for longer work.
