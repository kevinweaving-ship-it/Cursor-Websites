# Admin Dashboard – Code and CSS (https://sailingsa.co.za/admin/dashboard)

The admin dashboard is **server-rendered in the FastAPI backend**. There is no separate HTML or CSS file; everything lives in **`api.py`**.

---

## 1. Where the code lives

| Item | Location |
|------|----------|
| **Route** | `api.py` line **996**: `@app.get("/admin/dashboard", response_class=HTMLResponse)` |
| **Handler** | `api.py` line **997**: `def admin_dashboard(request: Request):` |
| **Auth & logic** | Lines **998–1174** (host check, role, DB queries, counts) |
| **HTML + CSS + JS** | Lines **1175–2362**: one `return HTMLResponse(content=f""" ... """, headers={"Cache-Control": "no-store"})` |
| **CSS** | Inside that string: **lines 1179–1381** (single `<style>...</style>` block) |

The response is **self-contained**: no external stylesheet is loaded. Layout uses the same skeleton as the landing (`.site-wrapper`, `.site-header`, `.container`, `.main-nav`) but **all visual styling is in the embedded `<style>`**.

---

## 2. Python route and auth (summary)

```python
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if socket.gethostname() != ADMIN_LIVE_HOSTNAME:
        raise HTTPException(status_code=403, detail="Admin dashboard disabled on local environment.")
    role = _get_session_role(request)
    if not role or role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    # ... DB connection, queries for:
    # uptime_seconds, signed_in_rows, offline_rows, registered_rows, registered_count,
    # sailors_rows, clubs_rows, regattas_rows, races_rows,
    # total_sailors, total_clubs, total_regattas, total_races,
    # review_sailors_count, review_classes_count, review_clubs_count
    # ...
    return HTMLResponse(content=f""" ... full HTML below ... """, headers={"Cache-Control": "no-store"})
```

---

## 3. Full CSS for Admin Dashboard

This is the exact CSS inside the dashboard’s `<style>` block (lines 1179–1381 in `api.py`). In the source, braces are escaped as `{{` and `}}` in the f-string; below they are written as normal `{` and `}`.

