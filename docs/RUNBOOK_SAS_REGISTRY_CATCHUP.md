# Runbook: SAS ID registry integrity and incremental catch-up

Follow these steps in order. Do **not** hardcode the range 28218–28406; let the incremental scraper probe forward and stop after 20 consecutive NOT_FOUND.

**Do not run checksum / integrity coverage until STEP 0 is done and structure is confirmed.**

---

## STEP 0 — Inspect existing table structure and data

Run this **first**. We need to see the real table definition and data before any integrity or catch-up.

### 1) Full table definition (psql)

```bash
psql "$DB_URL" -c "\d+ sas_id_registry"
```

From a psql session you can run: `\d+ sas_id_registry`

**We need to see:** column names, data types, nullability, default values, primary key, unique constraints, indexes.

### 2) Column-level summary (clean view)

```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'sas_id_registry'
ORDER BY ordinal_position;
```

Confirms exact column order and definitions.

### 3) Row count + range

```sql
SELECT
    COUNT(*) AS total_rows,
    MIN(sas_id) AS min_id,
    MAX(sas_id) AS max_id
FROM sas_id_registry;
```

### 4) Status distribution

See what status values actually exist (VALID, NOT_FOUND, ERROR, or any unexpected values).

```sql
SELECT status, COUNT(*)
FROM sas_id_registry
GROUP BY status
ORDER BY status;
```

### 5) Sample last 10 rows

```sql
SELECT *
FROM sas_id_registry
ORDER BY sas_id DESC
LIMIT 10;
```

Confirms what recent inserts look like.

### What we are verifying

- `sas_id` exists and type is **INTEGER**
- `sas_id` is **PRIMARY KEY**
- `status` column exists
- `scraped_at` exists (or equivalent)
- No unexpected columns
- No silent schema drift

**Only after seeing this output** do we run the integrity coverage scan (Steps 1–4) and then incremental catch-up (Step 5).

### Run all STEP 0 SQL in one go

```bash
psql "$DB_URL" -c "\d+ sas_id_registry"
psql "$DB_URL" -f scripts/step0_inspect_sas_id_registry.sql
```

Paste the output. Then: (1) confirm structure is safe, (2) identify any schema issues, (3) get the next exact command block. No guessing.

---

## STEP 1 — Confirm PRIMARY KEY

**Show full table definition:**
```bash
psql "$DB_URL" -c "\d sas_id_registry"
```
(Or from psql: `\d sas_id_registry`)

**We need:** `PRIMARY KEY (sas_id)` (or at least UNIQUE on `sas_id`).

**If NOT present**, run:
```sql
ALTER TABLE sas_id_registry
ADD CONSTRAINT sas_id_registry_pkey PRIMARY KEY (sas_id);
```
If it errors saying the key already exists → fine.

**Alternative check (SQL only):**
```sql
SELECT c.conname, c.contype
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'sas_id_registry' AND c.contype = 'p';
```
Should return one row (primary key).

---

## STEP 2 — Check for duplicates (must be zero)

```sql
SELECT sas_id, COUNT(*)
FROM sas_id_registry
GROUP BY sas_id
HAVING COUNT(*) > 1;
```

**Expected:** Zero rows.

If any rows are returned → stop and fix duplicates before continuing (e.g. dedupe and re-add PK).

---

## STEP 3 — Missing numeric IDs (coverage test)

Confirms we are not skipping numeric IDs below current max.

```sql
SELECT COUNT(*) AS missing_ids
FROM (
    SELECT series_id::int AS series_id
    FROM generate_series(
        (SELECT COALESCE(MIN(sas_id), 0) FROM sas_id_registry),
        (SELECT COALESCE(MAX(sas_id), 0) FROM sas_id_registry)
    ) series_id
    LEFT JOIN sas_id_registry r ON r.sas_id = series_id
    WHERE r.sas_id IS NULL
) t;
```

**Expected:** `0`.

If not zero → paste result and fix gaps before automation.

---

## STEP 4 — Current upper bound

```sql
SELECT MAX(sas_id) AS current_max_id FROM sas_id_registry;
```

**Expected:** `28217` (or updated value if you already ran a catch-up).

---

## STEP 5 — Run incremental catch-up (one-time manual trigger)

**Only after Steps 1–4 are clean.**

1. Run your incremental scraper **once** (e.g. call `incremental_sas_registry_scrape()` or run the script that implements it).
2. **Do NOT** hardcode the range 28218–28406.
3. **Do NOT** manually insert 28218–28406.
4. Let incremental logic: start at `MAX(sas_id)+1`, probe forward, stop after **20 consecutive NOT_FOUND**.

---

## STEP 6 — Verify batch log

After Step 5 completes:

```sql
SELECT *
FROM sas_scrape_batches
ORDER BY started_at DESC
LIMIT 1;
```

**Confirm:**

| Field | Expected |
|-------|----------|
| `start_id` | 28218 |
| `detected_upper_bound` | ≈ 28406 |
| `valid_count` | Reasonable (e.g. 100–200) |
| `not_found_count` | ≥ 20 (run stopped after 20 consecutive NOT_FOUND) |
| `error_count` | Low (ideally 0) |
| `completed_at` | Set (not NULL) |

---

## All-in-one verification script

To run Steps 1 (SQL check), 2, 3, 4 and 6 in one go:

```bash
psql "$DB_URL" -f scripts/verify_sas_id_registry_integrity.sql
```

Step 1’s full table definition still needs `\d sas_id_registry` in psql if you want to see the full DDL. Step 5 is always manual (trigger the scraper).

---

## Reference

- [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md) — Registry integrity, status enum, first-run strategy, deployment order.
- Migrations: `150_sas_scrape_batches.sql`, `151_sas_id_registry.sql`.
