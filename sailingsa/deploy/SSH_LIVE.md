# SailingSA Live Server — SSH & Deploy

⚠ **PRODUCTION MODE**  
You are operating on LIVE infrastructure.  
All edits must be deliberate.  
No silent overwrites.  
No baseline restores.  
Confirm path before change.

---

**Server:** `102.218.215.253`  
**User:** `root`  
**Auth:** SSH key preferred (`~/.ssh/sailingsa_live_key`); password fallback for legacy expect scripts.

**Blank hub UI:** Use **`https://sailingsa.co.za/blank.html`** as the canonical URL for hub work and verification. Nginx may also serve the same `blank.html` at **`/`**; see **`sailingsa/deploy/nginx-root-blank-hub.conf`** and the optional split there if root must show a different file.

---

## SSH key setup (one-time; then no password needed)

```bash
# Generate key (if not exists)
ssh-keygen -t ed25519 -f ~/.ssh/sailingsa_live_key -N "" -q

# Copy public key to server (use password once)
sshpass -p 'YOUR_ROOT_PASSWORD' ssh -o StrictHostKeyChecking=no root@102.218.215.253 "mkdir -p /root/.ssh && chmod 700 /root/.ssh"
sshpass -p 'YOUR_ROOT_PASSWORD' ssh -o StrictHostKeyChecking=no root@102.218.215.253 "echo \"$(cat ~/.ssh/sailingsa_live_key.pub)\" >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys"

# Test
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "echo SSH KEY WORKS"
```

---

## Production: deploy all fixes to live (not only local)

**Code and data fixes only take effect on production when you deploy and sync.** Use the commands below (see readme).

1. **Deploy code to live** (api.py, frontend, regatta results HTML — sailor URLs, no broken links, 404 for unknown slugs, sitemap):
   **Preferred (SSH key, no password):**
   ```bash
   bash sailingsa/deploy/deploy-with-key.sh
   ```
   **Or (expect + password):**
   ```bash
   cd sailingsa/frontend
   zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md"
   cd ../..
   expect sailingsa/deploy/push-to-cloud-expect.exp
   ```

2. **Sync regatta 385 data to live** (SAS ID matches, names, so regatta page shows correct sailor links):
   ```bash
   bash sailingsa/deploy/sync-385-local-to-live.sh
   ```
   Or: `python3 sailingsa/deploy/export_regatta_385_data.py` then `expect sailingsa/deploy/sync_regatta_385_to_live.exp`

**Verify on production:** https://sailingsa.co.za/regatta/hyc-cape-classic-2026 — sailor names with SAS ID should be links; no broken sailor URLs.

3. **After deploying bio or api.py: restart API** (required for sailor bio to show):
   ```bash
   ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
   ```
   Expected: `active`. See also **`sailingsa/deploy/BIO_BACKUP_RESTORE.md`** for bio backup/restore.

---

## Deploy api.py with verification (recommended)

**Cursor must deploy the file that was actually edited** (project root `api.py`). The live process runs **`/var/www/sailingsa/api/api.py`**. If deploy only restarts the service without copying the new file into that path, the dashboard and API will still serve old code.

**One-time setup on server:** copy the verified deploy script and make it executable:
```bash
scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/deploy_api_verified.sh root@102.218.215.253:/root/deploy_api_verified.sh
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "chmod +x /root/deploy_api_verified.sh"
```

**Single deploy command (Cursor must use this after every api.py change):**
```bash
# From project root:
scp -i ~/.ssh/sailingsa_live_key api.py root@102.218.215.253:/root/incoming/api.py && \
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "/root/deploy_api_verified.sh"
```

Optional: **`regatta_host_code.py`** next to `api.py` — `api.py` now **falls back inline** if the module is missing, so **scp api.py alone is enough** for deploy. Copying `regatta_host_code.py` is still fine:

```bash
scp -i ~/.ssh/sailingsa_live_key regatta_host_code.py root@102.218.215.253:/root/incoming/regatta_host_code.py && \
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "/root/deploy_api_verified.sh"
```

Update **`/root/deploy_api_verified.sh`** on the server from repo **`sailingsa/deploy/deploy_api_verified.sh`** when it gains the `regatta_host_code.py` copy step; **`/root/deploy_api.sh`** should match **`sailingsa/deploy/deploy_api.sh`** so `auto-dr` and manual `scp` both install the helper next to `api.py`.

### Jinja pages 500 (`/events`, `/stats`, `/about`) after api deploy

