# MAC TSL WC Team Sailing — Event URL (17–18 Oct 2026)

**Event URL (gold, locked):**  
https://sailingsa.co.za/regatta/2026-10-17-mac-tsl-wc-team-sailing

Slug: `2026-10-17-mac-tsl-wc-team-sailing`  
Format: `YYYY-MM-DD-{club}-{slug}` (same as `/regatta/2026-09-25-tsc-420-nationals`, `/regatta/2026-03-29-mac-24-hour-challenge`).  
Do **not** change this slug after create.

| Field | Value |
| --- | --- |
| SAS name (`event_name`) | SA Sailing WC Team Sailing Event |
| Dates | 2026-10-17 → 2026-10-18 |
| Host | MAC — Milnerton Aquatic Club |
| SAS | https://www.sailing.org.za/events/380433 |
| Block | `2026-10-17-mac-tsl-wc-team-sailing:tsl` |
| Class / fleet | TSL |
| Scoring | Team Racing |
| Apply | `python3 sailingsa/deploy/create_2026_mac_tsl_wc_event_url.py` |

Do not reuse March `328007` or July GLYC `370796`.

**WC structure (locked):** `docs/TSL_WC_STRUCTURE.md` — regional league only, per-event teams, 3v3 positional, SAS boats rotated.  
**Handbooks:** `docs/TSL_WC_HANDBOOKS.md` — Jacques Smit TSL PDFs are **not on the box**.

---

## Std header (do not invent a new layout)

Same `.header` as every Event URL / results sheet:

| Slot | Content |
| --- | --- |
| **Left** | Event logo — `/artwork/Event Logo/TSL-Team-Sailing.png` (same TSL mark; Event Logo folder so All Regattas / landing cards use the std left slot) |
| **Centre** | Event name · `Host: MAC - Milnerton Aquatic Club` (link `/club/mac`) · gold status stack |
| **Right** | Host club logo — MAC from `/api/club-logo/MAC` |

Gold centre stack (same as Ullman upcoming / 420 raced):

- Before racing: `Upcoming Event — 17–18 Oct 2026` plus people-icon `N Entries` (0 is shown) plus **Notice of Race** (opens the NOR popup; `#nor` on this Event URL).
- After the first scored race: `Results are Provisional` + as-at date line + entries icon, from `regattas.result_status` / `regattas.as_at_time`.

No Venue line (host and venue are the same club).  
No `(snapshot time not recorded)`. Do not invent as-at from the event dates.

---

## Live cards (this Event URL only)

Order under the header: **Wind → Media → (Cam later) → TSL Fleet**.

