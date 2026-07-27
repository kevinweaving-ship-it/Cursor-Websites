# SailingSA Design System

**Source of truth:** `sailingsa/frontend/css/main.css` and the existing homepage (landing, class, sailor, regatta, club pages). All new UI must follow these tokens and patterns. Do not invent new colours, spacing, or typography.

---

## Typography

| Token | Value | Usage |
|-------|--------|--------|
| **Font family** | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif` | body |
| **Body** | `color: #1e293b`, `line-height: 1.6` | Default text |
| **Box/body text** | `--box-body-text: #334155`, `--box-body-size: 0.9rem` | Text inside cards |
| **Headings (cards)** | `--box-heading-color: #001f3f` | Card titles, section titles, table links |
| **Section title** | `0.85rem`, `font-weight: 700`, `text-transform: uppercase`, `letter-spacing: 0.02em`, `border-bottom: 2px solid #001f3f` | `.card .section-title` |
| **Page title (hero)** | ~`1rem` base, up to `1.1rem` @600px, `1.35rem`–`1.6rem` on larger | Class/sailor hero h1 |

---

## Colours

| Role | Value | Notes |
|------|--------|------|
| **Primary** | `#6B2C91` | Brand purple |
| **Secondary** | `#DC143C` | Accent red |
| **Text** | `#1e293b` | Body |
| **Background** | `#f5f7fa` | Page background; cards stay white |
| **Header** | `#001f3f` | Navy; header links must be **white** |
| **Card border** | `2px solid #001f3f` | `--box-border` |
| **Border (generic)** | `#ddd` / `#e0e0e0` | Dividers, table borders |
| **White** | `#ffffff` | Cards, header text |

---

## Container widths & layout

| Element | Value | Notes |
|---------|--------|--------|
| **Main container** | `max-width: 1100px`, `margin: auto` | `.container` |
| **Container padding** | Mobile: `0.75rem 12px`; ≥768px: `12px` | Do not reduce below 12px on small screens |
| **Ad column** | `160px` width (hidden below 1023px) | Optional layout |
| **Ad banner** | `max-width: 970px` | Top banner slot |

---

## Spacing scale

Use these consistently; do not invent new values.

| Use | Value |
|-----|--------|
| Card padding (mobile) | `0.5rem 0.75rem` |
| Card padding (≥600px) | `0.5rem 0.85rem` |
| Card margin below | `16px` (margin-bottom) |
| Table cell padding | `0.4rem 0.6rem` |
| Section title margin | `0 0 0.4rem 0`, `padding-bottom: 0.35rem` |
| Stats link gap | `margin-bottom: 0.5rem` (last: 0) |
| Touch target minimum | **44px** (buttons, table headers, nav links) |

---

## Buttons

| Type | Notes |
|------|--------|
| **Min height** | `44px` for `button`, `.btn`, `[role="button"]` |
| **Header buttons** | White or light text on `#001f3f`; e.g. `.header-refresh-btn`: `background: rgba(255,255,255,0.15)`, `border: 1px solid rgba(255,255,255,0.3)`, `border-radius: 6px` |
| **Primary (header)** | Use existing `.btn-primary`; do not change header button layout |

---

## Card styles

- **Class:** `.card`
- **Background:** `#ffffff`
- **Border:** `2px solid #001f3f` (`--box-border`)
- **Border radius:** `8px` (`--box-radius`)
- **Box shadow:** `0 1px 3px rgba(0, 31, 63, 0.08)`; hover: `0 4px 12px rgba(0, 31, 63, 0.12)`
- **Padding:** `0.5rem 0.75rem` (mobile), `0.5rem 0.85rem` @600px
- **Margin:** `margin-bottom: 16px`
- **Section title inside card:** `.section-title` — uppercase, 0.85rem, border-bottom 2px #001f3f

Cards must be white; dark backgrounds only in the global header.

---

## Table styles

- **Wrapper:** `.table-container` — `overflow-x: auto`, `-webkit-overflow-scrolling: touch`
- **Table class:** `table.table`
- **Headers:** `min-height: 44px`, `padding: 0.4rem 0.6rem`, `border-bottom: 2px solid #001f3f`, `color: #001f3f`, `font-weight: 600`, `white-space: nowrap`
- **Cells:** `padding: 0.4rem 0.6rem`, `border-bottom: 1px solid #e0e0e0`, `white-space: nowrap`
- **Links in table:** `color: #001f3f`, `font-weight: 600`; hover: underline
- **Optional:** `.hide-mobile` on columns; show from `600px` with `@media (min-width: 600px)`

One line per cell on mobile; horizontal scroll only. No raw `<ol>`/`<ul>` for result lists.

---

## Event card (events page)

- **Class:** `.event-card`
- **Upcoming:** light green background/border; **Past:** light red; **Past with results:** darker red (`.event-card-has-results`)
- **Structure:** `.event-card-header`, `.event-date`, `.event-card-body`, `.event-type`, `.event-result-line`, host/club line
- **Type badge:** `background: #001f3f`, `color: #fff`, `border-radius: 4px`, `font-size: 0.85rem`
- **Result indicator:** green tick (`.event-result-yes`) or red (`.event-result-no`)

Event card styles are defined in the API-rendered events page; keep consistent with `main.css` and this doc.

---

## Master page layout (locked)

Used by Regatta, Sailor, Class, Club. **Do not change order or structure.**

1. Back link (optional)
2. **Title card** — `.card` (optional `.class-hero`), h1, description, association
3. **Stats card** — `.card.stats-card`, `.class-stats` (anchor links only)
4. **Data cards** — one or more `.card` with `id`, `h2.section-title`, `.table-container`, `table.table`

Only content passed into `buildMasterPageLayout(container, opts)` may vary; no extra wrappers or reordering.

---

## Mobile-first & breakpoints

- **Base:** mobile (single column, 44px min touch targets).
- **Breakpoints:** 400px, 480px, 600px, 640px, 768px, 1023px (see `docs/DESIGN_MOBILE_MASTER_VS_CLASS.md`).
- New/updated CSS: define mobile first, then `@media (min-width: …)` for tablet/desktop.

---

## Forbidden

- Inline CSS styles on page content
- Custom page-level fonts or colours not in this doc
- Raw `<ol>`/`<ul>` for results or sailor lists (use `.table` inside `.card`)
- Changing header/navigation layout or link colour (header links must stay white)
- Adding wrapper divs or changing order in the master page layout
