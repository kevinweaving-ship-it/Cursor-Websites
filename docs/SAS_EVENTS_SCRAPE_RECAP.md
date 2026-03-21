# SAS Events Scrape — Recap for GPT / Agents

This doc summarizes what has been done for the SAS (sailing.org.za) events scrape, which tables store the data, how the pipeline works, and how to report on auto-scrapes (when last run, what was scraped/added).

---

## 1. What has been done (SAS scrape)

- **List scraper**  
  - **Script:** `scrape_sas_events_list.py` (project root).  
  - **Source:** https://www.sailing.org.za/events/ (upcoming) and https://www.sailing.org.za/events/list/past (past).  
  - **Behaviour:** Paginates both list endpoints until a page returns no events. Parses each event card for: title, date range, venue, category, details URL. From the details URL it derives either `sas_event_id` (sailing.org.za/events/&lt;id&gt;) or `external_host` + `external_event_id` (e.g. Revolutionise, laser.org.za).  
  - **Modes:**  
    - **List-only (default for daily):** `--no-detail` — no per-event detail fetch; fast; venue/category often from list HTML (can be noisy).  
    - **With detail:** no `--no-detail` — fetches each event’s detail page for host, location, address, NOR/SI/results URLs, description, contact, organiser; slow (~15–20 min for 900+ events).  
  - **Output:** CSV: `sas_events_list.csv` (and with `--date-stamp`: `sas_events_list_YYYYMMDD.csv`). Written to `--output-dir` (e.g. `sailingsa/deploy`).

- **Loader**  
  - **Script:** `load_events_csv_to_db.py` (project root).  
  - **Input:** CSV produced by `scrape_sas_events_list.py`.  
  - **Behaviour:** Upserts into `events` on `(source, source_event_id)`. Sets `last_seen_at = now()` and `scrape_run_id = YYYYMMDDHHMM` (UTC) for the run.  
  - **Requires:** `DATABASE_URL` or `DB_URL`; migrations 145 and 146 applied.

- **Database**  
  - **Migrations:**  
    - `database/migrations/145_events_table.sql` — creates `events` table (see below).  
    - `database/migrations/146_events_list_scrape_columns.sql` — adds columns: category, description, contact, organiser, address, results_url, other_docs.  
  - **Live:** Both migrations have been run on the live server; events are loaded there.

- **API and audit UI**  
  - **API:** `GET /admin/api/events?is_past=true|false&limit=500&offset=0` (admin only, live host only). Returns events from `events` table.  
  - **Audit page:** https://sailingsa.co.za/admin/events-audit — shows events as cards: Title, date range (e.g. Sat 14 Mar 2026 – Sun 15 Mar 2026), Venue/Host (sanitized; "—" if HTML garbage), Category, Details link. Filter: All / Past / Upcoming; search by title, venue, source.

- **Daily auto scrape**  
  - **Runner:** `sailingsa/deploy/run-daily-events-scrape.sh`.  
  - **Behaviour:** Runs the scraper with `--output-dir sailingsa/deploy`, `--date-stamp`, and `--no-detail`. If `DATABASE_URL` or `DB_URL` is set, runs `load_events_csv_to_db.py` to upsert into `events`.  
  - **Log:** `sailingsa/deploy/logs/daily-events-scrape.log` (created by script; append each run).  
  - **Cron (example):** On server: `0 4 * * * /var/www/sailingsa/deploy/run-daily-events-scrape.sh --on-server >> /var/www/sailingsa/deploy/logs/daily-events-scrape.log 2>&1`.

- **Venue fix (detail pages)**  
  - **Venue source:** From the **Details card Location row** on event detail pages (e.g. revolutionise.com.au/…/events/&lt;id&gt;). Only text content is used; attributes (target=, href=, rel=) are ignored.  
  - **Validation:** Scraper and loader reject any venue/host value containing `target=`, `href=`, `http`, or `blank`; such values are not stored.  
  - **DB correction:** Run `database/migrations/170_events_clear_invalid_venue.sql` to clear bad venue_raw/host_club_name_raw, then run a full scrape **without** `--no-detail` and reload CSV to repopulate.  
  - **Verification:** e.g. event "TuziTekwini Ocean Race" should show Venue → King Shaka Yacht Club, correct date range, status upcoming.

---

## 2. Data stored and which tables

**Single table: `events`**

