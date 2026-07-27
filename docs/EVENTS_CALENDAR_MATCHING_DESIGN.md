# Events Calendar – Comparison Table & Matching Design

## Overview

Build a comparison/matching layer to:
1. **Match past SAS events → regatta results** so when a past event is selected, we show full results
2. **Derive recurring events** from the results audit so we know what events to expect each season

---

## 1. Data Sources Comparison

| Field | SAS Event Page (scrape) | Regattas Table (DB) | Notes |
|-------|-------------------------|---------------------|-------|
| **Identifier** | SAS Event ID (e.g. 293435) | `regatta_id` (e.g. `359-2025-zvyc-southern-charter-cape-classic`) | Different formats – need mapping |
| **Event name** | "Hobie 14 WC Champs", "2026 Hobie Tiger Nationals" | `event_name` (e.g. "ZVYC Southern Charter Cape Classic") | Names often differ; need fuzzy/normalized matching |
| **Dates** | Start/end (e.g. Sat 21 Feb 2026 09:00) | `start_date`, `end_date` (DATE) | Primary match key with name |
| **Location** | "Langebaan", "Royal Cape Yacht Club, Duncan Road..." | `host_club_id` → clubs table | Club name can help match |
| **NOR URL** | Sometimes (e.g. "2026 Hobie Tiger Nationals NOR" → cdn.revolutionise.com.au/events/xxx.pdf) | Not stored | Scrape from SAS when present |
| **SI URL** | Sometimes (Sailing Instructions) | Not stored | Scrape from SAS when present |
| **Results** | Not on SAS event page | `results` table via `regatta_id` | Full results only in our DB |
| **Contact** | Not typically on event page | Not stored | Limited availability |

---

## 2. Matching Logic: SAS Event → Regatta

### Primary match keys (in order of reliability)

| Priority | Match field | Logic |
|----------|-------------|-------|
| 1 | **Date window** | SAS `start_date` / `end_date` within ±2 days of `regattas.start_date` / `regattas.end_date` |
| 2 | **Event name (normalized)** | Tokenize, remove year, punctuation; compare against `event_name` |
| 3 | **Location / club** | Map SAS location text → `clubs.club_abbrev` or `clubs.club_name` |
| 4 | **Class / event type** | "420 Nationals", "Hobie 14" etc. from SAS title → compare with `regatta_blocks.class_canonical` |

### Normalization for name matching

```
SAS: "2026 Hobie Tiger Nationals"     → "hobie tiger nationals"
SAS: "Hobie 14 WC Champs"             → "hobie 14 wc champs"
Regatta: "2025 Hobie Tiger Nationals" → "hobie tiger nationals"
Regatta: "Hobie 16 Nationals"         → "hobie nationals"
```

Rules:
- Lowercase, strip punctuation
- Remove leading year (2025, 2026)
- Optional: stem words (nationals, championship, champs → same root)
- Token overlap threshold (e.g. 70%+ tokens match)

### Suggested mapping table

| Table | Purpose |
|-------|---------|
| `sas_event_regatta_map` | Maps SAS event_id → regatta_id when match is confirmed |
| Columns | `sas_event_id`, `regatta_id`, `match_score`, `match_method`, `confirmed_at` |

---

## 3. Past Event Selected → Full Results Flow

```
User selects past SAS event (e.g. "Gimco Regatta 30 Jan 2026")
    ↓
Lookup sas_event_regatta_map(sas_event_id) → regatta_id
    ↓
If match: fetch /api/regatta/{regatta_id} → full results
If no match: show SAS event info only; "Results not yet in our database"
```

API shape:
- `GET /api/events/{sas_event_id}/results` → returns regatta results if mapped, else 404
- Or: include `regatta_id` in event payload when known

---

## 4. Recurring Events from Audit

### Source

From `regattas` + `results` over multiple years:
- `event_name`, `start_date`, `end_date`
- Group by normalized event pattern (year removed)

### Derivation logic

```sql
-- Pseudocode: events that appear in 2+ years
SELECT 
  REGEXP_REPLACE(LOWER(event_name), '\d{4}', 'YYYY') as event_pattern,
  COUNT(DISTINCT EXTRACT(YEAR FROM start_date)) as years_seen,
  array_agg(DISTINCT EXTRACT(YEAR FROM start_date)::int ORDER BY 1) as years
FROM regattas
WHERE start_date IS NOT NULL
GROUP BY event_pattern
HAVING COUNT(DISTINCT EXTRACT(YEAR FROM start_date)) >= 2
```

### Example recurring patterns

| Pattern | Years seen | Interpretation |
|---------|------------|----------------|
| `yv nationals` | 2023, 2024, 2025 | Annual Youth Nationals |
| `cape classic` | 2024, 2025 | Annual Cape Classic |
| `hobie tiger nationals` | 2024, 2025, 2026 | Annual Hobie Tiger Nationals |
| `zv sc southern charter cape classic` | 2024, 2025 | Annual ZVYC event |

### Use

- **Expected events list**: "Events we typically have results for each season"
- **Missing results alert**: If SAS has "Hobie Tiger Nationals 2026" but we have no matching regatta yet → flag for results import
- **Auto-suggest match**: When new regatta is imported, suggest SAS events to link based on date + pattern

---

## 5. Implementation Phases

| Phase | Task | Output |
|-------|------|--------|
| 1 | Scrape SAS events with full fields (title, dates, location, NOR/SI URLs) | Enhanced `scrape_sas_events.py` |
| 2 | Add `sas_event_regatta_map` table + API | Mapping storage + lookup |
| 3 | Build matching job: date + normalized name + optional club | Populate map for past events |
| 4 | Recurring-events query from audit | `expected_events` list per season |
| 5 | Events UI: past event → "View full results" when mapped | Link to regatta viewer |

---

## 6. Edge Cases

| Scenario | Handling |
|----------|----------|
| Same event name, different years | Match by year + name (e.g. "2025 Youth Nationals" vs "2026 Youth Nationals") |
| SAS has event, we have no regatta | Show SAS info; no results link |
| We have regatta, SAS has no event | Not applicable (we don't create SAS events) |
| Multiple regattas in same date range | Prefer best name match; allow manual override in admin |
| Series vs single regatta | Exclude series (372, 373, 374) from match |
