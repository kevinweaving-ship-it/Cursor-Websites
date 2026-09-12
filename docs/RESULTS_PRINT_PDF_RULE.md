# Results print / PDF — product rule

Old SAS / Sailwave PDFs are **source documents only** (parse, audit, checksum). They are not our event result sheet and must not be served as “the” print/PDF of the URL.

**Truth for our print/PDF:** the event URL at that second — event header, each fleet header, that fleet’s results (`public.results` / fleet blocks). Spelling and class names may already be corrected vs the source PDF (SAS names, valid class names). Scores/ranks/fleets must match the URL.

Do **not** mass-regenerate PDFs for other closed events as a side effect of this rule.

---

## What is in the PDF (always)

- Event header (name, host, **Results are [Provisional|Final] as at …**).
- For each fleet: **fleet header + that fleet’s results table**.
- Clickable links where the URL has them (sailor, club, class, etc.) when **Save PDF**.

## What is never in the PDF (URL-only live features)

Ignored on print / save / share, including Cape Classic live:

- Weather / cam cards  
- MM / reels card  
- Staff list / crew gate  
- Live board chrome, score-edit boxes, SA toolbar, Sign up / Login / hub chrome  

Those stay on the URL. They are not the results sheet.

---

## Page geometry (parent and every child sheet)

Same for portrait and landscape:

1. **One fleet, one page block.** Fleet title/sailed-line and that fleet’s result rows must not split across two pages. If it will not fit, start that fleet on the next page — do not leave the header on page N and the table on page N+1.
2. **Orientation:** portrait if the sheet fits; **landscape** if there are too many race columns (too wide). Not “always portrait.”
3. Parent PDF = full event (all fleets), each fleet still obeys (1). Child PDF = one class/fleet sheet, same rules.

---

## Closed events (Final or Provisional, event closed)

Allowed to **pre-create** PDFs for parent + all children from the closed URL (stored rank/results). Those files are snapshots of **our** sheet, not the old SAS file.

If results are later corrected, those PDFs are stale and must be remade from the URL. Do not keep serving the old snapshot as if it were live.

---

## Live events (build-up and during the event)

Different file rule: **do not trust a pre-created PDF.**

Sailors, classes, and fleets change by design (add/drop, class moves, name fixes). After a results day, the URL is corrected to official scores; print must follow the URL.

**Print / Save / Share** always means: generate **now** from what is on the URL (header + fleets + results only). If data changed since last print, the next print is a new PDF. An old generated file is invalid.

User then chooses: **Save PDF** (clickable), **hard copy**, or **share**.

---

## What the code does today (gap)

- **Print** = browser `window.print()` of the HTML. Not a layout-controlled PDF (no guaranteed landscape, no guaranteed fleet-on-one-page).
- **Save** (iframe sheet bar) = `html2canvas` **PNG**, not PDF, not clickable links.
- **Archive files** in `regattas.local_file_path` = imported SAS/club PDFs (source only).

There is no generator yet that builds a results PDF from the live URL with the rules above.

---

## Build order (when implementing)

1. Print stylesheet: strip URL-only live widgets; print = header + fleets only.  
2. Generate PDF **on Print/Save** from that view (not from `local_file_path`).  
3. Landscape vs portrait from race-column width.  
4. `page-break-inside: avoid` (or equivalent) so fleet header + table stay together.  
5. Save = PDF with links; Print = same PDF to printer; Share = that file.  
6. Closed events only: optional store parent/child PDFs as **our** snapshots; regenerate if the URL’s results change. Never batch-rewrite other events unasked.
