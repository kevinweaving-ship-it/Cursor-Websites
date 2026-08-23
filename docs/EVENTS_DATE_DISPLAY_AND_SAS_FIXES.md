# Events date display + SAS scrape date fixes

## Date display (cards)

Target format in `_format_event_date_range` (`api.py`):

- With times: `18:00 Thu 27 – 18:00 Sat 29 Aug 2026`
- Without times: `Thu 27 – Sat 29 Aug 2026`
- Same day: `18:00 Thu 27 Aug 2026` or `Thu 27 Aug 2026`

## Known bad rows (live)

| Event | SAS list | Correct | Cause |
|-------|----------|---------|-------|
| VULCAN CHallenge (`370405`) | `Sat 12 Sep 2026 09:00 - 09:00` | end = **2026-09-12** (same day) | Parser used next card’s dates (DF95 Fri 18 Sep) from oversized HTML block — **fixed** (same-line gap only) |
| DSO Appointments (`361162`) | SAS literally shows **2029** | end = **2026-05-31** | SAS typo; we override |

## Immediate live SQL (Mac SSH when free)

```sql
UPDATE events
SET end_date = start_date, last_seen_at = now()
WHERE source = 'sas' AND source_event_id = '370405'
  AND end_date IS DISTINCT FROM start_date;

UPDATE events
SET end_date = DATE '2026-05-31', last_seen_at = now()
WHERE source = 'sas' AND source_event_id = '361162'
  AND end_date IS DISTINCT FROM DATE '2026-05-31';
```

Then restart API or wait for next `/events` rebuild.

## Scrape + load

```bash
# From project root (Cloud can scrape; load needs live DB/SSH)
python3 scrape_sas_events_list.py --output-dir sailingsa/deploy --date-stamp --no-detail
# Prefer with detail when times needed (slower):
# python3 scrape_sas_events_list.py --output-dir sailingsa/deploy --date-stamp

export DB_URL='postgresql://...'   # on server
python3 load_events_csv_to_db.py --csv sailingsa/deploy/sas_events_list.csv
```

Or on server: `bash /var/www/sailingsa/deploy/run-daily-events-scrape.sh --on-server` after deploying updated scraper/loader.
