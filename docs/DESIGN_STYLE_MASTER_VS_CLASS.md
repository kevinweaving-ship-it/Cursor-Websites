# Design / style / font / size / colour / boxes / layout – Master vs Class

Pure **design token comparison** (no DOM/structure). Same file: `index.html` + `main.css`.

---

## Global (both pages)

| Token | Value | Where |
|-------|--------|--------|
| **Font family** | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif` | `body` in main.css |
| **Page background** | `#f5f7fa` | `body` |
| **Main content bg** | `transparent` | `main` |
| **Content width** | `max-width: 1100px`, `margin: auto`, `padding: 12px` | `.container` (mobile: `padding: 0 0.75rem`) |

---

## Boxes / cards

| Element | Master (/) | Class (/class/…) | Match? |
|---------|------------|------------------|--------|
| **Main card** | `.profile-card`: bg `#fff`, border `2px solid #001f3f`, radius `8px`, padding `0.5rem 0.85rem`, line-height `1.35` | `.card`: same in main.css | ✅ |
| **Card hover** | `box-shadow: 0 4px 12px rgba(0,31,63,0.12)` | Same `.card:hover` | ✅ |
| **Intro/search box (master only)** | `.home-intro-box`, `#home-search-rows`: bg `#fff`, border `2px solid #001f3f`, radius `8px`, padding `1rem 1rem 1.25rem` | — | — |

---

## Typography – headings / titles

| Role | Master (/) | Class (/class/…) | Match? |
|------|------------|------------------|--------|
| **Big title (name / class name)** | `.sailor-name`: `1.35rem`, `700`, `#0f172a` (mobile); `1.6rem` (desktop) | `.class-hero h1`: `1rem`, `700`, `#001f3f`, `letter-spacing: 0.02em`; mobile `1.1rem` | ❌ Size/colour differ |
| **Section heading in card** | `.profile-card-header`: `0.85rem`, `700`, `#001f3f`, uppercase, `letter-spacing: 0.02em`, `border-bottom: 2px solid #001f3f`, `padding-bottom: 0.35rem`, `margin-bottom: 0.4rem` | `.card .section-title`: same in main.css | ✅ |
| **Regatta history h2 (master)** | `.sailor-career-regatta-history h2`: `1.125rem`, `700`, `#001f3f` | — | — |
| **Latest News h2 (master)** | Inline: `1.125rem`, `700`, `#001f3f`, `border-bottom: 2px solid #e65100` | — | — |

---

## Typography – body / labels / values

| Role | Master (/) | Class (/class/…) | Match? |
|------|------------|------------------|--------|
| **Body text** | `body`: `#1e293b`, `line-height: 1.6` | Same | ✅ |
| **Secondary / description** | `.profile-card-label`: `#666`, `400`; `.profile-card-body`: `0.85rem`; `.class-bio` / `.class-assoc`: `0.85rem`, `#666`, `400` | `.class-bio`, `.class-assoc`: `0.85rem`, `#666`, `400` | ✅ |
| **Value / emphasis** | `.profile-card-value`: `#001f3f`, `700` | Stats links: `#001f3f`, `600`; table links: `#001f3f`, `600` | ✅ (weight 600 vs 700 on class) |
| **Small label** | `.profile-card-name-label`: `0.7rem`, `#666`, `400`, uppercase, `letter-spacing: 0.04em` | — | — |
| **Name in card** | `.profile-card-name-value`: `1rem`, `700`, `#001f3f`, `letter-spacing: 0.02em` | Class title (h1) uses `1rem` `#001f3f` (different from sailor-name) | — |

---

## Colours (hex)

