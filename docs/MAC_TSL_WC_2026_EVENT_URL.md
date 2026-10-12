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

---

## Std header (do not invent a new layout)

Same `.header` as every Event URL / results sheet:

| Slot | Content |
| --- | --- |
| **Left** | Event logo — `/artwork/Class Logo/TSL-Class-Logo.png` (`_regatta_named_event_logo_url`) |
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
| **Media** | Same 5-clip card as HMYC Dart / Midmar. MAC club logo in the HMYC logo slot. `/mm-clips` for this slug. WhatsApp group **MAC Media**. |
| **Live cam** | **Not shown.** `data-mac-cam="later"`. Wait for the MAC feed URL before adding a cam card. |

JS: `/js/mac-tsl-live-cards.js` (also `sailingsa/frontend/js/mac-tsl-live-cards.js`). NOR body: `/js/mac-tsl-nor.html`. Not loaded on other slugs.

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
NOR scoring is positional 3-on-3 (lowest team total wins), not W/L.

Known teams so far (seed as entry rows, rank NULL, no races):

1. S.A. Sailing Eden District — Lulonke Lenks, Christiaan Cilliers, Isabella Watson, Arthur Watson, Owen Conradie, Rainier Lamprecht (roles not given)
2. Stellenbosch University / Maties — helms Corben Smith, Conrad Holm, Chiara Fruet; crews Shakur Abrahams, Nadia Bahnemann, Robyn Rosselli

---

## Admin live results

- **Who:** Super Admin (`regatta-sa-toolbar.js` already on the Event URL). Club manager later if MAC has one.
- **When:** Saturday 17 Oct after first warning (11:00). Add R1, then R2… Do not change the slug.
- **How:** Enter each team-race as the 3-boat place total on the team row (NOR: lowest score wins). Injury sub only, RO approval, same roster. Final sheet signed off by Race Officer / Coordinator.
- **Status line:** first scored race → `Results are Provisional as at DD Month YYYY at HH:MM` from the sheet clock. Final when the OA says so.
- **Public:** never edits scores. Empty race columns stay hidden until R1 exists.

Super-admin drop and WhatsApp **MAC Media** both write this slug’s `/mm-clips` (same as Dart / Midmar). Bind: `event_whatsapp_groups.group_name='MAC Media'`. Box number **076 263 9937** (GoWifi). Cam card waits for the MAC URL.

Live apply (full-box SSH): `docs` + `sailingsa/deploy/SSH_LIVE.md`.

1. Snapshot `/var/www/sailingsa/api/api.py` then `chattr -i`.
2. `python3 sailingsa/deploy/create_2026_mac_tsl_wc_event_url.py` with live `DB_URL`.
3. Surgical patch only: `python3 sailingsa/deploy/patch_live_mac_tsl_wc_event_url.py /var/www/sailingsa/api/api.py` (wind `/api/wind2speed/mac`, TSL logo rules, Upcoming Event + dates + entries icon, inject `/js/mac-tsl-live-cards.js`).
4. Copy `js/mac-tsl-live-cards.js` → `/var/www/sailingsa/js/`.
5. `chattr +i`, restart `sailingsa-api`, delete `/var/tmp/sailingsa_regatta_with_counts.json`.

Never replace live `api.py` with this repo snapshot.

**Live (2026-10-12):** Event URL is up. SAS event 380433 linked as `events.event_id=202753`. Cam still later.
