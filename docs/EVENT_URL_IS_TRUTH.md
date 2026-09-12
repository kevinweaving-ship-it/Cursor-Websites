# Event URL is truth — HARD RULE

**If you only read one results doc, read this.** Print/PDF: `docs/RESULTS_PRINT_PDF_RULE.md`. Rank helper: `appendix_a.py`.

This is the rule that was missed. The sheet was right in the DB and in the first HTML paint. The user’s phone showed the wrong 1st because **JS rewrote the DOM after paint**. Agents then declared it fixed from **raw HTML**. That is how you fuck this up again.

---

## Truth

While an event is **live**, the **event URL** (parent) is **truth**.

Every other surface that shows that event **must use the same live data** — not a copy, not last night’s HTML, not `result_id` order, not a stored product PDF, not a one-off JS reorder.

That stays true **until the event is closed**.

**Months later**, a correction can still land. That correction **is truth**. Whatever it affects (URLs, tables, reports, stored PDFs) must **sync / update automatically**.

Do **not** special-case one live event (Cape Classic or any other) with different ranking or sync rules.

---

## What “live” means

Live is **dynamic / fluid / changing all the time** — even if the only change is **race scores**.

Also (build-up and during live):

- fleets change → **child URLs** change
- entry **counts** change
- **sailors** add / remove / move
- **sail numbers** and anything else on the sheet can change
- class names / language / names can change

The same rule applies to **all URLs that use a live event URL as source**.

---

## What must stay in sync (always, auto)

Any change on the **event URL** must flow to:

- **child URLs** (each class / fleet)
- **landing page search** for that live event (fleets, entries, sailors, children)
- **tables / reports**
- **print / save / share PDF** (live: generate **now** from event URL; not a stale file)

If those disagree with the event URL, they are wrong.

---

## Ranking (not a racing rule: `result_id`)

`result_id` is a database row number. It is **not** RRS Appendix A.

When **assigning rank** on new / updated results (score-save of that fleet):

1. Low **nett** wins
2. Same nett → **A8.1** (counted scores best → worst; first difference wins)
3. Still tied → **A8.2 last race** (then the race before that). Last-race score wins even if shown in parens as a discard

Helper: `appendix_a.py` (`sort_result_rows_appendix_a`).

**Do not:**

- break ties with `result_id`, insert order, DOM order, `data-sheet-order`, or “keep original sheet order”
- re-sort **other events’** published sheets / stored ranks unasked
- add a second client-side ranker that invents 1st/2nd after the server already ranked

Names stay **SAS spelling**, not PDF nicknames. Official fleet name stays official (e.g. Open); class/boat column is the boat.

During live, the **official event PDF** is used only to **correct our URL to official scores** (except SAS spelling and bad class names). Users then print **our URL**, not that official file.

---

## DO NOT declare a live sheet fixed from raw HTML

The user’s URL is what they see **after JS**.

If `club-score-edit.js`, live autoscore, `pollLive`, `applyLiveFleets`, `rerankFleet`, `sortRowsBySheetNett`, `sortByRankings`, `tick()`, or any other script still rewrites `td.rank-col` / row order, **curl / View Source / first paint is a lie**.

**Must verify:** the **rendered** parent URL and the child fleet URL in a browser (or equivalent after JS). If the phone still shows a different 1st, it is not fixed.

Known rewrite sites (do not reintroduce):

- `sailingsa/frontend/js/club-score-edit.js` — `rerankFleet()` used to sort equal nett by `data-result-id` on load and every ~2s via `pollLive` → `applyLiveFleets`
- live `api.py` inline autoscore (`sortRowsBySheetNett`, `sortByRankings`, `sortRowsFromCompleted`, extra `tick()` after a “lock”)
- comments that say “A8 already applied” while the tie-break is still DOM / `data-sheet-order` / `result_id`

If official ranks are already on the row (`data-official-rank`), **do not invent a new 1st/2nd**. Removing the wrong rewrite is the fix; adding another sorter is not.

---

## PDF (does not override truth)

Full rule: `docs/RESULTS_PRINT_PDF_RULE.md`.

1. Source SAS / scrape / official PDF — parse / audit / checksum only. Irrelevant to **our** event PDF generation / print / save / share.
2. **Closed / passed** (Final or Provisional we closed) — generate **our** PDFs on print rules, **store**, then print/save/download/share **fetches** that file. Parent + all children.
3. **Live** — no stored product PDF. Generate **now** from the URL (event header + fleet headers + fleet results). Weather, MM/reels, staff list = URL-only; **out of print**.
4. When the event **closes**, it **leaves (3) and becomes (2)**.

A **later correction** (even months after close) updates truth. Stored PDFs and every URL/table/report that used the old data must **update auto** for that event.

Print layout: too many races → **landscape**; if it fits → portrait. **Fleet/class header + that fleet’s results on the same page** — never split across two pages.

**Today (gap):** Print is `window.print()`; Save on the iframe bar is `html2canvas` PNG, not a clickable PDF. `regattas.local_file_path` is the source archive, not the product PDF. Generator is **not built**. Do not pretend stored source PDFs are the product.

---

## What went wrong (Cape Classic Open — do not rediscover this the wrong way)

Official PDF + RRS Appendix A8, same nett 3:

- Sean Kavanagh 585: R1=2, R2=1 → A8.2 last race **1** → **rank 1**
- Gordon Guthrie 589: R1=1, R2=2 → last race **2** → **rank 2**

A8.1 both have 1 and 2 (still tied). A8.2 last race decides. Gordon’s lower `result_id` is irrelevant.

The Open sheet was **right in DB / first HTML paint**, then **flipped on refresh** because JS re-ranked equal nett by `result_id`. Agents checked raw HTML (Sean first) and called it fixed while the phone showed Gordon first.

**Do not** mass-re-sort other events to “apply Appendix A to display”. Appendix A is for **new rank assignment** (score-save of that fleet), not a global HTML rewrite.

---

## Live `api.py`

Never wholesale-copy repo `api.py` onto live. Surgical edit only (`chattr -i` / patch / `chattr +i`). See `sailingsa/deploy/SSH_LIVE.md`.
