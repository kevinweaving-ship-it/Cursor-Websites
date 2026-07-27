# Database Architecture Discovery — Structured Response

**Run date:** From pg_tables + \d+ + FK query + codebase + docs. No migrations, no new tables.

---

## PART 1 — FULL DATABASE MAP

### 1) All tables (all schemas)

```text
SELECT schemaname, tablename FROM pg_tables ORDER BY schemaname, tablename;
```

**User schemas (app + public) — application tables only:**

| schemaname | tablename |
|------------|-----------|
| app | class_id |
| app | clubs |
| app | event_documents |
| app | event_links |
| app | events |
| app | events_scrape_log |
| app | fleets |
| app | provinces |
| app | regatta_339_results |
| app | regatta_359_results |
| app | regatta_classifications |
| app | regatta_sources |
| app | regatta_xxx_results_template |
| app | regattas |
| app | sas_id_personal_backup |
| app | scrape_log |
| app | world_sailing_result_codes |
| public | audit_flags |
| public | boats |
| public | class_age_limits |
| public | class_aliases |
| public | class_candidates |
| public | class_group_members |
| public | class_groups |
| public | class_sailor_master_list |
| public | classes |
| public | club_aliases |
| public | clubs |
| public | entries |
| public | h2h_matrix_cache |
| public | imports_log |
| public | main_scores |
| public | master_list |
| public | member_roles |
| public | name_alias |
| public | people_club_history |
| public | processed_regattas |
| public | races |
| public | ranking_history |
| public | ranking_standings |
| public | regatta_blocks |
| public | regatta_public_mentions |
| public | regattas |
| public | result_match_overrides |
| public | result_match_suggestions |
| public | results |
| public | results_staging |
| public | roles |
| public | sailor_media_delete_requests |
| public | sailor_media_score |
| public | sailor_projection_meta |
| public | sailor_public_mentions |
| public | sas_id_personal |
| public | sas_id_personal_backup |
| public | schools |
| public | scrape_log |
| public | standing_list |
| public | standings_recalc_queue |
| public | temp_people |
| public | trusted_facebook_pages |
| public | user_accounts |
| public | user_sessions |

**Note:** `sas_id_registry` and `sas_scrape_batches` do **not** exist in pg_tables. `sailing_id` does **not** appear in this DB (public/app). So: **no sas_id_registry, no sas_scrape_batches, no sailing_id** on the connected database.

---

### 2) Full structure (\d+) for keyword-matched tables

Tables whose name contains: **sas**, **result**, **regatta**, **scrape**, **race**, **standing**, **personal**, **id**, **staging**, **import**.

Full \d+ output is in: `agent-tools/2bcb67ae-561c-4c0a-b398-94a104fbd2dd.txt` (408 KB). Summary below.

#### app.events_scrape_log
- **Columns:** id (serial), scrape_start_id, scrape_end_id, events_found, events_added, scrape_started_at, scrape_completed_at
- **Primary key:** events_scrape_log_pkey (id)
- **Indexes:** PK only
- **Foreign keys:** none

#### app.scrape_log
- **Columns:** id (serial), scrape_time, before_max_id, after_max_id, added_count, status
- **Primary key:** scrape_log_pkey (id)
- **Indexes:** PK only
- **Foreign keys:** none

#### app.regatta_339_results / app.regatta_359_results
- **Columns:** id (bigint), regatta_no, regatta_name, info_type, fleet_1..fleet_15, sailed, discarded, to_count, entries, score_sys, rank_position, fleet, boat_name, class, division, sail_no, jib_no, club, **helm_name, helm_sas_id, crew_name, crew_sas_id**, rating, class_ranking, race_1_score..race_30_score, race_*_lps_code, discard_*_r_no
- **Primary key:** regatta_*_results_pkey (id)
- **Foreign keys:** none
- **Note:** app-only regatta raw result tables; no FK to sas_id_personal

#### app.regattas
- **Columns:** id (serial), regatta_number, name, date_start, date_end, venue, status, scoring_system, total_entries, created_at
- **Primary key:** regattas_pkey (id)
- **Unique:** regattas_regatta_number_key (regatta_number)
- **Referenced by:** app.fleets (regatta_id → app.regattas(id))

#### app.sas_id_personal_backup
- **Columns:** id, sa_sailing_id, full_name, club_*, c_role_*, last_name, first_name, second_name, year_of_birth, age, gender, … (same shape as sas_id_personal)
- **Primary key:** none shown
- **Foreign keys:** none

#### public.imports_log
- **Columns:** import_id (PK), …
- **Primary key:** imports_log_pkey (import_id)
- **Foreign keys:** (see full file)

#### public.ranking_standings
- **Primary key:** ranking_standings_pkey (id)

