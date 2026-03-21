# SailingSA UI Components

Reusable layout and UI pieces. **Header and Footer are locked — do not modify.**

All styles come from `../css/main.css` and **`docs/design_system.md`**. Do not add new CSS frameworks; reuse these patterns.

| Component          | Class / usage                    | Notes                    |
|-------------------|-----------------------------------|--------------------------|
| Header            | `.site-header`                    | **Locked** — in index.html |
| Footer            | (if present)                     | **Locked**               |
| PageContainer     | `<div class="container">` inside `main` | Max-width 1100px, centered |
| SectionContainer  | `<section class="card">` or `.section` | Use `.card` for content boxes |
| Card              | `.card` + optional `h2.section-title` + `.table-container` | See design_system.md |
| Table             | `table.table` inside `.table-container` | 44px min header height |
| EventCard         | `.event-card` (events page)       | Structure in api.py + main.css |
| RegattaTable      | `table.table` with Event, Date, Club, Entries, Races | Use in buildMasterPageLayout |

Stories for Card and Table are in `*.stories.js` for visual preview in Storybook.

**Setup (tooling):** From `sailingsa/frontend` run `npm install`. Then: `npm run format` (Prettier), `npm run lint` (ESLint), `npm run storybook` (Storybook on port 6006). Optional IDE: Prettier, ESLint, Tailwind IntelliSense, HTML/CSS support extensions.
