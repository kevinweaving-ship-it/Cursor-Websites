# Accreditation quals – weekly scraper (SAS ID / member_roles)

Keeps **member_roles** in sync with who has which accreditation at [SAS accreditation finder](https://www.sailing.org.za/accreditation-finder/).  
*(SAS ID scraper is separate; see api.py run_daily_scrape / docs for reference. This doc is quals only.)*

---

## Layman's confirmation

- **Qual scrape is done** – We take the list of who has which qual (from the accreditation finder, via CSV export).
- **It is compared to what's already in the DB** – The script reads the `member_roles` table and only adds rows we don't already have.
- **We list the new SAS ID quals we don't have** – That list is written to **`new_quals_report_YYYYMMDD.txt`** (SAS ID + qual/role). Same list is what gets applied when you run the sync SQL.

So: scrape → compare to DB → list new quals (and generate SQL to add them).

---

## Qual pipeline – complete flow

1. **Get data** → CSV export from [accreditation finder](https://www.sailing.org.za/accreditation-finder/) (or use scraper with `--csv` when you have one). Save as `sailingsa/deploy/accreditation_export.csv` (columns: `sas_id` or "SA Sailing ID", and `framework` or "Accreditation framework").
2. **Run scraper** → `python3 sailingsa/deploy/scrape_accreditation_quals.py --csv sailingsa/deploy/accreditation_export.csv` (optionally set `DB_URL` to diff vs live). Produces `member_roles_sync_YYYYMMDD.sql` and `new_quals_report_YYYYMMDD.txt`.
3. **Apply on live** → `bash sailingsa/deploy/apply-member-roles-live.sh` (uploads SQL and runs psql on server).
4. **Weekly** → Use `bash sailingsa/deploy/run-weekly-accreditation-sync.sh` (with CSV in place). On server use `--on-server` and cron; script uses venv python so DB diff works.

**Done when:** CSV is updated (or exported) → weekly script runs → SQL applied → `new_quals_report_*.txt` shows what was added. No API restart needed (member_roles is data only).

---

## One-off run

1. **Get data** (either export CSV from the finder or use scraper when HTTP is supported):
   ```bash
   python3 sailingsa/deploy/scrape_accreditation_quals.py --csv sailingsa/deploy/accreditation_export.csv
   ```
   Or without CSV (script will try to fetch from site; if it fails, use CSV):
   ```bash
   export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"  # or your live URL
   python3 sailingsa/deploy/scrape_accreditation_quals.py
   ```
2. **Apply on live** (per SSH readme):
   ```bash
   bash sailingsa/deploy/apply-member-roles-live.sh
   ```

## Weekly auto-run (automatic going forward)

**Single script** runs scraper then apply: `sailingsa/deploy/run-weekly-accreditation-sync.sh`

**From your machine** (every Sunday 03:00 – cron on your Mac/local):
```bash
0 3 * * 0 cd /path/to/Project\ 6 && bash sailingsa/deploy/run-weekly-accreditation-sync.sh
```
Put a CSV at `sailingsa/deploy/accreditation_export.csv` (export from accreditation finder) before the first run, or update it weekly.

**On the live server** (recommended: run where the DB is, no SSH needed):
1. Copy deploy scripts to the server (e.g. with your normal deploy, or once):
   ```bash
   scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/run-weekly-accreditation-sync.sh sailingsa/deploy/scrape_accreditation_quals.py root@102.218.215.253:/var/www/sailingsa/deploy/
   ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "chmod +x /var/www/sailingsa/deploy/run-weekly-accreditation-sync.sh"
   ```
2. Put a CSV on the server (e.g. upload after you export from the finder):
   ```bash
   scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/accreditation_export.csv root@102.218.215.253:/var/www/sailingsa/deploy/accreditation_export.csv
   ```
3. Add cron on the server (run as root or the app user):
   ```bash
   ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253
   crontab -e
   # Add this line (every Sunday 03:00 UTC):
   0 3 * * 0 /var/www/sailingsa/deploy/run-weekly-accreditation-sync.sh --on-server >> /var/www/sailingsa/deploy/logs/weekly-accreditation-sync.log 2>&1
   ```
4. To refresh data weekly: replace `accreditation_export.csv` on the server (or re-export from the finder and re-upload) before the cron runs, or add a separate job that fetches/scrapes the finder and writes that CSV.

Logs: `sailingsa/deploy/logs/weekly-accreditation-sync.log` (and on server: `/var/www/sailingsa/deploy/logs/`).

## Checksum and "what new we did not have"

To checksum **our table** and (if you have a CSV) **scraped/source** and list **what new we did not have**:

```bash
# On server (has DB and psycopg2 in venv):
export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
/var/www/sailingsa/api/venv/bin/python3 /path/to/scrape_accreditation_quals.py --checksum-only --csv /path/to/accreditation_export.csv --output-dir /tmp
```

Output: `quals_checksum_report_YYYYMMDD.txt` with

- **OUR TABLE**: count and SHA256 of all (person_key, role_code) in `member_roles`
- **SCRAPED/SOURCE**: count and SHA256 of the CSV (or fetch) list
- **NEW (we did not have)**: count, SHA256, and full list of (sas_id, role_code) to add

**Live scrape:** The scraper can fetch directly from the accreditation finder (GET per framework with a browser User-Agent; results are in the HTML). So you can run without a CSV: `python3 sailingsa/deploy/scrape_accreditation_quals.py`. If the site blocks the request (403), use a CSV export instead. Latest run: our table **225** rows, checksum in `sailingsa/deploy/quals_checksum_report_20260307.txt`.

## CSV export format

**How to get the CSV:** Open [accreditation finder](https://www.sailing.org.za/accreditation-finder/), run searches (e.g. by framework), export or copy results. Save as CSV with the columns below. One row per person per qual.

If the site has no API or bulk export, use manual export with at least:

- **sas_id** (or “SA Sailing ID”) – numeric SAS ID  
- **framework** or **accreditation** (or “Accreditation framework”) – e.g. “Judge-Club Level”, “Race Officer-National”

Optional: first_name, last_name. The script maps framework labels to our `roles.role_code` and only inserts rows that are not already in `member_roles`.

## Files

| File | Purpose |
|------|--------|
| `sailingsa/deploy/run-weekly-accreditation-sync.sh` | **Weekly auto script:** run scraper then apply; use `--on-server` when cron runs on live server |
| `sailingsa/deploy/scrape_accreditation_quals.py` | Scraper: load/fetch (sas_id, qual), diff vs DB, write `member_roles_sync_YYYYMMDD.sql` and `new_quals_report_*.txt` |
| `sailingsa/deploy/apply-member-roles-live.sh` | Apply latest `member_roles_sync_*.sql` on live (see SSH_LIVE.md) |
| `member_roles_sync_*.sql` | Generated INSERTs; `ON CONFLICT DO UPDATE` so safe to re-run |
| `sailingsa/deploy/logs/weekly-accreditation-sync.log` | Log from each weekly run |

## DB

- **member_roles**: `(person_key, role_code, status, source, updated_at)`. `person_key` = `SAS:<sas_id>`.
- **roles**: defines `role_code` (e.g. JUDGE_CLUB, RO_NAT). Scraper only inserts role_codes that exist in `roles`.
