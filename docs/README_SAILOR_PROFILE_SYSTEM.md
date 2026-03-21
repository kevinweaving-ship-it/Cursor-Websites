# Sailor Profile System — Developer Documentation

## 1. Purpose

The Sailor Profile system provides read-only, public-facing sailor profiles that merge:
- **Regatta results** from the SA Sailing database
- **Public web mentions** (news articles, videos, official media)
- **Factual highlights** extracted from competition results
- **Performance statistics** (regattas sailed, races completed, sailing history)

Profiles are designed to:
- Load instantly from cached database data
- Never block on external API calls
- Respect privacy rules (especially for sailors under 18)
- Display sponsor-safe content only
- Provide SEO-friendly public pages

---

## 2. Core Design Rules (NON-NEGOTIABLE)

These rules are **absolute**. Any code changes must respect them.

### Rendering Rules
- ✅ **Profile must render immediately from DB** — No waiting for Google/external fetches
- ✅ **All background fetches are async + rate-limited** — Never synchronous
- ✅ **One sailor profile = one mobile screen** (Profile tab only) — No scrolling required
- ✅ **Broken URLs must never appear in UI** — All URLs validated before storage

### Data Rules
- ✅ **Regatta results are always allowed regardless of age** — Public competition data is never restricted
- ✅ **Social media is restricted for sailors under 18** — Facebook/Instagram/TikTok blocked for minors
- ✅ **Media refresh max once per 24h** — Rate limiting enforced via `media_last_fetched_at`
- ✅ **Never delete rows — mark invalid instead** — Use `is_valid = false` for broken links

### Safety Rules
- ✅ **Junior protection is automatic** — Age-based filtering applied at API level
- ✅ **Sponsor-safe domains only** — Domain allowlist enforced (`filter_public_media`)
- ✅ **Thumbnails cached locally** — No hotlinking, no external dependencies
- ✅ **URL validation before insert** — `validate_url()` must pass before storage

### UI Rules
- ✅ **Profile tab = header + summary + highlights + stats** — No career breakdown, no class breakdown
- ✅ **Media tab = Google-style cards** — Thumbnails, headlines, snippets, meta lines
- ✅ **Empty states are informative** — Explain why content is limited (especially for juniors)

---

## 3. Data Flow (High Level)

### Search → Profile Flow
1. **User searches** → Frontend calls `/api/search` or `/api/member/{sa_id}/results`
2. **Profile data fetched** → Regatta history, classes, club, province from DB
3. **Media data fetched** → `/api/member/{sa_id}/public-mentions` returns cached items
4. **Highlights extracted** → Client-side from `regattaHistoryRows` (or backend API)
5. **Profile rendered** → All data displayed immediately

### Background Refresh Flow
1. **Media fetch triggered** → If `media_last_fetched_at < NOW() - 24h` OR `media_fetch_status = 'failed'`
2. **Background job runs** → `fetch_media_for_sailor()` executes async
3. **Google searches performed** → Rate-limited, multi-phase search
4. **URLs validated** → `validate_url()` checks each URL before insert
5. **Thumbnails extracted** → YouTube/Vimeo/og:image cached locally
6. **Database updated** → New items inserted, existing items updated
7. **Status updated** → `media_fetch_status = 'idle'`, `media_last_fetched_at = NOW()`

### Media Maintenance Flow
1. **Maintenance job runs** → Daily/weekly via `jobs/sailor_media_maintenance.py`
2. **URLs revalidated** → Items where `last_validated_at < NOW() - 30 days`
3. **Broken links marked** → `is_valid = false` if URL now returns 404/410/5xx
4. **Thumbnail health checked** → Missing/corrupt files cleared (`thumb_local_path = NULL`)
5. **UI automatically updates** → Broken items filtered by `WHERE is_valid = true`

### Key Principle
**DB first, refresh async, UI never waits.**

---

## 4. Media Rules (Age-Aware)

| Content Type | Under 18 | Over 18 | Notes |
|--------------|----------|---------|-------|
| Official regatta results | ✅ | ✅ | Always public, regardless of age |
| Rankings / medals | ✅ | ✅ | Competition data is public record |
| News articles | ✅ | ✅ | From allowlisted domains only |
| Federation media | ✅ | ✅ | sailingsa.org.za, sa-sailing.co.za |
| YouTube videos | ✅ | ✅ | Official sailing content allowed |
| Social media (FB/IG/TikTok) | ❌ | ✅ | Personal profiles blocked for minors |
| Personal photos | ❌ | ✅ | Race photos OK, personal photos blocked |
| Opinion articles | ⚠️ | ✅ | Depends on domain allowlist |

