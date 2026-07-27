# Events Next Steps

## Summary

- **Total events:** *—*
- **Total unresolved hosts (rows):** *—*
- **Distinct unresolved host names:** *—*
- **Event types (categories):** *—*
- **Recurring event names (series candidates):** *—*
- **Past events without results (sample 100):** *—*

*(Run `python3 scripts/events_data_audit_run.py` with DB_URL set to populate from live DB.)*

## Event type list

*(Populated by audit script.)*

## Top recurring events

*(Populated by audit script.)*

## Past events missing results

See **EVENTS_DATA_AUDIT.md** §5. These represent missing results imports.

## Recommended next steps

1. **Host resolution:** Apply proposed mapping from **EVENTS_HOST_MATCH_PLAN.md** (after review); bulk `UPDATE events SET host_club_id = ? WHERE host_club_name_raw = ?`.
2. **Event type pages:** Implement `/events/type/{slug}` using **EVENTS_TYPE_URLS.md**.
3. **Series pages:** Implement `/events/series/{slug}` using **EVENT_SERIES_CANDIDATES.md**.
4. **Missing results:** Prioritise importing results for past events with `regatta_id` but no rows in `results`.
5. **Likely classes:** Keep current engine; validation in **EVENT_LIKELY_CLASSES_VALIDATION.md**.
