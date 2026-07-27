# SAS data tools – common scrapers and new SAS IDs

Single reference for scraper scripts that pull data from sailing.org.za and update our DB.

---

## 1. New SAS IDs (member-finder → sas_id_personal)

**Script:** `sailingsa/scripts/sas_member_scrape.py`  
**Source:** https://www.sailing.org.za/member-finder?parentBodyID={id}  
**Target:** `sas_id_personal` (upsert by sa_sailing_id)  
**Purpose:** Discover new SAS IDs after current max; keep sailor registry up to date.

**Run (env: DB_URL):**
```bash
export DB_URL="postgresql://..."
python3 sailingsa/scripts/sas_member_scrape.py
```

**Cron (daily):** `sailingsa/deploy/sailingsa_sas_scrape.cron` – install to `/etc/cron.d/`; script path on server: `/var/www/sailingsa/scripts/sas_member_scrape.py`.

**Behaviour:** Starts at MAX(sa_sailing_id)+1, probes member-finder sequentially, stops after 20 consecutive NOT_FOUND. Rate limit 0.5s per request.

---

## 2. SAS classes (sasclasses page → classes table)

**Script:** `sailingsa/deploy/scrape_sas_classes.py`  
**Source:** https://www.sailing.org.za/what-we-do/sasclasses  
**Target:** `classes` (sas_source_url, sas_contact_email, class_url)  
**Purpose:** Seed/update class contact and SAS page links.

**Run:** `python3 sailingsa/deploy/scrape_sas_classes.py` → writes `classes_sas_columns.sql`  
**Apply on live:** `bash sailingsa/deploy/apply-classes-sas-live.sh`  
**Docs:** `sailingsa/deploy/SSH_LIVE.md` (SAS classes section).

---

## 3. Accreditation quals (accreditation finder → member_roles)

**Script:** `sailingsa/deploy/scrape_accreditation_quals.py`  
**Source:** https://www.sailing.org.za/accreditation-finder/ (or CSV export)  
**Target:** `member_roles` (person_key = SAS:id, role_code)  
**Purpose:** Keep SAS ID / qualifications in sync with SAS.

**Run:** `python3 sailingsa/deploy/scrape_accreditation_quals.py [--csv path]`  
**Apply on live:** `bash sailingsa/deploy/apply-member-roles-live.sh`  
**Weekly auto:** `bash sailingsa/deploy/run-weekly-accreditation-sync.sh`  
**Docs:** `docs/ACCREDITATION_QUALS_WEEKLY.md`, `sailingsa/deploy/SSH_LIVE.md`.

---

## Summary

| Tool            | Script                          | Target             | Cron / schedule      |
|-----------------|----------------------------------|--------------------|----------------------|
| New SAS IDs     | sailingsa/scripts/sas_member_scrape.py | sas_id_personal    | Daily (sailingsa_sas_scrape.cron) |
| SAS classes     | sailingsa/deploy/scrape_sas_classes.py  | classes            | On demand / deploy  |
| Accreditation quals | sailingsa/deploy/scrape_accreditation_quals.py | member_roles | Weekly (run-weekly-accreditation-sync.sh) |

All require `DB_URL` (or `DATABASE_URL`) where the script runs against the DB.
