# Sailors Media Tab & Media Scores — Consolidated Reference

Single reference for **Sailors Media Tab** (sailor profile “Media” tab) and **media scores**: code, READMEs, API, DB, and env. Use this for the **Sailor Media Tab Task** agent scope.

---

## 1. What This Covers

- **Sailors Media Tab**: UI tab “Media” on sailor profile: “Sailor X in the Media”, cards from `sailor_public_mentions`, empty state, “View sources” link.
- **Media scores**: `sailor_media_score` table and jobs that compute/update scores; used to decide who gets discovery and to show “media_score” in API.

---

## 2. Frontend (Media Tab UI)

| File | Purpose |
|------|--------|
| `sailingsa/frontend/index.html` | Main app: Media tab button `data-tab="media"`, panel `#sailor-tab-panel-media`, `.sailor-public-mentions`, media cards, empty state, fetch `/api/member/{sa_id}/public-mentions?fetch=1`, “View sources” link. CSS: `.media-list`, `.media-card`, `.media-thumb`, `.media-title`, `.media-snippet`, `.media-meta`, `.media-google`, `.sailor-media-page-header`, `.sailor-media-section-title`, `.media-empty-state`. |
| `sailingsa/frontend/public/sailor.html` | Public sailor page: media section `#media-section`, `#media-list`, same card styles. |
| `sailingsa/frontend/public/components/public-mention-card.html` | Reusable media card component. |
| `sailingsa/frontend/public/components/public-mention-card.js` | Logic for public mention card. |

**Contract**: Media tab shows only `is_valid = true` items; thumbnails from local cache or remote; pinned first, then by date DESC. Empty state: juniors get limited-message; adults get “No public mentions yet.”

---

## 3. API

| Location | Purpose |
|----------|--------|
| `api.py` | `GET /api/member/{sa_id}/public-mentions` — returns `sailor_public_mentions` rows for `sa_id` (plus optional merge with regatta mentions). Query param `fetch=1` triggers background `fetch_media_for_sailor()` when rate limit allows. Returns `{ "items": [...], "media_score": N }`. |
| `api.py` | `api_sailors_media(sa_id)` — same data as above, fetch by `sa_id` only. |
| `api.py` | Helper for News: reads `sailor_media_score` + `sailor_public_mentions` (e.g. sailors with `media_score >= threshold`). |
| `api.py` | `filter_public_media()` — age/domain filtering for public media (e.g. juniors no social). |

**Rule**: Media tab displays ALL rows from `sailor_public_mentions` for that sailor (no extra relevance/age filters beyond `is_valid`). Use **numeric `sa_id`** only (never slug) when calling the API.

---

## 4. Database

### Tables

- **`sailor_public_mentions`**  
  - Created: `database/migrations/132_sailor_public_mentions.sql`  
  - Columns: `id`, `sa_id`, `headline`, `snippet`, `source`, `url` (UNIQUE), `type`, `published_at`, `thumb_url`, `created_at`; later migrations may add `is_valid`, `is_pinned`, `thumb_local_path`, `last_validated_at`, etc.  
  - Indexes: `sa_id`, `published_at DESC`.  
  - Purpose: Stored mentions for sailor Media tab; API returns these for `/api/member/{sa_id}/public-mentions`.

- **`sailor_media_score`**  
  - Used by: `api.py` (public-mentions, News), scoring jobs.  
  - Holds: `sa_id`, `sailor_name`, `media_score`, `media_status`, `processed_at`, etc.  
  - Purpose: Score used for “who gets discovery” and for API `media_score` in response.

- **`sas_id_personal`** (tracking)  
  - Migration 137: `media_last_fetched_at`, `media_fetch_status`, `media_fetch_error`.  
  - Purpose: Rate limit media refresh (e.g. max once per 24h).

### Migrations (media / mentions)