- **Identity:** `source` (e.g. `sas`, `external`), `source_event_id` (e.g. SAS event id or external id). Unique on `(source, source_event_id)`.  
- **Core:** `event_name`, `start_date`, `end_date`, `event_year`, `source_url`.  
- **Location:** `location_raw`, `venue_raw`, `host_club_name_raw`, `host_club_id` (FK to clubs), `province_code`, `address`.  
- **Docs:** `nor_url`, `si_url`, `results_url`, `other_docs`.  
- **Extra (from list/detail scrape):** `category`, `description`, `contact`, `organiser`.  
- **Lifecycle:** `event_status` — `unknown` | `upcoming` | `live` | `completed` | `cancelled` | `archived`. Set from CSV `is_past`: past → `completed`, else → `upcoming`.  
- **Audit:** `first_seen_at`, `last_seen_at`, `scrape_run_id` (set on each load run as `YYYYMMDDHHMM` UTC).  
- **Future (not populated yet):** `regatta_id` (link to regattas), `match_score`, `match_method`.

No other tables are used for the SAS events scrape; regattas/results are separate. Full schema: see `database/migrations/145_events_table.sql` and `146_events_list_scrape_columns.sql`.

---

## 3. How it all works (end-to-end)

1. **Scrape:** `scrape_sas_events_list.py` fetches list pages (upcoming + past), parses cards, optionally fetches each detail URL. Writes CSV.  
2. **Load:** `load_events_csv_to_db.py` reads CSV, maps columns to `events` columns, upserts by `(source, source_event_id)`, updates `last_seen_at` and `scrape_run_id`.  
3. **Consume:** Admin audit page calls `GET /admin/api/events`; backend reads from `events`; UI shows cards with title, date range, venue, category, Details link.  
4. **Daily:** Cron runs `run-daily-events-scrape.sh` → scraper (list-only) → CSV → loader (if DB_URL set) → log appended.

Detail scrape is optional and not used in the daily run; it improves venue/category/address etc. when run occasionally and CSV re-loaded.

---

## 4. AutoScrapes: when last run and what was scraped/added

- **When last run**  
  - **From DB (authoritative for “last load”):**  
    - `SELECT MAX(last_seen_at) AS last_load_at, MAX(scrape_run_id) AS last_scrape_run_id FROM events;`  
  - **From log (authoritative for “last script run”):**  
    - On server: `sailingsa/deploy/logs/daily-events-scrape.log` — each run starts with a line like `YYYY-MM-DDTHH:MM:SSZ --- Daily SAS events list scrape ---` and ends with `Done.`  
    - So: “last run” = last such block in that file.

- **What was scraped/added**  
  - **From log:** The loader prints to stderr (captured in the same log when run by the daily script):  
    - `Loaded N rows from ...`  
    - `Upserted N events (scrape_run_id=YYYYMMDDHHMM)`  
  - **From DB:**  
    - Total events: `SELECT COUNT(*) FROM events;`  
    - Events in last run: `SELECT COUNT(*) FROM events WHERE scrape_run_id = (SELECT MAX(scrape_run_id) FROM events);`  
    - Past vs upcoming: `SELECT event_status, COUNT(*) FROM events GROUP BY event_status;`

**Summary for a “status” report:**  
- Last load time: `MAX(last_seen_at)` from `events`.  
- Last scrape run id: `MAX(scrape_run_id)` from `events`.  
- Last script run: last “--- Daily SAS events list scrape ---” block in `sailingsa/deploy/logs/daily-events-scrape.log`.  
- Rows last loaded: count where `scrape_run_id = MAX(scrape_run_id)`, or from log “Upserted N events”.  
- Total in DB: `COUNT(*)` from `events`.

---

## 5. File reference

| Item | Purpose |
|------|--------|
| `scrape_sas_events_list.py` | List (+ optional detail) scraper; outputs CSV |
| `load_events_csv_to_db.py` | Upsert CSV → `events` |
| `database/migrations/145_events_table.sql` | Create `events` table |
| `database/migrations/146_events_list_scrape_columns.sql` | Extra columns for list scrape |
| `sailingsa/deploy/run-daily-events-scrape.sh` | Daily auto: scrape then load |
| `sailingsa/deploy/logs/daily-events-scrape.log` | Log of each daily run (on server) |
| `docs/EVENTS_TABLE_AND_SCRAPE.md` | Full design and scrape strategy |
| `/admin/events-audit` | Audit UI (live) |
| `/admin/api/events` | API for audit page |

---

*This recap is for GPT/agents to understand the SAS events scrape implementation, stored data, and how to report on auto-scrapes.*
