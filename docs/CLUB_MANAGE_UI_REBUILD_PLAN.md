# /club-manage UI rebuild — plan only (for approval)

**Status:** Plan only. Do not code or deploy until this layout is approved.

**Date:** 14 October 2026.

**Depends on:** Phases 1–5 already live. `docs/design_system.md`, `docs/UI_COMPONENTS_README.md`, `docs/DESIGN_MOBILE_MASTER_VS_CLASS.md`, Step 3 frontend spec in `docs/CLUB_EVENT_SELF_SERVICE_PLAN.md`.

**Ask:** Approve this layout before any implementation.

---

## Verdict

The live `/club-manage` page is the wrong layer. It is a standalone `api.py` HTML dump: copied nav, numbered generic forms, and typed `regatta_id` / `event_id` fields. That violates the design system and the original Step 3 frontend spec.

Rebuild it as a **club page**, not a form product. Use the same locked header, `.container` / `.card` / `.table` stack, and event-name selection that Class and Club pages already use. APIs stay as they are. No new colours, no new CSS framework, no manual database IDs.

**Preferred host:** `/club/{abbrev}?manage=1` (original spec). Keep `/club-manage` only as a login return URL that redirects to that club page after session.

---

## 1. Findings — established design rules

These are locked. The rebuild must follow them exactly.

### Header and navigation (do not touch)

| Rule | Source |
| --- | --- |
| Never edit `.site-header`, `.admin-v10-second-header`, or `js/blank-landing-header.js` | `.cursorrules`, master-header lock |
| Header links stay **white** on `#001f3f` | `docs/design_system.md` |
| Do not copy a second header into a standalone page | `docs/UI_COMPONENTS_README.md` §5 |
| Auth slot is owned by `js/session.js` + `js/blank-landing-header.js` | `js/session.js` hub-header isolation |

`/events` and the current `/club-manage` both emit a **simplified copy** of `.site-header` + `.nav-inline`. That is existing debt on the public events page. It is **not** a pattern to extend. New club-officer UI must sit under the real hub header (SPA / club page), not a pasted nav.

### Allowed classes only

`container`, `card`, `table`, `table-container`, `section-title`, `section`, `tabs`.

Forbidden for this rebuild: inline CSS, page-level fonts or colours, raw `<ol>`/`<ul>` for lists, extra wrappers around the master card order, new CSS files.

### Master page order (locked)

`buildMasterPageLayout(container, opts)` is the documented Club/Regatta/Sailor/Class wrapper:

1. Back link
2. **Title card** — `.card` (optional `.class-hero`): h1, description
3. **Stats card** — `.card.stats-card` with `.class-stats` **anchor links only**
4. **Data cards** — `#id.card` > `h2.section-title` > `.table-container` > `table.table`

Do not reorder, add wrappers, or drop `.table-container`.

### Live club / class gold standard (what officers already see)

Public `/club/{abbrev}` and the Class gold-std view use the same visual language even when they do not call `buildMasterPageLayout` by name:

- `.container` + `.card` + `h2.section-title` (uppercase, `#001f3f` underline)
- Event / sailor / regatta **names as links**, never typed IDs
- `table.table` inside `.table-container` with `.hide-mobile` on secondary columns
- Search filter uses the existing `.section-heading-row` + `.club-sailors-filter-input` / `.club-table-filter` (navy pill, 44px)
- Public calendar uses `.event-card` + Upcoming / Live / Past tabs — **read-only browse**, not an admin form

Class page table columns to copy for event lists:

`# · Event · Date · Host (hide-mobile) · Entries · Class · Races (hide-mobile)`

### Tokens (do not invent)

| Token | Value |
| --- | --- |
| Page background | `#f5f7fa` |
| Card | white, `2px solid #001f3f`, 8px radius |
| Body text | `#1e293b` / `#334155` |
| Section title | 0.85rem, 700, uppercase, navy underline |
| Font | system stack already on `body` |
| Container | max 1100px, 12px padding (0.75rem on mobile) |
| Touch | **44px** min on `button`, `.btn`, table headers |
| Table cells | nowrap; horizontal scroll only |

`main.css` already styles `form`, `input[type=text|email]`, `select`, `.btn-primary`, `.btn-secondary`. Login’s extra fonts / `.form-group` / `.login-container` are **login-only**. Do not copy them onto club-manage.

### Mobile

- Mobile-first, single column. Portrait ≤768px is **locked** — do not change shared portrait rules.
- `.table-container` already scrolls sideways; one line per cell.
- `.hide-mobile` hides secondary columns below 600px.
- Do not add new breakpoints or page-level media queries.
- Buttons stay 44px; do not shrink like header `.btn-primary` (that compact rule is header-only).

### Events page — what to reuse vs leave alone

Reuse from `/events` and club calendar:

