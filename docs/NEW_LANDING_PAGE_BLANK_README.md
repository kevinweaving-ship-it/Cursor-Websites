# New Landing Page README (`blank.html`)

Page URL: [https://sailingsa.co.za/](https://sailingsa.co.za/) (nginx serves `blank.html` for exact `/`; [https://sailingsa.co.za/blank.html](https://sailingsa.co.za/blank.html) is the same file). Legacy SPA home: [https://sailingsa.co.za/index.html](https://sailingsa.co.za/index.html).

## Purpose

`blank.html` is the new landing page for SailingSA: featured hero, two **News** subcards under it, search, events strip, and stats. Global header/nav/footer stay on the shared layout (do not redesign here).

This README tracks **implemented** behaviour in `blank.html` so updates stay consistent.

## Primary Sections (in order)

1. Search row  
2. Optional search-results card  
3. **Live spotlight** (`#blank-hub-spotlight-section`) — **WC Dinghy Champs multi-fleet hub only** (full-width Breaking parent). Omit for single-fleet live events (e.g. 29er Nationals) so the story appears once in the **News** subcard row (left) next to the partner slot (right), per the two-card pattern below — not duplicated full-width.  
4. **Featured hero** (`#blank-hub-hero-section`) — manual hub story + Super Admin panel when open  
5. **Class kids** (optional) — WC fleet grid when applicable  
6. **Two subcards** (`#blankHubSubcardsRow`):
   - **Left** — previous featured story; **Full View** expands to full hero detail; **limited** view shows compact News row + headline + image (Past/day/stats/podium hidden until Full View).  
   - **Right** — earlier displaced story (see queue below), or **OnePlus / partner ad** visual when no second story (see `blank.html` secondary slot).  
7. Events / calendar block (`#blank-news-section`)  
8. Site statistics grid  

## Featured hero — automatic badge (when `badge_label` not set in hub JSON)

Source event: `heroEvent || teaserFallback` in `blankHubHeroBuildInnerHtml`.

- **`Breaking news`** — event is **`is_live` and `has_results`**.  
- **`Top News`** — otherwise (past, live without results yet, or no linked event).  

Manual Super Admin **badge** text in hub config still overrides the auto label.

## Two News cards — in-memory queue (same browser session)

When the **featured** hero fingerprint changes (new top story), the previous main moves to the **left** card; what was on the **left** moves to the **right**; the new story is the hero.  

- First load: left mirrors main; right shows a short placeholder until there has been a second change.  
- **Full page reload** clears the queue (not persisted server-side).  

Lower cards render with **`lowerKind` `'left'` | `'right'`**: calendar label **Top News** displays as **News** with the blue lower-news badge; only the **left** card has the **Full View** control on the same row as freshness.

## Live ↔ past (product intent)

Featured event selection still comes from `loadBlankNews()` / hub logic (live with results, then fallbacks). The **auto badge** uses `is_live` + `has_results` as above; past featured events typically show **Top News** unless manually overridden.

## Super Admin editing

Single saved hub: **`/api/admin/hub/hero`** (`hub_hero.json`).  

Editor opens from **badge** tap on featured **or** either News card, or **drag/drop** image onto featured hero **or** either lower hero inner.  

Flow: image → headline → day → teaser → link → badge; Save / Clear.

## Podium (featured hero)

- Swipe pages with dots; desktop page size vs mobile page size as implemented in `blank.html`.  
- Medals for top 3; rank / names / nett as built by `blankFormatPodiumHtml`.

## Data sources

- Session: `/auth/session` (via existing session helpers)  
- Hero: `GET /api/hub/hero`, `PUT /api/admin/hub/hero`, `POST /api/admin/hub/hero/upload`  
- Events list: `/api/events` with `blank_hub=1` where used  
- Podium/results: regatta/class endpoints as wired in `loadBlankNews` / hero opts  

## Performance

- Prefer parallel fetches where already batched; keep `blank_hub=1` for scoped events when applicable.

## Change discipline

- One logical change at a time; follow `docs/design_system.md` and `sailingsa/frontend/css/main.css` for shared tokens.  
- Do **not** change global header/nav structure or footer without explicit approval.  
- Re-test guest and Super Admin after edits.

## Verification checklist (after changes)

1. Featured hero shows correct story; auto badge matches **live + has results** vs **Top News** rules (unless manual badge).  
2. Left News: limited vs Full View; freshness + **Full View** alignment.  
3. Right News: appears after second hero change in session; placeholder before that.  
4. Super Admin: open editor from any hero badge; upload/drop still saves and reloads.  
5. Podium swipe/dots on main hero.  
6. Mobile: readable, 44px targets on controls.  

## Optional follow-ups (not requirements)

- Cap subcard height to featured section height (CSS variable / measure).  
- Persist News queue server-side if product needs continuity across reloads.
