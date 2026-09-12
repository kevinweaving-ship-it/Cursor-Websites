# Results print / PDF — product rule

**Read first:** `docs/EVENT_URL_IS_TRUTH.md`. Event URL is truth. Children, landing search, tables, reports, and PDFs must sync to it while live, and again if a closed event is corrected later.

Four PDF points. Do not mix source PDFs into this.

## 1. Source PDF is irrelevant here

Old SAS / scrape / official file is only parse, audit, checksum.

It is **not** used to generate, print, save, download, or share **our** event PDF.

---

## 2. Passed / closed events — generate, store, fetch

Event is **closed** (passed, finalised, Final or Provisional we closed).

- Generate **our** PDFs using the print rules (orientation, fleet header + that fleet’s results on the **same page**, parent + all children).
- **Store** those files.
- Print / save / download / share on any **past** event **fetches** that stored PDF.

Data is frozen, so the file can be reused. Do not rebuild from a source PDF. Do not mass-rewrite other closed events unasked.

If we later amend a closed event’s results, regenerate and replace **that** event’s stored PDFs, then fetch again.

---

## 3. Live events (e.g. Cape Classic) — no stored product PDF

Live is **dynamic / fluid**. Sailors, classes, fleets, scores change (add/remove, amendments, race by race).

PDF **changes when the data changes**. There is no trusted stored file.

Print / save / download / share **generates now** from what is on the **URL** at that second (event header + fleet headers + fleet results only).

URL-only live chrome is **out** of the PDF: weather, MM card, staff list, etc.

User then: save (clickable like the URL), hard copy, or share.

---

## 4. When the event closes → it becomes (2)

Once **passed / finalised / closed**, it **leaves (3) and falls into (2)**: generate under the print rules, **store**, thereafter **fetch** on print / save / download / share.

---

## Print rules (used in 2 and 3)

- Too many races (too wide) → **landscape**; if it fits → **portrait**.
- **Class/fleet header and that class/fleet’s results stay on one page** — never split across two pages.
- Parent = full event; children = each class/fleet. Same rules.

## Today (gap)

Print is browser HTML; Save on the sheet bar is a PNG. Stored `local_file_path` is the **source** file (1), not (2). Live generate (3) and close→store (4) are **not built**.
