# HMYC Dart 18 Nationals 2026 — PAGE LOCKED

**Status: LOCKED. Do not change this Event URL again.**

Live: https://sailingsa.co.za/regatta/2026-09-24-hmyc-dart-18-nationals  
Slug: `2026-09-24-hmyc-dart-18-nationals`  
Dates: **24–27 September 2026**  
Name: **Dart 18 Nationals incorporating the KZN provincials**  
Host: **HMYC** (`clubs.club_id=98`)  
Calendar: HMYC `367984` / `events.event_id=139944` / `regatta_number=999010`

The user locked this page on **24 September 2026** after public + Super Admin scoring were signed off:

> save / note and update readme > all aspects of page and don’t fucking change it again

**Override:** do nothing unless the user writes exactly **`override lock`** in the **same** request. “Fix”, “polish”, “match Midmar”, “small CSS”, “public looks short”, or a new Event URL at another club is **not** an override.

This README is the full lock. `docs/CLUB_EVENT_LIVE_CARDS.md` is for **creating the next Event URL**, not for editing Dart.

---

## Do not touch (this page)

| Surface | Leave it |
| --- | --- |
| Live Event URL | `/regatta/2026-09-24-hmyc-dart-18-nationals` — HTML, cards, fleets, header, weather, media, camera, tables |
| Live JS | `/var/www/sailingsa/js/club-score-edit.js` (`?v=ccr31` or later cache only if user override-locks) |
| Repo JS | `sailingsa/frontend/js/club-score-edit.js` Dart slug path and styles |
| Live API | Surgical Dart / cape-live-fleets / `_touch_live_club_as_at` / `_public_race_has_score` already on live `api.py` |
| Live DB row | `public.regattas` slug, host fields, `result_status`, fleets. **Do not re-run** `create_2026_hmyc_dart_18_nationals.py` (ON CONFLICT would reset `as_at_time` to 11:00) |
| Entries | Preload already applied. **Do not re-run** `preload_2026_hmyc_dart_18_entries.py` unless override lock + new CSV |
| Landing | Dart hero / search row / class-logo chip |
| Midmar | Do not wholesale-replace live `midmar-*.js` |
| Leftovers | **Never** `blank69.html` or `js/breaking-news-card.js` |
| Master header | Locked separately — not this page |
| Iframe sheets | `class-results.html` / `results.html` stay locked |

Do **not** zip-deploy the full frontend. Do **not** scp/replace live `api.py` with the repo snapshot.

---

## 1. Event URL and landing

- Date-first slug: `YYYY-MM-DD-hmyc-dart-18-nationals`.
- Hub hero is `/` / `index.html` **`landing-event-card`** / `sa-home-regatta-card` (same slot as 420 Nationals).
- Search: `GET /api/regattas/with-counts` (live disk cache `/var/tmp/sailingsa_regatta_with_counts.json`).
- Search / hero pill is exactly **`Upcoming Event`** until the event is Live **or** has at least Race 1 scores. Then Live / Racing / Full Results.
- Landing Dart chip uses **`Dart-18-Class-Logo.png`** (class logo, not the word “Dart” as text). Same idea as the 420 logo chip.
- Series key merges prior-year Dart Nationals history on the hub card (`_yearly_event_series_key`).
- Prove on live only: Event URL 200, landing hero, Regatta Search hit.

---

## 2. Cards (copied from last HMYC event — Midmar Cup)

Source: `/regatta/2026-09-19-hmyc-midmar-cup`. Profile in `sailingsa/backend/club_live_cards.py` (`CLUB_LIVE_CARD_PROFILES`).

Locked stack on this slug:

1. Main header **Leader Board** (empty until scores).
2. **Weather** — same Agromet Midmar station as HMYC.
3. **Media** — empty shell only. Own `/mm-clips` for this slug. **No Midmar Cup / training leftovers.** Starts at `No media yet`.
4. **Fleet header** per fleet (see §4).
5. **Live camera** — HMYC camera already on the Midmar stack.

WhatsApp photos/video (`VID_…`) drop onto **this** slug’s media card when Super Admin saves them. Do not seed other events’ clips.

**HMYC Facebook Live / Reels is not wired.** Do not add a feed, token, or MM-card change on this page. Kevin must be added as a **person Page Admin** on the HMYC Facebook Page first; then a **new** request (with override lock if it touches this Event URL).

---

## 3. Header — Host only, no Venue

- Host line: HMYC / Henley Midmar Yacht Club.
- **No `Venue : Henley Midmar Yacht Club`.** Host and venue are the same club.
- Venue only if a **different** club is the sailing venue.
- Persist `host_club_id` **and** `host_club_name` **and** `host_club_code` from `clubs` (empty name/code makes the hide-Venue check fail).

Status stamp on this live-club page (Cape Classic header helper):

