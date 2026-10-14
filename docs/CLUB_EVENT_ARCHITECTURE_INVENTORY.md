# SailingSA club-event architecture — Step 1 inventory

**Status:** Plan only. No code, DB, or deploy. Competitor research (Step 2) not started.

**Date:** 14 October 2026. Source: this repo’s routes, scripts, and docs (no live `\d` this pass).

**Verdict:** SailingSA is a **publish-and-profile** site fed by **ops ingest** and a **SAS calendar scrape**. It is **not** a club event-management product. Clubs cannot log in as a club, create events, take entries, or score races.

---

## Status by domain

| Domain | Status | Exists | Partial / missing |
| --- | --- | --- | --- |
| Club permissions | **Missing** | `user_accounts.role` = `admin` \| `super_admin`; sailor session for own media | No `club_admin`, no `club_id` on session, officer columns on `sas_id_personal` are **not** ACL |
| Event creation | **Partial** | SAS scrape → `events`; scripts → `regattas` | No club/API create for calendar or regatta |
| Classes | **Exists** | `classes`, `class_aliases`, `is_race_class`; attached via `regatta_blocks` after ingest | No `event_classes` on upcoming `events` |
| Sailors | **Exists** | `sas_id_personal`, `/sailor/{slug}`, results IDs | Logged-in “my profile” tab plan not built (`docs/SAILOR_PROFILE_TABS_AND_LOGIN_PLAN.md`) |
| Registration / entries | **Missing** | `results` used as the entry list (ops scripts); live `entries` table unused by product | No online entry, payment, NOR/SI portal |
| Scoring | **Partial** | Ingested `race_scores` JSONB + Appendix A fields; super-admin `PATCH …/race` recalc | No club scoring UI; no HTTP results upload |
| Publishing | **Exists** | `/regatta/{slug}`, APIs, hub, sitemap once rows exist | No club-triggered publish step |
| Profile integration | **Partial** | Career + media from ingested helm/crew SA IDs | `events.regatta_id` often unmatched; no club-entry → profile |

---

## Two event layers (do not collapse)

```
sailing.org.za  --scrape-->  public.events   (calendar, NOR/SI URLs)
                                      | optional events.regatta_id
                                      v
ops PDF/sheet --ingest-->  public.regattas --> regatta_blocks --> results
                                      |
                                      +--> /regatta/{slug}  + sailor profiles
```

| Layer | Table | How created | Public read |
| --- | --- | --- | --- |
| Calendar | `public.events` | `load_events_csv_to_db.py` (CSV from SAS scrape) | `GET /events`, `GET /api/events`, club pages |
| Results | `public.regattas` | Ingestion scripts via `results_ingestion_common.py` | `GET /regatta/{slug}`, `GET /api/regatta/{id}` |

There is **no** `POST /api/events` and **no** create-regatta API.

---

## 1. Club permissions / auth

**Exists**

| Item | Location |
| --- | --- |
| Accounts | `public.user_accounts` (`sas_id`, `login_method`, `password_hash`, optional `role`) |
| Sessions | `public.user_sessions` (`session_id`, `account_id`, `sas_id`, cookie `session`) |
| Session / login / logout | `GET /auth/session`, `POST /auth/login`, `POST /auth/logout` — `api.py` |
| Account signup | `POST /api/register-account` — `login.html` (not event entry) |
| Facebook OAuth | `GET /auth/facebook`, `GET /auth/facebook/callback` |
| Role check | `_get_session_role`, `_require_super_admin` — `api.py` |
| Admin host gate | Many `/admin/*` also require live hostname |
| Frontend | `js/api.js` (`checkSession`), `js/session.js`, `login.html` |
| Nginx | `sailingsa/deploy/NGINX_AUTH_PROXY_FINAL.md` (`/auth/` → API) |

**Partial**

