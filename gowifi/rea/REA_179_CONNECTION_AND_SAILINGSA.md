# REA 179-tool connection fix and SailingSA read-only audit

**Date:** 18 October 2026 (SAST).  
**Re-verified:** 31 October 2026 (SAST) — live mux now also merges `ops_*` (see §4.1).  
**Production writes:** none (SailingSA code, PostgreSQL rows, and nginx were not modified).  
**Tunnel:** `tunnel_6ad4db67cc24819192e1938a21a5f663` (“GoWifi REA”), credentials unchanged.

Raw inspect JSON is on the GoWifi box at `/opt/rea/inspect/audit/sailingsa-arch-20261018/`.
Related live ops docs: `docs/REA_CHATGPT_ACCESS.md`, `gowifi/rea/ops/CATALOG.md`.

## 1. Why ChatGPT discovered 170 tools, not 179

ChatGPT’s custom MCP connector talks to tunnel channel **`main` only**. Extra channels are not merged into its tool list.

Before this fix:

- `main` was originally `/opt/rea/bin/rea mcp` → **170 REA tools**.
- The later profile bound `main` to `/opt/rea/inspect/bin/mcp-mux` (170 REA + 9 `audit_*`) **and** registered a second MCP server as `channel: audit` → `/opt/rea/inspect/bin/audit-mcp`.
- `mcp-mux` already returned **179 unique tools** when probed locally.
- ChatGPT still showed 170 because (a) it ignores the extra `audit` channel, and (b) the connector caches the catalog from the last `tools/list` (the pre-mux 170-tool REA identity).

## 2. Mux on the existing main channel

`/opt/rea/inspect/bin/mcp-mux` still:

