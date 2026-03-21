# News Feed — Dedicated agent scope

When the user says **"News Feed"** or **"News Feed agent"**, limit changes to this scope only.

## Behaviour (rules in code)

- **Sections:** Two headers below "Latest News": **Local News** (~60%) and **International News** (~40%).
- **Recency (all applied):** Local = max 5 months **and** prefer ~50% from last 45 days. International = max 1 month. Most recent first; no duplicates (by URL).
- **Headline:** Clickable to **original article URL** (Google News redirects resolved; no news.google.com in API output).
- **Thumbnail:** Must have thumbnail or the item is dropped. No placeholders — backend drops items without image; frontend does not render any card without a valid image.
- **Local news search (automated):** (1) Primary SA sailing sites + Facebook. (2) **Sailor names** from large-regatta podiums (1st–3rd): multi-fleet ≥50 entries, single-fleet ≥10 entries, last 5 months. (3) **Regatta names** from DB (last 5 months). SerpAPI and Google RSS use base queries plus sailor/regatta name queries to find posts that mention those.
- **Automation:** Background thread in `api.py` runs the pipeline every `LATEST_NEWS_CACHE_SEC` (e.g. 30 min) to refresh the feed.

## Frontend

- **File:** `sailingsa/frontend/index.html`
- **Section:** `#landing-news-embed` (aria-label "Latest news"), `#landing-news-list`
- **CSS:** All `.news-feed-*` classes (e.g. `.news-feed-list`, `.news-feed-section-header`, `.news-feed-lead`, `.news-feed-compact-*`, `.news-feed-empty`)
- **JS:** `loadLandingNews()`, `renderCompactList()`, the fetch to `apiBase + '/api/news/latest'` and the logic that splits items into Local / International and renders HTML
- **Nav:** The "News" link that points to `/sailingsa/news/` (if present in the same file)

Optional / related:

- **Placeholder page:** `sailingsa/news/index.html` (dedicated news page; may be empty or a redirect)

## Backend / API

- **File:** `api.py`
- **Endpoints:** `GET /api/news/latest`, `POST /api/news/refresh`
- **Cache / config:** `LATEST_NEWS_CACHE`, `LATEST_NEWS_CACHE_SEC`, `_NEWS_CACHE_DIR`, `_NEWS_CACHE_FILE`
- **Functions:** `_load_news_cache_from_disk()`, `_save_news_cache_to_disk()`, `_news_cache_refresh_loop()`, `_fetch_latest_news_pipeline()`, and any helpers used only by the news pipeline (e.g. sailor names for news, podium names)

## Docs (reference only)

- `sailingsa/frontend/NEWS_FEED_NOTES.md` — current state, restore instructions
- `sailingsa/frontend/LATEST_NEWS_BETA_V1.md` — API response shape, behaviour
- `sailingsa/frontend/LATEST_NEWS_FRONTEND_CONTRACT.md` — frontend contract

## Out of scope for News Feed agent

- Sailor profile tabs (Profile, Regattas, Media, Activity)
- Search, auth, other API routes
- Standings, regattas, member finder

Do not change those unless the user explicitly asks. Prefer small, one-concern edits within the News Feed scope above.
