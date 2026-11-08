# SailingSA / Cursor-Websites

This is an existing production application. **Do not treat this repository as a blank website template.** Live files can be ahead of GitHub. Never replace them without comparing and backing up.

## Default website build workflow

Every website or UI task automatically follows **[Website Development SOP](docs/WEBSITE_DEVELOPMENT_SOP.md)**, **[Development Tool Router](docs/DEVELOPMENT_TOOL_ROUTER.md)** and [AGENTS.md](AGENTS.md). The user should not need to repeat that MotionSites, Google Stitch, REA SSH, GitHub, Codex/Cursor, browser screenshots and CI/CD are available for task-aware consideration.

- **Research and design:** approved working sibling/design tokens first; MotionSites free agent skill and 2–3 suitable design patterns; MotionSites premium MCP or Google Stitch only when actually connected. Do not place cinematic marketing styles into compact production UI.
- **Implementation:** plan → validate → surgical edit; respect locked components, keep database and API contract intact.
- **Verify:** portrait 390×844 first with real mobile emulation, then landscape/desktop, correct interactions, overflow, accessibility, performance. Run local checks and GitHub CI.
- **Deploy:** REA SSH-backed authorised path, live-vs-repo diff, backup, documented deployment, live verification, rollback. A merged commit is **not** live deployment.

## Commands

```bash
node scripts/check_website_workflow.cjs
node scripts/check_dockside_mobile.cjs https://sailingsa.co.za/
```

The first command checks committed tool wiring and selected UI invariants without network access. The second uses local Chromium/Chrome and real DevTools mobile emulation to test the **already deployed** page; it is not a PR preview. See [Website Development SOP](docs/WEBSITE_DEVELOPMENT_SOP.md) for full release gates.

GitHub Actions: `.github/workflows/website-quality.yml` runs the static contract on pull requests and pushes; the live Dockside smoke is scheduled and can be dispatched manually. Browser tests of changed branch UI still belong on a real preview/local build before release. No automatic deployment or unauthorised service restarts are performed by this workflow.

## Key references

- [Mobile-first design system](docs/design_system.md)
- [Portable Google Stitch design context](DESIGN.md)
- [Live SSH/deployment documentation](sailingsa/deploy/SSH_LIVE.md)
- [MotionSites agent skill](.agents/skills/motionsites-web-builder/SKILL.md)
- [MotionSites Cursor rule](.cursor/rules/motionsites.mdc)
- [REA access guide](docs/REA_CHATGPT_ACCESS.md)

### Integration truthfulness

MotionSites MCP is registered in `.cursor/mcp.json`, but an unauthenticated probe returned HTTP 401 on 8 November 2026. Google Stitch official CLI MCP is now registered in the same Cursor config, pinned to `@google/stitch@0.12.1` (Node >=20). Its CLI was tested on the GoWifi REA host on 8 November 2026: `stitch status --json` returned `authenticated: false`, with no `STITCH_API_KEY` present there. Cursor/Mac and ChatGPT runtimes are separate and require their own checked authentication. Do not report Google design generation as working before a real authorized session. Do not report either premium integration as working without an actual authenticated runtime call. Keep credentials out of commits.