Templates must exist on disk under **`/var/www/sailingsa/templates/`** (from the frontend zip unzip). **`journalctl -u sailingsa-api -n 40`** should log: `Jinja template search paths (N): [...]`.

**Bottom line:** ensure **`templates/`** exists on the server **before** relying on the `api.py` Jinja path fix.

#### 1) On the server — verify template file

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  "ls -la /var/www/sailingsa/templates/pages/events.html || echo 'MISSING TEMPLATES'"
```

#### 2) If templates are missing — deploy frontend (run on your machine, project root)

Do **not** run `deploy-with-key.sh` **on the server** (it is not `/root/sailingsa/deploy/deploy-with-key.sh` unless you cloned the repo there). From your laptop:

```bash
bash sailingsa/deploy/deploy-with-key.sh
```

That builds `sailingsa-frontend.zip`, uploads it, and unzips into **`/var/www/sailingsa/`** (creates `templates/`, `index.html`, etc.).

**Server-only fallback** if you already have a zip on the box:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  "cd /var/www/sailingsa && test -f /tmp/sailingsa-frontend.zip && unzip -o /tmp/sailingsa-frontend.zip || echo 'Upload zip first or use deploy-with-key.sh locally'"
```

#### 3) Deploy `api.py` and restart (after templates exist)

```bash
scp -i ~/.ssh/sailingsa_live_key api.py root@102.218.215.253:/root/incoming/api.py && \
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "/root/deploy_api_verified.sh"
```

Or manual copy + restart:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "
  cp /root/incoming/api.py /var/www/sailingsa/api/api.py
  systemctl restart sailingsa-api
  sleep 2
  systemctl is-active sailingsa-api
  journalctl -u sailingsa-api -n 40 --no-pager | grep -i jinja
"
```

#### 4) If still broken

Paste the last 20–40 lines:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "journalctl -u sailingsa-api -n 40 --no-pager"
```

The `&&` in the scp one-liner guarantees the server script runs only if the copy succeeded.

**Or run the full verified script (adds file check + dashboard safeguard):**
```bash
bash sailingsa/deploy/deploy-api-live-verified.sh
```
This script exits with error if the dashboard HTML does not contain "Next Run" (proves new code is served).

**What the server script prints:** Incoming hash, live hash before/after, file timestamp after copy, `systemctl status`, running process (`ps aux`), and full output of `curl -s https://sailingsa.co.za/admin/api/version` (includes `deploy_marker`, `api_start_time`, `pid`). If hashes are identical before and after, the copy did not change the file.

**Required safeguard:** After deploy, confirm new code is live:
```bash
curl -s https://sailingsa.co.za/admin/dashboard-v3 | grep "Next Run"
```
If **empty** → deploy failed; Cursor must stop and report. The script `deploy-api-live-verified.sh` does this and exits 1 if missing.

**Version endpoint** returns `deploy_marker` (bump in api.py after each deploy), `api_start_time`, `pid`, `server_time`. Dashboard header shows Started | PID. New deploy = new PID and new api_start_time.

---

## Deploy Dashboard V2 only (api.py)

If **https://sailingsa.co.za/admin/dashboard-v2** still shows "Blank page. Build here.", the server is running old code. Deploy the current api.py and restart:

**From project root (folder that contains `api.py`):**
```bash
cd /Users/kevinweaving/Desktop/MyProjects_Local/Project\ 6
bash sailingsa/deploy/deploy-dash2-live.sh
```

Then open https://sailingsa.co.za/admin/dashboard-v2 and **hard-refresh (Cmd+Shift+R)**. You must be logged in as admin.

---

## Check SSH

**With key:**
```bash
ssh -i ~/.ssh/sailingsa_live_key -o ConnectTimeout=10 root@102.218.215.253 "echo OK"
```

**Without key (password):**
```bash
ssh -o ConnectTimeout=10 root@102.218.215.253 "echo OK"
```

If you see `OK`, SSH works. If it times out, check your network, VPN, or firewall.

---

## SSH to Live

