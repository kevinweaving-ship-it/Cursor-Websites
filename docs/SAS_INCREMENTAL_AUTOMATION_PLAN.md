# SAS Incremental Expansion — Automation Plan (Design Only)

**Status:** Design only. Do NOT enable yet. Do NOT schedule yet.

**Goal:** Keep `sas_id_personal` aligned with SAS website max ID with minimal footprint.

---

## 1. Strategy Summary

| Aspect | Rule |
|--------|------|
| **Job type** | Incremental only. Start from `MAX(id)+1`. |
| **Frequency** | Random execution window 00:30–05:30. After each run, schedule next run randomly 1–3 days later. No fixed cron time. |
| **Scrape** | Random sleep 1–4 seconds between requests. Hard cap 100 IDs per run. Stop after 20 consecutive NOT_FOUND. |
| **Safety** | INSERT ONLY. ON CONFLICT (sa_sailing_id) DO NOTHING. No updates, no deletes, no schema change. No manual touching of LIVE. |
| **Logging** | start_id, last_checked_id, highest_valid, inserted_count, consecutive_not_found, runtime duration. |
| **Fail-safe** | If error rate > 20% in a run → abort run (no commit of partial batch). |

---

## 2. Implementation Structure

### 2.1 Scheduler wrapper design

- **Single entry point:** One script or job that (a) decides “run now or not” and (b) invokes the scrape module. No cron at fixed times.
- **Time window:** At invocation, check current local time; if outside 00:30–05:30, exit without running (or reschedule for next window). Optionally: run only when explicitly triggered (e.g. manual or external scheduler that already respects the window).
- **Next-run scheduling:** After a successful run, compute next run = now + random(1–3 days) and persist that (file or DB). A separate lightweight “wake” process (e.g. daily cron at 00:15 that only checks “is it time?” and runs the wrapper if so) reads that timestamp and runs the job only when due. No fixed “every night at 03:00” pattern.
- **Idempotent:** Safe to run the wrapper multiple times; it only runs the scrape when (a) inside window and (b) next_run <= now (or when manually forced with a flag).
- **No scrape logic in scheduler:** Scheduler only handles when to run and calls the scrape module; no URLs, no INSERTs, no DB logic in the scheduler.

### 2.2 Scrape module separation

- **Dedicated module:** One module/script responsible only for the incremental scrape (fetch member-finder, parse, decide VALID vs NOT_FOUND, build rows). Same logic as current `scripts/incremental_sas_scrape_local.py` but parameterised and with caps.
- **Parameters:** Configurable: max_ids_per_run (default 100), consecutive_not_found_limit (20), min/max delay between requests (1–4s), DB connection (env). No hardcoded credentials.
- **Single run contract:** “Run once from MAX(id)+1; stop when (a) 100 IDs checked, or (b) 20 consecutive NOT_FOUND, or (c) error rate > 20%.” Returns structured result (start_id, last_checked_id, highest_valid, inserted_count, consecutive_not_found, errors_count, total_checked, runtime_seconds) for the wrapper to log.
- **No scheduling inside scrape:** Scrape module does not schedule the next run; it only returns result. Scheduler wrapper decides next run from that result.
- **LIVE vs LOCAL:** Scrape module reads DB URL from env; same code path for LOCAL or LIVE. Deployment and env (and “do not enable on LIVE yet”) are policy, not code branches.

### 2.3 Logging approach

- **Structured log per run:** One record per run with: start_id, last_checked_id, highest_valid_id, inserted_count, consecutive_not_found_at_stop, total_ids_checked, errors_count, error_rate, runtime_seconds, timestamp (and optionally status: completed | aborted_error_rate | aborted_exception).
- **Where to log:** Either (a) append-only file (e.g. `logs/sas_incremental_YYYYMM.log` or JSONL), or (b) a dedicated table (e.g. `sas_incremental_run_log`) with the above columns. No logging of PII; only IDs and counts.
- **Scheduler wrapper logs:** “Run skipped (outside window)”, “Run skipped (next run not due)”, “Run started”, “Run finished: …” with the structured result from the scrape module. Same sink as above or a separate scheduler log.
- **No log rotation in code:** Rely on system logrotate or DB retention policy; keep the design simple.

### 2.4 Safe deployment plan

- **Phase 1 — Design and review:** This document. Review and approve. No code execution yet.
- **Phase 2 — Implement on LOCAL:** Implement scheduler wrapper + scrape module (with 100-ID cap, 1–4s delay, 20 NOT_FOUND, error-rate abort). Run and verify logs and DB state on LOCAL only. Confirm no schema change, INSERT only, ON CONFLICT DO NOTHING.
- **Phase 3 — Validate LOCAL:** Multiple runs on LOCAL; confirm next-run delay 1–3 days, logs correct, gap count and MAX(id) behave as expected. No LIVE involvement.
- **Phase 4 — Deploy to LIVE (no enable):** Deploy scripts and config to LIVE (e.g. under `/var/www/sailingsa` or agreed path). Set DB URL to LIVE DB. Do not schedule and do not run. Confirm files present and permissions correct.
- **Phase 5 — Enable on LIVE (explicit):** Only after explicit approval: enable the “wake” check (e.g. one cron entry that runs a “should I run?” script in the 00:30–05:30 window). First LIVE run can be manual (invoke once in window) and verify logs and `sas_id_personal` on LIVE.
- **Rollback:** Disable = remove or comment the single cron (or equivalent) that triggers the wrapper. Scrape module and logs remain; no automatic runs. No schema or data rollback needed (INSERT-only, no deletes).

---

## 3. Boundaries (What This Plan Does Not Do)

- Does not add or change schema (no new tables required for the minimal design; logging can be file-based).
- Does not update or delete rows in `sas_id_personal`.
- Does not run on LIVE until Phase 5 and explicit enable.
- Does not fix historical gaps (218 gaps remain; expansion is forward-only from MAX(id)+1).
- Does not expose a fixed schedule (random 1–3 day delay, random time in window).

---

## 4. Review Checklist Before Enable

- [ ] Strategy (frequency, caps, safety, logging, fail-safe) agreed.
- [ ] Scheduler wrapper design agreed (who decides “run now”, how next run is stored and read).
- [ ] Scrape module contract (parameters, return shape, error-rate abort) agreed.
- [ ] Logging format and sink agreed.
- [ ] Phases 2–3 completed on LOCAL.
- [ ] Phase 4 completed on LIVE (deploy without run).
- [ ] Explicit approval to enable (Phase 5).

---

*Document: design only. No automation enabled. No code output in this plan. Implementation follows after review.*
