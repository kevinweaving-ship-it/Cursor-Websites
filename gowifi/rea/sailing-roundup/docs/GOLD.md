# Gold — locked Weekend Roundup product

**This is the contract.** Every Monday URL must come out of the unattended job looking like [2026-09-28](https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/) without anyone pasting a photo, rewriting a headline, or patching the homepage.

Gold is **not** the landing Latest News feed. Gold is the Monday magazine at:

`https://sailingsa.co.za/sailing-roundup/issues/YYYY-MM-DD/`

Locked reference: **2026-09-28** (racing 26–27 September 2026). `restyle_to_gold.py` refuses to restyle that date. Do not rebuild it to “fix” later weeks.

Related: [CONTENT_CONTRACT.md](../CONTENT_CONTRACT.md) (JSON shape) · [UNATTENDED_MONDAY_PUBLISH.md](UNATTENDED_MONDAY_PUBLISH.md) (timer + rsync) · [VERIFIED_EVIDENCE_FIX.md](VERIFIED_EVIDENCE_FIX.md) (checksum) · [REAL_AGGREGATORS.md](REAL_AGGREGATORS.md) (cluster + recap model) · [WEEKEND_ROUNDUP.md](../../../docs/WEEKEND_ROUNDUP.md) (calendar + Google).

---

## 1. What a Gold URL is

Cream paper, gold accent `#8b6c43`, navy `#001f3f`, SailingSA header, H1 **The Weekend Roundup**. CSS: `app/gold_default.css`. Render: `app/roundup.py`.

| Slot | Rule |
| --- | --- |
| Edition lead | Feature article. H1 “The Weekend Roundup”. Deck is Sat–Sun of the covered week (gold: `26–27 September 2026`). Lede counts fleets and names venues. Calendar-only events (no results) are listed as unavailable — scored same-weekend events are never hidden that way. |
| Weekend hero | One real photograph on the lead (and in `feed.json` / NewsArticle `image`). Admin-seed first, then a jpg from a verified story. **Never** Event / Club / Class Logo, **never** a PNG artwork file, **never** a photographed results sheet, **never** `*-source.jpg` collage as the card image. |
| Event story | Kicker (`CLASS  ·  CLUB`) → unique headline → **every SailingSA event URL that article refers to, listed and clickable immediately under the H2** → deck (`Venue · N nett · E entries`) → photos → cited magazine copy → heading exactly `1st, 2nd, 3rd` (or `{Class} · 1st, 2nd, 3rd` when one event has several classes) → official 3-row podium. |
| Event URL | Required. Directly under the headline, before the deck. Gold 505 is the shape: headline `Peter Funke and Thomas Funke take 505 Nationals after a points tie at Aeolians` then a clickable `https://sailingsa.co.za/regatta/2026-09-24-ayc-505-nationals`. Same for Dabchick, Dart 18, and 420. If copy, citations, or results blocks refer to more than one `/regatta/{slug}`, list each URL. Calendar-only names with no slug stay unlinked. Markup: `<p class="event-url"><a href="…">…</a></p>`. |
| Podium | `LEADERBOARD_LIMIT = 3`. Columns: Pos, Helm, Crew, Club, Sail No, Nett. Team racing: Pos, Team, Club [, Nett]. **Not** the full fleet. **Not** sailor cells on a TSL board. |
| Copy | Magazine paragraphs, not a results dump. Every paragraph ends with `[n]`. `[1]` is always the SailingSA results card. |
| Photos | Prizegiving and on-water from **this event’s** cluster. Video stills are valid (gold Dabchick still has the play-button overlay). More than one photo is allowed. No Wikimedia. No invented photo. No host/school/class logo as a photograph. |
| Age titles | U15 / U17 / U19 / U21 only when verified media names official-result sailors in that age group. Gold 420: NovaNews names Timothy Weaving and Hayden Miller as U17. |
| Empty week | **No URL.** Do not publish a stub. |

If a later issue looks like a box of event data, it is not Gold. Restyling chrome (`restyle_to_gold.py`) without a verified cluster and photographs is not Gold.

---

## 2. How Gold 2026-09-28 was created (step by step)

This is the path a new Monday must follow automatically. The September issue is the worked example.

### Step 1 — Assign the week

Code: `app/events_weekend.py`.

`GET https://sailingsa.co.za/api/events` (public projection of `public.events`).

An event belongs to **exactly one** Monday: the first Monday **strictly after** its `end_date`.

| Finish | Issue Monday |
| --- | --- |
| Sun 27 Sep 2026 | **28 Sep** |
| Wed 15 Apr | Mon 20 Apr (week 13–19 Apr) |
| Multi-week ending Tue 15 Dec | Mon 21 Dec |
| Empty week | no issue |

