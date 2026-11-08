# Agent / task-splitting guide

This project uses **split tasks** to avoid agent resource limits and crashes.

**Mandatory website workflow:** Before every website/UI/design/performance/CI/CD task read and execute `docs/WEBSITE_DEVELOPMENT_SOP.md`, together with `docs/DEVELOPMENT_TOOL_ROUTER.md`. This applies automatically: choose available MotionSites examples, Google Stitch when connected, real existing design tokens, REA SSH investigation, branch tests, true mobile screenshots, CI and post-deploy verification according to task scope. Do not require the user to repeat the tool list. Never call a configured but unauthenticated MCP integration functional. GitHub merging does not constitute deployment.

**Mandatory capability routing:** Read `docs/DEVELOPMENT_TOOL_ROUTER.md` before any website, agent-tool, MCP, UI, implementation, or deployment task. It is the integration status ledger and maps MotionSites, Stitch (only if connected), REA, GitHub, Codex, Cursor, and screenshot verification to their appropriate scope. Explicitly verify tool exposure and authentication; a checked-in MCP config does not prove a working session. Existing locks, deployment permissions, and page immutability always take precedence.

## REA access on GoWifi and SailingSA

Use REA for authorized server work on both boxes. The SSH-backed operations path has
been verified. Prefer the named `ops_*` tools when visible in ChatGPT Work. If they
are absent, use REA's `capture_process_scenario` with
`/opt/rea/ops/bin/rea-admin <target> -- capabilities`, then use the documented
management verbs or the installed `/opt/rea/ops/bin/ops-mcp` over MCP stdio.
See `docs/REA_CHATGPT_ACCESS.md` and `gowifi/rea/ops/CATALOG.md`.

A missing ChatGPT tool or failed direct SSH from the workspace does not establish
that REA lacks access. Try the verified REA path first. Report a blocker only with
the exact operation, target, and observed error after checking the available routes.
Keep server-side allowlists, the Gold deployment lock, and protected units in force.
Use scoped backups, staging, and live verification for production changes.

Do **not** use Box MCP or ask the user to connect Box. “Boxes” means the SSH
servers (GoWifi, SailingSA, and the rest). Use REA / SSH from the live readme.

## MotionSites (agent-side website research)

The user vibes. MotionSites is a tool for the **agent**, not a settings chore
for the human. Do not ask them to open Cursor Settings, Connect MCP, or paste
prompts. When building or visually improving a website, landing page, or hero,
read **`.agents/skills/motionsites-web-builder/SKILL.md`** and follow it
(examples, media shelf, numbered spec, screenshot-and-fix).

On SailingSA production pages, stay inside the existing design system and
locked header unless they explicitly want a cinematic rebuild. Use MotionSites
for polish, motion, and new marketing pages — not to replace live layout.

### How every page gets built (consistency)

Average AI pages fail for three reasons: a vague plan, fake media, and nobody
looking. Every visual change follows the same loop:

1. **Brief in one breath:** what/who, three-word mood, one signature, stack
   (existing SailingSA components vs new marketing page), hero vs full page.
2. **Study 2–3 closest MotionSites examples** for precision (px, clamp, hex,
   durations) — never copy their brands or layouts.
3. **Real media only:** user’s assets, then the skill media shelf, never
   invented URLs or logos rebuilt from description.
4. **Numbered spec first** (`.agents/skills/motionsites-web-builder/references/spec-template.md`).
   No adjective without a value. SailingSA tokens come from
   `docs/design_system.md` and `sailingsa/frontend/css/main.css` — reuse
   `.container`, `.card`, `.table`. New sites may pick a palette.
5. **Build exactly the spec.** One idea on the first screen. One material.
   `prefers-reduced-motion`. **SailingSA app chrome is compact** (body
   ~14–16px, tight padding, small avatars, slim inputs). MotionSites mega
   type (72–96px / 5–6× body) is only for a **new marketing hero the user
   asked for**. Never blow up cards, tables, chat, login, results, or copy
   overlays that hide the photo on MP/ML.
6. **Look and fix:** screenshot desktop + mobile, score the rubric, fix the
   three weakest scores with numbers, shoot again. Bar is average 8, nothing
   under 7. Two identical failures then diagnose — do not loop.
7. **Verify the other surfaces** that share the state (cards, logos, login).
   Same logo path, same card shell, same empty login fields.

## Never again (from past chats)

These already happened. Do not repeat them.

