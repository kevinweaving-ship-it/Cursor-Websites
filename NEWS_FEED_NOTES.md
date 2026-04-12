# News Feed — Parked for Later

The news feed was **removed from the main homepage** and replaced with a **placeholder page** so you can return to it later without it affecting the main site.

## Current state

- **Homepage** (`/sailingsa/frontend/index.html`): No news section; no `loadSailingNews()` call.
- **News placeholder URL:** `http://192.168.0.130:8081/sailingsa/news` (or `/sailingsa/news/`) — shows only a "Latest News" banner, nothing else.
- **API still live:** `GET /api/news/latest` and background refresh in `api.py` are unchanged; you can use them when you restore the feed.

## Where the code lives (to restore later)

### Backend (unchanged)

- **File:** `api.py` (project root)
- **Cache / config:** `LATEST_NEWS_CACHE`, `LATEST_NEWS_CACHE_SEC`, `_news_cache_refresh_loop()`, `_fetch_latest_news_pipeline()`, `_load_sailor_names_for_news()`, `_load_podium_sailor_names_6m()`, etc.
- **Endpoint:** `GET /api/news/latest` — returns array of news items; never blocks (background refresh).
- **Redirect:** `GET /sailingsa/news` → `RedirectResponse("/sailingsa/news/")` so the placeholder page loads.

### Frontend (removed from index; keep as reference)

- **Removed from** `sailingsa/frontend/index.html`:
  - The `<section class="sailing-news-section">` block (header + `#sailing-news-list`).
  - The `loadSailingNews()` function and `relativeTime()` helper.
  - The `loadSailingNews()` call in `DOMContentLoaded`.
  - The `.sailing-news-*` CSS block (section title, cards, image wrap, body, loading/empty).

To **restore on the homepage**: re-add the section HTML, the CSS, and the `loadSailingNews` (and `relativeTime`) code, and call `loadSailingNews()` from `DOMContentLoaded`. The API and backend behaviour are already in place.

### Placeholder page

- **File:** `sailingsa/news/index.html`
- **URL:** `/sailingsa/news/` or `/sailingsa/news` (redirect)
- **Content:** Only a "Latest News" banner; no cards, no API call. You can later turn this into the full news page or move the feed back to the homepage.

## Spec reference

See **LATEST_NEWS_BETA_V1.md** in this folder for API response shape, sample `curl`, and behaviour (SA filter, sailor match, podium prioritisation, etc.).
