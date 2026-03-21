# Scrape automation schedule and SAS ID Registry checklist

## Locate the SAS ID Registry scraper (run on server)

SSH to the server and run these in order. Or run the block from your machine (with key).

**One-shot from your machine (all checks):**
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "
echo '=== 1) Find script file ==='
find /var/www/sailingsa -type f -iname '*registry*' 2>/dev/null
echo ''
echo '=== 2) Deploy folder ==='
ls -la /var/www/sailingsa/deploy/
echo ''
echo '=== 3) Cron ==='
crontab -l 2>/dev/null || echo '(no crontab)'
echo ''
echo '=== 4) Logs ==='
ls -la /var/www/sailingsa/deploy/logs/ 2>/dev/null | head -30
echo ''
echo '=== 5) Database batches (last 10) ==='
psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -c \"SELECT batch_id, started_at, completed_at, valid_count, error_count FROM sas_scrape_batches ORDER BY started_at DESC LIMIT 10;\" 2>/dev/null || echo '(table missing or psql failed)'
echo ''
echo '=== 6) Grep for registry scraper references ==='
grep -R 'sas_registry\|registry scrape\|run-sas-id-registry' /var/www/sailingsa --include='*.py' --include='*.sh' -l 2>/dev/null || true
"
```

**If you are already on the server** (after `ssh root@102.218.215.253`):

```bash
# 1) Find the script file
find /var/www/sailingsa -type f -iname "*registry*"

# 2) Deploy folder
ls /var/www/sailingsa/deploy

# 3) Cron
crontab -l

# 4) Logs
ls /var/www/sailingsa/deploy/logs

# 5) Database batches (live DB is sailors_master)
psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -c "SELECT batch_id, started_at, completed_at, valid_count, error_count FROM sas_scrape_batches ORDER BY started_at DESC LIMIT 10;"

# 6) Code references
grep -R "registry scrape" /var/www/sailingsa --include='*.py' --include='*.sh' 2>/dev/null || true
grep -R "sas_registry" /var/www/sailingsa --include='*.py' --include='*.sh' 2>/dev/null || true
```

**Expected if everything is in place:**

| Check | Expected |
|-------|----------|
| Script | `/var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh` |
| Cron | Line containing `run-sas-id-registry-scrape.sh` (e.g. daily 02:00) |
| Log | `/var/www/sailingsa/deploy/logs/sas-id-registry-scrape.log` |
| Batches | Rows in `sas_scrape_batches` with `batch_id` not like `ACCREDITATION_SYNC%` (e.g. registry batch IDs) |

**If script missing:** Scraper was never deployed (no `run-sas-id-registry-scrape.sh` in this repo; may exist only on server or in another branch).  
**If cron empty for registry:** Automation was never scheduled.  
**If log missing:** Scraper has never run.  
**If no registry batches:** Scraper has never run or table not yet used.

**Typical locations:**

- Script: `/var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh`
- Python (if any): e.g. `/var/www/sailingsa/deploy/scrape_sas_id_registry.py` or under `/var/www/sailingsa/scripts/`

---

## A. Server checklist (SAS ID Registry scraper)

If the dashboard shows **Last Run —**, **New Records —**, **Batch —** for **SAS ID Registry**, run the locate commands above, then use the checklist below.

### 1. Script exists

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "ls -la /var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh"
```

**Expected:** Script present.  
**If missing:** Scraper was never deployed (script not in repo or not copied to server).

### 2. Cron job

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "crontab -l"
```

**Expected entry (example):**

```cron
0 2 * * * /var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh --on-server >> /var/www/sailingsa/deploy/logs/sas-id-registry-scrape.log 2>&1
```

**If missing:** Scraper was never scheduled; add the line above (or use the cron.d file below).

### 3. Log file

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "ls -la /var/www/sailingsa/deploy/logs/sas-id-registry-scrape.log"
```

**Expected:** Log file exists and has recent content if the scraper has run.  
**If log does not exist:** Scraper has never run.

---

## B. Why the dashboard shows nothing for SAS ID Registry

The dashboard **Auto Scrapes Status** card reads **SAS ID Registry** from:

- **Table:** `sas_scrape_batches`
- **Filter:** `batch_id NOT LIKE 'ACCREDITATION_SYNC%'` (so only registry batches, not accreditation).

If the registry scraper never runs (or was never deployed/scheduled):

- No rows exist in `sas_scrape_batches` for registry runs.
- So the dashboard shows: **Last Run —**, **New Records —**, **Batch —**.

**Conclusion:** Fix deployment and cron (script on server + cron entry); after the scraper runs at least once, the dashboard will show Last Run, New Records, and Batch ID.

**Expected system once fixed:** The Auto Scrapes table should show these three rows:

- **SAS ID Registry Scrape** — Last Run, Next Run, Batch from `sas_scrape_batches` (registry batches) or `scrape_runs` (sas_registry)
- **SAS Events List Scrape** — from events cron / scrape_runs
- **SAS Accreditation Sync** — from accreditation cron / sas_scrape_batches ACCREDITATION_SYNC% or scrape_runs

---

## C. Recommended daily schedule (no collisions)

Run scrapers in this order so they don’t overlap and logs are predictable:

| Time (UTC) | Scraper              | Script / note |
|------------|----------------------|---------------|
| **02:00**  | SAS ID Registry      | `run-sas-id-registry-scrape.sh --on-server` |
| **03:00**  | SAS Events list      | `run-daily-events-scrape.sh --on-server` |
| **04:00**  | SAS Accreditation    | `run-weekly-accreditation-sync.sh --on-server` (often run weekly, e.g. Sunday) |

Registry first (02:00), then Events (03:00), then Accreditation (04:00 or weekly).

---

## D. Complete scrape automation schedule (all scrapers)

Use this as the single reference for cron so all scrapers run in the correct order without collisions.

**Suggested cron.d file** (e.g. `/etc/cron.d/sailingsa_scrapes` on the server):

```cron
# SailingSA scrapes — order: Registry 02:00, Events 03:00, Accreditation 04:00 (weekly)
SHELL=/bin/bash
PATH=/usr/bin:/bin
0 2 * * * root /var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh --on-server >> /var/www/sailingsa/deploy/logs/sas-id-registry-scrape.log 2>&1
0 3 * * * root /var/www/sailingsa/deploy/run-daily-events-scrape.sh --on-server >> /var/www/sailingsa/deploy/logs/daily-events-scrape.log 2>&1
0 4 * * 0 root /var/www/sailingsa/deploy/run-weekly-accreditation-sync.sh --on-server >> /var/www/sailingsa/deploy/logs/weekly-accreditation-sync.log 2>&1
```

- **Registry:** daily at 02:00.  
- **Events:** daily at 03:00.  
- **Accreditation:** weekly (Sunday) at 04:00.

Adjust user (`root` vs `www-data`) and paths to match your server. Ensure `DB_URL` (and any other env) is available to the scripts (e.g. in `/var/www/sailingsa/.env` or systemd).

---

## E. Most likely situation

If the dashboard has always shown nothing for SAS ID Registry:

- **Script created but never added to cron** → scraper works when run manually, but automation was never installed.  
- **Fix:** Add the cron entry (or cron.d file) above and ensure the script exists at `/var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh`.

**Repo:** Script is `sailingsa/deploy/run-sas-id-registry-scrape.sh`; cron file is `sailingsa/deploy/sailingsa_registry_scrape.cron` (02:00 UTC). After deploy, copy script to server and install cron: `sudo cp /var/www/sailingsa/deploy/sailingsa_registry_scrape.cron /etc/cron.d/`.

---

## Reference

- **Dashboard:** https://sailingsa.co.za/admin/dashboard-v3 — Auto Scrapes Status card.
- **Runbook (registry integrity):** `docs/RUNBOOK_SAS_REGISTRY_CATCHUP.md`.
- **SSH and deploy:** `sailingsa/deploy/SSH_LIVE.md`.
- **Existing cron (different job):** `sailingsa/deploy/sailingsa_sas_scrape.cron` runs `sas_member_scrape.py` at 02:30; that is a separate “member finder” job, not the registry scraper that writes to `sas_scrape_batches`.
