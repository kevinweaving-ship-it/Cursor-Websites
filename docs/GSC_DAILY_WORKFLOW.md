# GSC daily loop (retrieval + diagnosis)

Google Search Console **Page Indexing** (Indexing → Pages) is a **web UI report**. There is no public API that lists those cohorts (404, noindex, redirect, 5xx, …). This workflow drives the **existing Mac Chrome session** that is already signed into https://search.google.com/search-console for **https://sailingsa.co.za**.

Code: `sailingsa/tools/gsc_daily/` (`mac_first.sh` on the Mac Mini)  
Data (not git): `~/Library/Application Support/sailingsa/gsc-daily/`

## Daily loop

1. Open authenticated GSC  
2. Read current Page Indexing issue counts  
3. Export Google’s affected/example URLs  
4. Compare with yesterday  
5. Live-test those exact URLs on production  
6. Group genuine defects by root URL pattern  
7. Propose fixes (report only)  
8. Apply **only** previously approved remediation classes — **off until we say so**  
9. Re-test production  
10. Start GSC validation when appropriate — **manual / later**  
11. Track validation on later runs  

First run: steps 1–7 only. **No website, SEO, sitemap, nginx, DB, or API changes.**

## Auth

- Do not ask for the Google password.  
- Do not copy cookies into the repo or `/var/www`.  
- If Google shows login / 2FA, stop at that screen and have Kevin approve in Mac Chrome.

## Manual sitemap resubmit (unchanged)

See `docs/GSC_SITEMAP_RESUBMIT.md`.
