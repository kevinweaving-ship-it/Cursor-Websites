# Event URL gold — Cape Classic (Appendix A / Low Point)

**GOLD — hard rule.** Every Event URL must comply (old and new).

**Source of truth:** [2026 Zeekoe Vlei Cape Classic](https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic).

**Scoring standard (~90% of events):** Appendix A Low Point. That is the gold. Do **not** write or validate Event URLs as if they were Time-on-Time. ToT / handicap / endurance are exceptions (see the end). They follow the same header, fleet card, names, and class rules. Only the score cells change.

Do not invent a logo, class, fleet name, club, SAS ID, or sailor. Find / match / auto is allowed. If it cannot be matched: **leave it**, **note it**, **admin deals with it**.

---

## Work top-down. Do not skip a layer.

Display is last. Names, class, club, and scores must be validated **before** the page is treated as gold.

| Step | What | Authority |
| --- | --- | --- |
| **0** | Landing / Regatta list | Event shows when it has results **or** start date is current (today through +5 SA and not ended) |
| **1** | Intake | Official sheet + `regattas` row. URL/dates from `start_date` / `end_date`, never ingest time |
| **2** | Event header fields | Name, host, status, as-at, entries |
| **3** | Fleet / block + sailed line | `fleet_label`, `races_sailed`, `discard_count`, `to_count`, `entries`, `scoring_system` |
| **4** | Class (every row) | `class_original` from sheet → `class_canonical` exact `classes.class_name` |
| **5** | Helm (every row) | SAS match → canonical name. No match → leave + admin. Never invent an SA ID |
| **6** | Crew (every row the class requires) | Same as helm. Crew column follows `crew_policy` |
| **7** | Sail number + club | Sheet sail no (no country prefix). Club from sheet then SAS / `clubs` |
| **8** | Race scores | Low Point values, discards in `( )`, penalties as `{entries+1}.0 CODE` |
| **9** | Total / Nett / Rank | Total = all races. Nett = Total − discards. Rank by Nett |
| **10** | Display | Header → fleet card → results table |

---

## 1. Intake

From `docs/RESULTS_PASSING_WORKFLOW.md` and `docs/README_RESULTS_INGESTION.md`:

1. Confirm the regatta against admin / `regattas`.
2. Verify the official results sheet (local and URL). If OCR/extraction fails: stop and request the sheet.
3. **URL and dates** come from `regattas.start_date` / `end_date`. Never ingest timestamp, never “today”. Re-import must keep the same Event URL.
4. Store header fields on `regattas`; store fleet scoring fields on `regatta_blocks`.

---

## 2. Event header (fields, then layout)

### Fields (validate first)

| Field | Source | Rule |
| --- | --- | --- |
| Event name | `regattas` | Display is **year + event name only** (`2026 Zeekoe Vlei Cape Classic`). Not the start date (`2026-04-06 …`). Date stays on the as-at line. Do not invent a different title |
| Host | `host_club_code` + club full name | `Host: CODE - Full Club Name`. If `host_club_id` is set and code is empty, fill code from `clubs.club_abbrev` |
| Venue | `regattas.venue` | Show **only if different** from the host club name |
| Status | `regattas.result_status` | `Provisional` or `Final`. Never “now” |
| As-at | `regattas.as_at_time` | Sheet as-at. Never current clock, never event start/end as a placeholder |
| Entries | Count of result rows | People icon + `N Entries` |

Event URL **display** of status (Cape Classic gold):

1. `Results are Final` (or Provisional)
2. `DD Mon YYYY HH:MM` on the **same** line (`13 Sep 2026 18:03`)
3. Gap, then Entries

Reports / iframe sheets still use the long sentence: `Results are [Provisional|Final] as at DD Month YYYY at HH:MM`. See `docs/RESULTS_HTML_STATUS_LINE_RULE.md`.

### Layout

| # | Slot | Required |
| --- | --- | --- |
| 1 | **Left** | **Event logo** |
| 2 | **Centre** | Event name → Host → (venue if different) → Results status → as-at → Entries |
| 3 | **Right** | **Host club logo** |

Event logo: find / match / auto. If none: empty slot + **note admin**. Do not put a class or host logo in the event-logo slot.

Do **not** copy Weather or the Marine Megastore card onto a standard Event URL. Those are Cape Classic / Lipton special-add only.