Midweek, long-weekend, and multi-week events are included once — the Monday after the week they ended. Meetings / courses / AGMs / appointments longer than 21 days are dropped (`skip_event`).

Gold week window: Mon 21 Sep – Sun 27 Sep. Events that started Thursday 24 Sep still count because they finished inside that week.

### Step 2 — Gold calendar (what the events table listed)

| Event | Dates | `regatta_id` | Results? |
| --- | --- | --- | --- |
| 505 Nationals | 24–27 Sep | `2026-09-24-ayc-505-nationals` | 7 boats, 12 races |
| Dabchick Gauteng Regionals | 24–26 Sep | `2026-09-24-ayc-dabchick-gauteng-regionals` | 17 boats, 12 races |
| Dart 18 Nationals + KZN provincials | 24–27 Sep | `2026-09-24-hmyc-dart-18-nationals` | 38 boats, 7 races (provisional) |
| 420 Nationals | 26–27 Sep | `2026-09-25-tsc-420-nationals` | 16 boats, 8 races |
| DF95 WC Regional Champs | 25–27 Sep | none | calendar only |
| J22 Nationals | 24–27 Sep | none | calendar only |
| FBYC Spring Regatta | 24–27 Sep | none | calendar only |

Four scored reports + three calendar mentions in the feature. That is why the gold lede is “Four fleets raced at Aeolians, Henley Midmar and Theewater” and the second paragraph lists the three without results.

### Step 3 — Official results are source [1]

`GET https://sailingsa.co.za/api/regatta/{slug}` → `facts_from_rows()`.

The official card is **always** citation `[1]`. Google hitting the same `/regatta/{slug}` page is corroboration, not discovery of our own data.

Facts locked from that JSON only:

- event title, host club, start/end, result status
- fleet size, races sailed, race scores
- winner / second / third **only if** official `rank` or nett exists (`official_order`)
- helm, crew, club, sail number, nett
- team identity = `boat_name` (MAC, MATIES, Eden District, RCYC Sailing Academy) when the class is TSL / team sailing

**Never invent a winner.** TSL 19 Oct published 8 named teams with `rank=null` and `nett=null`. Gold copy is “8 teams contested… Official overall scores were not in the published results table.” Checksum reason `sailor_name_on_team_event` rejects sailor cells from that overall table.

Multi-class: one official 1st/2nd/3rd board **per class**.

### Step 4 — Build the media pack (this event only)

`publish_weekend.media_pack` then `event_rewrite.cluster_coverage`.

For each scored slug, collect candidates **about this event**, then verify. Order:

1. Official results card (always kept).
2. Cached `{slug}-social.json` if a previous harvest exists.
3. Sailor Media tab: `GET /api/member/{sa_id}/public-mentions` for helm/crew SAS IDs on **this** fleet. Team events skip sailor mentions (`reason: team_event`).
4. Club / class URL directory (`club_sources.json` / `class_sources.json` from `catalog_sources.py` — the same website + Facebook + Instagram clubs already publish on `/club/{slug}` and `/class/{slug}`). SA class sites only; international class URLs may be stored as `not_local`.
5. Known host-club posts (`social_collect.known_club_posts`).
6. Seed URLs for this slug (`SEED_URLS` in `event_rewrite.py` — gold-weekend discovery aids; **new weeks must find the same class of URL by search**, not by hardcoding September IDs).
7. Paid cluster APIs if keyed (Perigon / NewsCatcher / Event Registry).
8. Everywhere search (`search_everywhere.py`): Google News RSS + DuckDuckGo / Bing. Queries are `{event} {year}`, `{event} {month} {year}`, `{event} {club} facebook`, `{class} RSA facebook group`, date-bounded `after:` / `before:`. That search is what should surface SailingSA, the class write-up, and the host Facebook post.
9. Optional: SocialCrawl / Apify / gallery-dl / yt-dlp when those keys exist.

Coverage window: published during the regatta or in the **two weeks after** (`after_days=14`). A late class report up to 28 days after is allowed only when class + venue + ≥2 official names + year match (gold 505 class note dated 13 Oct).

A 2024 write-up, a UK Nationals, `dart.dev`, Wikipedia, a Facebook page home, a login wall, and a `/gallery` directory are **not** this event.

### Step 5 — Verify every candidate (the edit gate)

`evidence_pipeline.verify` + `results_checksum` + `verified_cluster`.

A source is kept only when:

