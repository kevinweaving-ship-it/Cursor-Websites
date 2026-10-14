# SailingSA club self-service — Step 3 plan (for approval)

**Status:** Step 3 plan complete. Phase 1 implementation is on `cursor/club-phase1-permissions-045e` (live 81k `api.py` is the deploy base). Phases 2–5 not started.

**Date:** 14 October 2026.

**Depends on:** Step 1 `docs/CLUB_EVENT_ARCHITECTURE_INVENTORY.md`, Step 2 `docs/CLUB_EVENT_PLATFORM_MATRIX.md`.

**Ask:** Approve the phases below before any implementation.

---

## Verdict

Build a **club-hosted workflow on the tables that already publish**. Do not add a parallel event product.

A `club_admin` / `club_manager` scoped to `user_accounts.admin_club_id` can: confirm or create a hosted event, declare fleets, take SAS-ID entries, upload Sailwave HTML/CSV, validate, set Provisional/Final, and correct scores. Public `/regatta/{slug}` and sailor profiles update **automatically** because they already read `results`.

**Preserve:** all current public reads, SAS scrape → `events`, ops ingest scripts, admin review, locked iframe sheets, status-line wording, and the **three-slug scoring pilot** (`club-score-edit.js` on Cape Classic, Dart 18 Nationals, Dam Bottle Sprints).

**Do not:** rebuild Appendix A, parse `.blw`, run Windows messaging on the server, activate the unused `entries` table in v1, deploy git `api.py` (~27k) over live `/var/www/sailingsa/api/api.py` (81 476), edit master header, or edit locked `class-results.html` / `results.html`.

---

## End-to-end workflow (target)

```
club officer logs in
    → GET /auth/session  (role + admin_club_id)
    → club home: hosted calendar + results

1. Event
    claim scraped events row  OR  create events + regattas
    host_club_id := admin_club_id
    declare classes → regatta_blocks (no new event_classes table)

2. Registration (SAS ID)
    sailor self-enter  OR  club add
    write results rows (Youth Nats template), raced=TRUE, empty race_scores
    resolve sas_id_personal; else temp_people + review

3. Score off-platform
    club scores in Sailwave (unchanged)

4. Upload
    POST preview HTML/CSV → class resolve + checksums (no write)
    POST commit → UPDATE/INSERT results, imports_log, as_at_time
    never DELETE result rows; never rewrite start_date/end_date from file time

5. Publish
    PATCH result_status Provisional|Final + as_at_time
    GET /regatta/{slug} and sailor pages already serve the rows

6. Corrections
    re-upload (UPDATE by match key)
    three-slug live PATCH /race + /fleet-races stays as-is
    other slugs: upload or super_admin PATCH, not a new general score UI
```

Actor rules (HalSail ladder, mapped to what live already has):

| Live role | May |
| --- | --- |
| `sailor` | Enter own SAS ID on an open hosted event; edit own media |
| `club_admin` / `club_manager` | All writes for `regattas.host_club_id == admin_club_id` |
| `super_admin` (and live SAS `21172`) | Everything; reassign host; approve aliases |
| `admin` | Git/`admin_api.py` still list this string; live count is **0** — do not depend on it |

---

## Preserve list (non-negotiable)

| Item | How we preserve it |
| --- | --- |
| Three-slug pilot | Keep hardcoded path allowlist and live includes (`api.py` 73440/73448, `hmyc-dam-bottle-live-boot.js` 1550). Do **not** add slugs. After Phase 1, `canScore()` uses real `admin_club_id` (fixes fall-open without changing who can edit those three pages). |
| Live `PATCH /api/result/{id}/race` + `/fleet-races` | Leave guards as-is (`admin_club_id == host_club_id` or super_admin / 21172). |
| SAS scrape → `events` | `load_events_csv_to_db.py` remains the calendar upsert. Club create uses a distinct `origin`. |
| Ops ingest scripts | Keep `results_ingestion_common.py` as the shared resolver. New HTTP ingest **calls** it; does not replace scripts. |
| Public publish | No change to `GET /regatta/{slug}`, class pages, results-summary, sitemap. |
| Status line | Only `Provisional` \| `Final` + `as_at_time`. Wording locked (`docs/RESULTS_HTML_STATUS_LINE_RULE.md`). Do not map `Unknown`. |
| Slug stability | Never rename an existing `regatta_id`. |
| Locked sheets | Do not edit `class-results.html` / `results.html` without `override lock`. |
| Master header | Do not edit `.admin-v10-second-header` / `blank-landing-header.js`. |
| Design system | Club UI uses `.container`, `.card`, `.table`, `buildMasterPageLayout` only. |
| Live api.py | Implementation must patch **live 81k**, then mirror into git. Never overwrite live with workspace `api.py`. |
| SAS `21172` hard-allow | Leave unless a separate security ticket removes it. |

