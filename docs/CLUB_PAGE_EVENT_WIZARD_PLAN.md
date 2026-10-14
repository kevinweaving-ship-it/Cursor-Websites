# Club-page event wizard — plan only (for approval)

**Status:** Plan only. Do not code or deploy until this placement is approved.

**Date:** 14 October 2026.

**Replaces as the product surface:** standalone `/club-manage` and `/club-manage-preview` dashboards. Those stay unused for officers. Event management **starts on the existing club page**.

**HYC season calendar (plan only):** `docs/HYC_CALENDAR_CLUB_PAGE_PLAN.md` — Claim SAS Event / Activate Club Event / Add New Event, reusable vs missing fields, no auto-`regattas` for training / external / duty. Live `/club/hyc` uses `.sa-home-regatta-card` lists, not the workspace carousel fragment.

**Ask:** Approve the slots below before any implementation.

---

## Verdict

Authorised club admins manage events **on `/club/{abbrev}`** — the same page visitors already use. Do not send officers to a generic form page.

Visitors keep today’s club page unchanged: heading, Events carousel (Live / Upcoming / Past), Sailors, Regattas hosted.

Admins get two extra controls **inside existing chrome**, plus one extra `.card` that appears **only after** they choose Activate or Add club event.

---

## What the public club page already is (do not move)

Current `/club/{abbrev}` body, in this order:

```
.club-page
  ← Back to Search
  .header > h1          e.g. ZVYC - Zeekoe Vlei Yacht Club

  .card.stats-section.club-events-dashboard     ← SAS calendar
    .events-section-heading-row
      h2.section-title  “Events (N)”
      search pill
    p.club-events-intro
    .events-toolbar
      .events-tabs      Live | Upcoming | Past
    carousel             one .event-card per swipe
      .event-card-header   name + date
      .event-card-body
        type badge, host, result line
        .event-card-actions    [index] [Details]

  .club-content
    Sailors card (carousel)
    Regattas hosted card (carousel)
    Unmatched past (only if needed)
```

**Locked for visitors:** tabs, card colours, swipe, Details, Sailors, Regattas hosted, heading, search. No new dashboard, no numbered forms, no typed IDs.

---

## Who sees admin controls

After login, `GET /api/club/me` + `GET /api/club/me/events`.

Show Activate / Add **only when** all of these are true:

- role is `club_admin` or `club_manager` (or `super_admin` scoped to this club)
- `admin_club_id` equals this page’s club
- the event’s `host_club_id` is this club (or Unassigned, for Claim only)

Sailors and anonymous visitors: **zero** extra buttons, **zero** extra cards. Same HTML they have today.

---

## Exact slots (admin only)

### 1. Activate — on the upcoming event card

**Where:** existing `.event-card-actions`, **beside Details**. Same row as the index badge and Details. Do not add a second action row, do not restyle the card.

```
[ ✓ Result ]     [3] [Details] [Activate]
                 └─ .event-card-actions ─┘
```

**When it appears**

| Card tab | Condition | Control |
| --- | --- | --- |
| Upcoming / Live | `host_club_id` is this club, no `regatta_id` yet | **Activate** |
| Upcoming / Live | already linked (`regatta_id` set) | **Manage** (same slot, opens wizard on that event) |
| Past | already has public results URL | none (Details / result tick stay as now) |
| Any | visitor or other club | none |

Activate calls existing `POST /api/club/events/{event_id}/claim` (scraped rows only). That sets host if needed and **creates a `regattas` row only when `regatta_id` is null**. Existing slugs are never rewritten.

### 2. Add club event — on the Events heading row

**Where:** existing `.events-section-heading-row`, after the search pill (same row as `Events (N)`).

```
EVENTS (12)                    [ search… ]  [Add club event]
└──────── .events-section-heading-row ─────────────────────┘
```

One secondary button. Label: **Add club event**. Not a new card above the calendar. Not “Create event” as the first thing officers see.

This starts the wizard in **create** mode **after** a match check (below). If the calendar already has that weekend, the wizard offers Activate on the match instead of inserting a second row.

### 3. Wizard — one extra card, only after a choice

**Where:** one `.card.stats-section` inserted **immediately below** `.club-events-dashboard` and **above** `.club-content` (Sailors). Same club card chrome: `h2.section-title`, `.table-container`, `table.table`.

```
  Events carousel          ← always visible, unchanged
  ┌─ admin-only, after Activate / Add ─────────────┐
  │  ACTIVATE EVENT                                │
  │  stats links: Details · Fleets · Registration  │
  │               Entries · Upload · Publish       │
  │  one table at a time (ask only what’s missing) │
  └────────────────────────────────────────────────┘
  Sailors / Regattas hosted ← always visible, unchanged
```

