# Independent Sailing Roundup — news feed contract v1

Output: `GET https://sailingsa.co.za/sailing-roundup/issues/YYYY-MM-DD/issue.json`.
The edition is generated independently (GoWifi REA box) and published as static
files under `/var/www/sailingsa/sailing-roundup/`. SailingSA remains a read-only
results source; this path does not change the SailingSA SPA, header, or database.

The lead article is type `feature` and is written from the public `events`
table rows whose dates overlap Saturday–Sunday (reference: 26–27 Sep 2026).
Each following article is a **rewritten** regatta report: unique headline,
original copy clustered from the event's own sources with inline citations,
photographs from those same sources (podium and on the water are both
valid; more than one photo is allowed; never Wikimedia), and a compact
leaderboard only. Discovery searches `{event} {dates}` on the web and
keeps only posts published during the regatta or in the two weeks after. Fields: id (stable), type (feature|regatta_report|brief),
headline, deck, byline, kicker, layout (lead|photo-led|split|classic|compact),
published_at, event_id, hero_image (nullable), blocks (ordered), sources (URLs).
The public HTML/PDF must not dump `source_info` or social caption lists.

Block types: paragraph, heading, image, quote, results, video.
Image block: url, alt, caption, credit, source_url, rights_status.
Results block: source_event_url, columns, rows, as_of.
Draft/unverified data is not treated as licensed reuse.

The consuming website renders its own layout. A separately generated PDF uses
the same issue JSON. Empty article lists still produce a landing page + PDF.

Folders: `issues/YYYY-MM-DD/media`, `issues/YYYY-MM-DD/sources`,
`public/issues/YYYY-MM-DD/` for the published feed.
