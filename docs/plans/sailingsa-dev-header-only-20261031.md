# SailingSA /dev/ — Header-only acceptance plan (2026-10-31)

STATUS: PLAN ONLY. No /dev/ deployment, no frontend implementation, no live-file modifications.

## Boundary
- Proposed URL: https://sailingsa.co.za/dev/ (same origin, route not yet verified/configured).
- Only one visual component: existing SailingSA header. No roundup, events, search, chat, or profile body.
- Main homepage, existing routes and production authentication remain unchanged.
- Work from the authoritative live header, not the stale repository snapshot.
- Do not deploy dev header until server route ownership and fallback/rewrite handling are verified.

## Verified source details
- Live /var/www/sailingsa/index.html has #headerLogoLink linking to / and official /assets/logos/sailingsa-logo.png.
- Live header has #headerAuth and #loginBox, with dynamic signed-in/out state.
- /var/www/sailingsa/js/session.js contains sailingHandleHeaderSignIn, sailingHandleHeaderSignUp, updateHeaderAuthStatus, stored session handling, login.html and signup.html returnTo logic.
- Live deployed source differs from REA repository snapshot: do not blindly copy code or overwrite production.
- /dev/ uses same origin but shared cookies and localStorage; treat auth as production-sensitive, not an isolated sandbox.

## Locked pre-build audit
1. Capture reference screenshots at 375, 390, 430 and 480 px, and tablet/desktop; logged-out + logged-in states, including avatar/menu.
2. Identify exact authoritative header HTML, styles, assets, scripts, event handlers, auth calls, global dependencies, and their route scope. Confirm which code owns each button.
3. Inspect hosting config and /dev/ rewrite/fallback behaviour without modifying it. Verify the /dev/ path can be isolated.
4. Verify the real asset files and auth navigation returnTo rules; avoid /dev/ in login/signup URLs and prevent changes to production session logic.
5. Write a contract covering all visible controls and exact click destinations, including logo and signed-in profile navigation.

## One clean implementation only after audit and approval
- One dev/header markup owner, one scoped stylesheet, one narrowly scoped controller.
- No changes to shared JS/CSS, production API, sessions, redirect logic or live templates.
- Do not copy the current landing page as the dev page. Import only identified header dependencies through a controlled interface; otherwise stop and report blocker.
- Do not invent avatars, account states, links, or artwork.
- No alternate designs, duplicate handlers, inline corrective CSS or !important patches accumulating in accepted code.
- Rejected work remains in disposable branch; only reviewed implementation is promoted.

## Acceptance and negative tests
- Visual comparison to current header at 375/390/430/480 px; no overflow, clipping, tap-target or focus failures.
- Official logo asset and home navigation /.
- Signed out: Sign In and Sign Up show correct destinations and no duplicate clicks.
- Signed in: user identity and avatar (if set), profile link, menu and logout state correct.
- Refresh/back navigation: session persists or clears exactly as production intends.
- Real auth click tests only under an explicitly approved safe test account; never accidentally sign out a live user.
- /dev/ remains isolated: homepage, /login.html, /signup.html, profile and other routes pass before/after regression checks.
- AST/style audit: exactly one authoritative dev component implementation; dead code, unused imports, duplicate rules, global selectors, external writes fail.
- Document exact touched paths. No progression to next component unless *all* checks pass.

## Hard-stop conditions
- Cannot identify source of truth for header auth or valid reuse path.
- /dev/ route would require editing global auth/redirect handlers.
- Any production path would change as a side effect.
- No real-browser test available to validate UI.
- Existing functionality cannot be proven in test environment.

## Deliverables for audit
A. current-state header capture and dependency map;
B. exact-file implementation proposal;
C. one working /dev/ header when permitted;
D. pass/fail evidence for each control;
E. proof that no non-header files or production routes changed.

No task after the header is authorised by this plan.
