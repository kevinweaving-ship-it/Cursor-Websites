# Event URL standard — Header + Fleet + Results table

**GOLD — hard rule.** Every Event URL must comply (old and new).

**Source of truth:** [2026 Zeekoe Vlei Cape Classic](https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic).

## Top-down (what you validate, in this order)

Work **down the page**. Do not skip a layer. Do not invent data.

| Layer | What gold looks like | Validate from | If it cannot be matched |
| --- | --- | --- | --- |
| **0. Landing / Regatta list** | Event appears on the landing Regatta pill when it has results, **or** its start date is current (today through +5 days SA and not ended) | `regattas.start_date` / `end_date`, `results` count. List cache is **2 minutes** — race-day and amendments must show | Leave off the list only if there is no Event URL / no regatta row. Do not hide a current start-date event because a cache is old |
| **1. Event header** | Event logo left · name / Host / status / as-at / Entries · Host logo right | Event artwork map; `host_club_*`; `result_status`; `as_at_time`; entry count from results | Empty slot + **note admin**. Never put a class or host logo in the event-logo slot |
| **2. Fleet card** | Class logo left · **class logo + word `Fleet` only** · Host logo right · sailed line | Class catalogue / `class_id`; stored `fleet_label`; host club artwork | Mixed / no class: left = host club, title stays text (`Keelboat Fleet`). **Note admin**. Do not invent a class mark |
| **3. Results table** | Rank · Class · Sail No · Club · Helm · races · Total · Nett | Official sheet / DB only. Times and ranks from the source file. Names only if the source changes them | Wrong time/rank: correct from the sheet. Names already validated: **do not rewrite**. Unmatched club / SAS: leave empty, **note admin** |

**Validate** means: the on-page value must come from a real field or the official results file. Find / match / auto is allowed. Guessing is not.

### Data validation — do / do not

**Do**

- Status + as-at from `regattas.result_status` and `regattas.as_at_time` (not “now”, not the event start date).
- Event URL as-at **display**: two tight lines — `Results are Final` (or Provisional), then `D Mon YYYY HH:MM` on **one** line (`13 Sep 2026 18:03`).
- Venue only if it is **different** from the host club name.
- Fleet title: class logo is the name; the word is `Fleet` only. Same logo as the left column when that logo exists.
- Scoring / ToT / Appendix A on the **sailed line only**, never in the fleet title.
- Times, ranks, ToT, corrected, delta: from the official sheet (rev1 = that file only).
- Names, sail numbers, boats: leave once validated. Correct time/rank only unless the user says names are wrong.
- Club column: logo · divider · code, codes starting in one column.
- Class column: class logo if valid; else class name.

**Do not**

- Invent a logo, class, fleet name, club, or sailor.
- Rename a mixed fleet to a single class.
- Put scoring in `fleet_label` / `block_label_raw`.
- Copy Weather or MM Card onto a standard Event URL (Cape Classic / Lipton special-add only).
- Treat a 7-day list cache as truth. If the event is running or results changed, the landing list must refresh.

That page is the standard for all three:

1. **Event header**
2. **Fleet card**
3. **Results table**

Do not invent a different layout per event. Apply this layout. Where a logo, fleet name, or class cannot be found / matched / auto: **leave it**, **note it**, and **admin deals with it**. Do not guess.

## Admin help — leftovers (logo / fleet name / class)

When auto-match fails:

1. **Leave** the Event URL as-is on that slot (empty logo, existing text name, etc.).
2. **Note** the event URL, fleet, and what is missing or wrong.
3. **Ask admin.** Do not invent a logo. Do not rename a mixed fleet. Do not put a host logo in the event-logo slot or a class logo in the host-right slot.

Admin then:

- Provide the artwork, or
- Confirm the fleet / class name, or
- Approve leaving that slot empty.

Agents do not close those items themselves.

## Event header (hard rule)

| # | Slot | Required |
| --- | --- | --- |
| 1 | **Left** | **Event logo** |
| 2 | **Centre** | Event name → Host → Results status → as-at date & time → Entries |
| 3 | **Right** | **Host club logo** |

Centre stack, in order:

1. Event name (e.g. `2026 Zeekoe Vlei Cape Classic`)
2. `Host: CODE - Full Club Name` (e.g. `Host: ZVYC - Zeekoe Vlei Yacht Club`)
3. Venue **only if different from host**
4. `Results are Final` (or Provisional) — tight to the as-at line
5. `DD Mon YYYY HH:MM` (date and time on the **same** line, e.g. `13 Sep 2026 18:03`)
6. **gap** then people icon + `N Entries`

Do **not** copy Weather or the Marine Megastore card onto a standard Event URL.

### Event logo left — if missing or wrong

