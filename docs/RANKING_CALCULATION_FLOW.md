# Ranking calculation flow – score all, then cap from class, then rules

Ranking per class is **dynamic**: it must be recalculated when new results are uploaded so standings stay current.

---

## 1. Score all regattas for all sailors in the class

- **Time window:** Last 12 months by **regatta end date**.
- **Eligible results:** SA Sailing / class approved, valid fleet size (N), N ≥ class minimum (e.g. Optimist A/B ≥ 8), event has a grade, result status final or provisional.
- **For every eligible result** in the class:
  - Assign **event grade E** (Nationals 200, Provincial 100, Club 50).
  - Apply **provisional rule** per sailor (at most one provisional at full grade; others E=50).
  - Compute **EventPoints = E × (N − P + 1) / N** (decimal, no rounding).
- Outcome: a full set of **scores already calculated** for every sailor × event in the class (all results in the last 12 months that meet the rules).

So the first step is: **score all regattas for all sailors in their class** using the same formula and rules. All of that is then used for the next steps.

---

## 2. Class result cap from class participation (last 12 months)

- **Per class:** Look at how many eligible regattas each sailor in that class sailed in the last 12 months (using the same eligible set as above).
- **Class participation:** Compute a single number that represents “typical” number of regattas sailed in the class:
  - **Option A – Median:** Median of (regatta count per sailor). At least 50% of the class sailed that many or fewer. Robust to a few very active sailors.
  - **Option B – Average:** Mean of (regatta count per sailor). Simple; can be pulled up by a few sailors who sail many events.
- **Result cap:**  
  **ResultCap = MIN(6, ROUND(median or average))**  
  with .5 rounding up, and **ResultCap between 1 and 6**.
- **Practical choice:** **Median** is usually better so the cap reflects “typical” participation and is not skewed by a small number of sailors with many regattas. Average can be used if you explicitly want that behaviour.

So: **calculate based on all results/scores already calculated for all sailors in the class** to get regatta counts, then derive the class cap from that (median or average, as configured).

---

## 3. Which regattas count (regatta type and scores)

- **Per sailor, in that class:** Decide which results actually count toward their ranking, using:
  - **Regatta type:** e.g. province-fair rule: 1× Nationals, 1× Province (e.g. provincial with most entries N), rest as “other”.
  - **Scores:** Among “other” (and any downgraded provincial), take the **best by EventPoints** (already calculated) until the total number of counting results equals **ResultCap** (1× Nationals + 1× Province + (ResultCap − 2)× best other, if using province-fair).
- **RankingScore** = sum of EventPoints of the **counting** results only (decimals, no rounding for calculation).

So: **which ones must be used** is decided by **regatta type and scores** on the pre-calculated event points.

---

## 4. Rank sailors and store

- **Sort** sailors by RankingScore DESC, then tie-breaks (e.g. highest single EventPoints, then next, then most recent counted regatta, then name).
- **Assign** rank position (1, 2, 3, …).
- **Persist** to `standing_list` (and any related tables): rank, ranking_score, result_cap, results_counted, last_updated.

---

## 5. Keeping it current (dynamic system)

- Rankings are **per class** and **per sailor**, and must be **updated when data changes** (new results uploaded, result status changed, etc.).
- **When to recalculate:**
  - After **new results are uploaded** for a regatta (recalc affected classes).
  - On a **schedule** (e.g. nightly or weekly) for all classes.
  - Optionally **on demand** (e.g. admin “Recalc standings” or API trigger).
- **Automatic queue (100% automatic):** When any row in `results` is INSERTed, UPDATEd, or DELETEd, a trigger (`trg_queue_standings_recalc`) queues the affected class in `standings_recalc_queue`. Run `python3 process_standings_recalc_queue.py` (e.g. via cron every 5–15 minutes or as a post-upload step) so new results automatically update standings.
- **Manual recalc (optional):**
  - **All classes:** `python3 recalc_standings_after_upload.py` or `python3 calculate_universal_standings.py`
  - **One class:** `python3 recalc_standings_after_upload.py "Optimist A"`
- Recalculation **re-scores all eligible regattas** for all sailors in each class, **recomputes the class cap** from current participation (median or avg), **re-applies** which regattas count (type + score), then **re-ranks** and **writes** updated standings.

So: **ranking of sailor for each and every class is a dynamic system** that stays current by recalculating from the same flow (score all → cap from class → which count → rank) whenever new results are uploaded or when the queue processor runs.

---

## Summary

| Step | What |
|------|------|
| 1 | **Score all** eligible regattas for all sailors in the class (EventPoints, provisional rule). |
| 2 | **Class cap** = median (or average) number of regattas sailed in the class (last 12 months), rounded, min 1 max 6. |
| 3 | **Which count** = regatta type rules (e.g. 1× Nationals, 1× Province, rest best by score) up to ResultCap. |
| 4 | **Rank** by RankingScore and tie-breaks; persist. |
| 5 | **Recalc** when new results are uploaded (or on a schedule) so standings stay current. |
