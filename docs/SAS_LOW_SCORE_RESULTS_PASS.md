# SAS Low Score Results Pass (LOCKED STD)

**Label:** SAS low score results pass  
**Pinned chat (source of truth):** https://cursor.com/agents/bc-01a15515-4c8d-74d1-a6bf-1ba474ec1bcf  
**Worked example (after corrections):** https://sailingsa.co.za/regatta/2026-10-17-pyc-kzn-mirror-regionals  
**Layout gold (same header/columns, race count may differ):** https://sailingsa.co.za/regatta/2026-09-24-ayc-505-nationals

When the user says **SAS Low Score Results Pass**, **low score SAS results**, **Low Point Event URL**, or **Appendix A Event URL**, follow **this document and that pinned chat**. Apply the **final correct Event URL**, not the failed first attempts.

Do not invent extra cards, extra headers, or Super Admin chrome. This pass is the **public Event URL + Low Point results + print/PDF**.

---

## Rule 1 — Match `public.events` FIRST (do not skip)

**Failed in the worked example. This must stop. It wastes time and burns credit.**

Before any Event URL slug, dates, or `regattas` insert:

1. Parse the SAS Low Point / Appendix A sheet (ranks, races, discards, host, class).
2. Search **`public.events`** for the SAS event that **actually ran**:
   - `source = 'sas'`
   - name tokens (class + regionals/nationals/etc.)
   - **host club**
   - **dates that match the sheet / last raced weekend**
3. Confirm the SAS page (`source_url` / `https://www.sailing.org.za/events/{source_event_id}`).
4. Gold Event URL slug = **`YYYY-MM-DD-club-slug` from that row’s `events.start_date`**.
5. Event name = that events row’s `event_name` (SAS spelling).
6. Set `events.regatta_id` on **that** `source_event_id` only.

Daily SAS scrape putting a row in `events` is **not** matching. Scrape ≠ Event URL.  
Same series can have **two SAS listings** (stale May `344422` + actual Oct `382272`). Pick the dates that match the sheet, not the first name hit.

**If Rule 1 was already wrong on live:** migrate the slug to `events.start_date`, 301 the bad URL, unlink the stale SAS row, relink the correct `source_event_id`. Do not leave a May URL serving October results.

---

## Gold Event URL (public page)

### Columns

Same as 505 Nationals, except race count:

`Rank | Class | Sail No | Club | Helm | Crew | R1 … RX | Total | Nett`

### Header (and nothing more)

- **Left:** class = fleet. If the class is in the event name, use **that class logo**.  
  Mirror in the name → `/artwork/Class Logo/Mirror-Class-Logo.png`.  
  Combined Event Logo (e.g. `KZN-Mirror-ILCA-Regionals-Champs.png`) **only** if every class named in the filename is in the event name or slug. See `event_logo_class_compat.py`.
- **Right:** host club logo + `Host: {CODE} - {Full name}`. Club logos that appear **in result rows** (other clubs in the fleet) stay in the table, not as a second header Event Logo.
- **Landing Latest Results cards:** large left slot = named Event Logo when one exists (TSL, Dam Bottle, Midmar Cup, Ullman, …). If there is no Event Logo and the card is class = fleet, use that class/fleet logo in the large slot (Mirror, 420 Nationals, Dart 18, Leopard Challenge). Keep the small fleet chip. Never the default Sailing SA mark, and never a combined Event Logo that names a class the event does not.
- **Same event, same card:** the landing upcoming/live hero above search must match that event’s All Regattas list card (large Event/fleet logo, host, chip). Upcoming only on landing (7 days out, 14 for majors such as Youth Nationals) with an orange **X Days to Go** pill right of Entries and an orange **Upcoming event** button when within 7 days. The regatta list is past results. **Live** events show on both.
- **Status line:** `Results are [Provisional|Final] as at DD Month YYYY at HH:MM`  
  Source: `regattas.result_status` + `regattas.as_at_time`. Use **"as at"**.  
  For this pass, as-at is **17:05 on the event/results date the user gives** (worked example: Final as at 18 October 2026 at 17:05). Never “now”, never a placeholder.
- **Sailed line:** `Sailed: U, Discards: V, To count: W, Entries: X, Scoring system: Appendix A`

### Not on this Event URL

- No Marine Megastore / Facebook live / News type / Feed source cards. Those are **Lipton + Cape Classic only**.
- No extra header cards.
- **Super Admin section is not in this pass.** Do not add SA toolbars, column editors, hub-news, or other admin chrome to the public Event URL.

### Parent vs child URLs

- **One fleet** → parent Event URL only. No `/class-{fleet}` and no hyphen-tail child (`…-mirror`). 301 those to parent.
- **Two or more fleets** → child Event URL per fleet.

---

## Low Point checksums (Appendix A)

- `total` = sum of **all** race points **including** discarded races.
- `nett` = `total` − discarded race points.
- Discards: N → **exactly N** parenthesised scores per row (`"(5.0)"`, `"(9.0 DNS)"`).
- Penalty codes (DNC, DNS, DNF, …) = **entries + 1**.
- SAS names/IDs win; unmatched helm/crew ID = `NULL` (keep sheet name). Apply SAS catalogue spelling when the ID matches.

Ingest script pattern: `sailingsa/deploy/create_2026_pyc_kzn_mirror_regionals.py`.

---

## PDF / print / share

- Single fleet → **parent `results.pdf` only**.
- Delete leftover `class-*.pdf` and old slug PDF dirs. **Do not CSS-hide** replaced logos, old cache-bust query strings, or junk that still ships in print.
- Rebuild PDF from the **live** Event URL **after** Rule 1 dates/name/logo are correct.
- PDF unique images = class logo + host (plus club marks that appear in the table). No unrelated Event Logo.

---

## Live Box

Deploy via **`sailingsa/deploy/SSH_LIVE.md`**. Patch live in place. **Never scp an older local `api.py` over live.**

---

## Worked example (correct vs failed)

| | Failed (do not repeat) | Correct (this pass) |
|---|---|---|
| SAS event | `344422` May leftover | `382272` last weekend |
| Slug | `2026-05-16-pyc-kzn-mirror-regionals` | `2026-10-17-pyc-kzn-mirror-regionals` |
| Name | invented / Championships leftover | `KZN Mirror Regionals` from `events` |
| Dates | 16–17 May 2026 | 17–18 Oct 2026 |
| Left logo | KZN-Mirror-ILCA Event Logo | Mirror class logo |
| Extra cards | MM / Facebook / SA chrome | none |
| PDF | empty / old ILCA / child PDF leftover | parent `results.pdf` only |

`382272` was already in `events` from daily scrape (`last_seen_at` scrape `202610190102`). Linking the May listing was a Rule 1 failure, not a scrape miss.

---

## Related docs (this pass owns Low Point Event URLs)

- `docs/RESULTS_PASSING_WORKFLOW.md` — sailor IDs then ranks; status line format
- `docs/RESULTS_HTML_STATUS_LINE_RULE.md` — “Results are … as at …”
- `docs/RESULTS_CHECKSUM_RULES.md` / `docs/ENTRY_COUNT_CHECKSUM_RULES.md`
- `docs/README_RESULTS_INGESTION.md` — slug/date authority **after** Rule 1 is correct
- `docs/EVENTS_TABLE_AND_SCRAPE.md` — scrape fills `events`; this pass **matches** it
- `docs/EVENTS_CALENDAR_MATCHING_DESIGN.md` — date window + name + host
- `event_logo_class_compat.py` — combined Event Logo vs class=fleet
- `sailingsa/deploy/SSH_LIVE.md` — live apply
