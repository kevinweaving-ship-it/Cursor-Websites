# HYC season calendar → existing club page — plan only

**Status:** Plan only. Do not code or deploy until this document is approved.

**Date:** 14 October 2026.

**Reference:** Hermanus Yacht Club sailing season 2026/2027 PDF (`HYC Calendar 2026_7-1408A3.pdf`, September 2026–May 2027).

**Extends:** `docs/CLUB_PAGE_EVENT_WIZARD_PLAN.md` (Activate / Add / wizard on `/club/{abbrev}`). That placement still stands, but **live `/club/hyc` chrome is the list cards below**, not the workspace carousel fragment.

**Unified product (do not implement HYC-only):** `docs/CLUB_CALENDAR_DUTY_MESSAGING_PLAN.md` — this PDF is the **first test-case checklist** for every-club season items, duty rosters, messaging, and **calendar-name → sailor matching**. Duty names are matched to `sas_id_personal` / profiles with confidence scores; unknown club → propose the roster club (HYC here); never overwrite an existing affiliation; keep the calendar as evidence. Schema and APIs stay `club_id`-scoped.

**Ask:** Approve the match rules, no-auto-regatta kinds, reusable fields, and missing fields before any implementation. Do not implement a Hermanus-only path.

---

## Verdict

Use the HYC PDF as the **season checklist** for enhancing **`/club/hyc`** (Hermanus Yacht Club). Do not build a second dashboard.

For each calendar cell the officer gets one of three wizard starts:

| Officer action | When | What it does | Creates `regattas`? |
| --- | --- | --- | --- |
| **Claim SAS Event** | A SailingSA / SAS row already exists (any host) | Link the club-season row to that `events` row. Keep the existing host and category. | **No** |
| **Activate Club Event** | A scraped row is **HYC-hosted** and is a race weekend | Existing `POST /api/club/events/{id}/claim` (scraped only). Reuse `regatta_id` if set. | **Only if** `regatta_id` is null **and** the row is a race |
| **Add New Event** | No SAS / club match after name+date+host check | `POST /api/club/events` **after** the match check | **Only if** the officer marks it as a race |

**Never** auto-create a `regattas` row for **Training**, **External Event**, or **Duty** (Duty Officer / Bridge / Rescue / Galley). Informal, Christmas, Work Weekend, Opening/Closing Cruise, and model-yacht extras follow the same no-regatta default.

Visitors keep today’s `/club/hyc`. Admins see the three actions on existing card chrome, plus one wizard `.card` after a choice.

---

## Confirm before coding: HYC is not HMYC

| | Hermanus (this PDF) | Henley Midmar (live scoring pilot) |
| --- | --- | --- |
| Page | **`/club/hyc`** — live heading `HYC - Hermanus Yacht Club` | `/club/hmyc` |
| `club_abbrev` | `HYC` (`compare_hyc_regattas.py` / `fix_hyc_*.py` treat this as host **~10**) | `HMYC` |
| Live club role | **None documented** | `club_manager`, `admin_club_id=98` |
| Scoring pilots | Do not touch | Cape Classic host 3; Dart 18 / Dam Bottle host 98 |

At implement time: `SELECT club_id, club_abbrev, club_fullname FROM clubs WHERE upper(club_abbrev) IN ('HYC','HMYC')`. Do not bind this work to account 98. A Hermanus `club_admin` / `club_manager` on the HYC `club_id` is a **prerequisite**, not implied by the HMYC pilot.

---

## What live `/club/hyc` already is (do not replace)

Live page (fetched 14 Oct 2026), in this order:

```
.club-page
  header.club-story-header
    identity, “Events hosted at HYC” logo chips (29er Nationals, Cape Classic, Dabchick, …)
  .club-content
    .card.stats-section.club-upcoming-events-section
      h2 “Upcoming events (1)” + .club-home-card-filter
      .sa-home-regatta-card
        title, date pills, host chip, .sa-home-regatta-actions [Event Info]
    .card.stats-section.club-past-events-section
      h2 “Past Events / Regattas Hosted (17)”
    .card.stats-section.club-sailors-section
      h2 “Sailors (128)”
    .card.stats-section.club-other-events-section
      h2 “Other events (6)” — “still need an Event URL”
```

