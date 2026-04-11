# Issue: WC Dinghy Champs — placeholder result rows on public sheet

## Summary

Pre-seeded `results` rows (rank slots with only block default class, e.g. “420”, and no sailor identity) were visible on **the same URL** as the live results sheet for everyone. That broke the intended model: **input-only** via NEW/Late strip + **Hold** (super-admin), and **Add** (future) before a row exists in the scored table.

## Policy

- **Public / logged-in non-super-admin:** No editable grid, no Hold strip — read-only fleet tables only.
- **Super-admin:** Editable grid + `.wc-late-entry-strip` (Hold, on-hold list). Strip is hidden via CSS unless `regatta-page--super-admin-edit`.
- **Do not change** `sailingsa/frontend/public/*` for WC pilot behaviour; behaviour is driven by **`api.py`** (sheet HTML + `/api/regatta/{id}`).

## Fix (implemented)

- `_wc_result_row_is_placeholder_for_display()` — rows with no sail, no helm/crew (incl. temp ids), no club, no meta, no race scores, no total/nett count as placeholders.
- **Fleet HTML** (`_render_result_sheet_fleet`): filter those rows for `WC_DINGHY_CHAMPS_REGATTA_SLUG`, re-sort by stored rank, **display ranks 1…n** consecutively.
- **`GET /api/regatta/{id}`**: same filter for that regatta so JSON clients match the sheet.
- **Entries** count on the sailed line uses filtered row count for WC.

## Follow-up (not done here)

- **DB cleanup:** Optionally `DELETE` placeholder `results` rows server-side so `rank` in DB matches display (recalc job).
- **Step 3 — Add:** Promote hold or strip into a class/block via existing late-entry create endpoint; refresh fleet section.
- **Delete row** workflow: per user, later.

## Regatta slug

`live-2026-wc-dinghy-champs-sbyc` (`WC_DINGHY_CHAMPS_REGATTA_SLUG` in `api.py`).
