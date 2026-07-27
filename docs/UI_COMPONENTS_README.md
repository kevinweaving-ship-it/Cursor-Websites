# UI Components & Layout — Hard Rules (Do Not Break Pages)

**Store this in Cursor memory for easy access so layout and pages cannot be broken.**

---

## Hard rules

1. **Never modify the header or navigation layout.**
   - Header: `.site-header` in `sailingsa/frontend/index.html` and `public/index.html` (and about, etc.).
   - All links inside the header must remain **white** on the dark background (`#001f3f`).
   - Do not change the structure of the header, nav items, or mobile menu overlay.

2. **Never modify the footer structure** (if present) without explicit approval.

3. **Always reuse existing components and classes.**
   - Use: `.container`, `.card`, `.table`, `.table-container`, `.section-title`, `.section`, `.tabs`.
   - Use `buildMasterPageLayout(container, opts)` for Regatta, Sailor, Class, and Club pages — do not replace it with a different layout.

4. **Do not invent new CSS frameworks or new global styles.**
   - Follow **`/docs/design_system.md`** strictly.
   - All typography, colours, spacing, and component styles must come from the design system and `sailingsa/frontend/css/main.css`.

5. **Future UI changes must only modify components or page sections, not the global layout.**
   - Do not add extra wrapper divs, change the order of Back / Title / Stats / Data cards, or remove `.table-container` from the master template.
   - Do not introduce standalone HTML pages that bypass the theme layout.

6. **Allowed classes (from theme rule):** `container`, `card`, `table`, `tabs`, `section`.  
   **Forbidden:** raw `<ol>`/`<ul>` for results, inline CSS, custom page-level fonts or colours.

---

## Reusable components (reference)

| Component | Location / usage | Locked? |
|-----------|-------------------|---------|
| **Header** | Inline in `index.html` / `public/index.html`; `.site-header` | **Yes — do not modify** |
| **Footer** | Same as header | **Yes — do not modify** |
| **PageContainer** | Use `.container` inside `main` | Reuse only |
| **SectionContainer** | Use `.card` or `.section` | Reuse only |
| **Card** | `.card` + optional `h2.section-title`, `.table-container` | Reuse only |
| **Table** | `table.table` inside `.table-container` | Reuse only |
| **EventCard** | `.event-card` (events page; structure in API + CSS) | Reuse only |
| **RegattaTable** | `table.table` with Regattas columns (Event, Date, Club, Entries, Races) | Reuse only |

Component snippets and examples live in **`sailingsa/frontend/components/`** for reference and Storybook.

---

## Quick reference

- **Design system:** `docs/design_system.md`
- **Theme/layout rule:** `.cursor/rules/theme-layout-mandatory.mdc`
- **Master layout:** `buildMasterPageLayout(container, opts)` in `index.html` / `public/index.html`
- **Main CSS:** `sailingsa/frontend/css/main.css`

When in doubt: reuse existing classes, follow the design system, and do not change header/footer or master layout structure.
