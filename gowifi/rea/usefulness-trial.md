# REA usefulness trials (copies only, not live)

Two targets, same isolation: user `rea`, trees under `/opt/rea/work/…` only. Production was not written.

**Recommendation (recorded):** Retain REA 6.4.0 on the GoWifi box. Use it **selectively for reverse engineering** (minified/asar/native copies). Do **not** turn it on for routine SailingSA development — Cursor’s normal reads are faster and cheaper there.

## Setup this Cloud Agent could complete

| Check | Result |
| --- | --- |
| REA CLI | **6.4.0** |
| Isolated Node | **v24.21.0** under `/opt/rea` |
| `rea mcp doctor` (on box, as `rea`) | **healthy** — 170/170 tools, initialize OK |
| `recover-javascript-sources` | **unavailable** — needs a separate Wakaru ^1.13 Linux x64 binary (`REA_WAKARU_COMMAND`). Official REA install does not ship it. Not installed (would be extra software on the box). |
| Production after both trials | nginx, Mail-in-a-Box, MariaDB, GoWifi + Aerialnet APIs still **active**; no REA listener |
| Cursor Desktop `rea-gowifi` MCP | **Still not registered from this session.** This agent is a Linux VM. Kevin’s Mac Mini worker (`43e56b9a-b958-55dd-a151-df216da22615`, idle, approved, Darwin) is connected, but `Task` with `workerId` still executes on this VM (`uname` Linux / `hostname` cursor). Desktop registration requires running [register-rea-gowifi-on-mac.sh](register-rea-gowifi-on-mac.sh) **on the Mini**. |

---

## Trial 1 — owned, commented SailingSA JS

Question:

> How does this frontend rewrite `/api` calls to live production in local/dev mode, and how do GET vs mutating requests differ?

**Target:** repo copy of `sailingsa/frontend/js` → `/opt/rea/work/sailingsa-frontend-js`.

### REA

- Command: `/opt/rea/bin/rea analyze-javascript-application /opt/rea/work/sailingsa-frontend-js --json`
- Wall time: **48 seconds**
- Evidence: ~4.2 MB JSON, 6 JS files parsed, 99 714 AST nodes, 25 findings, 2 566 semantic nodes, **842 unknowns**, coverage **partial/truncated**
- Named the right helpers: `sailingDevModeActive`, `sailingDevIsPrivateLanHostname`, `sailingDevResolveLiveOrigin`, `sailingDevLiveSessionToken`, `sailingDevInstallFetchInterceptor`, `sailingDevMockSuperAdminSession`, `apiRequest`, `checkSession`
- Found literal `sailingsa.co.za`
- `fetch` request nodes had **`endpoint: null`**
- Electron-oriented summary was all zeros (expected; this is browser JS)
- Dropped full semantic graphs for `breaking-news-card.js`, `lipton-dev-playback.js`, `tracking-dev2-playback.js` (result-budget)

REA did **not** emit a readable GET-vs-mutate rewrite explanation.

### Cursor-normal (same files)

From `api.js` comments and the interceptor (minutes of targeted reads, no 4 MB dump):

1. Dev mode is on for `SAILINGSA_ENV=DEV`, loopback, private LAN / `*.local`, or `sessionStorage sailingsa_blank69_local_live_api=1`. Off if `SAILINGSA_LIVE_DEV_OFF`.
2. Live origin is `window.SAILINGSA_LIVE_ORIGIN` or `https://sailingsa.co.za`.
3. `sailingDevInstallFetchInterceptor` wraps `window.fetch` once.
4. **GET/HEAD** same-origin `/api/*` → rewritten to that live origin.
5. **POST/PUT/PATCH/DELETE** same-origin `/api/*` → mock/blocked unless `sailingsa_live_session_token` (live `?session=`) or `SAILINGSA_DEV_PASS_MUTATING_TO_LOCAL_API` (local api.py).
6. Production host never matches these helpers.

### Time / credits (trial 1)

| | REA CLI | Cursor-normal |
| --- | --- | --- |
| Time to a usable answer | 48s + parse 4.2 MB + still need source | Targeted reads of `api.js` |
| Cursor credits | 0 for the CLI itself; huge if the Evidence is pasted into chat | Reads only the relevant functions |
| What it added | Inventory of names + a `sailingsa.co.za` literal | The actual control flow |

**Verdict:** REA did **not** save time or credits on owned, commented JS.

---

## Trial 2 — genuinely minified third-party application

Question:

> How does this viewer open a PDF, create the worker, and render page 1? Identify entry points, worker script URL / `GlobalWorkerOptions`, `getDocument`, and the page-render path despite minification.

**Target:** Apache-2.0 `pdfjs-dist-viewer-min@3.11.174` (Mozilla PDF.js generic viewer, `gulp minified`) copied to `/opt/rea/work/pdfjs-viewer-min`. No source maps (those would cheat). Not live, not `/home/user-data`.

| File | Bytes | Lines | Longest line | Minified? |
| --- | ---: | ---: | ---: | --- |
| `web/pdf.viewer.js` | 564 364 | 43 | 319 188 | Yes (webpack UMD) |
| `build/minified/build/pdf.js` | 319 998 | 22 | 319 188 | Yes |
| `build/minified/build/pdf.worker.js` | 1 087 210 | 22 | 1 086 384 | Yes |
| `web/viewer.html` | 28 538 | 485 | — | HTML shell (`<script src="pdf.viewer.js">`) |

### REA

