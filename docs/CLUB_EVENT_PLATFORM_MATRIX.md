# SailingSA club-event platforms — Step 2 matrix

**Status:** Step 2 complete (plan only). No code, DB, or deploy.

**Date:** 14 October 2026.

**Depends on:** Step 1 inventory — `docs/CLUB_EVENT_ARCHITECTURE_INVENTORY.md`.

**Sources (official / first-party, read-only):**

- Sailwave home (updated 8 May 2026): https://www.sailwave.com/ — concepts, publish, CSV import, messaging
- HalSail FAQ + access levels + Hal API: https://halsail.com/Help/Faq — https://halsail.com/Help/pdfFaq?Faqitem=AccessLevels — https://halsail.com/HalApi
- Manage2Sail product copy + DSV ORM handbook + public results UI: https://www.manage2sail.com/ — portal terms
- Yacht Scoring: https://www.yachtscoring.com/howitworks.cfm — https://www.yachtscoring.com/getting_started.cfm
- TopYacht: https://topyacht.com.au/web/products-services/
- SailSys: https://www.sailsys.com.au/platform
- SA Sailing: Sailwave workshops https://www.sailing.org.za/events/80194 and `/events/110914`; Event Results PDF dump https://www.sailing.org.za/what-we-do/event-results; Sailwave-named result files e.g. FBYC Spring 2021 `/events/78813`; revSPORT membership (not scoring) https://www.sailing.org.za/revsport-sports-management-software/revsport-system-support/
- SailRSA archive (Sailwave logo): https://www.sailrsa.org.za/Result_index.htm
- SailingSA architecture: Step 1 live schema + `api.py` / `admin_api.py` (14 Oct 2026)

No product implementation in this step.

---

## Verdict

**Build natively** the national layer SailingSA already owns: club-scoped permissions, host-club event records, SAS-ID entries, class resolution against `classes.class_name`, `/regatta/{slug}` publish, sailor-profile career, and the locked status line.

**Integrate** Sailwave as the race-day scoring engine. Do **not** rebuild World Sailing Appendix A. The club already scores in Sailwave; SailingSA should ingest the **published HTML / CSV** (precomputed places and points), then attach SAS IDs.

**Do not adopt** HalSail, Manage2Sail, Yacht Scoring, TopYacht, or SailSys as the South African club product. They solve UK / EU / US / AU club-in-a-box problems. None of them know `sas_id_personal`, SailingSA slugs, or the two-layer `events` vs `regattas` model. Search of sailing.org.za found **Sailwave training and Sailwave-named result files**, and **no** HalSail or Manage2Sail product pages.

Live already has a three-slug native score-edit pilot (`club-score-edit.js` on Cape Classic, Dart 18 Nationals, Dam Bottle Sprints). Keep that as a **correction UI**, not the scoring strategy.

---

## South African club requirements (what the matrix is scored against)

From SA Sailing practice + Step 1 architecture, not from vendor marketing:

| Requirement | Evidence | Implication |
| --- | --- | --- |
| Volunteer race officers already use Sailwave | SA Sailing KZN workshops (set up file, record entries, record results, publish) at Point YC, 2020 and 2021 | Do not replace the desktop scorer |
| Results leave the club as Sailwave HTML / PDF / JPG | sailing.org.za Event Results; FBYC / Hobie files named `Sailwave-results-for-…`; SailRSA index branded with Sailwave | Import that artefact, do not require a new vendor |
| National identity is SAS ID | Live `sas_id_personal`; ingest docs require resolve-or-review; `POST /api/register-account` is login not entry | Any entry product must collect SAS ID |
| Canonical classes | `classes.class_name` authoritative; ingest will not create classes (`docs/README_RESULTS_INGESTION.md`) | Import must alias, not invent |
| Two event layers | Scrape → `events` (1302); ingest → `regattas` (478) → `results` (11233) | Club “create event” must write **both**, or link them |
| Entry today = `results` row | Live `entries` 51 unused; `results.entry_id` always NULL; Youth Nats process is TSV → `results` (`docs/REGATTA_375_ENTRY_PROCESS.md`) | Do not start from a unused `entries` table without a product decision |
| Publish is automatic once rows exist | `GET /regatta/{slug}`, sailor pages, sitemap; status line `Results are [Provisional\|Final] as at …` | Native publish already wins if ingest is reliable |
| Club ACL is a live pilot only | `club_admin` / `club_manager` + `admin_club_id` == `host_club_id`; git copy missing | First native build is permissions, not a scoring engine |
| SAS already has membership software | revSPORT for membership / courses / payments — **not** race scoring | Do not rebuild membership or payments first |

