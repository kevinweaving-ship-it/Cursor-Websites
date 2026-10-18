# REA inspect catalog (ChatGPT / MCP)

Use the existing REA 6.4.0 MCP tools. Do not add another MCP server.

## Browser / rendered pages / HTTP

`capture_browser_scenario` with:

```json
{
  "browser": {
    "mode": "launch",
    "executable_path": "/opt/chromium/chrome",
    "headless": true
  },
  "start_url": { "url": "https://sailingsa.co.za/", "query": [] },
  "actions": [
    { "step_id": "settle", "action": "wait_for_timeout", "duration_ms": 2000 }
  ],
  "capture": { "at_end": ["url", "dom"], "events": ["console", "page-errors", "network"] }
}
```

Chromium is pinned at `/opt/chromium/chrome` (Playwright 1.58.2 / revision 1208).
`REA_BROWSER_EXECUTABLE` is set on the existing `openai-rea-tunnel` unit.

Existing SEO crawler (no JS): `/opt/rea/seo/bin/siteone-crawler` via
`capture_process_scenario` only if a bounded read-only crawl is required.

## Live source, config, logs, SQL

`capture_process_scenario`:

- `executable`: `/opt/rea/inspect/bin/rea-inspect`
- `arguments`: `[target, op, ...]`
- `working_directory`: `/opt/rea/inspect`
- `target`: `gowifi` | `sailingsa` | `both`

Examples:

```text
sailingsa schema
sailingsa sql SELECT count(*) FROM sailors
sailingsa get /var/www/sailingsa/api/api.py
sailingsa list /var/www/sailingsa/templates
sailingsa find /var/www/sailingsa *.py
sailingsa logs sailingsa-api
sailingsa nginx
sailingsa revision
sailingsa compare
gowifi list /opt/aerialnet-arial
gowifi get /opt/aerialnet-arial/arial_app.py
both discover
```

Static catalog file (this document): `inspect_artifact` on `/opt/rea/inspect/CATALOG.md`.

Local GoWifi trees are also readable directly with `inspect_artifact` /
`analyze_javascript_application` under the allowlisted paths.

## Security

- Read-only. SQL allows `SELECT` / `WITH` / `EXPLAIN` / `SHOW` only.
- Secrets in file/log text are redacted.
- SailingSA SSH is key-only, `restrict` + ForceCommand to the inspect agent.
- Production services, REA package files, Cursor `mcp.json`, and the tunnel
  command are unchanged.
