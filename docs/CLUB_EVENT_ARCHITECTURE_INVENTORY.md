# SailingSA club-event architecture — Step 1 inventory

**Status:** Step 1 complete (evidence pass). Plan only. No code, DB, or deploy. Competitor research (Step 2) not started.

**Date:** 14 October 2026.

**Sources (read-only):**

- This git tree: `api.py` (~27k lines), `admin_api.py`, frontend under `js/` and `sailingsa/frontend/`
- Live host `vm103zuex.yourlocaldomain.com` (`102.218.215.253`): `/var/www/sailingsa/api/api.py` (**81 476 lines**, mtime 14 Oct 2026 11:16 SAST) and `information_schema` + counts on `sailors_master`
- `docs/SYSTEM_BASELINE_v1.md` is **stale** (28 Feb 2026) — no `events` table, no `user_accounts.role`

**Verdict:** Still a publish-and-profile site. **Live** has a **pilot** club-admin score path (ZVYC / HMYC, three 2026 slugs). **This git copy does not.** Clubs still cannot create events, take entries, or score arbitrary regattas.

**Repo vs live:** Treat **live `api.py` + live schema** as production truth. Do not implement from the shorter git `api.py` without diffing live first.

---

## Status by domain (evidence-backed)

| Domain | Status | Exists (with proof) | Partial / missing (with proof) |
| --- | --- | --- | --- |
| Club permissions | **Partial (live) / missing (git)** | Live `user_accounts.role`: sailor 69, super_admin 13, club_manager 3 (HMYC club_id 98), club_admin 1 (ZVYC club_id 3). Column `admin_club_id` integer nullable. Live helpers `_session_role_is_club_admin` 31079, `_session_admin_club_id` 31084, `_session_can_edit_regatta_scores` 31140, `_require_regatta_score_edit` 31152. Session: live/git `GET /auth/session` (git 19248 / live 42034) returns `role`, `is_super_admin` — **not** `admin_club_id`. Sailor media: git 12433–12445 (`session sas_id` must match). Admin lists: `_admin_review_guard` git 8368–8374 (`super_admin`\|`admin` + hostname `vm103zuex.yourlocaldomain.com`). `admin_api.py` 102–107, 155–189 (session proxy; live copy `/var/www/sailingsa/api/admin_api.py` 11 Apr 2026). Frontend: `js/api.js` `sailingSessionIsSuperAdmin` 491–499; `js/session.js`; `login.html`. | Git `api.py` has **no** `club_admin` / `admin_club_id`. Checks are only `("super_admin", "admin")` (git 8373; `admin_api.py` 104). Live has **zero** `admin` rows. Live `club-score-edit.js` `canScore()` (lines 41–57) falls open if `session.admin_club_id` is missing (it is). Server PATCH still scopes to host. No general club portal. |
| Event creation | **Partial** | Live `events`: **1302** rows, 893 `host_club_id`, 405 `regatta_id`. Loader `load_events_csv_to_db.py`. Reads: `GET /events` git 795, `GET /api/events` 9769, `GET /admin/review/events-host` 8709, `POST /admin/review/assign-event-host` 8658–8691. Super-admin patches existing `regattas` (git 19901+). | **No** `POST /api/events` or INSERT into `events`/`regattas` in git `api.py`. Live: **0** `nor_url`, **0** `si_url`. Hub JS `breaking-news-card.js` 4039 PATCHes `/api/super-admin/calendar-event/{id}` — **no such route** in git or live `.py`. |
| Classes | **Exists** | Live `classes.is_race_class`: 201 true, 1 false. Tables `classes`, `class_aliases`. Routes: `GET /classes` 1910, `GET /api/class/{class_ref}` 14502, `GET /api/regatta/{id}/class-entries` 16457. | No `event_classes` on upcoming calendar rows. Classes attach only after `regatta_blocks` ingest. |
| Sailors | **Exists** | Live `sas_id_personal` present; `sailing_id` / `sa_ids` **absent**. Profiles: `GET /sailor/{slug}` 1641, `GET /api/member/{sa_id}/results` 12978. Frontend Add Media: `sailingsa/frontend/index.html` ~6781 → `POST /api/member/{sa_id}/add-media`. | `GET /auth/session` still SELECTs `sailing_id` (git 19309–19320) — table missing on live. Logged-in default-profile plan not built. |
| Registration / entries | **Missing** | Live `results`: 11233 rows (9796 `raced` true). `GET /api/regatta/{id}/class-entries` 16457. User signup: `POST /api/register-account` 21460–21569 (sets `user_accounts`, default role `'sailor'`). | Live `entries`: **51** rows; `results.entry_id` **always NULL**. `GET /api/open-regattas` 19063 hard-codes `regatta_number = 374` (comment says 375). No online entry POST. |
| Scoring | **Partial** | Ingest: `results.race_scores` JSONB. Git `PATCH /api/result/{id}/race` 14081–14084 (`_require_super_admin`). Live same route (34688) plus `PATCH /api/result/{id}/fleet-races` (35041) allow `club_admin`/`club_manager` when `admin_club_id == regattas.host_club_id` (34732–34758). Live UI: `/js/club-score-edit.js` path-gated to `2026-09-13-zvyc-cape-classic`, `2026-09-24-hmyc-dart-18-nationals`, `2026-10-10-hmyc-dam-bottle-sprints`; included from live `api.py` 73440/73448 and `/js/hmyc-dam-bottle-live-boot.js` 1550. | Not a general scoring product. No HTTP PDF/Sailwave upload. Git copy cannot serve the club-admin UI. Live `_require_super_admin` also hard-allows SAS id `21172` (31068). |
| Publishing | **Exists** | `GET /regatta/{slug}` 9548, class page 9541, `GET /api/regatta/{id}` 16642, `GET /api/regatta/{id}/results-summary` 16635. Hub columns live: `blank_hub_news_*`. Sitemap builder. Locked iframes 1656–1673. | Automatic once rows exist. `card_results_url` / `card_calendar_url` referenced in git 16508–16512 (`column_exists`) — **not** on live `regattas`. |
| Profile integration | **Partial** | `helm_sa_sailing_id` on results; media table live. Club pages `GET /club/{slug}` 9554. | 405/1302 events linked to a regatta. `result_participants` / `result_crew` **absent** on live — git `POST /api/result/attach-person` 13793 writes `result_participants` (would fail). |