| Use | Master | Class | Match? |
|-----|--------|--------|--------|
| **Primary / headings / links** | `#001f3f` (navy) | Same | ✅ |
| **Dark text (name)** | `#0f172a` (sailor-name) | Not used; class uses `#001f3f` | ❌ |
| **Body text** | `#1e293b` | Same | ✅ |
| **Secondary / grey** | `#666`, `#64748b`, `#334155`, `#475569` | `#666` (class-bio, class-assoc) | ✅ |
| **Input/placeholder** | `#333`, `#FF6600` placeholder | — | — |
| **Borders – card** | `2px solid #001f3f` | Same `.card` | ✅ |
| **Borders – divider** | `1px solid #e0e0e0`, `2px solid #e0e0e0`, `1px solid #e5e7eb` | Table: `1px solid #e0e0e0` (td) | ✅ |
| **Table header** | `2px solid #001f3f`, `#001f3f`, `600` | Same `.table thead th` | ✅ |

---

## Tables

| Token | Master (`.sailor-career-regatta-history`) | Class (`.card .table`) | Match? |
|-------|--------------------------------------------|------------------------|--------|
| **th** | `padding: 0.4rem 0.6rem`, `border-bottom: 2px solid #001f3f`, `color: #001f3f`, `font-weight: 600`, `text-align: left` | Same in main.css | ✅ |
| **td** | `padding: 0.4rem 0.6rem`, `border-bottom: 1px solid #e0e0e0` | Same + `white-space: nowrap` | ✅ (class adds nowrap) |
| **Links** | `color: #001f3f`, `font-weight: 600`, `text-decoration: none`; hover `underline` | Same `.card .table a` | ✅ |
| **Table font-size (master)** | `0.9rem` on table | Not set on .table (inherits body) | — |

---

## Buttons / tabs (master only)

| Element | Style |
|---------|--------|
| **.sailor-profile-tab** | `0.9rem`, `600`, `#001f3f`, bg `#e8ecf7`, border `2px solid #001f3f`, radius `6px`, padding `0.5rem 0.9rem` |
| **.sailor-profile-tab.active** | `#fff`, bg `#001f3f`, border-color `#001f3f` |
| **Back button (inline)** | `13px`, `600`, `#fff`, bg `#001f3f`, radius `6px`, padding `6px 12px` |

---

## Layout – spacing

| Area | Master | Class |
|------|--------|--------|
| **Container padding** | `12px` (mobile `0.75rem`) | Same (class lives inside same .container) |
| **Card margin** | Profile card `margin-bottom: 0.875rem`; last 0 | `.card` `margin-bottom: 16px` |
| **Section title margin** | `.profile-card-header` `margin-bottom: 0.4rem` | `.card .section-title` `margin: 0 0 0.4rem 0` ✅ |

---

## Mismatches to fix (design only)

1. **Class page title (class name)**  
   - Master sailor name: `1.35rem` (mobile) / `1.6rem` (desktop), `#0f172a`.  
   - Class: `1rem`, `#001f3f`.  
   - To match master “hero” title: set `.class-hero h1` to `1.35rem` and `#0f172a` (and desktop `1.6rem` if desired).

2. **Optional: table font-size**  
   - Master regatta table: `font-size: 0.9rem`.  
   - Class: inherits body. Add `.card .table { font-size: 0.9rem; }` to match.

3. **Placeholder profile card border**  
   - HTML has `border: 1px solid #001f3f` on placeholder; CSS `.profile-card` uses `2px solid #001f3f`. One source of truth (e.g. remove inline and use class) keeps boxes consistent.

---

## One-line design summary

- **Font:** Same stack everywhere.  
- **Sizes:** Section titles and card body match (0.85rem, etc.). Class **title** is smaller/different colour than sailor name.  
- **Colours:** Navy `#001f3f` and greys `#666` etc. aligned; sailor name uses `#0f172a`, class title uses `#001f3f`.  
- **Boxes:** `.card` and `.profile-card` use same border, radius, padding.  
- **Layout:** Same `.container`, same max-width and padding.  
- **Tables:** Same th/td/link styles; class adds `white-space: nowrap` and same border/colour rules.
