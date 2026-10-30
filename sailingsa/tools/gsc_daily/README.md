# GSC daily workflow (Mac Chrome)

Automates the **existing authenticated Google Search Console web session** on the Mac Mini.

Does **not** use a Page Indexing API (Google does not expose those cohorts).  
Does **not** copy cookies, tokens, or passwords into Git, `/var/www`, or the website.

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