```css
.section {
    margin-top: 1.5rem;
}
.status-card {
    background: #1e293b;
    padding: 16px 20px;
    border-radius: 8px;
}
.status-good {
    color: #22c55e;
    font-weight: bold;
}
.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
}
.metric-tile {
    background: #1e293b;
    padding: 20px;
    border-radius: 8px;
}
.metric-tile .title {
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.metric-tile .value {
    font-size: 28px;
    font-weight: bold;
    margin-top: 8px;
}
.metric-tile {
    cursor: pointer;
}
.metric-tile:hover {
    background: #334155;
}
.section-title {
    font-size: 18px;
    color: #38bdf8;
    margin-bottom: 12px;
}
.admin-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.admin-table th, .admin-table td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #334155;
}
.admin-table th { color: #38bdf8; }
.admin-table .active-yes { color: #22c55e; font-weight: bold; }
.admin-table .active-no { color: #94a3b8; }
.admin-table .active-logout { color: #ef4444; font-weight: bold; }
.admin-table tr.logout-row { transition: opacity 3s ease-out; }
.admin-table tr.logout-row.fade-out { opacity: 0; }
.active-sailors-table a { color: #7dd3fc; font-weight: 600; }
.active-sailors-table a:hover { text-decoration: underline; }
#classes-search { margin-bottom: 10px; padding: 8px 12px; width: 100%; max-width: 320px; box-sizing: border-box; }
#regattas-search { margin-bottom: 10px; padding: 8px 12px; width: 100%; max-width: 320px; box-sizing: border-box; }
.no-results-row { opacity: 0.4; }
.restart-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #94a3b8;
    border-top-color: #38bdf8;
    border-radius: 50%;
    animation: restart-spin 0.8s linear infinite;
}
@keyframes restart-spin { to { transform: rotate(360deg); } }
.session-history-link {
    cursor: pointer;
    color: #38bdf8;
    text-decoration: underline;
}
.session-history-link:hover { color: #7dd3fc; }
#sessionHistoryModal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 1001;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
#sessionHistoryModal.show { display: flex; }
#sessionHistoryModal .modal-inner {
    background: #1e293b;
    border-radius: 12px;
    max-width: 90vw;
    max-height: 85vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
#sessionHistoryModal .modal-body { overflow: auto; padding: 16px; font-size: 14px; }
#sessionHistoryModal .close-btn { background: #334155; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
#sessionHistoryModal table { width: 100%; border-collapse: collapse; margin-top: 8px; }
#sessionHistoryModal th, #sessionHistoryModal td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #334155; }
.admin-restart-btn {
    cursor: pointer;
    padding: 8px 16px;
    border-radius: 6px;
    background: #dc2626;
    color: white;
    border: none;
    font-size: 14px;
    font-weight: bold;
}
.admin-restart-btn:hover {
    background: #b91c1c;
}
#adminRestartModal {
    display: none;
    position: fixed;
    z-index: 10000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.6);
    align-items: center;
    justify-content: center;
}
#adminRestartModal.show { display: flex; }
#adminRestartModal .modal-box {
    background: #1e293b;
    padding: 24px;
    border-radius: 8px;
    max-width: 400px;
}
#adminRestartModal .modal-actions { margin-top: 16px; }
#adminRestartModal .modal-actions button { margin-right: 8px; padding: 8px 16px; cursor: pointer; border-radius: 6px; border: none; }
#adminModal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 1000;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
#adminModal.show { display: flex; }
#adminModal .modal-inner {
    background: #1e293b;
    border-radius: 12px;
    max-width: 90vw;
    max-height: 85vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
#adminModal .modal-header {
    padding: 16px 20px;
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
#adminModal .modal-body { overflow: auto; padding: 16px; }
#adminModal table { width: 100%; border-collapse: collapse; font-size: 14px; }
#adminModal th, #adminModal td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #334155; }
#adminModal th { color: #38bdf8; }
#adminModal .close-btn { background: #334155; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
#adminModal .close-btn:hover { background: #475569; }
#adminModal .loading { color: #94a3b8; }
#adminModal .err { color: #f87171; }
#adminModal .active-yes { color: #22c55e; font-weight: bold; }
#adminModal .active-no { color: #94a3b8; }
#adminModal #adminModalSearch { margin-bottom: 12px; padding: 8px 12px; width: 100%; max-width: 400px; box-sizing: border-box; }
.stat-cards-row { display: flex; flex-direction: row; flex-wrap: wrap; gap: 18px; align-items: flex-start; justify-content: center; }
.stat-card { display: flex; flex-direction: column; align-items: center; gap: 7px; padding: 18px; background: #001f3f; border-radius: 14px; margin-bottom: 18px; width: fit-content; }
.stat-value-wrap { flex-shrink: 0; width: 83px; height: 83px; position: relative; display: flex; align-items: center; justify-content: center; overflow: visible; margin: 0; transform: translateY(-8px); }
.stat-ring { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.stat-ring circle { fill: none; stroke-width: 14; stroke-linecap: round; stroke-dasharray: 440; transform: rotate(-90deg); transform-origin: 50% 50%; }
.stat-ring .ring-track { stroke: #3a3d42; stroke-dashoffset: 0; }
.stat-ring .ring-fill { stroke: #B3E5FC; stroke-dashoffset: 440; }
.stat-ring .ring-fill.ring-fill-green { stroke: #00E676; }
.stat-ring .ring-fill.ring-fill-orange { stroke: #FF9500; }
.stat-ring .ring-fill.ring-fill-red { stroke: #FF3B30; }
.stat-value-inner { position: absolute; inset: 0; z-index: 1; display: flex; align-items: center; justify-content: center; font-size: 1.01rem; font-weight: 800; color: #fff; line-height: 1; text-align: center; transform: translateY(9px); }
.stat-label-above { font-size: 0.81rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #fff; text-align: center; }
.stat-label-below { font-size: 0.81rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #fff; text-align: center; }
@media (max-width: 640px) {
    .stat-cards-row { flex-wrap: nowrap; gap: 7px; justify-content: space-between; }
    .stat-card { padding: 7px 5px; margin-bottom: 0; border-radius: 9px; gap: 2px; flex: 1 1 0; min-width: 0; }
    .stat-value-wrap { width: 51px; height: 51px; transform: translateY(-3px); }
    .stat-ring circle { stroke-width: 9; }
    .stat-value-inner { font-size: 0.69rem; transform: translateY(5px); }
    .stat-label-above, .stat-label-below { font-size: 0.58rem; letter-spacing: 0.02em; }
}
#admin-stat-card-1 { cursor: pointer; }
#active-sailors-panel-wrap { margin-top: 8px; }
#active-sailors-search { margin-bottom: 10px; padding: 8px 12px; width: 100%; max-width: 320px; box-sizing: border-box; }
```

