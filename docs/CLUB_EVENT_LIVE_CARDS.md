# Event URL preload — copy last same-club cards

When creating or preloading a **new Event URL**, do not invent a new card layout.

1. **Find the event** (SAS / club calendar) and match it.
2. **Create the Event URL** as `YYYY-MM-DD-{club}-{slug}`  
   Example: `/regatta/2026-09-24-hmyc-dart-18-nationals`
3. **Look up the last Event URL at the same host club** that already has live cards.
4. **Copy that club’s card stack** onto the new page:
   - Main header **Leader Board** (empty until scores)
   - **Weather** card (same station as that club)
   - **Media** card (**empty** — this event’s own `/mm-clips` only)
   - **Fleet header** for this event’s class
   - **Live camera** if that club already has one
5. Add a fleet block so the fleet header renders before results exist.
6. Set **`host_club_id` + `host_club_name` + `host_club_code`** on the `regattas` row (from `clubs`). Link `events.regatta_id`.
7. **You SSH the server.** The user only vibe-codes. Do not skip SSH, do not hand back SQL/deploy for them to run. Repo-only does **not** create the Event URL, landing hero, or search hit. See `sailingsa/deploy/SSH_LIVE.md`.
8. **Prove it on live:** Event URL 200, landing hero card, landing Regatta Search.

HMYC source event: `/regatta/2026-09-19-hmyc-midmar-cup`  
Profile: Leader Board + Agromet Midmar weather + media + HMYC camera.

**When the event opens:**
- **Entries** — update the fleet / entry list on this Event URL; do not change the slug. Dart 2026 is **two fleets: DH and SH** (`:dart-18-dh` / `:dart-18-sh`). Fleet header is class logo + **DH Fleet** / **SH Fleet**, not logo + the word Fleet alone.
- **HMYC club manager** — Alison Grunewald `#28280` is `user_accounts.role=club_manager` + `admin_club_id=98`. Same Cape Classic score UI on Dart only (`club-score-edit.js`): enter places, auto rank, add/remove races. Not Midmar. Not other clubs.
- **Names** — SAS ID is the person. Format is Title Case (`Ciara Neumann`). Never preload ALL CAPS from SAS or the entry sheet (`TRISTAN ELLIOTT` is wrong; amend SAS then use `Tristan Elliott`).
- **WhatsApp group** — add the official event group. Super-admin drop on the media card accepts WhatsApp photos/video (`VID_…` → `/mm-clips`). Media stays empty until those clips are saved to **this** slug.

Code: `sailingsa/backend/club_live_cards.py` — later date-first Event URLs at the same club inherit the stack. Add a new club profile only when that club’s first live Event URL is set up.

---

## Surfaces that count (use these only)

| What | Live surface |
| --- | --- |
| Event URL | `/regatta/{YYYY-MM-DD-club-slug}` |
| Upcoming hero | `/` / `index.html` **`landing-event-card`** / `sa-home-regatta-card` (same slot as 420 Nationals) |
| Regatta Search | `GET /api/regattas/with-counts` (live disk cache `/var/tmp/sailingsa_regatta_with_counts.json` — clear it after insert). Search row pill is **Upcoming Event** until the event is live or has Race 1 scores; then Live / Racing / Full Results. |

Landing search needs a real `public.regattas` row. Hub history needs `events.regatta_id` **and** a series key that merges prior years (`_yearly_event_series_key`, same idea as 420 → `2026-09-25-tsc-420-nationals`).

**Header:** Host line only. **No `Venue : …` unless host and venue are different clubs.** Same club (HMYC / Henley Midmar Yacht Club) = hide Venue.

**Media:** inherit the card shell, not the clips. Seeded Midmar cup/training thumbs stay on Midmar. New slug starts at `No media yet` via its own `/mm-clips`.

---

## Do not touch (leftover / unused)

These are **not** the landing and are **not** part of creating an Event URL:

- **`blank69.html`** — QA hub, unused for months
- **`js/breaking-news-card.js`** — old Breaking / Upcoming news cards, unused for months
- Repo **`blank.html`** old hub fallbacks — live `/` / `blank.html` is the `landing-event-card` hub, not that leftover JS