**With key (recommended):**
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253
```

**Without key:** `ssh root@102.218.215.253` (enter password when prompted).

---

## Live backend immutability and deploy rules (no silent overwrites)

**api.py on PROD is immutable** so it cannot be overwritten by SCP or editor by mistake.

- **Current state:** `chattr +i /var/www/sailingsa/api/api.py` (file is immutable).
- **To change api.py on live:** use the **LIVE EDIT PROTOCOL** in **`sailingsa/deploy/PROD_RULES.md`** (read-only first → snapshot → chattr -i → edit → chattr +i → restart → verify). Summary:

  **1. Timestamped backup (on PROD):**
  ```bash
  cp /var/www/sailingsa/api/api.py \
     /var/www/sailingsa/api/api.py.$(date +%Y%m%d_%H%M%S).bak
  ```

  **2. Unlock:**
  ```bash
  chattr -i /var/www/sailingsa/api/api.py
  ```

  **3. Edit** (sed, scp, or editor).

  **4. Lock and restart:**
  ```bash
  chattr +i /var/www/sailingsa/api/api.py
  systemctl restart sailingsa-api
  ```

  That’s the full cycle. Friction is intentional.

  **Optional full snapshot** (entire api dir): `tar -czf /root/releases/api_$(date +%Y%m%d_%H%M%S).tar.gz -C /var/www/sailingsa api`

**Rule: develop locally, deploy intentionally.** Confirm line count and diff locally; deploy; restart; verify. Never "patch live while debugging".

**Dashboard version:** The admin dashboard header shows `VERSION 2026-03-02-ADV-13K` so you always know what backend version is running.

**Deploy api.py via incoming + script (recommended):** One-time setup: copy `sailingsa/deploy/deploy_api.sh` to server as `/root/deploy_api.sh`, then on server `chmod +x /root/deploy_api.sh` and `mkdir -p /root/incoming`. From then on:
```bash
scp -i ~/.ssh/sailingsa_live_key api.py root@102.218.215.253:/root/incoming/api.py
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "/root/deploy_api.sh"
```
Script backs up to `/root/backups/api.py.TIMESTAMP`, copies from `/root/incoming/api.py` to live, chown, chattr +i, restart. See **`sailingsa/deploy/PROD_RULES.md`** for full steps.

---

## Fix API Timeouts (ERR_CONNECTION_TIMED_OUT)

**Fix API timeouts:**

```bash
expect sailingsa/deploy/fix-live-full.exp
```

This will diagnose, restart sailingsa-api, ensure STATIC_DIR, and reload nginx on the live server.

If API still crashes, rollback to backup api.py:
```bash
expect sailingsa/deploy/fix-live-rollback-api.exp
```

---

## Restart sailingsa-api (from your machine only) — always working on live

**The API never restarts itself.** Restart is done via SSH from your machine. Use this for prod; it always works on live.

**Canonical restart (from project root):**
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "sudo systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
```
Expect output: `active`. If you see `failed` or `inactive`, SSH in and run `journalctl -u sailingsa-api -n 30 --no-pager`.

**Restart and show PID before/after:**
```bash
bash sailingsa/deploy/restart-live.sh
```

**Or manually (with PID check):**
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "systemctl show -p MainPID sailingsa-api --value; sudo systemctl restart sailingsa-api; sleep 2; systemctl show -p MainPID sailingsa-api --value"
```

**Service file on server** must have (see `sailingsa/deploy/sailingsa-api.service`):
- `Restart=always`
- `RestartSec=1`
- `KillSignal=SIGTERM`
- `TimeoutStopSec=5`

After editing the unit on the server: `sudo systemctl daemon-reload` then `sudo systemctl restart sailingsa-api`.

**Only restart when required** (e.g. after deploying api.py, or to recover from a bad state). Do not restart blindly.

**Flow:** SSH in → check status → restart only if needed:
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253
systemctl status sailingsa-api
sudo systemctl restart sailingsa-api   # only when needed
```

---

## DB checks (LIVE, sailors_master)

Run on the server (or via `psql` from your machine if you have DB access). There is **no `review_queue` table**; review counts come from `results` + `ingestion_issues`.

**Core counts:**
```sql
SELECT COUNT(*) FROM classes;
SELECT COUNT(*) FROM sas_id_personal;
```

**Unresolved sailors (review queue – distinct helm_name + sail_number with no SAS ID):**
```sql
SELECT COUNT(*) FROM (
  SELECT 1 FROM results
  WHERE helm_sa_sailing_id IS NULL
    AND (identity_status IS NULL OR identity_status != 'invalid')
    AND helm_name IS NOT NULL AND TRIM(helm_name) != ''
  GROUP BY helm_name, sail_number
) t;
```

**Open class issues (ingestion_issues):**
```sql
SELECT COUNT(*) FROM ingestion_issues WHERE status = 'OPEN';
```
(If `ingestion_issues` is missing, the query will error; that’s expected on older DBs.)

---

## Fix restart permissions (LIVE only)

