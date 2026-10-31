# SailingSA dormant feature archive — landing audit

This directory is **not loaded by the website**. It preserves previously developed features for possible reuse and tracks deliberately disabled functionality. No feature may be reactivated without confirming permissions (including any SAS-related restrictions), data requirements, and regression testing.

## Archived source

| Feature | File | Original source | State | Reuse conditions |
|---|---|---|---|---|
| Podium/congratulations messages | `2026-10-31-congratulations.js.txt` | `index.html`, original commit `f5b291df4f681ec0db2a350a02d572c96714c400`, approximately lines 8974–9125 | Archived original commented-out implementation; removed from active HTML in cleanup commit `9143ff37` | Check SAS/other approval, scoring data assumptions, profile display, accessibility and tests |

### Podium/congratulations feature detail

The historical implementation fetched member results, selected a recent regatta and produced a congratulatory message using position and fleet-relative performance. It referenced result metadata, regatta name, class, club and medal/position presentation. Original code was already enclosed in a `/* RE-ADD LATER */` block after an unconditional return. The small live `loadCongratulations(sasId)` function remains in `index.html` and hides its section; archiving does **not** switch the feature on.

## Other disabled or potentially dormant functionality — NOT YET extracted

| Feature / area | Evidence in original `index.html` | Current classification |
|---|---|---|
| Site-stat gauges | Hidden `#site-stats-embed`; code comment: "temporarily removed (mobile perf / layout); redo later via site-stats.html" | Deliberately hidden, preserve pending dependency check |
| Historical modal handling | Early `purgeLandingModals` removes regatta and sailor modals, including late-added elements | Active defensive behaviour, do not remove without testing |
| Profile media/activity tabs | `sanitizeTempProfileShell` removes their tab nodes from the landing search result | Deliberate visibility rule, not proof feature is unused elsewhere |
| Results and class routes | Functions inside the large inline script render class, regatta and sailor paths | Active shared code, DO NOT extract/remove without route tests |
| Live-board statuses | Interval polling for event status | Active behaviour, optimise after runtime test |

## Preservation / restore

- Full pre-cleanup landing source: branch `backup/landing-before-cleanup-20261031`, commit `f5b291df4f681ec0db2a350a02d572c96714c400`.
- Working cleanup branch: `audit/landing-surgical-cleanup-20261031`, draft PR #278.
- Archive files are **reference copies**, not modules to be imported, evaluated or bundled.
- GitHub restoration is source restoration only; deployed server and database backups are not yet verified.
- Prior to removing more source, identify whether it is live code, intentionally hidden feature, or genuinely obsolete implementation. Archive recoverable feature code first.

## Scanning caveat

A regular-expression search for `/* ... */` falsely spans thousands of active lines when it encounters the phrase `member/* API` inside a `//` comment. Do NOT mass-delete on naive regex classifications. Use a JavaScript parser / syntax-aware scanner and tests.
