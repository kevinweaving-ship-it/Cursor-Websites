# Likely Classes Validation

Validates the “likely classes” engine used on event cards.

**Query:**
```sql
SELECT
  regatta_id,
  class_canonical,
  COUNT(*) AS entries
FROM results
GROUP BY regatta_id, class_canonical
ORDER BY entries DESC
LIMIT 200;
```

Confirm that `class_canonical` values align with expected classes:

- Optimist
- ILCA
- 420
- Sonnet
- 29er
- Dabchick

**Sample (top 50):**

| regatta_id | class_canonical | entries |
|------------|-----------------|--------|
| *(run script to populate)* | | |

**Distinct class_canonical in result set:** *(run script to populate)*

**Summary:** Expected classes vs found → *(run script to populate)*
