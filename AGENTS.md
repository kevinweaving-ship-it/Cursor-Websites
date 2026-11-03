# Agent / task-splitting guide

This project uses **split tasks** to avoid agent resource limits and crashes.

## SSH / deploy / live — how work actually runs

**`sailingsa/deploy/SSH_LIVE.md`** is the primary source for deploy, fix, sync, and SSH. **`sailingsa/deploy/PROD_RULES.md`** is the live edit protocol (read-only check, snapshot, then change).

Cloud or Mac is fine. Do the task in the session the user opened. SSH to the live box is normal work. Use the commands in the readme (`~/.ssh/sailingsa_live_key`, `root@102.218.215.253`). If a deploy or fix was asked for, run it. Local-only edits do not change https://sailingsa.co.za.

**Production host:** `102.218.215.253` (`sailingsa.co.za`). Other boxes (Gowifi, Aerial, Zabbix, or any host not in `SSH_LIVE.md`) are in scope only when the user names that box in the same message.

### Standard live work — do it when asked

- SSH read and status: `systemctl status`, `journalctl`, `nginx -t`, `ls`, `curl`, read-only `psql` on `sailors_master`.
- Documented deploys: `bash sailingsa/deploy/deploy-with-key.sh` (or `push-to-cloud-expect.exp`), `deploy_api.sh` / `deploy_api_verified.sh`, `sync-385-local-to-live.sh`.
- Restart `sailingsa-api` after an api deploy, or when status shows the service is down. Confirm `active`.
- `pre-change-backup.sh` before other frontend or `api.py` edits, then the snapshot / `chattr` cycle in `PROD_RULES.md` when editing live `api.py`.
- Nginx reload only for the location blocks already documented in `SSH_LIVE.md`.

### Stop and wait — user must authorize in that same message

Ask, then stop, when the action can take down a box or a public service, or can replace live data. The user must authorize that action in the same message (for example “authorize rollback” or “yes, restore the backup”). A general “fix live” or “look at the box” is not that authorization.

Wait for that authorization before:

- Restore, rollback, or copy a backup over live files (`fix-live-rollback-api.exp` and any baseline restore).
- `stop`, `disable`, or `mask` of `sailingsa-api`, nginx, or PostgreSQL. Reboot.
- `DROP`, `TRUNCATE`, or a mass `DELETE` / `UPDATE` on production tables. Schema changes that drop columns or tables.
- Nginx or firewall changes outside the documented location blocks. SSH keys, `sshd_config`, users, passwords.
- Package upgrades, disk cleanup, or anything else that reboots or fills the box.
- Service changes on a named extra box (Gowifi, Aerial, Zabbix). Read-only SSH and a report on a box the user named are standard. Changing that box is not.

If a task mixes both, do the standard part and leave the high-impact part unrun until the user authorizes it.

## Avoid frontend drift / wrong-layer fixes

**`docs/AVOID_FRONTEND_DRIFT_AND_WRONG_LAYER.md`** — Do **not** add local-only frontend changes that diverge from live. Do **not** fix the frontend when the failure is backend or DB (e.g. "Failed to load regatta data" → diagnose API/DB first; fix SQL or data). Match live first; fix the layer that is actually broken.

## Crash README (Crash RM)

**`docs/CRASH_README.md`** — When the user says "refer to crash RM" or "crash readme": (1) run the resource test (`python3 scripts/resource_test_standings_and_profile.py`), (2) do an issue check for crash cause and fix using that doc.

## Resource use / avoiding crashes

- **One active agent at a time**: Close other agent chats or Composer sessions while working on this project so resources are not shared and the current agent is less likely to crash.
- **Keep requests small**: One clear task per message; for big work, ask to "split into steps" and do step 1 only.
- **Agents**: Use minimal context (targeted reads, small edits, few tool calls per turn). See `.cursor/rules/task-splitting-and-resources.mdc` for the full rule.

## For humans

- Give **one clear, small task** per request when possible (e.g. "add a logout button to the header" not "redo the whole header and auth").
- For big work, say: "Split this into steps" or "Do step 1 only" so the agent can break it down and do one step per run.

## For agents

