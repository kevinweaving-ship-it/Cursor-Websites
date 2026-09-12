# Results print / PDF — product rule

**Read first:** event URL is truth while live. Children, landing search, tables, reports, and PDFs must sync to it, and again if a closed event is corrected later.

Four PDF points. Do not mix source PDFs into this.

## 1. Source PDF is irrelevant here

Old SAS / scrape / official file (`regattas.local_file_path` under `results/YYYY/…`) is only parse, audit, checksum.

It is **not** used to generate, print, save, download, or share **our** event PDF.

---

## 2. Passed / closed events — generate, store, fetch

Event is **closed** (passed: `end_date` / `start_date` before today in Africa/Johannesburg).

- Generate **our** PDFs (event header + fleet headers + fleet results). Landscape if the table is too wide for portrait. Each fleet stays on one page.
- **Store** under `/var/www/sailingsa/data/regatta-pdfs/{regatta_id}/results.pdf` and `class-{slug}.pdf`.
- Print / save / download / share **fetches** that file: `/regatta/{id}/results.pdf` (parent) or `/regatta/{id}/class-{slug}/results.pdf` (child). `?download=1` for save/download.

Do not rebuild from a source SAS PDF. If we later amend that event, regenerate and replace **that** event’s stored PDFs.

---

## 3. Live events — no trusted stored product PDF

Print / save / download / share **generates now** from the event URL (header + fleets only). Weather, MM/reels, staff/crew lists stay off the PDF.

---

## 4. When the event closes → it becomes (2)

---

## UI wiring

- Standalone `/regatta/{id}` Print/Share uses the server PDF chooser (`ssaRegattaPrint`).
- Landing / sailor **iframe bar** Save / Share / Print must use the same `/results.pdf` URLs — not `html2canvas` PNG and not `iframe.print()` of the HTML sheet.
- Podium has no results.pdf; it may keep the old capture.

## Batch closed events

`python3 sailingsa/deploy/generate_closed_event_product_pdfs.py` on the live server (uses existing `_rebuild_regatta_stored_pdfs`). Skip live/fluid events.