Typical SA club weekend: create or confirm the event on the SAS calendar, take entries by email / WhatsApp / beach sheet, score in Sailwave (Appendix A, discards), publish HTML/PDF to the club and sailing.org.za. SailingSA’s gap is **structured ingest + sailor graph**, not a new handicap engine.

---

## Capability matrix

Legend: **Yes** = first-party documented. **Partial** = exists with a hard limit. **No** = not a product surface. **SailingSA** column is Step 1 production truth (live).

| Capability | Sailwave | HalSail | Manage2Sail | Yacht Scoring | TopYacht / TES | SailSys | **SailingSA (live)** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Event creation | Partial — one portable `.blw` series file; not a multi-club calendar | Yes — calendar + events; sailing secretary+ | Yes — club creates events; sailor one-profile entry | Yes — register event, get access code + public menu | Yes — TES event toolbox | Yes — series setup, then weekly races | Partial — scrape/`load_events_csv_to_db.py`; **no** `POST /api/events` |
| Online entries | No (CSV / wizard / Windows messaging from a web form) | Yes — public no-login apply; sailing secretary accepts; payment via PayPal/WebCollect link | Yes — online entry + payment + crew | Yes — registration, owner/crew login, payments | Yes — TES + payment gateway | Yes — season / series / casual + payment | **Missing** — `register-account` is login; `open-regattas` hard-codes 374 |
| Race scoring | Yes — RRS 2025–2029 Appendix A; flights, Q/F, medal, many ratings | Yes — low points (RRS), bonus, 0.75, high points; handicap + tandem series | Yes — ORM: low point, handicap, groups, cup; Shadow-ORM test | Yes — finish times / one-design order; ORC, ToT, PHRF variants | Yes — times or places; IRC/AMS/SMS/ORC/PHRF | Yes — PHS pedigree + IRC/OCRI/SMS; time capture | Partial — ingest **precomputed** `race_scores`; 3-slug live PATCH; **no** shared engine |
| Publishing | HTML / email / Word / Excel / FTP-SFTP; Sailwave results folder; WS XML | Public read-only links, QR, iframe, embargo; bar slideshow | Event site + provisional/official/overall + notice board | Immediate public menu; scratch, cumulative, notice board | Upload to club web; TES rotating display | Online results + SMS | **Exists** — `/regatta/{slug}`, class pages, sailor career, hub, sitemap |
| Import | CSV competitors + race results; timing devices | Excel/CSV boats, classes, schedule, finishes; SailEvent; HAL file | Full in-product workflow; some events link **external** results URL | Event-admin data entry; not a national ingest | TES ↔ desktop TopYacht; CSV finishes | In-product | Scripts + `results_ingestion_common.py`; **no** HTTP Sailwave upload |
| Export | HTML, CSV, XML to World Sailing / RYA / Irish Sailing; `.blw` | HAL file; Hal API JSON **read-only** | Downloadable result reports | Static archive copy of results | TES / TopYacht interchange | Reports | JSON APIs for pages already published |
| Club permissions | None — whoever has the `.blw` on a Windows PC | Yes — Anonymous / Race Officer / Boat Admin / Sailing Secretary / Club Admin | Organiser-controlled club+event site (DSV handbook modules) | Event access code + admin vs public menu | Club/regatta admin vs sailor dashboard | Multi-user club admin | Partial live — `club_admin`/`club_manager` + `admin_club_id`; git missing |
| Programmatic API | Windows **WM_COPYDATA** messaging (desktop only); no REST | Yes — `GET https://halsail.com/HalApi/…` + apikey; **no writes** | Portal / event site; not a documented public ingest API for SailingSA | Web app; no public national API | Documented club-membership APIs | Cloud app | FastAPI read + super-admin / live club PATCH |
| SAS / national ID | World Sailing sailor support; **no SAS ID** | Helm/crew names; **no SAS ID** | Sailor profile (EU); **no SAS ID** | Owner/crew login; **no SAS ID** | Club sailor profile; **no SAS ID** | Yacht-centric PHS; **no SAS ID** | **`sas_id_personal` is the graph** |
| SA club fit | **Primary** — trained by SA Sailing; files already on sailing.org.za | Low — UK PY / Irish Sailing / SailEvent | Low — DSV / Central Europe championships | Low — US/Caribbean keelboat | Low — AU/NZ | Low — Sydney PHS | National index, not a race-day box |