Do not add Event URL fallbacks, cache-busts, or search merges in those files.

---

## Live deploy (SSH) — required (agent job, not the user’s)

**Why no SSH last time:** that was a fuckup. The user only vibe-codes. Creating a new Event URL **is** server SSH. Do it. Do not ask them to apply SQL, restart the API, or “run from This Mac”.

`sailingsa/deploy/SSH_LIVE.md`. Production is `root@102.218.215.253`.

- Apply SQL **on live** (insert `regattas` + `regatta_blocks`, `UPDATE events SET regatta_id=…`).
- Live `api.py` is ~80k lines and **immutable (`chattr +i`)**. Snapshot → `chattr -i` → surgical edit → `chattr +i` → restart `sailingsa-api`.
- **Never** scp/replace live `api.py` with the repo copy (stale snapshot; would wreck production).
- **Never** zip-deploy the full frontend (overwrites hub / `landing-event-card` / live Midmar JS).
- Do **not** wholesale-replace live `midmar-*.js` during a live Midmar event. Patch only what the new slug needs (`currentRid()`, empty media, script tag for the new slug).
- After insert, delete `/var/tmp/sailingsa_regatta_with_counts.json` so search sees the new row.

```bash
# live box — example Dart apply (This Mac / SSH, not Cloud-only)
export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
python3 sailingsa/deploy/create_2026_hmyc_dart_18_nationals.py --apply
```

---

## Corrections from Dart 18 Nationals 2026 — do not repeat

Creating `/regatta/2026-09-24-hmyc-dart-18-nationals` went wrong in this order. Next Event URL must not.

1. **Failed to deploy / no SSH** — first pass stayed in repo and told the user to apply SQL. Live had no row, so there was **no Event URL, no landing hero, not in Regatta Search**. User only vibe-codes; **SSH is the agent’s job**. Do not wait to be told “you have full SSH”.
2. **blank69** — Dart fallback / search merge / cache-bust was patched into `blank69.html` (repo + live). Unused QA hub. Reverted. **Never open blank69 for Event URL work.**
3. **Old breaking-news / news cards** — same fallback went into `js/breaking-news-card.js` and old hub `blank.html`. Those cards have not been the landing for months. Reverted. **Landing hero is `landing-event-card` on `/` / `index.html`.**
4. **No hero + not in list** — landing Upcoming and search only see a calendar row with `events.regatta_id` / a `regattas` row. 420 already had `2026-09-25-tsc-420-nationals`. Dart did not until live SQL + cache clear. Code fallbacks on leftover hubs do not count.
5. **Old media fuckup** — live `midmar-live-media.js` treated Dart as Midmar and seeded Midmar Cup still + “Last minute Training”. Dart `/mm-clips` was already empty (0). Must `emptyMedia` when slug ≠ Midmar; do not call `cupVideos()` / `mmLiptonReelsInit` on a new event.
6. **Venue : Henley Midmar Yacht Club** — Host was already HMYC. New row had `host_club_id` but **empty `host_club_name` / `host_club_code`**, so the “hide Venue if same as host” check had nothing to compare. Always persist name+code from `clubs`, and resolve host via `host_club_id` join. Venue only if a **different** club.

Dart Event URL: `/regatta/2026-09-24-hmyc-dart-18-nationals`  
Calendar: HMYC `367984` / `events.event_id=139944` / `regatta_number=999010`.

---

## Corrections from TSC 420 Nationals 2026 — do not repeat

`/regatta/2026-09-25-tsc-420-nationals` was already created and correct. The ask was **entries only**.

What went wrong: live `api.py` was replaced with the repo snapshot, and invented sheet copy was added (blue/grey rows, “Blue = SAS matched”, “snapshot time not recorded”, 2025-order legend). **No README specifies that.** That is not an Event URL format.

Do not use or reintroduce `.entry-sas`, `.entry-pending`, `.entry-unresolved`, or any preload legend on the sailed line.

When the Event URL exists: write `public.results` only. Do not edit `api.py`, headers, or the sheet.