| Check | Fail reason |
| --- | --- |
| Host is not wiki / dart.dev / etc. | `unrelated_host` |
| Not another SailingSA `/regatta/` | `different_event` |
| Not a login, homepage, `/photos`, Facebook page without `/posts/` or `/share/p/` | `directory_or_login` / `social_directory` |
| Body/caption ≥ 40 characters | `no_article_or_caption` |
| Year on the page matches the event year | `wrong_year` |
| Posted in the coverage window (or late-report exception) | `outside_event_window` |
| Title tokens of **this** event appear | `wrong_event_title` |
| Class **and** (venue **or** ≥2 official names) | `insufficient_event_identity` |
| Claimed 1st/2nd/3rd / “won” names are in official results | `results_checksum_failed` |
| Team event does not treat sailor cells as identity | `sailor_name_on_team_event` |
| Canonical URL / Facebook post id / content hash unique | `duplicate_source` |

Labels such as `seed` / `host` / `verified` are **not** identity. The body has to prove the event.

Schools cannot become competitor names. Gold 420 helm/crew cells are people (Dale Rae, Timothy Weaving), not “Hermanus High”.

Equal nett does not imply a tie-break rule. Gold 505 says the top two were level and the **official results** rank the Funkes first; the class report sentence about “won the last race” is cited `[2]` only because that text is on rsa505.org.za.

Six wins from eight is not a “clean sweep”. Sweep is only when wins == races and races ≥ 6 (gold Dabchick: 12/12).

### Step 6 — Gold external media (what actually survived)

This is the cluster that made Gold magazine copy, not a keyword dump.

#### 505 Nationals — Aeolians

| # | Source | Role |
| --- | --- | --- |
| [1] | `https://sailingsa.co.za/regatta/2026-09-24-ayc-505-nationals` | Official card. Funkes 14 nett, Klaas/Von Gruenewaldt 14, Biagio/Milln 30. 6 race wins each for the top two. |
| [2] | `https://rsa505.org.za/index.php?option=com_content&view=article&id=338:505-nationals-2026-great-event-at-aeolians` | Class write-up. Tight racing, tie, “The Funkes won the tie break by winning the last race.” |

**Photographs:** class page collage `https://rsa505.org.za/images/20261013_101619-COLLAGE.jpg` is a **three-panel contact sheet** (prizegiving / trophy / on-water) with a **photographed 2025 results sheet** in the collage. That URL is in `MEDIA_EXCLUSIONS` and must **never** be used as a photograph or as the homepage card.

Gold used the **on-water / prizegiving / trophy panels only**, cropped with SVG `source-photo-panel` viewBoxes on `media/2026-09-24-ayc-505-nationals-source.jpg` (2160×3840):

| Panel | viewBox | What it is |
| --- | --- | --- |
| On-water | `0 2560 2160 1280` | Boats on the water — the Gold story lead and the only legal homepage crop |
| Prizegiving | `0 0 2160 1280` | Prizegiving |
| Trophy | `0 1280 1080 1280` | Trophy presentation |

The 2025 sheet must stay clipped out. A later card that showed the raw `*-source.jpg` (prizegiving + sheet, black side bars) **broke this rule**. Homepage JS must `bannedHero` any `*-source.jpg` and prefer a dedicated on-water raster (`…-onwater.jpg` = that viewBox, 2160×1215).

Dropped: 2018 Worlds congratulations, J22 TikTok, class Facebook avatar, Wikimedia 505s.

#### Dabchick Gauteng Regionals — Aeolians

| # | Source | Role |
| --- | --- | --- |
| [1] | `https://sailingsa.co.za/regatta/2026-09-24-ayc-dabchick-gauteng-regionals` | Official card. Dylan Hall 10 nett, 12/12 wins. Maximilian Malan 21. Megan Stegen 35. |
| [2] | Facebook group post `facebook.com/groups/1072757722777738/posts/28611958198430986/` (Dabchick Oumanne & Ouchicks) | “Dabbie Gautengs 2026… 17 boats… Aeolians Club” + Google Photos album. |

**Photograph:** video still `media/2026-09-24-ayc-dabchick-gauteng-regionals.jpg`. Caption: “Video still; shared by Mark Biagio.” Play-button overlay **stays** — that is how Gold proved the still came from the on-water video (`media_kind: video_still`, Google Photos date 26 Sep). A later harvest that rejected this Facebook post as `social_directory` / `wrong_event_title` and fell back to a Lake Deneys Event Logo is why “the media is gone.”

Generic class-gallery lineup / hiking-dabbie shots from another weekend are **wrong event**. Do not reuse this Gauteng still on 3–4 Oct (Free State Youth / LDYC).

Dropped: YouTube channel homes, revolutionise.com.au class hero team photo as if it were this regional.

#### Dart 18 Nationals — Henley Midmar