- Command: `/opt/rea/bin/rea analyze-javascript-application /opt/rea/work/pdfjs-viewer-min --max-heap-mb 768 --analysis-timeout-ms 180000 --format json`
- Evidence id: `ev_82775035d867a4f9d213bca8de20d01e768ff0557dd88776652ca3a60894015b`
- Wall time: **116 seconds**
- Evidence: **50.5 MB** JSON (~12.6 million tokens if ingested at ~4 bytes/token)
- Stats: 5 files inventoried, 3 JS parsed, **580 970** AST nodes, **611** findings, 375 application-graph nodes, 623 edges, **20 002** semantic nodes, **35 777** unknowns
- Application-graph kinds: 328 `endpoint`, 33 `javascript-module`, 3 `javascript-asset`, **2 `worker`**, 2 `storage`
- Coverage: **partial**; semantic graph **truncated**. `pdf.js` semantic graph exceeded the parent result budget. `pdf.worker.js` **exhausted the analyzer heap**.
- Electron summary all zeros (expected; browser viewer)
- Named inventory included `getViewerConfiguration`, `webViewerLoad`, `setDocument`, `PDFDocumentProxy`, `forceRendering`, `renderPage`, `PDFPrintService`, `getPagesOverview`
- Evidence JSON contains the strings `getDocument`, `GlobalWorkerOptions`, `workerSrc`, `PDFViewerApplication`, `pdf.worker`
- Did **not** emit a readable open → worker → `getDocument` → `load` → render narrative. An agent still has to walk a 50 MB graph (or re-read the minified source).
- `recover-javascript-sources` on `pdf.viewer.js` failed in **4 seconds** with `capability_unavailable` / Wakaru not installed.

Box load went 0.20 → ~0.79 during the run. nginx, MariaDB, Mail-in-a-Box, GoWifi and Aerialnet units stayed **active**. No REA listen port.

### Cursor-normal (same minified files)

Regex + snippet reads of the webpack UMD, **0.07 seconds**, 912 KB scanned, no 50 MB dump. Public export names survived minification, so the control flow is recoverable without REA:

1. `viewer.html` loads only `pdf.viewer.js`.
2. `PDFViewerApplication.run(config)` → `initialize` → `parseQueryString(location.search).get("file")` or `AppOptions.defaultUrl` = `compressed.tracemonkey-pldi-09.pdf`.
3. `PDFViewerApplication.open({url|data})` copies `AppOptions` `OptionKind.WORKER` onto `GlobalWorkerOptions`, then `getDocument(options)`.
4. Default `workerSrc` is `../build/pdf.worker.js` (`OptionKind.WORKER`). `PDFWorker.workerSrc` reads `GlobalWorkerOptions.workerSrc` or `./pdf.worker.js` fallback.
5. `getDocument` builds a `PDFDocumentLoadingTask`, constructs `PDFWorker` / `WorkerTransport` unless a worker was passed in, and requires `.url`, `.data`, or `.range`.
6. `open` assigns `this.pdfLoadingTask`, wires `onPassword` / `onProgress`, then `o.promise.then(doc => this.load(doc))`.
7. Render path is the usual viewer classes still named in the bundle: `PDFViewer` / `PDFPageView` / `PDFRenderingQueue` / `forceRendering` / `renderPage`.

That is the behaviour the question asked for.

### Time / credits (trial 2)

| | REA CLI | Cursor-normal |
| --- | --- | --- |
| Time to a usable answer | 116s + parse 50.5 MB + still need source for the load path | **0.07s** of targeted regex on named webpack exports |
| Cursor credits (CLI) | **0** — ran on the box, not through Cursor | **0** — local reads on a copy |
| Cursor credits if the artifact is fed into chat | ~**12.6M tokens** for the Evidence (will blow context; even a 1% slice is ~126k tokens) | ~**500 tokens** of useful snippets, or ~228k if you dumped all 912 KB of JS |
| What it added | Inventory: 2 worker nodes, named viewer helpers, 328 endpoints | The actual open / worker / `getDocument` / `load` / render path |

**Verdict:** Even on a **genuinely minified third-party webpack application**, REA did **not** save time or Cursor credits. Webpack left the public API names intact; Cursor-normal recovered the full load path from those names. REA’s dump was **~25× the source tree** (50.5 MB vs 2.0 MB) and still omitted the narrative. Source recovery (the feature that would matter most here) is **off** until Wakaru is installed under `/opt/rea` only.

---

## Combined recommendation

| Use | Do |
| --- | --- |
| Routine SailingSA / hub / Event URL work | Cursor-normal. Do not add `rea-gowifi` to the daily Desktop MCP set for this. |
| Reverse engineering a copy we do not have sources for (fully mangled JS, Electron `asar`, .NET, later native) | Isolated box REA, after copying into `/opt/rea/work/…`. Optional later: Wakaru (JS recover) or Ghidra (native), still under `/opt/rea` only. |
| Live production trees | Never. Stay off `/home/user-data`, `/root/gowifi-upp`, Aerialnet, nginx, MariaDB. |

Retain the isolated GoWifi install. Use it selectively.

## Mac Desktop (do this on the Mini)

```bash
bash gowifi/rea/register-rea-gowifi-on-mac.sh
```

That creates `~/.ssh/rea_gowifi` if needed, **merges** `rea-gowifi` into `~/.cursor/mcp.json` (backup `mcp.json.rea-gowifi.bak`), and checks `rea --version` == 6.4.0. If SSH is denied, append the printed public key with `gowifi/rea/add-cursor-pubkey.sh` on the box. Fully quit Cursor afterward. Do not run `npx rea-agents setup`.