**Today’s only upcoming HYC-hosted SAS card:** `HYC Cape Classic`, 13–14 Feb 2027, Event Info → `https://www.sailing.org.za/events/380677`. No `regatta_id`, category empty.

**Past (17)** already has reusable previous-edition slugs: `2026-02-16-hyc-cape-classic` (73 entries), `2026-02-15-hyc-cape-classic`, `2025-12-19-hyc-youth-nationals`, `2025-01-12-sa-sonnet-nationals`, `2024-02-11-hyc-cape-classic`, plus 29er / Windsurfer / Lipton rows currently attributed to this host.

**Other events (6)** are older SAS/Revolutionise cards without a results slug (2020–2023 Cape Classic / Sonnet / WC Dinghy). Leave that list as-is for visitors.

The workspace `_events_dashboard_fragment` carousel (`.event-card` / `.event-card-actions` / Live|Upcoming|Past tabs) is **not** what live `/club/hyc` renders. Admin chips go on **this** chrome.

---

## Exact admin slots on `/club/hyc`

Same rules as `docs/CLUB_PAGE_EVENT_WIZARD_PLAN.md`: only when `GET /api/club/me` says this page’s club; visitors get zero extra buttons.

### 1. Actions — on the existing upcoming (and other) card

**Where:** `.sa-home-regatta-actions`, **beside Event Info**. Do not add a second action row. Do not restyle `.sa-home-regatta-card`.

```
[Event Info] [Claim SAS Event]     ← other-host SAS match, or unlinked SAS row
[Event Info] [Activate Club Event] ← HYC-hosted scraped race, no regatta_id
[Event Info] [Manage]              ← already has events.regatta_id
```

Show **one** of Claim / Activate / Manage, never both Claim and Activate. Past cards with a public `/regatta/{slug}` stay Details-only.

### 2. Add New Event — on the Upcoming heading row

**Where:** `h2.section-title.club-section-title-row` of `.club-upcoming-events-section`, after the search filter.

```
UPCOMING EVENTS (1)     [ search… ]  [Add New Event]
```

Secondary control. Starts the wizard in create mode **after** match check. If name+dates match an existing SAS or HYC card, the wizard offers Claim or Activate instead of `POST` create.

### 3. Wizard — one extra card after a choice

**Where:** one `.card.stats-section` inserted **below** the Upcoming card and **above** Past / Sailors. Same club card chrome: `h2.section-title`, `.table-container`, `table.table`.

Closing the wizard removes it. No `/club-manage` redirect. Optional deep link only: `/club/hyc?event={event_id}`.

Wizard steps stay as already planned (Details → Fleets → Registration → Entries → Upload → Publish). Fleets / Entries / Upload / Publish **do not appear** when the row is Training, External, Duty, Informal, Cruise, Christmas, or Work Weekend.

---

## PDF columns vs SailingSA fields

The PDF is a **four-kind** club diary. SailingSA `events` is a **hosted SAS calendar**. They are not the same list.