---

## Platform notes (evidence, not marketing)

### Sailwave — integrate this

Desktop Windows scorer (Linux/Mac via emulation). One series = one `.blw` that contains ratings. No print menu: **Publish → HTML**. CSV import for competitors and race results (elapsed, place, codes, laps, start/finish). Built-in FTP/SFTP/SSH/FTPS and a hosted “Sailwave results folder”. Messaging system lets another Windows app push entries/results (SailEvent Import App; user Python via `WM_COPYDATA`). Plugins to World Sailing XML, RYA PY, Irish Sailing.

**Limits for SailingSA:** no cloud ACL; no REST; messaging cannot run on the SailingSA API host. `.blw` is a local file, not an HTTP product.

**Fit:** this is what SA clubs already produce. Official SA Sailing workshops teach exactly four steps SailingSA needs to consume: set up file → record entries → record results → publish.

### HalSail — do not adopt; optional later pull

Cloud club scorer. Documented roles: Anonymous (read), Race Officer (provisional scores), Boat Administrator (register + handicaps), Sailing Secretary (classes, schedule, validate), Club Administrator (users + HAL upload). Public entry page with accept/reject. Embargo. Integrates SailEvent, PYOnline, Irish Sailing Live. Read-only Hal API (`GetSeriesResult`, `GetBoat`, `GetEvents`, …) with a support-issued apikey.

**Limits:** UK/Irish handicap returns; no SAS ID; write API does not exist. No evidence of SA Sailing training or result files.

**Fit:** copy the **role ladder** (RO vs secretary vs club admin) into SailingSA permissions. If a future SA club publishes only on HalSail, pull `GetSeriesResult` — do not send clubs there.

### Manage2Sail — do not adopt

European regatta portal (STSO; used as DSV “Regattamanager”). Club creates events; sailors keep one profile and enter many clubs; online payment and crew. ORM scores dinghy and offshore; Shadow-ORM lets the scorer test settings on real entries without publishing. Notice board: protests, RRS 42, crew/equipment changes. Cup scoring across clubs. Public UI distinguishes Provisional / Official / Overall and can point at an **external results URL**.

**Limits:** championship operating system, not a volunteer SA dinghy club tool. No SAS ID. No SA Sailing footprint found.

**Fit:** for a World/European event hosted in SA that already lives on Manage2Sail, **link out** (same pattern as their external-results URL). Do not rebuild ORM, notice board, or payments.

### Other leading platforms (why they stay out of the SA build)

| Platform | What it is | Why not native for SailingSA |
| --- | --- | --- |
| **Yacht Scoring** | 100% web event menu: NOR/SI, registration, payments, scratch, finish times, cumulative results, protests | US/Caribbean keelboat; event-access-code model; no national sailor graph |
| **TopYacht + TES** | AU desktop scorer + online entry/payments/sign-on; APIs to club membership | AU/NZ ratings (IRC/AMS/SMS/ORC/PHRF NZ); two-app split we would only recreate |
| **SailSys** | AU cloud series + PHS handicapping + TimeCapture + SMS | PHS data centre is the product; SA dinghy nationals are one-design Appendix A |
| **SA Sailing revSPORT** | Membership, courses, payments, SAS ID profile | Already the federation membership system — SailingSA must **link**, not replace |

---

## Native vs integrate (SailingSA)

Prioritised for SA clubs and the **existing** tables/routes. “Native” means build in SailingSA. “Integrate” means consume another product’s export. “Out of scope” means do not build or switch to.

