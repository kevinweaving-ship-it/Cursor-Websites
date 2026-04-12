# index2.html vs index.html – How It Should Work

## index2.html (reference)

- **URL:** http://192.168.0.130:8081/sailingsa/frontend/index2.html
- **Layout:** Single search bar in a `.search-header` below main header; secondary nav; then sailor + regatta search in dark blue `.search-header-container` blocks; one results area `#sailor-search-results`.
- **Logged-in profile:** Injected into `#sailor-search-results` via `showSailorStatsInResults()`. That div has `.sailor-search-results { max-height: 70vh; overflow-y: auto; }` – so in index2 the main profile is also inside a 70vh box (same trap unless you’re only testing dropdown).
- **No `#main-search-results`:** Only one results container: `#sailor-search-results` (used for both dropdown and logged-in profile).

## index.html (current)

- **URL:** http://192.168.0.130:8081/sailingsa/frontend/index.html
- **Layout:** Main header (logo + search field + auth); then sailor + regatta search in two dark blue `.search-header-container` blocks; then **two** results areas:
  - `#main-search-results` – main logged-in sailor profile (unified container).
  - `#sailor-search-results` – dropdown search results only.
- **Scroll fix in place:** At end of inline `<style>` (before `</style>`):
  - `html, body { overflow-y: auto !important; height: auto !important; min-height: 0 !important; }`
  - `.main-content, .layout-three-col, .main-column, .main-column .container { overflow: visible !important; max-height: none !important; }`
  - `#main-search-results, #main-search-results.sailor-search-results { max-height: none !important; overflow: visible !important; }`
- **Earlier in same file:** `.sailor-search-results:not(#main-search-results)` keeps 70vh only on the dropdown; `#main-search-results.sailor-search-results { max-height: none; overflow-y: visible; }`.

## What to do if scroll is still stuck

1. **Use the sailingsa frontend URL:**  
   http://192.168.0.130:8081/sailingsa/frontend/index.html  
   (Not http://192.168.0.130:8081/index.html – that’s the root landing page.)

2. **Hard refresh:** Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows) so cached CSS/JS is cleared.

3. **Restart API** so `/api/member/{id}/media` is loaded and the Media section loads (stops 404):
   ```bash
   cd "/Users/kevinweaving/Desktop/MyProjects_Local/Project 6"
   export DB_URL="${DB_URL:-postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master}"
   python3 -m uvicorn api:app --host 0.0.0.0 --port 8081 --reload
   ```

4. **Root redirect:** Opening `http://192.168.0.130:8081/index.html?profile=21172` redirects to `.../sailingsa/frontend/index.html?profile=21172` so you land on the fixed page.

## Summary

- index2 has a single results container and a slightly different header/search layout.
- index.html has separate `#main-search-results` (main profile) and `#sailor-search-results` (dropdown) and already has a full scroll-fix block at the end of its inline styles.
- If scroll is still stuck, it’s likely cache or wrong URL; use the sailingsa frontend URL and hard refresh after an API restart.
