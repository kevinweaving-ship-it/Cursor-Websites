# Ranking Rules – All Classes & Sailors

This document describes the **universal ranking rules** applied to **all classes** and **all sailors**. The same logic runs for every class (Optimist A, Optimist B, 420, ILCA 6, Dabchick, etc.); the only class-specific parts are **entry cutoffs** (per-class, per-regatta-type) and, for **420**, the population used to compute “how many regattas count”.

---

## Order of operations (acid test first)

1. **Valid rankable sailors in class** = acid test: sailed that class in **at least one regatta** in the **last 12 months**. Count those (distinct people).
2. **From that list, only sailors with a valid SAS ID** — eliminate anyone without SAS ID. The result is the **valid rankable sailors** for the class. **Y** (in "Ranked X / Y Sailors") = count of this list. All pages that show class stats/ranking for that class must use this same Y. **Automatic routine:** Run `python3 scripts/update_class_valid_sailors.py` (or let the daily job run it after recalc) to refresh valid sailor counts for every class into `standings_metadata`. Then all HTML pages can pull Y via **GET /api/class-totals** (returns `{ class_name: total_sailors_12m }`) or from existing endpoints that read from `standings_metadata` when present. **API:** `/api/class-totals`, `/api/standings/db`, `/api/member/{sa_id}/nationals-rank`, and `/api/member/{sa_id}/results` (summary.class_stats[class].sailors_total) all supply Y.
3. **Then** apply the other rules (result cap, province-fair selection, grades, entry cutoffs, etc.) to **rank each and every** valid sailor from step 2. **X** = a sailor's rank within that list. **Each sailor must have a ranking score in the standing_list table for each valid class they sail (in the last 12 months).** That is achieved by running the **universal recalc** for all classes: `python3 recalc_standings_after_upload.py` (or the daily job `scripts/check_new_regatta_and_recalc.py`), which uses `calculate_universal_standings.py` and writes `ranking_score` for every class. Then the UI can show “Ranked X (Score: Z) / Y Sailors” for every class.

---

## 1. Who Can Be Ranked

- **Simple rule:** Only sailors with a SAS ID who sailed the class in the last 12 months are valid sailors in that class to be ranked.
- Sailors with **no SAS ID** (temp ID only or no ID) **cannot be ranked and are excluded** from:
  - the standing list,
  - the “total sailors in class” count used for “Ranked X / Y sailors”.
- **Implementation:** All ranking queries use `helm_sa_sailing_id IS NOT NULL` (and, where crew count, `crew_sa_sailing_id IS NOT NULL`). Temp IDs are never used for ranking.

---

## 2. Total Sailors in Class (“Ranked X / Y Sailors”)

- **Simple rule:** Any sailor with a SAS ID who sailed the class being looked at (e.g. Dabchick) in the last 12 months is a valid sailor in that class to be ranked. **Y** = count of those sailors (distinct SAS IDs).
- **Single-handed classes:** count distinct helms (SAS ID).
- **Double-handed classes (e.g. 420):** count **helm + crew** (each person once, SAS ID only). Crew count as sailors for the denominator Y.
- **X** = the sailor’s rank. For **double-handed (420)**, every sailor (helm or crew) is ranked; a sailor’s **ranking score** uses **all** their results in the class (races where they were **helm or crew**). Each boat gives one position; that result counts for both helm and crew. So a sailor who only crews still gets a rank and score from those crew results.
- **Sailors rank independently.** They do **not** need to sail with the same crew (or same helm) across regattas. Each sailor gets the **same score** for the **same regatta** as their boat-mate (same position P, fleet N, grade E → same points). They can sail with different partners in different regattas; **rank score is not tied to sailing with the same sailor.** Ranking is per person, not per pair.
- **Implementation:** `get_total_sailors_in_class_last_12m()` in the API unions helm and crew sailor IDs (SAS ID only). In `calculate_universal_standings.py`, for 420 we add events from both helm and crew result rows so each sailor’s score includes all their 420 races; each event is (N, P, grade) for that boat, so helm and crew get the same points for that regatta.
- - **Ranking score per class:** Each sailor must have a **ranking_score** in `standing_list` for each valid class they sail (last 12 months). The UI shows "Ranked X (Score: Z) out of Y sailors" when `ranking_score` is present. **To get scores for all classes**, run a full universal recalc: `python3 recalc_standings_after_upload.py` (no class argument). That recalculates every class that has results in the last 12 months (Optimist A/B, 420, Dabchick, ILCA 6, etc.) and writes `ranking_score` for each. If only one class (e.g. Optimist) shows a score, other classes may not have been recalculated yet — run the full recalc once.
- **HTML display:** All pages that show “Ranked X / Y Sailors” use **Y** from the API (`total_sailors`). **Single source of truth:** Y is always from `standings_common.get_total_sailors_in_class_last_12m()` — no other source (e.g. standings_metadata or standing_list length) is used for display. `/api/standings`, `/api/standings/db`, and `/api/member/{sa_id}/nationals-rank` all call this one function. **Do not duplicate this logic** elsewhere so **Y stays correct** and **Y updates automatically** as more results are added (Y can go up) or as sailors drop out of the class (no race in last 12 months → Y goes down).

