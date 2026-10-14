# REA usefulness trial (copied JS, not live)

Question asked of both REA and normal Cursor analysis:

> How does this frontend rewrite `/api` calls to live production in local/dev mode, and how do GET vs mutating requests differ?

**Target:** repo copy of `sailingsa/frontend/js` → `/opt/rea/work/sailingsa-frontend-js` on the GoWifi box (user `rea` only). Not `/home/user-data`, not live dash.

## Setup that this Cloud Agent could complete

| Check | Result |
| --- | --- |
| REA CLI | **6.4.0** |
| `rea mcp doctor` (on box, as `rea`) | **healthy** — 170/170 tools, initialize OK |
| Production | nginx, Mail-in-a-Box, MariaDB, GoWifi + Aerialnet APIs still **active**; no REA listener |
| Cursor Desktop `rea-gowifi` MCP | **Not registered from this session** — this agent runs on a Linux VM. Kevin’s Mac Mini worker is connected (`Kevin - Mac Mini`) but Task cannot be placed on My Machines from a Cloud Agent. Use `gowifi/rea/register-rea-gowifi-on-mac.sh` on the Mac (merge-only, no local REA install). |

## REA run

- Command: `/opt/rea/bin/rea analyze-javascript-application /opt/rea/work/sailingsa-frontend-js --json`
- Wall time: **48 seconds**
- Evidence: ~4.2 MB JSON, 6 JS files parsed, 99 714 AST nodes, 25 findings, 2 566 semantic nodes, **842 unknowns**, coverage **partial/truncated**
- Named the right helpers: `sailingDevModeActive`, `sailingDevIsPrivateLanHostname`, `sailingDevResolveLiveOrigin`, `sailingDevLiveSessionToken`, `sailingDevInstallFetchInterceptor`, `sailingDevMockSuperAdminSession`, `apiRequest`, `checkSession`
- Found literal `sailingsa.co.za`
- `fetch` request nodes had **`endpoint: null`**
- Electron-oriented summary was all zeros (expected; this is browser JS)
- Dropped full semantic graphs for `breaking-news-card.js`, `lipton-dev-playback.js`, `tracking-dev2-playback.js` (result-budget)

REA did **not** emit a readable GET-vs-mutate rewrite explanation. An agent still has to interpret the graph (or re-read source).

## Normal Cursor analysis (same files)

From `api.js` comments and the interceptor (minutes of targeted reads, no 4 MB dump):

1. Dev mode is on for `SAILINGSA_ENV=DEV`, loopback, private LAN / `*.local`, or `sessionStorage sailingsa_blank69_local_live_api=1`. Off if `SAILINGSA_LIVE_DEV_OFF`.
2. Live origin is `window.SAILINGSA_LIVE_ORIGIN` or `https://sailingsa.co.za`.
3. `sailingDevInstallFetchInterceptor` wraps `window.fetch` once.
4. **GET/HEAD** same-origin `/api/*` → rewritten to that live origin.
5. **POST/PUT/PATCH/DELETE** same-origin `/api/*` → mock/blocked unless `sailingsa_live_session_token` (live `?session=`) or `SAILINGSA_DEV_PASS_MUTATING_TO_LOCAL_API` (local api.py).
6. Production host never matches these helpers.

That is the behaviour that matters for shipping hub/dev vs live.

## Time / credits

| | REA CLI | Cursor normal |
| --- | --- | --- |
| Time to a usable answer | 48s + parsing 4.2 MB + still need source for the rewrite rules | A few targeted reads of `api.js` |
| Credits | Extra model tokens if you feed the Evidence into chat; graph is larger than the source | Reads only the relevant functions |
| What it added | Inventory of function names and a `sailingsa.co.za` literal | The actual control flow |

**Verdict for this owned, commented JS:** REA did **not** save time or credits. Cursor’s normal analysis answered the question more completely and cheaper.

REA is more likely to pay off on **minified/bundled** JS, Electron `asar`, or binaries (needs Ghidra/Hopper — not on the box). Keep the isolated box install; do not make it the daily Cursor MCP until a minified/native target shows a win.

## Mac Desktop (do this on the Mini)

```bash
bash gowifi/rea/register-rea-gowifi-on-mac.sh
```

That creates `~/.ssh/rea_gowifi` if needed, **merges** `rea-gowifi` into `~/.cursor/mcp.json` (backup `mcp.json.rea-gowifi.bak`), and checks `rea --version` == 6.4.0. If SSH is denied, append the printed public key with `gowifi/rea/add-cursor-pubkey.sh` on the box. Fully quit Cursor afterward. Do not run `npx rea-agents setup`.