- `database/migrations/127_regatta_public_mentions.sql` — regatta mentions (can be merged with sailor mentions in API).
- `database/migrations/131_roger_hudson_google_style_media.sql` — Roger Hudson media in regatta mentions.
- `database/migrations/132_sailor_public_mentions.sql` — creates `sailor_public_mentions`.
- `database/migrations/133_roger_hudson_sailor_public_mentions.sql` — seed Roger Hudson.
- `database/migrations/134_remove_roger_from_regatta_mentions.sql` — cleanup.
- `database/migrations/135_timothy_weaving_sailor_public_mentions.sql` — seed Timothy Weaving.
- `database/migrations/136_timothy_weaving_optimist_chairpersons_report.sql` — extra seed.
- `database/migrations/137_add_media_fetch_tracking.sql` — media fetch tracking on `sas_id_personal`.

---

## 5. Jobs (Code & READMEs)

### Fetch / discovery (fill Media tab)

| File | Purpose |
|------|--------|
| `jobs/sailor_media_fetch.py` | Core: `fetch_media_for_sailor()`, web search, validation, insert into `sailor_public_mentions`. Used by API when `fetch=1`. |
| `jobs/README_sailor_media_fetch.md` | On-view fetch: frontend calls `GET /api/member/{sa_id}/public-mentions?fetch=1` → API runs fetch, returns merged list. Needs `SERPAPI_API_KEY` or `BING_SEARCH_KEY`. CLI: `SERPAPI_API_KEY=... python3 jobs/sailor_media_fetch.py 21172`. |

### Batch fetch

| File | Purpose |
|------|--------|
| `jobs/batch_fetch_all_sailors_media.py` | Batch all sailors (or `--limit`, `--offset`, `--sa-id`, `--force`, `--delay`). Google AI summary + phases 0/1/2, stores in `sailor_public_mentions`. |
| `jobs/batch_fetch_priority_sailors_media.py` | Same idea for priority/top sailors. |
| `jobs/README_batch_media_fetch.md` | Usage, scheduling (cron), what the script does. |

### Refresh by score / recent

| File | Purpose |
|------|--------|
| `jobs/refresh_sailor_media_by_score.py` | Refresh media for sailors by score (e.g. score ≥ 1). Used by `run_media_refresh_all.sh`. |
| `jobs/refresh_sailor_media_recent.py` | Refresh recent sailors; used when Media tab is opened and item count is 0 (e.g. with `--sa-id`). |

### Media scores (scoring)

| File | Purpose |
|------|--------|
| `jobs/score_all_sailors_media.py` | Score sailors (populate/update `sailor_media_score`). |
| `jobs/score_all_sailors_media_with_output.py` | Same with extra output. |
| `process_new_podium_media_scores.py` | New podium results → media scoring (passes 1–3). |
| `second_pass_media_scoring.py` | Second pass scoring. |
| `third_pass_podium_sailors.py` | Podium sailors pass. |
| `process_all_sailors_comprehensive.py` | Comprehensive scoring run. |
| `process_batch_5.py`, `process_batch_20.py`, `process_manual_batch.py` | Batch scoring. |
| `manual_search_and_score.py` | Manual search and score. |
| `get_scoring_summary.py` | Summary: score 0 vs >0, remaining. Expects `sailor_media_score` (says “Run: python3 jobs/score_all_sailors_media.py” if missing). |
| `check_scoring_health.py` | Health check for scoring. |
| `monitor_media_scores_realtime.py` | Realtime monitoring. |
| `monitor_scoring_progress.py` | Progress monitoring. |
| `audit_top_sailors_in_batch.py` | Audit top sailors in batch. |
| `docs/MEDIA_SCORING_AUTOMATION.md` | Doc: only new podium results can create new media scores; `process_new_podium_media_scores.py` usage and cron. |

### Maintenance & quality

| File | Purpose |
|------|--------|
| `jobs/sailor_media_maintenance.py` | URL revalidation (link rot), thumbnail health; marks broken as invalid, never deletes. |
| `jobs/README_sailor_media_maintenance.md` | Dry-run, cron, options (`--skip-urls`, `--skip-thumbs`). |
| `jobs/validate_mention_urls.py` | Validate URLs (404/410 etc.); remove or report invalid. `--table sailor` for sailor mentions only. |
| `jobs/README_validate_mention_urls.md` | Usage, dry-run, `--table regatta|sailor|both`. |
| `jobs/fetch_mention_thumbnails.py` | Populate `thumb_url` (or local path) for mentions. `--table sailor` for sailor media. |
| `jobs/README_fetch_mention_thumbnails.md` | `--remote` vs `--local`, dry-run. |
| `jobs/backfill_media_thumbnails.py` | Backfill thumbnails. |
| `jobs/cleanup_bad_media_mentions.py` | Remove bad mentions. |