**Run these steps ON THE LIVE SERVER after SSH as root.** No local changes. No UI.

**1. Confirm hostname**
```bash
hostname
```
Must equal: `vm103zuex.yourlocaldomain.com`

**2. Identify API service user**
```bash
systemctl show -p User sailingsa-api
```
Note the value (e.g. `www-data`).

**3. Create sudoers entry** (replace `<SERVICE_USER>` with the value from step 2)
```bash
sudo bash -c 'echo "<SERVICE_USER> ALL=NOPASSWD: /bin/systemctl restart sailingsa-api" > /etc/sudoers.d/sailingsa-api'
```

**4. Set permissions**
```bash
sudo chmod 440 /etc/sudoers.d/sailingsa-api
```

**5. Test as service user** (replace `<SERVICE_USER>`)
```bash
sudo -u <SERVICE_USER> sudo systemctl restart sailingsa-api
```

**6. Verify PID changes**
```bash
systemctl show -p MainPID sailingsa-api
sudo systemctl restart sailingsa-api
systemctl show -p MainPID sailingsa-api
```
PID must change.

**One-shot script on server** (copy script to server, then run as root):
```bash
# From your machine, run the fix script on LIVE:
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 'bash -s' < sailingsa/deploy/fix-restart-sudoers-on-live.sh
```
Script checks hostname, gets service user, creates `/etc/sudoers.d/sailingsa-api`, chmod 440, tests restart, and prints a short report.

**Report:** Service user, PID before, PID after.

---

## Deploy to Live (Automated)

**From project root — use key (no password):**
```bash
bash sailingsa/deploy/deploy-with-key.sh
```

**Or with expect (password in script):**
```bash
cd sailingsa/frontend
zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md"
cd ../..
expect sailingsa/deploy/push-to-cloud-expect.exp
```

Deploy script / expect:
- Uploads `sailingsa-frontend.zip` to `/tmp/`
- Backs up `/var/www/sailingsa`
- Extracts zip to web root
- Uploads `api.py` and `requirements.txt` to `/var/www/sailingsa/api/`
- Restarts `sailingsa-api` service

---

## Nginx: Required Location Blocks

Ensure `/etc/nginx/sites-enabled/timadvisor` (or sailingsa config) has these **before** `location /`:

- `location ^~ /api/` → proxy to 127.0.0.1:8000
- `location ^~ /profiles/` → proxy to 127.0.0.1:8000 (registration “Find Your Profile” search)
- `location ^~ /auth/` → proxy to 127.0.0.1:8000
- `location = /about` → proxy to 127.0.0.1:8000 (so /about serves about.html)
- `location = /` and `location = /index.html` → proxy to API
- `location ~ ^/sailor/` → proxy to API

Fix /about if missing: `expect sailingsa/deploy/fix-nginx-about.exp`

---

## Paths on Server

| Path | Purpose |
|------|---------|
| `/var/www/sailingsa` | Frontend (index.html, about.html, css/, js/, assets/, favicon-48.png, favicon-192.png) |
| `/var/www/sailingsa/api` | Backend (api.py, requirements.txt, venv) |

---

## Favicon and docroot (why curl matters)

The HTML references **`/favicon-48.png`** and **`/favicon-192.png`**. The deploy script extracts the frontend zip into **`/var/www/sailingsa`**, so those files land at `/var/www/sailingsa/favicon-48.png` and `/var/www/sailingsa/favicon-192.png`. **The curl test confirms they are publicly reachable** — i.e. that nginx is serving static files from that directory. If nginx’s `root` (or equivalent) for sailingsa.co.za points elsewhere, the browser and Google will get 404 for the favicon even though the file exists on disk.

**After deploy, verify:**
```bash
curl -I https://sailingsa.co.za/favicon-48.png
curl -I https://sailingsa.co.za/favicon-192.png
```
**Expected:** `HTTP/1.1 200 OK` and `Content-Type: image/png`.  
**If 404:** nginx docroot mismatch — ensure the server block for sailingsa.co.za uses `root /var/www/sailingsa` (or that static files are served from there).

---

---

## Fix About Popup/Redirect on Live

If `/about` shows the SPA (index.html) instead of the About page on live, the API needs `STATIC_DIR` and nginx needs `location = /about`:

