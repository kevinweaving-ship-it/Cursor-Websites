# Diagnosis: Sailor profile → Click regatta → Modal (LIVE vs LOCAL)

**No code changes. Diagnosis only.**

---

## 1. Network flow (same on LIVE and LOCAL)

| Step | What happens |
|------|----------------|
| **Click** | Table row onclick calls `showRegattaResultChoice(regattaId, className, regattaName)` |
| **Handler** | `showRegattaResultChoice` (index.html) → `navigateToClassResults(regattaId, className, regattaName)` |
| **URL built** | `navigateToClassResults` builds: `/regatta/class/class-results.html?regatta_id={id}&class={class}&regatta_slug={slug}&class_slug={slug}` |
| **Modal** | `openResultPageInModal(url)` sets `iframe.src = window.location.origin + path` (absolute URL) |
| **Iframe load** | Browser loads that URL (same origin). Document: `regatta/class/class-results.html` |
| **API call** | Inside iframe, `loadClassResults()` runs `fetch(API + '/api/regatta/' + regattaId + '?t=' + Date.now())` |
| **Backend** | `GET /api/regatta/{regatta_id}` → `api.py` `api_regatta(regatta_id)` |

---

## 2. Exact endpoints and URLs

| | LIVE | LOCAL |
|--|------|--------|
| **Iframe document URL** | `https://sailingsa.co.za/regatta/class/class-results.html?regatta_id=385&class=420&regatta_slug=...&class_slug=...` | `http://192.168.0.130:8081/regatta/class/class-results.html?regatta_id=385&class=420&regatta_slug=...&class_slug=...` |
| **Query params** | `regatta_id`, `class`, `regatta_slug`, `class_slug` (same both) | Same. **Not** `slug=` in path. **Not** `/regatta?slug=` |
| **API endpoint** | `GET /api/regatta/{regatta_id}` (numeric id) | Same |
| **Full API URL** | `https://sailingsa.co.za/api/regatta/385?t=...` | `http://192.168.0.130:8081/api/regatta/385?t=...` |
| **Slug vs regatta_id** | API is called with **regatta_id** (e.g. 385). Slug only in query for display/links. | Same |
| **Response (when working)** | 200 + JSON array of regatta rows | 200 + same shape (when API runs) |
| **Response (when broken on local)** | N/A | 404 or 500 from whatever is serving 8081 (often static server → 404) |

---

## 3. JS function and fetch

| | LIVE | LOCAL |
|--|------|--------|
| **Modal trigger** | `showRegattaResultChoice` → `navigateToClassResults` → `openResultPageInModal(url)` |
| **File** | `sailingsa/frontend/index.html` | Same |
| **fetch()** | In `class-results.html`: `fetch(\`${API}/api/regatta/${encodeURIComponent(regattaId)}?t=${Date.now()}\`)` | Same endpoint; LOCAL has extra variable `apiUrl` and longer error message |
| **Backend route** | `api.py` → `@app.get("/api/regatta/{regatta_id}")` → `def api_regatta(regatta_id: str)` | Same (no `/results/` endpoint used here) |

---

## 4. Diff: LIVE frontend bundle vs LOCAL frontend bundle

### 4.1 index.html

| Area | LIVE | LOCAL | File + line (LOCAL) |
|------|------|--------|----------------------|
| **API_BASE** | `window.API_BASE = window.location.origin;` | `window.API_BASE = (window.location.origin \|\| '').replace(/\/$/, '');` | **index.html** ~1693–1694 |
| **Comment** | `// README: API and frontend on same host:port (8081). Use origin.` | `// Same origin for local (e.g. http://192.168.0.130:8081) and live...` | **index.html** ~1693 |
| **Regatta click handler** | Same: `showRegattaResultChoice(regattaId, className, regattaName)` | Same | — |
| **Modal loader** | Same: `openResultPageInModal(url)`, `absoluteUrl = window.location.origin + path` | Same | — |
| **Slug routing** | Uses `regatta_id` in URL and API; slug only in query params | Same | — |

### 4.2 regatta/class/class-results.html

| Area | LIVE | LOCAL | File + line (LOCAL) |
|------|------|--------|----------------------|
| **Base tag** | None | `<base href="/" id="regatta-base">` + script that sets `base.href = window.location.origin + '/'` | **class-results.html** head ~line 8; script ~114 |
| **API variable** | `const API = window.API_BASE \|\| (window.location.origin \|\| '');` | `const API = (window.parent && window.parent.API_BASE ? window.parent.API_BASE : (window.API_BASE \|\| window.location.origin \|\| '')).replace(/\/$/, '');` | **class-results.html** ~115 |
| **fetch** | `fetch(\`${API}/api/regatta/${encodeURIComponent(regattaId)}?t=${Date.now()}\`)` | `const apiUrl = \`${API}/api/regatta/...\`;` then `fetch(apiUrl)` | **class-results.html** ~148–150 |
| **Error on !ok** | `throw new Error('Failed to load regatta data');` | `throw new Error('Failed to load regatta data (HTTP ' + regattaDataResponse.status + '). Local: run...');` | **class-results.html** ~150 |
| **dateTimeStr fallback** | `'Unknown'` | `'date not recorded'` | **class-results.html** ~157 |

