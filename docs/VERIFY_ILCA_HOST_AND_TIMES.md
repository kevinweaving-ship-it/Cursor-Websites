# ILCA Nationals 2026 — host and time verification

Run these on **live DB** (local has no `events` table).

## 1. Host data for ILCA Nationals 2026

```sql
SELECT event_name, host_club_name_raw, venue_raw, host_club_id
FROM events
WHERE event_name ILIKE '%ILCA Nationals 2026%';
```

Interpretation:
- If `host_club_name_raw` contains `·` or `•` or `|`, parsing uses the part **after** the separator for club resolution (e.g. "LASA (…) · Club Mykonos" → "Club Mykonos").
- `host_club_id` should be set if "Club Mykonos" (or whatever is after the separator) matches a row in `clubs`.

## 2. Club match for Mykonos

```sql
SELECT club_id, club_abbrev, club_fullname
FROM clubs
WHERE club_fullname ILIKE '%Mykonos%';
```

If this returns a row, bulk host resolution can match "Club Mykonos" to that club and set `host_club_id` / show "Host: {abbrev} ({fullname})" on the event card.

## 3. Event time fields for ILCA Nationals

```sql
SELECT event_name, start_date, start_time, end_date, end_time
FROM events
WHERE event_name ILIKE '%ILCA Nationals%';
```

- If `start_time` and `end_time` are **NULL**: scraper is not saving times (or columns don’t exist yet).
- If they have values: ensure the API SELECT includes them (see below).

## 4. API SELECT in `_get_upcoming_events()` — time columns

**Current behaviour:** The events SELECT in `api.py` (`_get_upcoming_events()` and the past-events query) does **not** include `e.start_time` or `e.end_time`. Columns selected are:

- `e.event_id`, `e.event_name`, `e.start_date`, `e.end_date`, `e.source_url`
- `e.venue_raw`, `e.host_club_name_raw`, `e.location_raw`, `e.category`
- `{reg_col}`, `{club_cols}`, `{map_col}`, `{img_col}`, `{addr_col}`

So even if the scraper (or a manual UPDATE) sets `start_time`/`end_time`, the API does not return them. To support times on the events page, add `e.start_time` and `e.end_time` to both SELECTs and to `_event_row_to_card()` / date_display logic.

## 5. Check if any events have times populated

```sql
SELECT COUNT(*) AS events_with_times
FROM events
WHERE start_time IS NOT NULL
OR end_time IS NOT NULL;
```

```sql
SELECT event_name, start_date, start_time, end_date, end_time
FROM events
ORDER BY start_date
LIMIT 50;
```

## Run on live

From your machine (with DB URL from server env):

```bash
# Get DB_URL from server (e.g. from systemd service)
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "grep -o 'DB_URL=[^ ]*' /etc/systemd/system/sailingsa-api.service | cut -d= -f2- | tr -d '\"'"

# Then run the script (set DB_URL to the value above)
DB_URL='postgresql://...' python3 scripts/verify_ilca_host_and_times.py
```

Or run the SQL above in `psql` on the server after connecting to the live DB.
