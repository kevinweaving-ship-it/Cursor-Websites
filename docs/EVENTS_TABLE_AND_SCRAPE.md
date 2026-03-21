# Event table and SAS events scrape

## Purpose

- **Event table**: Canonical list of events (past + upcoming) from [sailing.org.za/events/](https://www.sailing.org.za/events/), with links to our regattas (results) and to club pages.
- **Scrape**: Pull event list from SAS; capture both SAS event IDs and **external** event IDs (e.g. Revolutionise `334371`, laser.org.za `301648`) from detail URLs for matching.
- **Later**: Events page; link from results → event (past); upcoming vs past on club pages.

---

## Source: sailing.org.za/events/

- **List**: [https://www.sailing.org.za/events/](https://www.sailing.org.za/events/) (upcoming) and [Past](https://www.sailing.org.za/events/list/past).
- **Detail URLs** can be:
  - **SAS**: `https://www.sailing.org.za/events/293438` → SAS event ID `293438`.
  - **Revolutionise**: `https://www.revolutionise.com.au/29erclass/events/334371` → external host `revolutionise`, event ID `334371`.
  - **Other**: e.g. `https://www.laser.org.za/events/301648` → host `laser.org.za`, event ID `301648`.

Event ID in the URL (SAS or external) is the stable key for matching and de-duplication.

---

## Scrape strategy

1. **List scrape** (browser User-Agent):
   - GET `/events/`, `/events/list`, `/events/list/past`.
   - Parse each event card: **title**, **date range**, **venue** (club/location), **category**, **details URL**.
   - From details URL derive:
     - `sas_event_id` (if path is `/events/<digits>` on sailing.org.za), or
     - `external_host` + `external_event_id` (e.g. from `.../events/334371`).
2. **Wide scrape (optional)**:
   - For each details URL, GET the page and scrape extra fields (description, contact, etc.).
   - For Revolutionise/laser.org.za, parse their page to confirm event ID and title/date/venue.
3. **Output**: Structured rows (CSV/JSON or into `events` table) with at least: title, start_date, end_date, venue_text, category, details_url, sas_event_id (nullable), external_host (nullable), external_event_id (nullable).

---

## Event table (for later)

```sql
-- Optional: link to our regattas when we have results for this event
CREATE TABLE IF NOT EXISTS public.events (
  event_id         SERIAL PRIMARY KEY,
  -- Source identifiers (one of these set)
  sas_event_id     INT UNIQUE,                    -- sailing.org.za/events/293438
  external_host    TEXT,                          -- 'revolutionise', 'laser.org.za'
  external_event_id TEXT,                         -- '334371', '301648'
  -- Content
  title            TEXT NOT NULL,
  start_date       DATE,
  end_date         DATE,
  venue_text       TEXT,                          -- "Mossel Bay Sailing Club", "Langebaan"
  category         TEXT,                          -- "National Championships", "Training"
  details_url      TEXT NOT NULL,
  -- Match to our regattas (when we have results)
  regatta_id       TEXT REFERENCES regattas(regatta_id),
  -- Club (match venue_text to clubs for club-page listing)
  club_id          INT REFERENCES clubs(club_id),
  is_past          BOOLEAN,
  scraped_at       TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS events_external_uid
  ON events (external_host, external_event_id) WHERE external_host IS NOT NULL AND external_event_id IS NOT NULL;
```

- **Match to regattas**: By normalised title + date range, or by storing `sas_event_id` / `external_event_id` on `regattas` when we create a regatta from an event.
- **Results → event**: Results already link via `regatta_id`. When `events.regatta_id` is set, regatta page can show the event (and link to SAS/external details). "Past" events with a regatta = have results; "upcoming" = no regatta yet.
- **Club pages**: Filter `events` by `club_id` (or venue_text) for "Past events" and "Upcoming events" sections.

---

## Matching: old event ↔ results we have

- **We have**: `regattas` (event_name, start_date, end_date, host_club) and results linked by `regatta_id`.
- **We scrape**: SAS/external events (title, start_date, end_date, venue).
- **Match**: Normalise title (strip year/numbers, lowercase) and match date range; or match by `sas_event_id` / `external_event_id` if we later store that on regattas when creating from scrape.
- **Link from results to event**: Regatta page already exists; add optional "Event details" link to `events.details_url` when we have a matching event row.

---

## Club pages: past and upcoming events

- **Past**: Events where `is_past = true` and `club_id` = this club (or venue matches club).
- **Upcoming**: Events where `is_past = false` and same club.
- Data comes from the same scrape; club matching via `venue_text` → `clubs` (name/alias lookup).

---

## Scraper script

- **Script**: `scrape_sas_events_list.py`:
  - Fetch list page(s) with browser User-Agent.
  - **Pagination**: Fetches all pages for `/events/list` (upcoming) and `/events/list/past` (past) until a page returns no events — so **all past events as far back** and **all upcoming as far ahead** as the site lists (typical run: ~48 upcoming, ~913 past, date range e.g. 2019 → 2027).
  - Parse cards: title, dates, venue, category, details URL.
  - Parse details URL: if `sailing.org.za/events/<id>` → sas_event_id; if `.../events/<id>` on other host → external_host + external_event_id.
  - Output: `sas_events_list.csv` (and with `--date-stamp`: `sas_events_list_YYYYMMDD.csv`).
  - Options: `--output-dir DIR`, `--date-stamp` (for daily retention), `--no-detail` (list-only; full detail fetch for 900+ events takes ~15–20 min).
- **Wide scrape**: With detail (default): GET each event’s details URL to fill host, location, address, NOR/SI/results URLs, description, contact, organiser.

## Events table (DB)

- **Migrations**: Run `database/migrations/145_events_table.sql` then `146_events_list_scrape_columns.sql` (adds category, description, contact, organiser, address, results_url, other_docs).
- **Load CSV → DB**: `load_events_csv_to_db.py --csv path/to/sas_events_list.csv` (upserts on `source` + `source_event_id`). Requires `DATABASE_URL` or `DB_URL`.
- **Audit page (live)**: **https://sailingsa.co.za/admin/events-audit** — temp page to view/audit scraped events (Admin only). Shows All / Past / Upcoming, search, table with Title, dates, Venue, Status, Source, Link.
- **API**: `GET /admin/api/events?is_past=true|false&limit=500&offset=0` returns events from DB (Admin only).

## Daily auto scrape

- **Runner**: `sailingsa/deploy/run-daily-events-scrape.sh`  
  Runs the scraper with `--output-dir sailingsa/deploy`, `--date-stamp`, and `--no-detail` (list-only for speed). If `DATABASE_URL` or `DB_URL` is set, then runs `load_events_csv_to_db.py` to upsert into `events`. Log: `sailingsa/deploy/logs/daily-events-scrape.log`.

- **Cron (daily, e.g. 04:00 UTC):**
  ```bash
  0 4 * * * /path/to/Project\ 6/sailingsa/deploy/run-daily-events-scrape.sh >> /path/to/sailingsa/deploy/logs/daily-events-scrape.log 2>&1
  ```
  On the **server** (set `DB_URL`, then):
  ```bash
  0 4 * * * /var/www/sailingsa/deploy/run-daily-events-scrape.sh --on-server >> /var/www/sailingsa/deploy/logs/daily-events-scrape.log 2>&1
  ```

- **Output**: `sas_events_list.csv` (latest) and `sas_events_list_YYYYMMDD.csv` per run; DB `events` table updated when loader runs.

---

## File reference

| Item | Purpose |
|------|--------|
| [sailing.org.za/events/](https://www.sailing.org.za/events/) | Main list (upcoming + past links) |
| [Revolutionise example](https://www.revolutionise.com.au/29erclass/events/334371) | External event; ID in path `334371` |
| `scrape_sas_events.py` | Existing scraper (SAS numeric IDs only) |
| `scrape_sas_events_list.py` | List + external URLs + event IDs; pagination |
| `load_events_csv_to_db.py` | Upsert CSV into `events` table |
| `database/migrations/145_events_table.sql` | Events table |
| `database/migrations/146_events_list_scrape_columns.sql` | Extra columns for list scrape |
| `/admin/events-audit` | Temp audit page (live) |
| `/admin/api/events` | API for audit page |
| `regattas` | Our results events; link via `events.regatta_id` |
| Club pages | Show events where venue/club matches |
