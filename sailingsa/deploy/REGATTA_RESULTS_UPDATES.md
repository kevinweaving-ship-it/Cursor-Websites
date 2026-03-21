# Regatta Results — Local → Cloud Updates

**Rule:** As we finish each new Regatta Results (or frontend) change, **treat the cloud version as needing an update**. Deploy frontend to cloud so https://sailingsa.co.za/ stays in sync with local.

---

## How to update cloud after a change

From **project root**:

```bash
./sailingsa/deploy/push-to-cloud.sh
```

This builds `sailingsa-frontend.zip` from `sailingsa/frontend/`, uploads it to the server, and extracts it to the web root (full replace). No backend or DB steps for frontend-only Regatta Results changes.

**If you use full-tag deploys instead:** build the zip from `sailingsa/frontend/` as in DEPLOYMENT_PLAN.md Step A.3, then upload and extract that zip to the server’s web root.

---

## Regatta Results changes (local) to be on cloud

These were done locally; cloud gets them when you run the steps above.

| Change | Files | What it does |
|--------|--------|--------------|
| No “View results” popup | `sailingsa/frontend/index.html` | Regatta Search click opens Full Regatta Results directly (no modal with Full Regatta / Class Result / Go Back). |
| Full regatta results open expanded by default | `sailingsa/frontend/index.html`, `sailingsa/frontend/regatta/results.html` | Full regatta results open in expanded table view; URL uses `view=expanded`, bar shows Expanded active. |
| Regatta results auto-close like sailor profiles | `sailingsa/frontend/index.html` | Switching to Sailor mode or running a sailor search closes the regatta results modal. Sailor click in regatta results still closes modal and shows sailor profile. |

**Files touched (all under `sailingsa/frontend/`):**

- `index.html` — `showRegattaResultChoice`, `navigateToFullRegattaResults`, `openResultPageInModal`, `navigateToResultView`, `setSearchMode`, `runSailorSearch`
- `regatta/results.html` — default view from `view=expanded` URL param

---

## After deploying

1. Run push (or your full deploy) as above.
2. Quick check: https://sailingsa.co.za/ → Regatta search → click a regatta → should see full regatta results **expanded** with **no** “View results” popup; click a sailor row → modal closes and sailor profile shows; switch to Sailors or run sailor search → regatta modal closes.

---

*Last summary: 2026-02-10. Update this list when adding more Regatta Results (or frontend) changes so cloud stays in sync.*