---

## 4. Color and layout tokens (dashboard)

| Token | Value | Use |
|-------|--------|-----|
| Card/panel background | `#1e293b` | `.status-card`, `.metric-tile`, modals |
| Stat card background | `#001f3f` | `.stat-card` (navy) |
| Accent / links | `#38bdf8` | `.section-title`, `.admin-table th`, links |
| Muted text | `#94a3b8` | `.metric-tile .title`, `.active-no`, loading |
| Success | `#22c55e` | `.status-good`, `.active-yes` |
| Error / logout | `#ef4444`, `#dc2626` | `.active-logout`, `.admin-restart-btn` |
| Border / table | `#334155` | table borders, modal header, close btn |
| Ring track | `#3a3d42` | stat circle track |
| Ring fill (default) | `#B3E5FC` | stat 1 |
| Ring green/orange/red | `#00E676`, `#FF9500`, `#FF3B30` | stat 2–4 |

Layout: `.metrics-row` is a 4-column grid; stat cards use flex and SVG rings; modals are fixed full-screen with `.modal-inner` centered. Breakpoint: `640px` for stat cards.

---

## 5. HTML structure (outline)

- `<html>` → `<head>` → `<title>Admin Dashboard</title>` → `<style>...</style>` → `</head>`
- `<body>`
  - `<div class="site-wrapper">`
    - `<header class="site-header">` → `<div class="container">` → logo “SailingSA”, `<nav class="main-nav">` (Dashboard, Data Review) → `</header>`
    - `<main class="content-container">`
      - Section: API uptime + Restart API button (`.status-card`)
      - Section: four stat cards (Active Sailors, Classes Sailed, Regatta’s Sailed, Races raced) with SVG rings
      - Panels (initially hidden): Active Sailors table, Classes table, Regattas table, Races table
      - Section: SYSTEM STATUS – `.metrics-row` (Registered Users, Online Users)
      - Section: Data Review – `.metrics-row` (Unresolved Sailors, Unknown Class Issues, Unknown Club Refs) with links to `/admin/review/*`
      - Section: Online Users table
      - Section: Offline table
      - Modals: `#adminModal`, `#sessionHistoryModal`, `#adminRestartModal`
    - `</main>`
  - `</div>`
  - `<script>...</script>` (uptime ticker, dashboard-data fetch, modal open/close, metric-tile clicks, stat-card panels, session history, restart flow)
  - `</body>` → `</html>`

---

## 6. Data and endpoints

- **Initial data:** From DB in `admin_dashboard()` (signed-in rows, registered count, review counts, etc.); some values are injected into the HTML (e.g. `{registered_count}`, `{len(signed_in_rows)}`, `{review_sailors_count}`).
- **Live data:** JavaScript calls `/admin/dashboard-data` and updates stat cards and Online Users table; `/admin/list/registered-users`, `/admin/list/classes`, `/admin/list/regattas`, `/admin/list/races` for modals/panels; `/admin/user-session-history/<sas_id>` for session history; POST `/admin/api/restart` for restart.

To change the dashboard’s code or CSS, edit the `admin_dashboard()` function in **`api.py`** (the f-string from ~1175 to 2362) and redeploy/restart the API.