```bash
# Option A: Run expect script (may prompt for password)
expect sailingsa/deploy/fix-about-live.exp

# Option B: SSH and run manually
ssh root@102.218.215.253
# On server:
grep -q STATIC_DIR /etc/systemd/system/sailingsa-api.service || \
  sed -i '/WorkingDirectory=/a Environment="STATIC_DIR=/var/www/sailingsa"' /etc/systemd/system/sailingsa-api.service
systemctl daemon-reload && systemctl restart sailingsa-api

# Then apply nginx /about fix:
bash /tmp/fix-nginx-about.sh   # (upload first: scp sailingsa/deploy/fix-nginx-about.sh root@102.218.215.253:/tmp/)
# Or: expect sailingsa/deploy/fix-nginx-about.exp
```

**Why:** The API serves `/about` from `STATIC_DIR` + `about.html`. Without `STATIC_DIR`, it looks in the wrong folder and returns 404. Nginx then falls through to SPA.

---

## SAS classes (scrape and apply on live)

Adds `sas_source_url`, `sas_contact_email`, and `class_url` to `classes` and seeds from https://www.sailing.org.za/what-we-do/sasclasses.

**1. Generate SQL** (from project root):
```bash
python3 sailingsa/deploy/scrape_sas_classes.py
```
Writes `sailingsa/deploy/classes_sas_columns.sql`.

**2. Apply on live** (scp + psql + restart, same pattern as fix-regatta-302):
```bash
bash sailingsa/deploy/apply-classes-sas-live.sh
```
With key: script uses `-i ~/.ssh/sailingsa_live_key`. If DB password fails, get URL from server: `ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "grep -E 'DB_URL|DATABASE' /etc/systemd/system/sailingsa-api.service"`.

**Manual** (if script fails):
```bash
scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/classes_sas_columns.sql root@102.218.215.253:/tmp/
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -f /tmp/classes_sas_columns.sql && systemctl restart sailingsa-api && systemctl is-active sailingsa-api"
```

---

## SAS accreditation quals (weekly scraper – member_roles)

Keeps SAS ID / quals up to date from https://www.sailing.org.za/accreditation-finder/. **Reuse weekly.**

**1. Generate SQL** (from project root; use CSV if site has no API):
```bash
python3 sailingsa/deploy/scrape_accreditation_quals.py --csv sailingsa/deploy/accreditation_export.csv
# Or without CSV (script tries HTTP): set DB_URL then run scrape_accreditation_quals.py
```
Writes `sailingsa/deploy/member_roles_sync_YYYYMMDD.sql`.

**2. Apply on live:**
```bash
bash sailingsa/deploy/apply-member-roles-live.sh
```
Uses latest `member_roles_sync_*.sql`; no API restart needed.

**Weekly auto-run:** **Live cron is installed:** every Sunday 03:00 UTC the server runs `run-weekly-accreditation-sync.sh --on-server` (fetch from accreditation finder, diff vs `member_roles`, apply SQL). No CSV needed. Log: `/var/www/sailingsa/deploy/logs/weekly-accreditation-sync.log`. From local: `bash sailingsa/deploy/run-weekly-accreditation-sync.sh`. See **`docs/ACCREDITATION_QUALS_WEEKLY.md`**.

---

## SAS events list (daily scrape + DB)

