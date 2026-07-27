# SAS ID Scrape — Corrected Architecture

This document defines the corrected architecture for SAS ID scraping. It extends (does not replace) the existing SAS scrape readmes.

---

## 1. Two concepts

| Concept | Definition |
|--------|------------|
| **DOCUMENTED_SAS_MAX_ID** | Manual snapshot from the [SA Sailing Member Finder](https://www.sailing.org.za/member-finder?parentBodyID=28406&firstname=&surname=). Human reference only. **28406** is a snapshot as of Feb 2026. It must **not** be treated as a permanent ceiling; re-verify periodically on the site. |
| **DETECTED_SAS_MAX_ID** | Auto-probed by the system. The incremental scraper probes forward until N consecutive NOT_FOUND, then records the upper bound in `sas_scrape_batches.detected_upper_bound`. This is the operational upper bound; the documented max is secondary. |

---

## 2. Snapshot clarification (28406)

- **28406** is a **manual snapshot as of Feb 2026**, not a permanent ceiling.
- Do not hard-code it as the only stop condition; the system must support **DETECTED_SAS_MAX_ID** from incremental scrape runs.
- Manual check on member-finder becomes **secondary**, not primary, for automation.

---

## 3. Registry expansion rules

- **`sas_id_registry` is infrastructure only.** Expansion writes **only** to `sas_id_registry`.
- **No automatic merge** into any sailors/personal table.
- **No automatic identity resolution.**
- **No automatic qualification scrape.**

One pipeline only: expand the registry. Identity merge, profile creation, and results are separate.

---

## 4. Incremental Scrape Strategy

The system must:

1. **Start** at `MAX(sas_id) + 1` (from `sas_id_registry`).
2. **Probe forward** sequentially (current_id = last_id + 1, then current_id + 1, …).
3. **Stop** after **N consecutive NOT_FOUND** (suggest **N = 20**).
4. **Record** `detected_upper_bound` (last valid ID before the run of NOT_FOUND).
5. **Log** the scrape batch in `sas_scrape_batches` (see Batch Logging Requirement).

High-level algorithm:

- `last_id = SELECT MAX(sas_id) FROM sas_id_registry`
- `current_id = last_id + 1`
- `consecutive_not_found = 0`
- **While** `consecutive_not_found < N`:
  - Fetch SAS page for `current_id`
  - **If VALID:** insert into `sas_id_registry`, `consecutive_not_found = 0`
  - **If NOT_FOUND:** insert with status NOT_FOUND, `consecutive_not_found += 1`
  - **If ERROR:** insert with status ERROR, count error
  - `current_id += 1`
- **Stop.** Set `detected_upper_bound = current_id - consecutive_not_found - 1` (last valid ID).

---

## 5. Rule: no direct write to race_results

- **Never write scraped results directly into `race_results`** (or any results table).
- All future pipelines must use **staging tables**. Scraping populates registry/staging only; identity and results flow are separate.

---

## 6. Batch Logging Requirement

Every scrape run must record:

| Field | Description |
|-------|-------------|
| `batch_id` | Unique batch identifier (e.g. `SAS_INCREMENTAL_{start_id}`) |
| `start_id` | First ID probed in this run |
| `end_id` | Last ID probed in this run |
| `detected_upper_bound` | Last valid SAS ID detected (before N consecutive NOT_FOUND) |
| `valid_count` | Number of VALID inserts |
| `not_found_count` | Number of NOT_FOUND |
| `error_count` | Number of ERROR |
| `started_at` | When the batch started |
| `completed_at` | When the batch completed |

Table: `sas_scrape_batches` (see migration `database/migrations/150_sas_scrape_batches.sql`).

---

## 7. What the incremental scraper does NOT do

- No qualification scrape  
- No identity merge  
- No profile creation  
- No event scrape  
- No results scrape  

Registry expansion only.

---

## 8. Reference: incremental registry scraper (Python)

Registry-only expansion; no identity merge, no sailors table, no race_results. Logs to `sas_scrape_batches`.

```python
def incremental_sas_registry_scrape(fetch_sas_profile, db):
    """
    Expands sas_id_registry forward until N consecutive NOT_FOUND.
    Does NOT merge identity.
    Does NOT touch sailors table.
    Does NOT touch race_results.
    """
    N_CONSECUTIVE_STOP = 20

    last_id = db.fetch_one(
        "SELECT COALESCE(MAX(sas_id), 0) FROM sas_id_registry"
    )[0]

    current_id = last_id + 1
    consecutive_not_found = 0

    batch_id = f"SAS_INCREMENTAL_{current_id}"

    batch_row = db.execute_returning("""
        INSERT INTO sas_scrape_batches (batch_id, start_id)
        VALUES (%s, %s)
        RETURNING id
    """, (batch_id, current_id))

    valid_count = 0
    not_found_count = 0
    error_count = 0

    while consecutive_not_found < N_CONSECUTIVE_STOP:
        try:
            result = fetch_sas_profile(current_id)

            if result["status"] == "VALID":
                db.execute("""
                    INSERT INTO sas_id_registry (sas_id, full_name, status, scraped_at)
                    VALUES (%s, %s, 'VALID', NOW())
                    ON CONFLICT (sas_id) DO NOTHING
                """, (current_id, result["full_name"]))
                valid_count += 1
                consecutive_not_found = 0

            elif result["status"] == "NOT_FOUND":
                db.execute("""
                    INSERT INTO sas_id_registry (sas_id, status, scraped_at)
                    VALUES (%s, 'NOT_FOUND', NOW())
                    ON CONFLICT (sas_id) DO NOTHING
                """, (current_id,))
                not_found_count += 1
                consecutive_not_found += 1

            else:
                db.execute("""
                    INSERT INTO sas_id_registry (sas_id, status, scraped_at)
                    VALUES (%s, 'ERROR', NOW())
                    ON CONFLICT (sas_id) DO NOTHING
                """, (current_id,))
                error_count += 1

        except Exception:
            error_count += 1

        current_id += 1

    detected_upper_bound = current_id - consecutive_not_found - 1

    db.execute("""
        UPDATE sas_scrape_batches
        SET end_id = %s,
            detected_upper_bound = %s,
            valid_count = %s,
            not_found_count = %s,
            error_count = %s,
            completed_at = NOW()
        WHERE id = %s
    """, (
        current_id - 1,
        detected_upper_bound,
        valid_count,
        not_found_count,
        error_count,
        batch_row[0]
    ))
```

**Note:** Assumes `sas_id_registry` exists with columns `sas_id`, `full_name`, `status`, `scraped_at` and unique constraint on `sas_id`. Create that table if your schema uses a different name (e.g. staging table).

---

## 9. Registry integrity (required for ON CONFLICT)

- **`sas_id_registry.sas_id`** must be **PRIMARY KEY** or at least **UNIQUE**. Without that, `ON CONFLICT (sas_id) DO NOTHING` is meaningless.
- **Pre-flight:** After applying migrations, run:
  ```bash
  psql "$DB_URL" -c "\d sas_id_registry"
  ```
  You must see a primary key or unique index on `sas_id`. If not, fix before automation goes live (migration `151_sas_id_registry.sql` creates the table with `sas_id INTEGER PRIMARY KEY`).

## 10. Status enum (controlled values only)

- The registry allows **only** these status values: **VALID**, **NOT_FOUND**, **ERROR**, **EMPTY** (optional).
- Implemented via `CHECK (status IN ('VALID', 'NOT_FOUND', 'ERROR', 'EMPTY'))` so weekly automation cannot introduce rogue values.
- If your existing table has free-text status, add the CHECK constraint and backfill invalid values before enabling automation.

## 11. First run strategy (do not hardcode range)

- Even if you are behind (e.g. 28218 → 28406), **do NOT hardcode** the range 28218–28406.
- Let the incremental scraper: **start at `MAX(sas_id)+1`**, run until **20 consecutive NOT_FOUND**. It will naturally stop around 28406 and validate the architecture.
- Then check logs and `DETECTED_SAS_MAX_ID` in `sas_scrape_batches`. Only after one full run and log check consider the next layer (no qualification scrape, no identity merge, no events/results reconcile until registry is stable).

## 12. Deployment order (recommended)

1. Fix readmes (DOCUMENTED_SAS_MAX_ID / DETECTED_SAS_MAX_ID, registry rules, incremental strategy, batch logging).
2. Create `sas_scrape_batches` (migration `150_sas_scrape_batches.sql`) and **`sas_id_registry`** (migration `151_sas_id_registry.sql`).
3. **Verify integrity:** `\d sas_id_registry` — must show PRIMARY KEY or UNIQUE on `sas_id`; status CHECK in place.
4. Implement incremental scraper (writes only to `sas_id_registry`, logs to `sas_scrape_batches`).
5. Run once in staging (incremental from `MAX(sas_id)+1`, no hardcoded range).
6. Verify batch logs and DETECTED_SAS_MAX_ID.
7. Schedule (e.g. weekly).

---

## Related docs

- `docs/README_SA_SAILING_SCRAPE_PROCESS.md` — Scraping source, URL format, name parsing, data flow.
- `docs/README_sailing_id_table.md` — Table rules and scraping process.
- `docs/SCRAPING_DATA_RULES.md` — What may be scraped and what must not be assumed.
