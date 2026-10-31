# GOLD STANDARD — SailingSA canonical site header
Locked: 2026-10-31. Status: immutable default unless owner explicitly authorises a header change.

## Authoritative implementation
The real live production SailingSA homepage header, successfully extracted to `https://sailingsa.co.za/dev/` on 31 October 2026, is the single source of truth for the header on EVERY SailingSA URL.
- Production markup source: `/var/www/sailingsa/index.html`, the entire `<header class="site-header"> ... </header>` element only.
- Canonical stylesheet: `/css/gold-header.css?v=20261030source` plus any verified necessary original header styling/dependencies; do not create alternative approximations.
- Official logo: `/assets/logos/sailingsa-logo.png`.
- Existing authentication: `/js/config.js`, `/js/api.js?v=20260901landingfix`, `/js/session.js?v=20261028_LOGINURL` and required verified existing header wiring.
- Canonical component markup IDs: `headerLogoLink`, `headerUserCenter`, `headerAuth`, `loggedInStatus`, `loginBox`.
- Navy header and browser/Safari top surround must match actual original landing page. Content **beneath** the header follows that page's own design; it must NOT inherit a full-page navy background.

## Absolute visual/functional invariants
1. Exact original header height, logo size, location, colours, horizontal/vertical positioning, navigation and button/icon styling.
2. Official SailingSA logo LEFT; signed-in user identity CENTRED in the designated middle header position; logged-in logout control RIGHT.
3. Logged-out Login and Sign Up controls are EXACTLY the production ones, including icons and styling — no substitute buttons, red boxes or invented controls.
4. Existing session, login/signup, logout, auto-login prompt, profile routing, browser refresh and redirect behaviour must remain unchanged.
5. Do NOT add SAS ID, extra metadata, status panels, debug text, experimental buttons or other unrequested elements.
6. Any new page, including `/dev/`, must reuse the canonical implementation. The header is frozen: work on surrounding page components ONLY.
7. Do not change production/global authentication or routes to make a dev page work. No global overrides, duplicate headers, orphan fragments, copied complete homepage, or accidental changes to the content background.
8. Before shipping any other page, compare the header against the current real production reference with a real browser in mobile portrait, logged-in and logged-out states, and verify browser top area separately on Safari when relevant. A Chrome screenshot cannot prove Safari browser chrome behaviour.
9. If a future requirement explicitly changes the header: first obtain approval, update the ONE canonical implementation surgically, remove superseded logic rather than layer overrides, and regression-test all URLs.
10. This file documents the standard; it does not mean all existing URLs have already passed the parity audit.

## Do not repeat prior failures
Avoid making a visually similar but different header. Do not use inventively hand-coded logo sizes or layouts. The approved method was to extract the exact original live header and reuse its real styles and scripts. No independent redrawing.

## Verification source
The header-only extraction was confirmed via actual mobile Chrome rendering at 390px on 2026-10-31; actual Safari address-bar rendering remains a separate platform-specific verification requirement.