Visitors never get this card. Closing the wizard (Back to events / done) removes it. The carousel, tabs, and public cards stay on screen so the officer still sees the club page.

Do **not** use a separate URL as the home. Optional deep link only: `/club/{abbrev}?event={event_id}` to reopen the wizard on a claimed event. No `/club-manage` redirect.

---

## Wizard steps (same card, named dropdowns)

Stats anchors jump between tables inside that one card. One selected event. IDs stay in JS.

| Step | Title | What the officer sees | Prefill | Must confirm |
| --- | --- | --- | --- | --- |
| 1 Details | Event | Name, dates, venue, type | Calendar row: `event_name`, `start_date`, `end_date`, `venue_raw` / location, `category`. Last year’s same-name event at this club if the scrape is thin. | Name/date if scrape looks wrong. Venue if scrape ≠ last year. |
| 2 Fleets | Fleets | Class dropdown + suggested classes | Previous edition at this host: `regatta_blocks.class_name` from past `regattas` already in `GET /api/club/me/events`. Race-class list for the picker. | **Always.** Calendar rows have no official class list. `_likely_classes` on public cards is empty. |
| 3 Registration | Registration | Open / Closed | Default **Closed** (`entry_open` false). | Opening entries. |
| 4 Entries | Entries | Helm, sail no, class, SAS ID add row | Official name from SAS after ID. Existing `GET /api/regatta/{id}` rows. | Each add. |
| 5 Upload | Upload | File, Preview table, then Commit | — | Preview table before Commit. |
| 6 Publish | Publish | Locked status sentence, Provisional \| Final | Current `result_status` / `as_at_time`. | Publish. |

Ask only for blanks. If name, dates, and venue are present, step 1 is a confirm table (no empty form). If last year had ILCA 6 / ILCA 7, step 2 lists those as suggestions; the officer accepts or changes via the class **name** dropdown.

---

## Activate vs Add (no duplicate URLs)

```
Upcoming card [Activate]
    → POST /api/club/events/{id}/claim
    → reuse events.regatta_id if already set
    → else new slug {YYYY-MM-DD}-{abbrev}-{name}
    → never UPDATE an existing regatta_id
    → open wizard on that event

Heading [Add club event]
    → compare title + dates + this host against GET /api/club/me/events
    → if a calendar row matches: do not POST create; offer Activate on that row
    → only if no match: POST /api/club/events, then wizard
```

`POST /api/club/events` always inserts. The match check **must** run in the wizard before that call, or the officer will mint a second event and a second URL.

Claim already refuses `origin=club` rows and other clubs’ hosts. Keep that.

---

## What existing data can actually prefill

Already on the club card or in `GET /api/club/me/events` (this club only):

| Field | Source | Ready? |
| --- | --- | --- |
| Name, start, end | `events` | Yes |
| Venue / location | `venue_raw`, `location_raw` | Yes when scrape filled it |
| Type | `category` | Yes when set |
| NOR / SI | `nor_url`, `si_url` | Often empty — ask only if blank |
| Host | session `admin_club_id` | Never a field |
| Public URL | `events.regatta_id` or new slug | Yes; do not rewrite |
| Previous edition | past events/regattas, same host, similar name (year stripped) | Heuristic — show as “Last year: …” and confirm |
| Classes | last edition `regatta_blocks` | Suggest only; confirm |
| Entries / scores | `GET /api/regatta/{id}` | After a slug exists |
| Race-class picker | `race_classes[]` | Yes (names in the select, ids in `value` only) |

**Not available without a new list API (out of this UI pass):** scraped rows whose `host_club_id` is still Unassigned. This plan matches **by `host_club_id` only**, so those stay on the public Unassigned club / admin host-review tools. Do not invent a second calendar.

---

## What we will not do

- A separate `/club-manage` or `/club-manage-preview` as the officer home
- Generic stacked forms or typed `regatta_id` / `event_id`
- Changing visitor tabs, event-card colours, Details, Sailors, or Regattas hosted
- Auto-adding fleets from last year without a confirm
- Rewriting existing slugs or the three scoring-pilot URLs
- New CSS / colours / header edits
- Opening entries by default

---

## Implementation notes (only after approval)

- Gate with `GET /api/club/me` on `/club/{abbrev}` only. Inject Activate / Add / wizard card in JS; public HTML stays the default.
- Reuse `POST …/claim`, `POST /api/club/events`, class / entry / ingest / publish routes already live.
- Preview, if needed later: same club URL while logged in as ZVYC/HMYC — not a second site.
- Mobile: Activate sits in the existing action row (may wrap; 44px tap). Wizard card is one column, tables scroll in `.table-container`.

---

## Approval

Reply to implement **on the club page only**, with Activate beside Details and Add club event on the Events heading row. This document is not a licence to code until you say so.
