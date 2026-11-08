# Website development — standard operating procedure

**Applies automatically to every website, UI, performance, bugfix, and deployment task in this repository.** Read this with `AGENTS.md`, `docs/DEVELOPMENT_TOOL_ROUTER.md`, and `sailingsa/deploy/SSH_LIVE.md`. User does not need to ask for tools, SSH or tests separately.

## 0. Discover before deciding

- Check whether a matching page/component already works; inspect *live* and repository versions and their drift.
- Discover current GitHub, REA, browser, Cursor/Codex, MotionSites and Google Stitch integrations. A checked-in MCP endpoint is **configured**, not necessarily authenticated.
- **Never claim REA lacks SSH** merely because a named tool is not exposed. GoWifi REA's `capture_process_scenario` can run `/opt/rea/ops/bin/rea-admin <target> -- capabilities`; authenticated `sailingsa-publish` SSH has also been verified. Follow authorisation, backups, Gold lock and protected-service rules. Do not disclose keys.
- Do not install a second copy of an existing service or request credentials until the available connection was checked.

## 1. Choose the tools relevant to the specific change

| Work | Tools automatically considered |
| --- | --- |
| Visual concept / new marketing page | MotionSites skill/examples; MotionSites MCP if authenticated; Google Stitch if a real session is exposed; existing approved assets |
| SailingSA production component | Existing working sibling, actual CSS/design tokens, browser screenshot; MotionSites **only for suitable small patterns** (no cinematic app redesign) |
| Plan / code | GPT as architecture reviewer; REA to inspect code/data/live state; scoped Codex or Cursor changes; GitHub diff and review |
| Search / results / API | REA SSH + database/route evidence, existing schema and provenance; no mockup-derived schema |
| Tests and release | `node scripts/check_website_workflow.cjs`; targeted tests and browser viewport checks; CI, backup, staging/deploy, post-deploy smoke and rollback |

Do not fake unavailable tool outputs. If Stitch or MotionSites premium returns an authentication requirement, record that and continue with the verified existing skill and codebase, rather than blocking ordinary repairs.

## 2. Mandatory Plan → validate → surgical edit

1. **Scope:** name exactly which page, component and files can change. Preserve all other pixels and elements. For SailingSA header, gold header, regatta sheets, `api.py` and production data, apply the existing specific locks.
2. **Design:** for UI work, read the approved design system and a working sibling. Where visual research adds value, inspect 2–3 relevant MotionSites examples; ask Stitch for ideas only when it is connected. Design **390×844 portrait first**, then landscape, then desktop.
3. **Implement:** small, single-purpose change. Do not launch competing agents or invent CSS when an existing component can be reused. Verify code diff and dynamic records remain deduplicated.
4. **Visual QA:** actual mobile emulation (not only screenshot crop), text wrapping, controls, arrows, loading/error/empty states, click-through and overflow. Compare before/after screenshots. Test other pages sharing changed CSS.
5. **Performance:** for changed loading/search/links, measure with the browser; report real timings instead of asserting "instant". Respect pagination/filtered querying where established.
6. **CI:** run the repository contract check locally before proposing merge. GitHub Actions `website-quality.yml` runs the same repository checks on PR/push. Live-browser smoke is independently run on the explicit workflow's schedule/manual trigger and during releases (not a substitute for branch-specific preview testing).
7. **Deploy:** follow `sailingsa/deploy/SSH_LIVE.md`, REA controlled path, live diff + file-specific backup + protected-unit rules. A GitHub merge does not deploy code; a successful command does not prove visual acceptance. Verify live asset versions, HTTP status and actual interactions. Record rollback path.
8. **Report:** specify changes made, exact commit, tests actually run and their results, actual production status, and any **unverified** integration. No "sorted" without live evidence.

## Standing prohibitions

- No redesign or hero-sized type on existing app pages unless explicitly requested. Dense 14–16px body, tight card padding, slim inputs, lite tables, accessible tap targets.
- No editing the approved compact sailor header or unrelated CSS.
- No silently overwriting live `api.py` or syncing a stale cloned repository onto live.
- No more than two identical screenshot-fix attempts; diagnose at that point.
- No fake screenshots, no guessed links, and no user babysitting for an already-authorised workflow.
- Do not assume Mac, GoWifi server, GitHub Actions and ChatGPT share the same MCP sessions or credentials.

## CI boundaries

The repo-check script validates committed wiring and several explicit design/UX invariants. It is **not** proof that every visual detail is correct. Live browser smoke tests the deployed website and requires network/browser availability. Branch changes require a local/preview visual test, then verified production smoke after deployment.