### Domain Allowlist (Always Allowed)
- `sailingsa.org.za`
- `sa-sailing.co.za`
- `sailingsa.co.za`
- `youtube.com` / `youtu.be`
- `vimeo.com`
- Official club domains (as configured)

### Soft-Block Domains (Blocked for Under 18)
- `facebook.com`
- `instagram.com`
- `twitter.com` / `x.com`
- `tiktok.com`

**Implementation**: `filter_public_media()` in `api.py` (lines 6380-6442)

---

## 5. Highlights System (STEP 11–14)

### What Are Highlights?
Factual achievements extracted from regatta results. **Not AI-generated, not media-based.**

### Generation Rules
- **Source**: Regatta results database (`results` + `regattas` + `regatta_blocks`)
- **Event types**: Nationals, Provincial Championships, Youth Nationals
- **Rank threshold**: Only positions ≤ 10
- **Max items**: 3 highlights per profile
- **Priority order**: Nationals > Provincials > Youth (then date DESC)

### Format
```
1st place – SA Youth Nationals (Optimist A, 2025)
Top 5 – Western Cape Championships (ILCA 6, 2024)
2nd place – Optimist Provincial Championships (Optimist A, 2023)
```

### Rank Display (Step 14)
- 🥇 **Rank 1** → Gold medal emoji
- 🥈 **Rank 2–3** → Silver medal emoji
- 🥉 **Rank 4–10** → Bronze medal emoji

### Medal Summary
Below compact stats, shows medal counts from **Nationals & Provincials only**:
```
🥇 1  🥈 0  🥉 2   Nationals & Provincials
```

**Implementation**: 
- Backend: `extract_sailor_highlights()` in `api.py` (lines 6444-6558)
- Frontend: Client-side extraction from `regattaHistoryRows` in `sailingsa/frontend/index.html` (lines 1677-1745)

---

## 6. Profile Tab Layout Contract

### Exact Order (Mobile-First)
1. **Profile Header**
   - Avatar (cached local image or initials fallback)
   - Name + "South African Sailor" subtitle
   - Meta rows: Age, Class, Club, Province, SAS ID, Last active

2. **"What it says about you" Summary Card** (if exists)
   - Google Profile summary (pinned media item)
   - Max 2 lines of text
   - "View sources" link → scrolls to Media tab

3. **Highlights Section** (if exists)
   - Max 3 bullet points
   - Emoji prefixes based on rank
   - Format: "Position – Event Name (Class, Year)"

4. **Compact Stats Line**
   - Format: "X regattas • Y races • Sailing since YYYY"

5. **Medal Summary** (if medals exist)
   - Format: "🥇 X  🥈 Y  🥉 Z   Nationals & Provincials"

### What Must NEVER Appear in Profile Tab
- ❌ Career Summary (detailed breakdown)
- ❌ Class Breakdown (statistics by class)
- ❌ Regatta History Table (moved to "Regattas Sailed" tab)
- ❌ Long scroll sections

**Implementation**: `sailingsa/frontend/index.html` line 1905 — Profile tab assembly

---

## 7. Media Tab Rules

### Fetch Rules (generic for all sailor media tabs)

When fetching or adding a URL to a sailor’s media tab, use these five data points (example: `https://optimist.org.za/?p=15742`):

