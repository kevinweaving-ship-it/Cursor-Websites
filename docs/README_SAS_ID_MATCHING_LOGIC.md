# SAS ID matching logic (better rules)

Use **better logic** to link results (helm/crew with NULL SA ID) to `sas_id_personal`. Regatta **385** is the reference test set for these rules.

---

## Test cases (regatta 385)

| Result | Class | Helm | Crew | Issue |
|--------|--------|------|------|--------|
| 4517 | Sonnet | Tim Deversen **6148** | **Cheryl Deverson** NULL | Crew same surname as helm; helm has SAS ID → match crew by same surname + first name. |
| 4495 | 420 | **Simamkele Mtshofeni** NULL | Lihle Matomela NULL | Helm spelling variant of "Simankele Mtshofeni" (18908). Use fuzzy + club/surname. |
| 4495 | 420 | Simamkele … | **Lihle Matomela** NULL | Crew = "Kamvaelihle Matomela" (23596); first name match / nickname. |
| 4519 | Sonnet | Gordon Guthrie 5820 | **Helen** NULL | Crew first name only → match by club (HYC) + other results where "Helen" has SAS ID. |

---

## Five rules (order of use)

### 1. Helm surname + crew same surname, helm has SAS ID

- **When:** Crew has NULL SA ID; helm has SAS ID; crew surname is same (or obvious misspell) as helm surname.
- **Do:** Look up `sas_id_personal` for same surname (normalised) and first name match / fuzzy on crew first name. If exactly one candidate, set `crew_sa_sailing_id`.
- **Example:** Cheryl **Deverson**, helm Tim **Deversen** (6148) → find person with surname Deverson/Deversen and first name Cheryl; if found, set crew SA ID.

### 2. Club + similar surname spelling, other member has SAS ID

- **When:** Helm or crew has NULL SA ID; result has club (e.g. `club_id`).
- **Do:** At same club, find another member (from `sas_id_personal` or other results) with similar surname who has SAS ID; if typed name is a plausible spelling of that person (fuzzy), match.
- **Example:** **Simamkele** Mtshofeni at IZI → "Simankele" Mtshofeni (18908) in `sas_id_personal`; surname match + fuzzy first name → set helm 18908.

### 3. Sail number match

- **When:** Helm or crew has NULL SA ID; result has `sail_number` and class/club.
- **Do:** Find other results with same sail number (and same class or same club) where that role (helm or crew) has SAS ID; use that SA ID.
- **Example:** Sail 583 Sonnet HYC elsewhere has helm 6148 → same boat, same helm; if another row had crew with SA ID for sail 583, use for crew.

### 4. First name only (e.g. "Helen") + club + other classes

- **When:** Name is single word (first name only); result has club.
- **Do:** Same club, other results where a sailor with that first name has SAS ID (and sails other classes if possible); if unique or best candidate, match.
- **Example:** Crew "Helen" at HYC → find HYC results where helm or crew name contains "Helen" and has SAS ID; set crew_sa_sailing_id to that SA ID.

### 5. Family SAS ID range (±10)

- **When:** One role (helm or crew) already has a matched SAS ID; the other role has NULL and a similar surname (or spelling variant).
- **Do:** Family members often join SAS at the same time, so their SA Sailing IDs are close. Look up `sas_id_personal` for **same surname** (as the matched person) where `sa_sailing_id` is in the range **[matched_id − 10, matched_id + 10]** (excluding the matched ID). If exactly one candidate matches the unmatched name (first name fuzzy), suggest that SA ID.
- **Example:** Kevin Weaving matched → his SAS ID is X; search X−10 to X+10 for surname Weaving → find Birgitta Weaving → set crew_sa_sailing_id (or helm_sa_sailing_id) to her ID.

---

## Implementation

- **Script:** `scripts/match_results_to_sas_id_better.py`  
  - Applies rules 1–5 to results with NULL helm or crew SA ID.  
  - **Regatta 385:** use as test with `--regatta 385-2026-hyc-cape-classic` or `--regatta 385`.  
  - Default: dry-run (report only). Use `--apply` to write updates.

- **Existing:** Inline editor + `docs/README_SAS_ID_MATCHING.md` (fuzzy + nickname + club score) still apply when a user edits a name; the script is for batch/semi-auto fix using the four rules above.

---

## Cheryl Deverson (4517)

- She **is** in the result line: Sonnet 385, result_id 4517, sail 583, HYC, helm Tim Deversen 6148, crew **Cheryl Deverson** NULL.
- Rule 1: same surname as helm (Deverson/Deversen), helm has 6148 → look up Cheryl with surname Deverson in `sas_id_personal`. If she is not in `sas_id_personal`, no match until she is added; script will report "no candidate" for Rule 1.
- Rule 2: at HYC, no other Deverson with SAS ID in data except Tim → no Rule 2 match unless another family member is added with SAS ID.

---

## Simamkele Mtshofeni (4495) – mismatch and why 18908 wasn’t added

### The mismatch

| Where | Value |
|-------|--------|
| **Result row (4495)** | helm_name = **Simamkele** Mtshofeni, helm_sa_sailing_id = **NULL** |
| **sas_id_personal** | **Simankele** Mtshofeni, sa_sailing_id = **18908** |

So the result has a spelling variant (“Simamkele”) and no SA ID; the correct person is Simankele Mtshofeni (18908).

### Why it wasn’t found and added

1. **At import/sync**
   - The 385 data is loaded from `regatta_385_sync.sql` or from `add_regatta_385_420_fleet.py`. The Python script has a fixed map `SAILOR_IDS` with `'Simamkele Mtshofeni': None` and a `lookup_sa_id()` that only does **exact** name match (or first+last). So “Simamkele” never matches “Simankele” and the row is inserted with **NULL**.
   - The sync SQL also inserts that row with `helm_sa_sailing_id` NULL. Nothing at import time runs fuzzy matching or the matcher script.

2. **After load**
   - The only thing that can set 18908 is **`scripts/match_results_to_sas_id_better.py`** (Rule 2 global fuzzy + % match). That script is **not** run automatically when 385 is synced or when results are uploaded. So the DB stays NULL until someone runs the matcher and applies suggestions.

3. **Summary**
   - **Mismatch:** Result spelling “Simamkele” vs DB “Simankele” + no SA ID at import.
   - **Why not found at import:** Import uses exact match / fixed map; no fuzzy or variant lookup.
   - **Why not added after import:** Matcher script is a separate step; it was never run with `--apply`, or wasn’t run at all.

### How to add Simankele Mtshofeni (18908)

- **Option A (recommended):** Run the matcher and apply:
  ```bash
  python3 scripts/match_results_to_sas_id_better.py --regatta 385 --apply
  ```
  That will suggest helm 18908 for “Simamkele Mtshofeni” (and show % match) and update the row.

- **Option B:** So that future 385-style imports set 18908 without running the matcher, add the variant to the import map (see below).

### Optional: set 18908 at import (e.g. 385 fleet script)

In `add_regatta_385_420_fleet.py`, the map has `'Simamkele Mtshofeni': None`. Change it to:

```python
'Simamkele Mtshofeni': '18908',  # spelling variant of Simankele Mtshofeni
```

Then (re)run that script or regenerate the sync SQL so new loads get helm_sa_sailing_id = 18908 for that row. Existing DB rows still need Option A (matcher --apply) once.
