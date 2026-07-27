# Admin UI design spec (Dash V2)

Design tokens and patterns extracted from the landing page (`sailingsa/frontend/public/index.html` and `sailingsa/frontend/css/main.css`) so Admin Dash V2 uses the same system 1:1.

---

## Font stack

- **Primary:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif`
- **Body:** Same as primary (set on `body` in main.css).

---

## Base typography

- **Base font-size:** Not set on `html`; inherit (browser default 16px). Use `rem` for scaling.
- **Line-height:** `1.6` (body).
- **Letter-spacing:**  
  - Labels / uppercase: `0.04em`–`0.05em`  
  - Headings / emphasis: `0.02em`  
  - Ad/small caps: `0.05em`

---

## Color tokens

From `main.css` `:root` and landing usage:

| Token / usage        | Value        | Notes                    |
|----------------------|-------------|--------------------------|
| `--primary-color`    | `#6B2C91`   | Purple (buttons, etc.)   |
| `--secondary-color`  | `#DC143C`   | Crimson                  |
| `--text-color`       | `#333`      | Body text                |
| `--bg-color`         | `#f5f5f5`   | Page background          |
| `--white`            | `#ffffff`   |                          |
| `--border-color`     | `#ddd`      |                          |

Landing / header (inline and main.css):

| Usage              | Value        |
|--------------------|-------------|
| Navy (header, key UI) | `#001f3f` |
| Navy hover         | `#002a52`   |
| Orange primary     | `#e65100`   |
| Orange hover       | `#ff6f00`, `#FF6600` |
| Orange border/focus| `#cc4400`   |
| Muted text         | `#666`, `#64748b`, `#94a3b8` |
| Dark text (headings)| `#0f172a`, `#001f3f` |
| Table header (blue)| `#2C3B8D`   |
| Table border       | `#e0e0e0`, `#b0b8d4` |
| Row alternate      | `#F4D68B` (golden), `#fff` |
| Card border        | `#001f3f`   |
| Input placeholder  | `#FF6600`   |

---

## Background

- **Page:** Solid `var(--bg-color)` → `#f5f5f5` (no gradient in main.css or index).
- **Header:** `#001f3f` (navy); bottom border `1px solid rgba(255, 255, 255, 0.1)`.
- **Search header (dark block):** `#001f3f`; pill container can be `transparent`.
- **Ad/side panels:** `#f0f4f8`, `#e8eef4`, `#e8ecf0`.

---

## Container

- **Max-width:** `1200px`
- **Padding:** `0 20px`
- **Margin:** `0 auto`
- **Selector:** `.container`

At 768px and below, header `.container` uses `padding: 0 0.75rem`.

---

## Card styles

- **Border-radius:** `8px` (profile cards, placeholders); `6px` (buttons, thumbnails); `4px` (inputs, small UI).
- **Shadow:** `0 4px 12px rgba(0,31,63,0.12)` (card hover); `0 4px 12px rgba(0,0,0,0.2)` (overlay/modal).
- **Profile card:** `border: 2px solid #001f3f`, `border-radius: 8px`, `padding: 0.5rem 0.85rem`.
- **Card hover:** `box-shadow: 0 4px 12px rgba(0,31,63,0.12)`.

---

## Button styles

- **Primary (.btn-primary):**  
  `background: var(--primary-color)`, `color: var(--white)`, `border: none`, `padding: 0.75rem 1.5rem`, `border-radius: 4px`, `font-size: 1rem`, `font-weight: 500`.

- **Pill / search mode (.search-mode-btn):**  
  `padding: 0.35rem 0.75rem`, `font-size: 0.85rem`, `font-weight: 600`, `color: #fff`, `background: #001f3f`, `border-radius: 999px`.  
  Active: `background: #e65100`, `box-shadow: 0 0 0 1px #e65100`.  
  Hover: `#002a52` / `#ff6f00`.

- **Header secondary (.header-refresh-btn, .btn-logout):**  
  `background: rgba(255, 255, 255, 0.15)`, `border: 1px solid rgba(255, 255, 255, 0.3)`, `color: #fff`, `padding: 0.35rem 0.65rem`–`0.5rem 1rem`, `border-radius: 6px` / `4px`, `font-size: 0.8rem`–`0.9rem`.