- Event **name + date + host code** as the human key
- Result line wording stays locked: `Results are [Provisional\|Final] as at DD Month YYYY at HH:MM`
- Type badge navy (`#001f3f`) if a type is shown

Do **not** reuse for manage:

- Coloured Upcoming / Live / Past tab buttons (green / orange / red)
- Event-card swipe carousel
- Copied `.site-header` + inline `<style>` blocks in `api.py`

Those are public-calendar chrome. Club manage is a **table workflow**.

---

## 2. Reusable components (use these, nothing else)

| Component | Use on club-manage |
| --- | --- |
| Hub header | Already on SPA / club-linked hub. Do not fork. |
| `buildMasterPageLayout` | Page shell for the manage view |
| `.card` + `.section-title` | Every block |
| `.table` + `.table-container` | Events, fleets, entries, ingest preview |
| `.class-stats` / `.stats-link` | In-page jump: Events / Fleets / Entries / Upload / Publish |
| `.event-card` | **Do not** use on manage. Public calendar only. |
| Class dropdown | `<select>` filled from `GET /api/club/me/events` → `race_classes[]` (`class_name` visible, `class_id` in `value` only) |
| Event dropdown | Same payload → `events[]` (`event_name` + date visible) |
| `login.html` + `returnTo` | Unauthenticated redirect. Relative `returnTo` already works. |
| `js/session.js`, `js/api.js` | Session + `credentials: same-origin`. Add `sailingSessionClubId()` as Step 3 specified. |
| Existing buttons | `button` / `.btn` / `.btn-primary` / `.btn-secondary` from `main.css` |

**Do not ship** `club-score-edit.js` onto this page or any new slug.

---

## 3. What is wrong with current `/club-manage`

| Current | Why it fails |
| --- | --- |
| Standalone HTML in `api.py` | Bypasses theme / hub header (`UI_COMPONENTS_README` §5) |
| Copied `.site-header` + `.nav-inline` | Second header; locked nav must stay the real one |
| Numbered cards “1. Create event” … “5. Publish” | Feature dump, not a club page |
| `<input name="regatta_id">` / `event_id` | Manual database IDs |
| Hosted-events table shows raw `regatta_id` | Officers pick events by name/date on every other page |
| Preview and commit in one click | Step 3 asked for a **preview table**, then a separate commit |
| No selected-event state | Later steps do not follow the event just created or clicked |
| Does not call `buildMasterPageLayout` | Club pages must |
| Does not load `session.js` / `api.js` | Parallel fetch + `?session=` instead of the hub session |
| 403 page is another standalone shell | Should be one `.card` under the real header |

The interrupted `cursor/club-manage-ui-045e` work started down this path. **Do not continue it.** This plan replaces that UI.

---

## 4. Proposed host and auth

```
Unauthenticated  →  /login.html?returnTo=/club-manage
Sailor (403)     →  hub page, one .card: “A club admin or club manager login is required.”
                    Link to public /club/{abbrev} if we know it; no manage tables.
club_admin /
club_manager     →  /club/{abbrev}?manage=1  (abbrev from GET /api/club/me)
super_admin      →  same, scoped to session admin_club_id when set;
                    if none, title card says choose a club from the Events table
                    (still names, not typed IDs).

/club-manage     →  302 to /club/{abbrev}?manage=1 after session
                    (keeps the bookmark / returnTo that already exists)
```

Permissions copy in the **title card description** (plain language, no role jargon dump):

- You can manage events **hosted by {ZVYC / HMYC}**.
- That is the club on your login. You cannot host for another club.
- Sailors do not use this page. When entries are open they enter from the public event.
- Super admin can help any hosted event; club officers only see their own.

`host_club_id` is always taken from the session. Never shown as a field.

---

## 5. Proposed layout

One selected event drives every card below Events. Selecting a row (or creating an event) sets that selection. IDs stay in JS only.

```
[ Back to results ]                         ← existing master back control

┌─ Title card ─────────────────────────────┐
│  ZVYC — manage events                    │
│  You can create and publish events       │
│  hosted by ZVYC. Club admin / manager    │
│  for this club only.                     │
└──────────────────────────────────────────┘

┌─ Stats card (anchors only) ──────────────┐
│  Events    Fleets    Entries             │
│  Upload    Publish                       │
└──────────────────────────────────────────┘

┌─ Events (#club-manage-events) ───────────┐
│  EVENTS                                  │
│  table: Date · Event · Venue · Entries   │
│         · Results · Fleets               │
│  last row: Title · Start · End · Venue   │
│            · Class (select) · Create     │
└──────────────────────────────────────────┘

┌─ Fleets (#club-manage-fleets) ───────────┐
│  FLEETS — {selected event name}          │
│  table: Class · Races sailed             │
│  last row: Class (select) · Add fleet    │
│  Entries: Open | Closed  [Set]           │
└──────────────────────────────────────────┘

┌─ Entries (#club-manage-entries) ─────────┐
│  ENTRIES — {selected event name}         │
│  table: Helm · Sail no · Class · Source  │
│  last row: SAS ID · Helm · Sail no       │
│            · Class (select) · Add        │
└──────────────────────────────────────────┘

┌─ Upload (#club-manage-upload) ───────────┐
│  UPLOAD — {selected event name}          │
│  Choose file  [Preview]                  │
│  preview table: Class · Sail no · Helm   │
│                 · Place · Warnings       │
│  [Commit scores]  (enabled after preview)│
└──────────────────────────────────────────┘

┌─ Publish (#club-manage-publish) ─────────┐
│  PUBLISH — {selected event name}         │
│  Status line (locked wording)            │
│  Provisional | Final  [Publish]          │
│  link: view public /regatta/{slug}       │
└──────────────────────────────────────────┘
```

