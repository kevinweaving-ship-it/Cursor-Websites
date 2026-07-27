# Project 6 — Goals, Scope, and Architecture (Living Doc)

This document captures the core goals, entity model, data contracts, and the delivery plan for the SA Sailing regatta platform. It is a living document and will be updated as we progress.

## Core Goals

- **Accurate regatta storage**
  - Preserve race-by-race values including decimals (e.g., 3.4, 4.4) with exact points from source sheets.
- **Single source of truth**
  - Normalised People, Clubs, Classes, Boats, Sail Numbers.
- **Normalised roles & qualifications**
  - Replace 27 booleans with `roles` + `person_roles` time-bound assignments.
- **Provenance & auditing**
  - Every stored value traceable to a source sheet/scrape with locators.
- **POPIA controls**
  - `people.consent_public_profile` and view-layer respect for privacy.

## Entity Overview (ERD in Words)

- **People** have many **roles/qualifications** and belong to a **primary club**.
- A **Regatta** (hosted at a **club**) has one or more **Fleets** (by **Class**).
- **Entries** represent competing boats (sail number, helm, optional crew).
- Each **Race** has a **Race Result** per entry.
- **Series Results** compute `total_points` and `net_points` with discards per fleet.
- **Sail Numbers** and **Boats** are versioned to retain history.
- **Sources → Artifacts → Mappings** track provenance for every stored value.

## Data Model (Tables & Columns)

### 1) Directory / Reference

- **people**: `person_id (PK)`, names, DoB, `sa_sailing_id (unique, nullable)`, `primary_club_id`, contacts, `consent_public_profile`, timestamps; `search_name` (generated, indexed) for fast lookup.
- **clubs**: `club_id (PK)`, `club_name (unique)`, `short_name`, `province`, `country_iso2`, `lat`, `lng`, `website_url`, timestamps.
- **classes**: `class_id (PK)`, `class_name (unique)`, `is_two_person`, `min_crew`, `max_crew`, `world_sailing_code`, timestamps.
- **boats** (optional, physical hulls): `boat_id (PK)`, `class_id`, hull metadata, `current_owner_person_id`, timestamps.
- **sail_numbers**: `sail_number_id (PK)`, `class_id`, `sail_number` (unique within class/time), `allocated_to_person_id`, `allocated_from/to`, `status`, timestamps; unique `(class_id, sail_number, allocated_from)` for history.

### 2) Events & Structure

- **regattas**: `regatta_id (PK)`, `title`, `host_club_id`, `province`, `country_iso2`, `start_date`, `end_date`, `organiser`, `notice_board_url`, `official_results_url`, `status`, timestamps.
- **fleets**: `fleet_id (PK)`, `regatta_id`, `class_id`, `fleet_name`, `age_band`, `target_races`, `scoring_system`, timestamps.
- **races**: `race_id (PK)`, `fleet_id`, `race_number`, `race_date_time`, `course_notes`, timestamps; unique `(fleet_id, race_number)`.

### 3) Entries & Results

- **entries**: `entry_id (PK)`, `fleet_id`, `boat_id?`, `sail_number_id?`, `helm_id`, `crew_id?`, `club_id?`, `country_iso2?`, `sail_number_text` (raw), `entry_notes?`, timestamps. (Extensible `entry_crew` for >1 crew.)
- **race_results**: `race_result_id (PK)`, `race_id`, `entry_id`, `finish_place numeric(6,2)?`, `elapsed_time_sec?`, `corrected_time_sec?`, `code?`, `points numeric(6,2)`, `penalty_points numeric(6,2) default 0`, `notes?`, timestamps; unique `(race_id,entry_id)`.
- **series_results**: `series_result_id (PK)`, `entry_id (unique per fleet)`, `races_sailed`, `discards_applied`, `total_points numeric(8,2)`, `net_points numeric(8,2)`, `rank numeric(6,2)`, `tiebreak_notes?`, timestamps.

### 4) Roles / Qualifications (Normalised)

- **roles**: `role_id (PK)`, `role_name (unique)`, `role_category`, `rank_order`, timestamps.
- **person_roles**: `person_role_id (PK)`, `person_id`, `role_id`, `valid_from/to`, `issuing_body?`, `credential_id?`, `notes?`, timestamps; unique `(person_id,role_id,valid_from)`.