- `regattas.result_status` = **Provisional** until someone sets Final.
- `regattas.as_at_time` **must move** when a race is closed or a race/fleet-races PATCH succeeds (`_touch_live_club_as_at` stamps `regattas.as_at_time` + `results.as_at_time` = NOW()).
- `GET …/cape-live-fleets` returns `as_at_time`.
- Display splits: **`Results are Provisional`** then **`24 Sep 2026 HH:MM`** (Africa/Johannesburg). Not a frozen 11:00. Not “as of”. Not today’s clock unless a race just closed.
- Do not freeze Midmar / Cape Classic official `as_at` while touching Dart (those stay their own stamps).

---

## 4. Fleets and entries

Two blocks only:

| Fleet | `block_id` | Header |
| --- | --- | --- |
| Double-handed | `2026-09-24-hmyc-dart-18-nationals:dart-18-dh` | Dart 18 class logo + **DH Fleet** |
| Single-handed | `2026-09-24-hmyc-dart-18-nationals:dart-18-sh` | Dart 18 class logo + **SH Fleet** |

- After the fleet logo, the title is **DH Fleet** / **SH Fleet**, not the word “Fleet” alone.
- `public.results` **is** the entry list. `raced=false` until that boat has scores.
- Entry Type: Dart 18 Double / Youth → DH; Dart 18 Single → SH.
- Do not invent a third fleet. Do not merge DH+SH.
- Do not leave fake live scores for testing.

---

## 5. Names and SAS ID

- **SAS ID is the person.** Display name is **Title Case** from `sas_id_personal` (`Ciara Neumann`, `Tristan Elliott`).
- Never preload ALL CAPS from SAS `full_name` or the entry sheet (`TRISTAN ELLIOTT` is wrong).
- If SAS is ALL CAPS, **amend SAS first**, then copy Title Case onto Dart helm/crew.
- Forced IDs already applied include Ciara Neumann `#21650`, Tristan Elliott `#28611`.
- `sa_sailing_id` is **varchar** — compare as text (`sa_sailing_id::text = %s`), never `= 271` as integer.
- Luc Neumann is still **TMP** until a real SAS ID is supplied. Do not invent one.

See `docs/SAS_ID_RESULTS_NAME_MATCH.md`.

---

## 6. Age column — code `Y`, never the word Youth