| # | Source | Role |
| --- | --- | --- |
| [1] | `https://sailingsa.co.za/regatta/2026-09-24-hmyc-dart-18-nationals` | Official card. Bradley Levin 20 nett, no race win. Kyle Boman 26. Stemmetts 27. Status provisional. |
| [2] | HMYC Facebook Day 2 `…/posts/1632007462054028/` | One race, light shifting breeze. Day-2 places are **not** overall. |
| [3] | HMYC Facebook final `…/posts/1633819895206118/` (share `facebook.com/share/p/1PGpY1pGh1/`) | Overall top 3 + host-club 5th/7th/8th/9th (Kim Phillips, Lorrian Wells, Gregory Dobson, Josh Pretorius) — names checksum against official results. |

**Photographs:** two HMYC on-water / event jpgs from those posts (`…-nationals.jpg`, `…-nationals-2.jpg`), credited Henley Midmar Yacht Club.

Dropped: `dart.dev`, Dallas Area Rapid Transit, Dart Container, DartPad, **UK** Dart 18 Nationals at Royal Yorkshire, Instagram login PNG. A cluster that keeps those and then writes “public coverage focused on the same championship weekend” is a failed cluster.

#### 420 Nationals — Theewater

| # | Source | Role |
| --- | --- | --- |
| [1] | `https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals` | Official card. Dale & James Rae 10 nett, 6 wins / 8 races. Leoto/January 20. Mgcubhe/Smit 27. |
| [2] | `https://novanews.co.za/school/hermanus-high-schools-sailors-crowned-national-champions/` | Local news. Timothy Weaving and Hayden Miller **U17** champions. Caption names them. Age title is allowed **only** because this body names official-fleet sailors. |
| [3] | Facebook `420nationalssouthafrica` wrap post `…/posts/1647232950746805/` | Prizegiving photo (watermark 26–27 September 2026, TSC). Credit: Sara Falcon / Diplodocus Media. Also lists U19 Henshilwoods and U17 Weaving/Miller. |

**Photographs:** prizegiving from the class Facebook post; NovaNews U17 pair with the 420 trophy.

Dropped: generic Facebook `/photos` directories, Wikimedia 420s, school logos.

### Step 7 — Write the recap from the box score (pipeline B)

`evidence_pipeline.recap` — United Robots / Sportradar shape. No Google required.

Sentence order (Gold voice):

1. `{winner} won {Event} at {Venue}, scoring {nett} nett points across {R} races in a {E}-boat fleet. [1]`
2. Race-win colour from official heats only. Sweep / dominate / no individual race win. Dates from official start/end. `[1]`
3. Late-series colour only when the last four heats exist (`won N of the final four`). `[1]`
4. Second and third with nett. `[1]`
5. Other classes in a multi-class event. `[1]`
6. Tie: “The top two crews were level on nett points; the official results rank {winner} first.” `[1]` — no invented countback.
7. `source_notes` from verified cluster only: age titles, host-club place mentions that match official rank, class-report tie-break **if the body says it**. Each note carries its own `[n]`.
8. Provisional line if `result_status` is provisional. `[1]`

Headline (`unique_headline`): winner + verb + event + short venue. Verbs: *take* after a points tie, *sweep* when every race is a win (races ≥ 6), *dominate* when wins ≥ max(3, races/2), else *win*. Team event with no official winner: `{N} teams contest {title} at {venue}`.

Deck: `Venue · nett · entries` (winner name is **not** repeated in the deck on Gold HTML).

Kicker: `{CLASS}  ·  {CLUB}`.

### Step 8 — AI over-creation (polish, not invent)

`app/ai_assist.py` → `polish(facts, cluster, index, fallback)`.

When `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` or `PERPLEXITY_API_KEY` is set on the GoWifi box, the model redrafts the recap in the Gold voice. **RAG cage:** the prompt is only official facts + numbered source bodies (≤900 chars each) + the fallback paragraphs. System rules:

- Magazine paragraphs, not a box score.
- First sentence = winners / event / venue / nett / races / fleet. `[1]`
- Race-win colour only from the official card. `[1]`
- Then 2nd and 3rd. `[1]`
- Then only facts that appear in a numbered source.
- No invented names, venues, photos, or scores.
- Every paragraph ends with `[n]`.
- Return JSON `{"paragraphs":[…]}`.

`valid()` rejects the draft unless: ≥2 paragraphs; every paragraph has a citation in the index; winner or venue/title appears; proper nouns are official names or known venue words.

**Failed or missing key → Gold recap is published as-is.** The AI is an over-writer, not a source. It cannot add a photo, a U17 title, or a TSL winner that is not in the cage.