CSS: wrap the two status lines + Entries in `.regatta-header-status-stack`. Status lines tight (`gap: 1px`). Entries gap: `.regatta-header-status-stack .entry-total-line { margin-top: 14px }`.

---

## 3. Fleet / block + sailed line

Create one block per fleet. `block_id` = `{regatta_id}:{fleet-slug}` (colon, single year, no quotes). `fleet_label` is the real fleet name — never `Overall`.

On the **sailed line only** (never in the fleet title):

`Sailed: 5, Discards: 1, To count: 4, Entries: 19, Scoring system: Appendix A`

| Token | Field | Meaning |
| --- | --- | --- |
| **Sailed** | `regatta_blocks.races_sailed` | Races completed in this fleet (R1…Rn) |
| **Discards** | `regatta_blocks.discard_count` | How many worst races each boat may drop |
| **To count** | `regatta_blocks.to_count` | Must equal `races_sailed − discard_count` |
| **Entries** | count of rows in the block | Boats in this fleet |
| **Scoring system** | `regatta_blocks.scoring_system` | Default **`Appendix A`**. Must be populated |

Checksum: `to_count = races_sailed − discard_count`. If the sheet says Discards: 1 and Sailed: 5, To count must be 4.

Forbidden in `fleet_label` / `block_label_raw` / on-page title: `Appendix A`, `ToT - Custom`, rating names. Live stripper: `_strip_scoring_system_from_fleet_title`.

---

## 4. Class validation (every row)

Authority: `docs/CLASS_CANONICAL_VALIDATION_RULES.md`, `docs/README_RESULTS_INGESTION.md`.

HTML and Event URL use **`class_canonical` only**. Never display `class_original`.

1. Copy the sheet class into `class_original` exactly (`Lazer 7`, `MIRROR (D/H)`, `29-er`). Do not tidy this field.
2. Normalise for lookup only: TRIM, collapse spaces.
3. Resolve in this order only:
   - exact match to `classes.class_name` (case-insensitive compare, store the **exact** `class_name` spelling)
   - else `class_aliases.alias` → that `class_id`
4. Only classes with `is_race_class = TRUE` go into `results`. Family rows (Optimist, ILCA) are not race classes — use Optimist A / B / C, Ilca 4.7 / 6 / 7.
5. Store `class_canonical` = exact `classes.class_name`. Examples that must not be guessed:
   - `Ilca 4` is **not** `Ilca 4.7`
   - `29er` is **not** `29Er` unless that is the catalogue spelling
   - `Lazer 7` → only becomes `Ilca 7` if the catalogue / alias says so
6. No fuzzy match. No auto-create class. Unknown label → **do not insert** (or leave unmatched) + `ingestion_issues` / **note admin**.
7. After entry, invalid `class_canonical` (LEFT JOIN `classes` is NULL) is a hard fail. It breaks class filter/search.

Crew column on the table follows `classes.crew_policy` (only `'single'`, `'double'`, `'Crewed'`, or NULL):

- `single` — Helm only. No Crew column.
- `double` — Helm + one crew. Crew column required when the sheet has a crew.
- `Crewed` — Helm + 2+ (`crew`, `crew2`, `crew3` as on the sheet).

If class cannot be matched: leave the class cell as the stored name (or empty), **note admin**. Do not invent a class logo.

---

## 5. Helm name validation (every row)

Authority: `docs/RESULTS_PASSING_WORKFLOW.md`, `docs/SAS_ID_RESULTS_NAME_MATCH.md`, `docs/README_RESULTS_INGESTION.md`, `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`.

List every helm **before** processing ranks.

### Match (do not invent)

1. Search `sas_id_personal` / `sailor_helm_aliases` via `resolve_helm_to_sa_id` (name + sail number). Unambiguous only.
2. If no SA ID: existing `helm_temp_id` (`TMP:N` format only).
3. If still unmatched: prior results, then sail number in the same class.
4. Batch assists (not guesses): same-surname helm/crew, club + similar surname, sail-number history, first-name-only + club, family SAS range ±10. See `docs/README_SAS_ID_MATCHING_LOGIC.md`.
5. Still unknown: `helm_sa_sailing_id = NULL`, keep sheet name, **note admin**. Never invent an SA ID. Never auto-create `TMP:` without approval.

