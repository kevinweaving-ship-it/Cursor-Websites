# Where the production DB URL is provided (DB_URL / DATABASE_URL)

Read-only summary: how scripts get the DB connection string; where the events loader should obtain it.

---

## 1. .env files

| File | DB_URL / DATABASE_URL |
|------|------------------------|
| **`.env`** (project root) | Not present in repo (likely in .gitignore). Docs and scripts assume you can set `DB_URL` or `DATABASE_URL` here for local runs; e.g. SSH_LIVE.md line 617: `export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"`. |
| **`.env.example`** (project root) | Does **not** define DB_URL or DATABASE_URL; only SERPAPI/BING keys. So DB URL is not documented in example env. |
| **`sailingsa/backend/.env.local`** | Backend-specific; not used by events loader or deploy scripts. |
| **`sailingsa/backend/.env.local.example`** | Same. |

**Conclusion:** The events loader does **not** read any .env file itself. It uses `os.getenv("DATABASE_URL") or os.getenv("DB_URL")`. So the URL must be **exported in the environment** by the caller (shell that runs the script, or a wrapper that sources .env before invoking the loader).

---

## 2. Deploy scripts

| Script | How DB URL is provided |
|--------|------------------------|
| **`sailingsa/deploy/run-daily-events-scrape.sh`** | Lines 25–29: If `DB_URL` is already set, it exports it. Else if `--on-server` then sets `export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"`. So on server, the script **provides** DB_URL; locally you must set it before running (or in .env and source it). Lines 102–110: Loader runs only when `DATABASE_URL` or `DB_URL` is set; loader is invoked as `$PYTHON "$LOADER" --csv ...` so it **inherits** the same env. |
| **`sailingsa/deploy/run-weekly-accreditation-sync.sh`** | Lines 30–34: Same pattern — use existing `DB_URL` or, when `ON_SERVER=true`, set the same hardcoded URL. |
| **`sailingsa/deploy/run-sas-id-registry-scrape.sh`** | Line 44: When `--on-server`, `export DB_URL="${DB_URL:-postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master}"`. |
| **`sailingsa/deploy/setup-events-table-live.sh`** | Lines 6–9: Requires `DB_URL` or `DATABASE_URL` to be set **before** running; uses `DB="${DB_URL:-$DATABASE_URL}"` for psql and then runs `python3 load_events_csv_to_db.py --csv "$CSV"` (so loader gets URL from env). |
| **`sailingsa/deploy/backup-local-with-proof.sh`** | Line 9: `DB_URL="${DATABASE_URL:-${DB_URL:-postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master}}"` (fallback default for local). |
| **`sailingsa/deploy/setup-dashboard-restore-on-live.sh`** | Line 29: Contains the same `Environment="DB_URL=..."` string for systemd (reference only). |
| **`sailingsa/deploy/apply-classes-sas-live.sh`** | Comment only: “Live DB password has no ! (see server: grep DB_URL /etc/systemd/system/sailingsa-api.service)”. |

So for **production**, deploy scripts that run on the server either set `DB_URL` themselves when `--on-server` (run-daily-events-scrape.sh, run-weekly-accreditation-sync.sh, run-sas-id-registry-scrape.sh) or require the caller to set `DB_URL`/`DATABASE_URL` (setup-events-table-live.sh).

---

## 3. systemd services

| Service file | DB URL |
|--------------|--------|
| **`sailingsa/deploy/sailingsa-api.service`** | Line 10: `Environment="DB_URL=postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"`. This is the **production** DB URL for the API process. Scripts run by **cron** or manually on the server do **not** inherit this unless they are started in a way that reads the same env (e.g. same user and env file, or script sets DB_URL as in run-daily-events-scrape.sh). |

The **events loader** is not started by systemd. It is started by:
- `run-daily-events-scrape.sh` (which sets or uses `DB_URL` before calling the loader), or
- Manual runs (where the user must set `DB_URL` or `DATABASE_URL` in the environment).

So the **canonical production URL** is the one in `sailingsa-api.service`; scripts that need it on the server either hardcode the same string (run-daily-events-scrape.sh, etc.) or document “get it from systemd” (e.g. SSH_LIVE.md: `grep -E 'DB_URL|DATABASE' /etc/systemd/system/sailingsa-api.service`).

---

## 4. run-daily-events-scrape.sh (detail)

- **Lines 25–29:**  
  - If `DB_URL` is already set → `export DB_URL` (use it).  
  - Else if `ON_SERVER=true` (i.e. `--on-server`) → `export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"`.  
  - So when cron runs `run-daily-events-scrape.sh --on-server`, the script **sets** DB_URL for that run; the loader is then invoked in the same process and **inherits** this env.
- **Lines 102–113:** Loader is run only if `LOADER` is set and `DATABASE_URL` or `DB_URL` is set; invoked as `$PYTHON "$LOADER" --csv "$OUTPUT_DIR/sas_events_list.csv"`. So the **events loader obtains the DB connection string from the environment** that run-daily-events-scrape.sh has set (or that was already present when the script started).

---

## 5. Where the events loader should obtain the DB connection string

- **Mechanism:** The loader already uses **environment variables only**:  
  `get_db_url()` returns `os.getenv("DATABASE_URL") or os.getenv("DB_URL")` (see `load_events_csv_to_db.py` lines 26, 169). It does **not** read any .env file or config file.
- **When run by run-daily-events-scrape.sh (production):**  
  The shell script sets or forwards `DB_URL` (see §4). The loader is started as a child process and **inherits** that environment, so it gets the connection string from `DB_URL` (or `DATABASE_URL` if set).
- **When run manually on the server:**  
  The user must **export** `DB_URL` or `DATABASE_URL` before running the loader (e.g. from the value in systemd: `grep DB_URL /etc/systemd/system/sailingsa-api.service`), or run the loader from a shell that has already sourced an env file that sets one of these.
- **When run locally:**  
  The user must set `DB_URL` or `DATABASE_URL` in the environment (e.g. `export DB_URL=...` or `source .env` if .env contains one of them).

So the events loader **should** obtain the DB connection string **only from the process environment** (`DATABASE_URL` or `DB_URL`), as it does now. The **source** of that value is:

- **Production (cron):** run-daily-events-scrape.sh sets `DB_URL` when `--on-server`.
- **Production (manual) or local:** Caller must set `DB_URL` or `DATABASE_URL` (e.g. from systemd service file on server, or from local .env if present).

No change to the loader is required for “where” it gets the URL; ensuring the **caller** (run-daily-events-scrape.sh or the user) sets one of these variables is sufficient.
