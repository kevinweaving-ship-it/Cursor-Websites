# Public pages (prep only)

Placeholder routes and components for **public** regatta and sailor pages. No UI polish, no crawling, no auth changes.

- **Routes:** `regatta.html` → `/regatta/{slug}`, `sailor.html` → `/sailor/{slug}` (slug from pathname or query when wired).
- **Component:** `components/public-mention-card.html` — shared stub for Public Mention Card (thumbnail, content-type icon, title, one-line context, external link).

**Note:** The main app (`index.html`) also renders Public Mentions & Sailor Activity in a News24-style vertical feed (image-first, divider-only, grouped by year); see in-app Media and Activity tabs.

## Facebook handling (guardrails)

- Facebook URLs may be stored **only at regatta level** (RegattaMention). Never at sailor level.
- **Only Facebook Pages** allow engagement. Groups and personal profiles are **record-only**.
- **No automated Facebook actions** will ever be implemented (no likes, shares, comments). Read-only archive only.

## Schema

See project root: `docs/PUBLIC_REGATTA_MENTIONS_SCHEMA.md`.
