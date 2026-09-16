# Fleet-card gold leftovers

**Status (2026-09-16):** ~90%+ of Event URL fleet cards comply with Cape Classic gold. Come back here for the rest. Do **not** invent a logo, class, or fleet name.

**Gold:** [2026 Zeekoe Vlei Cape Classic](https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic)

Fleet card: class logo left · logo + the word **`Fleet`** centre · host logo right · then

`Sailed: N, Discards: N, To count: N, Entries: N, Scoring system: Appendix A`

`To count` must equal `Sailed − Discards`. Scoring never in the title. `Overall` is not a fleet name.

Live renderer patch: `GOLD_FLEET_HEADERS_v1` on `/var/www/sailingsa/api/api.py`. Deploy script: `sailingsa/deploy/apply_gold_fleet_headers_v1.py`.

---

## Already gold (do not reopen)

- Single-class dinghy / ILCA / Hunter 19 / Hobie / Extra / Open-with-Open-mark: logo + `Fleet`, host logo right.
- Mixed Keelboat with no class mark: text `Keelboat Fleet`, host logo left (Vulcan).
- DF95 gold / silver / bronze: gold sailed tokens (Q/F score columns stay).
- Checksum: renderer always sets `To count = Sailed − Discards`.
- Scoring stripped from titles (Mykonos Multi → `Multi Fleet`).
- Single-class `Overall` → real class (Mirror Nationals logo + `Fleet`; 2021 Lipton Cape 31; 2022–2024 Lipton `ORC Fleet` when that is the stored class).
- ToT: no extra `Rating system:` token on the sailed line (scoring system already says ToT).
- 769 standard fleet cards have left + right logos.

---

## Come back — need admin

### 1. Mixed fleets still titled Overall

Many classes in one block. Do not guess `Open` / `Keelboat`. Ask what the centre should say.

| Event URL | Current title |
| --- | --- |
| https://sailingsa.co.za/regatta/2026-07-26-brass-monkey-regatta | Overall Fleet |
| https://sailingsa.co.za/regatta/2026-04-12-wc-youth-regatta | Overall Fleet |
| https://sailingsa.co.za/regatta/2026-04-05-fbyc-easter-regatta | Overall Fleet |
| https://sailingsa.co.za/regatta/2025-10-19-ec-champs | Overall Fleet |
| https://sailingsa.co.za/regatta/2025-05-18-double-cape | Overall Fleet |
| https://sailingsa.co.za/regatta/2024-10-05-nks-grand-prix-series-4 | Overall Fleet |
| https://sailingsa.co.za/regatta/2024-09-28-wc-youth-regatta | Overall Fleet |
| https://sailingsa.co.za/regatta/2024-06-01-legend-frank-lenz-race | Overall Fleet |
| https://sailingsa.co.za/regatta/2024-05-05-double-cape | Overall Fleet |
| https://sailingsa.co.za/regatta/2024-01-28-king-of-vaal | Overall Fleet |
| https://sailingsa.co.za/regatta/2023-02-25-mykonos-offshore | Overall Fleet |
| https://sailingsa.co.za/regatta/2025-01-01-hmyc-grand-slam-multihull | Multihull Overall Division Fleet |
| https://sailingsa.co.za/regatta/2019-12-22-winter-2019-hbyc-wednesdaysummer19-20 | Overall Fleet |

Also mixed Overall / All (same rule, not on the first visual pass): `2024-03-03-admirals-regatta-orc`, `2025-07-07-rcyc-youth-regatta`.

### 2. No class logo in the catalogue

Leave text. Add artwork only when admin supplies it, then logo + `Fleet`.

| Class text | Example Event URL |
| --- | --- |
| IOM | https://sailingsa.co.za/regatta/2024-10-20-iom-nationals — also Mpumalanga IOM, DF95+IOM |
| Musto Skiff | HMYC club champs 2024-07-07 |
| Jaz 25 | HMYC club champs 2024-07-07 |
| Stadt 26 | HMYC club champs 2024-07-07 |
| Theta 26 | HMYC club champs 2024-07-07 |
| Mistral / Mistral Fin | L26 FS provincials; SASNR keelboat champs 2019 |
| Topaz Duo | https://sailingsa.co.za/regatta/2023-04-10-msc-dinghy-western-cape-champs |

Named/mixed **text that should stay text** (not a fail): `Keelboat Fleet`, `WSEH Fleet`, `ORC Fleet`, `PHRF Fleet`, `Division A Fleet`, `Non ORC Fleet`, `Multihull Fleet`, `Fast Fleet`, `Slow Fleet`.

### 3. Mykonos Multi — no race scores

https://sailingsa.co.za/regatta/2025-03-01-mykonos-race-multi-01032025

Title is `Multi Fleet`. All 3 rows have empty `race_scores`, so the line is `Sailed: 0`. Need the official race count / sheet before filling.

### 4. MAC / TSC endurance (not the Cape Classic card)

Specialised Line Honours / handicap blocks. Leave unless admin asks to redesign.

- https://sailingsa.co.za/regatta/2026-03-29-mac-24-hour-challenge (`Overall (Handicap)` / `Overall (Line Honours)` — exception)
- https://sailingsa.co.za/regatta/2025-03-30-mac-24hr
- https://sailingsa.co.za/regatta/2025-03-14-tsc-9hr
- https://sailingsa.co.za/regatta/2024-03-24-mac-12hr

### 5. Lipton fleet-card exception (not a fail)

Documented: event logo left, class logo right. 2026/2025 centre still reads `J22 Fleet` (class mark is on the right). Do not force logo + `Fleet` in the centre unless admin says so.

### 6. Optional later

- Persist official `as_at_time` where the Event URL header already shows an inferred clock (often `17:00`). Header work, not fleet-card.
- Phone / MP score-sheet sticky — **paused**. Do not resume until asked.

---

## How to resume

1. Read this file and `docs/FLEET_HEADER_STANDARD.md` (Cape Classic gold) if present on the branch.
2. Do not invent logos or mixed-fleet names. Ask admin for §1–§3.
3. After admin names a mixed Overall fleet or supplies a class mark, set `regatta_blocks.fleet_label` / catalogue artwork only — then the existing gold renderer will draw logo + `Fleet`.