### 4.3 regatta/results.html

| Area | LIVE | LOCAL |
|------|------|--------|
| **API** | `window.API_BASE \|\| window.location.origin` | Same + base tag + parent.API_BASE + .replace(/\/$/, '') (same pattern as class-results) |

### 4.4 regatta/class/podium/podium.html

| Area | LIVE | LOCAL |
|------|------|--------|
| **API** | `(window.parent && window.parent.API_BASE) \|\| window.API_BASE \|\| window.location.origin` | Same + base tag + .replace(/\/$/, '') |

---

## 5. Confirmations

| Question | Answer |
|----------|--------|
| **Is LOCAL using /regatta?slug= ?** | **No.** Both use `/regatta/class/class-results.html?regatta_id=...&class=...&regatta_slug=...&class_slug=...`. No `?slug=` in the iframe URL. |
| **Is LOCAL using old /results/ endpoint?** | **No.** The only API call from the regatta modal is `GET /api/regatta/{regatta_id}`. No `/results/` or `/api/results/` in this flow. |
| **Is LOCAL using wrong API base (localhost vs prod)?** | **No.** LOCAL uses `window.location.origin` (or parent’s `API_BASE`), so when you open `http://192.168.0.130:8081`, the API base is `http://192.168.0.130:8081`. It is not hardcoded to localhost or prod. |

---

## 6. Root cause

**The request path and endpoint are the same on LIVE and LOCAL.**  
The iframe loads `.../regatta/class/class-results.html?regatta_id=385&class=...` and then calls `GET {origin}/api/regatta/385`. On LIVE, origin is `https://sailingsa.co.za` and that server serves both the app and `/api/regatta/...`. On LOCAL, origin is `http://192.168.0.130:8081`; if **that** server is a **static-only** server (e.g. `python -m http.server 8081` or a dev server that doesn’t proxy to the API), then `GET http://192.168.0.130:8081/api/regatta/385` returns **404** (or a non-200), so you see "Failed to load regatta data".

So:

- **Root cause:** The host:port you use for the app on LOCAL (e.g. 8081) is **not** serving the FastAPI app that implements `GET /api/regatta/{regatta_id}`. It is serving only static files (or something else), so the API request fails (typically 404).
- **Not caused by:** Wrong endpoint, wrong API base, slug vs regatta_id, or old /results/ usage. Those match LIVE.

---

## 7. Exact file + line responsible (when it fails)

| Role | File | Line(s) |
|------|------|--------|
| **JS that triggers the modal** | `sailingsa/frontend/index.html` | `showRegattaResultChoice` ~4391; `navigateToClassResults` ~4473; `openResultPageInModal` ~4504 |
| **fetch() that fails on local** | `sailingsa/frontend/regatta/class/class-results.html` | ~148–150 (`apiUrl` build and `fetch(apiUrl)`) |
| **Backend route** | `api.py` | `@app.get("/api/regatta/{regatta_id}")` → `def api_regatta(regatta_id: str)` ~5436–5437 |

The **failure** (404/500) is observed when the request issued at **class-results.html** ~148–150 gets a non-2xx response from whatever is serving the current origin (e.g. 8081). The code that **builds** the request is correct; the **server** at that origin on LOCAL is not the API.

---

## 8. What changed compared to LIVE (summary)

| File | What changed vs LIVE |
|------|----------------------|
| **index.html** | `API_BASE` set with `.replace(/\/$/, '')` and comment about local/live. |
| **regatta/class/class-results.html** | Added `<base href="/">` + script to set base; API uses `window.parent.API_BASE` when present and `.replace(/\/$/, '')`; fetch stored in `apiUrl`; error message includes HTTP status and uvicorn hint; `dateTimeStr` fallback `'date not recorded'` (LIVE: `'Unknown'`). |
| **regatta/results.html** | Same base + API pattern as class-results. |
| **regatta/class/podium/podium.html** | Base tag + script; API has `.replace(/\/$/, '')`. |

None of these changes alter the **endpoint** or **when** the fetch runs; they only change how the base URL is chosen and how errors are reported. The functional failure on LOCAL is that the server at the app’s origin does not serve `/api/regatta/{regatta_id}`.