1. **Heading** — Section or page title. Prefer the **section heading** (e.g. first `<h2>`) when the page title is long or generic (e.g. “Optimist Class Chairpersons report 2024/25 – Alistair Keytel” → use “Our Sailors Take on the World” when that section pertains to the sailor).
2. **Second heading / subheading** — Optional second line (e.g. article subheading); can be merged into headline or omitted.
3. **Content / sentence mentioning sailor** — The **snippet** must be (or include) the sentence or paragraph that actually mentions the sailor (e.g. for Tim: “We've had a number of our sailors traveling… Tim Weaving, Nathan McCombe, and Josh Keytel—attended the Prince Moulay Hassan Trophy…”). Use `og:description` when it contains this; otherwise allow manual snippet or extract the paragraph that contains the sailor’s name.
4. **Date / time** — Stored as the **date/time when the media was added** (server `NOW()`). Do **not** use the post date from the URL or page content.
5. **Thumbnail** — `og:image` from the page, or user-provided `thumb_url` when adding media. Store and display per Thumbnail Sources below.

These rules apply to add-media API, batch fetch jobs, and any code that populates `sailor_public_mentions`.

### Card Structure (Google-Style)
Each media item renders as:
- **Thumbnail** (left): Local cached image OR icon placeholder
- **Headline** (clickable): Article/post title
- **Snippet** (2–3 lines max): Summary text (ideally the sentence/paragraph mentioning the sailor)
- **Meta line**: "Source • Date • Type"

### Display Rules
- ✅ **Only validated URLs** → `WHERE is_valid = true` enforced
- ✅ **Thumbnails cached locally** → `thumb_local_path` preferred over `thumb_url`
- ✅ **Pinned items first** → Google Profile summary always at top
- ✅ **Sorted by date DESC** → Most recent first

### Empty State Rules
- **Juniors (< 18)**: "Media results are limited for junior sailors. Verified race results and highlights are shown instead."
- **Adults**: "No public mentions yet."

### Thumbnail Sources
1. **YouTube**: `https://img.youtube.com/vi/{id}/hqdefault.jpg`
2. **Vimeo**: oEmbed API
3. **Articles**: `og:image` meta tag
4. **Fallback**: Icon emoji (📄 article, ▶️ video, 📷 photo)

**Implementation**: Media card rendering in `sailingsa/frontend/index.html` (lines 1838-1793)

---

## 8. Background Jobs

### Media Refresh Job
**File**: `jobs/sailor_media_fetch.py`
**Function**: `fetch_media_for_sailor()`

**Responsibilities**:
- Google AI baseline search
- Class-specific searches
- Validation searches
- URL validation before insert
- Thumbnail extraction
- Avatar generation (from thumbnails)

**Rate Limiting**:
- Max once per 24h per sailor (`media_last_fetched_at`)
- Status tracking: `media_fetch_status` ('idle' | 'running' | 'failed')

**Failure Behavior**:
- Sets `media_fetch_status = 'failed'`
- Stores error in `media_fetch_error`
- Retries allowed after 24h

### Thumbnail Extraction
**Function**: `_extract_and_cache_thumbnail()`

**Process**:
1. Extract thumbnail URL (YouTube/Vimeo/og:image)
2. Validate URL (`_validate_image_url()`)
3. Download image
4. Resize to ~320px wide
5. Save to `media/thumbs/{sa_id}/{hash}.jpg`
6. Update `thumb_local_path` in DB

**Retry Rules**:
- Failed thumbnails marked with `thumb_fetch_failed_at`
- No retry for 24h

### Avatar Generation
**Function**: `_generate_avatar_from_thumbnail()`

**Process**:
1. Select best thumbnail (pinned > any)
2. Download and crop to square (200x200px)
3. Save to `media/avatars/{sa_id}.jpg`
4. Refresh monthly (if file older than 30 days)

### Media Maintenance Job
**File**: `jobs/sailor_media_maintenance.py`

**Responsibilities**:
- Revalidate URLs older than 30 days
- Mark broken links as `is_valid = false`
- Check thumbnail file health
- Clear missing/corrupt thumbnails

**Schedule**: Daily or weekly (via cron)

---

## 9. Public SEO Pages

### URL Structure
```
/sailor/{slug}
```
Example: `/sailor/sean-kavanagh`

**Slug Generation**: Deterministic from name (lowercase, hyphenated)

### Data Exposed (Public Only)
- Name
- Club
- Province
- Age (optional, configurable)
- Classes sailed
- Public media (filtered by `filter_public_media()`)
- Highlights (from regatta results)
- Summary (Google Profile snippet, if available)

### Data Never Exposed
- Internal IDs
- Admin flags
- Private fields
- Raw database keys
- Search endpoints

### SEO Metadata
- `<title>`: "{Name} | South African Sailor"
- `<meta name="description">`: Summary text
- **Open Graph tags**: `og:title`, `og:description`, `og:image` (avatar), `og:type` (profile)
- **JSON-LD Person schema**: Name, nationality, sport, affiliation

### Safety Filters Applied
- `filter_public_media()` — Domain allowlist + age-based restrictions
- `is_valid = true` — Only working URLs
- Public data only — No admin/internal fields

**Implementation**: 
- Backend: `api_public_sailor()` in `api.py` (lines 6560-6669)
- Frontend: `sailingsa/frontend/public/sailor.html`

---

## 10. Troubleshooting / Fault Finding

### "Media Tab Empty" Checklist
1. ✅ Check `media_last_fetched_at` — Is it NULL or > 24h old?
2. ✅ Check `media_fetch_status` — Is it 'failed'?
3. ✅ Check `is_valid` — Are items marked invalid?
4. ✅ Check age — Is sailor under 18? (Social media blocked)
5. ✅ Check domain allowlist — Are URLs from blocked domains?
6. ✅ Check `filter_public_media()` — Are items filtered out?
7. ✅ Check database — Run `SELECT COUNT(*) FROM sailor_public_mentions WHERE sa_id = '{sa_id}' AND is_valid = true`

### "Highlights Missing" Checklist
1. ✅ Check regatta results — Does sailor have results in DB?
2. ✅ Check event types — Are events Nationals/Provincials/Youth?
3. ✅ Check rank — Are positions ≤ 10?
4. ✅ Check client-side extraction — Is `regattaHistoryRows` populated?
5. ✅ Check backend API — Does `/api/member/{sa_id}/highlights` return data?

### "Profile Slow" Checklist
1. ✅ Check for blocking fetches — Are any API calls synchronous?
2. ✅ Check thumbnail loading — Are images loading synchronously?
3. ✅ Check database queries — Are queries optimized?
4. ✅ Check network — Are external APIs timing out?
5. ✅ Check browser console — Are there JavaScript errors?

### "Cursor Crash Safety Tips"
1. ✅ **Never scan entire codebase** — Use targeted searches
2. ✅ **Read existing code first** — Don't guess implementation
3. ✅ **Check syntax before saving** — Run `python3 -m py_compile api.py`
4. ✅ **Verify file paths** — Use absolute paths when possible
5. ✅ **Test incrementally** — Small changes, verify, then continue
6. ✅ **Read this README** — Rules are documented here

### Common Issues

**Issue**: Highlights show without emojis
- **Cause**: Using API highlights (no rank info) instead of client-side extraction
- **Fix**: Use client-side extraction from `regattaHistoryRows` (includes rank)

**Issue**: Media tab shows broken links
- **Cause**: `is_valid = false` items not filtered
- **Fix**: Ensure queries include `WHERE is_valid = true`

**Issue**: Profile tab too long (scrolls)
- **Cause**: Career Summary or Class Breakdown included
- **Fix**: Remove from Profile tab assembly (line 1905)

**Issue**: Juniors see social media
- **Cause**: `filter_public_media()` not applied
- **Fix**: Ensure age passed to filter function

---

## 11. Do NOT Do This (Anti-Patterns)

### ❌ Do NOT fetch Google synchronously
- **Why**: Blocks UI, violates "render immediately" rule
- **Correct**: Background fetch only, return cached data immediately

### ❌ Do NOT show social media for juniors
- **Why**: Privacy protection, legal compliance
- **Correct**: `filter_public_media(mentions, age=age)` blocks social domains for < 18

### ❌ Do NOT re-introduce blocking loaders
- **Why**: Violates "render immediately" rule
- **Correct**: Show cached data, refresh in background

### ❌ Do NOT merge Profile + Regattas views
- **Why**: Profile tab must fit one mobile screen
- **Correct**: Keep separate tabs, Profile = summary only

### ❌ Do NOT delete rows — mark invalid instead
- **Why**: Preserves history, allows debugging
- **Correct**: `UPDATE SET is_valid = false` instead of `DELETE`

### ❌ Do NOT skip URL validation
- **Why**: Broken links degrade UX
- **Correct**: `validate_url()` must pass before insert

### ❌ Do NOT hotlink thumbnails permanently
- **Why**: External dependencies break, slow loading
- **Correct**: Cache locally, use `thumb_local_path`

### ❌ Do NOT add career/class breakdown to Profile tab
- **Why**: Violates "one mobile screen" rule
- **Correct**: Keep in "Regattas Sailed" tab only

### ❌ Do NOT restrict regatta results by age
- **Why**: Competition data is public record
- **Correct**: Results always visible, regardless of age

### ❌ Do NOT generate highlights from media
- **Why**: Highlights must be factual competition data
- **Correct**: Extract from regatta results DB only

---

## Summary

This system prioritizes:
1. **Speed** — Instant rendering from cached DB
2. **Safety** — Age-aware filtering, URL validation
3. **Accuracy** — Factual highlights, validated media
4. **Maintainability** — Background jobs, clear rules

**When in doubt, refer to this README. These rules are non-negotiable.**

---

**Last Updated**: 2026-01-30  
**Version**: 1.0 (Steps 1-14 Complete)