- `user_accounts.role` is used in code but omitted from some schema docs (`docs/SYSTEM_BASELINE_v1.md` column list vs `api.py`).
- Password-reset columns exist; **no** forgot-password route on main API.
- `POST /auth/register` is referenced in `js/api.js` and **not** implemented.
- `member_roles` + `roles` = SA qualifications (Instructor, Judge) — **display only** (`GET /api/member/{sa_id}/roles`).
- `sas_id_personal` commodore / secretary fields are **not** permission checks.

**Missing**

- Club-scoped role, `club_id` on session, “officer of club X may edit club X”.
- Club self-service for events, entries, or results.

**Who can write**

| Action | Who | Route |
| --- | --- | --- |
| Own media | Session `sas_id` match | `POST/PATCH/DELETE /api/member/{sa_id}/media*` |
| Assign `events.host_club_id` | `admin` or `super_admin` | `POST /admin/review/assign-event-host` |
| Patch result / race score | `super_admin` | `PATCH /api/result/{id}`, `PATCH /api/result/{id}/race` |
| Create club / patch regatta host | `super_admin` | `POST /api/super-admin/clubs`, `PATCH /api/super-admin/regatta/{id}/host-club` |
| Hub breaking-news badge | `super_admin` | `PATCH /api/super-admin/regatta/{id}/breaking-news-meta` (root `api.py`) |
| Create calendar event / upload results | Ops only | Scripts, not HTTP |

---

## 2. Event creation

**Exists**

- Scrape pipeline (script documented as `scrape_sas_events_list.py` — **not on this branch**; deploy: `sailingsa/deploy/run-daily-events-scrape.sh`).
- Loader: `load_events_csv_to_db.py` upsert on `(source, source_event_id)`.
- Public: `GET /events`, `GET /events/type/{slug}`, `GET /yearly-events`, `GET /api/events`, `GET /api/events/upcoming-window`, `GET /api/events/live-summary`.
- Admin: `GET /admin/events-audit`, `GET /admin/api/events`, `GET /admin/review/events-host`.
- Club page: `GET /club/{slug}` lists hosted `regattas` + upcoming `events` (`api.py` `serve_club_page`).
- Super-admin patches on **existing** `regattas` (name, host, header icons, WC fleets).

**Partial**

- `events.host_club_id` / `events.regatta_id` optional; matching is often **in-memory** on the events page (`docs/EVENTS_CALENDAR_MATCHING_DESIGN.md` — `sas_event_regatta_map` not built).
- Hub JS calls `PATCH /api/super-admin/calendar-event/{event_id}` — **no matching route** in workspace Python.
- `/events/series/{slug}` still notes-only (`docs/EVENT_SERIES_CANDIDATES.md`).
- `GET /api/open-regattas` is a stub (hard-coded number), not an entry API.

**Missing**

- Club or public form to create an event.
- Migrations cited as `database/migrations/145_events_table.sql` — **absent from git**.

**Docs:** `docs/EVENTS_TABLE_AND_SCRAPE.md`, `docs/EVENTS_PIPELINE_TRACE.md`, `docs/EVENTS_NEXT_STEPS.md`.

---

## 3. Classes

**Exists**

| Table | Role |
| --- | --- |
| `public.classes` | Canonical names; **`classes.class_name` is authoritative** (`docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md`) |
| `public.class_aliases` | Ingest aliases |
| `classes.is_race_class` | Family classes must not enter `results` |
| `public.regatta_blocks` | Fleet ↔ `class_id` after ingest |

Routes: `GET /classes`, `GET /class/{class_slug}`, `GET /api/classes`, `GET /api/class/{class_ref}`, `GET /regatta/{slug}/class-{class_slug}`, `GET /api/regatta/{id}/class-entries`, admin `GET /admin/review/classes`, `POST /admin/review/resolve-class`.

Likely classes on **calendar cards** are derived from a matched regatta’s results (`docs/EVENT_LIKELY_CLASSES_VALIDATION.md`), not stored on `events`.