| PDF column | Meaning on the page | Existing SailingSA field | Reuse? |
| --- | --- | --- | --- |
| DAY / DATE | Weekend window (Sat/Sun often one event) | `events.start_date`, `events.end_date` | Yes — parse to ISO |
| EVENTS | Title | `events.event_name` | Yes when a SAS row exists |
| EVENTS EXTRA INFO | Fleet / series hint (A&B, Carioca C, 29er, Sonnet Series #n) | none (`_likely_classes` on public cards is empty) | Suggest in Fleets step only |
| TRAINING | Club course | closest: `events.category = 'Training'` | Category only; **no** `regattas` |
| EXTERNAL EVENT | Other club’s event | other row’s `event_name` + `host_club_id` + `category` | **Claim SAS Event** only |
| DUTY OFFICER / BRIDGE / RESCUE / GALLEY | Roster names | **nothing** | Do not store as events |
| Footer (Portsmouth all-dinghy series, Windsurfer LTs, club champs standalone) | Club scoring policy | none | Wizard copy / Fleets suggestions |

### SAS `events.category` values already on live (preserve)

From `GET /api/events` (1 302 rows, 14 Oct 2026):

| Category | Count | Use on HYC |
| --- | --- | --- |
| *(empty)* | 397 | 2027 HYC Cape Classic is in this set — officer confirms type |
| National Championships | 292 | Claim only; never overwrite |
| Regional Championships | 167 | Claim only |
| Training | 129 | Training rows; hide result tick (already in `hide_result_types`) |
| Dinghy Event | 121 | Historical HYC Cape Classic; default for new HYC race weekends |
| Keel Boat Event | 106 | Agulhas Race (different weekend — see mismatches) |
| Team Sailing Events | 34 | — |
| Meetings | 29 | Hide result tick |
| Interschools | 10 | — |
| Youth Events | 8 | — |
| Multiclass Event | 6 | — |
| District Competitions | 2 | — |
| Club | 1 | Dam Bottle only today; optional for new club cups |

Do **not** invent SAS categories (`Duty`, `Informal`, `Cruise`, `External`). Keep `events.category` as the SAS/club type badge. Club-diary kind (race / training / external / duty / informal) is a **separate** flag — see Missing fields.

`hide_result_types` is already `("Meeting", "Meetings", "Training")`. After approval, extend the **result-tick hide** to Informal / Duty / Cruise **without** adding those strings as SAS categories.

---

## Match rules (calendar → existing events)

Match **name tokens + date window** using the existing calendar↔regatta helper (`api.py` ~27224: `sonnet`, `classic`, `ilca`, `29er`, `420`, `hobie`, …). Prefer an existing `events` row over `POST` create. Never rewrite slugs. Never move another club’s `host_club_id`.

### A. Claim SAS Event — matched, do not mint an HYC slug

| Calendar | Dates | Live SailingSA / SAS row | Category | Existing slug | Notes |
| --- | --- | --- | --- | --- | --- |
| Zeekovlei YC Cape Classic | 12–13 Sep 2026 | `ZVYC Cape Classic` | Dinghy Event | **`2026-09-13-zvyc-cape-classic`** | Scoring-pilot host **3**. Claim = link only. |
| 420 Nationals @ Theewaterskloof SC | 26 Sep 2026 | `420 Nationals` 26–27 Sep 2026 | National Championships | **`2026-09-25-tsc-420-nationals`** | Other host. |
| Youth Nationals @ LDYC | 16–21 Dec 2026 | `2026 SA Sailing Youth National Championship` 16–21 Dec | National Championships | none yet | Dates exact. **2025** edition was HYC (`2025-12-19-hyc-youth-nationals`). Do **not** claim 2026 as HYC-hosted. |
| Western Cape Dinghy Champs @ SBYC | 27 Mar 2027 | `Western Cape Dinghy Championships 2027` 26–29 Mar | Regional Championships | none | Other host. |
| ILCA Nationals @ Richards Bay | 24–27 Apr 2027 | `ILCA Nationals` 24–27 Apr 2027 | National Championships | none | Other host. |
| Hobie Nats @ Struisbaai | 25–27 Apr 2027 | `Hobie 16 Nationals` 25–27 Apr 2027 | National Championships | none | Other host. |

### B. Activate Club Event — HYC-hosted scraped race

| Calendar | Dates | Live row | Category | Slug | Action |
| --- | --- | --- | --- | --- | --- |
| HYC Cape Classic (+ Sonnet Series #3 in extra-info) | 13–14 Feb 2027 | `HYC Cape Classic` (SAS `380677`) | **empty** | none | **Activate** after officer confirms type `Dinghy Event` (last years used that). Previous edition: `2026-02-16-hyc-cape-classic` (73 entries) + `2026-02-15-hyc-cape-classic`. Suggest those fleets; do not auto-copy `regatta_blocks`. |

This is the only 2026/27 HYC PDF weekend that already sits on the public Upcoming card.

### C. Add New Event — no SAS row (club racing)

None of the named HYC cups appear in `GET /api/events` (search: carioca, hangover, watermeyer, benningfield, endeavour, easter egg, spear, brody, galactics, straus, westcott, louw, arton, prain, port, collingridge). After a no-match check, the officer may create a **club-origin** race. Default category: **Dinghy Event** (or **Club** if they pick it). Default venue: Hermanus Yacht Club. Registration stays Closed.

Race weekends (officer must confirm before a `regattas` insert):

- 10–11 Oct 2026 — All Dinghy & Multihulls; ILCA Endeavour Trophy / Watermeyer Cup
- 24–25 Oct 2026 — Carioca Louw Cup & Sonnet Straus Trophy (Sonnet Series #1)
- 7–8 Nov 2026 — All Dinghy & Multihulls; ILCA Benningfield Shield
- 21–22 Nov 2026 — Carioca Arton Trophy
- 5–6 Dec 2026 — All Dinghy; Carioca Schultz Single Handed; ILCA Club Champs; Sonnet Westcott Trophy
- 28–31 Dec 2026 — **Sonnet Nationals at HYC** (no 2026/27 SAS row yet; last SAS Sonnet Nats is 12 Jan 2025, slug `2025-01-12-sa-sonnet-nationals`). If a SAS row appears later, switch to Activate / Claim. **HYC50 Model Yacht Race** on the same cell is **not** a dinghy `regattas` row.
- 1 Jan 2027 — Hangover Race (all classes)
- 2–3 Jan 2027 — Fun Series (all classes)
- 16–17 Jan 2027 — Carioca Prain Trophy
- 30–31 Jan 2027 — All Dinghy; ILCA Over 45; Multihulls Brody Trophy
- 27–28 Feb 2027 — Carioca Club Champs & 29er Club Champs
- 6–7 Mar 2027 — Sonnet Galactics (Sonnet Series #4)
- 13–14 Mar 2027 — All Dinghy; Multihulls Club Champs; Dabchick Club Champs
- 27–28 Mar 2027 — Easter Egg Cup (all classes) + Carioca Transom Distance *(same weekend as WC Dinghy @ SBYC — two rows: Add the cup, Claim the champs)*
- 10–11 Apr 2027 — All Dinghy; 29er Regatta; Sonnet Collingridge Shield
- 24–25 Apr 2027 — Carioca Schultz Double Handed; 29er Regatta *(same weekend as three externals — do not merge)*
- 8–9 May 2027 — All Dinghy; Multihull Spear Cup; Optimist Club Champs
- 15–16 May 2027 — Carioca Port Cup only *(Closing Cruise is separate, no-regatta)*

Club champs stay standalone events (PDF footer). Do not fold them into the all-dinghy series.

### D. No event / no `regattas` — training, external-without-match, duty, ops

| Calendar | Kind | Why no auto-regatta |
| --- | --- | --- |
| 5–6 Sep HYC Work Weekend | Club ops | Not a race |
| 24–25 Sep Bridge Course / Rescue Course | Training | No SAS Training row on those dates. Later SAS Training rows are instructor / safety-boat courses at other venues. |
| 26 Sep Opening Cruise | Club activity | Not a race |
| All INFORMAL Sat/Sun | Informal | Club ops / no results URL |
| 25–26 Dec Christmas | Closed | Not a race |
| 15 May Closing Cruise | Club activity | Not a race |
| DUTY OFFICER / BRIDGE / RESCUE / GALLEY names | Duty | Roster only. Never an `events` row. |
| HYC50 Model Yacht Race (28–31 Dec extra-info) | Other | Not a scored dinghy/multihull regatta |

### E. Date / name mismatches — officer must pick the SAS row

| Calendar says | Live SailingSA says | Rule |
| --- | --- | --- |
| 29er Nationals @ SBYC/LBYC **20–21 Mar 2027** | `29er Nationals` **25–27 Apr 2027** (National Championships). 2026 29er Nats were 28–30 Mar. | Do not create a March HYC-hosted nationals. Offer the April SAS row as Claim. March stays Informal unless the officer knows otherwise. |
| 100 km Cape Agulhas 23–24 Apr 2027 | Only `Agulhas Race` **2–4 Oct 2026** (Keel Boat Event), plus a 2024 Training row | No 2027 April match. Claim nothing. Do not create an HYC keelboat slug. |
| TWK Cape Classic 28–29 Nov 2026 | No 2026 TSC/TWK Cape Classic in the scrape (last: `TSC Cape Classic` 8 Dec 2025, slug `2025-12-08-tsc-cape-classic`) | Claim when the scrape grows; until then show as External unmatched. |
| Sonnet Nationals at HYC 28–31 Dec 2026 | No 2026/27 Sonnet Nats in the scrape | Add New (HYC race) **or** Activate if SAS lists it later. Category should stay **National Championships** if a SAS row appears. |
| “Zeekovlei” spelling | DB `ZVYC Cape Classic` | Token match (`classic` + dates) is enough. |

---

## Three wizard paths (no duplicate URLs)

```
Upcoming / Other card
  [Claim SAS Event]
      → match API finds existing events row (any host)
      → store a club-season link only
      → do NOT UPDATE host_club_id
      → do NOT INSERT regattas
      → do NOT rewrite slugs (Cape Classic 52 / Dart 18 / Dam Bottle untouched)

  [Activate Club Event]
      → POST /api/club/events/{id}/claim
      → scraped rows only; host null / Unassigned / self
      → reuse events.regatta_id if set
      → INSERT regattas only when regatta_id is null AND kind = race
      → slug {YYYY-MM-DD}-hyc-{name}
      → never UPDATE an existing regatta_id

Heading [Add New Event]
      → compare title + dates against:
           1) this club’s events (GET /api/club/me/events)
           2) all-events match (name + ±3 days)   ← missing today
      → if SAS match: offer Claim (other host) or Activate (HYC host)
      → if no match and kind = race: POST /api/club/events (creates events + regattas)
      → if no match and kind ∈ {training, external, duty, informal, cruise}:
           create calendar row WITHOUT regattas (API gap — see below)
```

`POST /api/club/events` **always inserts a `regattas` row today**. `POST …/claim` **always inserts `regattas` when `regatta_id` is null**. Those two behaviours are why training / external / duty must not call the current endpoints unchanged.

---

## Reusable data (already there)

| Need | Source | Ready? |
| --- | --- | --- |
| Club page surface | Live `/club/hyc` cards, heading, Sailors, Past, Other | Yes — enhance, do not replace |
| HYC identity | `clubs` abbrev `HYC`, slug `/club/hyc`, logo `/artwork/Club Logo/HYC.png` | Yes |
| Upcoming SAS card | `HYC Cape Classic` 13–14 Feb 2027, SAS `380677` | Yes — Activate candidate |
| Previous HYC Classic | `2026-02-16-hyc-cape-classic`, `2026-02-15-hyc-cape-classic`, 2025/2024 slugs | Heuristic “Last year: …” |
| Previous Sonnet Nats at/near HYC | `2025-01-12-sa-sonnet-nationals`, `2024-01-09-sa-sonnet-nationals`; Other-events 2022 SAS `139354` | Suggest only |
| External SAS rows | ZVYC Classic, 420 Nats, Youth Nats 2026, WC Dinghy 2027, ILCA Nats 2027, Hobie 16 Nats 2027 | Yes — Claim |
| Name / dates / venue / type | `events.event_name`, `start_date`, `end_date`, `venue_raw`, `location_raw`, `category` | Yes when scrape filled them |
| NOR / SI | `events.nor_url`, `si_url` | Live still often empty — ask only if blank |
| Host | session `admin_club_id` / card host chip | Never a typed field |
| Public URL | `events.regatta_id` or Event Info `source_url` | Do not rewrite |
| Claim / create APIs | `POST …/claim`, `POST /api/club/events`, `GET /api/club/me/events` | Yes for **races** only |
| Race-class picker | `GET /api/club/me/events` → `race_classes[]` | Names in the select |
| Known classes for extra-info | Live: `Ilca 6`, `Ilca 7`, `29er`, `Sonnet`, `Dabchick`, `Optimist` / `Optimist A`, `Multihull`, `Hobie 16`, `Windsurfer LT` | Suggest; officer confirms |
| Hide result tick | `hide_result_types` Meeting / Training | Extend hide list; do not invent SAS categories |
| Keyword match | `_tok` / classic / sonnet / 29er helper ~27224 | Reuse for Claim match |
| Design system | `.container`, `.card`, `.table`, `.table-container`, `.section-title` | Mandatory |

---

## Missing fields and API gaps (blockers)

Identify these **before** implementation. Do not start coding by stuffing duty names into `event_name`.

### 1. Club-diary kind (not a SAS category)

Need a stored flag so Training / External / Duty / Informal / Cruise / Race can be preserved without overwriting `events.category`.

Options (pick at implement, do not do both):

- Nullable `events.club_kind` text: `race` \| `training` \| `external` \| `duty` \| `informal` \| `cruise` \| `ops`
- Or a small `club_season_items` table (`club_id`, dates, title, `kind`, `event_id` null, `regatta_id` null) so duty/informal never touch `events`

**Recommendation:** `club_season_items` for duty / informal / cruise / unmatched external; reuse `events` only when there is a real SAS or club-race row. Avoid a second source of truth for HYC Cape Classic.

### 2. Claim-without-regatta / create-without-regatta

| Current API | Problem |
| --- | --- |
| `POST /api/club/events/{id}/claim` | Sets host if Unassigned **and** inserts `regattas` when `regatta_id` is null |
| `POST /api/club/events` | Always inserts `events` **and** `regattas` |
| `GET /api/club/me/events` | `WHERE host_club_id = session club` — cannot see ZVYC / TSC / LDYC / SBYC rows |

Need (after approval):

- `GET /api/club/events/match?name=&start=&end=` — search **all** `events` by token + ±3-day window; return `event_id`, name, dates, category, host name (not a raw id field in the UI), `regatta_id`
- Claim SAS Event: link only (`create_regatta=false`, `assign_host=false`)
- Activate: current claim, but refuse when `club_kind` is not `race` (or category is Training / Meetings)
- Add New: `create_regatta` default **false**; set true only after the officer confirms a race

### 3. Duty roster

PDF columns Duty Officer, Bridge, Rescue, Galley (people, “Volunteer crews”, “No galley”).

**No table, no API, no UI field.** Out of the event wizard. If the club later wants a roster, that is a separate card — not `events.organiser` / `events.contact` (those are SAS scrape fields).

### 4. Extra-info fleets and series

| PDF text | Missing |
| --- | --- |
| A&B racing fleet, 29er | No `events` class list; `_likely_classes` empty |
| B non-racing & C fleet | Carioca C is not a `classes` row |
| Sonnet Series #1–#4 | No series membership table |
| All-dinghy Portsmouth series (footer) | No PY / scoring-system flag on create |
| Windsurfer LTs sail on Dinghy & Multihulls weekends | Suggestion text only |
| Club champs standalone | Policy copy, not a field |

Fleets step: show extra-info as **suggested class names**. Officer picks from `race_classes[]`. Do not auto-insert `regatta_blocks`. Do not auto-insert missing classes.

### 5. Carioca is not a live race class

`GET /api/class/Carioca` → 404. Louw / Arton / Schultz / Prain / Port / Club Champs cannot declare a Carioca fleet until a `classes` row (and aliases) exists. **Do not auto-insert.** Super-admin class add is a prerequisite for those cups, or the officer skips Fleets.

`GET /api/class/ILCA` also 404; use **Ilca 6** / **Ilca 7** in the dropdown (names, not ids).

### 6. HYC officer account

Live club writers are ZVYC `club_admin` (3) and HMYC `club_manager` (98). There is **no** documented Hermanus officer. Activate / Add on `/club/hyc` will not appear until `admin_club_id` equals the HYC `club_id`.

### 7. 2027 HYC Cape Classic category empty

Preserve associated SAS info (`source_url` 380677, dates, host HYC). Officer sets category on Activate (suggest Dinghy Event from 2024–2026 editions). Do not default-fill in the scrape loader.

### 8. Unassigned / other-host rows

Host-scoped lists hide Unassigned-but-looks-like-HYC and all externals. Claim SAS Event **requires** the match API in (2). Until then, those stay on `/admin/review/events-host` and the public Other-events / Unassigned tools. Do not invent a second public calendar.

---

## What we will not do

- Auto-create `regattas` for Training, External Event, Duty, Informal, Christmas, Work Weekend, Opening/Closing Cruise, or model-yacht extras
- Steal host on ZVYC Cape Classic, 420 Nats, Youth Nats 2026, WC Dinghy, ILCA Nats, Hobie Nats
- Treat 2025 Youth Nats at HYC as a reason to host 2026
- Create a March 2027 29er Nationals slug because the PDF wrote 20/21 Mar
- Store duty/bridge/rescue/galley names as events
- Overwrite SAS categories (National / Regional / Training / Dinghy Event / …)
- Rewrite slugs or the three scoring-pilot URLs
- Replace live `/club/hyc` with `/club-manage` or `/club-manage-preview`
- Change visitor heading, chips, Upcoming/Past/Other/Sailors cards, or header/nav
- Auto-copy last year’s `regatta_blocks`
- Open entries by default
- Auto-insert `Carioca` (or any class)
- New CSS frameworks, inline CSS, custom fonts/colours
- PDF ingest as a product in v1 — the officer uses Claim / Activate / Add against the checklist

---

## Suggested fleet text (not auto-blocks)

From EVENTS EXTRA INFO + footer, for the Fleets confirm table only:

| Weekend type | Suggest (names) |
| --- | --- |
| All Dinghy & Multihulls | Ilca 6, Ilca 7, 29er, Multihull, Windsurfer LT, plus named cup class |
| Carioca trophy weekends | Carioca **if/when the class exists**; else skip + note |
| Sonnet series / Nats | Sonnet |
| Club champs | That class only (ILCA → Ilca 6 + Ilca 7; Carioca; 29er; Multihull; Dabchick; Optimist) |
| Hangover / Fun Series / Easter Egg | All-classes + Portsmouth note (no class auto-add) |

---

## Implementation notes (only after approval)

1. Confirm HYC `club_id` vs HMYC 98; attach a Hermanus officer.
2. Backup live `api.py` (`sailingsa/deploy/pre-change-backup.sh`). Patch **live 83k**, never overwrite with git ~28k.
3. Gate with `GET /api/club/me` on `/club/hyc` only. Inject Claim / Activate / Add / wizard in JS on `.sa-home-regatta-actions` and the Upcoming heading row.
4. Add match API + `create_regatta` / `assign_host` flags **before** wiring Training or External to any POST.
5. Reuse claim for Activate on HYC Cape Classic 2027 (SAS 380677) as the first race path.
6. Extend result-tick hide; keep SAS `category` values.
7. Mobile: actions stay in `.sa-home-regatta-actions` (wrap, 44px tap). Wizard is one column in `.table-container`.

---

## Approval

Reply to implement **on `/club/hyc` only**, with Claim SAS Event / Activate Club Event / Add New Event as specified, **no auto-`regattas`** for training, external events, or duty. This document is not a licence to code until you say so.
