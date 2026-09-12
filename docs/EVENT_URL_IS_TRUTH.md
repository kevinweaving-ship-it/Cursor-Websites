# Event URL is truth — sync rule

This is the rule that was missed earlier (live treated as a frozen sheet / local JS / stored file).

## Truth

While an event is **live**, the **event URL** (parent) is **truth**.

Every other surface that shows that event **must look at the event URL / the same live data** — not a copy, not last night’s HTML, not `result_id` order, not a stored product PDF.

That stays true **until the event is closed**.

**Months later**, a correction can still land. That correction **is truth**. Whatever it affects must **sync / update automatically**.

---

## What “live” means

Live is **dynamic / fluid / changing all the time** — even if the only change is **race scores**.

Also (build-up and during live):

- fleets change → **child URLs** change  
- entry **counts** change  
- **sailors** add / remove / move  
- **sail numbers** and anything else on the sheet can change  
- class names / language / names can change  

Cape Classic is one live event. The same rule applies to **all URLs that use a live event URL as source** (before closed).

---

## What must stay in sync (always, auto)

Any change on the **event URL** must flow to:

- **child URLs** (each class / fleet)  
- **landing page search** for that live event (fleets, entries, sailors, children)  
- **tables / reports**  
- **print / save / share PDF** (live: generate **now** from event URL; not a stale file)

If those disagree with the event URL, they are wrong.

---

## PDF (does not override truth)

1. Source SAS PDF — irrelevant to our event PDF. Parse / checksum only.  
2. **Closed** — generate our PDFs on print rules, **store**, fetch on print/save/download/share.  
3. **Live** — no stored product PDF. Generate from event URL **now** (header + fleets only; weather / MM / staff out).  
4. **Close** → event **falls into (2)**.  

A **later correction** (even months after close) updates truth. Stored PDFs and every URL/table/report that used the old data must **update auto** for that event.

---

## What went wrong earlier today

The Open sheet was treated as a one-off rank/JS/`result_id` problem. The event URL was already truth; the browser rewrite and other surfaces did not stay synced to it. Live data is not allowed to fork.