### Canonical name (mandatory once an SA ID exists)

- Overwrite `helm_name` with `sas_id_personal.full_name` (or `first_name || last_name`).
- Nicknames (`Jacqui`, `Mike`, `Charlie`) are for matching only. Store `Jacqueline`, `Michael`, `Charles`.
- PDF misspellings are corrected **from SAS**, not “improved” by the agent.
- `helm_sa_sailing_id` is an integer with no leading zeros. It must exist in `sas_id_personal`.

### After names are validated

Do not rewrite helm names when fixing times, ranks, or scores. Names are a separate pass.

Checksum: same SA ID must not appear in two `class_canonical` values in the same regatta.

---

## 6. Crew name validation (every required crew)

Same pipeline as helm: `crew_name` / `crew_sa_sailing_id` / `crew_temp_id` (and crew2 / crew3 when the class is Crewed).

- Resolve crew **before** ranks, same as helm.
- If helm has an SA ID and crew shares the surname: try family / same-surname match first.
- If SA ID found: store canonical `full_name`, not the sheet nickname.
- If the sheet has no crew and `crew_policy` is `single`: leave crew empty.
- If `crew_policy` is `double`/`Crewed` and the sheet has a crew that will not match: keep the sheet name, SA ID NULL, **note admin**.
- Crew inherits helm club when crew has no club.

Output two lists for admin: matched sailors, and unmatched (Temp / None).

---

## 7. Sail number + club

**Sail number**

- Store as shown, minus country prefix (`RSA-3452` → `3452`). Keep suffixes (`5733R`).
- Used in helm/crew SAS matching. Do not invent a sail number.

**Club**

1. `club_raw` = exact text from the sheet (`VLC/LDYC`, `SBYC`).
2. `club_id` = first club only if the sheet lists two, resolved via `clubs` / `club_aliases`.
3. After SAS match: prefer helm `primary_club` then `club_1`; if missing, crew club.
4. Unmatched: leave `club_id` NULL, keep `club_raw` if present, **note admin**. Do not invent a club code or logo.

Display: logo · divider · code. Codes start in one column. If there is no club: empty cell.

---

## 8. Scoring — Appendix A Low Point (the 90%)

This is Cape Classic Extra and almost every dinghy / youth / class fleet.

### What Low Point means

- Finish place **is** the score: 1st = `1.0`, 2nd = `2.0`, 10th = `10.0`.
- Lowest **Nett** wins. Rank is by Nett, then the sheet’s tie-break (do not invent a tie-break).
- Penalties (DNC, DNS, DNF, RET, OCS, DSQ, BFD, UFD, DPI): points = **`entries + 1`**. 19 entries → DNC = `20.0 DNC`.
- Store the code the sheet used. Never change DNC to DNS.

### Race-score format (hard stop if wrong)

Authority: `docs/RACE_SCORES_RULES.md`, `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md`.

| Sheet shows | Store as | Why |
| --- | --- | --- |
| `5` | `5.0` | Always one decimal |
| `(11)` or `-11` or struck-through 11 | `(11.0)` | Parentheses = discard. Never a minus sign in the DB |
| `DNC` | `20.0 DNC` | Score + space + uppercase code |
| discarded DNC | `(20.0 DNC)` | Discard + penalty together |

Keys are sequential `R1`, `R2`, … (no `R01`, no gaps). Reject: `"DNC"`, `"5"`, `"-11.0"`, `"10.0DNS"`, `"dnc"`.

Run `admin/tools/validate_race_scores_pre_entry.sql` **before** insert.

### Discards

- The block rule (`Discards: 1`) applies to **every** boat in that fleet.
- Discarded cells are the **worst** scores, wrapped in `( )`.
- After insert: number of bracketed cells **per row** must equal `discard_count`.
- Worst-score check: do not bracket a `4.0` while a `11.0` is live.
- Script: `admin/tools/validate_discard_brackets_compliance.sql`.

HTML: parentheses get CSS class `disc`. Penalty tokens get `code`. Codes sit overlaid under the number (no extra row height).

---

## 9. Total, Nett, Rank

| Field | Formula | Example (Sailed 5, Discard 1) |
| --- | --- | --- |
| **Total** | Sum of **all** race numbers, **including** discarded and penalty points | `1.0 + 2.0 + 3.0 + 8.0 + (12.0)` = `26.0` |
| **Nett** | Total − sum of discarded numbers | `26.0 − 12.0` = `14.0` |
| **Rank** | Order by Nett (lowest first). Ties allowed when Nett is equal | Rank 1 = lowest Nett |