- starts REA (`/opt/rea/bin/rea mcp`) and `audit-mcp` as stdio children
- (after #260) also starts `/opt/rea/ops/bin/ops-mcp`
- keeps MCP identity `rea` / `6.4.0`
- merges `tools/list` (REA first, then `audit_*` / `ops_*` if the name is new)
- routes `ops_*` → `ops-mcp`, `audit_*` → `audit-mcp`, everything else → REA

No second tunnel, no duplicate tool names. Do **not** add a second YAML channel.

## 3. Configuration correction

Edited only `/opt/openai-tunnel/profiles/rea-box.yaml` (backup `rea-box.yaml.bak-drop-audit-channel-20261018185858`).

`mcp.commands` is now a single entry:

```yaml
mcp:
  commands:
    - channel: main
      command: "/opt/rea/inspect/bin/mcp-mux"
```

Restarted **only** `openai-rea-tunnel.service`. Same tunnel id, same `file:/opt/openai-tunnel/runtime.key`.

After restart:

- `/healthz` live, `/readyz` ready
- channels: **`main`** (stdio `mcp-mux`, `probe_status: ok`) + disabled `harpoon`
- process tree (18 Oct): `tunnel-client` → `mcp-mux` → `rea mcp` + `audit-mcp`
- process tree (31 Oct re-check): same, plus `ops-mcp` as a third mux child

## 4. `tools/list` verification

Probed as user `rea` against `/opt/rea/inspect/bin/mcp-mux` (NDJSON `initialize` + `tools/list`) on **18 Oct 2026**:

| Metric | Value |
| --- | --- |
| Server | `rea` 6.4.0 |
| Tool count | **179** |
| Unique names | **179** |
| Duplicates | none |
| `audit_*` | 9 |

Audit tools present:

`audit_compare`, `audit_database_schema`, `audit_deployment`, `audit_discover`, `audit_logs`, `audit_nginx`, `audit_read_file`, `audit_search_source`, `audit_select_query`.

Standalone `audit-mcp` still advertises those nine tools with `readOnlyHint: true`.

`/health/mcp` remains `not_observed` because the tunnel health UI does not issue `initialize`/`tools/list`. That is expected and is not a mux failure.

### 4.1 Re-verification — 31 October 2026 (SAST)

Live profile is still **main-only** → `mcp-mux`. No `channel: audit`. Tunnel id unchanged. `/healthz` live, `/readyz` ready.

| Metric | Value |
| --- | --- |
| Server | `rea` 6.4.0 |
| Unique tools | **201** |
| Duplicates | none |
| REA tools | 170 |
| `audit_*` | 9 (all present) |
| `ops_*` | 22 |

`ops_*` names: `ops_backup`, `ops_db`, `ops_deploy`, `ops_deps`, `ops_gh`, `ops_git`, `ops_health`, `ops_http_check`, `ops_inspect_arial`, `ops_inventory`, `ops_jobs`, `ops_logs`, `ops_migrate`, `ops_nginx`, `ops_read_file`, `ops_retarget_ingest`, `ops_rollback`, `ops_run`, `ops_service`, `ops_transfer`, `ops_whatsapp_status`, `ops_write_file`.

Smoke (read-only / capabilities only):

- `rea-inspect sailingsa sql "SELECT current_user, current_database()"` → `rea-ro` / `sailors_master`
- `rea-admin sailingsa -- capabilities` → ForceCommand helper, Gold lock on, no general root shell
- `rea-admin gowifi -- capabilities` → helper OK

The 179-tool fix remains the correct base. #260 added scoped `ops_*` onto the **same** `main` mux. ChatGPT must still refresh the connector to see anything beyond its cached catalog.

## 5. ChatGPT plugin refresh — remaining limitation

Server-side connector refresh is **not supported** with the runtime key on this box.

- `tunnel-client admin tunnels get tunnel_6ad4db67cc24819192e1938a21a5f663` → **401 Unauthorized** (`x-request-id: req_b4b97f591f754130a8a2c4194469b9aa`).
- `admin tunnels list/update` need an OpenAI **admin** key (`OPENAI_ADMIN_KEY`). None is configured.
- Restarting the tunnel does not push a new catalog into ChatGPT. ChatGPT caches tools until the custom MCP connector is rediscovered.

**Remaining ChatGPT-side step (must be done in the ChatGPT UI):**

1. Open [ChatGPT connector settings](https://chatgpt.com/#settings/Connectors).
2. Refresh / republish the existing **GoWifi REA** custom MCP connector (do not create a second connector).
3. Start a **new** chat and confirm the full mux catalog (**201** unique tools as of 31 Oct 2026: 170 REA + 9 `audit_*` + 22 `ops_*`).

Until that UI refresh, ChatGPT can keep showing a cached older count (170 or 179) even though the tunnel already serves 201.

## 6. Read-only confirmation (SailingSA)

Inspect path: `rea` → `rea-inspect sailingsa` → SSH `rea-ro@102.218.215.253` with `/opt/rea/.ssh/id_rea_sailingsa`, ForceCommand `inspect-agent`.

Allowlists (from `help`): `/var/www/sailingsa`, `/var/www/timadvisor`, named nginx files/sites, logs `nginx-error` / `nginx-access` / `sailingsa-api`. Database: PostgreSQL `sailors_master`.

| Probe | Result |
| --- | --- |
| `get /root/secrets` | `path_denied` / `denied_path` |
| `get /opt/openai-tunnel/runtime.key` | `path_denied` |
| `get /etc/systemd/system/sailingsa-api.service` | `path_denied` |
| `list /etc/nginx` (whole tree) | `path_denied` / `not_allowlisted` |
| `INSERT` / `UPDATE` / `DROP` / `COPY` | `sql_denied` / `not_read_only` |
| Multi-statement SQL | `sql_denied` / `multiple_statements` |
| SSH `uname -a` via ForceCommand | `unknown_op` (no shell) |
| Table privileges for `rea-ro` | **SELECT only** (157 grants, 0 non-SELECT) |

Reads that succeeded: live `api.py` (4 059 962 bytes), `index.html`, nginx site configs, `information_schema`, SELECT counts.

## 7. Architecture and database audit (read-only)

### Runtime shape

- **Public site:** nginx `sailingsa.co.za` / `www` — HTTP 301 to HTTPS, document root `/var/www/sailingsa`.
- **App:** FastAPI monolith `/var/www/sailingsa/api/api.py` (~4.06 MB, mtime 2026-10-18 16:21 UTC), proxied at `127.0.0.1:8000` for `/`, `/api/`, `/sailor`, `/regatta`, `/club`, `/class`, plus `@api` fallback.
- **Same nginx file also reverse-proxies keypad APIs** on this host: `/api/arial/` → `:8003`, `/api/voelklip/` → `:8004`, `/api/stanford/` → `:8005`, `/api/bing/` → `:8006`.
- **TimAdvisor** is a separate vhost (`00-timadvisor`) on the same box (`/var/www/timadvisor`, API `:8766`).
- Entity pages (`/sailor/`, `/club/`, `/class/`, `/boat/`) use `ssa_entity` cache + rate/conn limits.
- `/results` 301s to `/events`. Probe paths (PHP/WordPress/`.env`/`.git`) return 403.
- Live `api.py` SHA `42fe3896…` **differs** from the inspect-box repo snapshot. `index.html` / `blank.html` were rewritten 18 Oct 17:00 UTC. No git metadata on those revision roots.

### Static vs git drift

`audit_compare` against `/opt/rea/inspect/repo`:

| Live path | Status |
| --- | --- |
| `/var/www/sailingsa/api/api.py` | **differ** |
| `/var/www/sailingsa/index.html` | **differ** |
| `/var/www/sailingsa/blank.html` | live_only (snapshot missing) |
| `js` / `css` / `templates` dirs | compare is file-only (expected) |

Static `index.html` still opens with `lang="en-US"` (SSR routes were separately set to `en-ZA`). `sitemap-priority.xml` still exists on disk next to `sitemap-core.xml`.

Recent discover hits: `blank.html`, `index.html`, sitemap XML, `js/club-page-wizard.js`.

Club/event UI on live includes `js/club-page-wizard.js` and `js/club-score-edit.js`. `club_season_items` has three rows (HYC/ZVYC wizard fixtures). Native club entries are still tiny (`entries` = 51) versus published `results` (11 231).

### PostgreSQL `sailors_master`

Session: `current_user=rea-ro`, database `sailors_master`. Agent denylist blocks writes even though `transaction_read_only=off`; Postgres grants are SELECT-only.

| Object | Count / size |
| --- | --- |
| Public base tables | 131 |
| Public views | 26 |
| `app` schema tables | 2 (`regatta_339_results`, template) |
| Public columns | 7 511 |
| `sas_id_personal` (people; there is no `sailors` table) | **26 138** |
| `clubs` | **85** |
| `classes` | **202** |
| `regattas` | **479** |
| `results` | **11 231** |
| `events` (calendar/scrape, 406 linked to a `regatta_id`) | **1 302** |
| `entries` | **51** |
| `boats` | **3 168** |
| `member_roles` | **959** |
| `sailor_public_mentions` | **1 083** |
| `club_season_items` | **3** |

Largest relations: `lipton_telemetry` **2 652 MB** (~4.36M estimated rows), `site_traffic_events` 237 MB, `session_page_hits` 34 MB, `public_page_hits` 25 MB, `ranking_audit_contribs` 24 MB, `results` 22 MB.

`regattas.result_status`: Final 360, Provisional 106, `event_page` 7, null 4, `published` 2.

Integrity: indexes include primary-key unique indexes, but `information_schema` reports **0 FOREIGN KEY** constraints and **0 PRIMARY KEY** constraint rows (1 UNIQUE constraint). Referential integrity is application-side, not declared in PostgreSQL.

Identity is **`sas_id_personal.sa_sailing_id`**, not a `sailors` table. Results join people via `helm_sa_sailing_id` / `crew_sa_sailing_id`. Roles live in `member_roles.role_code` (instructors, race officers, judges, coaches — not the web `super_admin` / club-admin ACL, which is in live `api.py`).

### Implications

1. Live SailingSA is still a **publish-and-profile site** plus a small club-admin / wizard overlay; it is not a full native scoring platform. Evidence: 11k imported `results` vs 51 `entries`, 479 `regattas` vs 1 302 scraped `events`.
2. **Live `api.py` is the source of truth** and has drifted from the inspect snapshot / git copy.
3. The nginx vhost is a **shared edge** for SailingSA, TimAdvisor, and four Arial keypad APIs. Club/SEO work on this file must not disturb those locations.
4. `lipton_telemetry` dominates disk; traffic/hit tables are next. Schema work should treat those as telemetry, not core racing data.
5. No declared FKs: joins must be validated in application code; orphaned `host_club_id` / SAS ids are possible.
6. Audit user `rea-ro` can read production source, schema, and nginx site files, and cannot write them.

SailingSA production code, database records, and website configuration were left unchanged.