1. Try find / match / auto (event artwork, known Event Logo map).
2. If you **cannot find, match, or auto** a correct Event logo: **stop and ask admin** to guide or provide the file.
3. Do **not** invent a logo. Do **not** put a class logo or host logo on the left of the Event header.

### Status + entries (centre)

Two status lines stay **tight** to each other. Then a **clear gap** before Entries.

1. `Results are Final` (or Provisional)
2. `DD Mon YYYY HH:MM` (as-at)
3. **gap** (`.regatta-header-status-stack .entry-total-line { margin-top: 14px }`)
4. people icon + `N Entries`

CSS: wrap those three rows in `.regatta-header-status-stack`. Status lines `gap: 1px` / `margin: 0`. Do not use the old `.status-line { margin-top: 8px }` between the two status lines.

## Not part of the Event standard

**Weather** and **MM Card / Event Reels** are a special add on Cape Classic 2026 (and Lipton). They are **not** on a standard Event results URL.

Later, if a club page already has a weather station **and** an MM card (example: [ZVYC](https://sailingsa.co.za/club/zvyc)), and that club has another **live** event, admin can request Weather + MM / Live for that event only. Do not add them by default.

## Fleet header (GOLD / hard rule)

**Source:** Extra card on [Cape Classic](https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic). This is the standard Fleet card for 99% of old fleets and every new fleet.

| # | Slot | Required |
| --- | --- | --- |
| 1 | **Left** | **Fleet / class logo** (large). If there is no class logo (mixed fleet e.g. Keelboat): **host club logo**. |
| 2 | **Centre** | **Class logo** immediately left of the word `Fleet` only. Not `Hunter 19 Fleet`, not `Hobie Fleet`, not `ILCA 7 Fleet` as text. The logo is the name. |
| 3 | **Right** | **Host club logo** |

Then the sailed line under that header, exactly this shape:

`Sailed: 5, Discards: 1, To count: 4, Entries: 19, Scoring system: Appendix A`

Scoring never goes in the title. It lives on this line only.

### Fleet logos — if missing or wrong

Any of the three logos (left fleet, small title fleet, host right):

1. Try find / match / auto (class catalogue artwork, host club artwork).
2. If you **cannot find, match, or auto**: **stop and ask admin** to guide or provide the file.
3. Do **not** invent a logo. Do **not** put a class logo on the host-right slot.
4. **No class / mixed fleet** (Keelboat): left slot is the **host club logo**. Keep the stored fleet name as text (`Keelboat Fleet`). Ask admin if a dedicated fleet mark exists.

## Results table (GOLD / Extra)

Column order: **Rank** → **Class** → **Sail No** → **Club** → Helm → races → Total → Nett.

- **Class:** class logo when a valid class logo exists. If there is no class logo, show the class name. If the logo cannot be found or matched: **ask admin**.
- **Club:** logo left, light vertical divider, then club code. Codes all **start in the same column**. Do **not** push the code to the far right. Club column is only as wide as logo + divider + code; leftover width goes to Helm / Crew.

Race codes (`DNC`, `OCS`, `RET`, …) stay **overlaid** (no extra row height). Centre under the score, lift slightly off the bottom, size about as wide as `(20)` (`font-size: 50%`).

## Class == fleet

When the block is a single class (class name and fleet name are the same after stripping a trailing `Fleet`), use the standard above. Keep the stored `fleet_label` casing (`ILCA 6 Fleet`, not a catalogue rewrite).

Examples: `420 Fleet`, `Hunter 19 Fleet`, `ILCA 6 Fleet`.

## Class != fleet — leave as is

Do **not** rename or invent a class logo when the fleet is mixed or the fleet name is not the class name.

Examples: `Open A Fleet`, `Hobie Fleet` (class is Hobie 16), `Keelboat Fleet` (L26 / Beneteau / Sadler). Keep the stored `fleet_label`. Still strip scoring text from the title.

## Never put scoring in a fleet title

`block_label_raw`, `fleet_label`, and the on-page title must **not** include scoring or rating:

- Forbidden: `Hobie Fleet — ToT - Custom`, `Hunter 19 Fleet — ToT - Custom Fleet`, `… Appendix A Fleet`
- Scoring system (`ToT - Custom`, `Appendix A`, …) lives on the **sailed line only**
- `block_label_raw` should match the fleet name (`Hobie Fleet`), not `{fleet} — {scoring}`

Live title builder: `_strip_scoring_system_from_fleet_title` in `/var/www/sailingsa/api/api.py`.

## Exceptions (do not “fix”)

- **Lipton**: Event logo left, class logo right (not host on the right of the fleet card).
- **Cape Classic 2026 ZVY**: same logo + word `Fleet` title as every other Event URL (this is the gold source, not a special case).
- **MAC / TSC endurance**: keep specialised block titles (Line Honours, Handicap, etc.).
