# Systematic Cleanup Plan (Vibe Coder)

**Principle:** One phase at a time. Preserve functions. No breaking pages. Fully reversible.

---

## Phase 1: Archive backup files ✅ SAFE
- Create `ARCHIVE_BACKUPS_20260208/`
- **Move** (not delete) all `*.BU_*`, `*.bak`, `*.broken_*` into archive
- Live files untouched: `index.html`, `login.html`, `api.js`, `session.js`, etc.
- **Reversible:** `mv ARCHIVE_BACKUPS_20260208/* sailingsa/frontend/`

## Phase 2: Add DEBUG flag, wrap logs ✅ DONE
- Added `window.DEBUG_MODE = false` and `_dbg()` helper in index.html
- Replaced all `console.log('[DEBUG]'` with `_dbg('[DEBUG]'` in index.html and session.js
- session.js defines its own `_dbg` that respects `window.DEBUG_MODE`
- **Reversible:** Set `window.DEBUG_MODE = true` in console or index.html to restore logs

## Phase 3: Replace hardcoded IPs ✅ DONE
- api.js: fallback → `window.location.origin || ''`
- session.js: login URL → `(window.location.origin || '') + '/sailingsa/frontend/login.html'`
- results.html, class-results.html: API fallback → `window.location.origin || ''`
- **login.html** still has host-specific logic (localhost vs 192.168) — left as-is for now; can refactor later.

## Phase 4: (Future) Remove duplicate API_BASE logic
- Only after Phases 1–3 verified.
- Single source of truth for API base.

---

## DO NOT (this session)
- Delete any files
- Refactor function logic
- Touch api.py routes
- Change CSS that affects layout
- Merge duplicate auth branches in session.js
