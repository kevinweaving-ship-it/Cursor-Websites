# Results table checksum rules

When verifying or importing results, these rules must hold. Violations are data errors.

---

## 1. Same sailor, same regatta: one class only

**Rule:** It is impossible for the same sailor to sail in more than one class in the same regatta.

- For each `regatta_id`, each `helm_sa_sailing_id` and each `crew_sa_sailing_id` must appear in only one distinct `class_canonical` (or fleet) for that regatta.
- If a sailor appears as helm or crew in e.g. both "Optimist" and "Sonnet" in the same regatta, one of those rows is wrong (wrong sailor linked or wrong class).

**Check:** Run the verification script; it reports `[CHECKSUM] Same sailor >1 class in same regatta (impossible)`.

```bash
python3 scripts/fix_5820_optimist_and_verify_results.py
```

The script outputs any regatta/sailor_id that has multiple classes; fix by correcting the sailor or class on the offending result row(s).

---

## 2. Helm/crew IDs must exist in sas_id_personal

Every non-null `helm_sa_sailing_id` and `crew_sa_sailing_id` must exist in `sas_id_personal`. The same script reports "Helm ID not in sas_id_personal" and "Crew ID not in sas_id_personal".

---

## 3. Other checks in the script

- Helm name vs `sas_id_personal` name mismatch (spelling/nicknames; ID is still correct).
- Same sailor as helm and crew (single-hander; allowed but flagged).

---

**Script:** `scripts/fix_5820_optimist_and_verify_results.py` (run with local `DB_URL` or set for live).