### 5) Provenance & Auditing

- **sources**: `source_id (PK)`, `regatta_id?`, `source_type`, `source_url?`, `captured_at`, `parser_version?`, `checksum?`, `status`, timestamps.
- **source_artifacts**: `artifact_id (PK)`, `source_id`, `filename`, `mime_type`, `byte_size`, `storage_path`, timestamps.
- **source_mappings**: `mapping_id (PK)`, `source_id`, `target_table`, `target_pk`, `source_locator`, `raw_value`, `normalized_value`, timestamps.

### 6) Helpers

- **name_aliases**: aliasing for matching.
- **country_flags**: cached assets for UI.

## Scoring & Series Rules (Appendix A style)

- **Per-race points**: exact decimals from source; penalties recorded as given; do not infer.
- **Totals**: `total_points = SUM(points)`; **Nett** = `total_points - sum(discarded)`.
- **Discards**: progressive (5→1, 10→2, 15→3). Worst scores discarded; UI shows brackets for discarded.
- **Penalty codes**: store `code` and the points that appear on the sheet; no guessing.

## Provenance Workflow

1. **Import sheet** → insert into `sources` + `source_artifacts`.
2. **Parse header** → upsert `regattas`.
3. **Create fleets** per class.
4. **Create entries** with raw `sail_number_text` and mapped IDs where known.
5. **Create races** → ensure correct count per fleet.
6. **Insert race_results** from each R# cell → `points` = exact numeric shown.
7. **Insert series_results** from sheet totals/nett/rank + discards.
8. **Write source_mappings** for every stored cell (page/row/col or selector).

## POPIA & Privacy

- **Public view** respects `people.consent_public_profile`.
- Private/PII fields visible only to admin/authenticated roles.

## Views for UI

- **vw_fleet_scoreboard**: pivot race results (R1..Rn) + series totals for a fleet.
- **vw_person_summary**: profile with roles, aliases, recent regattas, best ranks.

## Indexing & Constraints (Integrity)

- `people(search_name)` for fuzzy lookup.
- Unique: `classes.class_name`, `clubs.club_name`.
- `sail_numbers` uniqueness per class/time `(class_id, sail_number, allocated_from)`.
- `race_results` unique `(race_id, entry_id)`; `races` unique `(fleet_id, race_number)`.
- Consider FK cascades vs soft deletes (to be agreed).

## Success Criteria (Acceptance)

- **Accuracy**: For selected regattas (e.g., 359), series totals and nett match the official sheet exactly; race-by-race decimals correctly preserved.
- **Traceability**: Each stored value has a `source_mappings` locator to the original artifact.
- **Searchability**: People lookup is fast and robust (aliases handled).
- **Privacy**: Public pages hide PII unless consented.
- **Admin UX**: Inline edits, club/class mapping, and ID matching are reliable.

## Non‑Goals (initially)

- No multi-tenant support.
- No automatic inference of points from codes (we store what the sheet says).
- No full-blown CMS; focus on results and directory accuracy first.

## Roadmap & Milestones

- **M1 — Data model readiness**
  - Create initial migration SQL for core tables + roles.
  - Seed `classes`, `roles` with `rank_order`.
  - Create `vw_fleet_scoreboard`, `vw_person_summary`.
- **M2 — Import & provenance**
  - Ingest selected regattas with `sources`/`artifacts`/`mappings`.
  - Run checksum audits and produce discrepancy reports.
- **M3 — Viewer polish**
  - Align header strip, table columns, score/penalty styling, responsive behavior.
  - Public viewer respects POPIA.
- **M4 — Admin tools**
  - Inline editor with safe endpoints, audit log, and role-protected access.
- **M5 — Deploy staging → production**
  - Reverse proxy, TLS, CORS, logging/monitoring, backups.

## Next Actions (me)

- Prepare initial migration SQL (`/migrations/0001_init.sql`) from this model.
- Create seed files (`/seeds/classes.sql`, `/seeds/roles.sql`).
- Stand up `vw_fleet_scoreboard` and validate against regatta 359.
- Keep this doc updated as decisions are made.
