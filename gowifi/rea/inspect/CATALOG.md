# REA / ChatGPT audit catalog

ChatGPT should call the dedicated `audit_*` MCP tools. Do **not** use
`capture_process_scenario` for production audits (OpenAI safety checks treat
that generic process launcher as high-risk).

## Dedicated read-only tools

All advertise `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`.

| Tool | Purpose |
| --- | --- |
| `audit_discover` | New/changed allowlisted files (`gowifi`, `sailingsa`, `both`) |
| `audit_read_file` | Read one allowlisted source/config file |
| `audit_search_source` | Find files by glob under an allowlisted root |
| `audit_database_schema` | information_schema (SailingSA `sailors_master`) |
| `audit_select_query` | One SELECT/WITH/EXPLAIN/SHOW query |
| `audit_nginx` | Allowlisted nginx site configs |
| `audit_logs` | `nginx-error`, `nginx-access`, `sailingsa-api` |
| `audit_deployment` | Live revision metadata |
| `audit_compare` | Live SailingSA files vs repo snapshot |

Existing REA tools remain available (170). Browser work still uses
`capture_browser_scenario` with `executable_path: /opt/chromium/chrome`.

## Dedicated ops tools

`ops_*` tools (see `gowifi/rea/ops/`) perform scoped writes, checks,
backups, allowlisted service control, and WhatsApp diagnosis. They are
not generic shell. Refresh the ChatGPT connector after install.

## ChatGPT discovery

The custom MCP plugin talks to tunnel channel `main` only. Extra tunnel
channels are not merged into ChatGPT’s tool list. After these tools are added,
refresh or republish the ChatGPT custom MCP / connector so it rediscovers
tools. Start a new chat after refresh.

## Security

Inspect agents stay read-only. `ops_*` adds scoped writes through ACLs and
ForceCommand helpers. Secrets, WhatsApp auth state, and unrestricted root
remain denied. No arbitrary shell.