### Ingestion (social / news → sailor_public_mentions)

| File | Purpose |
|------|--------|
| `jobs/ingest_facebook_to_sailor_media.py` | Facebook posts → `sailor_public_mentions` (so they appear in News and Sailors Media Tab). |
| `jobs/ingest_trusted_facebook_posts.py` | Trusted Facebook pages ingestion. |
| `jobs/force_ingest_sailor_results.py` | Force ingest for a sailor (e.g. SERPAPI); can insert into sailor mentions. |
| `jobs/force_ingest_local_sa_news.py` | Local SA news ingest. |
| `jobs/ingest_regatta_public_mentions.py` | Regatta-level mentions (separate from sailor-specific). |

### Scripts & shell

| File | Purpose |
|------|--------|
| `run_media_refresh_all.sh` | Run media refresh for all (score ≥ 1). Uses `jobs/refresh_sailor_media_by_score.py`. Set `SERPAPI_API_KEY` (or equivalent). |
| `check_media_status.py` | Check media status. |
| `test_media_display.py` | Test media display. |
| `test_api_search_no_media_score.py` | Test API search without media score. |

---

## 6. Other Documentation (Summaries / Pointers)

- **`SEARCH_API_SETUP.md`** — Why Media tab can show “No public mentions yet” (no search API key); SerpAPI vs Bing; env vars; re-run fetch for test sailors.
- **`MEDIA_SEARCH_CODE_INVENTORY.md`** — Inventory of media search code.
- **`MEDIA_SEARCH_CODE_DOCUMENTATION.md`** — Full system doc for media search.
- **`MEDIA_SEARCH_FILES_LIST.md`** — List of files (core, batch, DB, docs); “to remove cleanly” checklist.
- **`ALL_MEDIA_SEARCH_CODE.txt`** — Raw code dump for media search.
- **`docs/README_SAILOR_PROFILE_SYSTEM.md`** — Profile system: Media tab rules, card structure, empty states, background fetch, maintenance flow, age/domain rules.
- **`docs/PUBLIC_REGATTA_MENTIONS_SCHEMA.md`** — Regatta mentions concept (sailors inherit via participation).
- **`FETCH_ROGER_HUDSON.md`** — Roger Hudson fetch notes.
- **`TIMOTHY_PROFILE_PREVIEW.md`** — Timothy profile/Media tab preview.
- **`AI_OVERVIEW_PROFILE_INTEGRATION.md`** / **`docs/AI_OVERVIEW_INTEGRATION.md`** — AI overview and profile integration.

---

## 7. Environment Variables

- **`SERPAPI_API_KEY`** — SerpAPI key for search (preferred for fetch).
- **`BING_SEARCH_KEY`** — Alternative search API.
- **`DB_URL`** — Database connection (defaults used if not set).

Without a search API key, DuckDuckGo fallback often returns 0 results → “No public mentions yet.”

---

## 8. Agent / Task Scope (Sailor Media Tab Task)

When working on **Sailors Media Tab** or **Sailor Media Tab Task**:

- **In scope**: Media tab UI in `sailingsa/frontend/index.html` and `sailingsa/frontend/public/sailor.html`; sailors media endpoint and related logic in `api.py`; `sailor_public_mentions` and `sailor_media_score`; all jobs under `jobs/` that feed or maintain the Media tab and media scores (fetch, batch, refresh, score, maintain, validate, thumbnails, ingest).
- **Docs**: This file plus the READMEs and docs listed above.
- **Rule**: Prefer small, one-concern edits; don’t change other tabs (Profile, Regattas, Activity) or unrelated API unless asked.

See also: **`.cursor/rules/sailors-media-tab.mdc`** and **`AGENTS.md`** (Named agents / tasks).
