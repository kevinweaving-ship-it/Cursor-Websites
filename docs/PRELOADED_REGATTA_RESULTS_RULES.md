# Regatta results ingestion — rules (parsed, historical & preloaded)

> **Required reference:** Read this document **before** ingesting, correcting, or checksumming **any** regatta results that land in `results` / `regatta_blocks` — including **parsed** imports (PDF, sheets, pipelines), **historical** regattas, and **preloaded** multi-fleet events (e.g. WC Dinghy Champs). Do not re-derive workflow from chat history alone — **start here**, then use server scripts and `api.py` scoring paths as applicable.
>
> **Shortcut:** `sailingsa/deploy/README_WC_PRELOADED_RESULTS.md` (deploy folder index; WC-heavy examples).

## Scope (same rules everywhere)

| Situation | These rules apply to |
|-----------|----------------------|
| Parser / ETL writing `results` rows | §1–3, §5–6; recalc per §4 (use correct engine for that `regatta_id`) |
| Historical regatta backfill or fix | Same identity, names, clubs; validate checksums against source document |
| Preloaded / seeded event (e.g. WC Dinghy Champs) | Full §4–5 including WC-specific recalc and `fix_wc_2026_*` patterns |

**WC Dinghy Champs** is a **worked example** with extra tooling (`fix_wc_2026_*`, `_recalculate_fleet_block_scoring_and_ranks` for that slug). **Everything else** still follows §1–3 and §5–6; use the **legacy** scoring path in `api.py` for non-WC regattas unless the regatta is wired for WC-style scoring.

---

## 1. Source of truth (identity vs results)

| Layer | Role |
|--------|------|
| **`sas_id_personal` (live SAS mirror)** | **Identity:** `sa_sailing_id`, names as scraped from SAS. Do not invent IDs. Amend only when explicitly fixing a known scrape error (e.g. typo), then document. |
| **Official results sheet / NOR / parsed source** | **Racing truth:** sail numbers, race columns, fleet header, penalties (DNC/OCS/DNF/…), ranks as published. |
| **`results` rows** | **Link** scores to sailors via `helm_sa_sailing_id` / `crew_sa_sailing_id` when matched; store **display names** per §2. |

If there is **no SAS match** yet: store the **source** helm/crew strings and leave SAS columns `NULL`. When a later SAS scrape resolves an ID, **attach** the ID and **normalize** the stored name; optionally backfill other rows for the same person.

---

## 2. How names are stored on `results` (when SAS ID is set)

- **Do not** copy SAS `full_name` if it is **Last, First** comma style for display on the site.
- **Do** set `helm_name` / `crew_name` from SAS columns as:

  **`first word of `first_name` + space + `last_name`**

  (ignores `second_name` and extra given names — e.g. “Hannah Lynn” → **Hannah** + surname.)

SQL pattern (PostgreSQL):

```sql
TRIM(
  split_part(TRIM(COALESCE(p.first_name, '')), ' ', 1)
  || ' '
  || TRIM(COALESCE(p.last_name, ''))
)
```

Apply when inserting/updating from `sas_id_personal` joined on `helm_sa_sailing_id` / `crew_sa_sailing_id`.

- **Lookup-only aliases** (e.g. sheet “Charlie” vs SAS “Charles”) are allowed **only** to resolve `sa_sailing_id`; stored names still follow the rule above after match.

---

## 3. Clubs

- If the source shows **two clubs** (e.g. `ZVYC / HYC`, `VLC/Aeolians`): store the **first-listed** code and resolve `club_id` from that.
- Long host-style strings (e.g. `UCT Yacht Club`) → resolve to the usual **abbrev** (`UCT`) when that matches your `clubs` table pattern.

---

## 4. Loading and correcting scores

### 4.1 Initial / bulk load (any regatta)

1. Ensure `regattas` and `regatta_blocks` exist for the event and fleet (`block_id` like `{regatta_id}:{fleet-suffix}`).
2. **Delete** or **update** existing rows for that `block_id` according to whether you are replacing or patching.
3. **Insert** `results` with `race_scores` JSON **R1…Rn** in the format your ingestion path and `api.py` expect (WC: unbracketed cells + penalty codes; other regattas: follow existing ingestion / `DATA_FORMAT_SPECIFICATIONS.md`).
4. **Recalculate** the fleet block:
   - **WC Dinghy Champs** (`WC_DINGHY_CHAMPS_REGATTA_SLUG`): `_recalculate_fleet_block_scoring_and_ranks` (WC engine).
   - **Other regattas:** same function routes to **legacy** scoring — see `api.py`; still run after cell edits so totals/netts/ranks persist.

### 4.2 Correction passes

1. **One concern per change** where possible.
2. After **any** change to `race_scores` or identity fields: **recalc** that block again.
3. Refresh **`regatta_blocks`** metadata (`races_sailed`, `discard_count`, `to_count`, `block_label_raw` where used) after recalc.

### 4.3 WC deploy scripts (repo examples)

- **`sailingsa/deploy/fix_wc_2026_<fleet>_*.py`**: sheet arrays + `EXPECTED_NETT`, then recalc, then assert nett (± tolerance).
- Server: `PYTHONPATH=/var/www/sailingsa/api:/var/www/sailingsa`, `DB_URL` from systemd env.

Non-WC historical loads should follow the **same §1–3 and §5–6**; reuse patterns (checksum arrays, one block per script) even if the filename is not `fix_wc_*`.

---

## 5. Checksums (before calling a fleet “final”)

Applies to **parsed, historical, and preloaded** loads whenever you have an authoritative source:

1. **Nett (and total if published):** After recalc, compare to the **official** source; fail automation if mismatch beyond tolerance (~0.06).
2. **Entries** and **races sailed** match the source.
3. **Discards** match the scoring system for that event (WC: see `api.py` WC block).
4. Spot-check discards in the UI for one row if unsure.

---

## 6. What not to do

- Do not set display names from comma **`full_name`** alone when `first_name` / `last_name` exist.
- Do not skip **recalc** after editing `race_scores` for a block that uses the scoring pipeline.
- Do not invent SAS rows; fix **`sas_id_personal`** only under explicit product rules.

---

## 7. Related code

- Scoring / recalc: `api.py` — `_recalculate_fleet_block_scoring_and_ranks` (WC vs legacy by `regatta_id`).
- WC helpers: `_wc_points_for_race_cell`, etc.
- WC one-off recalc all blocks: `sailingsa/deploy/recalc_wc_dinghy_champs_blocks_once.py`.
- WC examples: `sailingsa/deploy/fix_wc_2026_optimist_a_18.py`, `fix_wc_2026_optimist_b_8.py`, `fix_wc_2026_sonnet_14.py`.
- Data shapes: `docs/DATA_FORMAT_SPECIFICATIONS.md` (and related results docs).

---

*Covers parsed pipelines, historical regattas, and preloaded WC workflows (names, SAS links, checksums).*