| Work | Decision | Why (architecture) |
| --- | --- | --- |
| Club permissions (`club_admin` / `club_manager` + `admin_club_id` == `host_club_id`) | **Native — first** | Live helpers already exist (`api.py` 31079–31152). Git missing. Session must return `admin_club_id` (today it does not). HalSail’s RO / secretary / club-admin ladder is the model to copy, not a vendor to install. |
| Create / confirm a hosted event | **Native** | Write `events` + `regattas` (or set `events.regatta_id`) with `host_club_id`, dates, classes. Today: scrape only; hub JS PATCHes a **missing** `calendar-event` route. Dates must stay event dates, not ingest time (`docs/README_RESULTS_INGESTION.md`). |
| Declare classes on an upcoming event | **Native** | Need an `event_classes` (or `regatta_blocks` before first race). Ingest cannot create `classes` rows. |
| Online entry with SAS ID | **Native (phase 2)** | Unique SA requirement. Reuse `sas_id_personal`. Product decision: new rows in unused `entries`, or `results` with `raced` until scored (Youth Nats template). No payment in v1 — HalSail itself outsources PayPal/WebCollect. |
| Appendix A / handicap engine | **Integrate Sailwave — do not build** | Sailwave is RRS 2025–2029 compliant; SailingSA stores **precomputed** `results.race_scores`. Live PATCH is a correction tool. Rebuilding flights/Q-F/medal/IRC is Manage2Sail-scale work. |
| Race-day finish capture | **Out of scope** | HalSail/SailSys/TopYacht TimeCapture are on-water products. SA clubs already capture in Sailwave. |
| Import Sailwave **published HTML** and/or **CSV** | **Integrate — first ingest product** | Matches what clubs email and what sailing.org.za already hosts. Map into `regatta_blocks` + `results` via `results_ingestion_common.py` (strict class resolve). HTTP upload gated by live club ACL. |
| Import Sailwave `.blw` or Windows messaging | **Out of scope** | Desktop-only; cannot run on `vm103zuex`. SailEvent’s Import App is a Windows sidecar, not a server API. |
| Import HalSail via Hal API | **Integrate later, on demand** | Read-only JSON is clean, but no SA club evidence. Requires each club’s apikey. |
| Manage2Sail / Yacht Scoring / TopYacht as the club OS | **Out of scope** | Wrong market. Link-out if an event already publishes there. |
| Public publish + sailor profiles + sitemap | **Native — already exists** | Do not iframe Sailwave HTML as the long-term page. Keep `/regatta/{slug}` and locked sheets; ingest structured rows. |
| Status line + slug/date lock | **Native — keep locked** | `Results are [Provisional\|Final] as at DD Month YYYY at HH:MM`. Import must not rewrite `start_date`/`end_date`. |
| NOR/SI hosting | **Native (lightweight)** | Live `events.nor_url` / `si_url` exist and are **0/0**. Store URLs (or files) on the event; do not build Manage2Sail notice board. |
| Payments, protests, notice board, SMS | **Out of scope for club-event v1** | Federation payments sit in revSPORT. Protest/notice board is Manage2Sail ORM. SMS is SailSys. |
| Membership / “my SAS ID” | **Integrate / link revSPORT** | Do not create a second membership system. |

---

## Recommended build order (plan only)

1. **Promote the live club ACL** into the product (and into git): persist `admin_club_id` on `GET /auth/session`; stop `club-score-edit.js` falling open; keep `admin_club_id == host_club_id`.
2. **Club event confirm/create** for a host club: title, dates, venue, classes, NOR/SI URL, link to scraped `events` row when one exists.
3. **Sailwave HTML/CSV upload** for that host: parse published series, resolve classes via `class_aliases`, create/update `regatta_blocks` + `results`, set `result_status` / `as_at_time`. Fail closed on unknown class (existing ingest rule).
4. **SAS ID attach** on imported names (existing review queue / `temp_people`). This is the national value — vendors do not do it.
5. **Optional entry list** before racing (Youth Nats TSV flow, club-owned). Only after 1–3 work. Payment later or never.
6. Keep the three-slug live score PATCH as an emergency editor. Do not generalise it into “SailingSA is the scorer.”

---

## What “success” looks like for an SA club

A ZVYC or HMYC officer (already the live pilot roles) can: confirm next Saturday’s event on SailingSA, optionally list entries with SAS IDs, score as today in **Sailwave**, upload the published HTML, and see `/regatta/{slug}` plus sailor profiles update — without ops running a Python ingest script.

That is a **national publish + identity** product that **imports Sailwave**. It is not a HalSail or Manage2Sail clone.

---

## Implications carried from Step 1 (unchanged)

1. Write path today = scripts + super-admin, plus a live-only score pilot.
2. Entry = `results` row until a product decision on `entries`.
3. Classes must already exist.
4. Status line and event dates stay locked.
5. Club ACL must be first-class before any club upload ships.

Step 3 (self-service plan): `docs/CLUB_EVENT_SELF_SERVICE_PLAN.md`. Implementation waits on approval.
