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

## Recorded scoresheet (wins)

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

Gold **Wins** and **F15…F1** cells keep the numeric team points (including F3/F4 audited 15s). Officials’ sheet is the source of those scores. **Rank** is calculated from D4.3 wins; a two-team overall tie is broken by the last race those two sailed against each other (winner above loser).

---

## Calculated standings — displayed Rank

Calculated D4.3 then D4.4(a)(1)–(4) + D4.4(c), **without** D4.4(a)(5). Two-team ties use last head-to-head first (`["last", "h2hPct", "h2hAvg", "common"]`).

Among the three 3-win teams (Eden, RCYC B, MAC) each beat one of the others (cycle). H2H win % and H2H average points do not split the three. Common-opponent averages then put MAC behind Eden and RCYC B. Restarting D4.4 on the remaining two (D4.4(c)) uses F5 (RCYC B beat Eden) and ranks **RCYC B above Eden**.

| Rank | Team | Wins |
| --- | --- | --- |
| 1 | RCYC A | 5 |
| 2 | RCYC B | 3 |
| 3 | Eden | 3 |
| 4 | MAC | 3 |
| 5 | MATIES | 1 |
| 6 | UCT | 0 |

When the event is Final / closed / complete and the last pair is odd (F15 sailed, F16 empty), hide empty F16 and its table. Gold columns stay F15…F1 (`highestUsedFlight`).

---

## UI change (original gold table only)

One existing gold table (`#macTslGoldSheet`). No second table. Surrounding Event URL (header, wind, media, flights/teams cards, master nav) stays as-is.

| Column | Before (error) | After (final) |
| --- | --- | --- |
| Rank | 1–6 from lowest point-sum | D4.3 wins; last H2H splits a 2-team tie |
| Club | Club | **Club/Team** (label only) |
| Wins | (was Total = point-sum) | race wins 5 / 3 / 3 / 3 / 1 / 0 |
| Total | — | sum of recorded flight scores including F3/F4 `score_adjust`: A 34, Eden 50, B 50, MAC 51, UCT 65, MATIES 67 |
| F15…F1 | team race points | **unchanged** team race points |

DOM classes stay the standard Event URL set: `table-wrapper`, `fleet-results-table`, `rs-compact-row-logos`, `rank-col`, `club-col`, `total-col` (Wins uses this class), `race-col`, `rs-club-with-logo`, `medal-gold` / `medal-silver`. No new font, colour, or row-height rules.

Podium: RCYC A `medal-gold`; RCYC B `medal-silver` (`rank === 2`). Eden is 3rd with no bronze. Medal colours remain `css/regatta.css` (`#D4AF37` / `#D7D7D7`).

Status: `regattas.result_status = 'Final'` and `as_at_time` via the existing stamp path. Header reads `Results are Final as at DD Month YYYY at HH:MM`. `stamp_tsl_provisional` already refuses to overwrite Final.

No roster edits. No invented penalties. `score_adjust` and all 15 flight grids stay stored.

---

## DOM / CSS / JS validation (before execution)

| Surface | Keep | Change |
| --- | --- | --- |
| `css/regatta.css` th/td 8px, 1px `#1d294d` borders, system-ui, `#1a2750` | yes | none |
| `#macTslGoldSheet` 2px wrapper (already matches `.header` / `.class-header`) | yes | none |
| Split pane `.tsl-gold-left` + `.tsl-gold-right` overflow-x | yes | left headers nowrap so `Club/Team` and `Wins` do not wrap |
| `goldBuilt()` D4.3 wins + last H2H for 2-team ties | yes | header labels only |
| `goldItemMedal` | gold 1, silver 2 | never bronze |
| Flight note table `Team \| B1… \| Total \| W/L` | yes | not the gold table |
| Master header / nav / wind / media | yes | none |

---

## Gold split layout fix (413px clip)

Live: `.tsl-gold-left` was **413px** with `overflow:hidden` while the left table’s content width was **431px**. Cause: `flex: 0 1 auto` plus `max-width: 62%` (58% / 54% on smaller breakpoints) shrinks the pane; the table is `width: 100%` of that squeezed pane and the last column / join border is clipped. A second white strip comes from `.race-col{max-width:3em}` plus the right table `width: max-content`, so flight columns cannot fill leftover width.

**Smallest correction (CSS + Total column placement only):**

- Left pane `flex: 0 0 auto; max-width: none; overflow: visible`. Left table `width: max-content` so Rank | Club/Team | Wins | **Total** size to content and are never clipped. Club names still ellipsis via existing `.club-col` max-width.
- Move **Total** from the scroll pane onto the locked left table (user: keep Rank | Club/Team | Wins | Total visible).
- Right pane `flex: 1 1 0; min-width: 0; overflow-x: auto`. Right table `width: 100%; min-width: max-content`. Drop `race-col` **max-width**. Keep `min-width: 2.2em` (no scale/squeeze). Extra width is shared by F columns; if 15× min-width exceeds the pane, swipe left (F15 is already first).
- Join: keep right first-cell `border-left: none` so the left last-cell right border is the shared gridline. Outer 2px `#macTslGoldSheet` border unchanged. `syncGoldRowHeights` unchanged.
- Gold sheet `width: 100%` of the fleet block; page padding (16px / 12px at ≤768) is the equal left/right inset. No extra white strip.

MP ≤480px: same rules; fewer F columns in view; no 54% left cap (that was the clip). ML: F columns grow to fill.

Do not change scores, ranks, logos, fonts, medals, or cards above/below.

---

## Mobile ≤480px impact

Portrait uses the existing split: locked left Rank | Club/Team | Wins | **Total**; remaining width is `.tsl-gold-right` with `overflow-x: auto` and `-webkit-overflow-scrolling: touch`. Columns are newest-first (`goldRaceNos` reverses, F15 after Total). Swipe left reveals older flights. No 54%/58%/62% left cap (that clipped the 431px table inside 413px). Club names ellipsis at `club-col` max-width 6.4em. Race columns keep `min-width: 2.2em` (no 2.1em squeeze). Gold thead/td are `font-size:90%` so F1 also fits on Mac/PC.

- `Club/Team` is longer than `Club`; left thead `white-space: nowrap` so the label stays one line.
- `Wins` is a single digit; **Total** is two digits — both stay on the locked pane.
- Flight cells, 15 columns, row-height sync, fonts, and medal fill are unchanged.
- No second table, no fleet-header note.

No 480px layout rewrite. Do not hide Rank / Club/Team / Wins / Total. Do not stack the split pane.

---

## Code

- `goldBuilt()` / gold headers in `js/mac-tsl-admin.js` and `sailingsa/frontend/js/mac-tsl-admin.js`  
- Pin `mac-tsl-admin.js?v=20261022h`  
- `stamp_tsl_final` in `sailingsa/backend/tsl_team_racing.py`  
- Tests: `sailingsa/backend/test_tsl_admin_js.py`, `sailingsa/backend/test_tsl_team_racing.py`
