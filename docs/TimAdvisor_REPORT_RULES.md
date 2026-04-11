# TimAdvisor report — rules

**Canonical format:** copy structure and tone from **`docs/TimAdvisor_Report_Bazolele_Mseswa.md`**. Same headings, same table columns (**Compared to you**), same sections in the same order.

## Sections (always, sailor-facing)

1. `# TimAdvisor Report for [Name]`
2. `Hi [name],` + one short opening (last regatta, class, place / fleet size, nett, one encouraging line).
3. `## Where you finished` — markdown table: Place | Who | Nett | Compared to you (use “X points ahead” on first gap row if you like, then shorter “X ahead” / “X behind” like the template).
4. One short paragraph under the table (who is above / below on **that** table — **3 above, 3 below** by **rank** next to the sailor).
5. `## Race by race (who had the better finish)` — exact sub-line: **Lower number = better.** This is each race, not the final nett.
6. Bullets: **Name:** He was ahead… / You were ahead… (same voice as Baz template).
7. **Takeaway:** one bold paragraph.
8. `## What you did really well` — bullets.
9. `## One simple thing to grow` — short para + **Try next time:** line.
10. `## Quick note (not the main story)` — one paragraph.
11. Closing line + **TimAdvisor**
12. Optional `---` + *Source: … block_id …*

## Do not

- Put “how this report was built” in the sailor text.
- Call a **race** a **“day”** (unless you mean a calendar day).
- Change the template headings to “Gap vs you” or “One thing to grow” — use **Compared to you** and **One simple thing to grow**.

## Data

- `results`: `block_id`, `rank`, `nett_points_raw`, `race_scores` JSON for H2H (numeric part per race).