#### public.regatta_blocks
- **Primary key:** regatta_blocks_pkey (block_id)
- **Foreign keys:** regatta_id → regattas(regatta_id), class_id → classes(class_id)

#### public.regattas
- **Columns:** regatta_id (text PK), name, date_start, date_end, doc_hash, host_club_id, …
- **Primary key:** regattas_pkey (regatta_id)
- **Unique:** ux_regattas_doc_hash (doc_hash)
- **Foreign keys:** host_club_id → clubs(club_id)

#### public.results
- **Columns:** result_id (bigint serial PK), regatta_id, block_id, rank, fleet_label, class_original, class_canonical, sail_number, helm_name, **helm_sa_sailing_id**, crew_name, **crew_sa_sailing_id**, helm_temp_id, crew_temp_id, club_raw, club_id, class_id, race_scores (jsonb), total_points_raw, nett_points_raw, match_status_helm, match_status_crew, validation_flag, created_at, crew2_*, crew3_*, entry_id, event_name, start_date, end_date, …
- **Primary key:** results_pkey (result_id)
- **Indexes:** idx_results_helm_sas, idx_results_crew_sas, idx_results_regatta_id, idx_results_sailor_regatta_helm, idx_results_sailor_regatta_crew, ix_results_*, etc.
- **Foreign keys:**
  - results_regatta_id_fkey → regattas(regatta_id)
  - results_block_id_fkey → regatta_blocks(block_id)
  - results_class_id_fkey → classes(class_id)
  - results_club_id_fkey → clubs(club_id)
  - results_entry_id_fkey → entries(entry_id) ON DELETE SET NULL
- **Referenced by:** audit_flags(result_id), result_match_overrides(result_id), result_match_suggestions(result_id)
- **Triggers:** sync_temp_people_on_results_insert, trg_auto_update_sailor_regatta_numbers, trg_queue_standings_recalc, trg_results_class_canon, trg_results_class_strict, trg_results_fleet_class_check, trg_update_sailor_counts
- **No FK from results to sas_id_personal or sailing_id.**

#### public.results_staging
- **Columns:** staging_id (serial PK), regatta_id, block_id, fleet_label, class_original, class_canonical, sail_number, boat_name, helm_name, **helm_sa_sailing_id**, crew_name, **crew_sa_sailing_id**, club_raw, club_id, race_scores (jsonb), total_points_raw, nett_points_raw, ranks_sailed, raced, validation_status, validation_errors, created_at
- **Primary key:** results_staging_pkey (staging_id)
- **Indexes:** idx_results_staging_regatta (regatta_id)
- **Foreign keys:** none

#### public.sas_id_personal
- **Columns:** id (integer, nullable), **sa_sailing_id** (character varying), full_name, club_1..club_5, c_role_1..5, primary_class, primary_sailno, first_regatta_no, last_regatta_no, last_name, first_name, second_name, year_of_birth, age, gender, communication_preferences_*, social_media_handles (jsonb), sponsor_name_1..5, phone_primary, phone_secondary, address_line1, city, postal_code, country, profile_photo_path, parent_guardian_id, coach_1_sas_id..coach_5_sas_id, placeholder_1..9, sa_sailing_certifications_roles, examiners_*, national_senior_examiner*, samsa_*, safety_*, instructors_training_*, senior_instructor*, instructor_keelboat*, instructor_dinghy_multihull*, assistant_instructor*, coaching_4_types, senior_race_coach*, race_coach*, assistant_race_coach*, judiciary_*, judge_*, race_management, race_officer_*, measurer, protest_committee, technical_committee, placeholder_*_qual, club_roles, commodore, vice_commodore, committee_member, club_secretary, …, primary_club, club_*_join_date, club_*_member_status, reserve_*, regatta_1..regatta_500 (text columns)
- **Primary key:** **NONE**
- **Unique:** sas_id_personal_new_sa_sailing_id_key UNIQUE CONSTRAINT, btree (sa_sailing_id)
- **Foreign keys:** none
- **Referenced by:** none (results does not FK to this table)

#### public.sas_id_personal_backup
- Same column shape as sas_id_personal (backup table).

#### public.scrape_log
- **Columns:** id (serial), scrape_time, before_max_id, after_max_id, added_count, status (and possibly message, timestamp — see full \d+)
- **Primary key:** scrape_log_pkey (id)
- **Foreign keys:** none

#### public.standing_list, public.standings_recalc_queue, public.races, public.result_match_overrides, public.result_match_suggestions, public.regatta_public_mentions
- See full dump file for columns/indexes/FKs. result_match_* reference results(result_id).

---

### 3) Foreign key relationship map

```text
SELECT tc.table_schema, tc.table_name, kcu.column_name, ccu.table_schema AS foreign_table_schema, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_schema, tc.table_name;
```

**Result (18 rows):**

