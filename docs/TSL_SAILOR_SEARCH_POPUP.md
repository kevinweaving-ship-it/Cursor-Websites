# TSL sailor search popup — reuse this

Working Super Admin picker on the MAC TSL Event URL. **Reuse this same system** when adding a new team or adding sailors. Do not invent a second search.

Live: https://sailingsa.co.za/regatta/2026-10-17-mac-tsl-wc-team-sailing  
Code: `js/mac-tsl-admin.js` (keep `sailingsa/frontend/js/mac-tsl-admin.js` in sync).  
Pin: `mac-tsl-admin.js?v=` in `api.py`. Current working pin **`20261013z`**.

---

## What the user sees (locked)

1. Super Admin clicks a helm/crew **name**.
2. A **standard `.card` popup** opens on `document.body` (`position: fixed`, not over the table cell, no iOS zoom).
3. One row: **original sailor** | **left-arrow** (`/js/tsl-swap-left.png`) | **search field**.
4. Type **2+ letters**. More letters → shorter list (landing-style).
5. Each hit: **first name surname | club logo | SAS ID**.
6. Select a hit → card shows **Original | ← | Chosen** plus small **Save**.
7. Arrow swaps the two sides (visual only). **Save** writes the **selected** sailor (from search) into the original slot and closes.
8. Status line: `Type a name` → `Searching…` → list, or `No sailors found.` / `SAS missing — not invented`.
9. Escape or click outside closes without save.

No invented SAS IDs. Club of the **team** does not change when a sailor is replaced.

---

## Search rules that actually work

Do **not** send the raw typed string to a Super-Admin-only TSL endpoint. That failed (403 / silent empty list).

| Step | Do this |
| --- | --- |
| Normalize | `spaceCamel(q)` so `TimWeaving` → `Tim Weaving`. Raw `TimWeaving` against `/api/search` returns **[]**. |
| Min length | 2 characters after normalize. |
| Fetch | `GET /api/search?q={firstToken}&hub=1&limit=80` — **same landing sailor search**. Public. Returns a JSON **array**. |
| Shorten list | `filterHits(rows, tokens)` — every extra token must appear in first / last / name / SAS / club. |
| Map row | `normalizeSearchHit` — `first_names`→`first_name`, `surname`→`last_name`, `club_logo` from `club_logo_url` or `/api/club-logo/{club}`. |
| Debounce | 80ms on `input` via **document** delegation (`#tslPopSearch`). Survives innerHTML rebuilds. |

`/api/tsl/{rid}/sailors-search` is Super Admin only. Keep it for the old 1-line picker if needed. **New pickers use `/api/search`.**

---

## Why it must live on `document.body`

The Teams table / `.card` / overflow clips a popup that sits on the name. iOS also zooms inputs under 16px.

- Create once: `ensureNamePop()` → append `#tslNamePop` to `body`.
- Do **not** put `#tslNamePop` inside `teamCardsHtml()` (rebuild would duplicate the id).
- Input font **16px !important** so iPhone does not auto-zoom.
- CSS is `#tslNamePop …` (not `#macTslTeamsCard #tslNamePop`) because the node is not inside the teams card.

---

## Functions to reuse

Copy these, or later extract them into a shared helper (only when Add Team needs them):

| Function | Job |
| --- | --- |
| `spaceCamel` | Unspaced name → words |
| `normalizeSearchHit` | Landing `/api/search` row → `{ first_name, last_name, name, sas_id, club, club_logo }` |
| `filterHits` | More letters, shorter list |
| `runPopSearch` | Fetch + filter + status text |
| `searchHitHtml` | `Name \| logo \| SAS` |
| `sailorChip` | Compact first + surname + logo |
| `ensureNamePop` / `bindNamePopControls` | One body card, delegated input |
| `copyPerson` | Slot payload (`sas_id` is what PATCH saves) |

Save path today: `writeRoster` + `paintAndSave` → `PATCH /api/tsl/{rid}/teams/{id}` with `helm_sas_id` / `crew_sas_id`. Existing sailors only.

---

## Reuse later — Add Team / add sailors

When that work starts, **same popup + same search**. Change only the **save target**:

- Replace slot (now): write `pickState.selected.sas_id` into that boat role.
- Add sailor to a team: append/fill the next empty helm or crew slot with that `sas_id`.
- Add team: first pick club (existing club search), then use **this** sailor search for the 3 helm + 3 crew. Still no invented SAS.

Keep: `.card`, `.action-button`, `.wc-result-field-input`, `.tsl-ac-list`, 16px field, body-fixed card, `/api/search?hub=1`, hit format **name | logo | SAS**.

Do not: over-the-name absolute card, TSL sailors-search for the typeahead, hide empty results with no status line, raw `TimWeaving` query.

---

## Tests / deploy

- Contract: `python3 -m unittest sailingsa.backend.test_tsl_admin_js`
- JS pin in `api.py` + `sailingsa/deploy/patch_live_mac_tsl_results.py` + `patch_live_mac_tsl_wc_event_url.py`
- Live JS: `/var/www/sailingsa/js/mac-tsl-admin.js` (surgical copy). Do not overwrite live `api.py` wholesale — pin bump + `chattr` only. See `sailingsa/deploy/SSH_LIVE.md`.
