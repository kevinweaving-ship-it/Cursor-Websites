# Independent Sailing Roundup — news feed contract v1

Output: `GET /sailing-roundup/issues/YYYY-MM-DD/issue.json` on the REA box
(`https://box.gowifi.co.za/sailing-roundup/`). SailingSA is a read-only input
source and optional feed consumer; its codebase, services, database and CSS
remain untouched.

Each article: id (stable), type (feature|regatta_report|brief), headline, deck,
byline, published_at, event_id, hero_image (nullable), blocks (ordered),
sources (URLs), social_sources (optional).

Block types: paragraph, heading, image, quote, results, video.
Image block: url, alt, caption, credit, source_url, rights_status.
Results block: source_event_url, columns, rows, as_of.
Draft/unverified data is not treated as licensed reuse.

The consuming website renders its own layout. A separately generated PDF uses
the same issue JSON. Empty article lists still produce a landing page + PDF.

Folders: `issues/YYYY-MM-DD/media`, `issues/YYYY-MM-DD/sources`,
`public/issues/YYYY-MM-DD/` for the published feed.