Before any `api.py` edit: `bash sailingsa/deploy/pre-change-backup.sh` and confirm the server tarball exists.

---

## Exact database changes

Reuse first. New tables only where reuse would create a second source of truth.

### Reuse as-is

| Table | Role in this workflow |
| --- | --- |
| `user_accounts.role`, `admin_club_id` | ACL |
| `user_sessions` | Cookie session |
| `events` | Calendar card; `host_club_id`, `regatta_id`, `nor_url`, `si_url` already live |
| `regattas` | Results event; `host_club_id`, `result_status`, `as_at_time`, `source_url`, `file_type`, `doc_hash`, `import_status` |
| `regatta_blocks` | Fleets / classes (create **before** first race, as Youth Nats already does) |
| `results` | Entry **and** score row (`raced`, `helm_sa_sailing_id`, `race_scores` JSONB) |
| `classes`, `class_aliases` | Resolve only; never auto-insert classes |
| `sas_id_personal`, `temp_people` | Identity |
| `ingestion_issues` | Unknown class / blocked ingest |
| `imports_log` | Per-upload audit (`regatta_id`, `source_file`, `imported_by`, row counts) |
| `clubs` | `admin_club_id` / `host_club_id` |

### Do not use in v1

| Table | Why |
| --- | --- |
| `entries` | Live 51 rows; `results.entry_id` always NULL. Dual-write would desync publish. Revisit only after `results` entry flow is stable. |
| `result_participants`, `result_crew`, `sailing_id`, `sa_ids` | **Absent** on live. Do not write them. |

### Additive columns (nullable, default-safe)

Apply only if missing on live (check `information_schema` at implement time).

| Table.column | Type | Purpose |
| --- | --- | --- |
| `events.origin` | `text` default `'sas_scrape'` | `'sas_scrape'` \| `'club'` so the daily scrape does not upsert-clobber club-created rows |
| `events.created_by_sas_id` | `text` null | Audit |
| `events.entry_open` | `boolean` default `false` | Sailor self-enter gate |
| `regattas.origin` | `text` default `'ops_ingest'` | `'ops_ingest'` \| `'club'` |
| `regattas.created_by_sas_id` | `text` null | Audit |
| `results.entry_source` | `text` null | `'club_entry'` \| `'sailor_self'` \| `'sailwave_ingest'` \| `'ops'` |

No new `event_classes` table: a class on an upcoming event **is** a `regatta_blocks` row (`class_id` required, `races_sailed` 0 until ingest).

Slug for **new** club-created regattas follows the **live 2026 pilot** pattern, not the older numbered doc:

`{YYYY-MM-DD}-{club_abbrev}-{event-slug}`  
Example: `2026-09-13-zvyc-cape-classic`

Allocate `regatta_number` via existing `_next_regatta_number`. Collision: append `-2`. Never rewrite historical `{number}-{year}-…` slugs.

---

## Exact API changes

All new writes: session cookie or `?session=`; `_require_super_admin` **or** `_session_can_edit_regatta_scores` (live 31140) / equivalent for events (`admin_club_id == events.host_club_id`).

### Phase 1 — session + security (no new product UI)

| Change | Location | Notes |
| --- | --- | --- |
| Return `admin_club_id`, `is_club_admin` | `GET /auth/session` git 19248 / live 42034 | Frontend `club-score-edit.js` `canScore()` already reads this |
| Port live helpers into git **without** deleting live-only routes | `_session_role_is_club_admin` 31079, `_session_admin_club_id` 31084, `_session_can_edit_regatta_scores` 31140 | Git currently has none |
| Auth-gate unauthenticated writes | `POST /api/id/temp` 13758, `/api/id/promote` 13775, `/api/result/attach-person` 13793 / live 33576, `/api/result/{id}/set_person` 13844 | Require super_admin (or club host if the result’s regatta matches). `attach-person` must **not** INSERT `result_participants` (table missing). Write `helm_sa_sailing_id` / `crew_sa_sailing_id` instead |
| `GET /api/club/me` | New | `{ role, admin_club_id, club_abbrev }` |

### Phase 2 — event + fleets

| Route | Body / rules |
| --- | --- |
| `GET /api/club/me/events` | Union: `events.host_club_id` + `regattas.host_club_id` for this club |
| `POST /api/club/events` | `title, start_date, end_date, venue_text?, nor_url?, si_url?, class_ids[]`. Inserts `events` (`origin='club'`) **and** `regattas` + one `regatta_blocks` per class. `host_club_id` forced from session — **not** from the body |
| `POST /api/club/events/{event_id}/claim` | Scraped row only; sets `host_club_id` if null **or** already this club. Creates `regattas` if `regatta_id` is null. Super_admin can reassign (existing `POST /admin/review/assign-event-host` 8658 / live 26004 stays) |
| `PATCH /api/club/events/{event_id}` | title, dates, NOR/SI, `entry_open`. Cannot change `host_club_id` |
| `POST /api/club/regattas/{regatta_id}/classes` | `{ class_id }` or alias string → resolve; insert `regatta_blocks`. Fail if class missing or `is_race_class` is false |
| `PATCH /api/super-admin/calendar-event/{id}` | Implement the route hub JS already calls (`breaking-news-card.js` 4039). Super_admin only. Separate from club routes |