1. **Cloud over Mac for SailingSA.** Live SSH keys and logos live on Kevin’s Mac Mini. Cloud Linux has no `sailingsa_live_key`. Do not deploy SailingSA/GoWifi from Cloud. Do not “rebuild from description”. Exception: the user types Cloud in the same message.
2. **Do not touch headers.** Master / event / fleet / gold-header / `enforceHeader` / header MutationObservers are locked. “Fix results” is not a license to copy `api.py` or header JS.
3. **Do not thin-rewrite `/dev1/`.** Live fat `index.html` (~320KB) and `landing-roundup-cards.js` / `dockside-chat.js` are canonical. Delete demo HTML; do not replace the page. `/dev1/` ≠ `/dev-1` sailor embed.
4. **Do not clobber live with git.** Live `api.py` / homepage / logo generators can be ahead of the repo. Snapshot live first. Diff before copy. After an angry stop, freeze live.
5. **One logo path.** Parent Event Logo / `_CLUB_EVENT_LOGO_RULES` for every surface. Whole-name match, not substrings (“uct” in “instructor”). Unlock empty logo slots.
6. **Homepage must not fetch the archive.** Current `feed.json` item + one hero only. Reserve 16:9 before paint. Next **4** upcoming events always. Roundup title lists every event that week.
7. **Login fields load empty.** No prefilling WhatsApp/email. No user/session/`PUB_` until OAuth or Confirm click. `/sailor/general-public` must 404.
8. **Diagnose the layer.** Live works / local fails → API/DB/env, not a frontend workaround. Don’t Lighthouse a 502. Don’t invent results-table CSS.
9. **Cheap models, no loops.** Two identical failures then diagnose. No Max Mode, no extra Cloud agents, no Box MCP.
10. **MotionSites does not override the design system** on SailingSA production. Cinematic rebuilds only when the user asks. New marketing pages (Aerialnet, etc.) may use the full skill.
11. **Compact, modern, functional, mobile-portrait-first.** Kevin’s standing design complaint: agents make things **large**. Do not. Match an existing working card. Screenshot **390×844 first**. No large blank areas, no full-width giant buttons, no stretched graphs, no overflow tables, no overlay copy that blocks the photo on MP or ML. Copy existing CSS — do not invent a new look. Redo loops (Dockside, weather cams, landing type, Aerialnet overlay, print fonts, sailor-card width, WC Event URL / MP sticky ×3, Hub/sailor search ×3) happened because the first shot ignored MP density.

## Compact / mobile-first (do not make things large)

He has asked to redo the same visual jobs because agents ship **large,
loose, invented CSS** instead of **compact, modern, functional, MP-first**.

Every visual change:

- Design at **390×844** (phone portrait / MP) first, then ML, then desktop.
- Clone the working sibling (ZVYC weather, Ullman sponsor, roundup issue
  CSS, Facebook-style Dockside, results lite table). Same padding, type,
  height, border, width.
- Tight padding, small type, slim rows. App pages are not cinematic heroes.
- Full card width on MP and ML — not a partial-width island.
- Tables: compact lite view; fit portrait or switch the print/PDF to
  landscape; every rank line must stay readable.
- Overlay copy must not cover the photo on MP or ML.
- Keep 44×44 tap targets **without** inflating the whole card.
- Two identical visual failures then diagnose — do not spawn another agent
  for the same screenshot job.

See `docs/DESIGN_MOBILE_MASTER_VS_CLASS.md` (mobile-portrait locked
baseline) and `docs/RESULTS_TABLE_RENDER_RULES.md` (lite/compact tables).

## Dynamic weekly roundups

All weekly roundup editions, including archived and previously skipped weeks, must
reflect verified changes to the results or event data they cover. After a result is
published, corrected, moved to a different reporting week, or withdrawn, rebuild
each affected edition using the event's reporting week in Africa/Johannesburg.
Late imports belong in the original reporting week. Update the existing issue URL
and regenerate the HTML, PDF, issue JSON and dependent cards or indexes together.
Validate before publishing and retain the last good edition on failure. Retries
must be safe and must not create duplicate editions. A skipped week becomes
publishable once it has qualifying verified results.

## SSH / deploy / live — MUST use readme

**`sailingsa/deploy/SSH_LIVE.md`** is the primary source for deploy, fix, sync, and SSH. Use it for any live-server work. **Never** say "SSH is blocked", "can't SSH", or "run from your machine" — when asked to deploy or fix live, give the exact commands from the readme (deploy code, sync 385, etc.).

**Production:** All fixes (sailor URLs, regatta links, 385 data, no broken URLs) must be deployed to **live** via the SSH readme — deploy code (push-to-cloud-expect.exp) and sync 385 (sync-385-local-to-live.sh). Local-only changes do not affect https://sailingsa.co.za.

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
- **Compact, modern, functional, mobile-portrait-first.** Do not make things large. Screenshot 390×844 before desktop. Clone the working card; do not invent type scale or padding.

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
