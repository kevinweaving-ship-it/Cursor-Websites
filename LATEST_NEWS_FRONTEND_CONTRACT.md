# Latest News — Frontend Visual Contract (Complete)

**No backend, scraping, filters, or APIs were modified.** Frontend-only fixes.

## Required Frontend Fixes (Implemented)

### 1. Fixed visual structure
- Card height is consistent: image container always 16:9 with min-height; body has min-height so spacing does not collapse.
- Card spacing unchanged: `margin-bottom: 1rem` between cards.

### 2. Image === null → placeholder
- When `image === null`, render a **neutral placeholder block** (gradient `#e5e7eb` → `#d1d5db`), same 16:9 container. No collapse, no logo fallback.

### 3. Image dominance
- Image container: **fixed aspect ratio 16:9**, `object-fit: cover`, `min-height` so portrait/uncropped images never stretch layout.
- On image load error: wrap gets placeholder gradient; img hidden so layout stays stable.

### 4. Headline rules
- `font-weight: 600`, line-height tightened (`1.28`).
- **Mobile:** clamp to exactly **2 lines** (`-webkit-line-clamp: 2`).
- **Desktop (≥640px):** clamp **2–3 lines** (`-webkit-line-clamp: 3`).

### 5. Excerpt rules
- Max **2 lines** (line-clamp: 2), font smaller and muted (`0.875rem`, `#6b7280`) so visually subordinate to headline.
- **Missing excerpt:** only headline + meta rendered; no empty paragraph.

### 6. Source + time
- Single muted row: **Source · relative time** (· = middle dot).
- `white-space: nowrap; overflow: hidden; text-overflow: ellipsis` so it **never wraps** to two lines.
- Font-size **smaller than excerpt** (`0.75rem`, `#9ca3af`).

### 7. Empty / degraded data
- **Missing image** → neutral placeholder block (gradient), same 16:9 box.
- **Missing excerpt** → headline + meta only; card body min-height keeps rhythm.

---

## Acceptance Test

Compare visually against News24 mobile:
- Scroll rhythm identical (no card “jumps”).
- No visual noise.
- Fixed card structure; no layout shift when image loads or is null.

---

## Deliverables

### ONE mobile screenshot
1. Open the site on a **mobile** device or DevTools device toolbar (e.g. iPhone 12, 390×844).
2. Scroll to **Latest News**.
3. Confirm: fixed card height, 16:9 image/placeholder, headline 2 lines max, excerpt 2 lines max (or hidden if empty), source · time on one line.
4. Capture **one** screenshot of the Latest News section (header + 2–3 cards).

### ONE desktop screenshot
1. Open the site at **desktop** width (e.g. 1280px).
2. Scroll to **Latest News**.
3. Confirm: image right-aligned (or placeholder), headline 2–3 lines, excerpt 2 lines, source · time one line; no card jumps.
4. Capture **one** screenshot of the Latest News section (header + 2–3 cards).

---

## Summary

- **Layout:** Stable, professional; card height consistent; image 16:9 with placeholder when null.
- **Typography:** Headline dominant (600, 2–3 lines); excerpt subordinate (2 lines); meta single line, muted.
- **Data handling:** Missing image → placeholder block; missing excerpt → headline + meta only.
- **No backend changes.** Task complete when layout is stable and matches the contract above.
