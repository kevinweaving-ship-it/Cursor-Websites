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

Gold table **Rank** and row order use this recorded list. **Wins** replaces the old accumulated-points Total. **F15…F1** cells keep the numeric team points (including F3/F4 audited 15s).

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

One existing gold table (`#macTslGoldSheet`). No second table. Surrounding Event URL (header, wind, media, flights/teams cards, master nav) stays as-is.

| Column | Before (error) | After (final) |
| --- | --- | --- |
| Rank | 1–6 from lowest point-sum | Published: 1, =2, =2, 4, 5, 6 |
| Club | Club | **Club/Team** (label only) |
| Total | sum of flight points | **Wins** (5 / 3 / 3 / 3 / 1 / 0) |
| F15…F1 | team race points | **unchanged** team race points |

DOM classes stay the standard Event URL set: `table-wrapper`, `fleet-results-table`, `rs-compact-row-logos`, `rank-col`, `club-col`, `total-col` (Wins uses this class), `race-col`, `rs-club-with-logo`, `medal-gold` / `medal-silver`. No new font, colour, or row-height rules.

Podium: RCYC A `medal-gold`; Eden and RCYC B both `medal-silver` (`rank === 2`). **No** `medal-bronze` row (published order has no 3rd). Medal colours remain `css/regatta.css` (`#D4AF37` / `#D7D7D7`).

Status: `regattas.result_status = 'Final'` and `as_at_time` via the existing stamp path. Header reads `Results are Final as at DD Month YYYY at HH:MM`. `stamp_tsl_provisional` already refuses to overwrite Final.

No roster edits. No invented penalties. `score_adjust` and all 15 flight grids stay stored.

---

## DOM / CSS / JS validation (before execution)

| Surface | Keep | Change |
| --- | --- | --- |
| `css/regatta.css` th/td 8px, 1px `#1d294d` borders, system-ui, `#1a2750` | yes | none |
| `#macTslGoldSheet` 2px wrapper (already matches `.header` / `.class-header`) | yes | none |
| Split pane `.tsl-gold-left` + `.tsl-gold-right` overflow-x | yes | left headers nowrap so `Club/Team` and `Wins` do not wrap |
| `goldBuilt()` wins + published ranks | yes | header labels only |
| `goldItemMedal` | gold 1, silver 2 | never bronze |
| Flight note table `Team \| B1… \| Total \| W/L` | yes | not the gold table |
| Master header / nav / wind / media | yes | none |

---

## Mobile ≤480px impact

Portrait uses the existing split: locked left Rank | Club/Team | Wins; remaining width is `.tsl-gold-right` with `overflow-x: auto` and `-webkit-overflow-scrolling: touch`. Columns are already newest-first (`goldRaceNos` reverses, F15 at the left of the flight pane). Swipe left reveals older flights.

At 480px: left `max-width: 54%`, club-col `max-width: 6.4em` (ellipsis on long names), race-col `min-width: 2.1em`.

- `Club/Team` is longer than `Club`; left thead `white-space: nowrap` so the label stays one line. Rank + Club/Team + Wins still fit in ~180px of ~259px.  
- `Wins` is a single digit — narrower than the old two-digit point Total, which offsets the longer Club/Team header.  
- Flight cells, 15 columns, row-height sync, fonts, and medal fill are unchanged.  
- No extra column, no second table, no fleet-header note.

No 480px layout rewrite. Do not hide Rank / Club/Team / Wins. Do not stack the split pane.

---

## Code

- `goldBuilt()` / gold headers in `js/mac-tsl-admin.js` and `sailingsa/frontend/js/mac-tsl-admin.js`  
- Pin `mac-tsl-admin.js?v=20261018b`  
- `stamp_tsl_final` in `sailingsa/backend/tsl_team_racing.py`  
- Tests: `sailingsa/backend/test_tsl_admin_js.py`, `sailingsa/backend/test_tsl_team_racing.py`
