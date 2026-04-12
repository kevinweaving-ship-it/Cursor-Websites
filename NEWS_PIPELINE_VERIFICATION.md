# News Pipeline v1 — Verification Summary

**Tag:** `news_pipeline_v1_verified`  
**Date:** 2026-02-04 (Phase 3C lock)

---

## STEP 1 — Verify (run once)

1. Call **GET /api/news/latest** (e.g. `curl -s http://192.168.0.130:8081/api/news/latest | jq length`).
2. Confirm **result count > 0**.
3. Confirm each item has: **title**, **excerpt**, **url** (NOT news.google.com), **published_at**; **image** may be `""` (allowed).
4. In backend logs confirm:
   - One summary per refresh: `[news] refresh: N items, reasons=[...]` with N > 0.

---

## STEP 2 — Log summary (fill after verify)

| Field | Value |
|-------|--------|
| **Total items returned** | _(e.g. 8)_ |
| **Acceptance reasons seen** | _(e.g. keyword, allowlist+keyword)_ |
| **Example headline (keyword)** | _(if any)_ |
| **Example headline (co_za)** | _(if any)_ |
| **Example headline (sailor)** | _(if any)_ |
| **Example headline (allowlist+keyword)** | _(if any)_ |

---

## Baseline (frozen)

- **Endpoint:** GET /api/news/latest  
- **Response:** `[{ title, excerpt, url, image, source, published_at }]`  
- **Max items:** 20  
- **Cache:** 30 min, background refresh  
- **SA filter:** sailor match → .co.za → SA keywords → domain allowlist + keyword  
- **No** news.google.com in response; **no** filter changes after this tag.

Phase 4 (landing page, sailor highlighting, editorial, social) comes after this baseline.