Production `data/roundup.env` must carry at least one of those keys or every new URL stays on the template recap. Template recap is Gold-legal. Invented colour is not.

### Step 9 — Photographs: pick, prove, store

`pick_images` → `download_image` → local `issues/YYYY-MM-DD/media/` and `public/issues/YYYY-MM-DD/media/`.

Keep, in order:

1. `admin_seed` (WhatsApp / race office file in `app/seed_media/`, mapped in `SEED_PHOTOS`). Portrait is allowed. Credit stays “event administration”. Cropped to Gold 16:9 with `crop_center_hero` (horizon from row variance; subject at 0.66 of frame so boats sit low and water under the hulls is thin).
2. Images attached to **accepted** cluster members (og:image, article `<img>`, Facebook lookaside) whose source URL passed verify.
3. Media-tab images for official sailors of **this** event.

Reject:

- `/artwork/event logo/`, `/artwork/club logo/`, `/artwork/class logo/`
- any URL with `logo`, `flag`, `banner`, `avatar`, `icon`, `sprite`, `.svg`, `yt_1200`, `api/og`
- Wikimedia
- `MEDIA_EXCLUSIONS` (505 collage results sheet)
- Facebook page chrome (page home OG, not a `/posts/` or `/share/p/`)
- bytes that fail `_is_event_photograph`: too small, extreme aspect, square poster, ≥55% flat colour blocks (flags / “enter now” artwork)
- PNG official artwork as the weekend hero
- a photo whose source is not in the accepted cluster (unless admin_seed)

Score (`_event_photo_score`) prefers prizegiving / trophy / final-result posts and this event’s class/club hosts. Wiki and wrong-class tokens go negative.

Download: ≥8 KB, real image bytes, unique sha. Duplicate photograph hashes fail `safe_publish.validate`.

Caption (`photo_caption`): official names + age title if the source body has them; else `{title} — {venue}. Photo: {credit}.`

**No photograph is better than a logo.** A scored event may publish with copy + podium and zero figures. It must not publish the host Event Logo to “fill the hole.”

Gold 09-28 kept: 505 three cropped panels, one Dabchick video still, two Dart club jpgs, two 420 jpgs (prizegiving + NovaNews). That is the bar: **event photography from the event’s own sources**.

### Step 10 — Assemble `issue.json`

`rewrite_event` + `rewrite_weekend_feature`.

```text
issue.json
  feature          (type=feature, layout=lead, weekend hero attached)
  regatta_report × N   (one per scored slug)
```

Each report: headline, deck, kicker, byline `SailingSA`, `published_at` = Monday, `hero_image`, ordered `blocks` (images, paragraphs, heading, results), `sources`, `citations`, `review_status=rewritten`.

`review_status=edited` is a human lock. `enrich_existing` must not overwrite it.

Sources written beside the issue:

| File | What |
| --- | --- |
| `issues/YYYY-MM-DD/sources/events-weekend.json` | Calendar snapshot |
| `issues/YYYY-MM-DD/sources/{slug}-results.json` | Official API rows |
| `issues/YYYY-MM-DD/sources/{slug}-cluster.json` | Accepted + rejected evidence |
| `issues/YYYY-MM-DD/sources/{slug}-media.json` | Media-tab pack |
| `issues/YYYY-MM-DD/sources/build-log.json` | Per-event status |

The public HTML/PDF must **not** dump `source_info` or social caption lists.

### Step 11 — Render HTML + PDF + NewsArticle

`roundup.render(issue)` + `gold_default.css`.

- Sticky SailingSA header (do not restyle the site-wide header).
- Edition lead + one `.event-story` per report.
- Citations become `<sup class="cite"><a href="#slug-src-n">n</a></sup>`.
- Event URL(s) immediately under every event H2: `<p class="event-url"><a href="https://sailingsa.co.za/regatta/{slug}">https://sailingsa.co.za/regatta/{slug}</a></p>`. Gold 09-28 lists all four: 505, Dabchick, Dart 18, 420. A story with no `/regatta/` slug publishes without a fake link. `roundup._article_event_urls` collects every `/regatta/` URL from results blocks, sources, citations, and the event id — all of them must render as clickable lines under that headline.
- 505 source-region crops stay SVG `source-photo-panel` viewBoxes on `*-source.jpg`. Re-render must not flatten those panels into a full collage `<img>`.
- NewsArticle JSON-LD (`app/news_schema.py`): `datePublished` Monday 06:00 SAST, `headline`, `author`, `image` = weekend hero, `about` = SportsEvent per scored slug. Each SportsEvent must include Google’s Events required fields (`name`, `startDate`, `location`). If a report has no dated slug or venue, omit that `about` item — incomplete SportsEvent markup is a Search Console ERROR.
- PDF: headless Chromium, A3, same HTML.