- Store and show **`Y`** in `results.age_category` for youth (Aydin O'Hara, Josh Pretorius, Mathew Olsen).
- Adults: `NULL` / blank.
- **Never** write or render `Youth`, `youth`, or `YOUTH` in the Age cell.
- Preload rule: `"Y" if youth else None` in `sailingsa/deploy/preload_2026_hmyc_dart_18_entries.py`.

---

## 7. Who may edit scores (hard)

**Only:**

1. **Super Admin** (`role` `super_admin` / `is_super_admin`), or
2. **Event club admin** for HMYC: `club_admin` / `club_manager` with `admin_club_id=98`.

**Alison Grunewald** `#28280` is the HMYC club manager (`user_accounts.role=club_manager`, `admin_club_id=98`). Same Cape Classic score UI, **Dart + Cape Classic slugs only**.

**Nobody else:**

- Public (logged out) — never.
- Any logged-in sailor / member who is not Super Admin or this event’s club admin — never.
- Other clubs’ admins — never.
- Midmar is not this editor.

`club-score-edit.js` is slug-locked to:

- `2026-09-13-zvyc-cape-classic`
- `2026-09-24-hmyc-dart-18-nationals`

Save: `PATCH /api/result/{id}/race` (403 unless Super Admin / club_admin / club_manager, plus live SAS `21172` bypass).  
Add/remove races: `PATCH /api/result/{id}/fleet-races`.  
Then `_recalculate_fleet_block_scoring_and_ranks` → Dart uses `_recalculate_fleet_block_scoring_legacy` (Appendix A, discard `races//5`, `sort_result_rows_appendix_a`).

Auto-rank after save: official rank from the API. `rerankFleet` must not invent ranks from empty `{"R1":""}` or nett 0. Unscored boats stay unranked.

---

## 8. Public sheet (must always look the same)

Public is **read-only** and **compact**. Do not “fix” public to look like admin.

| Rule | Public |
| --- | --- |
| Score inputs | **None.** No `.club-score-input`. `removePublicScoreInputs()` on every poll. |
| Empty entry races (e.g. R4 with `races_sailed=4` but no scores) | **Hidden.** API `_public_race_has_score` drops empty race columns when `not wc_sa_fleet_edit`. JS `hideEmptyRacesForPublic()` / `.race-col--entry-hide`. |
| Row height | Same compact table as before score-edit existed. Do not grow cells for hidden inputs. |
| Closed / wait races | No green-fill toggle, no wait boxes. Just scored R columns (R1–R3 while R4 is empty). |
| `pollLive` | `applyFleetRow` + `rerankFleet` only. **Never** `wireSaWaitOnly` / `applySaRaceClosed` unless `scoreEditOn()`. |

---

## 9. Super Admin / club admin sheet

Admin is **different** from public. Do not shrink public to match admin, and do not restyle admin “to match public”.

| Rule | Admin |
| --- | --- |
| Page class | `.regatta-page--club-score-edit` (club) and/or `.regatta-page--super-admin-edit` (SA) |
| Closed race header | **Green fill** `#15803d` + **white** type. Not green text on a white header. |
| Closed R is the toggle | Click closed R → reopen scores. Click again → close. No extra box toggle. `localStorage` key `ssa-race-open:{slug}`. |
| Wait / open race | Transparent header; compact score boxes only in wait cells. |
| Score box size | Edit-mode R text (R1…R4 and every later R) = **computed `th.race-col` size** (R1 header label, live table **9px**). Explicit px on the input — iOS ignores `inherit` and blows up to 16px. Place box **`1.7em × 1em`**. **Not** 16px / 22px / 1.6rem circles. |
| Edit field value | Full stored cell: **`40 DNS`**, not bare `40`. Admin must see the code (DNS/DNC/OCS/…) in the box on R1 when later entering R10. Widen only coded cells (`7ch` at 9px). |
| Extra empty race (R4+) | Visible for entry. Public still hides it until a score exists. |
| Total / Nett / Rank | Read-only. Auto after PATCH. |
| Banner | “Type a place or OCS/DSQ…” — admin only. |

Do not add a separate “close race” checkbox. The **R header is the control**.

---

## 10. Compact site rule (this page)

The whole site goal is **compact**. On this Event URL:

- Do not enlarge race headers, score inputs, or row padding “for readability”.
- Do not add 1–2px / bold wait-mode experiments (already rejected).
- Do not invent new CSS frameworks, page fonts, or colours.
- Reuse `.container`, `.card`, `.table`, existing fleet table classes only.

---

## 11. Scoring (do not replace)

- Appendix A, discard every 5 races (`races//5`).
- Places or penalty codes (`OCS`, `DSQ`, …). Extra DSQ = entries+1 DSQ.
- Empty input clears the cell.
- Enter = next box; Tab/arrows save.
- Do not put test places on the live sheet.

---

## 12. Deploy / SSH (agent job — not a reason to restyle this page)

User vibe-codes only. Agent SSHs live per `sailingsa/deploy/SSH_LIVE.md`. Production `root@102.218.215.253`.

- Live `api.py` is ~80k lines and **`chattr +i`**. Snapshot → `chattr -i` → surgical edit → `chattr +i` → restart `sailingsa-api`. **Never** replace with repo `api.py`.
- After API restart, 502 for ~12–16s is warmup. Wait; do not “fix” the page.
- Creating **another** Event URL is a new slug. Copy this club’s **card stack**, not this locked HTML/JS restyle.

---

## 13. Fuckups already paid for — do not repeat

From creating and scoring this page (also in `docs/CLUB_EVENT_LIVE_CARDS.md`):

1. Repo-only / no SSH → no Event URL, no hero, not in search.
2. `blank69.html` and `breaking-news-card.js` — unused for months. Never open them for Event URL work.
3. Media inherited Midmar clips — new slug starts empty.
4. `Venue : Henley Midmar Yacht Club` because host name/code were empty.
5. `as_at_time` frozen at 11:00 because score PATCH did not stamp NOW(); R3 closed ~17:21.
6. Public got score boxes and short rows because `pollLive` wired wait-mode for everyone.
7. Closed R was green **text**, not green **fill**.
8. Huge score inputs stretched every rank row.
9. Empty R4 shown on public because `races_sailed=4`.
10. Age written as `Youth` instead of `Y`.
11. ALL CAPS helm from raw SAS (`TRISTAN ELLIOTT`).
12. Auto-rank used empty cells / `data-official-rank` and ranked a 1st as 16th.

---

## 14. Out of scope until a new user request

Leave these **unfinished** rather than “finishing” them on this page:

- HMYC Facebook Live / Reels on the media card.
- Luc Neumann TMP → real SAS ID.
- Further entries / WhatsApp media (user supplies).
- Marking PR ready.
- Changing Cape Classic or Midmar official stamps.

---

## Code map (read-only reference)

| Piece | Where |
| --- | --- |
| Event create | `sailingsa/deploy/create_2026_hmyc_dart_18_nationals.py` |
| Entry preload | `sailingsa/deploy/preload_2026_hmyc_dart_18_entries.py` |
| Card inherit | `sailingsa/backend/club_live_cards.py` |
| Score UI | `sailingsa/frontend/js/club-score-edit.js` |
| Live as_at / public race filter | live `/var/www/sailingsa/api/api.py` (`_touch_live_club_as_at`, `cape-live-fleets`, `_public_race_has_score`) |
| Club admin | Alison `#28280` / HMYC `98` / `club_manager` |
| SSH | `sailingsa/deploy/SSH_LIVE.md` |

---

**End of lock.** If a later Event URL needs the same behaviour, copy the **rules** onto that new slug. Do not reopen this one.
