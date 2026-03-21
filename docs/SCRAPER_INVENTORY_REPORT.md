# Scraper inventory and status report

**Generated:** From codebase scan + live server checks (deploy dir, cron, DB).

---

## 1. Scraper inventory (codebase vs server)

| Scraper | Script (codebase) | Script on server | Cron schedule | Target table (intended) | Target table (actual) |
|--------|--------------------|------------------|---------------|-------------------------|------------------------|
| **SAS Events Scrape** | `scrape_sas_events_list.py` + `run-daily-events-scrape.sh` | **NOT INSTALLED** in `/var/www/sailingsa/deploy/` | **None** on server | `events` | `events` (961 rows; loaded in past run) |
| **SAS Qualifications (Accreditation)** | `scrape_accreditation_quals.py` + `run-weekly-accreditation-sync.sh` | **Installed** in deploy/ | **Weekly** Sun 03:00 UTC | `member_roles` | `member_roles` (950 rows) |
| **SAS ID Registry** | `sailingsa/scripts/sas_member_scrape.py` (writes `sas_id_personal`) | **Installed** at `/var/www/sailingsa/scripts/sas_member_scrape.py` | **Daily** 02:30 UTC (`/etc/cron.d/sailingsa_sas_scrape`) | Docs say `sas_id_registry`; code uses **`sas_id_personal`** | `sas_id_personal` (28,424 rows) |
| **SAS Associations Scrape** | **Not found** in repo | **NOT INSTALLED** | — | `associations` | **Table `associations` does not exist** on live |
| **SAS Clubs Scrape** | **Not found** (future) | **NOT INSTALLED** | — | `clubs` | `clubs` table exists; no scraper |

---

## 2. Server deploy directory (`/var/www/sailingsa/deploy/`)

| Script / file | Status |
|---------------|--------|
| Events: `run-daily-events-scrape.sh`, `scrape_sas_events_list.py`, `load_events_csv_to_db.py` | **NOT INSTALLED** |
| Qualifications: `run-weekly-accreditation-sync.sh`, `scrape_accreditation_quals.py` | **Present** |
| SAS ID incremental | Script is in **`/var/www/sailingsa/scripts/sas_member_scrape.py`** (not under deploy/). No script named “incremental_sas_registry_scrape” in repo. |
| Associations scraper | **NOT INSTALLED** (no script in repo) |

---

## 3. Automation (cron on live)

| Scraper | Schedule | Source |
|---------|----------|--------|
| **Events** | **None** | No cron entry for events scrape. |
| **Qualifications** | **Weekly** Sun 03:00 UTC | `crontab -l`: `0 3 * * 0 /var/www/sailingsa/deploy/run-weekly-accreditation-sync.sh --on-server >> .../logs/weekly-accreditation-sync.log 2>&1` |
| **SAS ID** | **Daily** 02:30 UTC | `/etc/cron.d/sailingsa_sas_scrape`: `30 2 * * * www-data .../scripts/sas_member_scrape.py >> /var/log/sailingsa_sas_scrape.log 2>&1` |
| **Associations** | **None** | No scraper. |
| **Clubs** | **None** | Future. |

---

## 4. Target tables and row counts (live DB)

| Table | Exists | Row count (live) | Written by |
|-------|--------|------------------|------------|
| `events` | Yes | **961** | Events scraper (when run; scripts not currently on server) |
| `member_roles` | Yes | **950** | Qualifications scraper ✓ |
| `sas_id_personal` | Yes | **28,424** | SAS ID scraper (`sas_member_scrape.py`) ✓ |
| `sas_scrape_batches` | **No** | — | Not on live; used in codebase for “SAS ID Registry” dashboard row (batch log). |
| `sas_id_registry` | **No** | — | Not in migrations; codebase uses `sas_id_personal`. |
| `associations` | **No** | — | Not in migrations. |
| `race_results` | **No** | — | Not on live (historical results future). |
| `clubs` | Yes | (not counted) | Existing table; no dedicated “SAS Clubs scraper” yet. |

**Mapping used today:** Events → `events`; Qualifications → `member_roles`; SAS ID → **`sas_id_personal`** (not `sas_id_registry`). Associations → no table. Clubs → `clubs` exists, no scraper.

---

## 5. Last run and batch info

| Scraper | Last run | Last batch ID | Rows in last batch | Source |
|---------|----------|---------------|--------------------|--------|
| **Events** | 2026-03-07 (from `events.last_seen_at`) | `202603071723` | 961 (all in that run) | `events` table |
| **Qualifications** | No batch table | — | — | Log file: last run e.g. 2026-03-08 (weekly-accreditation-sync.log) |
| **SAS ID** | No `sas_scrape_batches` on live | — | — | `sas_member_scrape.py` does **not** write to `sas_scrape_batches`; only to `sas_id_personal`. Last run from cron: daily 02:30. |
| **Associations** | N/A | — | — | No scraper. |
| **Clubs** | N/A | — | — | No scraper. |