`landing.write_public_index()` then writes:

- `public/issues/YYYY-MM-DD/cards.json`
- `public/feed.json` (newest first; `image` = `edition_hero` = **feature** photograph, not `cards[0]`)
- `public/archive.json`, `public/latest.json`, `public/index.html`, `public/latest/`

### Step 12 — Isolated validate, then replace only that issue

`app/safe_publish.py`:

1. Copy app + this issue into `.builds/`.
2. Delete previous HTML/JSON/PDF so a failed render cannot reuse last week’s PDF.
3. `publish_weekend.py --monday YYYY-MM-DD --rebuild`.
4. `validate()`:
   - unique event ids
   - every scored calendar slug has a report
   - every cluster article `verification.accepted`
   - unique citations; every paragraph `[n]` is in the index
   - every results block has rows (≤80)
   - every image file exists and hashes are unique
   - HTML + real PDF
5. Atomic replace of `issues/YYYY-MM-DD` and `public/issues/YYYY-MM-DD` only. On failure, restore last-good. Other issues are not touched.

### Step 13 — Publish the URL on SailingSA

`deploy/publish-to-sailingsa.sh <public> YYYY-MM-DD`

- Generation stays on GoWifi (`/opt/rea/work/sailing-roundup`).
- Authenticated rsync of **one** issue onto `/var/www/sailingsa/sailing-roundup/issues/YYYY-MM-DD/`.
- Landing files (`index.html`, `latest.json`, `feed.json`, `cards.json`) overwritten **without** `--delete` of other issues.
- Never touch the SailingSA SPA, API, nginx, database, or master header.
- Never full-deploy local `sailingsa/frontend/index.html` (live homepage is ahead: event cards, landing-top-row). Homepage card JS/CSS is a **surgical** file (`/var/www/sailingsa/js/landing-roundup-cards.js`) plus a small style block — not a zip of the frontend.

Verify: `https://sailingsa.co.za/sailing-roundup/issues/YYYY-MM-DD/` plus `issue.json` and `edition.pdf` return 200 and match the rebuilt HTML.

### Step 14 — Homepage card + Google (automatic consumers)

Homepage `#landing-top-card` loads `/sailing-roundup/feed.json`, then each issue HTML.

| Card rule | Why |
| --- | --- |
| Default = newest Monday | Swipe left = older; swipe right = newer |
| One card visible | Next card must not peek (`visibility:hidden` on inactive slides) |
| Tap → `window.location.assign(issue URL)` | Full magazine, not a fragment |
| Hero = `feed.image` if not banned, else first real `<img>` jpg | Skip artwork logos, `*-source.jpg`, all `.png` |
| 16:9, max-height ~220px, `object-fit: cover`, full bleed | Gold hero height. No black side bars. No sky-locked crop. |
| Headline clamp 28–40px | Do not crunch with viewport `cqw` fitters |

Google (automatic — no Search Console click after the first submit):

| File | Rule |
| --- | --- |
| `/sailing-roundup/` | Hub. Always in `/sitemap-roundups.xml`. `changefreq` weekly, `lastmod` = newest Monday |
| `/sailing-roundup/latest/` | Child of the hub. Same weekly signal |
| `/sailing-roundup/issues/YYYY-MM-DD/` | Every published Monday HTML. Example: `/sailing-roundup/issues/2026-10-19/` |
| `/sitemap-roundups.xml` | Hub + `/latest/` + **all** issue URLs (historical depth) |
| `/sitemap-news.xml` | First-party issue URLs from the last **48 hours** only (`news:news`) |
| `/sitemap.xml` | Index lists both child sitemaps |
| `/robots.txt` | `Sitemap:` lines for `sitemap.xml`, `sitemap-roundups.xml`, `sitemap-news.xml` |
| Issue HTML | Self-canonical (apex, trailing slash), `index,follow`, Open Graph, NewsArticle JSON-LD |
| `/sailing-roundup/latest/` | Canonical **to the newest issue URL** so GSC does not treat it as a duplicate |
| `/regatta/{id}` | SportsEvent (sport Sailing) — already on the results card |

Monday publish (`publish-to-sailingsa.sh`) rewrites the two child sitemaps at `/var/www/sailingsa/`, patches the index + robots, and pings `https://www.google.com/ping?sitemap=`. The daily cron (`refresh-sitemap-cron.sh` → `utils.sitemap_builder`) writes the same files so a new Monday is not deleted overnight. Indexing API `URL_UPDATED` is optional (`--notify-google` / `GOOGLE_INDEXING_SA_JSON`) and fires for the hub, `/latest/`, and the new issue. Failure must not block publish. A traction day can burn the daily quota on purpose: `python3 app/request_google_index.py --until-quota` (roundup URLs first, then high-traffic site pages, stop when Google returns quota exhausted).

