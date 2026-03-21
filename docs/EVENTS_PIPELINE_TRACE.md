# Events pipeline trace: scrape → DB → /events API/page

Read-only trace of where events are inserted and why `start_time`/`end_time` are not populated and where association text gets into host fields.

---

## 1. Pipeline overview

```
Source (sailing.org.za/events/, list + optional detail)
    ↓
scrape_sas_events_list.py  (list + detail parser)
    ↓
sas_events_list.csv  (fieldnames: title, details_url, start_date, end_date, start_time, end_time, venue_text, host, location, ...)
    ↓
load_events_csv_to_db.py  (CSV → INSERT/ON CONFLICT into events)
    ↓
events table  (start_date, end_date, start_time, end_time, venue_raw, host_club_name_raw, host_club_id)
    ↓
api.py: _get_upcoming_events() / _get_events_by_type_slug()  (SELECT + bulk host resolution)
    ↓
_event_row_to_card()  (card dict: date_display, host_club, host_code, ...)
    ↓
_events_page_html() / _events_type_page_html()  (HTML with embedded JSON)
    ↓
GET /events  or  GET /events/type/{slug}
```

---

## 2. Where events are inserted into the database

**Single write path:** `load_events_csv_to_db.py`.

- **Code path:** `main()` → open CSV → build `rows` (one dict per event) → `conn.cursor()` → for each row `cur.execute("""INSERT INTO events (...) VALUES (...) ON CONFLICT (source, source_event_id) DO UPDATE SET ...""")` → `conn.commit()`.
- **Location:** `load_events_csv_to_db.py` lines 241–291 (INSERT with ON CONFLICT DO UPDATE).
- **Trigger:** Run manually or by `run-daily-events-scrape.sh` after the scraper writes `sas_events_list.csv`. The scraper that produces that CSV is **`scrape_sas_events_list.py`** (list + optional detail fetch).

There is no other INSERT/upsert into `events` in the codebase (aside from `scrape_sas_events_historical.py`, which is a separate historical scrape and also writes to `events`).

---

## 3. Exact scraper/parser and flow

| Step | Component | File | What it does |
|------|------------|------|---------------|
| 1 | List fetch | `scrape_sas_events_list.py` | `fetch_list_page(path)` → GET sailing.org.za `/events/`, `/events/list`, `/events/list/past` (with pagination). |
| 2 | List parse | same | `parse_list_html(html, is_past)` → `EVENT_LINK_RE` / `EVENT_LINK_REL_RE` for links, `parse_start_end(block)` for dates, line-scan for **venue_text**. Outputs **start_date**, **end_date** only (no times); **start_time**, **end_time** left `""`. **host**, **location** left `""`. |
| 3 | Detail fetch | same | If run **without** `--no-detail`: for each event `fetch_detail_page(ev["details_url"])` → GET source_url (SAS or external, e.g. revolutionise, laser.org.za). |
| 4 | Detail parse | same | `parse_detail_html(html, base_url)` → Location/Venue/Host labels, DATE_RE for dates+times, category, NOR/SI, etc. Sets **start_date**, **end_date**, **start_time**, **end_time**, **host**, **location**. |
| 5 | Merge | same | `for k, v in detail.items(): if v: ev[k] = v` then `ev["venue_text"] = loc or ev.get("venue_text") or ""`. Detail overrides list. |
| 6 | CSV write | same | `csv.DictWriter(f, fieldnames=fieldnames)` → `sas_events_list.csv` (includes start_time, end_time, host, location, venue_text). |
| 7 | Load | `load_events_csv_to_db.py` | Reads CSV; `venue_val = row.get("location") or row.get("venue_text")`; `host_val = row.get("host") or venue_val`; `start_time_val` / `end_time_val` from row; **club_id** from `resolve_host_to_club_id(cur, parse_host_after_separator(host_val))`; INSERT/ON CONFLICT into **events** with start_date, end_date, **start_time**, **end_time**, venue_raw, host_club_name_raw, host_club_id. |

---

## 4. Code paths that populate each field

| Field | Populated by | Code path |
|-------|--------------|-----------|
| **start_date** | Scraper list or detail | List: `parse_start_end(block)` → `to_iso(m)` (date only) in `parse_list_html`. Detail: `parse_detail_html` DATE_RE → `to_iso(date_matches[0])`. Loader: `parse_date(row["start_date"])` → `r["start_date"]` in INSERT. |
| **end_date** | Same | List: second match of `parse_start_end` or same as start. Detail: `to_iso(date_matches[1])` or same as start. Loader: `parse_date(row["end_date"])` → `r["end_date"]`. |
| **start_time** | Scraper **detail only** | Detail: `parse_detail_html` → `to_time(date_matches[0])` (from DATE_RE group 4). List never sets it (stays `""`). Loader: `row.get("start_time")` → `r["start_time"]` in INSERT. |
| **end_time** | Scraper **detail only** | Detail: `to_time(date_matches[1])` or `out["start_time"]`. List never sets it. Loader: `row.get("end_time")` → `r["end_time"]`. |
| **venue_raw** | Scraper list or detail | Loader: `venue_val = (row.get("location") or row.get("venue_text") or "").strip()` → `r["venue_raw"]`. Detail sets `location`/`host`; merge sets `venue_text = loc or venue_text`. So venue_raw = detail location/host or list venue_text. |
| **host_club_name_raw** | Scraper list or detail | Loader: `host_val = (row.get("host") or "").strip() or venue_val` → `r["host_club_name_raw"]`. No splitting on ·/•/| before **storing**; full string is written to DB. |
| **host_club_id** | Loader only | `host_for_resolution = parse_host_after_separator(host_val)` then `resolve_host_to_club_id(cur, host_for_resolution)`. So only the part after ·/•/| is used for **resolution**; the raw stored value is unchanged. |

