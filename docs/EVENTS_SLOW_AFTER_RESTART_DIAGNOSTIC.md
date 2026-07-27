# Events page — slow after restart diagnostic

## STEP 1 — DB connection handling

**Finding:** In `_get_upcoming_events()` the connection was returned in the `except` block, but the **cursor was never closed** on exception. When an exception occurred after `cur = conn.cursor()`, the connection was returned to the pool with an open cursor, which can cause connection-pool issues and slowdowns over time.

**Fix applied:** A `finally` block was added so that:
- `cur` is always closed (if it was created).
- `conn` is always returned via `return_db_connection(conn)` (if it was obtained).

`cur` and `conn` are initialized to `None` at the start; the `finally` runs on both success and exception paths. This prevents connection and cursor leaks.

---

## STEP 2 — Global variables

**Finding:** All of these are **local** to the function, created inside `_get_upcoming_events()` (or `_get_events_by_type_slug()`):

- `regattas_with_results = set()` — local
- `likely_by_event_name = {}` — local
- `club_by_name = {}` — local
- `host_displays_to_resolve` — local

None are module-level or appended to on every request. **No global list or cache is growing per request.**

---

## STEP 3 — Results / likely-classes queries

**Queries that run every request (no LIMIT):**

1. `SELECT DISTINCT regatta_id FROM results WHERE regatta_id IN (...)` — bounded by number of past event regatta_ids.
2. `SELECT regatta_id, event_name FROM regattas WHERE regatta_id IN (SELECT DISTINCT regatta_id FROM results)` — scans all regattas that have results (no LIMIT).
3. `SELECT regatta_id, class_canonical, COUNT(*) ... FROM results ... GROUP BY regatta_id, class_canonical` — full scan of `results` for class counts.

**Change made:** A temporary timer was added around the two likely-classes queries (regattas + results class counts). Log line:

- `EVENTS: likely_classes queries X.XXX`

So you can see their combined runtime in the logs. If this value grows over time, the slowdown is not from these queries alone but from something else (e.g. connection pool exhaustion before the fix).

---

## STEP 4 — Row count debug

**Added in `_get_upcoming_events()`:**

```text
print("EVENTS: rows upcoming:", len(out["upcoming"]), "past:", len(out["past"]))
```

This runs just before `EVENTS: total`. If upcoming/past counts stay stable (e.g. ~46 upcoming, ~895 past) across requests, response data is not growing. If they grow, something is wrong elsewhere (e.g. shared mutable state).

---

## STEP 5 — Active DB connections (run on server)

To check for connection leaks, run on the **live server** (e.g. after a few /events loads):

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname='sailors_master';
```

- Run it once, then hit `/events` several times, then run it again.
- If the count **keeps increasing** and never drops, connections are leaking (the `finally` fix should prevent that for `_get_upcoming_events()`).
- If the count stays stable or returns to a baseline, connections are not leaking from this path.

---

## STEP 6 — Report summary

| Check | Result |
|-------|--------|
| **Connections leaking?** | **Fixed.** Previously the cursor was not closed on exception, so the connection could be returned to the pool with an open cursor. A `finally` block now always closes `cur` and returns `conn`. |
| **Global lists growing per request?** | **No.** `regattas_with_results`, `likely_by_event_name`, `club_by_name`, `host_displays_to_resolve` are all created inside the function each request. |
| **Results / likely-classes query runtime** | Logged as `EVENTS: likely_classes queries X.XXX`. Run `journalctl -u sailingsa-api -f`, load `/events` a few times, and compare this value on first request vs after several requests. |

**Next steps:** Deploy the updated `api.py`, restart the API, then (1) run the `pg_stat_activity` query before/after multiple `/events` loads, and (2) capture the EVENTS log lines (including `rows upcoming`/`past` and `likely_classes queries`) to confirm where time is spent and that row counts and connection count are stable.