Scrape [sailing.org.za/events/](https://www.sailing.org.za/events/) (all past + upcoming pages). Data is written to CSV and, when `DB_URL` is set, upserted into the `events` table.

- **Events table:** Run migrations `database/migrations/145_events_table.sql` and `146_events_list_scrape_columns.sql` on live DB once. Then load CSV: `python3 load_events_csv_to_db.py --csv sailingsa/deploy/sas_events_list.csv` (requires `DB_URL`).
- **Audit page (live):** https://sailingsa.co.za/admin/events-audit — view/audit events (Admin only).
- **Run once:** `bash sailingsa/deploy/run-daily-events-scrape.sh` (scrape with `--no-detail`; if `DB_URL` set, runs loader and updates `events`). Writes `sailingsa/deploy/sas_events_list.csv` and `sas_events_list_YYYYMMDD.csv`.
- **Daily auto:** Cron e.g. `0 4 * * * /var/www/sailingsa/deploy/run-daily-events-scrape.sh --on-server >> /var/www/sailingsa/deploy/logs/daily-events-scrape.log 2>&1`. On server: copy `scrape_sas_events_list.py`, `load_events_csv_to_db.py`, and `run-daily-events-scrape.sh` to `/var/www/sailingsa/deploy/`; set `DB_URL` in env so the loader runs after each scrape.
- See **`docs/EVENTS_TABLE_AND_SCRAPE.md`**.

---

## Sync Regatta 385 (Table Data Only)

Keeps live 385 results identical to local. Use after any fleet amendments (420, Hobie, ILCA 4/6/7, Mirror, Optimist A/B, Sonnet).

**One command** (export + sync):
```bash
bash sailingsa/deploy/sync-385-local-to-live.sh
```

**Or step by step:**
```bash
# 1. Export from local DB (run first after amendments)
python3 sailingsa/deploy/export_regatta_385_data.py

# 2. Push to live
expect sailingsa/deploy/sync_regatta_385_to_live.exp
```

**Safe & stable:**
- Only touches regatta 385 data (no HTML/API changes)
- Transactional SQL (BEGIN/COMMIT – all-or-nothing)
- Restarts sailingsa-api after apply
- No schema changes – same columns as local

**Manual** (if expect fails):
```bash
scp sailingsa/deploy/regatta_385_sync.sql root@102.218.215.253:/tmp/
ssh root@102.218.215.253 "psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -f /tmp/regatta_385_sync.sql && systemctl restart sailingsa-api"
```

**Fix 4563 on live** (Sail 1311 Optimist B = Mason Guthrie, remove Gordon’s SAS ID so his profile stops showing that entry). From project root:

**One command (expect, uses password in script):**
```bash
expect sailingsa/deploy/apply-patch-4563-live.exp
```

**Manual (scp + ssh):**
```bash
scp sailingsa/deploy/patch_4563_mason_optimist_b.sql root@102.218.215.253:/tmp/
ssh root@102.218.215.253 "psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -f /tmp/patch_4563_mason_optimist_b.sql && systemctl restart sailingsa-api"
```
With key: add `-i ~/.ssh/sailingsa_live_key` to both `scp` and `ssh`.

**Verify:** Gordon Guthrie’s profile must not show Sail No 1311: https://sailingsa.co.za/sailor/gordon-guthrie-5820

**Check what’s on live for 4563** (Gordon’s SAS ID must not be there):
```bash
expect sailingsa/deploy/verify_4563_live.exp
```
You should see `helm_name = Mason Guthrie`, `helm_sa_sailing_id` empty. If you see `5820`, run the apply-patch command above.

---

## Fix regatta 302 NULL class_id (Sonnet Nationals)

Sets `results.class_id` from `classes` where it is NULL for regatta 302 so class links work.

**One command** (from project root, uses SSH key):
```bash
bash sailingsa/deploy/fix-regatta-302-class-id-live.sh
```

**Manual** (if script fails e.g. DB password; use same DB URL as sailingsa-api):
```bash
scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/fix-regatta-302-class-id.sql root@102.218.215.253:/tmp/
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -f /tmp/fix-regatta-302-class-id.sql && systemctl restart sailingsa-api"
```
If password auth fails, get the real URL from the server: `ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "grep -E 'DB_URL|DATABASE' /etc/systemd/system/sailingsa-api.service"` and use that in the `psql` command.

**Verify:** `SELECT COUNT(*) FROM results WHERE regatta_id = '302-2025-sonnet-nationals-results' AND class_id IS NULL;` must return 0.

---

## Run read-only query on live DB (regatta 385)

Raw psql output from live `sailors_master`:

```bash
expect sailingsa/deploy/query-live-regatta-385.exp
```

Runs: `SELECT regatta_id, result_status, as_at_time, start_date, end_date FROM regattas WHERE regatta_id = '385-2026-hyc-cape-classic';`

---

## Verify Sailor Links (SSH or curl)

**Debug a broken sailor link (SSH):**

```bash
# 301 from ?sas_id= to /sailor/<slug>
curl -sI "https://sailingsa.co.za/?sas_id=18020"
# Expect: 301, Location: https://sailingsa.co.za/sailor/...

# /sailor/<slug> returns 200
curl -sI "https://sailingsa.co.za/sailor/ben-henshilwood"
# Expect: 200

# Resolve API (sas_id)
curl -s "https://sailingsa.co.za/api/sailor/resolve?sas_id=18020"
# Expect: JSON with slug, canonical_url

# Resolve API (slug) – sailors in results but not sas_id_personal now work
curl -s "https://sailingsa.co.za/api/sailor/resolve?slug=tom-henshilwood-16401"
# Expect: JSON or 404 (404 if sailor has no results)
```

To debug a specific broken sailor link via SSH:

```bash
ssh root@102.218.215.253
# On server (replace SLUG with the broken slug, e.g. tom-henshilwood-16401):
psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -c \
  "SELECT sa_sailing_id::text, full_name FROM sas_id_personal WHERE sa_sailing_id::text = '16401';"
psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -c \
  "SELECT helm_name, helm_sa_sailing_id FROM results WHERE helm_sa_sailing_id::text = '16401' LIMIT 3;"
```

---

## Sitemap (static file, event-driven rebuild)

**SITEMAP ARCHITECTURE — FROZEN (Mar 2026).** Lock uses `fcntl` (advisory lock); no file-existence check, no manual delete. OS releases lock automatically when process exits — no stale file risk. Before `os.replace()` the builder checks `<urlset` exists and URL count > 0 to prevent accidental empty overwrite.

**Authority:** Nginx serves `/var/www/sailingsa/static/sitemap.xml`. No dynamic API generation. Rebuild runs only after results ingestion, regatta `result_status` update, or regatta create/edit (lock prevents concurrent rebuilds).

**One-time verification on production** (after deploy or when checking SEO):

```bash
# From project root on your machine: python3 sailingsa/scripts/build_sitemap.py (with DB_URL set).
# On server: use venv (see Manual rebuild below) then:
# grep -c '<url>' /var/www/sailingsa/static/sitemap.xml
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "grep -c '<url>' /var/www/sailingsa/static/sitemap.xml"
```

**Spot-check lastmod (no current_date; no ingestion contamination):**

1. **One regatta-result URL** — `<lastmod>` must match that regatta’s `regattas.end_date` (or `start_date` if `end_date` is NULL).
2. **One sailor URL** — `<lastmod>` must match the latest regatta end_date for that sailor (helm/crew in results).
3. **One class URL** — `<lastmod>` must match the latest regatta end_date for that class.

**IMPORTANT: Always use `/var/www/sailingsa/api/venv/bin/python3` for manual sitemap rebuild on the server.** Set `PYTHONPATH=/var/www/sailingsa` so the `sailingsa` package is found. Use the real `DB_URL` from `cat /etc/systemd/system/sailingsa-api.service` (password has no `!` on live).

**Manual rebuild on server** (e.g. after admin corrects `regattas.end_date`). When server is reachable, run this exact clean sequence:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253

cd /var/www/sailingsa
export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
export SITEMAP_STATIC_DIR=/var/www/sailingsa/static
export PYTHONPATH=/var/www/sailingsa
/var/www/sailingsa/api/venv/bin/python3 sailingsa/scripts/build_sitemap.py

grep -c '<lastmod>' /var/www/sailingsa/static/sitemap.xml
head -n 40 /var/www/sailingsa/static/sitemap.xml
```

**Expected:** `<lastmod>` count > 0; each `<url>` block contains `<lastmod>YYYY-MM-DD</lastmod>`. Once run, sitemap system is fully live-correct.

**Important:** If a regatta’s `end_date` is corrected by admin, run a sitemap rebuild so `<lastmod>` stays correct. If results are re-imported but dates unchanged, slug and lastmod must remain unchanged (SEO-stable).

---

## Sitemap final hardening checklist (do not skip)

**1. Rebuild only on write events**

- **Called after:** Results ingestion commit (e.g. `add_regatta_385_420_fleet.py`), and should be called after regatta created, regatta edited (including date correction), and `result_status` updated in any script that does those writes.
- **Never called in:** GET routes, login, any page view, any read-only DB query. The `/sitemap.xml` route only serves the static file; it does not call the builder.

**2. Verify no orphan regatta URLs**

Expected: sitemap regatta count = DB count of regattas that have `result_status` and a non-null date.

```bash
# On server (or local with DB_URL): expected regatta count (excludes NULL lastmod)
psql "$DB_URL" -t -c "SELECT COUNT(*) FROM regattas WHERE result_status IS NOT NULL AND COALESCE(end_date, start_date) IS NOT NULL;"

# Regatta entries in sitemap (should match)
grep -c '/regatta/' /var/www/sailingsa/static/sitemap.xml
```

Counts must match.

**3. Sailor MAX lastmod spot test**

Pick one sailor’s SA ID (e.g. `XXXX` from a sailor URL in the sitemap). Then:

```sql
SELECT MAX(COALESCE(rg.end_date, rg.start_date))
FROM regattas rg
JOIN results r ON rg.regatta_id = r.regatta_id
WHERE r.helm_sa_sailing_id::text = 'XXXX'
   OR r.crew_sa_sailing_id::text = 'XXXX';
```

The result must match that sailor’s `<lastmod>` in the sitemap exactly.

**4. Lock behaviour (concurrent runs)**

- Open two shells. In both, run: `/var/www/sailingsa/api/venv/bin/python3 sailingsa/scripts/build_sitemap.py` (with `DB_URL` set; from `/var/www/sailingsa`).
- First run builds and exits 0. Second run must exit cleanly without corrupting the file (lock exists → skips; or waits and then builds after first removes lock). No partial/corrupt sitemap.

**5. GSC submission after production rebuild**

1. Rebuild on production (see “Manual rebuild on server” above).
2. Open Google Search Console → Sitemaps.
3. Resubmit `https://sailingsa.co.za/sitemap.xml`.
4. Check that “Last read” timestamp updates.
5. Over the next 48h, monitor “Discovered – currently not indexed” if desired.

If all of the above pass, the sitemap system is final and frozen: no drift, no dynamic generation, no current_date, SEO-safe.

**One final professional check (optional but recommended)** — Run once in production (on server, use venv Python):

```bash
# On server, from /var/www/sailingsa:
/var/www/sailingsa/api/venv/bin/python3 sailingsa/scripts/build_sitemap.py
# Then inspect recent logs (API or script output):
# - Success: "Sitemap rebuilt successfully at <timestamp> — URL count: <n>"
# - URL count matches: grep -c '<url>' /var/www/sailingsa/static/sitemap.xml
# - No warnings: no "refused to write invalid/empty" or "write failed"
```

If the build was triggered by ingestion/API, check `journalctl -u sailingsa-api -n 50` (or your app log) for the same success line and absence of replace-skipped warnings.

**Operational note (future evolution):** If regatta volume grows heavily and the sitemap exceeds ~50,000 URLs, the next step would be a sitemap index plus chunked sitemap files — same architecture (static-only, event-driven, DB-authoritative dates, atomic write, advisory lock), same locking model. For now, a single file is correct. This is infrastructure, not “just a sitemap.”

---

## Results PDFs (regatta storage)

**Source of truth (Mac):**  
`/Users/kevinweaving/Desktop/MyProjects_Local/My Fourth Project/results/`  
Structure: `results/<year>/<event-folder>/<filename>.pdf` (e.g. `results/2022/2022-hobie-14-nationals/ka0k7kptyfklnujf.pdf`). ~410 PDFs. Server backups (`/var/www/sailingsa.backup.*/results`) do **not** contain PDFs (only `full.html`/`lite.html`).

**Target on LIVE:**  
`/var/www/sailingsa/results/`  
DB `regattas.local_file_path` must be **relative** only: `results/2025/folder/filename.pdf`. No absolute paths, no Mac paths, no HTML in that column.

**Deploy archive (from your Mac):**
```bash
# 1. Ensure target exists on server
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "mkdir -p /var/www/sailingsa/results"

# 2. Rsync full archive (dry-run first)
rsync -avzn --delete -e "ssh -i ~/.ssh/sailingsa_live_key" "/Users/kevinweaving/Desktop/MyProjects_Local/My Fourth Project/results/" root@102.218.215.253:/var/www/sailingsa/results/

# 3. Real run (remove -n when ready)
rsync -avz --delete -e "ssh -i ~/.ssh/sailingsa_live_key" "/Users/kevinweaving/Desktop/MyProjects_Local/My Fourth Project/results/" root@102.218.215.253:/var/www/sailingsa/results/

# 4. Fix ownership
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "chown -R www-data:www-data /var/www/sailingsa/results"
```

**Verify after deploy:**
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "find /var/www/sailingsa/results -type f -name '*.pdf' | wc -l"
```
Expect hundreds. Then re-run existence check from server with base `/var/www/sailingsa` (see earlier validation: `psql ... -t -c "SELECT local_file_path FROM regattas WHERE ..." | while read file; do [ ! -f "/var/www/sailingsa/\$file" ] && echo "MISSING: \$file"; done`).

**Bad row (fixed):** Regatta `342-2025-sas-mirror-national-championship-2025` had `local_file_path` = Mac path `.../regatta-admin-V22.html`. Cleared: `local_file_path = NULL`, `file_type = NULL`.

---

## Other Docs

- **BACKUP_AND_PROOF.md** — Backup locations and live vs local alignment (proof)
- **DEPLOY_SLUG_COMMANDS.md** — Manual deploy steps (scp + ssh)
- **LIVE_FIX_NOW.md** — Fix API/auth not proxying
- **push-to-cloud-expect.exp** — Automated deploy (includes STATIC_DIR + nginx /about)
