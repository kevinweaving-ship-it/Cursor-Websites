# Latest News — Bugfix + Quality Gate (STOP deliverable)

## Fixes applied (no layout/header/features changed)

1. **FIX 1 — Image = article hero (mandatory)**  
   - Resolution order: (1) **og:image from article HTML** (PRIMARY, timeout ≤3s), (2) SerpAPI image only if og missing, (3) RSS image only if both missing, (4) null.  
   - Reject og:image if: SVG, or URL contains `/logo`, `/icon`, `/brand`, `/favicon`.  
   - Do NOT show any image if the only available image is a logo → API returns `"image": null`.

2. **FIX 2 — Sanitise text**  
   - Decode HTML entities (`&nbsp;`, `&amp;`, etc.).  
   - Strip HTML tags, collapse whitespace.  
   - Remove duplicated headline from excerpt.  
   - Excerpt: max 140 chars, must not repeat headline, end at word boundary.

3. **FIX 3 — Freshness filter**  
   - Drop article if `published_at < now() - 180 days`.  
   - Exception: if `matched_sailors.length > 0`, allow up to **365 days**.  
   - Everything else → DROP.

4. **FIX 4 — South Africa filter (tightened)**  
   - Keep item ONLY if: source domain ends with `.co.za`, OR text contains South Africa/SA, Cape Town/Durban/Gqeberha/provinces, recognised SA yacht clubs/regattas, OR mentions a SAS-ID sailor.  
   - Do not rely on Google News category alone.

5. **FIX 5 — Sort order**  
   - Sort strictly by: `matched_sailors.length > 0` (desc), then `published_at` (newest first). No other weighting.

---

## Before / after (ONE item)

**Example: one News24 / Sail-World article**

| | Before | After |
|---|--------|--------|
| **URL** | (unchanged) article URL | (unchanged) article URL |
| **Image URL** | SerpAPI thumbnail or RSS media (sometimes logo/SVG) | **og:image** from article HTML, or null if only logo/SVG/icon |
| **Excerpt** | Raw RSS/SerpAPI (could contain `&nbsp;`, tags, or headline repeat) | Sanitised, no headline repeat, max 140 chars, word boundary |
| **Old articles** | 2018/2023 could appear | Dropped if &gt; 180 days (or &gt; 365 if sailor matched) |

**Concrete before/after for ONE item (to verify with real URLs):**

- **News24 article** → correct hero image (og:image), no logo in slot.  
- **Sail-World article** → yacht/image from og:image, not logo.  
- **Youth sailor article** → sailor photo if og:image exists and is not logo.

---

## API JSON (3 items)

After fixes, `GET /api/news/latest` returns an **array** of items. Example shape for **3 items**:

```json
[
  {
    "headline": "Timothy Weaving wins SA Youth Nationals",
    "excerpt": "South African youth sailor Timothy Weaving secured first place at the SA Youth Nationals held in...",
    "url": "https://www.news24.com/...",
    "image": "https://cdn.news24.com/hero-image.jpg",
    "source": "News24",
    "published_at": "2026-02-05T09:12:00Z",
    "matched_sailors": ["Timothy Weaving"]
  },
  {
    "headline": "Cape to Rio fleet sets sail",
    "excerpt": "The Cape to Rio Yacht Race fleet departed from Cape Town on schedule...",
    "url": "https://www.sail-world.com/...",
    "image": "https://cdn.sail-world.com/yacht-image.jpg",
    "source": "Sail-World",
    "published_at": "2026-02-04T14:00:00Z",
    "matched_sailors": []
  },
  {
    "headline": "ILCA nationals wrap in Durban",
    "excerpt": "The ILCA South Africa nationals concluded at Royal Natal Yacht Club...",
    "url": "https://example.co.za/...",
    "image": null,
    "source": "Example.co.za",
    "published_at": "2026-02-03T10:00:00Z",
    "matched_sailors": []
  }
]
```

- If the only available image for an item is a logo → `"image": null`.  
- No `&nbsp;` or raw HTML in `headline` / `excerpt` / `source`.  
- No articles older than cutoff (180 days, or 365 if sailor matched).

---

## ONE mobile screenshot (instruction)

1. Open the site on a **mobile** device or DevTools device toolbar (e.g. iPhone 12, 390×844).  
2. Scroll to the **Latest News** section.  
3. Confirm:  
   - Headline links to the **actual article URL**.  
   - Image is **article hero** (or placeholder if null), **not** logo/SVG.  
   - No `&nbsp;` or broken HTML in text.  
   - No articles older than cutoff.  
4. Take **one** screenshot of the Latest News section (header + 2–3 cards) and keep for acceptance.

---

## Acceptance (non‑negotiable)

- [ ] News24 article → correct hero image.  
- [ ] Sail-World article → yacht image, not logo.  
- [ ] Youth sailor article → sailor photo if og:image exists.  
- [ ] No `&nbsp;` in UI.  
- [ ] No articles older than cutoff.  
- [ ] No logos in image slots (logo → null).

If any fail → STOP and fix before committing.
