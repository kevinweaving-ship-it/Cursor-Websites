# Latest News — BETA V1

Professional “Latest News” section (News24-style editorial cards), mobile-first, South African sailing only, with SAS-ID sailor matching.

## API

**Endpoint:** `GET /api/news/latest`

**Response:** Array of items (no wrapper). Example:

```json
[
  {
    "headline": "Timothy Weaving wins SA Youth Nationals",
    "excerpt": "South African youth sailor Timothy Weaving secured first place at the SA Youth Nationals held in...",
    "url": "https://www.news24.com/...",
    "image": "https://cdn.news24.com/...",
    "source": "News24",
    "published_at": "2026-02-05T09:12:00Z",
    "matched_sailors": ["Timothy Weaving"]
  },
  {
    "headline": "Cape to Rio fleet sets sail",
    "excerpt": "The Cape to Rio Yacht Race fleet departed from Cape Town on schedule...",
    "url": "https://www.sail-world.com/...",
    "image": "https://cdn.sail-world.com/...",
    "source": "Sail-World",
    "published_at": "2026-02-04T14:00:00Z",
    "matched_sailors": []
  }
]
```

- **headline** — Clickable title (links to actual article URL).
- **excerpt** — 1–2 line summary (~140 chars).
- **url** — Actual article URL (not publisher homepage).
- **image** — Main article image (SerpAPI thumbnail, og:image, or placeholder).
- **source** — Publisher name.
- **published_at** — ISO 8601 (e.g. `2026-02-05T09:12:00Z`).
- **matched_sailors** — SAS-ID sailors mentioned in headline/excerpt (for ranking/display).

## API JSON sample (first pass)

To capture a live sample:

```bash
curl -s "http://localhost:3001/api/news/latest" | jq .
```

Or from production:

```bash
curl -s "https://sailingsa.co.za/api/news/latest" | jq .
```

If `SERPAPI_KEY` is not set, the pipeline still runs using **RSS fallback** (Google News RSS), SA filter, and sailor matching. SerpAPI is used when `SERPAPI_KEY` is set in the environment.

## Screenshots (first pass)

After deploying:

1. **Mobile**
   - Open https://sailingsa.co.za/ on a phone or DevTools device toolbar (e.g. iPhone 12).
   - Scroll to the “Latest News” section.
   - Cards: image stacked **above** headline; headline; 1–2 line excerpt; “Source · X hours ago”.
   - Screenshot the full section (header + 2–3 cards).

2. **Desktop**
   - Open https://sailingsa.co.za/ in a desktop browser (e.g. 1280px width).
   - Scroll to “Latest News”.
   - Cards: **right-aligned** thumbnail; left: headline, excerpt, “Source · X hours ago”.
   - Screenshot the section (header + 2–3 cards).

## Acceptance (pass/fail)

- [ ] Clicking headline opens the **real article** (not publisher homepage).
- [ ] Image matches article hero (or SerpAPI/og:image; no tiny RSS-only thumbnails when og:image exists).
- [ ] SA sailors appear in news when mentioned (`matched_sailors` populated; items boosted).
- [ ] Mobile view: clean, authoritative (no “Breaking”, no gimmicks).
- [ ] Cached and fast (30–60 min cache).

## Configuration

- **SerpAPI (primary):** Set `SERPAPI_KEY` in environment. Queries: South African sailing, SA Youth Sailing, Cape to Rio Yacht Race, Optimist Nationals South Africa, ILCA South Africa sailing (`gl=za`, `hl=en`).
- **RSS (secondary):** Used when SerpAPI is not configured or for dedupe/fallback.
- **SA filter:** Keeps only items with `.co.za` domain, SA-related keywords in title/excerpt, or a matched SAS-ID sailor.
- **Sailor match:** Names from `sas_id_personal`; word-boundary match in headline + excerpt; `matched_sailors` set and used for ranking.

## Versioning

- **BETA V1** — This implementation. Deploy without overwriting unrelated pages.
- **V2** — Social media sources (future).
- **V3** — Sailor-profile linked news (future).
- Database changes must be additive only.
