# Pending items – to deal with later

Items listed here are deferred. Kept in `.gitignore` so only required/current changes show. Revisit when ready – files remain on disk.

**Current changes** = modified core files (api.py, sailingsa/frontend/*) plus .gitignore and this file.

## Config / env
- .env.example
- .gitignore
- .icloudignore

## Docs (root)
- AGENTS.md
- AI_OVERVIEW_PROFILE_INTEGRATION.md
- API_COLUMN_MAPPING.md
- API_PORT.md
- BUG_LOGO_NOT_DISPLAYING.md
- README.md
- README_CLEAN_STACK.md
- README_DEPLOYMENT.md
- README_SAILINGSA.md
- README_SEO_URLS.md
- REQUIREMENTS.md
- backend_optimization_guide.md
- maintenance_guide.md

## Shell scripts
- SETUP_FACEBOOK_NGROK.sh
- SET_CREDENTIALS_NOW.sh
- SET_FACEBOOK_AND_RESTART.sh
- SET_FACEBOOK_CREDENTIALS.sh
- START_API_HTTPS.sh
- START_API_SERVER.sh
- START_BOTH_SERVERS.sh
- START_NGROK.sh
- build.sh
- cleanup_icloud.sh
- compare_local_vs_cloud.sh
- deploy.sh
- deploy_slug_live.sh
- exclude_from_icloud.sh
- restart_all_services.sh
- run_media_refresh_all.sh
- set_facebook_secret.sh
- setup_production.sh
- start_api.sh
- start_clean.sh
- start_local.sh
- update_site.sh
- verify_data_consistency.sh

## Regatta add/amend scripts
- add_regatta_375_entries.py
- add_regatta_385_420_fleet.py
- add_regatta_385_420_results.py
- add_regatta_385_hobie_results.py
- add_regatta_385_ilca4_results.py
- add_regatta_385_ilca6_results.py
- add_regatta_385_ilca7_results.py
- add_regatta_385_open_results.py
- add_regatta_385_optimist_a_results.py
- add_regatta_385_optimist_b_results.py
- add_regatta_385_sonnet_results.py
- add_regattas_377_384_no_results.py
- amend_regatta_385_420_final.py
- amend_regatta_385_hobie_final.py
- amend_regatta_385_ilca4_final.py
- amend_regatta_385_ilca6_final.py
- amend_regatta_385_ilca7_final.py
- amend_regatta_385_mirror_final.py
- amend_regatta_385_optimist_a_final.py
- amend_regatta_385_optimist_b_final.py
- amend_regatta_385_sonnet_final.py

## Audit / fix / check scripts
- audit_highlights.py
- audit_regatta.py
- audit_regatta_host_status.py
- audit_results_missing_sailor_id.py
- audit_results_missing_sas_ids.py
- audit_top_sailors_in_batch.py
- fix_all_clubs_host_regattas.py
- fix_confident_sas_id_matches.py
- fix_deverson_sas_ids_all_results.py
- fix_hyc_host_club_id.py
- fix_hyc_wrong_host.py
- fix_regatta_385_optimist_a_scores.py
- check_baz_nationals.py
- check_genmac_dabchick.py
- check_hyc_club_data.py
- check_media_status.py
- check_scoring_health.py
- find_missing_sas_matches.py

## Other scripts (build, calculate, etc)
- api_optimized.py
- auto_update_master_list.py
- build_b_standings.py
- build_master_list_audit.py
- build_b_standings_from_readme.py
- calculate_all_standings.py
- calculate_optimist_b_standings.py
- calculate_optimist_b_test.py
- calculate_universal_standings.py
- checksum_regatta_385.py
- compare_hyc_regattas.py
- compare_national_html_vs_db.py
- count_sailors_with_results.py
- count_zvyc_results.py
- debug_5820_standings.py
- diagnose_search_quality.py
- ensure_sailor_club_from_results.py
- fetch_ai_overview.py
- fetch_ai_overviews_batch.py
- get_one_sailor_url.py
- get_scoring_summary.py
- get_timothy_profile.py
- h2h_clulow_dugas.py
- insert_genmac_dabchick_1_8.py
- list_ilca6_rankings_by_fleet.py
- list_missing_sas_proper_names.py
- list_national_regattas_entries.py
- list_regattas_375_380.py
- list_standings_5820.py
- manual_search_and_score.py
- monitor_media_scores_realtime.py
- monitor_scoring_progress.py
- optimist_a_ranking_breakdown.py
- process_all_sailors_comprehensive.py
- process_batch_20.py
- process_batch_5.py
- process_manual_batch.py
- process_new_podium_media_scores.py
- process_standings_recalc_queue.py
- rebuild_b_standings.py
- rebuild_b_standings_complete.py
- rebuild_b_standings_correct.py
- recalc_standings_after_upload.py
- refactor_search.py
- regatta_385_club_utils.py
- remove_regatta_385_sonnet.py
- report_sailors_missing_club.py
- report_unresolved_club_raw.py
- sailor_21172_ranking_report.py
- scrape_sas_events.py
- scrape_sas_events_historical.py
- second_pass_media_scoring.py
- show_ilca6_top10_calculation.py
- standings_common.py
- test_ai_overview_display.py
- test_api_search_no_media_score.py
- test_fetch_3_sailors.py
- test_media_display.py
- third_pass_podium_sailors.py
- top10_h2h_ranking_12m.py
- update_374_standings_and_main_class.py
- update_main_scores.py
- update_regatta_385_sonnet_sas_ids.py
- verify_regatta_385_fleets.py

## HTML / misc files
- 420-nationals-results.html
- boat_pedigree.html
- header_test.html
- index.html
- member-finder.html
- page-template.html
- regatta-admin-V22.html
- regatta-live-results.html
- regatta_search.html
- regatta_viewer.html
- regatta_viewer.html.BU.20251123_201840
- sailingsa_placeholder.html
- search.html
- search.html.BU.20251123_201840
- test_mobile_view.html
- timothy_mobile_profile.html
- viewer.html

## Quick fixes
- FIX_MAIL_NOW.txt
- QUICK_CLEANUP_STEPS.txt
- QUICK_SECURITY_FIXES.py

## Directories
- admin/
- artwork/
- assets/
- build/
- class_engine/
- data/
- deploy/
- dist/
- docs/
- jobs/
- output/
- profile_images/
- projection_engine/
- ranking_engine/
- results/
- sailingsa/ (various subdirs)
- scripts/
- search/
- templates/
- timadvisor/
- var/

## Data / reports
- main_scores_example.json
- standings_top21.json
- icloud_cleanup_report_*.txt
- sailingsa-frontend.zip