- **Menu button (.menu-btn):**  
  `background: rgba(255, 255, 255, 0.1)`, `border: 1px solid rgba(255, 255, 255, 0.2)`, `padding: 0.5rem`, `border-radius: 4px`.

---

## Link styles

- **In header / navy (.main-nav a):** `color: #ffffff`, `text-decoration: none`, `font-weight: 500`; hover: `opacity: 0.8`, `text-decoration: underline`.
- **In content (e.g. career/regatta):** `color: #001f3f`, `font-weight: 600`, `text-decoration: none`; hover: `text-decoration: underline`.
- **Headline hover:** `color: #e65100`, `text-decoration: underline`.

---

## Table styles

- **Regatta search table:**  
  `width: 100%`, `border-collapse: collapse`, `font-size: 11px` (10px at 768px).  
  `th`: `background: #2C3B8D`, `color: #fff`, `padding: 6px 8px`, `border: 1px solid #b0b8d4`, `font-weight: 700`.  
  `td`: `padding: 6px 8px`, `border: 1px solid #e0e0e0`, `color: #111`.  
  `tbody tr:nth-child(odd)`: `background: #F4D68B`; `even`: `background: #fff`.  
  Row hover: `filter: brightness(0.97)`.

- **Career / profile tables:**  
  `th`: `text-align: left`, `padding: 0.4rem 0.6rem`, `border-bottom: 2px solid #001f3f`, `color: #001f3f`, `font-weight: 600`.  
  `td`: `padding: 0.4rem 0.6rem`, `border-bottom: 1px solid #e0e0e0`.  
  `tbody tr:hover`: `background: #f5f5f5`.  
  Links: `color: #001f3f`, `font-weight: 600`.

---

## Breakpoints

- **1023px:** Hide side ad columns (`.ad-column-left`, `.ad-column-right`).
- **768px:**  
  Header padding and logo size reduced; nav/auth spacing and font sizes reduced; `.nav-menu-overlay` becomes full-screen overlay; `.btn-primary` and form controls smaller.
- **640px:** Stats iframe and search heights adjusted.
- **480px:** Tighter padding and font sizes; search labels `0.7rem`, `min-width: 75px`.

---

## Mobile nav behavior

- **Desktop:** `.nav-menu-overlay` is dropdown: `position: absolute`, `top: 100%`, `right: 0`, `background: #001f3f`, `border-radius: 4px`, `padding: 0.5rem 0`, `min-width: 140px`, `box-shadow: 0 4px 12px rgba(0,0,0,0.2)`. Toggled via `.menu-btn`; `display: none` when closed, `flex` when open.
- **≤768px:** Overlay becomes full-screen: `position: fixed`, `top/right/bottom/left: 0`, `border-radius: 0`, `padding: 4rem 1rem 1rem`, `background: rgba(0,31,63,0.98)`, `z-index: 9999`. Links: `padding: 1rem 1.25rem`, `font-size: 1.1rem`, `min-height: 44px`, `border-bottom: 1px solid rgba(255,255,255,0.15)`. Hover: `background: rgba(255,255,255,0.1)`.
- **Toggle:** JS toggles `display: none` vs `flex` and `aria-hidden`; menu button has `aria-expanded`, `aria-controls="navMenuOverlay"`. No gradient on overlay; solid navy with slight transparency on mobile.

---

## Summary for Admin Dash V2

- Use the same **font stack** and **line-height: 1.6**.
- Use **.container** `max-width: 1200px`, `padding: 0 20px`.
- Use **#001f3f** for header and primary UI; **#e65100** / **#FF6600** for accents and active states.
- Cards: **8px** radius, **2px solid #001f3f** or equivalent, shadow on hover as above.
- Buttons: **4px** radius (6px for header secondary); same padding and font-weight scale.
- Tables: same header (e.g. #2C3B8D or #001f3f), borders, and alternating row colors where applicable.
- Breakpoints: **1023**, **768**, **640**, **480**; mobile nav full-screen overlay at **768** with same navy and link styling.
