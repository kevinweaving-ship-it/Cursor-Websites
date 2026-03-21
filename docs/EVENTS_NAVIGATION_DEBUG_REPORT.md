# EVENTS NAVIGATION DEBUG — READ-ONLY REPORT (NO DR / NO DEPLOY)

## 1. Click interceptors and related patterns

### preventDefault(
| File | Line(s) |
|------|--------|
| sailingsa/frontend/index.html | 13, 47, 62, 2154, 2171, 2750, 2807, 2975, 3451, 3593, 3719, 3804, 4027, 5056, 5086, 5117, 5137, 5147, 5179, 5189, 5200, 5215, 5230, 5982, 6087, 6146, 6167, 6879, 6886 |
| sailingsa/frontend/public/index.html | 13, 47, 62, 2082, 2099, 2606, 2662, 2829, 3304, 3446, 3572, 3641, 3722, 3723, 3931, 4964, 4994, 5025, 5045, 5055, 5087, 5097, 5108, 5123, 5138, 5889, 5957, 6673, 6680 |
| sailingsa/frontend/about.html | 154, 157–158, 162–163, 167–168 |
| sailingsa/frontend/public/about.html | 190, 193–194, 198–199, 203–204 |
| sailingsa/frontend/login.html, public/login.html | 516, 816, 821, 920, 960, 1277, 1484 |
| sailingsa/frontend/facebook-confirm.html, public/facebook-confirm.html | 249, 542, 779 |
| sailingsa/frontend/js/session.js | 203, 317, 399, 784, 789 |
| sailingsa/frontend/js/popup.js | 66, 158, 198 |

### addEventListener("click"
| File | Line(s) |
|------|--------|
| sailingsa/frontend/index.html | 11, 46, 48, 61, 2009, 2153, 2170, 3408, 3421, 3443, 3447, 3531, 3564, 3591, 3718, 3825, 4026, 5055, 5085, 5116, 5136, 5146, 5178, 5188, 5199, 5214, 5229, 5981, 6087, 6146, 6589, 6884, 6987 |
| sailingsa/frontend/public/index.html | 11, 46, 48, 61, 1952, 2081, 2098, 3261, 3274, 3296, 3300, 3384, 3417, 3444, 3571, 3722, 3723, 3725, 3930, 4963, 4993, 5024, 5044, 5054, 5086, 5096, 5107, 5122, 5137, 5888, 6383, 6678, 6781 |
| sailingsa/frontend/about.html | 153, 157, 162, 167, 170 |
| sailingsa/frontend/public/about.html | 189, 193, 198, 203, 206 |
| sailingsa/frontend/regatta/results.html, public/regatta/results.html | 128 |
| sailingsa/frontend/regatta/class/class-results.html, public/regatta/class/class-results.html | 124 |
| sailingsa/frontend/js/session.js | 202, 316, 398, 783, 788 |
| sailingsa/frontend/js/popup.js | 13, 19, 27–31, 46–48, 57–59 |

### history.pushState / history.replaceState
| File | Line(s) |
|------|--------|
| sailingsa/frontend/index.html | 70–71, 1858, 3861–3862, 3869, 3886–3887, 3891, 3894, 3958 |
| sailingsa/frontend/public/index.html | 70–71, 1793, 3766–3767, 3774, 3790–3791, 3795, 3798, 3862 |
| sailingsa/frontend/login.html, public/login.html | 749 |

### fetch(
Many uses in index.html and public/index.html (API calls, session, sailor/class data, etc.). No explicit “router” or “spa” symbol; routing is pathname-based in an async IIFE.

### router / spa / interceptLinks / handleNavigation
- No matches for `interceptLinks` or `handleNavigation`.
- “router” / “spa” only in comments or unrelated uses (e.g. “router” in login/public/login, “spa” in regatta results). No central router object.

---

## 2. Main menu and Events link markup

### In SPA (sailingsa/frontend/index.html)

- **header_home** (lines 1492–1514): no visible nav list; only logo, auth, menu button. **navMenuOverlay** (line 1513) is empty in the source (`<nav id="navMenuOverlay" ...></nav>`). No Events link in static HTML.
- **header_site** (lines 1515–1541):  
  - Desktop: `<nav class="nav-inline">` (1520–1527): Home, Sailors, Regattas, Classes, Clubs, About. **No Events, no Statistics.**  
  - Overlay (1533–1539): same set, no Events.

So in the frontend repo, the main menu **does not** include Events or Statistics. Those links appear only on API-served pages.

### In API (api.py)

Nav used on API-rendered pages (e.g. events, stats) includes Events:

- Example (line 1572, events page):  
  `nav_links = '<a href="/">Home</a><a href="/sailors">Sailors</a><a href="/regattas">Regattas</a><a href="/classes">Classes</a><a href="/clubs">Clubs</a><a href="/stats">Statistics</a><a href="/about">About</a>'`
- In the events page HTML (line 1626):  
  `<nav class="nav-inline" ...>{nav_links}</nav>`  
  and the events page body uses that same nav pattern, which includes `<a href="/events">Events</a>` in the full nav string at 871 and 1469.

So the **exact Events link** on API-served pages is plain:

```html
<a href="/events">Events</a>
```

No `data-` attributes, no `js-` classes, no `onclick`. So from the markup, Events is a normal link.

