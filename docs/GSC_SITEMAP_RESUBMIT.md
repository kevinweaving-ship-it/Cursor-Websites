# Google Search Console — SailingSA sitemaps

Property: **https://sailingsa.co.za** (apex). `www` should 301 here (`nginx-sailingsa-www-redirect-443.conf`).

## Submit once

1. Open [Google Search Console](https://search.google.com/search-console) → property **https://sailingsa.co.za**.
2. Indexing → Sitemaps → add:

| Sitemap | What Google gets |
| --- | --- |
| `sitemap.xml` | Index of all child urlsets |
| `sitemap-roundups.xml` | Hub + `/latest/` + every `/sailing-roundup/issues/YYYY-MM-DD/` |
| `sitemap-news.xml` | Issues from the last 48 hours only (`news:news`) |

New Monday issues are added automatically (Monday publish + daily cron + Google ping). Do not submit each issue URL by hand.

## Live files Google must fetch as XML

- https://sailingsa.co.za/sitemap.xml
- https://sailingsa.co.za/sitemap-roundups.xml
- https://sailingsa.co.za/sitemap-news.xml
- https://sailingsa.co.za/robots.txt

`sitemap-classes.xml`, `sitemap-clubs.xml`, `sitemap-core.xml`, `sitemap-regattas.xml`, `sitemap-sailors.xml` stay in the index.

If a child sitemap 404s as `application/json`, nginx is proxying a missing file to the API. Write the file to `/var/www/sailingsa/` and keep `nginx-sitemap-children.conf` in front of `location /`.

## Issue pages

Each `https://sailingsa.co.za/sailing-roundup/issues/YYYY-MM-DD/` must have:

- `<link rel="canonical">` to itself (apex, trailing slash)
- `<meta name="robots" content="index, follow">`
- `og:title` / `og:url` / `og:image` when a photograph exists
- `NewsArticle` JSON-LD (`datePublished`, `headline`, `publisher`)

`/sailing-roundup/latest/` canonicals to the newest issue so GSC does not treat it as a duplicate.

JSON feeds (`feed.json`, `archive.json`, `cards.json`, `latest.json`) are `Disallow` in robots — they are not HTML locs.