Checksum (mandatory):

```
nett_points_raw = total_points_raw − sum(discarded race values)
```

If `discard_count = 0`, Nett = Total. Nett must never exceed Total.

Store both as `.0` numerics (`15.0`, not `15`). Script: `admin/tools/checksum_total_nett_points.sql`.

Also checksum: entry count per block; `fleet_label` identical on every row in the block; `class_canonical` in `classes`; every non-null helm/crew SA ID in `sas_id_personal`.

Then extract ranks 1…n using the **already validated** helm/crew/class. Do not re-type names while passing ranks.

---

## 10. Display (only after 1–9)

### Landing / Regatta list

Show the event when it has results **or** `start_date` is in today…+5 SA and the event has not ended. List cache is **2 minutes** so race-day and amendments appear. Typed search bypasses cache. Do not hide a current start-date event because a cache is old.

### Fleet card

| # | Slot | Required |
| --- | --- | --- |
| 1 | **Left** | Class logo. Mixed / no class logo (Keelboat): **host club logo** |
| 2 | **Centre** | Class logo + the word **`Fleet` only**. The logo is the name. Not `ILCA 7 Fleet` as text |
| 3 | **Right** | Host club logo |

Then the sailed line from step 3.

Single-class fleet (class name == fleet name after stripping `Fleet`): use this card. Keep stored `fleet_label` casing in the DB (`ILCA 6 Fleet`); the title still renders as logo + `Fleet`.

Mixed fleet (`Open`, `Keelboat`): do **not** rename to one class. Title stays text (`Keelboat Fleet`). Left = host logo if there is no class mark. **Note admin**.

### Results table

Column order (Cape Classic Extra): **Rank → Class → Sail No → Club → Helm → [Crew] → R1…Rn → Total → Nett**.

- **Class:** class logo if a valid class logo exists; else `class_canonical` text.
- **Club:** logo · divider · code.
- **Helm / Crew:** validated canonical names; click through to sailor profile when an SA ID exists.
- **Races:** Low Point cells. Discards in parentheses. Codes overlaid.
- **Total / Nett:** from step 9. Rank matches Nett order.

Optional columns (Boat Name, Bow, Jib) only if the sheet has them.

---

## Admin leftovers

**Event URL title (year only):** [Western Cape Dinghy Champs](https://sailingsa.co.za/regatta/2026-04-06-western-cape-dinghy-championships) — display is `2026 Western Cape Dinghy Champs`. URL slug stays.

When auto-match fails (logo, class, helm, crew, club):

1. Leave the Event URL as-is on that slot.
2. Note event URL, fleet, row, and what is missing.
3. Ask admin. Do not invent.

---

## Exceptions (not the standard)

- **ToT / handicap / time** (small minority, e.g. some keelboat challenges): same header, fleet card, class/helm/crew validation, sailed line. Score cells are elapsed / corrected time, not Low Point. Total/Nett may equal rank. Do not treat this as gold for other events.
- **Lipton:** Event logo left, class logo right on the fleet card.
- **MAC / TSC endurance:** specialised block titles (Line Honours, Handicap).
- **Weather / MM Card:** Cape Classic / Lipton special-add only.

---

## Related (read these; do not skip)

- `docs/RESULTS_PASSING_WORKFLOW.md` — intake, header, sailor list, then ranks
- `docs/CLASS_CANONICAL_VALIDATION_RULES.md` — class original vs canonical
- `docs/README_RESULTS_INGESTION.md` — no fuzzy class, no fake SAS ID
- `docs/SAS_ID_RESULTS_NAME_MATCH.md` — helm/crew name = `sas_id_personal`
- `docs/README_SAS_ID_MATCHING_LOGIC.md` — match order when SA ID is NULL
- `docs/RACE_SCORES_RULES.md` — `.0`, `(discard)`, `N.0 CODE`
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` — hard stops before insert
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` — every results column
- `docs/RESULTS_CHECKSUM_RULES.md` — one class per sailor per regatta
- `docs/RESULTS_HTML_STATUS_LINE_RULE.md` — long “as at” sentence on sheets
