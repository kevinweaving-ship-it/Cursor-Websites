# Agent / task-splitting guide

This project uses **split tasks** to avoid agent resource limits and crashes.

## SSH / deploy / live — MUST use readme

**The user only vibe-codes. The agent’s job is server SSH.** Do the live apply yourself. Do **not** skip SSH, do **not** leave “run this on This Mac”, do **not** wait to be told “you have full SSH”. If sailingsa.co.za must change, SSH per **`sailingsa/deploy/SSH_LIVE.md`** in the same turn.

**`sailingsa/deploy/SSH_LIVE.md`** is the primary source for deploy, fix, sync, and SSH. Use it for any live-server work. **Never** say "SSH is blocked", "can't SSH", or "run from your machine" — when asked to deploy or fix live, give the exact commands from the readme (deploy code, sync 385, etc.) **and run them**.

**Production:** All fixes (sailor URLs, regatta links, 385 data, no broken URLs, new Event URLs) must be deployed to **live** via the SSH readme — deploy code (push-to-cloud-expect.exp) and sync 385 (sync-385-local-to-live.sh). Local-only changes do not affect https://sailingsa.co.za.

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

- **New Event URL** — Preload / match / Event URL + same-club cards. **Must read `docs/CLUB_EVENT_LIVE_CARDS.md` first.** User vibe-codes; **agent SSHs live** (not repo-only, not “run this on Mac”). Landing hero is `/` `landing-event-card`; search is `/api/regattas/with-counts`. **Do not** edit `blank69.html` or `js/breaking-news-card.js`. Media empty on the new slug (no Midmar leftovers). No Venue line unless host and venue are different clubs.

- **HMYC Dart 18 Nationals 2026 (LOCKED)** — `/regatta/2026-09-24-hmyc-dart-18-nationals`. **Do not change this page again** unless the user writes exactly **`override lock`**. All public + admin rules: **`docs/HMYC_DART_18_NATIONALS_2026_PAGE_LOCKED.md`**. Public never edits scores and never sees empty entry races; Age is code `Y`; Super Admin closed R is green fill + click toggle; only Super Admin + HMYC club admin (`admin_club_id=98`).

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
