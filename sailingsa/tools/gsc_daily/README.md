# GSC daily workflow (Mac Chrome)

**Primary 24/7 collector is now Ubuntu** — see **`docs/GSC_SERVER_FIRST.md`**. This Mac Chrome path remains the fallback for Page Indexing UI fields the official API does not expose. Do not disable `com.kevinweaving.gsc-daily` until that API exists.

Automates the **existing authenticated Google Search Console web session** on the Mac Mini.

Does **not** use a Page Indexing API (Google does not expose those cohorts).  
Does **not** copy cookies, tokens, or passwords into Git, `/var/www`, or the website.

Priority event URLs (Cape Classic, Lipton, near-term 2026 events) are first on the inspect watchlist. Daily run re-submits `sitemap.xml` (write scope). One-shot: `PYTHONPATH=/opt/sailingsa-gsc python3 -m sailingsa.tools.gsc_daily.inspect_priority`. Generic pages cannot use Google’s Indexing API (JobPosting/BroadcastEvent only). Do not click Validate Fix.

Ubuntu `run_server_daily.py` also writes **`seo_health.json`**: verified Googlebot activity (nginx logs + rDNS/fDNS, 48h; skipped if logs do not cover the window), GSC sitemap last-download/errors (7d; auth gaps are not stale), URL Inspection crawl-vs-index split (not-crawled ≠ crawled-not-indexed), live canonical mismatches only when **both** user and Google URLs still HTTP 200, new REAL defects vs yesterday, and sustained Search Analytics drops (clicks AND impressions vs prior week, 2 consecutive days). Alerts append to the existing WhatsApp block. Replay (no GSC API): `PYTHONPATH=/opt/sailingsa-gsc python3 -m sailingsa.tools.gsc_daily.seo_health --day YYYY-MM-DD`.

## What it does

1. Open the already-signed-in Mac Chrome tab for Search Console  
2. Read **Indexing → Pages** counts  
3. Export / scrape Google’s example URLs per issue  
4. Live-test those exact URLs on https://sailingsa.co.za  
5. Classify: `REAL DEFECT` / `ALREADY FIXED — GOOGLE STALE` / `INTENTIONAL/CORRECT` / `NEEDS HUMAN DECISION`  
6. Group by URL pattern  
7. Compare with yesterday if a previous run exists  

**No website fixes on first run.** Validation clicks stay manual until approved.

## First run (Mac Mini)

Chrome can stay open. The puller talks to the existing window via AppleScript (no second profile, no cookie export).

**Chrome requirement:** View → Developer → **Allow JavaScript from Apple Events** must be on. If it is off, `mac_first.sh` stops with that instruction — do not paste the Google password into chat.

Live property is **sc-domain:sailingsa.co.za**. Drilldowns use GSC `item_key` values in `config.py`.

```bash
cd ~/Desktop/sailingsa-clean   # or Project 6
git fetch origin cursor/gsc-daily-workflow-baea
git checkout cursor/gsc-daily-workflow-baea
bash sailingsa/tools/gsc_daily/mac_first.sh
```

If Google shows login / 2FA / account picker: **approve it yourself**. Do not type the password into chat. Re-run the script after you are in Search Console.

## Where data is stored

`~/Library/Application Support/sailingsa/gsc-daily/YYYY-MM-DD/`

- `gsc_pull.json` — counts, example URLs, export paths  
- `*_probes.json` — live HTTP/canonical/robots  
- `REPORT.md` / `report.json`  
- CSVs if GSC Export worked  

Never commit this folder.

## Optional CDP

Only if AppleScript cannot drive the tab: quit Chrome, then `bash sailingsa/tools/gsc_daily/start_chrome_debug.sh` (same profile, port 9222).
