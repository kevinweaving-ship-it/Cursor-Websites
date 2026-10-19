# Real article-aggregation systems to reverse-engineer

Researched 19 October 2026 from public docs. No paid keys were used.

## The model to copy: Perplexity Discover (RAG news)

Perplexity Discover / core search is the best working example of
“many sources → one article” for a real event.

- **Aggregate:** when an event is flagged, scrape primary outlets
  (Reuters / BBC / Bloomberg *and* the local club or class page). For
  sailing that means search for the host-club Facebook post, the local
  class Facebook group, the class write-up, and the local news piece —
  not Wikipedia, and not waiting for someone to paste every share link.
  A human can find `share/g/…` groups in two seconds; discovery must
  do the same query (`505 RSA facebook group`, `Dart 18 SA facebook`).
  Search is `{event_name} {venue} {dates}`; keep a hit only when it was
  posted during the event or in the days immediately after
  (`after:` / `before:` on Google, `pubDate` / `article:published_time`
  on the page). A 2024 write-up is not coverage of the 2026 nationals.
- **Synthesize:** the model reads those bodies, drops repeated fluff,
  and writes one structured article from scratch.
- **Accuracy:** every claim has an inline citation back to a scraped
  source. Retrieval-Augmented Generation (RAG) locks the writer to the
  cage of those 10–20 texts. If a fact is not in a source, it is not
  written.
- **Photographs:** come from a member of that cluster. Prizegiving of
  1st / 2nd / 3rd and boats on the water are both valid. More than one
  photo is allowed. A Wikimedia file of a 1954 dinghy is not a source.

Same family, used for the same contract:

| Platform | What to copy |
| --- | --- |
| [Rize](https://rizenews.com) | Morning digest: cluster same-topic stories, write 1–2 paragraphs. |
| [Ground News](https://ground.news/about/) | Cluster dozens of articles for one event, one unified summary. |
| Artifact | De-bait the headline; rewrite long reports into a clear timeline. |
| LetMeKnow.News | AI clustering so the reader is not shown the same story twice. |

`app/event_rewrite.py` is **not** one of these systems. It keyword-dumps
Google News / Bing hits into a list named `cluster`, then fills five mad-lib
paragraphs from the results table. The 2026-09-28 Dart cluster contains
`dart.dev`, Dallas Area Rapid Transit, Dart Container, DartPad, and the
**UK** Dart 18 Nationals at Royal Yorkshire. The article then says
“public coverage focused on the same championship weekend.” That is why the
copy does not make sense.

There are **two** products. REA mixed their names and implemented neither.

```text
A. News cluster          B. Sports NLG
   many URLs                one event id + box score
        |                         |
   same real-world event    insight engine on structured data
        |                         |
   story object                 recap article
   (name, summary,              (headline + body + image
    members, image)              from a tagged library)
```

Sailing weekend coverage needs **both**, in that order:

1. Build a **verified cluster** (pipeline A). If it has fewer than two
   independent items about **this** event (same class, venue, dates), the
   cluster is empty. Do not invent “coverage.”
2. Write the recap from **results** (pipeline B). Colour from the cluster
   only when a sentence is grounded in a member article body.
3. Featured image comes from a **member of that cluster**, or from a
   class/club photo library tagged to the boat that raced. Never from a
   keyword image search for “Dabchick” (birds) or “Dart” (the language).

---

## Pipeline A — cluster many articles about one happening

These systems take a firehose of published articles and group them. They do
**not** start from a results table. They do **not** write a newspaper
feature unless noted.

### 1. NewsCatcher — clustering algorithm to copy

- Docs: https://www.newscatcherapi.com/docs/news-api/guides-and-concepts/clustering-news-articles
- Search: `POST` with `clustering_enabled=true`
- What it actually does:
  1. Offline: embed each article (`title` + `content`). From 1 Jan 2026
     the model is **Qwen3-Embedding-0.6B**.
  2. Query time: cosine similarity between embeddings.
  3. Pairs above `clustering_threshold` (default **0.7**) become edges.
  4. **Leiden** community detection → `cluster_id` + `cluster_size` + articles.
- What it does **not** do: write a unique article or pick a photo.
- Reverse-engineer this first. A “cluster” that mixes Midmar Darts with
  `dart.dev` is a failed similarity graph, not a story.

### 2. Perigon Stories — story object to copy

- Docs: https://perigon.io/docs/api/data-model
- Shape write-up: https://perigon.io/blog/news-stories-api-json-response-shape-and-sample-output
- `GET /v1/stories/all?q=` then `GET /v1/articles/all?clusterId=`
- One Story ← N Articles. An article belongs to **one** story.
- Generated fields: `name`, `summary`, `shortSummary`, `keyPoints[]`,
  `imageUrl`, `uniqueCount` / `reprintCount`, top people / orgs / topics.
- A story **title is generated only after five member articles**.
- Sample (rugby, not sailing): “Red Bull Completes Newcastle Rugby
  Takeover…” + six unique articles + key points with source ids.
- Reverse-engineer the **object**, not a five-paragraph essay:
  `cluster_id`, generated name, short summary, key points, member URLs,
  one `imageUrl` taken from the members.

### 3. Event Registry / NewsAPI.ai — event object to copy

- https://newsapi.ai/ · `POST /event/getEvents` · `POST /event/getEvent`
- An **event** is a deduplicated real-world happening, not a keyword hit.
- Event has title, summary, images, concepts, location, and the grouped
  article bodies (`articleBodyLen`).
- Reprints of the same wire story collapse into one event.
- Reverse-engineer: one event URI per regatta weekend, then pull member
  **bodies**, not Open Graph titles.

### 4. Monok — the only one that emits a full unique article + stored image

- Docs: https://monok.news/docs/ · API: https://monok.readthedocs.io/en/latest/api.html
- Integration: https://monok.news/docs/integration/
- Two APIs:
  - `GET /api/v1/articles/` — original publisher articles (optional `full=true` body).
  - `GET /api/v1/clusters/` — clusters of those articles about the **same news event**.
- Then it **writes a new article** and pushes JSON to the publisher CMS:

  | Field | Meaning |
  | --- | --- |
  | `title` / `shortTitle` | Unique headline, not the source headline |
  | `description` | Meta deck |
  | `content` | Full HTML article |
  | `text` | Markdown + JSON widgets (YouTube / IG / X embeds) |
  | `thumbImageData` | **Base64 PNG stored in the publisher image DB** |
  | `thumbImageDescription` | Caption |
  | `vfImage` | Featured-image metadata |

- Human edit mode exists. Auto-push happens after an editor submits.
- Featured image is **the cluster’s visual focus**, stored locally. Not a
  Wikimedia fallback, not a club logo, not a YouTube `yt_1200` card.
- Reverse-engineer this as the **output contract** of the Monday job:
  unique headline, original body, one stored image, then a box score.

### 5. Ground News — consumer UI of a cluster

- https://ground.news/about/
- ~60 000 articles/day from ~50 000 outlets. Same event → one story card:
  neutral headline, short summary, source list.
- Does **not** write original journalism. Useful as the **landing-card**
  shape: one event, one headline, one image, N sources.

### 6. Techmeme / Memeorandum — editorial cluster gold standard

- https://www.techmeme.com/ · sister sites for politics / media
- Seed a source list, discover more by **inbound links**, rank a cluster
  by citations + recency, show **one lead headline + related coverage**.
- Does **not** rewrite. Reverse-engineer the **page**: lead + related
  links, never a paste of every caption.

### 7. Also in this family (do not pretend we implemented them)

| System | URL | What it is |
| --- | --- | --- |
| Google News | https://news.google.com | Story clusters / Full coverage. No usable cluster API. |
| Apple News | — | Editor + algo clusters. Closed. |
| NewsNow | https://www.newsnow.co.uk | Keyword columns, not event clusters. |
| GDELT | https://www.gdeltproject.org | Global event database, not an article. |
| Diffbot KG | https://www.diffbot.com | Entity/event extraction from pages. |
| Aylien / Meltwater | https://aylien.com | News intel, story clusters. |
| News 2 Post | https://adabeat.com/case/news-2-post-built-with-elixir-phoenix-and-openai/ | Fetch bodies → rewrite one CMS post + image. |

---

## Pipeline B — structured sports data → recap

These systems start from an **event id and a box score**. That is the
SailingSA `/api/regatta/{slug}` job. They do not Google the class name.

### 8. Sportradar GenAI Recaps — event-id → article

- https://developer.sportradar.com/images-and-editorials/reference/gen-ai-overview
- Recap: https://developer.sportradar.com/images-and-editorials/reference/gen-ai-recap
- Live on marketplace 12 June 2026.
- `GET .../games/{sport_event_id}/post-match-recap.json`
- Available **30 minutes after** the event ends.
- Payload: `metadata.title`, `content.markdown`, `content.html`,
  `content.plaintext`, plus `references` (players, venue, competition).
- Length is **300–400 characters**, not a five-paragraph feature.
- Reverse-engineer: `regatta_id` → headline + short recap + entity
  references (helm, crew, club, class, venue). No web search required.

### 9. Stats Perform Automated Insights / Wordsmith

- https://www.statsperform.com/automated-insights/
- Opta (and OptaAI / xG) → previews, live insights, **post-game recaps**,
  player bios. The AP used Wordsmith for earnings and sports.
- Reverse-engineer: every sentence is a **data point** (winner, nett,
  countback, race wins, discard). If the data is not in the JSON, the
  sentence is not written.

### 10. United Robots — the production newsroom version

- Sports: https://www.unitedrobots.ai/content-services/sports
- How: https://www.unitedrobots.ai/about/the-robots
- Reuters Institute write-up (Diario Huarpe, ~250 football pieces/month):
  https://reutersinstitute.politics.ox.ac.uk/news/how-local-paper-argentina-uses-ai-publish-hundreds-sports-pieces-month
- Insight engine on **structured data** chooses the angle (sweep, tie,
  come-from-behind, no race wins).
- NLG inserts those data points into **human-written language segments**.
  Facts are guaranteed because they come from the feed, not a model.
- Image library is **uploaded and tagged** (team, win/loss). The robot
  picks a tagged photo. It does not image-search the class name.
- Reverse-engineer for sailing:
  - Angle from the race card (tie / sweep / consistency / provisional).
  - Language segments, not one mad-lib for every event.
  - Photo library: 420 / 505 / Dart 18 / Dabchick **boats**, tagged.
  - Box score is 1st / 2nd / 3rd only.

### 11. Historical cousins (same contract)

| System | Notes |
| --- | --- |
| Washington Post Heliograf | Data → short sports / election copy. |
| AP + Automated Insights | Earnings and sports recaps at scale. |
| BBC / PA RADAR | Structured local-news NLG. |

---

## What the 2026-09-28 cluster actually contained

From `issues/2026-09-28/sources/*-cluster.json`:

| Event | Kept as “coverage” | Should have been dropped |
| --- | --- | --- |
| Dart 18 Nationals | HMYC Facebook top-3 post | `dart.dev`, dart.org (Dallas transit), Dart Container, DartPad, UK Nationals at Royal Yorkshire, Instagram login PNG |
| 505 Nationals | RSA 505 class note; some FB | 2018 Worlds congratulations; J22 Nationals TikTok; class Facebook avatar |
| 420 Nationals | NovaNews U17 piece (real, different title) | Generic Facebook /photos URLs |
| Dabchick Regionals | Almost nothing on-event | YouTube channel homes, class site hero team photo |

A real clusterer (NewsCatcher Leiden at 0.7, or Perigon’s “five articles
before a title”) would have produced **one** Dart story (the HMYC results
post) and refused to write “public coverage” from the rest.

---

## Contract to implement next (do not name-drop this time)

Copy **NewsCatcher + Perigon** for ingest, **United Robots + Sportradar**
for the recap, **Monok** for the stored article JSON.

```text
regatta slug
    → fetch /api/regatta/{slug}                 # structured data
    → collect candidate URLs (club/class/FB)
    → extract TITLE + BODY (skip login/home/logo)
    → embed title+body; drop similarity < 0.7
      to the event seed (class + venue + dates + helm names)
    → if members < 2: cluster = empty
    → angle from results (tie / sweep / lead / win)
    → write recap from results + quoted cluster facts only
    → image = cluster member photo of the class that raced
      else tagged class-boat library
    → emit Monok-shaped article:
         title, shortTitle, description, content/html,
         thumb stored under issues/YYYY-MM-DD/media/,
         leaderboard rows 1..3 only
```

Do **not**:

- Keyword-search the class name on Bing and call it a cluster.
- Write “Outside the scoreboard, public coverage…” when the cluster is junk.
- Use a Wikimedia / gallery image of the wrong boat, a logo, a team lineup,
  or a YouTube placeholder.
- Print the full fleet. Leaderboard is positions **1, 2, 3**.
