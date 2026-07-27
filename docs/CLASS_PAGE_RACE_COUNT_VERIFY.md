# Class page: sailor race count verification

**Rule:**  
- **Regattas** = `COUNT(DISTINCT regatta_id)`  
- **Races** = `SUM(number_of_race_scores_keys)` (from `race_scores` JSON)

Example: `{"R1":1,"R2":2,"R3":4,"R4":3}` → race count = 4.

## Direct SQL check (e.g. Timothy Weaving, class 62)

Run against your DB (psql or API DB):

```sql
SELECT
    COUNT(DISTINCT regatta_id) AS regattas_in_class,
    SUM(
        (SELECT COUNT(*) FROM json_object_keys(race_scores::json))
    ) AS races_in_class
FROM results
WHERE class_id = 62
  AND raced = TRUE
  AND helm_name = 'Timothy Weaving';
```

**Expected (example):** regattas_in_class = 13, races_in_class = 78 (not 13/13).

## API check

After deploy, open `/class/62-optimist-a` and confirm e.g.:

- **Timothy Weaving:** Races: 78, Regattas: 13

## Correct SQL pattern in code

- Class-level **total_races**: `SUM(CASE WHEN race_scores IS NOT NULL THEN (SELECT COUNT(*) FROM json_object_keys(race_scores::json) AS k) ELSE 0 END)` over `results` for that class.
- Per-sailor **races_in_class**: same expression in a CTE per (sailor, result), then `SUM(races_this_result)` grouped by sailor.
- **regattas_in_class**: always `COUNT(DISTINCT regatta_id)`.

Do **not** use `COUNT(*)` from results for race counts; that equals number of result rows (one per regatta per sailor), so Races would wrongly match Regattas.
