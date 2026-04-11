# Regatta results (WC examples + deploy index) — read this first

**Do not guess the workflow.** The **canonical rules** for **all** regatta result ingestion — parsed imports, **historical** regattas, and preloaded events — are in:

### **`docs/PRELOADED_REGATTA_RESULTS_RULES.md`**

*(Despite the filename, that doc is scoped to **any** `results` load, not only preloads.)*

Use it every time you:

- Parse or import **any** regatta into `results` / `regatta_blocks`
- Backfill or fix **historical** events
- Load or fix **R1–Rn** for preloaded events (e.g. `live-2026-wc-dinghy-champs-sbyc`)
- Apply **final scores**, **checksums**, **SAS links**, or **helm/crew display names** (first word of `first_name` + `last_name`)

**Also required for live ops:** `SSH_LIVE.md` (DB URL, paths, `venv` Python).

## Scripts (WC Dinghy Champs — patterns you can mirror elsewhere)

| Script | Purpose |
|--------|---------|
| `recalc_wc_dinghy_champs_blocks_once.py` | Recalc **all** WC blocks after DB edits |
| `fix_wc_2026_optimist_a_18.py` | Fleet reload: sheet + `EXPECTED_NETT` |
| `fix_wc_2026_optimist_b_8.py` | Same pattern, 8 entries |
| `fix_wc_2026_sonnet_14.py` | Sonnet, helm + crew |

Run on server with `PYTHONPATH=/var/www/sailingsa/api:/var/www/sailingsa` and `DB_URL` from `sailingsa-api.service` (see `SSH_LIVE.md`).

## API

- **WC** slug: `api.py` → `_recalculate_fleet_block_scoring_and_ranks` uses WC engine.
- **Other regattas:** same entry point → **legacy** scoring path — see `docs/PRELOADED_REGATTA_RESULTS_RULES.md` §4.
