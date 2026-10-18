# MAC TSL WC — scoring spec (RRS 2025–2028 Appendix D)

Event URL: https://sailingsa.co.za/regatta/2026-10-17-mac-tsl-wc-team-sailing  
Engine: `js/mac-tsl-admin.js` (`goldBuilt`, `teamFlightScore`, `flightScoreAdjust`).  
Authoritative sheet: officials’ TSL racing score sheet, 17/18 Oct 2026, races 1–15.

---

## Previous scoring error

The gold fleet table ranked teams by **accumulated race points** (sum of each flight’s three-boat place total, plus audited `score_adjust`). Lowest sum was treated as rank 1, with a “won last flight” tie-break.

That is **not** Appendix D series scoring. Race points decide **who won that race**. They are not the round-robin ranking criterion.

**Correction:** Total = race **wins**. Flight cells stay the officials’ numeric team points. Published ranks come from the officials’ sheet (recorded), not from point-sum order.

---

## Race (RRS D3.4)

Each team’s three boat finishing places (codes score 7 in this Event URL) plus any audited team-flight `score_adjust` make that team’s race score. **Lowest race score wins** (D3.4). If the two team totals are equal, the team that does **not** have first place wins (D3.4). Existing F3 MATIES +1 and F4 MAC +1 overrides are preserved; they do not change any of the 15 winners.

---

## Series (RRS D4.3 / D4.4)

**D4.3(a)** — Rank by number of race wins, highest first. If teams have not completed an equal number of races, rank by percentage of races won, highest first.

**D4.4** — Ties in a round-robin stage use results from that stage only:

1. Win percentage in races among the tied teams, highest first  
2. Average points per race among the tied teams, lowest first  
3. If two teams remain tied, winner of the last race between them  
4. Average points per race against common opponents, lowest first  
5. Sail-off if possible, otherwise a game of chance  

This Event URL does **not** invent a sail-off or a game of chance (D4.4(a)(5)). Remaining unresolved calculated ties share a rank.

Accumulated race points are **never** the primary overall ranking criterion.

---

## Recorded (published) standings — authoritative

Officials’ scoresheet after 15 races (Score = wins, Position as printed). Joint second is **unresolved on the sheet**. Do not claim D4.4 established it.

| Rank | Team | Wins |
| --- | --- | --- |
| 1 | RCYC A | 5 |
| =2 | Eden | 3 |
| =2 | RCYC B | 3 |
| 4 | MAC | 3 |
| 5 | MATIES | 1 |
| 6 | UCT | 0 |

Wins sum to 15. Each team sailed 5 races (equal, so D4.3 uses wins, not win %).

Gold table **Rank** and row order use this recorded list. **Total** shows wins. **F15…F1** cells keep the numeric team points (including F3/F4 audited 15s).

---

## Calculated standings — separate, not displayed as Rank

Calculated D4.3 then D4.4(a)(1)–(4) + D4.4(c), **without** D4.4(a)(5):

Among the three 3-win teams (Eden, RCYC B, MAC) each beat one of the others (cycle). H2H win % and H2H average points do not split the three. Common-opponent averages then put MAC behind Eden and RCYC B. Restarting D4.4 on the remaining two (D4.4(c)) uses F5 (RCYC B beat Eden) and would rank **RCYC B above Eden**.

| Calculated rank | Team | vs recorded |
| --- | --- | --- |
| 1 | RCYC A | same |
| 2 | RCYC B | recorded **=2** |
| 3 | Eden | recorded **=2** |
| 4 | MAC | same |
| 5 | MATIES | same |
| 6 | UCT | same |

**Disagreement:** officials published Eden and RCYC B as joint second and did not place B above Eden. Calculated D4.4 would split that pair. The gold Rank column follows the **recorded** sheet. The gold wrapper sets `data-tsl-standings-disagreement="1"` and `window.__ssaMacTslStandingDisagreement` when labels differ. No second table. No fleet-header note.

---

## UI change (original gold table only)

| Column | Before (error) | After |
| --- | --- | --- |
| Rank | 1–6 from lowest point-sum | Published: 1, =2, =2, 4, 5, 6 |
| Club | unchanged | unchanged |
| Total | sum of flight points (e.g. 34) | race wins (5 / 3 / 3 / 3 / 1 / 0) |
| F15…F1 | team race points | **unchanged** team race points |

No second table. No roster edits. No invented penalties or DNS codes. `score_adjust` and all 15 flight place grids stay as stored.

Medals: rank 1 gold, both =2 silver, no bronze (no published 3rd).

---

## Mobile ≤480px impact

Existing gold split: left Rank | Club | Total (max-width 54%), right F-columns `min-width: 2.1em`, horizontal scroll. No extra column, no second table, no header note.

- Total values become one digit (0–5) instead of two-digit point sums — slightly more room in the locked left pane.  
- Rank `=2` is two characters; `white-space: nowrap` on `.rank-col` so it does not wrap.  
- Flight cells, 15 columns, and right-pane scroll are unchanged.  
- Row-height sync is unchanged.

No 480px layout rewrite required.

---

## Code

- `goldBuilt()` in `js/mac-tsl-admin.js` and `sailingsa/frontend/js/mac-tsl-admin.js`  
- Pin `mac-tsl-admin.js?v=20261018a`  
- Tests: `sailingsa/backend/test_tsl_admin_js.py`