### Events table (selection, not IDs)

| Date | Event | Venue | Entries | Results | Fleets |
| --- | --- | --- | --- | --- | --- |
| 13 Sep 2026 | Cape Classic | … | Open / Closed | Provisional / Final / — | ILCA 6, ILCA 7 |

- Event cell is the name (link to `/regatta/{slug}` when a slug exists).
- Row click or a **Select** text link in the Event cell sets the working event. Selected row stays visually a table row (no new highlight colour — use existing table / bold name link).
- Hide `Venue` and `Results` with `.hide-mobile` if the row is tight.
- **Never** show `regatta_id`, `event_id`, or `class_id`.

Create is the **last table row**, not a separate stacked form: Title, Start, End, Venue, Class `<select>` from `race_classes`, button “Create event”. On success, that new event becomes the selection and the Events table reloads.

### Fleets / entries / upload / publish

All bound to the selected event name in the section title (`FLEETS — Cape Classic`). If nothing is selected, the table body is one row: “Select an event above.”

- **Class selects:** options are `class_name`; `value` is `class_id`. Officer never types an ID.
- **Open / Closed:** a `<select>` in the Fleets card, not an `event_id` field. `PATCH /api/club/events/{id}` with the selected event’s id from JS.
- **Entries table** filled from existing `GET /api/regatta/{id}/class-entries`. Add row uses SAS ID + sail number + class select. Empty-score remove is a table action, not a form.
- **Upload:** file input + Preview. Preview fills the table. Commit is a second button, disabled until preview succeeds. Do not auto-commit.
- **Publish:** show the locked status sentence from current `result_status` + `as_at_time`. Select Provisional or Final. No date rewrite.

### How each step operates (officer-facing)

1. **Create or select an event** — name, dates, venue, one or more classes. The club is already yours; you do not enter a host.
2. **Fleets** — add classes that will race. Open entries when the Notice is ready. Closed is the default.
3. **Entries** — register a sailor by SAS ID and sail number into a fleet. Official name comes from SAS, not free-typed identity.
4. **Upload** — Preview the Sailwave HTML/CSV as a table. Commit only after the table looks right. Existing scores are updated, not deleted.
5. **Publish** — Provisional or Final. The public regatta page and sailor profiles already read those rows.

---

## 6. Data already available (no new product APIs)

`GET /api/club/me` → `role`, `admin_club_id`, `club_abbrev`

`GET /api/club/me/events` →

- `events[]`: name, dates, venue, `entry_open`, linked `regatta_id` (JS only)
- `regattas[]`: `result_status`, `blocks[]` with `class_name`
- `race_classes[]`: `class_id`, `class_name`

Writes already live: create event, add class, patch `entry_open`, add/delete empty entry, ingest preview/commit, patch `result_status`.

Optional later (not in this UI pass): claim scraped event, sailor self-enter surface. Do not add them while rebuilding layout.

---

## 7. Implementation notes (only after approval)

| Do | Do not |
| --- | --- |
| Render manage cards on `/club/{abbrev}?manage=1` via `buildMasterPageLayout` | Keep growing the `api.py` HTML string |
| `/club-manage` → redirect to that URL | Ship a second theme-less page |
| Reuse `login.html` `returnTo`, `session.js`, `api.js` | New auth UI |
| Patch **live** `api.py` only if the redirect must live there; never overwrite live 83k with git ~28k | Continue `cursor/club-manage-ui-045e` form dump |
| `pre-change-backup.sh` before any live `api.py` edit | Edit master header, locked results sheets, or `club-score-edit.js` slugs |
| Match live frontend; no local-only CSS | Invent `.club-manage-*` styles or inline CSS |
| Disposable session for browser check after approval | Deploy this plan |

Mobile check after approval: Events table scroll, 44px Create/Add/Preview/Publish, dropdowns usable at 375px, selected event name still readable.

---

## Approval

Reply to implement this layout (recommended: **layout only**, no new APIs, no deploy until the page is reviewed). This document is the specification; it is not a licence to code until you say so.
