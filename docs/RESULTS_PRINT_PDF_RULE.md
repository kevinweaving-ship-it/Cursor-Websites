# Results print / PDF — full product rule

Every item below is required. Do not collapse live and closed into one file policy. Do not treat an old SAS PDF as our output.

---

## 1. Old SAS PDF (archive / scrape)

Has **nothing to do with our event results output**.

It is only:

- the **source document** we **parse**
- then **audit / checksum** against what we stored

It is not the URL sheet. It is not Print. It is not Save. It is not Share. It is not the parent/child PDF we give users.

---

## 2. Official **event PDF** during a live event (e.g. after results day 1)

Different from (1). During the event we **use that event’s official results PDF** and **correct our data** so **our URL matches official results**, except:

- sailor **spelling** — we fix via SAS / validation (canonical names)
- **bad class names** — we fix to real classes

Add/remove sailors, class changes, and **language / name** changes can happen in **build-up** and **while live**. The URL is allowed to change **race by race by design**.

After those corrections, **users do not print the official event PDF**. They print **our URL** (see 5).

---

## 3. What our PDF contains (the results sheet)

Generated from **what is on the URL at that second**:

- **Event header**
- **Each fleet / class header**
- **That fleet’s results**

Not weather. Not MM card. Not staff list. Not other live URL chrome.

Cape Classic live URL has those extras **on purpose**. They are **URL features**. Print / save / share **ignore them** — left out of the PDF.

---

## 4. Page rules (parent and every child, portrait and landscape)

**Width:** if the sheet is **too wide** (many races) → **landscape**, not portrait. If it **fits** → portrait is fine.

**Same-page rule (both orientations):** **class/fleet header and that class/fleet’s results stay on the same page.** Must **not** render the header on one page and the table on the next. Cannot split one fleet across two pages.

**Parent** = full event (all fleets); each fleet still obeys the same-page rule.  
**Child** = one class/fleet URL; same rules.

---

## 5. User action: Print on the URL

At **any** point (live or closed), if the user wants what is on the URL **right now**:

**Push Print → create a PDF** that obeys section 4, from **event header + fleets + results at that second**.

Then they **choose**:

1. **Save PDF** — **clickable areas like the URL** (same destinations: sailor, club, class, etc.)
2. **Print hard copy**
3. **Share** (whatever share path)

Same generated PDF. Not a PNG screenshot. Not `window.print()` of the whole live page including widgets.

---

## 6. Live events — different **file** rule

Live is **dynamic**. Do **not** keep a pre-created PDF as the product.

If results, sailors, or fleets are **updated**, that PDF is **wrong** and **must be redone**. Generation is **on Print**, from **what is currently on the URL**.

---

## 7. Closed events (passed; **Final or Provisional**; we closed)

May **pre-create** PDFs for:

- **parent** (full event), and
- **all children** (every class/fleet sheet)

Those are **our** sheets (from our URL/results), still under section 4. **Not** copies of the old SAS PDF.

If we later change stored results, those files are stale and must be remade. Do not batch-rewrite other closed events unasked.

---

## 8. What the code does today (gap — not the rule)

- Print = browser print of HTML (widgets can appear; no landscape/same-page guarantee).
- Save on the iframe bar = **PNG**, not a clickable PDF.
- `local_file_path` = old SAS/club file (section 1 only).

The generator in 5–7 is **not built yet**.
