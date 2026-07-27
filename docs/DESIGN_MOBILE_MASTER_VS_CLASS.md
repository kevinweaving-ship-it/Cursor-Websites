# Mobile design – Master (/) vs Class (/class/…) – Always mobile-first

**Rule:** Design and CSS must treat **mobile as the default**; enhance for larger screens with `@media (min-width: …)`.

Current codebase uses **desktop-first** (`@media (max-width: …)`). When adding or changing styles, prefer **mobile-first**: base = mobile, then `min-width` for tablet/desktop.

---

## Locked — mobile portrait (audit / scope)

**Status:** **Mobile portrait** (phone held upright: narrow width, typically `max-width: 768px` and `orientation: portrait`) is **accepted as the current baseline — good as-is.** Treat it as **locked for now** so other work does not accidentally regress it.

**Do not change** portrait-mobile layout, spacing, typography, or breakpoint behaviour **while doing unrelated tasks** (tablet, desktop, mobile landscape–only tweaks, blank hub sections, new components, etc.).

**How to change other sizes without touching portrait**

- Prefer **`@media (min-width: 769px)`** (or higher) for tablet/desktop adjustments so **≤768px portrait rules stay as they are**.
- If you must touch shared rules, **narrow the edit** to non-portrait (e.g. `(orientation: landscape)` or a `min-width` band) or get **explicit user approval** for a mobile-portrait change.

**When portrait mobile *may* change**

- The user explicitly asks for a mobile-portrait fix, or
- A small follow-up they approve after review.

**Audit:** When reviewing a PR or task, if files touch `main.css`, hub HTML, or shared components, confirm portrait mobile was not altered unless in scope.

---

## Breakpoints in use

| Breakpoint | Usage |
|------------|--------|
| **400px** | Tabs smaller, search controls tighter |
| **480px** | Header/logo/buttons more compact, sailor-search font 0.7rem |
| **600px** | .hide-mobile (hide table columns), profile-card body 2-col, sailor-profile-tab 0.75rem |
| **640px** | Home intro/site-stats iframe smaller |
| **768px** | Main mobile: container padding 0.75rem, header compact, nav overlay, ad columns hidden, class-hero single column |
| **1023px** | Ad side columns hidden |

---

## Mobile (≤768px) – design tokens

### Layout / container

| Token | Master | Class | Match? |
|-------|--------|--------|--------|
| **Content padding** | `.container` → `0 0.75rem` (12px) | Same (class uses same .container) | ✅ |
| **Max width** | 1100px (unchanged) | Same | ✅ |
| **Ad columns** | Hidden | N/A | — |

### Boxes / cards

| Token | Master | Class | Match? |
|-------|--------|--------|--------|
| **Card** | `.profile-card`: 2px #001f3f, 8px radius, `0.5rem 0.85rem` padding; at 600px `0.5rem 0.75rem`, min-height 44px | `.card`: same (no mobile override in main.css) | ✅ |
| **Card padding on very small** | Profile gets 0.5rem 0.75rem @600px | .card stays 0.5rem 0.85rem | Optional: add .card @600px same as profile |

### Typography – mobile

| Element | Master (≤768px / ≤600px / ≤480px) | Class (≤768px / ≤600px) | Match? |
|---------|------------------------------------|--------------------------|--------|
| **Page title** | .sailor-name: 1.35rem (no 768 change); 1.6rem @ min-width 768px | .class-hero h1: 1rem base → **1.1rem @600px** | Class bumps at 600px; master sailor name is 1.35rem on mobile |
| **Section title** | .profile-card-header: 0.85rem (no mobile change) | .card .section-title: same | ✅ |
| **Body / labels** | .profile-card-label #666; .profile-card-body 0.85rem; @600px body 2-col | .class-bio .class-assoc 0.85rem #666 (no mobile change) | ✅ |
| **Tabs (master)** | @600px: tab 0.75rem, padding 0.35rem 0.5rem, border 1px; @400px: 0.7rem, 0.3rem 0.4rem | — | — |

### Tables – mobile

| Token | Master | Class | Match? |
|-------|--------|--------|--------|
| **Horizontal scroll** | .table-container overflow-x auto, -webkit-overflow-scrolling touch | Same (main.css) | ✅ |
| **1 line per cell** | Not forced on sailor-career table | .table th/td white-space: nowrap | Class stricter (good for mobile) |
| **Touch target** | th min-height 44px (main.css) | Same | ✅ |
| **Hide columns** | — | .hide-mobile @600px on some th/td | Class can hide less important cols |

### Touch targets (44px min)

| Element | Master | Class | Match? |
|---------|--------|--------|--------|
| **Buttons** | button, .btn min-height 44px | Same | ✅ |
| **Table headers** | .table thead th min-height 44px | Same | ✅ |
| **Nav overlay links** | min-height 44px @768px | — | — |
| **Stats links** | — | .class-stats a block, padding from card | ✅ (tap area from card padding) |

### Colours on mobile

No change: same #001f3f, #666, #e0e0e0, #fff, #f5f7fa as desktop.

---

## Very small (≤480px)

| Area | Master | Class |
|------|--------|--------|
| **Header** | padding 0.5rem 0; .container 0 0.5rem; logo 28px; user font 0.7rem/0.6rem; btn-logout smaller | Same (shared header) |
| **Main .container** | Still 0 0.75rem (no 480px override for content) | Same |
| **Class hero** | — | No 480px-specific; h1 already 1.1rem from 600px |

---

## Mobile-first checklist (for new/updated CSS)

1. **Base = mobile:** Default rules = small viewport (single column, readable font-size, 44px min touch targets).
2. **Enhance with min-width:** Use `@media (min-width: 769px)` or `601px` for larger layout (e.g. class-hero grid, multi-column).
3. **Same design tokens:** On mobile, use same font-size, colour, border, and padding as the design doc (DESIGN_STYLE_MASTER_VS_CLASS.md); only layout and density change.
4. **Class page = master on mobile:** Container, card, section title, table scroll, 1-line cells, colours must match https://sailingsa.co.za/ on narrow viewports.

---

## Gaps / recommendations

1. **.card mobile padding:** Optionally add `@media (max-width: 600px) { .card { padding: 0.5rem 0.75rem; } }` so class cards match profile-card on small screens.
2. **.container on very small:** Content padding stays 0.75rem below 480px; could add `@media (max-width: 480px) { .container { padding: 0 0.5rem; } }` for consistency with header if desired.
3. **Mobile-first refactor:** Long-term, base styles could be written for mobile and enhanced with min-width; current max-width overrides are fine as long as mobile tokens match this doc.