Historical issues are **archive URLs**. They are not injected into `/api/news/latest`.

---

## 3. Automatic Monday path (no human)

Timer: `sailing-roundup.timer` — `OnCalendar=Mon *-*-* 06:00:00` Africa/Johannesburg, user `rea`.

```text
sailing-roundup.timer
    → deploy/run-monday.sh
        → app/safe_publish.py --monday <this Monday>
            → publish_weekend.py --rebuild
                events table → results API → cluster → recap → AI polish
                → photos → issue.json → HTML/PDF → feed.json
        → deploy/publish-to-sailingsa.sh public YYYY-MM-DD
        → write_google_sitemaps.py --web-root /var/www/sailingsa
        → curl live HTML / issue.json / edition.pdf
```

`ROUNDUP_MODE=due` in `/opt/rea/work/sailing-roundup/data/roundup.env`. `test-weekend` is **only** for rebuilding 2026-09-28.

Controls already in the job:

- `flock` on `data/monday.lock` — second start exits 0
- three attempts, 90s apart, for generate / publish / verify
- last-good under `backups/` + remote `.last-good/issues/`
- mail `ROUNDUP_ALERT_TO` (kevin@aerialnet.co.za) on failure
- SailingSA-local `/opt/sailing-roundup` timer is **masked** so it cannot publish a second copy

Empty week: `publish()` returns `skipped_empty_weekend` — no URL, no card.

Missing scored slug: `RuntimeError` — last-good stays; alert fires. The job must retry the slug, not skip Mirror because a calendar stub lacked a slug (`has_results` must survive the calendar-stub merge).

`review_status=edited` articles are left alone on `--due` enrich.

Admin WhatsApp seeds (`SEED_PHOTOS`) are an **escape hatch**, not the weekly path. If a new week needs a human photo, harvest failed.

---

## 4. Rules that later issues broke (do not repeat)

These are Gold rules, not preferences. They are why 5 / 12 / 19 Oct needed intervention.

| Failure | Gold rule | Code that must enforce it |
| --- | --- | --- |
| Event-data dump instead of a magazine | Cluster + cited recap + photos. AI polish when keyed. | `cluster_coverage`, `recap`, `ai_assist.polish` |
| Full-fleet table | Podium is 1st/2nd/3rd only | `LEADERBOARD_LIMIT=3`, heading `1st, 2nd, 3rd` |
| Invented TSL 1-2-3 (MAC/MATIES/Eden) | No official rank/nett → no winner, no invented board places | `_fleet_from_rows.official_order`, `recap` team branch |
| Sailor names on TSL board | Identity is `boat_name` | `is_team_row`, checksum `sailor_name_on_team_event` |
| Host Event Logo as the photograph | Logos are not photographs. Empty figure is legal. | `pick_images` skip `official_event_artwork`; `_is_event_photograph`; homepage `bannedHero` |
| 505 collage / 2025 results sheet as card | Collage URL excluded; card uses on-water crop only | `MEDIA_EXCLUSIONS`; `bannedHero` on `*-source.jpg` |
| Dabchick media “gone”; FS Youth logo on 3–4 Oct | Keep the verified Facebook video still; do not reuse it on another event; do not substitute a logo | `verify` must accept class/group **posts**; never fall back to artwork |
| Mirror missing on 19 Oct | Scored same-weekend event cannot be “results not available” | `feature()` only lists `has_results=false`; calendar-stub merge keeps the slug |
| Homepage still showing 10/11 Oct | Card reads `feed.json` newest first; hero from feature | `edition_hero`, live `landing-roundup-cards.js` |
| Card not clicking through | Tap assigns the issue URL; swipe does not | `data-issue-url` + `location.assign` |
| Next card peeking | Only the active slide is visible | `showOnly` + overflow hidden |
| Squashed / crunched headline | Gold type scale, 16:9 cover | no `fitTitle` / `8cqw` |
| Black bars on Sep card | Full-bleed jpg, not a letterboxed SVG collage | dedicated `…-onwater.jpg` |
| Harvest rejects class Facebook as `social_directory` | A `/posts/` or `/share/p/` or group post with a caption is a source | `verify` path tokens; do not treat group posts as page homes |
| `_event_photo_score` only boosts September Facebook ids | New weeks must score prizegiving / on-water / this-class hosts without hardcoded Sep post ids | generalize the scorer |
| `SEED_URLS` only lists the four Sep slugs | Discovery queries + club/class directory must find the class write-up and host post for **any** slug | `discovery_queries`, `catalog_local_urls` |
| Live homepage JS drift | Publish path updates `feed.json`; card JS is a separate surgical file. A frontend zip wipes live event cards. | issue-scoped rsync only |
| AI keys missing on the box | Template recap is legal; do not invent colour to compensate | `ai_assist.polish` fallback |