### Phase 3 — SAS-ID registration

| Route | Who | Writes |
| --- | --- | --- |
| `POST /api/club/regattas/{id}/entries` | Club host | One or many `{ sas_id?, helm_name, crew_sas_id?, sail_number, class_id, club_id? }`. Resolve SAS ID; insert `results` with empty `race_scores`, `raced=TRUE`, `entry_source='club_entry'` |
| `POST /api/regattas/{id}/enter` | Logged-in sailor | `class_id`, `sail_number`, optional crew SAS. `sas_id` **from session only**. Requires `events.entry_open` |
| `DELETE /api/club/regattas/{id}/entries/{result_id}` | Club host | Allowed only if `race_scores` is empty/`{}`. Never delete scored rows |
| Existing `GET /api/regatta/{id}/class-entries` 16457 | Public | Unchanged (counts `raced IS TRUE`) |

`POST /api/register-account` remains **login signup**, not event entry.

### Phase 4 — Sailwave upload + validation

| Route | Behaviour |
| --- | --- |
| `POST /api/club/regattas/{id}/ingest/preview` | Multipart `file` (`text/html` or `text/csv`, max ~2 MB). Parse places/points. Resolve classes via `results_ingestion_common.resolve_class_id`. Checksum nett vs total. Return `{ fleets, rows, unknown_classes, unmatched_sailors, warnings }`. **No DB write** |
| `POST /api/club/regattas/{id}/ingest/commit` | Same file + preview token (hash of file). Apply UPDATE-or-INSERT by match key `(regatta_id, block_id, sail_number, helm_name)` preferring existing `result_id`. Set `race_scores`, totals, `rank`, `file_type`, `doc_hash`, `as_at_time` (from sheet or upload clock — **not** into `start_date`/`end_date`). Log `imports_log`. Unknown class → `ingestion_issues` + **abort that fleet** (existing hard-fail) |
| Reject | `.blw`, PDF, images, exe. PDF stays ops-only |

Parser: new module called by HTTP **and** optional CLI, wrapping `results_ingestion_common.py`. Do not fork class rules.

### Phase 5 — publishing + corrections (mostly existing)

| Action | Mechanism |
| --- | --- |
| Publish | `PATCH /api/club/regattas/{id}/result-status` `{ result_status: Provisional\|Final, as_at_time? }`. Pages already render the locked sentence |
| Re-upload | Phase 4 commit UPDATE path |
| Three-slug inline edit | **Unchanged** live JS + PATCH |
| Other slugs inline | Not in v1 (avoids generalising the pilot) |
| Super-admin row edit | Existing `PATCH /api/result/{id}` |
| Sailor profiles | No new job. `GET /api/member/{sa_id}/results` 12978 and `/sailor/{slug}` already join `helm_sa_sailing_id` / `crew_sa_sailing_id`. Ingest that sets those columns updates profiles on next read |
| Sitemap | Existing builder includes `/regatta/{id}` when results exist |

---

## Frontend (club controls)

New club home only — not a new CSS system.

- Logged-in club officer: card on club page or `/club/{slug}?manage=1` using `buildMasterPageLayout`.
- Tables for events, fleets, entries, last ingest preview.
- Reuse `login.html`, `js/session.js`, `js/api.js`. After Phase 1, `sailingSessionIsSuperAdmin` stays; add `sailingSessionClubId()` next to it (491–499).
- **Do not** ship `club-score-edit.js` to other slugs.
- Hub SA calendar save keeps calling `calendar-event` once Phase 2 implements it.

---

## Security fixes (must ship with Phase 1)

1. Session omits `admin_club_id` → live UI fall-open. Add the field.
2. Four write routes have **no session**. Gate them. Stop `attach-person` writing a missing table.
3. Club writes **ignore** client-supplied `host_club_id` / `admin_club_id`.
4. Upload: type allowlist, size cap, preview-hash bind, no path write outside a staging dir, store `doc_hash`.
5. `entry_open` default false so random sailors cannot enter a claimed event until the club opens it.
6. Do not expose other clubs’ `admin_club_id` lists.
7. Keep hostname gate on `/admin/*` (`vm103zuex.yourlocaldomain.com`).
8. Leave SAS `21172` bypass documented; do not copy it onto new club routes.

---

## Implementation dependencies

