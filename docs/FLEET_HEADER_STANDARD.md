# Event / fleet header standard (results URLs)

**GOLD — hard rule** for **99% of old Event results** and **every new Event**.

**Source of truth:** [2026 Zeekoe Vlei Cape Classic](https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic).

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
5. `DD Mon YYYY HH:MM`
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

## Fleet header

Standard fleet card, Cape Classic 420 card:

| Slot | Content |
| --- | --- |
| **Left** | Class / fleet logo (class catalogue artwork) |
| **Centre** | Class logo + the word `Fleet` only (not `{Class} Fleet` as text). Scoring never belongs here. |
| **Right** | Host club logo |

Sailed line under the title stays: `Sailed: N, Discards: N, To count: N, … Scoring system: …`

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
- **Cape Classic 2026 ZVY**: existing logo + word `Fleet` title rule stays.
- **MAC / TSC endurance**: keep specialised block titles (Line Honours, Handicap, etc.).
