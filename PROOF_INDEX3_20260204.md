# Proof: index3.html and avatars (4 Feb 2026)

**Backup tag:** `BU_20260204_0849`

## Backup (BU)

- **index3.html** → `index3.html.BU_20260204_0849`
- **assets/avatars/** → `assets/avatars.BU_20260204_0849/` (copy of avatars folder)

Restore: `cp index3.html.BU_20260204_0849 index3.html` and optionally restore `assets/avatars` from the BU folder.

---

## What index3.html does (proof of behaviour)

### Page and URL

- **File:** `sailingsa/frontend/index3.html`
- **URL:** `http://192.168.0.130:8081/sailingsa/frontend/index3.html`

### Sailor profile box (permanent)

- One results box is **always visible** (no `display: none`).
- **Empty/dormant:** Placeholder skeleton (Back to results, tabs, header with "—", "Select a sailor from search or sign in...").
- **Logged-in, no search:** Box is filled with the **logged-in sailor’s profile** (same `showSailorStatsInResults` as search).
- **Search with result clicked:** Box shows that sailor’s profile.
- **Search &lt; 5 chars / cleared:** If logged in, box shows logged-in profile; else placeholder.

### Profile function (no ReferenceError)

- `showSailorStatsInResultsFn` is defined at **block level** (not only inside `runSailorSearch()`), so it exists on load.
- `window.showSailorStatsInResults = showSailorStatsInResultsFn` is set before any async “load logged-in profile” logic.
- After that, an async IIFE runs: `checkSession()` then, if valid, `window.showSailorStatsInResults(sasId, displayName, club, [], { isLoggedInUser: true })` so the box gets the logged-in profile when search is empty/dormant.

### Avatars

- **Local folder:** `assets/avatars/`
- **Custom:** `assets/avatars/{SAS_ID}.png` or `.jpg` (e.g. `21172.png`) replaces initials (T, JK, etc.).
- **Default youth (9–18):** `assets/avatars/default-youth.png` used for **all sailors aged 9–18** when no custom avatar.
- **Fallback:** API thumbnail → media/avatars → initials (on img `onerror`).
- **Size:** Avatar 36×36px, `object-position: center top`, `overflow: hidden` so full cap shows in box.

### Avatars in BU

- `21172.png` – custom for SAS ID 21172 (e.g. Timothy Weaving).
- `default-youth.png` – same image used for all sailors 9–18 years.
- `README.md` – explains naming and default youth avatar.

---

## Quick test

1. Open `http://192.168.0.130:8081/sailingsa/frontend/index3.html`.
2. Log in → box shows logged-in sailor profile (not placeholder).
3. Search sailor, click result → box shows that sailor’s profile.
4. Clear search → box shows logged-in profile again (or placeholder if not logged in).
5. Youth sailor (9–18) → avatar is `default-youth.png` if no custom `{SAS_ID}.png`/`.jpg`.
6. Custom avatar (e.g. 21172.png) → shows in profile instead of “T”.

---

*Proof doc created 2026-02-04 after BU_20260204_0849.*
