# Resubmit sitemap in Google Search Console (GSC)

After adding or changing URLs in the sitemap (e.g. class URLs `/class/{id}-{slug}`), resubmit so Google recrawls.

## Steps

1. Go to [Google Search Console](https://search.google.com/search-console).
2. Select the property for **https://sailingsa.co.za** (or your live domain).
3. In the left menu, open **Sitemaps** (under “Indexing”).
4. In “Add a new sitemap”, enter: **`sitemap.xml`** (or the full URL **https://sailingsa.co.za/sitemap.xml** if the field accepts it).
5. Click **Submit**.

If the sitemap is already listed, you can request a re-crawl by opening the sitemap and using “Resubmit” or similar, or by submitting the same URL again.

## Sitemap URL

- **Live:** https://sailingsa.co.za/sitemap.xml  
- Served dynamically by the API; includes home, about, sailors, **classes** (`/class/{id}-{slug}`), and regattas.
