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

---

## Std header (do not invent a new layout)

Same `.header` as every Event URL / results sheet:

| Slot | Content |
| --- | --- |
| **Left** | Event logo — `/artwork/Class Logo/TSL-Class-Logo.png` (`_regatta_named_event_logo_url`) |
| **Centre** | Event name · `Host: MAC - Milnerton Aquatic Club` (link `/club/mac`) · status line only when `as_at_time` is set |
| **Right** | Host club logo — MAC from `/api/club-logo/MAC` |

No Venue line (host and venue are the same club).  
No `(snapshot time not recorded)`. Empty status until racing has a real as-at time.

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
| Rank | `rank` | Auto from wins, then race-off / nett |
| Team | `boat_name` | Text (Eden District, Maties, …) |
| Club | `club_raw` + `club_id` | Club code (MAC, Maties, GYLC, …) |
| Helms | `helm_name` | Three names, `"; "` joined (Title Case, SAS ID is the person) |
| Crews | `crew_name` | Three names, `"; "` joined |
| Helm SAS | `helm_sa_sailing_id` | First helm SAS; others in notes / later crew2 if needed |
| R1 … Rn | `race_scores` JSON `R1`… | **W** / **L** (or points if NOR says so) |
| Wins | derived / `nett_points_raw` | Computed |
| Losses | derived | Computed |
| Nett | `nett_points_raw` | Wins, or points if NOR uses points |

Hidden / unused until a sheet needs them: Sail No, Jib, Bow, Hull, Class (always TSL).

Do **not** invent Appendix A places. Do **not** write race scores until the first race is sailed.  
NOR / SI still outstanding — if the sheet is points not W/L, keep the same columns and store numbers in `R1`… instead of W/L.

Known teams so far (seed as entry rows, rank NULL, no races):

1. S.A. Sailing Eden District — Lulonke Lenks, Christiaan Cilliers, Isabella Watson, Arthur Watson, Owen Conradie, Rainier Lamprecht (roles not given)
2. Stellenbosch University / Maties — helms Corben Smith, Conrad Holm, Chiara Fruet; crews Shakur Abrahams, Nadia Bahnemann, Robyn Rosselli

---

## Admin live results

- **Who:** Super Admin (`regatta-sa-toolbar.js` already on the Event URL). Club manager later if MAC has one.
- **When:** Saturday 17 Oct after first warning (11:00). Add R1, then R2… Do not change the slug.
- **How:** Enter each team-race as W/L on the team row (same idea as Dart place entry on `club-score-edit.js`, TSL-specific). Rank recalculates from wins.
- **Status line:** first scored race → `Results are Provisional as at DD Month YYYY at HH:MM` from the sheet clock. Final when the OA says so.
- **Public:** never edits scores. Empty race columns stay hidden until R1 exists.

Live apply (SSH, not Cloud-only): `docs` + `sailingsa/deploy/SSH_LIVE.md`. Clear `/var/tmp/sailingsa_regatta_with_counts.json` after insert. Never replace live `api.py` with this repo snapshot.
