# Results print / PDF — product rule

**This is why SailingSA exists.** The thing the user prints, saves, downloads, or shares is **our** curated results PDF — one standard format, every event, every time.

SAS source is random (PDF / PNG / XLS / photo / whatever they uploaded). We ingest that only to get the data right. The **output** is our sheet: event header + fleet headers + fleet results, print rules, same layout for every event. Not their file, not a screenshot of their file, not a PNG of our HTML.

**Read first:** event URL is truth while live. Children, landing search, tables, reports, and PDFs must sync to it, and again if a closed event is corrected later.

Four PDF points. Do not mix source files into the product.

## 1. Source PDF is irrelevant here

Old SAS / scrape / official file (`regattas.local_file_path` under `results/YYYY/…`) is only parse, audit, checksum.

It is **not** used to generate, print, save, download, or share **our** event PDF.

---

## 2. Passed / closed events — generate, store, fetch

Event is **closed** (passed: `end_date` / `start_date` before today in Africa/Johannesburg).

- Generate **our** PDFs (event header + fleet headers + fleet results). Landscape if the table is too wide for portrait. Each fleet stays on one page.
- **Parent URL** (`/regatta/{id}`): one PDF with **every** fleet. Print / save / share that file — never the first fleet only.
- **Child URL** (`/regatta/{id}-{fleet}` or `/regatta/{id}/class-{slug}`): PDF of **that fleet only**.
- **Store** under `/var/www/sailingsa/data/regatta-pdfs/{regatta_id}/results.pdf` (all fleets), `class-{slug}.pdf`, and `{child-slug}/results.pdf`.
- Print / save / download / share **fetches** that file: `/regatta/{id}/results.pdf` (parent, all fleets) or the child path `/results.pdf`. `?download=1` for save/download.

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

`python3 sailingsa/deploy/generate_closed_event_product_pdfs.py` on the live server (uses existing `_rebuild_regatta_stored_pdfs`). Regenerates every closed parent + child so `/regatta/{id}/results.pdf` is all fleets and a child URL PDF is that fleet only. Skip live/fluid events.