---

## Auth matrix (exact)

| Layer | Location | What it checks |
| --- | --- | --- |
| Session cookie | `user_sessions.session_id`; git `_get_session_sas_id` 12334–12353 | Valid `expires_at` |
| Role | Live `user_accounts.role` NOT NULL default `'sailor'`; git `_get_session_role` 12356–12379 | Join session → account |
| Super admin | git `_session_role_is_super_admin` 12382–12388; `_require_super_admin` 12391–12394 | `super_admin` / `superadmin` |
| Staff admin (git + `admin_api.py`) | git 8368–8374; `admin_api.py` 102–107 | `super_admin` **or** `admin` **and** hostname `vm103zuex.yourlocaldomain.com` |
| Club admin (**live only**) | live `api.py` `_session_role_is_club_admin` ~31079; `_session_admin_club_id` ~31090 | `club_admin` / `club_manager` + `admin_club_id` |
| Club score scope (**live only**) | live `_session_can_edit_regatta_scores` ~31143 | `admin_club_id == regattas.host_club_id` |
| Sailor self | git 12443–12445 | `session.sas_id == path sa_id` |
| Unauthenticated writes | git `POST /api/id/temp` 13758, `POST /api/id/promote` 13775, `POST /api/result/attach-person` 13793, `POST /api/result/{id}/set_person` 13844 | **No session argument** |

`admin_api.py` does **not** create events or scores. It proxies `GET /admin/api/session` → `/auth/session` (155–169) and `POST /admin/api/logout` (172–189), then staff lists / scrape / restart.

Frontend controls: `login.html` + `js/session.js` + `js/api.js` (`sailingSessionIsSuperAdmin` 491–499); sailor **Add Media** on `index.html`; hub SA editors in `breaking-news-card.js` / `blank69.html`; live-only `club-score-edit.js`. **No** create-event or entry form in git frontend.

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

- Live `user_accounts.role` + `admin_club_id` exist; git `api.py` never reads `admin_club_id` or `club_admin`.
- Live `GET /auth/session` (~42034) returns `role` + `is_super_admin` only — **not** `admin_club_id`. Live `/js/club-score-edit.js` `canScore()` reads `session.admin_club_id` and, if it is null, **allows any** `club_admin`/`club_manager`. Server PATCH still enforces `admin_club_id == host_club_id`.
- Password-reset columns exist; **no** forgot-password route on main API.
- `POST /auth/register` is referenced in `js/api.js` and **not** implemented.
- `member_roles` + `roles` = SA qualifications (Instructor, Judge) — **display only** (`GET /api/member/{sa_id}/roles`).
- `sas_id_personal` commodore / secretary fields are **not** permission checks.
- Live `_require_super_admin` (~31064) also hard-allows SAS id `21172`.

