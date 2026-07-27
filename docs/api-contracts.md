# API & UI Contracts — Routing, DTOs, Editing, Provenance (Cheat‑Sheet)

This doc encodes the 20‑point contract for moving data cleanly between Postgres and the HTML/admin pages. It is the source of truth for routes, payloads, locking, and edge cases.

## 1) IDs, Routing & URL Contracts

- **Canonical pathing (stable, bookmarkable):**
  - `/regattas/:regattaId`
  - `/regattas/:regattaId/fleets/:fleetId`
  - `/regattas/:regattaId/fleets/:fleetId/races/:raceNumber`
  - `/people/:personId` (sailor profile)
- **IDs, not labels**: Never trust display strings in URLs. Use numeric IDs (or short slugs + IDs) and re‑load rows from DB.
- **Link safety**: Any page that accepts an ID must 404 if the child does not belong to the parent (e.g., `fleets.regatta_id == :regattaId`).

## 2) View Models (DTOs) vs DB Rows

- **Fleet scoreboard DTO** (UI‑ready):
  - `regatta`, `fleet`, `races[]`, `entries[]`, pivot of `race_results` as `{ R1, R2, … }`, plus `series_results`.
  - Pre‑format decimals as strings ("4.4").
- **Admin entry editor DTO**:
  - `entry` + `lookup` sections: people, clubs, classes, sail_numbers, alias suggestions.
  - Avoid N+1; batch join server‑side.

## 3) Form Posting (Idempotent & Safe)

- **Upserts with versioning**: add `updated_at` (and/or `row_version` int). Reject on version mismatch with friendly merge message.
- **Idempotency keys**: `X-Idempotency-Key` on import endpoints to avoid duplicates.
- **Transactions**: per logical write (e.g., create race → insert `races`, then placeholder `race_results` → commit). Imports include `source_mappings` and rollback on parse error.

## 4) Decimal Handling

- **DB**: `numeric(6,2)` for points, finish_place, rank, totals.
- **Transport**: strings in JSON to avoid float drift ("4.4").
- **Validation**: accept `.` and `,` → normalise to `.` before save. Client never recomputes authoritative points.

## 5) Race Grid Editing

- **Cell key**: `{race_id}:{entry_id}`.
- **PATCH shape**:
```json
{
  "updates": [ { "raceId": 3210, "entryId": 9001, "points": "4.4", "code": "DNC", "note": "" } ],
  "sourceLocator": "pdf:p2:r14:c7"
}
```
- **Server merge**: Only present fields are updated, all within one TX. Response returns updated cells + recomputed `series_results`.

## 6) Creating Fleets, Entries, Races Without Duplicates

- **Uniqueness**:
  - `races`: unique `(fleet_id, race_number)`
  - `race_results`: unique `(race_id, entry_id)`
  - `sail_numbers`: unique `(class_id, sail_number)` or time‑sliced with `allocated_from`.
- **Create many**: `ON CONFLICT DO NOTHING` + report skipped.

## 7) Cross‑Page Lookups (Dropdowns & Typeahead)

- **Typeahead (paginated)**:
  - `/lookup/people?q=weav&classId=420`
  - `/lookup/clubs?q=hyc`
  - `/lookup/sail-numbers?classId=OPTIMIST&q=1556`
- **Alias expansion**: return canonical and matched alias.
- **Caching**: ETag + TTL 5–15 mins; invalidate on writes.

## 8) Provenance: Map Rows to Sheet Cells

- Every import write must insert `source_mappings` with:
  - `target_table`, `target_pk`, `source_locator` (e.g., `pdf:p3:r12:c8`), `raw_value`, `normalized_value`.
- **UI affordance**: "Jump to source" opens the artifact and highlights the locator.

## 9) Concurrency & Locking

- **Imports**: pessimistic locks while bulk editing a fleet.
- **Single cells**: optimistic locking via `row_version` on `race_results`.

## 10) Security, Roles & POPIA

- **Scopes**:
  - `viewer`: read public (respect `consent_public_profile`)
  - `club_official`: edit regattas they host
  - `data_admin`: import / mass‑edit / delete
- **Field‑level filtering**: hide PII if `consent_public_profile=false`.
- **Audit**: `change_log` with who/when/before/after JSON; reference `source_id` when applicable.

## 11) Error Taxonomy (for Clean UX)

- `CONFLICT_VERSION`, `CONFLICT_DUPLICATE`, `INVALID_DECIMAL`, `CROSS_REGATTA_LEAK`, `PROVENANCE_REQUIRED`.
- Return machine code + human message.

## 12) Import Pipeline (HTML/PDF → DB)

- **Stage 1**: `sources` + `source_artifacts` (checksum).
- **Stage 2**: parse regatta header → upsert `regattas`, `fleets`, `races`.
- **Stage 3**: entries + matching; minimal `people` when unknown.
- **Stage 4**: race cells → insert `race_results` with exact decimals; set `code`.
- **Stage 5**: series → copy totals/net/rank (don’t compute unless missing).
- **Idempotency**: same checksum + parser → no‑op.

## 13) Read Models (Views)

- `vw_fleet_scoreboard`: row per entry with `R1..Rn` + Totals + Nett + Rank.
- `vw_race_cells`: for fast cell updates and conflicts.
- `vw_person_summary`: profile, roles, aliases, recent regattas, best ranks.

## 14) Sorting & Ties

- `rank` numeric for calculations; `display_rank` for "=3".
- `series_results.tiebreak_notes` stores the reason (e.g., BCR over 12345).

## 15) Background Jobs & Notifications (Optional)

- Debounced recompute of `series_results` after grid edits.
- Data drift warnings if totals != sum(R1..Rn).

## 16) People Normalisation & Dedupe

- Identity merge replaces `old.person_id` → `new.person_id` across tables in a TX; add alias.
- Safeguards for POPIA: caution when both have consent and conflicting emails.

## 17) Client‑Side UX Contracts

- Dirty state on race cells; batch PATCH on blur / Ctrl+S.
- Local undo (last 20 edits) + server audit for revert.
- Import progress bars: fleets, entries, races, cells, totals.

## 18) Performance Tips

- Preload scoreboard with two queries: (1) fleet+races+entries (JOINed), (2) results+series (pivotted or view).
- Composite indexes where filtered/sorted often:
  - `race_results (race_id, entry_id)`
  - `entries (fleet_id, sail_number_id)`
  - `people (search_name)`
  - `person_roles (person_id, role_id, valid_from)`

## 19) Data Integrity Checks (Server‑Side)

- Validate parentage on save: `race_id ∈ fleet`, `entry_id ∈ fleet`.
- If `code` present, `points` must be present (store what sheet shows).
- On import close: per‑entry checksum (sum(points) == `series_results.total_points` when provided).

## 20) Minimal Payload Examples

- **GET scoreboard**
```json
{
  "regatta": { "id": 101, "title": "420 Nationals 2025", "startDate": "2025-10-10" },
  "fleet": { "id": 555, "className": "420", "races": [1,2,3,4,5] },
  "entries": [
    {
      "entryId": 9001,
      "sailNumber": "54789",
      "helm": "Timothy Weaving",
      "club": "HYC",
      "R": { "1":"3.4","2":"5.0","3":"1.0","4":"7.0","5":"4.4" },
      "totals": { "total":"20.8","net":"16.8","rank":"2" }
    }
  ]
}
```

- **PATCH race cells**
```json
{
  "updates": [
    { "raceId": 3210, "entryId": 9001, "points": "4.4", "code": null }
  ],
  "sourceLocator": "pdf:p2:r14:c7"
}
```
