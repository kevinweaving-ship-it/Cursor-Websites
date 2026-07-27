# Sailor resolution & results ingestion — structural improvements

**Context:** Before large historical imports, these four improvements should be in place so matching is accurate and guardrails are hard.

**Related:** `docs/README_SAS_ID_MATCHING_LOGIC.md`, `docs/README_RESULTS_INGESTION.md`, `sailor_helm_aliases`, `sas_id_personal`, `classes`.

---

## 1. Age / class validation

**Issue:** Resolver does not check sailor age vs youth class (Optimist, Dabchick, etc.), so father/son (or similar) can collide when same sail number or name matches an adult.

**Goal:** When matching helm/crew to `sas_id_personal`, reject or down-rank candidates whose `year_of_birth` / `age` is inconsistent with a youth class.

**Acceptance:**

- Define “youth classes” (e.g. Optimist A/B/C, Dabchick, 29er, etc.) — from `classes` or a tag.
- For results in a youth class: only consider SAS IDs where age is in allowed range (e.g. &lt; 18 or class-specific).
- For results in open/adult classes: allow any age; optional “prefer adult” when sail number has multiple candidates.
- Document in resolver/matching logic and in `README_SAS_ID_MATCHING_LOGIC.md`.

**Not done yet.**

---

## 2. Sail-number ownership history (dedicated table)

**Issue:** Matching uses “prior results” (same sail number already has `helm_sa_sailing_id`) but there is no dedicated sail-number ownership table, so history is implicit and harder to reason about.

**Goal:** A single source of truth for “sail number X in class Y (or globally) was used by SAS ID Z in time window / regatta,” improving match accuracy and auditability.

**Acceptance:**

- New table (e.g. `sail_number_ownership` or `sail_number_history`) with at least: sail_number, class_id (optional), sa_sailing_id, first_seen / last_seen (regatta or date), source (result_id or manual).
- Resolver (and historical scraper) can: (1) look up this table for strong prior ownership, (2) optionally update it when a result is matched.
- Migration creates table; backfill from existing `results` where `helm_sa_sailing_id` + sail_number exist.
- Document in `README_SAS_ID_MATCHING_LOGIC.md` and DB schema docs.

**Not done yet.**

---

## 3. Alias learning (auto-suggest from corrections)

**Issue:** Aliases are only created when an admin manually resolves; the system does not auto-suggest aliases from repeated corrections (e.g. same helm_name → same sa_id applied multiple times).

**Goal:** When resolver or admin repeatedly assigns the same (helm_name, sail_number) → sa_sailing_id, suggest (or auto-create) an entry in `sailor_helm_aliases` so future scrapes resolve without manual steps.

**Acceptance:**

- After N successful matches of the same `LOWER(TRIM(helm_name))` (and optionally sail_number) to the same sa_sailing_id, suggest “Add alias: helm_name → sa_sailing_id.”
- Optional: batch job or resolver step that inserts into `sailor_helm_aliases` with a “source = auto” or “suggested” flag for review.
- Document in `README_SAS_ID_MATCHING_LOGIC.md` and next to `sailor_helm_aliases`.

**Not done yet.**

---

## 4. Results ingestion guardrails (hard validation)

**Issue:** Historical scraper does not yet enforce: (1) class must exist in `classes`, (2) sailor must resolve to SAS ID or go to review queue. Without this, bad data can be inserted.

**Goal:** Every results ingestion path (including historical scraper) must:

1. **Class:** Resolve class to an existing `classes.class_id` (via `class_name` or `class_aliases`). If no match → do not insert row; log to ingestion_issues / review; fail or skip that row.
2. **Sailor:** Resolve helm (and crew if applicable) to a valid SAS ID (`sas_id_personal`) or to the **review queue** (no SAS ID set; row still inserted but flagged for review). No “guess” insert of a new or invalid SAS ID.

**Acceptance:**

- Historical scraper (and any script that inserts into `results`) validates class before insert; on unknown class → skip row + log.
- Sailor resolution: either set `helm_sa_sailing_id` (and crew) from `sas_id_personal` or `sailor_helm_aliases`, or leave NULL and ensure row is in the unresolved/review queue (no fake IDs).
- Document in `README_RESULTS_INGESTION.md` and in scraper/ingestion code.

**Not done yet.**

---

## Order of work (suggested)

1. **4. Guardrails** — Prevents bad data during historical import; do first.
2. **2. Sail-number table** — Improves matching and gives a clear place to backfill ownership.
3. **1. Age/class validation** — Reduces father/son (and similar) collisions.
4. **3. Alias learning** — Reduces manual work over time; can run after resolver and sail-number table are used.

---

## Status

| # | Improvement              | Status   |
|---|--------------------------|----------|
| 1 | Age/class validation    | Not done |
| 2 | Sail-number ownership    | **Done** — `sail_number_history` table (migration 162) + backfill (163). Resolver can use it. |
| 3 | Alias learning           | Not done |
| 4 | Ingestion guardrails     | **Done** — Class: `require_class_id` (reject + log). Sailor: `resolve_helm_to_sa_id` (NULL → review queue; never fake ID). See `results_ingestion_common.py` and `README_RESULTS_INGESTION.md`. |