---

## 5. Acceptance checklist for a new Monday URL

A new `https://sailingsa.co.za/sailing-roundup/issues/YYYY-MM-DD/` is Gold when **all** of these are true with **no hand edit**:

1. Timer ran `--due` for that Monday (or `--year` for a historical week that had racing).
2. Every scored `regatta_id` that finished in the previous week has a report. Calendar-only names appear only in the feature.
3. Each report has a unique headline, kicker, **every referred-to SailingSA event URL listed and clickable directly under the H2**, Gold deck, cited paragraphs, and a 3-row official podium headed `1st, 2nd, 3rd`. Gold 505: heading then `https://sailingsa.co.za/regatta/2026-09-24-ayc-505-nationals`.
4. Team events name teams. No sailor dump. No invented overall places.
5. Every paragraph has `[n]`. `[1]` is the official card. Age titles cite a verified body that names official sailors.
6. Photographs (if any) are on-water or prizegiving from this event’s cluster, credited, unique hashes. Video stills may show playback UI. **Zero logos.**
7. Weekend hero on the lead, `feed.json`, and NewsArticle is that photograph (or empty — never a logo).
8. Homepage newest card is this Monday, full-bleed 16:9, tappable to this URL, no peek of the next card.
9. HTML, `issue.json`, `edition.pdf` all 200. Other issue URLs unchanged.
10. `/sitemap-roundups.xml` lists the hub, `/latest/`, and this URL. `/sitemap-news.xml` lists this URL only if it is inside 48 hours. `robots.txt` names both child sitemaps.

If any item fails, the job alerts and last-good stays. A human does not open the HTML to “fix the card.”

---

## 6. Commands (GoWifi)

```bash
# Production Monday (timer does this)
ROUNDUP_MODE=due bash /opt/rea/work/sailing-roundup/deploy/run-monday.sh

# Rebuild one week in isolation, then publish only that URL
python3 app/safe_publish.py --monday YYYY-MM-DD
bash deploy/publish-to-sailingsa.sh /opt/rea/work/sailing-roundup/public YYYY-MM-DD

# Gold lock — do not use to “fix” later weeks
python3 app/safe_publish.py --test-weekend

# Historical year (skip empty weeks; keep edited issues)
python3 app/publish_weekend.py --list-year 2026
python3 app/publish_weekend.py --year 2026

# Tests
python3 -m unittest discover -s tests
```

Live publish from a laptop (issue-scoped only):

```bash
SAILINGSA_SSH_IDENTITY=~/.ssh/sailingsa_live_key \
  bash gowifi/rea/sailing-roundup/deploy/publish-to-sailingsa.sh \
  gowifi/rea/sailing-roundup/public YYYY-MM-DD
```

---

## 7. Code map

| Step | File |
| --- | --- |
| Week assignment | `app/events_weekend.py` |
| Monday / year publish | `app/publish_weekend.py` |
| Isolated validate + replace | `app/safe_publish.py` |
| Facts, cluster, photos, article | `app/event_rewrite.py` |
| Verify, checksum, recap, feature | `app/evidence_pipeline.py` |
| AI polish | `app/ai_assist.py` |
| Search | `app/search_everywhere.py` |
| Club/class directory | `app/catalog_sources.py`, `club_sources.json`, `class_sources.json` |
| Social verify | `app/event_social_verify.py`, `app/social_collect.py` |
| Media-tab | `app/sailor_mentions.py` |
| HTML / PDF | `app/roundup.py`, `app/gold_default.css` |
| Feed / archive / edition hero | `app/landing.py` |
| NewsArticle JSON-LD | `app/news_schema.py` |
| Chrome restyle (never 09-28) | `app/restyle_to_gold.py` |
| Timer | `deploy/run-monday.sh`, `sailing-roundup.timer` |
| Live rsync | `deploy/publish-to-sailingsa.sh` |
| Homepage cards | live `/var/www/sailingsa/js/landing-roundup-cards.js` (not the SailingSA SPA zip) |

---

## 8. What this document is for tomorrow

Stop patching live cards by hand. Close the harvest gaps in §4 so the Monday job produces a Gold URL on its own: find the class/club/Google/Media-tab sources, keep real photographs (including video stills), write the cited recap, optionally polish with AI, checksum, publish, and let `feed.json` update the homepage.

The locked proof remains:

https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/