**Missing:** junction table to declare classes on an upcoming event before results exist.

---

## 4. Sailors

**Exists**

| Table | Role |
| --- | --- |
| `public.sas_id_personal` | Master sailor registry (names, slugs, contact) |
| `public.temp_people` | Unmatched names (`helm_temp_id` / `crew_temp_id`) |
| `results.helm_sa_sailing_id` / `crew_sa_sailing_id` | Link to profiles |
| `public.sailor_public_mentions` | Media tab |

Routes: `GET /sailor/{slug}`, `GET /sailors`, `GET /api/sailor/resolve`, `GET /api/sailor/{id}`, `GET /api/member/{sa_id}/results`, `/public-mentions`, `/highlights`, `/activity`, `/roles`, `/hub-summary`. Frontend: `sailingsa/frontend/index.html` sailor tabs; `sailingsa/frontend/public/sailor.html`. Bio: `api/modules/sailor_bio.py`.

**Partial**

- Docs still mention `sailing_id` / `sa_ids`; production path is **`sas_id_personal`**.
- `docs/SAILOR_PROFILE_TABS_AND_LOGIN_PLAN.md` (logged-in default profile) — **not implemented**.
- Some ID helpers (`POST /api/result/attach-person`, `set_person`) have **no session check**.

**Missing:** club “register this sailor for this event” → auto profile.

**Docs:** `docs/README_SAILOR_PROFILE_SYSTEM.md`, `docs/README_sas_id_personal.md`, `docs/SAILORS_MEDIA_TAB_AND_MEDIA_SCORES.md`.

---

## 5. Registration / entries

**`POST /api/register-account` is user signup, not event entry.**

**Exists (ops)**

- Entrants live in **`results`** (often with `raced = TRUE` before scores). Template: `docs/REGATTA_375_ENTRY_PROCESS.md`.
- Per-class counts: `GET /api/regatta/{id}/class-entries` (filters `raced IS TRUE`).
- Calendar NOR/SI: `events.nor_url`, `events.si_url` (links only).

**Partial**

- Live DB has **`public.entries`** (`docs/SYSTEM_BASELINE_v1.md`: `entry_id`, `regatta_id`, `helm_sas_id`, …). Product and ingest **do not** use it as the entry list (`results.entry_id` FK exists in baseline; unused as a club product).
- `GET /api/open-regattas` stub.

**Missing:** online entry form, fees, waitlist, NOR/SI hosting as a workflow, club entry admin.

---

## 6. Scoring

**Exists**

| Layer | Storage |
| --- | --- |
| Per-race | `results.race_scores` JSONB (`R1`…; discards in parentheses) |
| Fleet header | `regatta_blocks.races_sailed`, `discard_count`, `to_count`, `scoring_system` (display: Appendix A) |
| Totals | `results.total_points_raw`, `nett_points_raw`, `rank` |
| Status line | `regattas.result_status` + `regattas.as_at_time` → `Results are [Provisional\|Final] as at …` (`docs/RESULTS_HTML_STATUS_LINE_RULE.md`) |

Primary path: PDF/sheet → script → `results_ingestion_common.py` (strict class resolve; **no shared scoring engine** — scripts supply precomputed scores).

**Partial**

- `PATCH /api/result/{id}/race` (`super_admin`): updates JSONB, recomputes fleet nett/rank. Discard rule in patch is `races_sailed // 5`, **not** necessarily `regatta_blocks.discard_count`.
- WC Dinghy Champs standalone HTML can inline-edit when super-admin (`WC_DINGHY_CHAMPS_REGATTA_SLUG` in `api.py`).
- Series: `standing_list` via `recalc_standings_after_upload.py` / `calculate_universal_standings.py` — **not** per-regatta scoring.

**Missing:** club scoring UI, HTTP upload of Sailwave/HTML/CSV, live scoring for all events.

