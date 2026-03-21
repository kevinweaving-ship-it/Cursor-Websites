# Manual fix: sailor class display (e.g. adult showing Optimist)

When a sailor’s “Confirm Your Profile” (or profile search) shows a class that doesn’t fit (e.g. **age 62** but **Optimist**), the list comes from **all results** where that sailor is helm or crew. One wrong or odd result row can add that class.

**Example:** Gordon Guthrie, SAS ID **5820**, age 62/63, shows Optimist (X1) + Sonnet (X3) + Hobie 16 (X8). Optimist is usually youth; at 62 it may be coach/masters or a data error.

---

## 1) Find which result(s) gave the class

Run on **local** (or **live** if you have DB access):

```sql
-- Replace 5820 with the sailor’s SAS ID
SELECT r.result_id, r.regatta_id, r.class_canonical, r.class_original, r.fleet_label,
       r.helm_name, r.helm_sa_sailing_id, r.crew_name, r.crew_sa_sailing_id,
       reg.event_name, reg.start_date, reg.end_date
FROM results r
JOIN regattas reg ON reg.regatta_id = r.regatta_id
WHERE (r.helm_sa_sailing_id::text = '5820' OR r.crew_sa_sailing_id::text = '5820')
  AND r.class_canonical ILIKE '%optimist%'
ORDER BY reg.end_date DESC;
```

That shows every result where 5820 is helm or crew and the class is Optimist. Check if it’s correct (e.g. coach boat, masters) or a mistake (wrong class on the row).

---

## 2) Fix if the class is wrong

Only change data if the **class on that result** is wrong (e.g. should be Sonnet or another class, not Optimist).

- **Single result:** update that row (and optionally `class_original` / `fleet_label` to match):

```sql
-- Replace result_id and the correct class name
UPDATE results
SET class_canonical = 'Sonnet', class_original = 'Sonnet', fleet_label = 'Sonnet'
WHERE result_id = 12345;
```

- **Several results:** same idea, with a `WHERE` that matches the wrong Optimist rows (e.g. by `regatta_id` and helm/crew):

```sql
UPDATE results
SET class_canonical = 'CorrectClass', class_original = 'CorrectClass', fleet_label = 'CorrectClass'
WHERE (helm_sa_sailing_id::text = '5820' OR crew_sa_sailing_id::text = '5820')
  AND class_canonical ILIKE '%optimist%'
  AND regatta_id = 'xxx';
```

Then **re-run the profile search** (or refresh) to see the updated classes.

---

## 3) If it’s correct (e.g. coach / masters)

If the sailor really did sail Optimist (e.g. coach boat or masters), **no DB change**. The display is correct; the “manual” is just to confirm which result produced it (step 1).

---

## 4) Live DB

- **Local:** use your usual Postgres client / `psql` with local `DB_URL`.
- **Live:** from your machine, for example:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  "psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -c \"
SELECT result_id, regatta_id, class_canonical, helm_name, crew_name
FROM results
WHERE (helm_sa_sailing_id::text = '5820' OR crew_sa_sailing_id::text = '5820')
  AND class_canonical ILIKE '%optimist%';
\""
```

Then apply the same `UPDATE` on live if you confirmed the class is wrong.

---

**Summary:** The profile “classes” list is built from `results` (helm + crew). To “do manual” for a case like “he’s 62, can be Optimist”: (1) use the SELECT above to see which result(s) give Optimist; (2) if wrong, UPDATE that row’s class; if correct (e.g. coach), leave as is.