| table_schema | table_name           | column_name     | foreign_table_schema | foreign_table_name | foreign_column_name |
|--------------|----------------------|-----------------|----------------------|--------------------|---------------------|
| app          | fleets               | regatta_id      | app                  | regattas           | id                  |
| public       | class_aliases        | class_id        | public               | classes            | class_id            |
| public       | class_group_members  | class_id        | public               | classes            | class_id            |
| public       | classes              | parent_id       | public               | classes            | class_id            |
| public       | club_aliases         | club_id         | public               | clubs              | club_id             |
| public       | member_roles         | role_code       | public               | roles              | role_code           |
| public       | people_club_history  | club_id         | public               | clubs              | club_id             |
| public       | regatta_blocks       | regatta_id      | public               | regattas           | regatta_id          |
| public       | regatta_blocks       | class_id        | public               | classes            | class_id            |
| public       | regattas             | host_club_id    | public               | clubs              | club_id             |
| public       | result_match_overrides   | result_id   | public               | results            | result_id           |
| public       | result_match_suggestions | result_id   | public               | results            | result_id           |
| public       | results              | class_id        | public               | classes            | class_id            |
| public       | results              | club_id         | public               | clubs              | club_id             |
| public       | results              | regatta_id      | public               | regattas           | regatta_id          |
| public       | results              | block_id        | public               | regatta_blocks     | block_id            |
| public       | temp_people          | preferred_club_id | public             | clubs              | club_id             |
| public       | user_sessions        | account_id      | public               | user_accounts      | account_id          |

**There is no FK from results, regatta_blocks, or any table to sas_id_personal, sailing_id, or sas_id_registry.** Identity in results is by value (helm_sa_sailing_id / crew_sa_sailing_id) only.

---

## PART 2 — INGESTION FLOW DISCOVERY

Search terms: **sa_sailing_id**, **sas_id_personal**, **scrape**, **incremental**, **member finder**, **batch**, **registry**.

### File and function summary

| Term / concept       | Files | Functions / usage |
|----------------------|-------|-------------------|
| **sa_sailing_id**    | **api.py** | Search (SELECT sa_sailing_id FROM sailing_id), site stats (helm_sa_sailing_id, crew_sa_sailing_id from results; COUNT from sas_id_personal), podium (sas_id_personal), get_sailor_list (sas_id_personal + results), member profile (sas_id_personal, sailing_id fallback), auto-match (UPDATE sailing_id, SET helm_sa_sailing_id/crew_sa_sailing_id on results), api_sa_id_stats (MAX from sailing_id then sas_id_personal then results). **export_regatta_385_data.py:** override helm_sa_sailing_id for result 4563. |
| **sas_id_personal**  | **api.py** | get_sailor_list, get_podium_sailors, site stats “search-aligned” count (sas_id_personal JOIN results), member profile (primary), sailor search, media/sailor lookups, batch slug lookups. |
| **sailing_id**       | **api.py** | Search (FROM sailing_id), auto-match (UPDATE sailing_id), api_sa_id_stats (MAX(sa_sailing_id) FROM sailing_id first), member name fallback (FROM sailing_id), run_daily_scrape (SELECT MAX(sa_sailing_id) FROM sailing_id, INSERT INTO sailing_id). **Note:** sailing_id table does not exist on the connected DB; code expects it. |
| **scrape**           | **api.py** | _scrape_primary_html (news), api_sa_id_stats (last_scrape fields), log_pre_scrape, run_daily_scrape (member-finder URL, INSERT sailing_id), log_post_scrape; **scrape_log** table (before_max_id, after_max_id, added_count). **scrape_sas_events_historical.py**, **process_batch_5.py**, **process_batch_20.py**, **process_manual_batch.py**, **fetch_ai_overviews_batch.py**, **monitor_media_scores_realtime.py**. |
| **incremental**      | **Docs only** | SAS_SCRAPE_ARCHITECTURE.md, README_sailing_id_table.md — “incremental” from MAX(sas_id)+1. No incremental SAS scraper in api.py; run_daily_scrape loops IDs and INSERTs into **sailing_id**. |
| **member finder**    | **api.py** | run_daily_scrape: url = f"https://www.sailing.org.za/member-finder?parentBodyID={current_id}&firstname=&surname=". **Docs:** README_SA_SAILING_SCRAPE_PROCESS.md (URL format). |
| **batch**            | **api.py** | run_daily_scrape (batch over IDs into sailing_id); _batch_sailor_slugs_for_sas_ids; batch name/slug lookups. **process_batch_5.py**, **process_batch_20.py**, **process_manual_batch.py**. |
| **registry**         | **Docs only** | sas_id_registry in SAS_SCRAPE_ARCHITECTURE.md, RUNBOOK_SAS_REGISTRY_CATCHUP.md, SCRAPING_DATA_RULES.md, README_sailing_id_table.md. **No reference to sas_id_registry in api.py or any application code.** |