---

## 6. Dashboard integration (`/admin/dashboard-v3`)

**Auto Scrapes Status** card shows a row only when the corresponding table exists:

- **SAS Events List Scrape** → shown (table `events` exists). Shows: Last run, Status, New records, Target table, Batch ID, Audit, Log, Run Scrape.
- **SAS Accreditation Sync** → shown (table `member_roles` exists). Same columns; no batch ID.
- **SAS ID Registry Scrape** → **not shown on live** (table `sas_scrape_batches` does not exist).
- **Historical Results Scrape** → **not shown** (table `race_results` does not exist).

So on live the dashboard shows **2 rows**: Events and Accreditation. Each row shows Last run, Status, New records, Target table, Links, Actions (Run Scrape).

---

## 7. Audit pages

| Page | Exists | Route |
|------|--------|--------|
| Events | **Yes** | `/admin/events-audit` |
| SAS ID | **No** | `/admin/sas-id-audit` — not in api.py |
| Qualifications | **No** | `/admin/qualifications-audit` — not in api.py |
| Associations | **No** | `/admin/associations-audit` — not in api.py |

---

## 8. Gaps summary

| Scraper | Installed (script on server) | Automated (cron) | Target table (and rows) | Last run | Audit page |
|---------|------------------------------|------------------|-------------------------|----------|------------|
| **SAS Events** | **No** (scripts missing from deploy/) | **No** | events ✓ (961) | 2026-03-07 | ✓ `/admin/events-audit` |
| **SAS Qualifications** | Yes | Yes (weekly) | member_roles ✓ (950) | Weekly log | **Missing** |
| **SAS ID Registry** | Yes (scripts/sas_member_scrape.py) | Yes (daily) | sas_id_personal ✓ (28,424) | Daily 02:30 | **Missing** |
| **SAS Associations** | **No** | **No** | **Table missing** | — | **Missing** |
| **SAS Clubs** | **No** (future) | **No** | clubs exists | — | — |

**Highlight:**

- **Missing:** Events scraper scripts not in server deploy/; Associations scraper and table missing; Clubs scraper not implemented.
- **Not automated:** Events (no cron on server).
- **Not writing to batch log:** SAS ID scraper writes to `sas_id_personal` only; no `sas_scrape_batches` on live, so dashboard cannot show “SAS ID Registry” row or last batch.

---

## 9. Expected vs current

**Target state:** Operational scrapers for SAS ID, Events, Qualifications, Associations; Clubs when implemented.

**Current state:**

- **Operational:** Qualifications (weekly, writes `member_roles`), SAS ID (daily, writes `sas_id_personal`). Events data exists (961 rows) but **events scraper scripts are not installed** on server and **not scheduled**.
- **Partial:** Events — table populated from a past run; re-runs require installing `run-daily-events-scrape.sh` (and deps) in deploy/ and adding cron.
- **Not implemented:** Associations (no scraper, no table), Clubs (table only).

---

## 10. Recommendations for central monitoring

To make `/admin/dashboard-v3` the central panel for all scrapers with run status, records added, manual run, and audit links:

1. **Events:** Copy to server and schedule: `run-daily-events-scrape.sh`, `scrape_sas_events_list.py`, `load_events_csv_to_db.py` in `/var/www/sailingsa/deploy/`, add cron (e.g. daily 04:00).
2. **SAS ID row on dashboard:** Either (a) run migration `150_sas_scrape_batches.sql` on live and have `sas_member_scrape.py` (or a wrapper) write batch rows, or (b) add a separate “SAS ID” scrape status that reads from `sas_id_personal` (e.g. last updated / count) so the row appears without `sas_scrape_batches`.
3. **Audit pages:** Add `/admin/qualifications-audit`, `/admin/sas-id-audit` (and optionally `/admin/associations-audit` when associations exist).
4. **Associations:** Define `associations` table and scraper if required; then add cron and dashboard row.
5. **Clubs:** When a clubs scraper is implemented, add run_key and dashboard row; keep target table `clubs`.

---

*Sources: repo (api.py, sailingsa/deploy, sailingsa/scripts, database/migrations), live server (`/var/www/sailingsa/deploy/`, `crontab -l`, `/etc/cron.d/sailingsa_sas_scrape`, live DB table existence and counts).*