---

## 3. Time Window

- **Last 12 months** from today (by regatta end/start date).
- Regattas outside this window do not count.
- Only regattas that were **actually sailed** (with race results) count. Series placeholders or regattas with no race results are excluded — no need to mention specific IDs in the rule.

---

## 4. How Many Regattas Count (Result Cap)

- The **result cap** is how many regattas **count** toward a sailor’s ranking score (best N regattas per sailor).
- **Rule:** Result cap = **average number of regattas sailed by the top 50% of sailors** (those who sail the most), rounded, clamped between 1 and 6. For 420, “regattas sailed” includes races as **helm or crew** (so e.g. 4 regattas can count when the top 50% average is 4).
- **420 minimum:** For **420** only, the result cap has a **minimum of 4**: at least 4 regattas count toward each sailor’s score (even if the top-50% average is lower). Other classes use only the computed cap (1–6).
- **Population used for this average:**
  - **420 (and double-handed):** regatta counts are taken over **all sailors in the class** (helm + crew, SAS ID, last 12 months), and each sailor’s count = number of races they sailed (helm or crew).
  - **All other classes:** regatta counts are taken over **helms only** (SAS ID, last 12 months).
- **Implementation:** `calculate_universal_standings.py` builds `regatta_counts` (per sailor); for 420, each sailor’s events include both helm and crew results, so regatta count reflects all 420 races; then sorts descending, takes top 50%, averages, rounds, clamps 1–6. For 420, `result_cap = max(result_cap, 4)` is then applied.

---

## 5. Which Regattas Count (Selection & Grades)

- For each sailor we select **up to result_cap** regattas using the **province-fair** rule.
- **Nationals and Prov/Reg must be used if sailed – they cannot be discarded** in favour of club events.

### 5.1 Event Grades (E)

| Type              | Grade (E) | Description                          |
|-------------------|-----------|--------------------------------------|
| Nationals         | 200       | Event name contains “national”, “wc ”, “world champ” |
| Provincial/Regional | 100     | “regional”, “provincial”, “championship”             |
| Club/other        | 50        | All other events                     |

### 5.2 Province-Fair Selection (per sailor)

1. **Nationals:** At most **one** nationals (best by points at E=200). **Always included if sailed.**
2. **Provincial/Regional:** At most **one** provincial/regional at full grade (E=100): the one with **most entries (N)**. **Always included if sailed.** Any other provincial/regional events are re-scored at E=50 and compete with club for remaining slots.
3. **Remaining slots** (up to result_cap): Filled with the **best by EventPoints** from “others” (club events + downgraded provincial).
- **EventPoints** = E × (N − P + 1) / N, where N = fleet size (entries), P = position.

### 5.3 Discard Effect

- Sailors who sail **more** than the result cap have their **best** N regattas counted (best club/smaller can count); **worse/spare regattas are effectively discarded**.
- Sailors who sail **fewer** than the cap have **all** their regattas count (no discard).

---

## 6. Entry Cutoffs (Min Entries per Regatta Type)

- A regatta **block** (fleet) only **counts** if it has at least the **minimum entries** for its **regatta type** and **class**.
- **Per-class, per-regatta-type** cutoffs (Nationals, Provincial/Regional, Club) – unique to each class.
- Cutoffs can be:
  - **Configured** (e.g. Optimist: see below), or
  - **Derived** from that class’s average entries (last 12 months) for that type, then **lowered** (e.g. round(avg × 0.8)) so the cutoff is “lower than avg”.

### 6.1 Optimist (A, B, Optimist)

| Regatta type   | Min entries | Note                          |
|----------------|------------|-------------------------------|
| Nationals (×200) | 25         | e.g. last nationals 33 entries |
| Provincial/WC (×100) | 15   | Events with entries above 15   |
| Club (×50)     | 25         |                                |

### 6.2 Other Classes

- If a class has no configured cutoffs, cutoffs are computed: average entries per type (from blocks that already pass the class’s general min fleet), then `max(min_fleet, round(avg × 0.8))` per type.
- General **min fleet** floor (e.g. Optimist 8, default 3) still applies before per-type cutoffs.

---

## 7. Ranking Score & Order

- **Ranking score** = sum of EventPoints of the **selected** regattas (up to result_cap).
- **Sort order:** Ranking score **descending**, then tie-break by best single event, then next, then most recent counted regatta date, then name.
- **Display:** “Ranked X / Y Sailors” with optional “(Score: N)”.

---

## 8. Application to All Classes and Sailors

- **All classes** use the same:
  - SAS ID only (no temp ID).
  - Last 12 months; only regattas actually sailed (with race results) count.
  - Same province-fair selection (1× Nationals, 1× Prov, rest best by score).
  - Same grades (200 / 100 / 50).
  - Same “top 50% average” result cap logic.
  - Same rule: Nationals and Prov/Reg must be used if sailed (cannot be discarded).
