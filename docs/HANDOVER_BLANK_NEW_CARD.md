# Handover — New card on `blank.html` only (SailingSA)

**Scope for the next chat:** one feature area on **[https://sailingsa.co.za/blank.html](https://sailingsa.co.za/blank.html)** — the **new isolated card** (Breaking News). Do **not** refactor the rest of the page, other routes, or shared hub logic in the first pass unless this doc is updated.

**Later (separate work):** wire behaviour for the **rest of the page / other URLs** — only after the Breaking News card behaviour is stable.

---

## What “new card” means here

| Block | Role |
|--------|------|
| **Breaking News** (`.blank-breaking-news-card`, `data-bncard-*`) | **In scope** — standalone module; own qualification rules. |
| **Old News spotlight / hub hero** (`#blank-hub-spotlight-section`, `#blank-hub-hero-section`, etc.) | **Out of scope** for “new card” unless explicitly requested — different code paths and DB hub config. |

Do not merge Breaking News logic with spotlight, fleet pills, or `gates`.

---

## Files (Breaking News only)

| File | Purpose |
|------|---------|
| `sailingsa/frontend/blank.html` | Markup for `.blank-breaking-news-card`; loads script; small `.bn-card__*` CSS in same file. |
| `sailingsa/frontend/js/breaking-news-card.js` | All fetch, ordering, render, empty state. **No dependency** on hub globals. |

---

## Viewport strategy — Breaking News card (CSS only; fleet pills + podium)

**Intent:** One mental model — **phone + tablet both rotate**; **desktop** should match the **wide / horizontal** treatment without maintaining a separate “tablet breakpoint” band.

| Situation | Treatment |
|-----------|-----------|
| **Portrait** (`orientation: portrait`, typical phone + tablet upright) | **Locked baseline** — same as **mobile portrait** lock in `docs/DESIGN_MOBILE_MASTER_VS_CLASS.md` (do not regress when tuning wider layouts). |
| **Landscape** (phone or tablet on its side) | **Same “roomy” tier** — larger fleet pills, larger / wider podium text (when implemented). |
| **Desktop** | **Same as mobile landscape** for this card: reuse the same rules — easiest media shape: **`(orientation: landscape)` OR `(min-width: 1024px)`** scoped under `.blank-breaking-news-card` only. |

**Implementation note:** Use a single block such as `@media (orientation: landscape), (min-width: 1024px) { … }` for the “spacious” overrides. That way **narrow portrait** (phone or tablet) stays on the locked styles; **landscape** and **wide desktop** get the bigger UI. *Edge case:* a tablet in portrait with CSS width ≥1024px could pick up the spacious tier via `min-width` only — rare; adjust if it shows up in QA.

---

## Qualification (event → result), steps 1–3

Implemented only in `breaking-news-card.js`:

1. **GET** `/api/events?blank_hub=1` → normalize: `is_live` (dates), `has_results` (`races_sailed` or `entries` on calendar row).
2. **`buildCandidateList`** → ordered unique `regatta_id` list (live + calendar results first, then other live, then past with calendar results — see source comments).
3. **GET** `/api/regatta/{regatta_id}/results-summary` in order → **first** JSON where `entries_total > 0` **or** `races_total > 0` wins; else empty state.

**Authoritative gate is step 3** (DB summary), not the calendar alone.

---

## Live API snapshot (diagnostic, changes over time)

A sample pull of `GET https://sailingsa.co.za/api/events?blank_hub=1` showed **all rows with `regatta_id: null`** and **no** calendar `entries` / `races_sailed` — so **zero candidates** for step 2 and Breaking News stayed empty. If the card never populates, verify backend populates `regatta_id` (and ideally counts) for `blank_hub=1` events.

---

## UI behaviour on live page

- Section title: **Breaking News**.
- Loading → then either body (event name, host, “Results are … as at …” line) or **“No event currently qualifies for automated Breaking News.”**

---

## Related fix (hub hero JS, same `blank.html`)

`blankHubHeroBuildInnerHtml` must define **`oldNewsBadgeClass`** where the Old News purple badge class is used (was a `ReferenceError` risk if undefined). If hero HTML breaks, check that variable exists in that function — separate from Breaking News.

---

## Deploy

After changing `blank.html` or `breaking-news-card.js`, run project **D/R** per `sailingsa/deploy/SSH_LIVE.md` / `deploy-with-key.sh` so [blank.html](https://sailingsa.co.za/blank.html) matches repo.

---

## Helm / Crew lookup (SA — SAS ID or name)

For South African helm/crew fields (compact Claim Event table, SA edit flows, or any regatta-style entry where the user picks a person):

- **Input:** Accept **SAS ID** (numeric / known format) **or** **name** — same field; backend or search resolves both.
- **Suggestions:** Show a **sorted** list of matches (stable order, e.g. by surname then first name, or by relevance score then name).
- **Progressive narrowing:** As the user types **more characters**, the dropdown should show **fewer options** (filter-in-place), not a long static list — classic typeahead behaviour.

---

## Suggested first message in the new chat

> Continue from `docs/HANDOVER_BLANK_NEW_CARD.md`. Scope: Breaking News card on `blank.html` only; extend to rest of page/URLs only after this card is done.