| Depends on | Why |
| --- | --- |
| Live `api.py` 81k as the edit base | Git 27k is missing the pilot |
| `results_ingestion_common.py` | Class resolve, `is_race_class`, `ingestion_issues` |
| `classes` / `class_aliases` populated | Upload fail-closed |
| Live roles already assigned (ZVYC club_admin, HMYC club_manager) | Pilot clubs can dogfood Phases 2–4 |
| `pre-change-backup.sh` | Mandatory before API edits |
| Design-system + header + sheet locks | UI/scope constraints |
| Youth Nats entry template | `results` as entry row |
| Locked status-line + RESULTS_LINE rules | Publish values |

Out of v1: payments, revSPORT sync, HalSail API, Manage2Sail, `.blw`, general score UI, `entries` table, notice board, SMS.

---

## Migration / regression risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Deploying git `api.py` wipes live pilots | Critical | Patch live file; rsync that file back to git; never push 27k over 81k |
| Scrape upsert overwrites club-created `events` | High | `origin='club'` + loader skip; unique key stays `(source, source_event_id)` for scrape only |
| Duplicate `events` + `regattas` for one weekend | High | Claim-first UI; match on dates+host+title before create |
| Slug collision or rewrite | High | Date-club-slug for new only; `ON CONFLICT` abort; never UPDATE `regatta_id` |
| Re-ingest DELETE/reinsert drops `result_id`s / profile links | High | UPDATE only (`docs/README_results_table.md`) |
| Unknown Sailwave class labels | High | Preview + `class_aliases` + abort fleet |
| Ingest writes `start_date` from upload time | High | Explicitly forbidden (`docs/README_RESULTS_INGESTION.md`) |
| Club claims another club’s scraped event | Medium | Claim only if `host_club_id` is null or self; else super_admin |
| Generalising score-edit JS | Medium | Slug allowlist stays three strings |
| `entries` vs `results` dual write | Medium | Do not touch `entries` in v1 |
| Auth-gating unused ID routes breaks an old tool | Medium | Super_admin still allowed; confirm no public caller first |
| Session now includes `admin_club_id` | Low | Integer club id only |
| Standing-list stale after ingest | Low | Existing recalc scripts remain ops; not blocking publish |
| Remaining invalid `result_status` rows | Low | Do not auto-map (`docs/RESULTS_LINE_CLEANUP_COMPLETE.md`) |
| Frontend drift vs live | Medium | Match live first (`docs/AVOID_FRONTEND_DRIFT_AND_WRONG_LAYER.md`) |

---

## Phased implementation plan (approval gates)

Each phase is a separate implement request. Do not start Phase N+1 until the previous phase is on live and the three-slug pilot still works.

### Phase 1 — Permissions + security
**Approve to implement first.**

- Session payload + git/live helper alignment.
- Auth on the four open write routes; fix `attach-person` target columns.
- `GET /api/club/me`.
- `club-score-edit.js` fall-open gone **because session is complete**, not because slugs change.
- Verify: ZVYC/HMYC still edit the three slugs; other clubs still 403; public pages unchanged.

### Phase 2 — Event creation + classes/fleets
- Claim / create / patch event; `regatta_blocks` for classes; implement missing `calendar-event` for super_admin hub.
- Club UI: events table + class picker (existing `GET /api/classes`).
- Verify: scrape still loads; club-created rows not clobbered; no slug changes on existing 478 regattas.

### Phase 3 — SAS-ID registration
- Club add + sailor self-enter (`entry_open`).
- Writes `results` only.
- Verify: `GET /api/regatta/{id}/class-entries` counts; sailor cannot enter another SAS ID; empty-score delete only.

### Phase 4 — Sailwave HTML/CSV upload + validation
- Preview / commit; `imports_log`; fail closed on class.
- Verify on a **non-pilot** test slug first, then optionally on a copy of a pilot file without changing pilot JS.
- Verify: dates unchanged; status line; no DELETE.

### Phase 5 — Publishing, corrections, profiles
- Club `result_status` PATCH.
- Document re-upload as the correction path for non-pilot events.
- Confirm sailor `/sailor/{slug}` and media/results tabs pick up new IDs with no extra job.
- Pilot PATCH paths still the correction UI for the three slugs.

### Phase 6 (optional, later approval)
- Merge live `api.py` into git so the 27k/81k split ends.
- HalSail pull if a club asks.
- Revisit `entries` table.
- Payments / revSPORT link.

---

## Success test (after Phase 5, still plan)

A ZVYC `club_admin` (`admin_club_id=3`) or HMYC `club_manager` (`admin_club_id=98`) can run a **new** weekend event on SailingSA without an ops script, while Cape Classic / Dart 18 / Dam Bottle keep their current inline score boxes.

---

## Approval

Reply with which phases to implement (recommended: **Phase 1 only** next). This document is the specification; it is not a licence to code until you say so.