**Locks:** do not auto-map remaining invalid `result_status` (`docs/RESULTS_LINE_CLEANUP_COMPLETE.md`). Do not edit locked iframe sheets without `override lock`.

---

## 7. Publishing

**Exists**

| Surface | Route / file |
| --- | --- |
| SEO regatta page | `GET /regatta/{slug}` — `serve_regatta_standalone` |
| Class page | `GET /regatta/{slug}/class-{class_slug}` |
| JSON | `GET /api/regatta/{id}`, `GET /api/regatta/{id}/results-summary` (root `api.py`), class results / podium |
| Locked iframes | `GET /regatta/results.html`, `…/class-results.html`, `…/podium.html` (static; fetch API) |
| Hub / Breaking News | `breaking-news-card.js`, `blank69.html`, `GET /api/events?blank_hub=1` |
| Sitemap | `sailingsa/utils/sitemap_builder.py` — `/regatta/{regatta_id}` only if results exist; `lastmod` = event dates |

Once rows are in the DB, publish is **automatic** (read model). No club “publish” button.

**Partial:** `api.py` vs `api/api.py` drift (`results-summary` / `breaking-news-meta` on root `api.py`; deploy uses `api.py` per `sailingsa/deploy/SSH_LIVE.md`).

---

## 8. Profile integration

**Exists:** ingested IDs → `/sailor/{slug}` career, media, activity. Club pages show hosted regattas + scraped upcoming events.

**Partial:** calendar ↔ results link is weak; unmatched hosts go to `/admin/review/events-host`. `club_raw` without `club_id` still common (`docs/47_UNRESOLVED_CLUB_RAW_RESULTS.md`).

**Missing:** event registration writing sailor + club + class in one club-owned flow.

---

## File / route / table index

### Backend (canonical)

- `api.py` — live FastAPI app (mirror: `api/api.py`, not identical)
- `results_ingestion_common.py` — ingest helpers
- `load_events_csv_to_db.py` — calendar upsert
- `admin_api.py` — proxies `/admin/api/session` → `/auth/session`
- `api/modules/sailor_bio.py`
- `sailingsa/utils/sitemap_builder.py`

### Frontend

- `login.html`, `js/api.js`, `js/session.js`
- `sailingsa/frontend/index.html`, `public/sailor.html`
- `sailingsa/frontend/js/breaking-news-card.js`, `regatta-sa-toolbar.js`
- Locked: `sailingsa/frontend/regatta/results.html`, `class-results.html`

### Tables (club-event relevant)

`user_accounts`, `user_sessions`, `sas_id_personal`, `temp_people`, `clubs`, `club_aliases`, `classes`, `class_aliases`, `events`, `regattas`, `regatta_blocks`, `results`, `entries` (unused product), `result_crew`, `member_roles`, `roles`, `standing_list`, `ingestion_issues`, `sailor_public_mentions`

### Docs to keep

`docs/SYSTEM_BASELINE_v1.md`, `docs/README_RESULTS_INGESTION.md`, `docs/README_regattas_table.md`, `docs/README_results_table.md`, `docs/REGATTA_375_ENTRY_PROCESS.md`, `docs/EVENTS_TABLE_AND_SCRAPE.md`, `docs/RESULTS_HTML_STATUS_LINE_RULE.md`, `docs/README_SAILOR_PROFILE_SYSTEM.md`

---

## Implications for club-event automation (Step 2+)

Any Sailwave / HalSail / Manage2Sail automation must assume:

1. **Write path today = scripts + super-admin**, not a club API.
2. **Entry = `results` row**, not `entries` (until a product decision).
3. **Classes must already exist** (`class_name` / aliases); ingest will not create classes.
4. **Status line and dates** are locked rules; ingest must not rewrite `start_date`/`end_date` from import time.
5. **Club ACL does not exist** — building “club uploads Sailwave HTML” requires a new permission model first, or stays ops-only.

Step 2 (competitor matrix) waits on instruction.
