# Test and special URLs (SailingSA)

**Canonical base:** `https://sailingsa.co.za` (no `www`, HTTPS).

Use this list when you need to open **test views**, **utilities**, or **non-standard entry points** without hunting paths. **Add a row here** whenever a new standalone HTML page ships for QA or experiments.

---

## Quick copy (live)

```
https://sailingsa.co.za/
https://sailingsa.co.za/blank.html
https://sailingsa.co.za/cape-classic-series.html
https://sailingsa.co.za/regatta_viewer.html
https://sailingsa.co.za/site-stats.html
https://sailingsa.co.za/results/full.html
https://sailingsa.co.za/results/lite.html
https://sailingsa.co.za/blank2.html
https://sailingsa.co.za/admin_dashboard_v10_main.html
https://sailingsa.co.za/landing.html
https://sailingsa.co.za/index.html
```

*(Production home is usually `/` — nginx may serve the same app as [`blank.html`](https://sailingsa.co.za/blank.html); see `docs/NEW_LANDING_PAGE_BLANK_README.md`.)*

---

## What each URL is for

| URL | Purpose |
|-----|--------|
| [`/`](https://sailingsa.co.za/) | **Production home** (main landing). |
| [blank.html](https://sailingsa.co.za/blank.html) | Same landing as `/` when nginx maps root to `blank.html` (see README above). |
| [cape-classic-series.html](https://sailingsa.co.za/cape-classic-series.html) | **Test:** Cape Classic **series** aggregation (three legs); `noindex`. Not a normal regatta URL. |
| [regatta_viewer.html](https://sailingsa.co.za/regatta_viewer.html) | **Utility:** SA results viewer (standalone tool). |
| [site-stats.html](https://sailingsa.co.za/site-stats.html) | **Utility:** Site statistics page. |
| [results/full.html](https://sailingsa.co.za/results/full.html) | **Utility:** Full results HTML shell (if used in your workflow). |
| [results/lite.html](https://sailingsa.co.za/results/lite.html) | **Utility:** Lite results HTML shell. |
| [blank2.html](https://sailingsa.co.za/blank2.html) | Alternate / secondary blank-landing variant (if deployed). |
| [admin_dashboard_v10_main.html](https://sailingsa.co.za/admin_dashboard_v10_main.html) | **Admin:** dashboard UI — treat as **sensitive**; do not share publicly. |
| [landing.html](https://sailingsa.co.za/landing.html) | Alternate landing variant (legacy / experiments). |
| [index.html](https://sailingsa.co.za/index.html) | Legacy SPA home entry (see README above for `/` vs `blank.html`). |

---

## Local repo only (not guaranteed on live)

These live **outside** the usual frontend deploy zip unless you copy them:

| File | Purpose |
|------|--------|
| `test_mobile_view.html` (project root) | Mobile viewport iframe test. |
| `header_test.html` (project root) | Regatta header component test. |

Open locally: `file:///…/Project 6/test_mobile_view.html` (adjust path).

---

## Asking the assistant

You can say: **“Open the URLs in `docs/TEST_URLS.md`”** or **“Add the new test page to TEST_URLS”** so paths stay documented.
