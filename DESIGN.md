# SailingSA — DESIGN.md

> Portable design context for Google Stitch and other design agents.
> **Authoritative code:** `docs/design_system.md`, `sailingsa/frontend/css/main.css`, and existing approved live components. This description must not override those files or immutable UI decisions.

## Product and intent

SailingSA is a **dense, mobile-first sailing operations and results application**, not a cinematic marketing website. A 390px portrait user should immediately see the key sailor, event, results or discussion data with minimal scrolling. Responsive layout retains the most important information on the left, revealing optional columns toward the right as screen width grows.

## Design language

- Feel: compact, information-rich, clean, modern, fast, accessible.
- Background: `#f5f7fa`; content cards: `#ffffff`.
- Main dark navy: `#001f3f` for header/card titles, headers white on navy.
- Brand purple: `#6B2C91`; secondary red: `#DC143C`. Use accents sparingly and consistently.
- Primary text: `#1e293b`; internal card text: `#334155`; generic border `#ddd` / `#e0e0e0`.
- System font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif`.
- App body about 14–16px. Card section heading around `0.85rem`, uppercase, bold, restrained. Never use 72–96px marketing hero typography on functional pages.
- Main container max 1100px. Mobile container has 12px horizontal padding.
- Standard card padding mobile `0.5rem 0.75rem` and desktop `0.5rem 0.85rem`; table cells `0.4rem 0.6rem`. Prefer existing approved component dimensions over invented values.
- Keep touch interactions accessible (target area around 44px) without inflating cards, tabs or result rows.

## Responsive and component constraints

- **Mobile portrait 390×844 first**, then smaller 320px, larger 430px, landscape and desktop.
- No horizontal clipping, floating half-width cards, empty air, giant controls, text covered by overlays, hidden results or data duplication.
- Existing master header and compact sailor profile header are **locked**. Do not edit or reposition them.
- Reuse `.container`, `.card`, `.table`, `.table-container`, `.section-title` and the approved sibling card rather than generating new competing shells.
- Sailor results: compact lite table in portrait; preserve rank and essential fields. Reveal additional details with more width rather than moving the essential rank away.
- Regatta displays: keep approved full/lite modes and scoring structures; visual ideas must not change API, DB, event results or sailor identity.
- Dockside Chat: fully readable comment/reply text, compact actions, no artificial three-line clamping; keep existing author, timestamp and controls.
- Weekly roundup: newest edition has a visible right navigation arrow, older editions both left/right where older/newer items exist. Arrow placement must work when no hero image is present.
- Respect `prefers-reduced-motion`; interactions should remain functional without animation.

## Design-agent boundary

MotionSites supplies **reference techniques**, not a new SailingSA theme. Stitch may generate a **sandbox mock-up or alternative only when explicitly requested**, using this file as context. Do not apply generated CSS or output to the live site without Plan → scoped diff → visual validation → CI → verified deployment. No new DB schema just because a mock-up implies one.

## Source / acceptance

Always inspect the original relevant screen and real assets before offering a variant. Compare 390×844 screenshots and the existing approved master, then test portrait, landscape and desktop. Source changes belong in GitHub; production release must follow `sailingsa/deploy/SSH_LIVE.md` with REA SSH, backup, rollback, live clicks and CI checks.

See `docs/WEBSITE_DEVELOPMENT_SOP.md` and `docs/DEVELOPMENT_TOOL_ROUTER.md`.
