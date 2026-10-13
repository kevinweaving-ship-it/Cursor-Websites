# TSL sailor search popup — reuse this

Working Super Admin picker on the MAC TSL Event URL. **Reuse this same system** when adding a new team or adding sailors. Do not invent a second search.

Live: https://sailingsa.co.za/regatta/2026-10-17-mac-tsl-wc-team-sailing  
Code: `js/mac-tsl-admin.js` (keep `sailingsa/frontend/js/mac-tsl-admin.js` in sync).  
Pin: `mac-tsl-admin.js?v=` in `api.py`. Current working pin **`20261014o`**.

The popup is a body-fixed `.card` (`#tslNamePop`) centred on the Flight or Team card (`placeNamePop` / `showNamePop`). Flight team pick uses the same popup — do not open a list inside the table cell.

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

## Add Team / add sailors (same popup)

Super Admin only. After the last team card, a standard `.tsl-team-card.tsl-new-team-card` stays last: **+** icon + **New Team** (same table header as other teams). After each new team is saved, this card is painted again so another team can always be added.

1. Click **+ / New Team** (or T+, or an empty cell on that card).
2. Club search — same body-fixed `.card`, 16px field, short list as you type. Hits: **Club Logo | Club code | Club Full name**. Endpoint: `GET /api/tsl/{rid}/clubs-search` (fallback `/api/super-admin/clubs-search`).
3. Select club → **Team name** field (pre-filled with club full name; user edits) → **Add team**. `POST /api/tsl/{rid}/teams` with empty boats. Team card is written like the others even with 0 sailors.
4. Then sailor add (1 of 6): **search left, list right** — same `/api/search?hub=1` + `filterHits` + **name | logo | SAS**. At the same time: **M/F** and **Helm/Crew** toggles + Save. After save, offer 2nd…6th. **Done** / Escape / 1 or 3 sailors is enough — team stays.
5. Blank cell on any team: click **—** → same add flow (sailor + sex + Helm/Crew). Named cell still uses the replace card (original | ← | search).

Keep: `.card`, `.action-button`, `.wc-result-field-input`, `.tsl-ac-list`, 16px field, body-fixed card, `/api/search?hub=1`, hit format **name | logo | SAS**. No invented SAS. Club of an existing team does not change when a sailor is added.

## Edit / remove an existing team

Super Admin clicks the **team name** (header on that team’s card). Same body-fixed `.card` popup shows the club line, an editable **Team name**, the same roster table (sailors / S / Helm-Crew still work), **Save**, and **Remove team**. Remove calls `DELETE /api/tsl/{rid}/teams/{id}` (blocked if the team has a completed match). After remove, cards refresh and the New Team card stays last.

Do not: over-the-name absolute card, TSL sailors-search for the typeahead, hide empty results with no status line, raw `TimWeaving` query.

---

## Tests / deploy

- Contract: `python3 -m unittest sailingsa.backend.test_tsl_admin_js`
- JS pin in `api.py` + `sailingsa/deploy/patch_live_mac_tsl_results.py` + `patch_live_mac_tsl_wc_event_url.py`
- Live JS: `/var/www/sailingsa/js/mac-tsl-admin.js` (surgical copy). Do not overwrite live `api.py` wholesale — pin bump + `chattr` only. See `sailingsa/deploy/SSH_LIVE.md`.
