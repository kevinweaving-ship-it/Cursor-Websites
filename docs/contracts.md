# Final Glue + Guardrails — API/UI Contracts (Last‑Mile Checklist)

This one‑pager captures the operational guardrails needed so DTOs, imports, edits, and provenance behave reliably across the stack.

## A) Naming, Enums, Validation

- **Canonical enums (tables, not magic strings)**
  - `scoring_codes` (DNC, DNS, DNF, DSQ, OCS, BFD, UFD, RET, RDG, DPI …)
  - `scoring_systems` (low_point, appendix_a_alt, average_laps, pursuit)
  - `role_categories` (Examiner, Safety, Coaching, Instructor)
  - `age_bands` (U13, U16, U19, Open, Masters)
- **Normalisation rules (server‑side)**
  - Names → trim, collapse spaces, Title Case; store `search_name` lower/diacritic‑stripped.
  - Sail numbers → strip spaces, unique within class scope; store raw alongside normalised.
  - Decimals → accept `,` or `.`; persist as `numeric(6,2)`; transport as strings (e.g., "4.4").

## B) Discards & Ties (sheet‑accurate)

- `discard_profiles` table (e.g., "1 of 5", "2 of 8–10", "3 of 11–12"), attach to `fleets`.
- `tie_break_policy` on `fleets` (Appendix A default).
- If the sheet provides totals/ranks, store them; compute only when missing. Always keep `tiebreak_notes`.

## C) Import Pipeline Contracts

- **Dry‑run**: `POST /imports/parse?dryRun=true` → returns a diff (entries/races/cells) with an idempotency key.
- **Commit**: `POST /imports/commit` with the same key to write.
- **Idempotency**: Same checksum + parser version = no‑op.
- **Provenance**: `source_mappings` required per inserted cell (locator like `pdf:p3:r12:c8`).

## D) Concurrency & Safety

- Optimistic locking: `row_version` on `race_results`, `entries`, `series_results`.
- Bulk ops (imports) use a single transaction + `FOR UPDATE` on the `fleets` row.
- Cross‑parent checks everywhere (return `CROSS_REGATTA_LEAK` on violation).

## E) Lookups & UX Data Feeds

- Typeahead endpoints (paginated, 10–15 min TTL, ETag):
  - `/lookup/people?q=weav&limit=20`
  - `/lookup/clubs?q=hyc`
  - `/lookup/sail-numbers?classId=OPTIMIST&q=1556`
- Include the alias that matched so the UI can show “Matched via ‘Weaving, T.’”.

## F) Data Quality & Drift Detection

- Per‑entry checksum: `sum(points)` vs `series_results.total_points`; flag mismatch.
- Race coverage: each `entry` has exactly one `race_result` per defined race.
- Decimal integrity: forbid rounding on API; accept only string decimals or sanctioned codes.

## G) People Merging & Duplicates

- Merge endpoint moves all FKs loser → winner in one TX; append old names to `name_aliases`.
- Guard merges when both have consented public details and conflicting emails/DoB.

## H) POPIA / Privacy Switches

- Field‑level suppression when `consent_public_profile=false` (hide email/phone/DoB) in public API.
- `change_log` audit (who, when, table→pk, before/after JSON; redact private fields), optional `source_id`.

## I) Timezones & i18n

- Store timestamps in UTC; render in local tz (Africa/Johannesburg).
- Numbers: API always uses `.`; UI may show locale but must send back `.`.

## J) Performance & Indexing

- Hot indexes:
  - `race_results (race_id, entry_id)`
  - `entries (fleet_id, sail_number_id)`
  - `people (search_name)`
  - `person_roles (person_id, role_id, valid_from)`
- Views (materialise if needed): `vw_fleet_scoreboard`, `vw_race_cells`, `vw_person_summary`.

## K) Seeding Essentials

- `classes`: Optimist, 420, ILCA 4/6/7, 29er, 470 … (`is_two_person`, crew min/max).
- `roles` with `rank_order` (Senior → Junior).
- `scoring_codes`, `scoring_systems`, common `discard_profiles`.
- `country_flags` cache (ISO2 → flag path).

## L) Error Taxonomy (machine codes)

- `CONFLICT_VERSION`, `CONFLICT_DUPLICATE`, `INVALID_DECIMAL`, `INVALID_CODE`,
  `CROSS_REGATTA_LEAK`, `PROVENANCE_REQUIRED`, `NOT_FOUND`, `FORBIDDEN`.
- Consistent JSON: `{ code, message, details? }`.

## M) Backups, Staging, Migrations

- Two DBs: prod, staging. Early imports land on staging first.
- Nightly logical backups; PITR window ≥ 7 days.
- Migrations forward‑only; reversible data fixes as scripts, not rollbacks.

## N) CI/CD Scaffolding

- Contract tests for DTOs (scoreboard GET, race PATCH).
- Migration smoke test on empty DB + seed.
- Parser golden files (small PDFs/HTML): expected JSON + DB diff.

## O) Accessibility & Resilience

- Race grid keyboard‑editable, clear focus, error toasts.
- Undo (client) + server audit = one‑click revert.

## P) Admin Guardrails

- `regattas.status`: `draft|published` controls public exposure.
- Lock fleets when results are final; admin can unlock with reason.

---

If desired, we can ship this with:
- `/docs/contracts.md` (this file)
- seed SQL for classes/roles/scoring codes/discard profiles
- 3 SQL views: `vw_fleet_scoreboard`, `vw_race_cells`, `vw_person_summary`
