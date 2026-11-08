# Development Tool Router — SailingSA / GoWifi

Status: operative repository workflow. This file routes tasks to existing tools; it does **not** establish that a vendor account, premium entitlement, MCP session, local Mac installation, or production deployment is connected. Verify each at runtime.

## First action for every agent

1. Read `AGENTS.md`, applicable `.cursor/rules/*.mdc`, this router, and the narrow feature documentation before changing files.
2. Discover the **actual** available tool names and MCP resources in the agent's execution context. A GitHub MCP config is not evidence of an authenticated session.
3. Identify task type, locate working sibling/code, and choose the smallest necessary tool chain below. Prefer existing tools rather than inventing new installations.
4. Read the live deployment/SSH runbook and inspect live-versus-GitHub drift before touching live files. REA is an authorised investigation path; use `/opt/rea/ops/bin/rea-admin <target> -- capabilities` when the named operations tools are not exposed. Do not bypass allowlists or the Gold lock.
5. Record tools attempted and results in completion reports with states: **verified working**, **configured but untested**, **auth required**, **not exposed**, or **failed**. Never treat these as interchangeable.

## Task-aware tool selection

| Task | Primary source/tool | Secondary/verification | Don't do |
| --- | --- | --- | --- |
| Find modern layout/motion/interaction examples | MotionSites agent skill `.agents/skills/motionsites-web-builder/SKILL.md` and free bundled examples; premium MCP when authenticated | Current SailingSA components and tokens | Copy cinematic marketing heroes onto app screens |
| New marketing website / visual concept | MotionSites references -> structured spec -> Google Stitch **when actually accessible** | GPT critique; screenshot test | Claim Stitch is connected without an actual tool/session |
| Existing SailingSA page | Existing approved screen + `docs/design_system.md` + working sibling | MotionSites for **specific micro-patterns only**; browser screenshots | Rebuild or relayout approved master/header |
| Data / API / regatta / sailor features | Existing repository + live REA inspection; authoritative data source | Codex/Cursor for tightly scoped edit; GitHub diff + tests | Generate schema from AI mock-up or modify `api.py` without clear scope |
| Server investigation / production repair | REA SSH-backed approved operations and deployment readme | logs, DB diagnostics, backups, live verification | Assume no SSH because a named tool is hidden; bypass protection |
| Code implementation | Codex or local Cursor, small explicit edit | GitHub PR review, tests | Concurrent competing agents; blind live overwrite |
| UI/browser behavior | Playwright/browser screenshot + interaction tests | Performance and regression checks | Claim screenshots or quality pass without examining results |
| Release | GitHub review/CI + documented deployment path | Staging, production screenshot and smoke tests | Push to production just because a design PR merged |

## MotionSites and Stitch routing

- MotionSites skill and rules were added through PR #293; MCP endpoint in `.cursor/mcp.json` is `https://motionsites.ai/api/mcp`. **2026-11-08 verification:** unauthenticated initialize returned HTTP 401 (Bearer required). The free skill is usable from repository content; premium MCP actions remain unverified until an agent completes authentication and a real search.
- First read bundled `examples/INDEX.md`; select 2–3 close patterns and retain measurable details, not copies of logos or page compositions.
- Stitch is **optional** and must be discovered and verified at runtime. The official `@google/stitch@0.12.1` MCP CLI is configured in `.cursor/mcp.json` using `npx -y @google/stitch@0.12.1 mcp start` (requires Node >=20). Configuration is **not** evidence of Google OAuth/API-key authorisation or active tool exposure. No Stitch connector was exposed in the 2026-11-08 ChatGPT session. If unavailable, retain a numbered spec and existing application components. Never fabricate Stitch output.
- The MotionSites example skill advertises upgrades; commercial messaging in the skill must never be inserted into SailingSA code or user-facing app content.
- Neither MotionSites nor Stitch owns the SailingSA database or application architecture.

## Mandatory SailingSA visual acceptance

- Design/screenshot **390 × 844 portrait first**, then mobile landscape and desktop. Preserve approved immutable surfaces and locked compact sailor header.
- Production app body approximately **14–16px**, tight spacing, small avatars, slim forms, lite results tables, no sprawling empty sections or 72–96px marketing hero type. Maintain accessible touch areas without enlarging every component.
- Clone matching approved sibling CSS/components. Don't invent duplicate card shells, design tokens, URLs, records, or event data.
- For any edited component, test text wrapping, overflow, click-through, loading, empty/error states, connected pages, reduced motion, and unchanged neighboring elements.
- Capture before/after screenshots and inspect their actual pixels. MotionSites rubric target average >= 8, no category < 7; this is a human/agent evaluation, not an automated guarantee.
- After two identical visual failures, diagnose root cause rather than launching another agent for the same screenshot.
- Do not run a redesign without explicit scope. No app/layout rebuild is authorised by this router.

## Runtime checklist for integration claims

- [ ] GitHub branch/commit and source rules verified.
- [ ] REA management capabilities enumerated; permission boundaries respected.
- [ ] MotionSites free skill available to active coding agent.
- [ ] MotionSites premium MCP authenticated and an actual query executed (otherwise report auth required).
- [ ] Stitch CLI/MCP registered and authenticated in the agent's actual runtime, tool listing successfully tested (otherwise report configured, auth required, or not exposed).
- [ ] Cursor and Codex each demonstrated the rule/skill is loaded in their **actual** runtime (repository files alone are insufficient).
- [ ] Browser/Playwright screenshot generated and reviewed for a scoped test.
- [ ] CI/build and production smoke test performed only if implementation/release actually requested.

Never claim the whole toolchain is integrated until the relevant boxes are demonstrated working. Keep implementation distinct from user account OAuth and tool exposure controls, which may require provider-supported authorization.