| Card | Status |
| --- | --- |
| **Wind** | Live. Gold slot card. Data from [Wind2Speed widget 3](https://wind2speed.africa/widgetPage/3) / station **W2SMAC01** via `GET /api/wind2speed/mac` (`apidata/wsdata/3`). Dial + 1h spark + Now/Avg/Gust kt. |
| **Media** | Same 6-slot HMYC Dart / Midmar strip: MAC Event Reels mark far left (scaled, white), 5 clip tiles from WhatsApp **MAC Media** (`/mm-clips`). Click brand → `/club/mac`. No Add Clip / News / Live / Facebook chrome. |

This Event URL is the **gold / default TSL template** — first build used for later TSL events. Keep the Event Reels club mark in the media slot; do not swap in the plain club-logo PNG there.
| **Live cam** | **Not shown.** `data-mac-cam="later"`. Wait for the MAC feed URL before adding a cam card. |

JS: `/js/mac-tsl-live-cards.js` (also `sailingsa/frontend/js/mac-tsl-live-cards.js`). NOR body: `/js/mac-tsl-nor.html`. Not loaded on other slugs.

No ENTER / event-info-strip on TSL Event URLs (no Clock / Pin / Free entry / ENTER URL editor). Fleet-entry CTA stays on Cape Classic and other non-TSL events. Live skip is slug-gated in `_render_event_info_strip_html` + `regatta-entry.js`; JS also strips leftover `#eventInfoStrip` / `.eis-sa-bar` on `[data-mac-tsl="1"]`.

---

## Notice of Race (on this Event URL)

Gold text is in `/js/mac-tsl-nor.html`. Official file: `/js/2026-10-17-mac-tsl-wc-nor.docx`. The Event URL header link **Notice of Race** pops it (`#nor`). Link slot can move later — do not change the Event URL slug.

SAS entry: https://www.sailing.org.za/events/380433  
Invitation: TSL@MAC WhatsApp. Briefing Saturday 17 Oct 09:00 at the MAC clubhouse. Racing done by 16:00 Sunday. SI from the RO / clubhouse notice board.

NOR teams (8): EDEN, OVERBERG, ZVYC, RCYC Training Centre, Stellenbosch University Sailing Club, UCT Sailing Club, IZIVUNGU, MAC.

Scoring in the NOR is **3-on-3 positional** (places 1–6 summed; **lowest team score wins**), knockout / 28-race round-robin for 8 teams. Store race numbers in `R1`… — not Appendix A, not W/L.

---

## Fleet header + its data

Same `.class-header` as other Event URLs:

- TSL class logo (left of title)
- Title: **TSL Fleet**
- Sailed line: `Sailed: 0, Discards: 0, To count: 0, Entries: N, Scoring system: Team Racing`
- Empty `.table` until Saturday (block exists so the header renders)

Entries update this fleet only. Slug stays.

---

## Results table columns (team racing — one row per team)

Gold fleet order is Rank | Class | Sail No | Club | Helm | Crew | R1..Rn | Total | Nett.  
TSL is **team vs team**, not Appendix A boats. Map onto `public.results` like this:

| Display | `results` column | Admin live |
| --- | --- | --- |
| Rank | `rank` | From race outcomes (NOR / RO). Ties “not possible” per structure answers. |
| Team | `boat_name` | Text (Eden District, Maties, …) |
| Club | `club_raw` + `club_id` | Club code (MAC, Maties, GYLC, …) |
| Helms | `helm_name` | Three names, `"; "` joined (Title Case, SAS ID is the person) |
| Crews | `crew_name` | Three names, `"; "` joined |
| Helm SAS | `helm_sa_sailing_id` | First helm SAS; others in notes / later crew2 if needed |
| R1 … Rn | `race_scores` JSON `R1`… | Team race score (sum of 3 boat places) |
| Wins | derived | Knockout / round-robin wins |
| Losses | derived | Computed |
| Nett | `nett_points_raw` | Lower is better (NOR) |

Hidden / unused until a sheet needs them: Sail No, Jib, Bow, Hull, Class (always TSL).

Do **not** invent Appendix A places. Do **not** write race scores until the first race is sailed.

Match scoring stays **3-on-3 positional** (lowest team total wins). The overall table cells show **W / L / —** after a match is completed (official TSL scoresheet). Numeric place totals are stored on `tsl_event_matches`, not as Appendix A points.

Known teams so far (seed as entry rows, rank NULL, no races):

1. **MAC** (verified 2026-10-12) — `sailingsa/deploy/seed_mac_tsl_mac_team_roster.py`

   | Boat | Helm | Crew |
   | --- | --- | --- |
   | 1 | Kamva Mgcubhe **13516** | Maddison Smit **21052** |
   | 2 | Tristan Gress **8612** | Thandokazi Sibanyoni **29414** |
   | 3 | Unam Lubhelwana **13517** | Alexa Aab **22974** |

   Club `club_id=58`. Thandokazi’s `full_name` in SAS is `Sibanyoni, Thandokazi`; display uses first+last. No second MAC team in the event DB.

2. S.A. Sailing Eden District — Lulonke Lenks, Christiaan Cilliers, Isabella Watson, Arthur Watson, Owen Conradie, Rainier Lamprecht (roles not given)
3. Stellenbosch University / Maties — helms Corben Smith, Conrad Holm, Chiara Fruet; crews Shakur Abrahams, Nadia Bahnemann, Robyn Rosselli

---

## Admin live results (TSL dropdowns)

**Admin URL (same Event URL, Super Admin toggle On):**  
https://sailingsa.co.za/regatta/2026-10-17-mac-tsl-wc-team-sailing

- **Who:** Super Admin (`regatta-sa-toolbar.js` already on the Event URL). Club manager later if MAC has one.
- **Flights** card sits between the Fleet gold table and the Teams card. Flights open in pairs (1–2), (3–4)… newest pair on top, half-width. Click the centred **Flight N** title to collapse that card to the title only (closed / hide mode uses a pale green background). Show/hide sticks in the browser after refresh. When both flights in a pair are posted to the gold table, the next pair opens above the closed pair. **Max 28 flights** (last pair 27–28); the Event URL will not open Flight 29+. Columns: **Rank | Colour | Bow no | Team | Sailors**. Choosing a team writes the next free helm/crew pair into Sailors as `Kamva M (H), Maddison S (C)`. The Sailors picker lists full names with Helm/Crew; the table cell stays short. Click Sailors to pick another unused pair for that team in the flight. Used pairs drop out until one remains. Rank is only editable when Colour, Team and Sailors are filled; Enter or click-away saves, then rows sort 1–6. Places are **1–6**. Standard codes (**DNC DNS DNF RET DSQ OCS BFD UFD DPI NSC DNE**) are allowed and annotate as the code; they score **boats + 1** (7). Below each flight, after a gap, a note table lists each team in the flight: **Team | B1…Bn | Total**, one **B** column per boat entered (bow no), showing that boat’s rank or code. When a flight is complete, each team’s boat-rank total writes into the overall gold table **F1…Fn**, Total, and Rank (lowest wins). Bow no is 1–6 and not editable. Colour is an empty square that toggles Blue then Green (max 3 of each; if only 2 boats have a team, max 1 of each). Team and Sailors open the same centred `.card` popup. Row height matches the Teams roster tables. Gold sheet columns are **F1…Fn** (flights, not races). Boat-count logic follows how many boats have a team allocated. The Schedule / Generate schedule block is hidden on the Event URL.
- **TEAMS** card sits below Flights. Club and sailor fields are searchable dropdowns against existing `clubs` / `sas_id_personal`. Team name defaults to the club name and must stay unique on the event (second club team = a different name, not invented sailors).
- **M+ / M−** sit on the existing TSL fleet header (same slot as Cape Classic R+ / R−). They create/remove `tsl_event_matches` only. Dart 18 / Midmar / Appendix A `club-score-edit.js` is **not** loaded here.
- **Match entry** card is below the overall results table: Team A / Team B dropdowns (registered teams only), Blue/Green colours, three boats each with bow / sail / helm / crew / place / penalty. Helm and crew lists are that team’s master roster only.
- **Save match once** scores Appendix D3 (lowest total wins), then rewrites the existing results table cells to W / L / — and recalculates standings. Official override requires a reason and is audited.
- **Status line:** first scored race → `Results are Provisional as at DD Month YYYY at HH:MM` from the sheet clock. Final when the OA says so.
- **Public:** never edits scores. Empty match columns stay hidden until M1 exists.
- **MP:** Rank | Club | Colour | M1… | Wins. **ML:** same table, extra columns (team / sailors / losses / win %) — no second table.

**Sailor replace / New Team / add sailors:** `docs/TSL_SAILOR_SEARCH_POPUP.md` — landing `/api/search`, body-fixed `.card`, hit row `name | club logo | SAS ID`. New Team card stays last; club search then team name then 1–6 sailors with M/F and Helm/Crew.

Code: `sailingsa/backend/tsl_team_racing.py`, `sailingsa/backend/tsl_schedule.py`, `js/mac-tsl-admin.js`.

Tests:
`python3 -m sailingsa.backend.test_tsl_team_racing`
`python3 -m sailingsa.backend.test_tsl_schedule`
`python3 -m sailingsa.backend.test_tsl_admin_js`

Formats (backend only — Schedule / Generate schedule is hidden on the Event URL):

* **rr28** — 8 teams, 28 unique pairings, stay-on-boats then 4/3 Blue-Green.
* **flights16** — Flight A 6 + Flight B 6 + M13–M16 sail-offs (A1vB1 … A4vB4). M13 winner is Regional Champion.

Physical boats: `tsl_event_boats` (Blue 1–3, Green 1–3). Bow/sail are per-match allocations, not permanent sailor IDs.

Live apply later (do not overwrite live `api.py`): copy the backend modules + JS, then `python3 sailingsa/deploy/patch_live_mac_tsl_results.py /var/www/sailingsa/api/api.py`. **Do not deploy without approval.**

Clips come only from WhatsApp group **MAC Media** (same `/mm-clips` path as Dart / Midmar). There is no Add Clip box on the Event URL. Bind: `event_whatsapp_groups.group_name='MAC Media'`. Box number **076 263 9937** (GoWifi) must be in that group. Cam card waits for the MAC URL.

Live apply (full-box SSH): `docs` + `sailingsa/deploy/SSH_LIVE.md`.

1. Snapshot `/var/www/sailingsa/api/api.py` then `chattr -i`.
2. `python3 sailingsa/deploy/create_2026_mac_tsl_wc_event_url.py` with live `DB_URL`.
3. Surgical patch only: `python3 sailingsa/deploy/patch_live_mac_tsl_wc_event_url.py /var/www/sailingsa/api/api.py` (wind `/api/wind2speed/mac`, TSL logo rules, Upcoming Event + dates + entries icon, inject `/js/mac-tsl-live-cards.js`).
4. Copy `js/mac-tsl-live-cards.js` → `/var/www/sailingsa/js/`.
5. `chattr +i`, restart `sailingsa-api`, delete `/var/tmp/sailingsa_regatta_with_counts.json`.

Never replace live `api.py` with this repo snapshot.

**Live (2026-10-12):** Event URL is up. SAS event 380433 linked as `events.event_id=202753`. Cam still later.
