# Line-by-line: where index2.html (works) and index.html (broken) differ

## 1. First difference – inline `<style>` (around line 36)

| index2.html | index.html |
|-------------|------------|
| Line 35: `.visually-hidden { ... }` | Line 35: same |
| Line 36: `/* Search Header Below Main Header (News24 style) */` | Line 36: `/* News24-style Top Header */` |
| Line 37: `.search-header { background: #ffffff; ... }` | Line 37: `.top-header { display: grid; ... }` |

**Why it matters:** index2 uses a simple `.search-header` (one search bar). index.html uses `.top-header` and then ~300 lines of extra CSS (`.header-center`, `.search-box`, `.label-choice-box`, `.social-icons`, `.weather`, etc.). Same link to `css/main.css`; the difference is only in this big block of inline styles.

---

## 2. Inline CSS – `.sailor-search-results` (index2 line 244 vs index.html line 588)

| index2.html line 244 | index.html line 588 |
|----------------------|----------------------|
| `.sailor-search-results { margin-top: 0.5rem; display: flex; flex-direction: column; max-height: 70vh; overflow-y: auto; }` | `.sailor-search-results { margin-top: 0.5rem; display: flex; flex-direction: column; max-height: 70vh; overflow-y: auto; }` |

**Same** – one rule, box scrolls inside (70vh + overflow-y: auto).

---

## 3. End of `<style>` – index2 has no scroll block, index.html has extra block

| index2.html | index.html |
|-------------|------------|
| Line 1219: `}` | (many more rules) |
| Line 1220: `</style>` | Line 1565–1568: `/* PAGE SCROLL FIX */` then `html, body { ... }`, `.main-content, .layout-three-col, ...`, `#main-search-results ... { max-height: none !important; overflow: visible !important; }` |
| | Line 1569: `</style>` |

**Why it matters:** index2 has **no** html/body/main-content/main-search-results overrides. index.html adds a “PAGE SCROLL FIX” that forces `#main-search-results` to `max-height: none` and `overflow: visible`, and forces layout to `overflow: visible` / `max-height: none`. So index.html is mixing two ideas: (1) one scrollable box like index2, and (2) page-level scroll via #main-search-results. That only works if no ancestor traps scroll; if any parent still has overflow/flex/height, scroll stays broken.

---

## 4. HTML `<body>` – first structural difference

| index2.html | index.html |
|-------------|------------|
| Line 1222: `<body>` | Line 1571: `<body>` |
| Line 1223: `<header class="site-header">` | Line 1572: `<!-- Dark Blue Header (Original) -->` then same |
| Line 1250–1257: `<header class="search-header">` with one search input | Line 1599–1656: `<header class="top-header">` (grid, search-box, Sailor/Regatta labels, social icons, weather, date) |
| Line 1259–1272: `<header class="secondary-header">` with nav | Line 1658–1674: secondary-header **commented out** |
| Line 1274: `<main class="main-content">` | Line 1676: `<main class="main-content">` |
| Line 1276–1279: `<div class="ad-banner-top" id="adBannerTop">` | **Missing** – no `ad-banner-top` in index.html |
| Line 1281: `<div class="layout-three-col">` | Line 1678: same |
| Line 1285: `<div class="main-column">` then `<div class="container">` | Line 1687: same |
| Line 1307–1310: `<div class="search-row-container">` then **only** `<div id="sailor-search-results" class="sailor-search-results" ...>` | Line 1708–1715: **First** `<div id="main-search-results" class="sailor-search-results" ...>` then `<div class="search-row-container">` then `<div id="sailor-search-results" ...>` |

**Why it matters:**  
- index2: **one** results div (`#sailor-search-results`). Profile and dropdown both go there. One box, 70vh, overflow-y: auto → scroll inside the box.  
- index.html: **two** results divs (`#main-search-results` then `#sailor-search-results`). Profile goes into `#main-search-results`. So you have an extra wrapper and different DOM order, plus the “PAGE SCROLL FIX” trying to make that one box not limit height. If any parent still constrains height or overflow, scroll stays broken.

---

## 5. Summary – where it starts to differ and why scroll breaks

- **First difference:** inline styles, **line 36–37**: index2 = “Search Header” + `.search-header`; index.html = “Top Header” + `.top-header` and a large block of different header/search CSS.
- **Critical structural difference:** body structure around **index2 line 1307 / index.html line 1708**:
  - index2: no `#main-search-results`, only `#sailor-search-results` (and before that, `search-header` + `secondary-header` + `ad-banner-top`).
  - index.html: **has** `#main-search-results` before `search-row-container`, **no** `ad-banner-top`, **no** visible `secondary-header`, and a different header (`top-header`).
- **Why scroll is broken:** index.html added a second container (`#main-search-results`) and a “PAGE SCROLL FIX” so the page would scroll instead of scrolling inside one box. That only works if the whole chain (html, body, main, layout-three-col, main-column, container) allows height to grow and overflow to show. Something in that chain (or in the extra inline CSS / layout) is still constraining height or overflow, so the fix doesn’t take effect and scroll stays broken.

**Recommendation:** Make index.html match index2’s structure: **one** results container (`#sailor-search-results`), profile injected there when logged in, **no** `#main-search-results`, and **remove** the “PAGE SCROLL FIX” block so the same single-rule, 70vh + overflow-y: auto behavior is used (scroll inside the box, like index2).
