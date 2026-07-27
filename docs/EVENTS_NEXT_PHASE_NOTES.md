# EVENTS – Next Phase Notes (DO NOT IMPLEMENT YET)

Prepared notes for future implementation. Do not execute until master plan approved.

---

## 1. Event ↔ Regatta Matching Job

### Inputs
- `events` table: `source='sas'`, `event_status='completed'`, `regatta_id IS NULL`
- `regattas` table: `event_name`, `start_date`, `end_date`, `host_club_id`

### Matching logic (priority order)
1. **Date window**: `events.start_date` / `end_date` within ±3 days of `regattas.start_date` / `end_date`
2. **Normalized name**: Tokenize both, remove year, compare overlap (e.g. 70%+ token match)
3. **Host club**: Map `events.host_club_name_raw` → `clubs` → `regattas.host_club_id`

### Output
- `UPDATE events SET regatta_id = ?, match_score = ?, match_method = ? WHERE event_id = ?`
- Log matches and mismatches for manual review
- Consider: `event_regatta_matches` audit table for proposed matches (manual confirm)

### Edge cases
- Multiple regattas in same date range → pick best name match, flag for review
- Series regattas (372, 373, 374) → exclude from match
- SAS event with no regatta → leave `regatta_id` NULL

---

## 2. Recurring Event Detection

### Query
```sql
SELECT
  REGEXP_REPLACE(LOWER(event_name), '\d{4}', 'YYYY') AS event_pattern,
  COUNT(DISTINCT event_year) AS years_seen,
  array_agg(DISTINCT event_year ORDER BY event_year) AS years
FROM events
WHERE source = 'sas' AND event_year IS NOT NULL
GROUP BY event_pattern
HAVING COUNT(DISTINCT event_year) >= 2
ORDER BY years_seen DESC;
```

### Use
- Build `expected_events` list per season
- Flag: SAS has event X 2026, we have no matching regatta yet → "Results pending"
- Cross-check with `regattas` for same pattern across years

### Output table (optional)
- `recurring_event_patterns`: `(pattern, years_seen, years[], sample_event_name)`

---

## 3. Calendar API

### Endpoints (draft)
- `GET /api/events?status=upcoming|completed&year=2026&limit=50`
- `GET /api/events/{event_id}` – single event with optional `regatta_id` link
- `GET /api/events/{event_id}/results` – redirect to regatta viewer if `regatta_id` set

### Response shape
```json
{
  "event_id": 1,
  "source": "sas",
  "source_event_id": "293435",
  "event_name": "Hobie 14 WC Champs",
  "start_date": "2026-02-21",
  "end_date": "2026-02-22",
  "venue_raw": "Langebaan",
  "event_status": "upcoming",
  "regatta_id": null,
  "nor_url": "https://...",
  "si_url": "https://..."
}
```

### Filtering
- `event_status`: upcoming, completed, live, cancelled
- `event_year`: filter by year
- `host_club_name_raw` or `host_club_id`: filter by venue

---

## 4. Indexes (when allowed)

- `events(source, source_event_id)` – already UNIQUE
- `events(event_status, start_date)` – for calendar listing
- `events(regatta_id)` – for reverse lookup
- `events(event_year)` – for year filter
- `events(host_club_id)` – for venue filter