**Conclusion:** Live ingestion in code uses **sailing_id** (and scrape_log). **sas_id_registry** is not referenced in code. **sas_id_personal** is read for sailor list, podium, profile, counts; it is not the target of the daily scrape endpoint (that target is sailing_id).

---

## PART 3 — README ALIGNMENT

Docs that mention SAS, scrape, identity, results, ingestion (from grep in docs/*.md): README_SA_SAILING_SCRAPE_PROCESS.md, SAS_SCRAPE_ARCHITECTURE.md, README_sas_id_personal.md, SCRAPING_DATA_RULES.md, README_sailing_id_table.md, RUNBOOK_SAS_REGISTRY_CATCHUP.md, README_SAS_ID_MATCHING*.md, RESULTS_* docs, README_results_table.md, README_regatta_results_system.md, README_Regatta_Data_Flow.md, README_DATABASE_TABLES.md, DB_SCHEMA_MAP_AND_MIGRATION_GUIDE.md, and others.

### What the system THINKS it does
- Scrape SA Sailing IDs from member-finder URL; parse name/birth year; **insert/update sas_id_personal** (README_SA_SAILING_SCRAPE_PROCESS).
- **Corrected architecture (docs):** Registry expansion writes **only to sas_id_registry**; incremental from MAX(sas_id)+1; stop after N consecutive NOT_FOUND; batch log in sas_scrape_batches; never write scraped data into race_results; no auto-merge into sailors table (SAS_SCRAPE_ARCHITECTURE, SCRAPING_DATA_RULES).

### What tables it THINKS exist
- **sas_id_personal** — master sailor DB (app or public); PK id, unique sa_sailing_id; ~27,726 sailors (README_sas_id_personal).
- **sas_id_registry** — expansion-only table; sas_id, full_name, status, scraped_at; PK or UNIQUE on sas_id (SAS_SCRAPE_ARCHITECTURE, RUNBOOK).
- **sas_scrape_batches** — batch_id, start_id, end_id, detected_upper_bound, valid_count, not_found_count, error_count, started_at, completed_at (SAS_SCRAPE_ARCHITECTURE).
- **scrape_log** — before_max_id, after_max_id, added_count (exists in app and public).
- **sailing_id** — referenced in api.py (search, MAX, INSERT in run_daily_scrape) but **not** in docs as the canonical scrape target; docs point to sas_id_personal or sas_id_registry.

### Is sas_id_registry mentioned as active?
- **Yes in docs:** SAS_SCRAPE_ARCHITECTURE and RUNBOOK describe sas_id_registry as the expansion target and assume it exists.
- **No in code:** sas_id_registry is not referenced in api.py or elsewhere. It is **not deployed** on the connected DB (pg_tables has no sas_id_registry). So: **documented as active, not present in schema, not used in application code.**

### Is sas_id_personal treated as canonical?
- **In docs:** Yes — “master sailor database”, “central repository”, “Insert/Update sas_id_personal table” (README_SA_SAILING_SCRAPE_PROCESS, README_sas_id_personal).
- **In code:** Used for sailor list, podium, profile, “search-aligned” counts. But **api_sa_id_stats** and search/auto-match prefer **sailing_id** first; **run_daily_scrape** writes to **sailing_id**, not sas_id_personal. So **two canonical sources in code: sailing_id (for scrape and some reads) and sas_id_personal (for profile and many reads).** On the connected DB, **sailing_id does not exist**, so only sas_id_personal exists for identity tables.

---

## Summary

1. **Full table list:** Above (app + public user tables). **sas_id_registry, sas_scrape_batches, sailing_id** are **not** in pg_tables on this DB.
2. **Full structure:** \d+ for all keyword-matched tables is in `agent-tools/2bcb67ae-561c-4c0a-b398-94a104fbd2dd.txt`. **public.sas_id_personal** has **no primary key**, only **UNIQUE(sa_sailing_id)**.
3. **FK map:** 18 FKs; all are results/regatta_blocks/regattas/classes/clubs/aliases. **No FK to sas_id_personal, sailing_id, or sas_id_registry.**
4. **Ingestion:** Code uses **sailing_id** for scrape and some lookups; **sas_id_personal** for sailor list, podium, profile. **sas_id_registry** is docs/migrations only, not in code or schema.
5. **README vs reality:** Docs describe sas_id_registry as expansion target and sas_id_personal as master; **sas_id_registry is not present and not in code.** sas_id_personal is canonical for many features; **sailing_id** is canonical for the daily scrape and some stats when that table exists. **Align schema (which tables exist where), then ingestion (sailing_id vs sas_id_personal vs sas_id_registry) before changing scraping again.**