---

## 5. Why start_time / end_time are not being populated

1. **Daily scrape runs with `--no-detail`**  
   - **`sailingsa/deploy/run-daily-events-scrape.sh`** line 96:  
     `$PYTHON "$SCRAPER" --output-dir "$OUTPUT_DIR" --date-stamp --no-detail`  
   - With `--no-detail`, the script **never** calls `fetch_detail_page` or `parse_detail_html`.  
   - So **start_time** and **end_time** are never set in the event dict; they stay `""` and are written to CSV as empty.  
   - Loader then sets `start_time_val = (row.get("start_time") or "").strip() or None` → **None**, and that is what gets INSERTed/UPDATEd.

2. **List parser does not extract time**  
   - `parse_list_html` uses `parse_start_end(block)`, which uses DATE_RE but only returns **date** strings via `to_iso(m)` (year-month-day). It **discards** the time group (fourth group of DATE_RE).  
   - List-built events have `"start_time": "", "end_time": ""` in the CSV. So even when the list HTML contains "Thu 30 Apr 2026 18:00", the list path never populates start_time/end_time.

3. **Only detail path sets times**  
   - Times are set only in `parse_detail_html` when DATE_RE matches (e.g. "Thu 30 Apr 2026 18:00") and `to_time(m)` returns the time string.  
   - So for **start_time/end_time to be populated**, the scraper must run **without** `--no-detail` and the **detail page** HTML must contain that DATE_RE pattern. If the daily job always uses `--no-detail`, no event will ever get times from the current pipeline.

---

## 6. Where association text is written into host fields

1. **Detail page stores the full label value**  
   - In `parse_detail_html`, for labels "Location", "Venue", "Host" the code takes the first text part (3–120 chars) after the label and sets `out["location"] = part` and `out["host"] = part` (or comma-split).  
   - It does **not** split on · or • or |. So if the page shows e.g. **"LASA (Laser Association of South Africa) · Club Mykonos"** in that field, the **entire string** is stored in `host` (and `location`).  
   - That flows to CSV columns `host` and `location`, then into the loader.

2. **Loader stores raw host in the DB**  
   - Loader sets `host_val = (row.get("host") or "").strip() or venue_val` and then `r["host_club_name_raw"] = host_val`.  
   - So **host_club_name_raw** is the **full** scraped string (e.g. "LASA (Laser Association of South Africa) · Club Mykonos").  
   - `parse_host_after_separator` is used **only** for resolving **host_club_id**; it does **not** change what is written to **host_club_name_raw**. So association text is written into **host_club_name_raw** because the scraper and loader store the detail (or list) value verbatim.

3. **List page can contribute the same pattern**  
   - In `parse_list_html`, **venue_text** is the first non-date, non-category line in the block (5–120 chars).  
   - If the list HTML shows "LASA (...) · Club Mykonos" on that line, **venue_text** becomes that full string.  
   - When detail is skipped (`--no-detail`), `host` and `location` stay empty, so the loader uses `host_val = venue_val` (from venue_text). So **host_club_name_raw** and **venue_raw** can both get the association·club line from the **list** page.

4. **Summary**  
   - **Association text is written into host (and venue) fields** because:  
     - The **scraper** (list and/or detail) stores the **full** text of the Location/Venue/Host or list venue line, with **no** splitting on · • | before writing to CSV.  
     - The **loader** stores that same value in **venue_raw** and **host_club_name_raw**; it only uses the part after the separator for **club resolution** (host_club_id), not for what is persisted in host_club_name_raw.

---

## 7. API → page path (read path, no writes)

| Step | Code |
|------|------|
| Request | `GET /events` → `events_page()` → `_events_page_html()`. |
| Data | `_events_page_html()` calls `data = _get_upcoming_events()`. |
| Query | `_get_upcoming_events()` SELECTs from **events** (with `time_cols` = `e.start_time`, `e.end_time` when columns exist), bulk-resolves host via `_host_display_from_row(r)` and clubs table, then builds cards with `_event_row_to_card()`. |
| Card | `_event_row_to_card(r, ...)` uses `_host_display_from_row(r)` and `_format_event_date_range(start, end, start_time=start_t, end_time=end_t)` → **date_display**; returns dict with **start_time**, **end_time**, **host_club**, **host_code**, etc. |
| HTML | `_events_page_html()` embeds `events_json = json.dumps({"upcoming": upcoming, "past": past})` in `<script type="application/json" id="events-data">`, and the page script uses `DATA = JSON.parse(...)` and `renderCard(e, ...)` to show **e.date_display**, **e.host_code** / **e.host_club** / **e.host_club_fullname**. |

So the **only** place events are **inserted/updated** is `load_events_csv_to_db.py`; the scraper that feeds it is `scrape_sas_events_list.py`; and the **/events** API/page only **read** from the DB and format for display.
