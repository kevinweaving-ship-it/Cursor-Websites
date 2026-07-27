# Host logic — dry run report (LIVE)

**Environment:** LIVE — `root@102.218.215.253`, DB `sailors_master`, table `regattas`.  
**Date:** 2025-02-16 (from run).  
**No updates applied. No code changed.**

---

## STEP 2 — Freeze overwrite scripts (dry run)

### 1. `fix_all_clubs_host_regattas.py`

**Phase 1 (club abbrev / first-word patterns):**

- **SQL:** `UPDATE regattas SET host_club_id = %s WHERE event_name IS NOT NULL AND (host_club_id IS NULL OR host_club_id != %s) AND (pattern_placeholders).`
- **Exact WHERE:**  
  `event_name IS NOT NULL AND (host_club_id IS NULL OR host_club_id != %s) AND (UPPER(COALESCE(event_name, '')) LIKE %s OR UPPER(COALESCE(event_name, '')) LIKE %s ...)`  
  (one LIKE per club: abbrev and first word of full name, e.g. `%HYC%`, `%Hermanus%`).
- **Allows overwrite of non-NULL host_club_id?** **YES** — condition `host_club_id != %s` explicitly allows updating when host is already set.

**Phase 2 (EVENT_PATTERN_TO_CLUB):**

- **SQL:** `UPDATE regattas SET host_club_id = %s WHERE host_club_id IS NULL AND event_name IS NOT NULL AND UPPER(event_name) LIKE %s`
- **Exact WHERE:**  
  `host_club_id IS NULL AND event_name IS NOT NULL AND UPPER(event_name) LIKE %s`
- **Allows overwrite of non-NULL host_club_id?** **NO** — only rows with `host_club_id IS NULL` are updated.

---

### 2. `fix_hyc_wrong_host.py`

- **SQL:** `UPDATE regattas SET host_club_id = %s WHERE regatta_id = ANY(%s) AND host_club_id != %s`
- **Exact WHERE:**  
  `regatta_id = ANY(%s) AND host_club_id != %s`  
  (IDS is a hardcoded list of regatta IDs; second %s is HYC club_id).
- **Allows overwrite of non-NULL host_club_id?** **YES** — any row in IDS with `host_club_id != hyc_id` is updated.

---

### 3. `recalc_standings_after_upload.py`

- **No direct SQL on `regattas`.** It calls `run_fix_host_clubs(conn=conn, verbose=False)` from `fix_all_clubs_host_regattas`.
- **Effective behaviour:** Same as **fix_all_clubs_host_regattas** (Phase 1 + Phase 2) — i.e. Phase 1 **does** allow overwrite of non-NULL host; Phase 2 does not.

---

## STEP 3 — Safe auto-correct list (SELECT only, dry run)

**Definition used:** Host = exact `club_abbrev` token in `regattas.event_name` (word boundary, longest abbrev wins). No pattern maps, no fuzzy matching.

**Queries run on LIVE `sailors_master`.** No UPDATE executed.

---

### A) event_name contains exact club_abbrev AND host_club_id ≠ that club

**Count:** 11 rows.

| regatta_id | event_name | current_host | derived_club_id |
|------------|------------|--------------|-----------------|
| 186-2024-hmyc-grand-slam | HMYC Grand Slam | 127 | 98 |
| 188-2024-hmyc-6hr-race-results | HMYC 6hr Race Results | 127 | 98 |
| 197-2024-hmyc-autumn-series | HMYC Autumn Series | 127 | 98 |
| 208-2024-hmyc-memorial-series | HMYC Memorial Series | 127 | 98 |
| 228-2024-azalea-at-hmyc | AZALEA at HMYC | 127 | 98 |
| 229-2024-von-klemperer-at-hmyc | VON KLEMPERER at HMYC | 127 | 98 |
| 234-2024-hmyc-club-class-championships | HMYC Club Class Championships | 127 | 98 |
| 243-2024-hmyc-club-class-championships | HMYC Club Class Championships | 127 | 98 |
| 303-2025-hmyc-grand-slam-multihull-overall-final | HMYC Grand Slam_Multihull Overall_Final | 127 | 98 |
| 304-2025-hmyc-grand-slam-final | HMYC Grand Slam | 127 | 98 |
| 317-2025-hmyc-9-hr-endurance | HMYC 9 hr Endurance | 127 | 98 |

All 11: event_name contains exact token **HMYC**; current `host_club_id` = 127; derived host by longest-exact-abbrev = 98. So these are candidates for correction (set host_club_id = 98) **only** when you explicitly approve.

---

### B) No club_abbrev found in event_name (exact token)

**Count:** 337 regattas (full list in agent-tools output file).

Sample: Youth Nationals, KZN/Gauteng/FS regionals, class nationals, etc. Many have `host_club_id` NULL; some have a non-NULL host. No automatic correction applied; these remain as-is unless you define a separate policy.

---

### C) More than one club_abbrev found in event_name (exact token)

**Count:** 0 rows.

No regattas where more than one distinct club_abbrev appears as exact token (word boundary). No ambiguity list.

---

## STOP — No further action

- No UPDATE has been run.
- No code has been modified.
- Awaiting explicit instruction before any host correction or script change.