- **Class-specific:**
  - **Entry cutoffs:** per-class, per-type (config for Optimist; computed “lower than avg” for others).
  - **Result cap population:** 420 uses helm+crew for the average; all other classes use helms only.
  - **Result cap minimum:** 420 has a minimum result cap of 4 (at least 4 regattas count); other classes use only the computed cap (1–6).
- **Implementation:** Single code path in `calculate_universal_standings.py` (`calculate_universal_standings_for_class()`); class name is only used for min fleet, entry cutoffs, and 420 helm+crew regatta counts. No other class bypasses.

---

## 9. Recalculation

- Standings are recalculated when new results are uploaded (e.g. `recalc_standings_after_upload.py` or full run).
- Each class is processed independently; the same rules above apply to every class.

### 9.1 Where “XX sailors” is stored (standings_metadata)

- **Table `standings_metadata`** (per class): stores `total_sailors_12m` (distinct sailors, SAS ID, last 12 months), `last_regatta_number`, `last_updated`. Updated whenever standings are written (e.g. by `recalc_standings_after_upload.py` or `write_standings_to_db()`).
- **API/HTML:** “Ranked X / Y Sailors” uses **Y** from `standings_metadata.total_sailors_12m` when present; otherwise from live query `get_total_sailors_in_class_last_12m()`. So the displayed “XX sailors” is pulled from this table after each recalc and updates automatically as more results or sailors fall in/out of the 12‑month window.

### 9.2 Automatic daily recalc when new regattas appear

- **Table `standings_recalc_metadata`** (single row): stores `last_processed_regatta_number` and `last_run_at`.
- **Script `scripts/check_new_regatta_and_recalc.py`:** Run daily (e.g. cron `0 2 * * *`). Compares `MAX(regatta_number)` from `regattas` to `last_processed_regatta_number`. If max is greater (e.g. new regatta 378, 379, …), runs full standings recalc for all classes (same as `recalc_standings_after_upload.py` with no args), then updates `last_processed_regatta_number` and `standings_metadata` for every class. So new regatta classes sailed and “XXX sailors” and entire class rankings are redone automatically.
- **Migration:** Run `database/migrations/126_standings_metadata.sql` once to create `standings_metadata` and `standings_recalc_metadata`.

---

## 10. Audit / Corrections (learn and fix)

- **Double-handed (420): ranking used to use only helm results.** A sailor’s score only included races where they were **helm**. Races as **crew** (e.g. Alex Falcon at 420 Nationals, P=1) were **excluded**, so crew-only or helm+crew sailors were under-ranked. **Corrected:** for 420, we now add events from **crew** result rows as well as helm; each sailor’s ranking score uses **all** their 420 results (helm or crew). Same boat = one position, counted for both helm and crew.
- **Result cap “4 regattas should count”:** For 420, when crew results are included, regatta counts per sailor go up; the top 50% average may be 3 or 4. If class policy is that **4 regattas count** for 420, that can be enforced (e.g. `result_cap = max(result_cap, 4)` for 420) or left to the computed top-50% average.

---

## 11. Fix-and-verify workflow (keep correcting)

- **When you find an error or issue:** fix it in code (e.g. `calculate_universal_standings.py` or API), then **re-run verification on all audited classes** so the fix is applied everywhere and no previously audited class regresses.
- **Audited classes** (run after every ranking fix): **Optimist A**, **Optimist B**, **420**, **Dabchick**. These are the classes we have validated; any change to ranking logic must be tested on all of them.
- **How to verify:** run `python3 scripts/verify_audited_classes.py`. It recalculates standings for each audited class and checks that each returns data, has a valid result cap, and a sensible sailor count. Exit code 0 = all correct; non-zero = something failed.
- **After a fix:** (1) Apply the fix. (2) Run `recalc_standings_after_upload.py` for affected class(es) or all. (3) Run `scripts/verify_audited_classes.py`. (4) Optionally run `scripts/show_top10_class.py "<Class>"` for a quick human check.

---

## 12. Verification (Applied to All Classes)

- **Single code path:** `calculate_universal_standings_for_class(class_name, conn)` is used for every class (Optimist A, Optimist B, 420, ILCA 6, Dabchick, ILCA 7, etc.).
- **Class-specific only:** (1) Entry cutoffs (config for Optimist 25/15/25; computed “lower than avg” for others). (2) Result-cap population: 420 uses helm+crew for the average; all others use helms only. (3) Min fleet and age limits per class.
- **No bypasses:** SAS ID check, province-fair selection, grades, “top 50%” result cap formula, and “Nationals/Prov must be used if sailed” apply to every class and every sailor in the standing list.

---

## 13. References

- **Code:** `calculate_universal_standings.py` (selection: `select_province_fair`, grades: `get_event_grade`, `event_type`; entry cutoffs: `get_entry_cutoff_for_type`, `ENTRY_CUTOFF_BY_CLASS_TYPE`).
- **API:** `get_total_sailors_in_class_last_12m()` for “Ranked X / Y”; `/api/standings/db` returns rankings and `total_sailors`.
- **Specs:** `docs/STANDINGS_RANKING_SPEC_FULL.md`, `docs/RANKING_CALCULATION_FLOW.md`.