- **Regatta iframe sheets (locked):** Do **not** edit `class-results.html` or `results.html` under `sailingsa/frontend/regatta/` and `public/regatta/` unless the user writes exactly **`override lock`**. See **`.cursor/rules/regatta-results-sheets-readonly.mdc`**. Before other frontend or `api.py` edits, run **`bash sailingsa/deploy/pre-change-backup.sh`** and confirm the server backup tarball exists.
- Follow the rule in **`.cursor/rules/task-splitting-and-resources.mdc`**: one logical task per session, use todos for multi-step work, narrow scope, targeted reads.
- If the user’s request is large, propose a short list of steps and do **only the first step** unless they ask for more.

## Named agents / tasks

Use these names to scope work and split agents:

- **Sailors Media Tab** — Sailor profile “Media” tab: “Sailor X in the Media” section, public mentions cards, fetch/display/empty state. In scope: `sailingsa/frontend/index.html` (Media tab UI, `sailor-tab-panel-media`, `.sailor-public-mentions`, media cards), `sailingsa/frontend/public/sailor.html` (media section), `api.py` (e.g. `api_sailors_media` / sailors media endpoint), `sailor_public_mentions`, media scores, and jobs under `jobs/` that feed the Media tab. **Full list of code, READMEs, API, DB, env:** **`docs/SAILORS_MEDIA_TAB_AND_MEDIA_SCORES.md`**. When the user says “Sailors Media Tab”, limit changes to this scope only.

- **News Feed** — Landing-page "Latest News" section (Local / International), 16:9 thumb cards, fetch from `/api/news/latest`. In scope: `sailingsa/frontend/index.html` (`#landing-news-embed`, `#landing-news-list`, `.news-feed-*` CSS, `loadLandingNews()`), optional `sailingsa/news/index.html`, and in `api.py` only `GET /api/news/latest`, `POST /api/news/refresh`, and the news cache/pipeline. **Full scope:** **`docs/NEWS_FEED_AGENT.md`**. When the user says "News Feed", limit changes to this scope only.

## UI / design system — hard rules (do not break pages)

**`docs/UI_COMPONENTS_README.md`** — Hard rules for layout and components. **Store in Cursor memory for easy access.**

- **Never modify header or navigation layout.** Header links must stay white on dark background.
- **Always reuse existing components** (`.container`, `.card`, `.table`, `buildMasterPageLayout`). Do not invent new CSS frameworks; follow **`docs/design_system.md`** and `sailingsa/frontend/css/main.css`.
- **Modify only components or page sections, not global layout.** See `.cursorrules` and `.cursor/rules/design-system-and-components.mdc`.

## Logical areas in this repo (for scoping)

- **Frontend**: `sailingsa/frontend/` (e.g. `index.html`, assets, css)
- **Backend/API**: `api.py`, `sailingsa/backend/`
- **Data/scripts**: `data/`, and standalone `.py` scripts in project root
- **Config/deploy**: `deploy/`, `build/`, shell scripts

When asked to "fix the app" or "update the site", ask which area or file to focus on first.

## RESULTS_LINE cleanup (locked — RESULT_REGATTAS)

**`docs/RESULTS_LINE_CLEANUP_COMPLETE.md`** — Results-line / `result_status` work for regattas with rows in `public.results` only. **Do not** map `Unknown` or auto-fix unapproved values; remaining invalid rows are **intentional** until per-regatta review. Scripts: `list_distinct_result_statuses_results_only.py`, `apply_result_status_map.py`, `qa_results_line_metrics.py`. **Next (controlled):** HOST / `host_club_id` linking on the same results-only set.

## Results HTML "Results are" status line

**`docs/RESULTS_HTML_STATUS_LINE_RULE.md`** — For all results reports/sheets: the status line must be exactly **`Results are [Provisional|Final] as at DD Month YYYY at HH:MM`** (e.g. `Results are Provisional as at 15 February 2026 at 14:20`). Source: `regattas.result_status` and `regattas.as_at_time`. Use "as at" not "as of". No current date or event date placeholder. See also `docs/RESULTS_PASSING_WORKFLOW.md` and README "Results Data Pass".