---

## 3. Global / document-level click handling

### (A) document.addEventListener('click') — “go home” only (index.html ~11–14)

```javascript
document.addEventListener('click', function(e) {
    var a = e.target && e.target.closest && e.target.closest('a.js-go-home');
    if (a) { e.preventDefault(); window.location.replace(home); }
}, false);
```

- Only runs for `a.js-go-home`. Events link is not `js-go-home`, so this does **not** intercept the Events link.

### (B) document.addEventListener('click') — sailor profile / placeholder (index.html ~3825–3845)

```javascript
document.addEventListener('click', function(ev) {
    if (sailorSearchResults.querySelector('#chosen-sailor-before-profile')) return;
    var inRegattaResults = ev.target && ev.target.closest && (...);
    if (inRegattaResults) return;
    var inSearchRows = ev.target && ev.target.closest && ev.target.closest('#home-search-rows');
    if (!inSearchRows && !sailorSearchResults.contains(ev.target)) {
        (async function() {
            try {
                var session = typeof checkSession === 'function' ? await checkSession() : { valid: false };
                // ... showSailorStatsInResults or showSailorProfilePlaceholder()
            } catch (_) {}
        })();
    }
});
```

- Runs on **every** click that is not inside regatta results, search rows, or sailor results.
- Does **not** call `ev.preventDefault()`.
- So it does **not** stop the default action of a link (e.g. `<a href="/events">`).
- It does start an async path that calls `checkSession()` (and then may call `showSailorStatsInResults` or `showSailorProfilePlaceholder()`). If the user is on a page that loads this script (e.g. SPA or a page that includes the same bundle), this runs on every click, including on the Events link. It could add load or race with navigation but does not, by itself, prevent the request from starting.

### (C) navOverlay click (index.html ~48)

- Only closes overlay when target is an `<a>`; no preventDefault on the link’s default action.

### (D) public/index.html ~3725

- `document.addEventListener('click', function(ev) { ... });` — same pattern as (B): no preventDefault, async work (e.g. session/profile).

So there is **no** handler that explicitly converts “all links” into SPA navigation or that preventDefault’s the Events link. The only preventDefault in a document-level click is for `a.js-go-home`.

---

## 4. SPA “router” and whether /events is included

There is no named router. Routing is done by:

- **pathname** (e.g. `window.location.pathname`).
- An **async IIFE** on load (index.html ~3912–3970) that:
  - If path matches `/sailor/([^/]+)`: fetch sailor resolve, then `showSailorProfileFromResult`, return.
  - If path matches `/class/(\d+)-`: fetch class, then `renderClassPage`, return.
  - Else: `checkSession()`, then show logged-in sailor or placeholder, etc.

So the SPA explicitly handles:

- `/` (home)
- `/sailor/{slug}`
- `/class/{id}-...`

It does **not** handle `/events`, `/stats`, `/sailors`, `/regattas`, `/classes`, `/clubs`, `/about`. For those, a normal click would trigger a full document navigation. So **/events is not included in the SPA’s in-app routing**; it is expected to be a full page load.

If the Events link is still on a page that uses the SPA’s bundle (e.g. a shell that loads index.html or the same JS), then the only global click behavior that runs on that link is (B): no preventDefault, but an async `checkSession()` (and possibly profile logic). That could still be relevant for “delay before request starts” if something in that chain is slow or blocks (e.g. a very slow or hanging `/auth/session`).

---

## 5. Network timing test (for you to run)

- Open DevTools → Network. Optionally enable “Preserve log”.
- Click the Events link (from a page where the delay happens).
- Record:
  - **Time from click to when the request to `/events` appears** (e.g. “Request started at +0.1 s” vs “+40 s”).
  - **Request URL** (should be `https://sailingsa.co.za/events` or similar).
  - **Request duration** (e.g. “8 ms” as you already saw for the API).

Interpretation:

- If the **request appears only after ~40 s**, the delay is before the request (e.g. JS blocking or a long-running sync/async step before navigation).
- If the **request starts quickly** but the document takes ~40 s to load, the delay is in server or response handling.

---

## 6. Summary and suggested fix direction

- **No** JS routing attributes on the Events link; it’s a plain `<a href="/events">Events</a>` on API-served pages.
- **No** explicit “router” that lists routes; path-based logic only handles `/`, `/sailor/...`, `/class/...`. **/events is not in the SPA route set.**
- **One** document-level click handler that preventDefault’s anything: only `a.js-go-home`.
- **One** document-level click handler that runs on most clicks (including links) and does **not** preventDefault: it runs an async block that calls `checkSession()` and then profile/placeholder logic. That does not by itself block the Events request, but if the page that shows the Events link loads this script, any slow `/auth/session` or related work could coincide with the click.

**Recommended next step (when you do implement a fix):**  
Ensure that internal links that should perform a **full page load** (e.g. `/events`, `/stats`, `/sailors`, `/regattas`, `/classes`, `/clubs`, `/about`) are not affected by heavy click logic. For example, in the document click handler that runs the async “session + profile” logic, **return early** when the click target is an `<a href="...">` whose `href` is one of these paths (or more generally, any same-origin link that should not be “handled” in-app), so that the default navigation happens immediately and no unnecessary async work runs for that click.

No code was modified; no deploy or D/R was run.