**Missing (product)**

- General club portal: create event, take entries, score arbitrary host events.
- `admin` role rows: live count **0** (git/`admin_api.py` still check `("super_admin", "admin")`).
- Git copy of the live club-score path (`club-score-edit.js`, `_session_role_is_club_admin`).

**Who can write (production truth = live)**

| Action | Who | Route / location |
| --- | --- | --- |
| Own media | Session `sas_id` match | git/live `POST/PATCH/DELETE /api/member/{sa_id}/media*` (git 12433) |
| Assign `events.host_club_id` | `super_admin` (git guard also lists `admin`) | git `POST /admin/review/assign-event-host` 8658; live 26004 |
| Patch result row | `super_admin` (git); live also SAS `21172` via `_require_super_admin` | git `PATCH /api/result/{id}` 13980; live 33776 |
| Patch one race score | git: `super_admin` only (14081). Live: `super_admin` **or** `club_admin`/`club_manager` when `admin_club_id == regattas.host_club_id` | live `PATCH /api/result/{id}/race` 34688–34758 |
| Patch fleet race count | live only | `PATCH /api/result/{id}/fleet-races` 35041 |
| Toggle event WhatsApp on a hosted slug | live `super_admin` or scoped club admin | live `PATCH /api/super-admin/regatta/{id}/event-whatsapp` 59896 |
| Create club / patch regatta host | `super_admin` | git `POST /api/super-admin/clubs` 20432; `PATCH …/host-club` 20501 |
| Hub breaking-news badge | `super_admin` | git `PATCH /api/super-admin/regatta/{id}/breaking-news-meta` 19943 |
| Create calendar event / upload results | Ops scripts only | **No** `POST /api/events` in git or live `api.py` |

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

**Missing:** general club scoring UI for all host events; HTTP upload of Sailwave/HTML/CSV. Live UI is three slugs only (`club-score-edit.js` on Cape Classic + Dart 18 via live `api.py` ~73440/73448; Dam Bottle via live `/js/hmyc-dam-bottle-live-boot.js` 1550).

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

### Tables (club-event relevant) — live `sailors_master` 14 Oct 2026

**Present:** `user_accounts` (`role` NOT NULL default `'sailor'`, `admin_club_id` nullable int), `user_sessions` (`session_id`, `account_id`, `sas_id`, `last_path`; **no** `logout_time` / `device_type`), `sas_id_personal`, `temp_people`, `clubs`, `classes`, `class_aliases`, `events` (`host_club_id`, `regatta_id`, `nor_url`, `si_url`), `regattas` (`host_club_id`, `result_status`, `as_at_time`, `blank_hub_news_badge_label`; **no** `card_results_url` / `card_calendar_url`), `regatta_blocks`, `results`, `entries` (51 rows; `results.entry_id` always NULL), `member_roles`, `roles`, `sailor_public_mentions`.

**Absent on live:** `sailing_id`, `sa_ids`, `result_participants`, `result_crew`, `review_audit_log`.

### Live-only files (not in this git tree)

- `/var/www/sailingsa/api/api.py` — 81 476 lines; club ACL + score pilots
- `/var/www/sailingsa/js/club-score-edit.js` — slug-gated UI; PATCH `/api/result/{id}/race` and `/fleet-races`
- `/var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js` — injects `club-score-edit.js` for Dam Bottle Sprints

### Docs to keep

`docs/SYSTEM_BASELINE_v1.md`, `docs/README_RESULTS_INGESTION.md`, `docs/README_regattas_table.md`, `docs/README_results_table.md`, `docs/REGATTA_375_ENTRY_PROCESS.md`, `docs/EVENTS_TABLE_AND_SCRAPE.md`, `docs/RESULTS_HTML_STATUS_LINE_RULE.md`, `docs/README_SAILOR_PROFILE_SYSTEM.md`

---

## Implications for club-event automation (Step 2+)

Any Sailwave / HalSail / Manage2Sail automation must assume:

1. **Write path today = scripts + super-admin**, not a club API.
2. **Entry = `results` row**, not `entries` (until a product decision).
3. **Classes must already exist** (`class_name` / aliases); ingest will not create classes.
4. **Status line and dates** are locked rules; ingest must not rewrite `start_date`/`end_date` from import time.
5. **Club ACL is a live-only score-edit pilot** (`club_admin`/`club_manager` + `admin_club_id` == `regattas.host_club_id`) on three 2026 slugs. Git has none. A general “club uploads Sailwave HTML” product still needs a first-class permission + create/entry API, or stays ops-only.

Step 2 (competitor matrix) waits on instruction.
