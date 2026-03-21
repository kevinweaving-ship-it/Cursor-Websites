# SYSTEM_BASELINE_v1
Generated: 2026-02-28T07:14:48Z
Environment: LIVE
Hostname: vm103zuex.yourlocaldomain.com
Database: sailors_master
Deploy type: zip (no git on server)

## 1. Full Database Schema

### audit_flags

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| flag_id | integer | NO | nextval('audit_flags_flag_id_seq'::regclass) |
| result_id | integer | YES |  |
| entry_id | integer | YES |  |
| field_name | text | YES |  |
| issue_type | text | YES |  |
| severity | text | YES | 'warn'::text |
| status | text | YES | 'open'::text |
| created_at | timestamp with time zone | YES | now() |
| resolved_by | text | YES |  |
| resolved_at | timestamp with time zone | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### boats

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| boat_id | bigint | NO | nextval('boats_boat_id_seq'::regclass) |
| sail_number | text | NO |  |
| class_name | text | NO |  |
| make | text | YES |  |
| built_in | text | YES |  |
| year_made | integer | YES |  |
| boat_name | text | YES |  |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### class_age_limits

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('class_age_limits_id_seq'::regclass) |
| class_name | text | NO |  |
| max_age | integer | NO |  |
| notes | text | YES |  |
| created_date | timestamp without time zone | YES | CURRENT_TIMESTAMP |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### class_aliases

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| alias | text | NO |  |
| class_id | integer | YES |  |
| verified | boolean | YES | false |
| notes | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### class_candidates

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| seen_text | text | NO |  |
| seen_count | integer | NO | 1 |
| first_seen | timestamp with time zone | NO | now() |
| last_seen | timestamp with time zone | NO | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### class_group_members

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| group_id | integer | NO |  |
| class_id | integer | NO |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### class_groups

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| group_id | integer | NO | nextval('class_groups_group_id_seq'::regclass) |
| group_name | text | NO |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### class_sailor_master_list

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('class_sailor_master_list_id_seq'::regclas… |
| sailor_id | integer | NO |  |
| sailor_name | text | NO |  |
| class_code | text | NO |  |
| standing | integer | YES |  |
| score | numeric | YES |  |
| consistency | numeric | YES |  |
| regattas_count | integer | YES |  |
| races_count | integer | YES |  |
| club | text | YES |  |
| updated_at | timestamp without time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### classes

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| class_id | integer | NO | nextval('classes_class_id_seq'::regclass) |
| class_name | text | NO |  |
| crew_policy | text | YES |  |
| rating_system | text | YES |  |
| active | boolean | YES | true |
| checksum | text | YES |  |
| _sailors_in_class | integer | YES | 0 |
| _sailors_in_master | integer | YES | 0 |
| parent_id | integer | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### club_aliases

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| alias | text | NO |  |
| club_id | integer | YES |  |
| verified | boolean | YES | false |
| notes | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### clubs

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| club_id | integer | NO | nextval('clubs_club_id_seq'::regclass) |
| club_abbrev | text | YES |  |
| club_fullname | text | YES |  |
| province | text | YES |  |
| country | text | YES |  |
| status | text | YES | 'active'::text |
| address | text | YES |  |
| phone | text | YES |  |
| email | text | YES |  |
| location_url | text | YES |  |
| website_url | text | YES |  |
| facebook_url | text | YES |  |
| instagram_url | text | YES |  |
| gps_coordinates | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### entries

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| entry_id | integer | NO | nextval('entries_entry_id_seq'::regclass) |
| regatta_id | text | YES |  |
| block_id | text | YES |  |
| sail_number | text | YES |  |
| helm_sas_id | text | YES |  |
| crew_sas_id | text | YES |  |
| helm_temp_id | text | YES |  |
| crew_temp_id | text | YES |  |
| club_code | text | YES |  |
| boat_name | text | YES |  |
| verified | boolean | YES | false |
| created_at | timestamp with time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### h2h_matrix_cache

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('h2h_matrix_cache_id_seq'::regclass) |
| class_name | text | NO |  |
| sailor_a_id | text | NO |  |
| sailor_b_id | text | NO |  |
| wins | integer | YES | 0 |
| losses | integer | YES | 0 |
| wc_wins | integer | YES | 0 |
| wc_losses | integer | YES | 0 |
| last_updated | timestamp without time zone | YES | CURRENT_TIMESTAMP |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### imports_log

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| import_id | integer | NO | nextval('imports_log_import_id_seq'::regclass) |
| regatta_id | text | YES |  |
| source_file | text | YES |  |
| imported_at | timestamp with time zone | YES | now() |
| imported_by | text | YES |  |
| rows_added | integer | YES | 0 |
| rows_updated | integer | YES | 0 |
| errors_found | integer | YES | 0 |
| version | text | YES |  |
| notes | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### main_scores

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('main_scores_id_seq'::regclass) |
| sailor_id | text | NO |  |
| class_name | text | NO |  |
| main_score | numeric | NO |  |
| updated_at | timestamp without time zone | YES | now() |
| updated_by | text | YES |  |
| notes | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### master_list

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('master_list_id_seq'::regclass) |
| class_name | text | NO |  |
| sailor_id | text | NO |  |
| name | text | NO |  |
| first_name | text | YES |  |
| last_name | text | YES |  |
| year_of_birth | integer | YES |  |
| age | integer | YES |  |
| added_date | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| removed_date | timestamp without time zone | YES |  |
| removal_reason | text | YES |  |
| is_active | boolean | YES | true |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### member_roles

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| person_key | text | NO |  |
| role_code | text | NO |  |
| status | text | NO |  |
| awarded_date | date | YES |  |
| expires_date | date | YES |  |
| source | text | YES | 'sailing_id_column'::text |
| created_at | timestamp with time zone | YES | now() |
| updated_at | timestamp with time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### name_alias

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| base | text | NO |  |
| variants | ARRAY | NO |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### people_club_history

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| person_key | text | NO |  |
| club_id | integer | NO |  |
| first_seen | date | NO |  |
| last_seen | date | NO |  |
| appearances | integer | NO | 1 |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### processed_regattas

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('processed_regattas_id_seq'::regclass) |
| class_name | text | NO |  |
| regatta_id | text | NO |  |
| regatta_number | integer | YES |  |
| processed_date | timestamp without time zone | YES | CURRENT_TIMESTAMP |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### races

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| race_id | integer | NO | nextval('races_race_id_seq'::regclass) |
| regatta_id | text | YES |  |
| block_id | text | YES |  |
| race_no | integer | YES |  |
| start_time | timestamp with time zone | YES |  |
| wind_speed | numeric | YES |  |
| course_length | numeric | YES |  |
| notes | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### ranking_history

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('ranking_history_id_seq'::regclass) |
| sailor_id | integer | NO |  |
| class_code | text | NO |  |
| rank_position | integer | NO |  |
| final_score | numeric | YES |  |
| snapshot_date | timestamp without time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### ranking_standings

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('ranking_standings_id_seq'::regclass) |
| sailor_id | integer | NO |  |
| class_code | text | NO |  |
| rank_position | integer | NO |  |
| final_score | numeric | NO |  |
| trend | text | YES |  |
| best_regattas | jsonb | YES |  |
| fleet_size | integer | NO |  |
| class_position_out_of | text | YES |  |
| score_gap | numeric | YES |  |
| rank_change | integer | YES |  |
| main_competitors | jsonb | YES |  |
| competitor_insights | jsonb | YES |  |
| consistency_score | numeric | YES |  |
| consistency_label | text | YES |  |
| updated_at | timestamp without time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### regatta_blocks

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| block_id | text | NO |  |
| regatta_id | text | NO |  |
| class_original | text | NO |  |
| class_canonical | text | YES |  |
| fleet_label | text | YES |  |
| races_sailed | integer | NO | 0 |
| discard_count | integer | NO | 0 |
| to_count | integer | NO | 0 |
| scoring_system | text | YES |  |
| block_label_raw | text | YES |  |
| class_id | integer | YES |  |
| entries_raced | integer | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### regatta_public_mentions

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | bigint | NO | nextval('regatta_public_mentions_id_seq'::regclass… |
| regatta_id | text | NO |  |
| headline | text | NO |  |
| snippet | text | YES |  |
| source | text | YES |  |
| url | text | NO |  |
| type | text | NO | 'article'::text |
| published_at | timestamp with time zone | YES |  |
| thumb_url | text | YES |  |
| created_at | timestamp with time zone | NO | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### regattas

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| regatta_id | text | NO |  |
| regatta_number | integer | YES |  |
| event_name | text | NO |  |
| year | integer | YES |  |
| regatta_type | text | YES |  |
| host_club_id | integer | YES |  |
| host_club_code | text | YES |  |
| host_club_name | text | YES |  |
| province_code | text | YES |  |
| province_name | text | YES |  |
| start_date | date | YES |  |
| end_date | date | YES |  |
| result_status | text | YES |  |
| fleet_classes | text | YES |  |
| source_url | text | YES |  |
| local_file_path | text | YES |  |
| file_type | text | YES |  |
| doc_hash | text | YES |  |
| import_status | text | YES | 'pending'::text |
| best_method | text | YES |  |
| name_check_local_vs_source | text | YES |  |
| correct_url_source_match_name | text | YES |  |
| relevant_data_to_columns | text | YES |  |
| raw_data_length | integer | YES |  |
| scoring_system | text | YES |  |
| scoring_mode | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| updated_at | timestamp with time zone | YES | now() |
| as_at_time | timestamp with time zone | YES |  |
| source_platform | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### result_match_overrides

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| result_id | bigint | NO |  |
| helm_id | integer | YES |  |
| crew_id | integer | YES |  |
| note | text | YES |  |
| created_at | timestamp with time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### result_match_suggestions

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| suggestion_id | bigint | NO | nextval('result_match_suggestions_suggestion_id_se… |
| result_id | bigint | NO |  |
| role | text | NO |  |
| candidate_id | integer | NO |  |
| score | numeric | NO |  |
| method | text | NO |  |
| created_at | timestamp with time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### results

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| result_id | bigint | NO | nextval('results_result_id_seq'::regclass) |
| regatta_id | text | NO |  |
| block_id | text | NO |  |
| rank | integer | YES |  |
| fleet_label | text | YES |  |
| class_original | text | NO |  |
| class_canonical | text | YES |  |
| sail_number | text | YES |  |
| bow_no | text | YES |  |
| jib_no | text | YES |  |
| hull_no | text | YES |  |
| boat_name | text | YES |  |
| club_raw | text | YES |  |
| club_id | integer | YES |  |
| helm_name | text | YES |  |
| helm_sa_sailing_id | integer | YES |  |
| crew_name | text | YES |  |
| crew_sa_sailing_id | integer | YES |  |
| races_sailed | integer | NO | 0 |
| discard_count | integer | NO | 0 |
| race_scores | jsonb | NO | '{}'::jsonb |
| total_points_raw | numeric | YES |  |
| nett_points_raw | numeric | YES |  |
| duration_time | text | YES |  |
| corrected_time | text | YES |  |
| handicap | text | YES |  |
| laps | text | YES |  |
| match_status_helm | text | YES |  |
| match_status_crew | text | YES |  |
| validation_flag | text | YES |  |
| source_row_text | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| helm_temp_id | text | YES |  |
| crew_temp_id | text | YES |  |
| class_id | integer | YES |  |
| nationality | character varying | YES |  |
| crew2_name | text | YES |  |
| crew2_sa_sailing_id | integer | YES |  |
| crew2_temp_id | text | YES |  |
| crew3_name | text | YES |  |
| crew3_sa_sailing_id | integer | YES |  |
| crew3_temp_id | text | YES |  |
| entry_id | integer | YES |  |
| event_name | text | YES |  |
| start_date | date | YES |  |
| end_date | date | YES |  |
| host_club_name | text | YES |  |
| province_name | text | YES |  |
| as_at_time | text | YES |  |
| result_status | text | YES | 'Final'::text |
| start_time | text | YES |  |
| finish_time | text | YES |  |
| rank_ordinal | text | YES |  |
| ranks_sailed | integer | NO | 0 |
| raced | boolean | YES |  |
| age_category | text | YES |  |
| competition_level | text | YES |  |
| category_rank | integer | YES |  |
| pos | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### results_staging

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| staging_id | bigint | NO | nextval('results_staging_staging_id_seq'::regclass… |
| regatta_id | text | NO |  |
| block_id | text | YES |  |
| fleet_label | text | NO |  |
| class_original | text | YES |  |
| class_canonical | text | YES |  |
| sail_number | text | YES |  |
| boat_name | text | YES |  |
| helm_name | text | YES |  |
| helm_sa_sailing_id | integer | YES |  |
| crew_name | text | YES |  |
| crew_sa_sailing_id | integer | YES |  |
| club_raw | text | YES |  |
| club_id | integer | YES |  |
| race_scores | jsonb | NO |  |
| total_points_raw | numeric | YES |  |
| nett_points_raw | numeric | YES |  |
| ranks_sailed | integer | YES |  |
| raced | boolean | YES | true |
| validation_status | text | YES | 'PENDING'::text |
| validation_errors | text | YES |  |
| created_at | timestamp with time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### roles

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| role_code | text | NO |  |
| role_label | text | NO |  |
| category | text | NO |  |
| sort_order | integer | NO |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### sailor_media_delete_requests

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | bigint | NO | nextval('sailor_media_delete_requests_id_seq'::reg… |
| sa_id | text | NO |  |
| url | text | NO |  |
| reason | text | NO |  |
| requested_at | timestamp with time zone | NO | now() |
| confirm_token | text | YES |  |
| resolved_at | timestamp with time zone | YES |  |
| resolved_by | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### sailor_media_score

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| sa_id | text | NO |  |
| sailor_name | text | NO |  |
| media_score | integer | NO | 0 |
| media_status | text | NO | 'pending'::text |
| search_query | text | YES |  |
| result_count | integer | YES | 0 |
| valid_url_count | integer | YES | 0 |
| processed_at | timestamp with time zone | YES |  |
| error_message | text | YES |  |
| ai_overview_summary | text | YES |  |
| ai_overview_achievements | jsonb | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### sailor_projection_meta

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| sailor_id | integer | NO |  |
| class_code | text | NO |  |
| average_finish_small_fleet | numeric | YES |  |
| average_finish_big_fleet | numeric | YES |  |
| consistency_index | numeric | YES |  |
| dnf_probability | numeric | YES |  |
| ocs_probability | numeric | YES |  |
| dns_probability | numeric | YES |  |
| trend_factor | numeric | YES |  |
| fleet_strength_factor | numeric | YES |  |
| head_to_head | jsonb | YES |  |
| updated_at | timestamp without time zone | YES | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### sailor_public_mentions

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | bigint | NO | nextval('sailor_public_mentions_id_seq'::regclass) |
| sa_id | text | NO |  |
| headline | text | NO |  |
| snippet | text | YES |  |
| source | text | YES |  |
| url | text | NO |  |
| type | text | NO | 'article'::text |
| published_at | timestamp with time zone | YES |  |
| thumb_url | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| is_valid | boolean | YES | true |
| last_validated_at | timestamp with time zone | YES |  |
| source_added | text | NO | 'system'::text |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### sas_id_personal

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | YES |  |
| sa_sailing_id | character varying | YES |  |
| full_name | character varying | YES |  |
| club_1 | character varying | YES |  |
| c_role_1 | character varying | YES |  |
| primary_class | character varying | YES |  |
| primary_sailno | character varying | YES |  |
| first_regatta_no | integer | YES |  |
| last_regatta_no | integer | YES |  |
| last_name | character varying | YES |  |
| first_name | character varying | YES |  |
| second_name | character varying | YES |  |
| year_of_birth | integer | YES |  |
| age | integer | YES |  |
| gender | character varying | YES |  |
| communication_preferences_1 | character varying | YES |  |
| communication_preferences_2 | character varying | YES |  |
| communication_preferences_3 | character varying | YES |  |
| communication_preferences_4 | character varying | YES |  |
| social_media_handles | jsonb | YES |  |
| sponsor_name_1 | character varying | YES |  |
| sponsor_name_2 | character varying | YES |  |
| sponsor_name_3 | character varying | YES |  |
| sponsor_name_4 | character varying | YES |  |
| sponsor_name_5 | character varying | YES |  |
| phone_primary | character varying | YES |  |
| phone_secondary | character varying | YES |  |
| address_line1 | character varying | YES |  |
| address_line2 | character varying | YES |  |
| city | character varying | YES |  |
| postal_code | character varying | YES |  |
| country | character varying | YES |  |
| club_2 | character varying | YES |  |
| c_role_2 | character varying | YES |  |
| club_3 | character varying | YES |  |
| c_role_3 | character varying | YES |  |
| club_4 | character varying | YES |  |
| c_role_4 | character varying | YES |  |
| club_5 | character varying | YES |  |
| c_role_5 | character varying | YES |  |
| profile_photo_path | character varying | YES |  |
| parent_guardian_id | integer | YES |  |
| coach_1_sas_id | integer | YES |  |
| coach_2_sas_id | integer | YES |  |
| coach_3_sas_id | integer | YES |  |
| coach_4_sas_id | integer | YES |  |
| coach_5_sas_id | integer | YES |  |
| placeholder_1 | character varying | YES |  |
| placeholder_2 | character varying | YES |  |
| placeholder_3 | character varying | YES |  |
| placeholder_4 | character varying | YES |  |
| placeholder_5 | character varying | YES |  |
| placeholder_6 | character varying | YES |  |
| placeholder_7 | character varying | YES |  |
| placeholder_8 | character varying | YES |  |
| placeholder_9 | character varying | YES |  |
| sa_sailing_certifications_roles | character varying | YES |  |
| examiners_surveyors_3_types | character varying | YES |  |
| appointed_examiners | character varying | YES |  |
| appointed_examiners_status | character varying | YES |  |
| appointed_examiners_date | character varying | YES |  |
| national_senior_examiner | character varying | YES |  |
| national_senior_examiner_status | character varying | YES |  |
| national_senior_examiner_date | character varying | YES |  |
| samsa_vessel_surveyors | character varying | YES |  |
| samsa_vessel_surveyors_status | character varying | YES |  |
| samsa_vessel_surveyors_date | character varying | YES |  |
| safety_4_types | character varying | YES |  |
| national_senior_safety_officer | character varying | YES |  |
| national_senior_safety_officer_status | character varying | YES |  |
| national_senior_safety_officer_date | character varying | YES |  |
| sa_sailing_vessel_safety_officers | character varying | YES |  |
| sa_sailing_vessel_safety_officers_status | character varying | YES |  |
| sa_sailing_vessel_safety_officers_date | character varying | YES |  |
| sa_sailing_safety_boat_instructor | character varying | YES |  |
| sa_sailing_safety_boat_instructor_status | character varying | YES |  |
| sa_sailing_safety_boat_instructor_date | character varying | YES |  |
| safety_boat_operator | character varying | YES |  |
| safety_boat_operator_status | character varying | YES |  |
| safety_boat_operator_date | character varying | YES |  |
| instructors_training_4_types | character varying | YES |  |
| senior_instructor | character varying | YES |  |
| senior_instructor_status | character varying | YES |  |
| senior_instructor_date | character varying | YES |  |
| instructor_keelboat | character varying | YES |  |
| instructor_keelboat_status | character varying | YES |  |
| instructor_keelboat_date | character varying | YES |  |
| instructor_dinghy_multihull | character varying | YES |  |
| instructor_dinghy_multihull_status | character varying | YES |  |
| instructor_dinghy_multihull_date | character varying | YES |  |
| assistant_instructor | character varying | YES |  |
| assistant_instructor_status | character varying | YES |  |
| assistant_instructor_date | character varying | YES |  |
| coaching_4_types | character varying | YES |  |
| senior_race_coach | character varying | YES |  |
| senior_race_coach_status | character varying | YES |  |
| senior_race_coach_date | character varying | YES |  |
| race_coach_developer | character varying | YES |  |
| race_coach_developer_status | character varying | YES |  |
| race_coach_developer_date | character varying | YES |  |
| race_coach | character varying | YES |  |
| race_coach_status | character varying | YES |  |
| race_coach_date | character varying | YES |  |
| assistant_race_coach | character varying | YES |  |
| assistant_race_coach_status | character varying | YES |  |
| assistant_race_coach_date | character varying | YES |  |
| judiciary_multiple_levels | character varying | YES |  |
| judge_international_level_ij | character varying | YES |  |
| judge_international_level_ij_status | character varying | YES |  |
| judge_international_level_ij_date | character varying | YES |  |
| judge_national_level | character varying | YES |  |
| judge_national_level_status | character varying | YES |  |
| judge_national_level_date | character varying | YES |  |
| judge_regional_level | character varying | YES |  |
| judge_regional_level_status | character varying | YES |  |
| judge_regional_level_date | character varying | YES |  |
| judge_club_level | character varying | YES |  |
| judge_club_level_status | character varying | YES |  |
| judge_club_level_date | character varying | YES |  |
| race_management | character varying | YES |  |
| race_officer_international_level | character varying | YES |  |
| race_officer_international_level_status | character varying | YES |  |
| race_officer_international_level_date | character varying | YES |  |
| race_officer_national_level | character varying | YES |  |
| race_officer_national_level_status | character varying | YES |  |
| race_officer_national_level_date | character varying | YES |  |
| race_officer_regional_level | character varying | YES |  |
| race_officer_regional_level_status | character varying | YES |  |
| race_officer_regional_level_date | character varying | YES |  |
| race_officer_club_level | character varying | YES |  |
| race_officer_club_level_status | character varying | YES |  |
| race_officer_club_level_date | character varying | YES |  |
| other_qualifications | character varying | YES |  |
| measurer | character varying | YES |  |
| measurer_status | character varying | YES |  |
| measurer_date | character varying | YES |  |
| protest_committee | character varying | YES |  |
| protest_committee_status | character varying | YES |  |
| protest_committee_date | character varying | YES |  |
| technical_committee | character varying | YES |  |
| technical_committee_status | character varying | YES |  |
| technical_committee_date | character varying | YES |  |
| placeholder_1_qual | character varying | YES |  |
| placeholder_2_qual | character varying | YES |  |
| placeholder_3_qual | character varying | YES |  |
| placeholder_4_qual | character varying | YES |  |
| placeholder_5_qual | character varying | YES |  |
| placeholder_6_qual | character varying | YES |  |
| club_roles | character varying | YES |  |
| commodore | character varying | YES |  |
| vice_commodore | character varying | YES |  |
| committee_member | character varying | YES |  |
| club_secretary | character varying | YES |  |
| club_treasurer | character varying | YES |  |
| club_chairman | character varying | YES |  |
| club_director | character varying | YES |  |
| club_manager | character varying | YES |  |
| member | character varying | YES |  |
| cr_other_1 | character varying | YES |  |
| cr_other_2 | character varying | YES |  |
| cr_other_3 | character varying | YES |  |
| cr_other_4 | character varying | YES |  |
| cr_other_5 | character varying | YES |  |
| cr_other_6 | character varying | YES |  |
| cr_other_7 | character varying | YES |  |
| cr_other_8 | character varying | YES |  |
| cr_other_9 | character varying | YES |  |
| cr_other_10 | character varying | YES |  |
| placeholder_1_club | character varying | YES |  |
| placeholder_2_club | character varying | YES |  |
| placeholder_3_club | character varying | YES |  |
| placeholder_4_club | character varying | YES |  |
| placeholder_5_club | character varying | YES |  |
| placeholder_6_club | character varying | YES |  |
| placeholder_7_club | character varying | YES |  |
| placeholder_8_club | character varying | YES |  |
| placeholder_9_club | character varying | YES |  |
| judge_district_level | character varying | YES |  |
| judge_district_level_status | character varying | YES |  |
| judge_district_level_date | character varying | YES |  |
| race_officer_assistant | character varying | YES |  |
| race_officer_assistant_status | character varying | YES |  |
| race_officer_assistant_date | character varying | YES |  |
| race_officer_facilitator | character varying | YES |  |
| race_officer_facilitator_status | character varying | YES |  |
| race_officer_facilitator_date | character varying | YES |  |
| sa_sailing_return_to_play | character varying | YES |  |
| sa_sailing_return_to_play_status | character varying | YES |  |
| sa_sailing_return_to_play_date | character varying | YES |  |
| umpire_national | character varying | YES |  |
| umpire_national_status | character varying | YES |  |
| umpire_national_date | character varying | YES |  |
| class_representative | character varying | YES |  |
| primary_club | character varying | YES |  |
| club_1_join_date | date | YES |  |
| club_2_join_date | date | YES |  |
| club_3_join_date | date | YES |  |
| club_4_join_date | date | YES |  |
| club_5_join_date | date | YES |  |
| club_1_member_status | character varying | YES |  |
| club_2_member_status | character varying | YES |  |
| club_3_member_status | character varying | YES |  |
| club_4_member_status | character varying | YES |  |
| club_5_member_status | character varying | YES |  |
| reserve_215 | text | YES |  |
| reserve_216 | text | YES |  |
| reserve_217 | text | YES |  |
| reserve_218 | text | YES |  |
| reserve_219 | text | YES |  |
| reserve_220 | text | YES |  |
| reserve_221 | text | YES |  |
| reserve_222 | text | YES |  |
| reserve_223 | text | YES |  |
| reserve_224 | text | YES |  |
| reserve_225 | text | YES |  |
| reserve_226 | text | YES |  |
| reserve_227 | text | YES |  |
| reserve_228 | text | YES |  |
| reserve_229 | text | YES |  |
| reserve_230 | text | YES |  |
| reserve_231 | text | YES |  |
| reserve_232 | text | YES |  |
| reserve_233 | text | YES |  |
| reserve_234 | text | YES |  |
| reserve_235 | text | YES |  |
| reserve_236 | text | YES |  |
| reserve_237 | text | YES |  |
| reserve_238 | text | YES |  |
| reserve_239 | text | YES |  |
| reserve_240 | text | YES |  |
| reserve_241 | text | YES |  |
| reserve_242 | text | YES |  |
| reserve_243 | text | YES |  |
| reserve_244 | text | YES |  |
| reserve_245 | text | YES |  |
| reserve_246 | text | YES |  |
| reserve_247 | text | YES |  |
| reserve_248 | text | YES |  |
| reserve_249 | text | YES |  |
| reserve_250 | text | YES |  |
| regatta_1 | text | YES |  |
| regatta_2 | text | YES |  |
| regatta_3 | text | YES |  |
| regatta_4 | text | YES |  |
| regatta_5 | text | YES |  |
| regatta_6 | text | YES |  |
| regatta_7 | text | YES |  |
| regatta_8 | text | YES |  |
| regatta_9 | text | YES |  |
| regatta_10 | text | YES |  |
| regatta_11 | text | YES |  |
| regatta_12 | text | YES |  |
| regatta_13 | text | YES |  |
| regatta_14 | text | YES |  |
| regatta_15 | text | YES |  |
| regatta_16 | text | YES |  |
| regatta_17 | text | YES |  |
| regatta_18 | text | YES |  |
| regatta_19 | text | YES |  |
| regatta_20 | text | YES |  |
| regatta_21 | text | YES |  |
| regatta_22 | text | YES |  |
| regatta_23 | text | YES |  |
| regatta_24 | text | YES |  |
| regatta_25 | text | YES |  |
| regatta_26 | text | YES |  |
| regatta_27 | text | YES |  |
| regatta_28 | text | YES |  |
| regatta_29 | text | YES |  |
| regatta_30 | text | YES |  |
| regatta_31 | text | YES |  |
| regatta_32 | text | YES |  |
| regatta_33 | text | YES |  |
| regatta_34 | text | YES |  |
| regatta_35 | text | YES |  |
| regatta_36 | text | YES |  |
| regatta_37 | text | YES |  |
| regatta_38 | text | YES |  |
| regatta_39 | text | YES |  |
| regatta_40 | text | YES |  |
| regatta_41 | text | YES |  |
| regatta_42 | text | YES |  |
| regatta_43 | text | YES |  |
| regatta_44 | text | YES |  |
| regatta_45 | text | YES |  |
| regatta_46 | text | YES |  |
| regatta_47 | text | YES |  |
| regatta_48 | text | YES |  |
| regatta_49 | text | YES |  |
| regatta_50 | text | YES |  |
| regatta_51 | text | YES |  |
| regatta_52 | text | YES |  |
| regatta_53 | text | YES |  |
| regatta_54 | text | YES |  |
| regatta_55 | text | YES |  |
| regatta_56 | text | YES |  |
| regatta_57 | text | YES |  |
| regatta_58 | text | YES |  |
| regatta_59 | text | YES |  |
| regatta_60 | text | YES |  |
| regatta_61 | text | YES |  |
| regatta_62 | text | YES |  |
| regatta_63 | text | YES |  |
| regatta_64 | text | YES |  |
| regatta_65 | text | YES |  |
| regatta_66 | text | YES |  |
| regatta_67 | text | YES |  |
| regatta_68 | text | YES |  |
| regatta_69 | text | YES |  |
| regatta_70 | text | YES |  |
| regatta_71 | text | YES |  |
| regatta_72 | text | YES |  |
| regatta_73 | text | YES |  |
| regatta_74 | text | YES |  |
| regatta_75 | text | YES |  |
| regatta_76 | text | YES |  |
| regatta_77 | text | YES |  |
| regatta_78 | text | YES |  |
| regatta_79 | text | YES |  |
| regatta_80 | text | YES |  |
| regatta_81 | text | YES |  |
| regatta_82 | text | YES |  |
| regatta_83 | text | YES |  |
| regatta_84 | text | YES |  |
| regatta_85 | text | YES |  |
| regatta_86 | text | YES |  |
| regatta_87 | text | YES |  |
| regatta_88 | text | YES |  |
| regatta_89 | text | YES |  |
| regatta_90 | text | YES |  |
| regatta_91 | text | YES |  |
| regatta_92 | text | YES |  |
| regatta_93 | text | YES |  |
| regatta_94 | text | YES |  |
| regatta_95 | text | YES |  |
| regatta_96 | text | YES |  |
| regatta_97 | text | YES |  |
| regatta_98 | text | YES |  |
| regatta_99 | text | YES |  |
| regatta_100 | text | YES |  |
| regatta_101 | text | YES |  |
| regatta_102 | text | YES |  |
| regatta_103 | text | YES |  |
| regatta_104 | text | YES |  |
| regatta_105 | text | YES |  |
| regatta_106 | text | YES |  |
| regatta_107 | text | YES |  |
| regatta_108 | text | YES |  |
| regatta_109 | text | YES |  |
| regatta_110 | text | YES |  |
| regatta_111 | text | YES |  |
| regatta_112 | text | YES |  |
| regatta_113 | text | YES |  |
| regatta_114 | text | YES |  |
| regatta_115 | text | YES |  |
| regatta_116 | text | YES |  |
| regatta_117 | text | YES |  |
| regatta_118 | text | YES |  |
| regatta_119 | text | YES |  |
| regatta_120 | text | YES |  |
| regatta_121 | text | YES |  |
| regatta_122 | text | YES |  |
| regatta_123 | text | YES |  |
| regatta_124 | text | YES |  |
| regatta_125 | text | YES |  |
| regatta_126 | text | YES |  |
| regatta_127 | text | YES |  |
| regatta_128 | text | YES |  |
| regatta_129 | text | YES |  |
| regatta_130 | text | YES |  |
| regatta_131 | text | YES |  |
| regatta_132 | text | YES |  |
| regatta_133 | text | YES |  |
| regatta_134 | text | YES |  |
| regatta_135 | text | YES |  |
| regatta_136 | text | YES |  |
| regatta_137 | text | YES |  |
| regatta_138 | text | YES |  |
| regatta_139 | text | YES |  |
| regatta_140 | text | YES |  |
| regatta_141 | text | YES |  |
| regatta_142 | text | YES |  |
| regatta_143 | text | YES |  |
| regatta_144 | text | YES |  |
| regatta_145 | text | YES |  |
| regatta_146 | text | YES |  |
| regatta_147 | text | YES |  |
| regatta_148 | text | YES |  |
| regatta_149 | text | YES |  |
| regatta_150 | text | YES |  |
| regatta_151 | text | YES |  |
| regatta_152 | text | YES |  |
| regatta_153 | text | YES |  |
| regatta_154 | text | YES |  |
| regatta_155 | text | YES |  |
| regatta_156 | text | YES |  |
| regatta_157 | text | YES |  |
| regatta_158 | text | YES |  |
| regatta_159 | text | YES |  |
| regatta_160 | text | YES |  |
| regatta_161 | text | YES |  |
| regatta_162 | text | YES |  |
| regatta_163 | text | YES |  |
| regatta_164 | text | YES |  |
| regatta_165 | text | YES |  |
| regatta_166 | text | YES |  |
| regatta_167 | text | YES |  |
| regatta_168 | text | YES |  |
| regatta_169 | text | YES |  |
| regatta_170 | text | YES |  |
| regatta_171 | text | YES |  |
| regatta_172 | text | YES |  |
| regatta_173 | text | YES |  |
| regatta_174 | text | YES |  |
| regatta_175 | text | YES |  |
| regatta_176 | text | YES |  |
| regatta_177 | text | YES |  |
| regatta_178 | text | YES |  |
| regatta_179 | text | YES |  |
| regatta_180 | text | YES |  |
| regatta_181 | text | YES |  |
| regatta_182 | text | YES |  |
| regatta_183 | text | YES |  |
| regatta_184 | text | YES |  |
| regatta_185 | text | YES |  |
| regatta_186 | text | YES |  |
| regatta_187 | text | YES |  |
| regatta_188 | text | YES |  |
| regatta_189 | text | YES |  |
| regatta_190 | text | YES |  |
| regatta_191 | text | YES |  |
| regatta_192 | text | YES |  |
| regatta_193 | text | YES |  |
| regatta_194 | text | YES |  |
| regatta_195 | text | YES |  |
| regatta_196 | text | YES |  |
| regatta_197 | text | YES |  |
| regatta_198 | text | YES |  |
| regatta_199 | text | YES |  |
| regatta_200 | text | YES |  |
| regatta_201 | text | YES |  |
| regatta_202 | text | YES |  |
| regatta_203 | text | YES |  |
| regatta_204 | text | YES |  |
| regatta_205 | text | YES |  |
| regatta_206 | text | YES |  |
| regatta_207 | text | YES |  |
| regatta_208 | text | YES |  |
| regatta_209 | text | YES |  |
| regatta_210 | text | YES |  |
| regatta_211 | text | YES |  |
| regatta_212 | text | YES |  |
| regatta_213 | text | YES |  |
| regatta_214 | text | YES |  |
| regatta_215 | text | YES |  |
| regatta_216 | text | YES |  |
| regatta_217 | text | YES |  |
| regatta_218 | text | YES |  |
| regatta_219 | text | YES |  |
| regatta_220 | text | YES |  |
| regatta_221 | text | YES |  |
| regatta_222 | text | YES |  |
| regatta_223 | text | YES |  |
| regatta_224 | text | YES |  |
| regatta_225 | text | YES |  |
| regatta_226 | text | YES |  |
| regatta_227 | text | YES |  |
| regatta_228 | text | YES |  |
| regatta_229 | text | YES |  |
| regatta_230 | text | YES |  |
| regatta_231 | text | YES |  |
| regatta_232 | text | YES |  |
| regatta_233 | text | YES |  |
| regatta_234 | text | YES |  |
| regatta_235 | text | YES |  |
| regatta_236 | text | YES |  |
| regatta_237 | text | YES |  |
| regatta_238 | text | YES |  |
| regatta_239 | text | YES |  |
| regatta_240 | text | YES |  |
| regatta_241 | text | YES |  |
| regatta_242 | text | YES |  |
| regatta_243 | text | YES |  |
| regatta_244 | text | YES |  |
| regatta_245 | text | YES |  |
| regatta_246 | text | YES |  |
| regatta_247 | text | YES |  |
| regatta_248 | text | YES |  |
| regatta_249 | text | YES |  |
| regatta_250 | text | YES |  |
| regatta_251 | text | YES |  |
| regatta_252 | text | YES |  |
| regatta_253 | text | YES |  |
| regatta_254 | text | YES |  |
| regatta_255 | text | YES |  |
| regatta_256 | text | YES |  |
| regatta_257 | text | YES |  |
| regatta_258 | text | YES |  |
| regatta_259 | text | YES |  |
| regatta_260 | text | YES |  |
| regatta_261 | text | YES |  |
| regatta_262 | text | YES |  |
| regatta_263 | text | YES |  |
| regatta_264 | text | YES |  |
| regatta_265 | text | YES |  |
| regatta_266 | text | YES |  |
| regatta_267 | text | YES |  |
| regatta_268 | text | YES |  |
| regatta_269 | text | YES |  |
| regatta_270 | text | YES |  |
| regatta_271 | text | YES |  |
| regatta_272 | text | YES |  |
| regatta_273 | text | YES |  |
| regatta_274 | text | YES |  |
| regatta_275 | text | YES |  |
| regatta_276 | text | YES |  |
| regatta_277 | text | YES |  |
| regatta_278 | text | YES |  |
| regatta_279 | text | YES |  |
| regatta_280 | text | YES |  |
| regatta_281 | text | YES |  |
| regatta_282 | text | YES |  |
| regatta_283 | text | YES |  |
| regatta_284 | text | YES |  |
| regatta_285 | text | YES |  |
| regatta_286 | text | YES |  |
| regatta_287 | text | YES |  |
| regatta_288 | text | YES |  |
| regatta_289 | text | YES |  |
| regatta_290 | text | YES |  |
| regatta_291 | text | YES |  |
| regatta_292 | text | YES |  |
| regatta_293 | text | YES |  |
| regatta_294 | text | YES |  |
| regatta_295 | text | YES |  |
| regatta_296 | text | YES |  |
| regatta_297 | text | YES |  |
| regatta_298 | text | YES |  |
| regatta_299 | text | YES |  |
| regatta_300 | text | YES |  |
| regatta_301 | text | YES |  |
| regatta_302 | text | YES |  |
| regatta_303 | text | YES |  |
| regatta_304 | text | YES |  |
| regatta_305 | text | YES |  |
| regatta_306 | text | YES |  |
| regatta_307 | text | YES |  |
| regatta_308 | text | YES |  |
| regatta_309 | text | YES |  |
| regatta_310 | text | YES |  |
| regatta_311 | text | YES |  |
| regatta_312 | text | YES |  |
| regatta_313 | text | YES |  |
| regatta_314 | text | YES |  |
| regatta_315 | text | YES |  |
| regatta_316 | text | YES |  |
| regatta_317 | text | YES |  |
| regatta_318 | text | YES |  |
| regatta_319 | text | YES |  |
| regatta_320 | text | YES |  |
| regatta_321 | text | YES |  |
| regatta_322 | text | YES |  |
| regatta_323 | text | YES |  |
| regatta_324 | text | YES |  |
| regatta_325 | text | YES |  |
| regatta_326 | text | YES |  |
| regatta_327 | text | YES |  |
| regatta_328 | text | YES |  |
| regatta_329 | text | YES |  |
| regatta_330 | text | YES |  |
| regatta_331 | text | YES |  |
| regatta_332 | text | YES |  |
| regatta_333 | text | YES |  |
| regatta_334 | text | YES |  |
| regatta_335 | text | YES |  |
| regatta_336 | text | YES |  |
| regatta_337 | text | YES |  |
| regatta_338 | text | YES |  |
| regatta_339 | text | YES |  |
| regatta_340 | text | YES |  |
| regatta_341 | text | YES |  |
| regatta_342 | text | YES |  |
| regatta_343 | text | YES |  |
| regatta_344 | text | YES |  |
| regatta_345 | text | YES |  |
| regatta_346 | text | YES |  |
| regatta_347 | text | YES |  |
| regatta_348 | text | YES |  |
| regatta_349 | text | YES |  |
| regatta_350 | text | YES |  |
| regatta_351 | text | YES |  |
| regatta_352 | text | YES |  |
| regatta_353 | text | YES |  |
| regatta_354 | text | YES |  |
| regatta_355 | text | YES |  |
| regatta_356 | text | YES |  |
| regatta_357 | text | YES |  |
| regatta_358 | text | YES |  |
| regatta_359 | text | YES |  |
| regatta_360 | text | YES |  |
| regatta_361 | text | YES |  |
| regatta_362 | text | YES |  |
| regatta_363 | text | YES |  |
| regatta_364 | text | YES |  |
| regatta_365 | text | YES |  |
| regatta_366 | text | YES |  |
| regatta_367 | text | YES |  |
| regatta_368 | text | YES |  |
| regatta_369 | text | YES |  |
| regatta_370 | text | YES |  |
| regatta_371 | text | YES |  |
| regatta_372 | text | YES |  |
| regatta_373 | text | YES |  |
| regatta_374 | text | YES |  |
| regatta_375 | text | YES |  |
| regatta_376 | text | YES |  |
| regatta_377 | text | YES |  |
| regatta_378 | text | YES |  |
| regatta_379 | text | YES |  |
| regatta_380 | text | YES |  |
| regatta_381 | text | YES |  |
| regatta_382 | text | YES |  |
| regatta_383 | text | YES |  |
| regatta_384 | text | YES |  |
| regatta_385 | text | YES |  |
| regatta_386 | text | YES |  |
| regatta_387 | text | YES |  |
| regatta_388 | text | YES |  |
| regatta_389 | text | YES |  |
| regatta_390 | text | YES |  |
| regatta_391 | text | YES |  |
| regatta_392 | text | YES |  |
| regatta_393 | text | YES |  |
| regatta_394 | text | YES |  |
| regatta_395 | text | YES |  |
| regatta_396 | text | YES |  |
| regatta_397 | text | YES |  |
| regatta_398 | text | YES |  |
| regatta_399 | text | YES |  |
| regatta_400 | text | YES |  |
| regatta_401 | text | YES |  |
| regatta_402 | text | YES |  |
| regatta_403 | text | YES |  |
| regatta_404 | text | YES |  |
| regatta_405 | text | YES |  |
| regatta_406 | text | YES |  |
| regatta_407 | text | YES |  |
| regatta_408 | text | YES |  |
| regatta_409 | text | YES |  |
| regatta_410 | text | YES |  |
| regatta_411 | text | YES |  |
| regatta_412 | text | YES |  |
| regatta_413 | text | YES |  |
| regatta_414 | text | YES |  |
| regatta_415 | text | YES |  |
| regatta_416 | text | YES |  |
| regatta_417 | text | YES |  |
| regatta_418 | text | YES |  |
| regatta_419 | text | YES |  |
| regatta_420 | text | YES |  |
| regatta_421 | text | YES |  |
| regatta_422 | text | YES |  |
| regatta_423 | text | YES |  |
| regatta_424 | text | YES |  |
| regatta_425 | text | YES |  |
| regatta_426 | text | YES |  |
| regatta_427 | text | YES |  |
| regatta_428 | text | YES |  |
| regatta_429 | text | YES |  |
| regatta_430 | text | YES |  |
| regatta_431 | text | YES |  |
| regatta_432 | text | YES |  |
| regatta_433 | text | YES |  |
| regatta_434 | text | YES |  |
| regatta_435 | text | YES |  |
| regatta_436 | text | YES |  |
| regatta_437 | text | YES |  |
| regatta_438 | text | YES |  |
| regatta_439 | text | YES |  |
| regatta_440 | text | YES |  |
| regatta_441 | text | YES |  |
| regatta_442 | text | YES |  |
| regatta_443 | text | YES |  |
| regatta_444 | text | YES |  |
| regatta_445 | text | YES |  |
| regatta_446 | text | YES |  |
| regatta_447 | text | YES |  |
| regatta_448 | text | YES |  |
| regatta_449 | text | YES |  |
| regatta_450 | text | YES |  |
| regatta_451 | text | YES |  |
| regatta_452 | text | YES |  |
| regatta_453 | text | YES |  |
| regatta_454 | text | YES |  |
| regatta_455 | text | YES |  |
| regatta_456 | text | YES |  |
| regatta_457 | text | YES |  |
| regatta_458 | text | YES |  |
| regatta_459 | text | YES |  |
| regatta_460 | text | YES |  |
| regatta_461 | text | YES |  |
| regatta_462 | text | YES |  |
| regatta_463 | text | YES |  |
| regatta_464 | text | YES |  |
| regatta_465 | text | YES |  |
| regatta_466 | text | YES |  |
| regatta_467 | text | YES |  |
| regatta_468 | text | YES |  |
| regatta_469 | text | YES |  |
| regatta_470 | text | YES |  |
| regatta_471 | text | YES |  |
| regatta_472 | text | YES |  |
| regatta_473 | text | YES |  |
| regatta_474 | text | YES |  |
| regatta_475 | text | YES |  |
| regatta_476 | text | YES |  |
| regatta_477 | text | YES |  |
| regatta_478 | text | YES |  |
| regatta_479 | text | YES |  |
| regatta_480 | text | YES |  |
| regatta_481 | text | YES |  |
| regatta_482 | text | YES |  |
| regatta_483 | text | YES |  |
| regatta_484 | text | YES |  |
| regatta_485 | text | YES |  |
| regatta_486 | text | YES |  |
| regatta_487 | text | YES |  |
| regatta_488 | text | YES |  |
| regatta_489 | text | YES |  |
| regatta_490 | text | YES |  |
| regatta_491 | text | YES |  |
| regatta_492 | text | YES |  |
| regatta_493 | text | YES |  |
| regatta_494 | text | YES |  |
| regatta_495 | text | YES |  |
| regatta_496 | text | YES |  |
| regatta_497 | text | YES |  |
| regatta_498 | text | YES |  |
| regatta_499 | text | YES |  |
| regatta_500 | text | YES |  |
| created_at | timestamp without time zone | YES |  |
| updated_at | timestamp without time zone | YES |  |
| created_by | character varying | YES |  |
| notes | text | YES |  |
| personal_information | text | YES |  |
| nationality | character varying | YES |  |
| preferred_language | character varying | YES |  |
| province | character varying | YES |  |
| email | character varying | YES |  |
| date_of_birth | date | YES |  |
| sa_sailing_return_to_play_authorisation | character varying | YES |  |
| nickname | character varying | YES |  |
| club_safety_boat_skipper | character varying | YES |  |
| club_safety_boat_skipper_date | character varying | YES |  |
| club_safety_boat_skipper_status | character varying | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### sas_id_personal_backup

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | YES |  |
| sa_sailing_id | character varying | YES |  |
| full_name | character varying | YES |  |
| club_1 | character varying | YES |  |
| c_role_1 | character varying | YES |  |
| primary_class | character varying | YES |  |
| primary_sailno | character varying | YES |  |
| first_regatta_no | integer | YES |  |
| last_regatta_no | integer | YES |  |
| last_name | character varying | YES |  |
| first_name | character varying | YES |  |
| second_name | character varying | YES |  |
| year_of_birth | integer | YES |  |
| age | integer | YES |  |
| gender | character varying | YES |  |
| communication_preferences_1 | character varying | YES |  |
| communication_preferences_2 | character varying | YES |  |
| communication_preferences_3 | character varying | YES |  |
| communication_preferences_4 | character varying | YES |  |
| social_media_handles | jsonb | YES |  |
| sponsor_name_1 | character varying | YES |  |
| sponsor_name_2 | character varying | YES |  |
| sponsor_name_3 | character varying | YES |  |
| sponsor_name_4 | character varying | YES |  |
| sponsor_name_5 | character varying | YES |  |
| phone_primary | character varying | YES |  |
| phone_secondary | character varying | YES |  |
| address_line1 | character varying | YES |  |
| address_line2 | character varying | YES |  |
| city | character varying | YES |  |
| postal_code | character varying | YES |  |
| country | character varying | YES |  |
| club_2 | character varying | YES |  |
| c_role_2 | character varying | YES |  |
| club_3 | character varying | YES |  |
| c_role_3 | character varying | YES |  |
| club_4 | character varying | YES |  |
| c_role_4 | character varying | YES |  |
| club_5 | character varying | YES |  |
| c_role_5 | character varying | YES |  |
| profile_photo_path | character varying | YES |  |
| parent_guardian_id | integer | YES |  |
| coach_1_sas_id | integer | YES |  |
| coach_2_sas_id | integer | YES |  |
| coach_3_sas_id | integer | YES |  |
| coach_4_sas_id | integer | YES |  |
| coach_5_sas_id | integer | YES |  |
| placeholder_1 | character varying | YES |  |
| placeholder_2 | character varying | YES |  |
| placeholder_3 | character varying | YES |  |
| placeholder_4 | character varying | YES |  |
| placeholder_5 | character varying | YES |  |
| placeholder_6 | character varying | YES |  |
| placeholder_7 | character varying | YES |  |
| placeholder_8 | character varying | YES |  |
| placeholder_9 | character varying | YES |  |
| sa_sailing_certifications_roles | character varying | YES |  |
| examiners_surveyors_3_types | character varying | YES |  |
| appointed_examiners | character varying | YES |  |
| appointed_examiners_status | character varying | YES |  |
| appointed_examiners_date | character varying | YES |  |
| national_senior_examiner | character varying | YES |  |
| national_senior_examiner_status | character varying | YES |  |
| national_senior_examiner_date | character varying | YES |  |
| samsa_vessel_surveyors | character varying | YES |  |
| samsa_vessel_surveyors_status | character varying | YES |  |
| samsa_vessel_surveyors_date | character varying | YES |  |
| safety_4_types | character varying | YES |  |
| national_senior_safety_officer | character varying | YES |  |
| national_senior_safety_officer_status | character varying | YES |  |
| national_senior_safety_officer_date | character varying | YES |  |
| sa_sailing_vessel_safety_officers | character varying | YES |  |
| sa_sailing_vessel_safety_officers_status | character varying | YES |  |
| sa_sailing_vessel_safety_officers_date | character varying | YES |  |
| sa_sailing_safety_boat_instructor | character varying | YES |  |
| sa_sailing_safety_boat_instructor_status | character varying | YES |  |
| sa_sailing_safety_boat_instructor_date | character varying | YES |  |
| safety_boat_operator | character varying | YES |  |
| safety_boat_operator_status | character varying | YES |  |
| safety_boat_operator_date | character varying | YES |  |
| instructors_training_4_types | character varying | YES |  |
| senior_instructor | character varying | YES |  |
| senior_instructor_status | character varying | YES |  |
| senior_instructor_date | character varying | YES |  |
| instructor_keelboat | character varying | YES |  |
| instructor_keelboat_status | character varying | YES |  |
| instructor_keelboat_date | character varying | YES |  |
| instructor_dinghy_multihull | character varying | YES |  |
| instructor_dinghy_multihull_status | character varying | YES |  |
| instructor_dinghy_multihull_date | character varying | YES |  |
| assistant_instructor | character varying | YES |  |
| assistant_instructor_status | character varying | YES |  |
| assistant_instructor_date | character varying | YES |  |
| coaching_4_types | character varying | YES |  |
| senior_race_coach | character varying | YES |  |
| senior_race_coach_status | character varying | YES |  |
| senior_race_coach_date | character varying | YES |  |
| race_coach_developer | character varying | YES |  |
| race_coach_developer_status | character varying | YES |  |
| race_coach_developer_date | character varying | YES |  |
| race_coach | character varying | YES |  |
| race_coach_status | character varying | YES |  |
| race_coach_date | character varying | YES |  |
| assistant_race_coach | character varying | YES |  |
| assistant_race_coach_status | character varying | YES |  |
| assistant_race_coach_date | character varying | YES |  |
| judiciary_multiple_levels | character varying | YES |  |
| judge_international_level_ij | character varying | YES |  |
| judge_international_level_ij_status | character varying | YES |  |
| judge_international_level_ij_date | character varying | YES |  |
| judge_national_level | character varying | YES |  |
| judge_national_level_status | character varying | YES |  |
| judge_national_level_date | character varying | YES |  |
| judge_regional_level | character varying | YES |  |
| judge_regional_level_status | character varying | YES |  |
| judge_regional_level_date | character varying | YES |  |
| judge_club_level | character varying | YES |  |
| judge_club_level_status | character varying | YES |  |
| judge_club_level_date | character varying | YES |  |
| race_management | character varying | YES |  |
| race_officer_international_level | character varying | YES |  |
| race_officer_international_level_status | character varying | YES |  |
| race_officer_international_level_date | character varying | YES |  |
| race_officer_national_level | character varying | YES |  |
| race_officer_national_level_status | character varying | YES |  |
| race_officer_national_level_date | character varying | YES |  |
| race_officer_regional_level | character varying | YES |  |
| race_officer_regional_level_status | character varying | YES |  |
| race_officer_regional_level_date | character varying | YES |  |
| race_officer_club_level | character varying | YES |  |
| race_officer_club_level_status | character varying | YES |  |
| race_officer_club_level_date | character varying | YES |  |
| other_qualifications | character varying | YES |  |
| measurer | character varying | YES |  |
| measurer_status | character varying | YES |  |
| measurer_date | character varying | YES |  |
| protest_committee | character varying | YES |  |
| protest_committee_status | character varying | YES |  |
| protest_committee_date | character varying | YES |  |
| technical_committee | character varying | YES |  |
| technical_committee_status | character varying | YES |  |
| technical_committee_date | character varying | YES |  |
| placeholder_1_qual | character varying | YES |  |
| placeholder_2_qual | character varying | YES |  |
| placeholder_3_qual | character varying | YES |  |
| placeholder_4_qual | character varying | YES |  |
| placeholder_5_qual | character varying | YES |  |
| placeholder_6_qual | character varying | YES |  |
| club_roles | character varying | YES |  |
| commodore | character varying | YES |  |
| vice_commodore | character varying | YES |  |
| committee_member | character varying | YES |  |
| club_secretary | character varying | YES |  |
| club_treasurer | character varying | YES |  |
| club_chairman | character varying | YES |  |
| club_director | character varying | YES |  |
| club_manager | character varying | YES |  |
| member | character varying | YES |  |
| cr_other_1 | character varying | YES |  |
| cr_other_2 | character varying | YES |  |
| cr_other_3 | character varying | YES |  |
| cr_other_4 | character varying | YES |  |
| cr_other_5 | character varying | YES |  |
| cr_other_6 | character varying | YES |  |
| cr_other_7 | character varying | YES |  |
| cr_other_8 | character varying | YES |  |
| cr_other_9 | character varying | YES |  |
| cr_other_10 | character varying | YES |  |
| placeholder_1_club | character varying | YES |  |
| placeholder_2_club | character varying | YES |  |
| placeholder_3_club | character varying | YES |  |
| placeholder_4_club | character varying | YES |  |
| placeholder_5_club | character varying | YES |  |
| placeholder_6_club | character varying | YES |  |
| placeholder_7_club | character varying | YES |  |
| placeholder_8_club | character varying | YES |  |
| placeholder_9_club | character varying | YES |  |
| judge_district_level | character varying | YES |  |
| judge_district_level_status | character varying | YES |  |
| judge_district_level_date | character varying | YES |  |
| race_officer_assistant | character varying | YES |  |
| race_officer_assistant_status | character varying | YES |  |
| race_officer_assistant_date | character varying | YES |  |
| race_officer_facilitator | character varying | YES |  |
| race_officer_facilitator_status | character varying | YES |  |
| race_officer_facilitator_date | character varying | YES |  |
| sa_sailing_return_to_play | character varying | YES |  |
| sa_sailing_return_to_play_status | character varying | YES |  |
| sa_sailing_return_to_play_date | character varying | YES |  |
| umpire_national | character varying | YES |  |
| umpire_national_status | character varying | YES |  |
| umpire_national_date | character varying | YES |  |
| class_representative | character varying | YES |  |
| primary_club | character varying | YES |  |
| club_1_join_date | date | YES |  |
| club_2_join_date | date | YES |  |
| club_3_join_date | date | YES |  |
| club_4_join_date | date | YES |  |
| club_5_join_date | date | YES |  |
| club_1_member_status | character varying | YES |  |
| club_2_member_status | character varying | YES |  |
| club_3_member_status | character varying | YES |  |
| club_4_member_status | character varying | YES |  |
| club_5_member_status | character varying | YES |  |
| reserve_215 | text | YES |  |
| reserve_216 | text | YES |  |
| reserve_217 | text | YES |  |
| reserve_218 | text | YES |  |
| reserve_219 | text | YES |  |
| reserve_220 | text | YES |  |
| reserve_221 | text | YES |  |
| reserve_222 | text | YES |  |
| reserve_223 | text | YES |  |
| reserve_224 | text | YES |  |
| reserve_225 | text | YES |  |
| reserve_226 | text | YES |  |
| reserve_227 | text | YES |  |
| reserve_228 | text | YES |  |
| reserve_229 | text | YES |  |
| reserve_230 | text | YES |  |
| reserve_231 | text | YES |  |
| reserve_232 | text | YES |  |
| reserve_233 | text | YES |  |
| reserve_234 | text | YES |  |
| reserve_235 | text | YES |  |
| reserve_236 | text | YES |  |
| reserve_237 | text | YES |  |
| reserve_238 | text | YES |  |
| reserve_239 | text | YES |  |
| reserve_240 | text | YES |  |
| reserve_241 | text | YES |  |
| reserve_242 | text | YES |  |
| reserve_243 | text | YES |  |
| reserve_244 | text | YES |  |
| reserve_245 | text | YES |  |
| reserve_246 | text | YES |  |
| reserve_247 | text | YES |  |
| reserve_248 | text | YES |  |
| reserve_249 | text | YES |  |
| reserve_250 | text | YES |  |
| regatta_1 | text | YES |  |
| regatta_2 | text | YES |  |
| regatta_3 | text | YES |  |
| regatta_4 | text | YES |  |
| regatta_5 | text | YES |  |
| regatta_6 | text | YES |  |
| regatta_7 | text | YES |  |
| regatta_8 | text | YES |  |
| regatta_9 | text | YES |  |
| regatta_10 | text | YES |  |
| regatta_11 | text | YES |  |
| regatta_12 | text | YES |  |
| regatta_13 | text | YES |  |
| regatta_14 | text | YES |  |
| regatta_15 | text | YES |  |
| regatta_16 | text | YES |  |
| regatta_17 | text | YES |  |
| regatta_18 | text | YES |  |
| regatta_19 | text | YES |  |
| regatta_20 | text | YES |  |
| regatta_21 | text | YES |  |
| regatta_22 | text | YES |  |
| regatta_23 | text | YES |  |
| regatta_24 | text | YES |  |
| regatta_25 | text | YES |  |
| regatta_26 | text | YES |  |
| regatta_27 | text | YES |  |
| regatta_28 | text | YES |  |
| regatta_29 | text | YES |  |
| regatta_30 | text | YES |  |
| regatta_31 | text | YES |  |
| regatta_32 | text | YES |  |
| regatta_33 | text | YES |  |
| regatta_34 | text | YES |  |
| regatta_35 | text | YES |  |
| regatta_36 | text | YES |  |
| regatta_37 | text | YES |  |
| regatta_38 | text | YES |  |
| regatta_39 | text | YES |  |
| regatta_40 | text | YES |  |
| regatta_41 | text | YES |  |
| regatta_42 | text | YES |  |
| regatta_43 | text | YES |  |
| regatta_44 | text | YES |  |
| regatta_45 | text | YES |  |
| regatta_46 | text | YES |  |
| regatta_47 | text | YES |  |
| regatta_48 | text | YES |  |
| regatta_49 | text | YES |  |
| regatta_50 | text | YES |  |
| regatta_51 | text | YES |  |
| regatta_52 | text | YES |  |
| regatta_53 | text | YES |  |
| regatta_54 | text | YES |  |
| regatta_55 | text | YES |  |
| regatta_56 | text | YES |  |
| regatta_57 | text | YES |  |
| regatta_58 | text | YES |  |
| regatta_59 | text | YES |  |
| regatta_60 | text | YES |  |
| regatta_61 | text | YES |  |
| regatta_62 | text | YES |  |
| regatta_63 | text | YES |  |
| regatta_64 | text | YES |  |
| regatta_65 | text | YES |  |
| regatta_66 | text | YES |  |
| regatta_67 | text | YES |  |
| regatta_68 | text | YES |  |
| regatta_69 | text | YES |  |
| regatta_70 | text | YES |  |
| regatta_71 | text | YES |  |
| regatta_72 | text | YES |  |
| regatta_73 | text | YES |  |
| regatta_74 | text | YES |  |
| regatta_75 | text | YES |  |
| regatta_76 | text | YES |  |
| regatta_77 | text | YES |  |
| regatta_78 | text | YES |  |
| regatta_79 | text | YES |  |
| regatta_80 | text | YES |  |
| regatta_81 | text | YES |  |
| regatta_82 | text | YES |  |
| regatta_83 | text | YES |  |
| regatta_84 | text | YES |  |
| regatta_85 | text | YES |  |
| regatta_86 | text | YES |  |
| regatta_87 | text | YES |  |
| regatta_88 | text | YES |  |
| regatta_89 | text | YES |  |
| regatta_90 | text | YES |  |
| regatta_91 | text | YES |  |
| regatta_92 | text | YES |  |
| regatta_93 | text | YES |  |
| regatta_94 | text | YES |  |
| regatta_95 | text | YES |  |
| regatta_96 | text | YES |  |
| regatta_97 | text | YES |  |
| regatta_98 | text | YES |  |
| regatta_99 | text | YES |  |
| regatta_100 | text | YES |  |
| regatta_101 | text | YES |  |
| regatta_102 | text | YES |  |
| regatta_103 | text | YES |  |
| regatta_104 | text | YES |  |
| regatta_105 | text | YES |  |
| regatta_106 | text | YES |  |
| regatta_107 | text | YES |  |
| regatta_108 | text | YES |  |
| regatta_109 | text | YES |  |
| regatta_110 | text | YES |  |
| regatta_111 | text | YES |  |
| regatta_112 | text | YES |  |
| regatta_113 | text | YES |  |
| regatta_114 | text | YES |  |
| regatta_115 | text | YES |  |
| regatta_116 | text | YES |  |
| regatta_117 | text | YES |  |
| regatta_118 | text | YES |  |
| regatta_119 | text | YES |  |
| regatta_120 | text | YES |  |
| regatta_121 | text | YES |  |
| regatta_122 | text | YES |  |
| regatta_123 | text | YES |  |
| regatta_124 | text | YES |  |
| regatta_125 | text | YES |  |
| regatta_126 | text | YES |  |
| regatta_127 | text | YES |  |
| regatta_128 | text | YES |  |
| regatta_129 | text | YES |  |
| regatta_130 | text | YES |  |
| regatta_131 | text | YES |  |
| regatta_132 | text | YES |  |
| regatta_133 | text | YES |  |
| regatta_134 | text | YES |  |
| regatta_135 | text | YES |  |
| regatta_136 | text | YES |  |
| regatta_137 | text | YES |  |
| regatta_138 | text | YES |  |
| regatta_139 | text | YES |  |
| regatta_140 | text | YES |  |
| regatta_141 | text | YES |  |
| regatta_142 | text | YES |  |
| regatta_143 | text | YES |  |
| regatta_144 | text | YES |  |
| regatta_145 | text | YES |  |
| regatta_146 | text | YES |  |
| regatta_147 | text | YES |  |
| regatta_148 | text | YES |  |
| regatta_149 | text | YES |  |
| regatta_150 | text | YES |  |
| regatta_151 | text | YES |  |
| regatta_152 | text | YES |  |
| regatta_153 | text | YES |  |
| regatta_154 | text | YES |  |
| regatta_155 | text | YES |  |
| regatta_156 | text | YES |  |
| regatta_157 | text | YES |  |
| regatta_158 | text | YES |  |
| regatta_159 | text | YES |  |
| regatta_160 | text | YES |  |
| regatta_161 | text | YES |  |
| regatta_162 | text | YES |  |
| regatta_163 | text | YES |  |
| regatta_164 | text | YES |  |
| regatta_165 | text | YES |  |
| regatta_166 | text | YES |  |
| regatta_167 | text | YES |  |
| regatta_168 | text | YES |  |
| regatta_169 | text | YES |  |
| regatta_170 | text | YES |  |
| regatta_171 | text | YES |  |
| regatta_172 | text | YES |  |
| regatta_173 | text | YES |  |
| regatta_174 | text | YES |  |
| regatta_175 | text | YES |  |
| regatta_176 | text | YES |  |
| regatta_177 | text | YES |  |
| regatta_178 | text | YES |  |
| regatta_179 | text | YES |  |
| regatta_180 | text | YES |  |
| regatta_181 | text | YES |  |
| regatta_182 | text | YES |  |
| regatta_183 | text | YES |  |
| regatta_184 | text | YES |  |
| regatta_185 | text | YES |  |
| regatta_186 | text | YES |  |
| regatta_187 | text | YES |  |
| regatta_188 | text | YES |  |
| regatta_189 | text | YES |  |
| regatta_190 | text | YES |  |
| regatta_191 | text | YES |  |
| regatta_192 | text | YES |  |
| regatta_193 | text | YES |  |
| regatta_194 | text | YES |  |
| regatta_195 | text | YES |  |
| regatta_196 | text | YES |  |
| regatta_197 | text | YES |  |
| regatta_198 | text | YES |  |
| regatta_199 | text | YES |  |
| regatta_200 | text | YES |  |
| regatta_201 | text | YES |  |
| regatta_202 | text | YES |  |
| regatta_203 | text | YES |  |
| regatta_204 | text | YES |  |
| regatta_205 | text | YES |  |
| regatta_206 | text | YES |  |
| regatta_207 | text | YES |  |
| regatta_208 | text | YES |  |
| regatta_209 | text | YES |  |
| regatta_210 | text | YES |  |
| regatta_211 | text | YES |  |
| regatta_212 | text | YES |  |
| regatta_213 | text | YES |  |
| regatta_214 | text | YES |  |
| regatta_215 | text | YES |  |
| regatta_216 | text | YES |  |
| regatta_217 | text | YES |  |
| regatta_218 | text | YES |  |
| regatta_219 | text | YES |  |
| regatta_220 | text | YES |  |
| regatta_221 | text | YES |  |
| regatta_222 | text | YES |  |
| regatta_223 | text | YES |  |
| regatta_224 | text | YES |  |
| regatta_225 | text | YES |  |
| regatta_226 | text | YES |  |
| regatta_227 | text | YES |  |
| regatta_228 | text | YES |  |
| regatta_229 | text | YES |  |
| regatta_230 | text | YES |  |
| regatta_231 | text | YES |  |
| regatta_232 | text | YES |  |
| regatta_233 | text | YES |  |
| regatta_234 | text | YES |  |
| regatta_235 | text | YES |  |
| regatta_236 | text | YES |  |
| regatta_237 | text | YES |  |
| regatta_238 | text | YES |  |
| regatta_239 | text | YES |  |
| regatta_240 | text | YES |  |
| regatta_241 | text | YES |  |
| regatta_242 | text | YES |  |
| regatta_243 | text | YES |  |
| regatta_244 | text | YES |  |
| regatta_245 | text | YES |  |
| regatta_246 | text | YES |  |
| regatta_247 | text | YES |  |
| regatta_248 | text | YES |  |
| regatta_249 | text | YES |  |
| regatta_250 | text | YES |  |
| regatta_251 | text | YES |  |
| regatta_252 | text | YES |  |
| regatta_253 | text | YES |  |
| regatta_254 | text | YES |  |
| regatta_255 | text | YES |  |
| regatta_256 | text | YES |  |
| regatta_257 | text | YES |  |
| regatta_258 | text | YES |  |
| regatta_259 | text | YES |  |
| regatta_260 | text | YES |  |
| regatta_261 | text | YES |  |
| regatta_262 | text | YES |  |
| regatta_263 | text | YES |  |
| regatta_264 | text | YES |  |
| regatta_265 | text | YES |  |
| regatta_266 | text | YES |  |
| regatta_267 | text | YES |  |
| regatta_268 | text | YES |  |
| regatta_269 | text | YES |  |
| regatta_270 | text | YES |  |
| regatta_271 | text | YES |  |
| regatta_272 | text | YES |  |
| regatta_273 | text | YES |  |
| regatta_274 | text | YES |  |
| regatta_275 | text | YES |  |
| regatta_276 | text | YES |  |
| regatta_277 | text | YES |  |
| regatta_278 | text | YES |  |
| regatta_279 | text | YES |  |
| regatta_280 | text | YES |  |
| regatta_281 | text | YES |  |
| regatta_282 | text | YES |  |
| regatta_283 | text | YES |  |
| regatta_284 | text | YES |  |
| regatta_285 | text | YES |  |
| regatta_286 | text | YES |  |
| regatta_287 | text | YES |  |
| regatta_288 | text | YES |  |
| regatta_289 | text | YES |  |
| regatta_290 | text | YES |  |
| regatta_291 | text | YES |  |
| regatta_292 | text | YES |  |
| regatta_293 | text | YES |  |
| regatta_294 | text | YES |  |
| regatta_295 | text | YES |  |
| regatta_296 | text | YES |  |
| regatta_297 | text | YES |  |
| regatta_298 | text | YES |  |
| regatta_299 | text | YES |  |
| regatta_300 | text | YES |  |
| regatta_301 | text | YES |  |
| regatta_302 | text | YES |  |
| regatta_303 | text | YES |  |
| regatta_304 | text | YES |  |
| regatta_305 | text | YES |  |
| regatta_306 | text | YES |  |
| regatta_307 | text | YES |  |
| regatta_308 | text | YES |  |
| regatta_309 | text | YES |  |
| regatta_310 | text | YES |  |
| regatta_311 | text | YES |  |
| regatta_312 | text | YES |  |
| regatta_313 | text | YES |  |
| regatta_314 | text | YES |  |
| regatta_315 | text | YES |  |
| regatta_316 | text | YES |  |
| regatta_317 | text | YES |  |
| regatta_318 | text | YES |  |
| regatta_319 | text | YES |  |
| regatta_320 | text | YES |  |
| regatta_321 | text | YES |  |
| regatta_322 | text | YES |  |
| regatta_323 | text | YES |  |
| regatta_324 | text | YES |  |
| regatta_325 | text | YES |  |
| regatta_326 | text | YES |  |
| regatta_327 | text | YES |  |
| regatta_328 | text | YES |  |
| regatta_329 | text | YES |  |
| regatta_330 | text | YES |  |
| regatta_331 | text | YES |  |
| regatta_332 | text | YES |  |
| regatta_333 | text | YES |  |
| regatta_334 | text | YES |  |
| regatta_335 | text | YES |  |
| regatta_336 | text | YES |  |
| regatta_337 | text | YES |  |
| regatta_338 | text | YES |  |
| regatta_339 | text | YES |  |
| regatta_340 | text | YES |  |
| regatta_341 | text | YES |  |
| regatta_342 | text | YES |  |
| regatta_343 | text | YES |  |
| regatta_344 | text | YES |  |
| regatta_345 | text | YES |  |
| regatta_346 | text | YES |  |
| regatta_347 | text | YES |  |
| regatta_348 | text | YES |  |
| regatta_349 | text | YES |  |
| regatta_350 | text | YES |  |
| regatta_351 | text | YES |  |
| regatta_352 | text | YES |  |
| regatta_353 | text | YES |  |
| regatta_354 | text | YES |  |
| regatta_355 | text | YES |  |
| regatta_356 | text | YES |  |
| regatta_357 | text | YES |  |
| regatta_358 | text | YES |  |
| regatta_359 | text | YES |  |
| regatta_360 | text | YES |  |
| regatta_361 | text | YES |  |
| regatta_362 | text | YES |  |
| regatta_363 | text | YES |  |
| regatta_364 | text | YES |  |
| regatta_365 | text | YES |  |
| regatta_366 | text | YES |  |
| regatta_367 | text | YES |  |
| regatta_368 | text | YES |  |
| regatta_369 | text | YES |  |
| regatta_370 | text | YES |  |
| regatta_371 | text | YES |  |
| regatta_372 | text | YES |  |
| regatta_373 | text | YES |  |
| regatta_374 | text | YES |  |
| regatta_375 | text | YES |  |
| regatta_376 | text | YES |  |
| regatta_377 | text | YES |  |
| regatta_378 | text | YES |  |
| regatta_379 | text | YES |  |
| regatta_380 | text | YES |  |
| regatta_381 | text | YES |  |
| regatta_382 | text | YES |  |
| regatta_383 | text | YES |  |
| regatta_384 | text | YES |  |
| regatta_385 | text | YES |  |
| regatta_386 | text | YES |  |
| regatta_387 | text | YES |  |
| regatta_388 | text | YES |  |
| regatta_389 | text | YES |  |
| regatta_390 | text | YES |  |
| regatta_391 | text | YES |  |
| regatta_392 | text | YES |  |
| regatta_393 | text | YES |  |
| regatta_394 | text | YES |  |
| regatta_395 | text | YES |  |
| regatta_396 | text | YES |  |
| regatta_397 | text | YES |  |
| regatta_398 | text | YES |  |
| regatta_399 | text | YES |  |
| regatta_400 | text | YES |  |
| regatta_401 | text | YES |  |
| regatta_402 | text | YES |  |
| regatta_403 | text | YES |  |
| regatta_404 | text | YES |  |
| regatta_405 | text | YES |  |
| regatta_406 | text | YES |  |
| regatta_407 | text | YES |  |
| regatta_408 | text | YES |  |
| regatta_409 | text | YES |  |
| regatta_410 | text | YES |  |
| regatta_411 | text | YES |  |
| regatta_412 | text | YES |  |
| regatta_413 | text | YES |  |
| regatta_414 | text | YES |  |
| regatta_415 | text | YES |  |
| regatta_416 | text | YES |  |
| regatta_417 | text | YES |  |
| regatta_418 | text | YES |  |
| regatta_419 | text | YES |  |
| regatta_420 | text | YES |  |
| regatta_421 | text | YES |  |
| regatta_422 | text | YES |  |
| regatta_423 | text | YES |  |
| regatta_424 | text | YES |  |
| regatta_425 | text | YES |  |
| regatta_426 | text | YES |  |
| regatta_427 | text | YES |  |
| regatta_428 | text | YES |  |
| regatta_429 | text | YES |  |
| regatta_430 | text | YES |  |
| regatta_431 | text | YES |  |
| regatta_432 | text | YES |  |
| regatta_433 | text | YES |  |
| regatta_434 | text | YES |  |
| regatta_435 | text | YES |  |
| regatta_436 | text | YES |  |
| regatta_437 | text | YES |  |
| regatta_438 | text | YES |  |
| regatta_439 | text | YES |  |
| regatta_440 | text | YES |  |
| regatta_441 | text | YES |  |
| regatta_442 | text | YES |  |
| regatta_443 | text | YES |  |
| regatta_444 | text | YES |  |
| regatta_445 | text | YES |  |
| regatta_446 | text | YES |  |
| regatta_447 | text | YES |  |
| regatta_448 | text | YES |  |
| regatta_449 | text | YES |  |
| regatta_450 | text | YES |  |
| regatta_451 | text | YES |  |
| regatta_452 | text | YES |  |
| regatta_453 | text | YES |  |
| regatta_454 | text | YES |  |
| regatta_455 | text | YES |  |
| regatta_456 | text | YES |  |
| regatta_457 | text | YES |  |
| regatta_458 | text | YES |  |
| regatta_459 | text | YES |  |
| regatta_460 | text | YES |  |
| regatta_461 | text | YES |  |
| regatta_462 | text | YES |  |
| regatta_463 | text | YES |  |
| regatta_464 | text | YES |  |
| regatta_465 | text | YES |  |
| regatta_466 | text | YES |  |
| regatta_467 | text | YES |  |
| regatta_468 | text | YES |  |
| regatta_469 | text | YES |  |
| regatta_470 | text | YES |  |
| regatta_471 | text | YES |  |
| regatta_472 | text | YES |  |
| regatta_473 | text | YES |  |
| regatta_474 | text | YES |  |
| regatta_475 | text | YES |  |
| regatta_476 | text | YES |  |
| regatta_477 | text | YES |  |
| regatta_478 | text | YES |  |
| regatta_479 | text | YES |  |
| regatta_480 | text | YES |  |
| regatta_481 | text | YES |  |
| regatta_482 | text | YES |  |
| regatta_483 | text | YES |  |
| regatta_484 | text | YES |  |
| regatta_485 | text | YES |  |
| regatta_486 | text | YES |  |
| regatta_487 | text | YES |  |
| regatta_488 | text | YES |  |
| regatta_489 | text | YES |  |
| regatta_490 | text | YES |  |
| regatta_491 | text | YES |  |
| regatta_492 | text | YES |  |
| regatta_493 | text | YES |  |
| regatta_494 | text | YES |  |
| regatta_495 | text | YES |  |
| regatta_496 | text | YES |  |
| regatta_497 | text | YES |  |
| regatta_498 | text | YES |  |
| regatta_499 | text | YES |  |
| regatta_500 | text | YES |  |
| created_at | timestamp without time zone | YES |  |
| updated_at | timestamp without time zone | YES |  |
| created_by | character varying | YES |  |
| notes | text | YES |  |
| personal_information | text | YES |  |
| nationality | character varying | YES |  |
| preferred_language | character varying | YES |  |
| province | character varying | YES |  |
| email | character varying | YES |  |
| date_of_birth | date | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### schools

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| school_id | integer | NO | nextval('schools_school_id_seq'::regclass) |
| school_abbrev | text | YES |  |
| school_fullname | text | YES |  |
| province | text | YES |  |
| country | text | YES | 'RSA'::text |
| status | text | YES | 'active'::text |
| address | text | YES |  |
| phone | text | YES |  |
| email | text | YES |  |
| location_url | text | YES |  |
| website_url | text | YES |  |
| facebook_url | text | YES |  |
| instagram_url | text | YES |  |
| gps_coordinates | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### scrape_log

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('scrape_log_id_seq'::regclass) |
| timestamp | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| before_scrape_count | integer | NO |  |
| after_scrape_count | integer | NO |  |
| added_count | integer | NO |  |
| status | character varying | NO |  |
| message | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### standing_list

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| id | integer | NO | nextval('standing_list_id_seq'::regclass) |
| class_name | text | NO |  |
| sailor_id | text | NO |  |
| name | text | NO |  |
| rank | integer | NO |  |
| regattas_sailed | integer | YES | 1 |
| last_updated | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| ranking_score | numeric | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### standings_recalc_queue

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| class_name_normalized | text | NO |  |
| queued_at | timestamp with time zone | NO | now() |
| processed_at | timestamp with time zone | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### temp_people

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| temp_id | integer | NO | nextval('temp_people_temp_id_seq'::regclass) |
| temp_code | text | YES |  |
| full_name | text | YES |  |
| club_name | text | YES |  |
| notes | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| validated | boolean | YES | false |
| official_sa_sailing_id | text | YES |  |
| upgraded | boolean | YES | false |
| updated_at | timestamp with time zone | YES | now() |
| normalized_name | text | YES |  |
| preferred_club_id | integer | YES |  |
| preferred_club_code | text | YES |  |
| club_1 | character varying | YES |  |
| c_role_1 | character varying | YES |  |
| primary_class | character varying | YES |  |
| primary_sailno | character varying | YES |  |
| first_regatta_no | integer | YES |  |
| last_regatta_no | integer | YES |  |
| last_name | character varying | YES |  |
| first_name | character varying | YES |  |
| second_name | character varying | YES |  |
| year_of_birth | integer | YES |  |
| age | integer | YES |  |
| gender | character varying | YES |  |
| communication_preferences_1 | character varying | YES |  |
| communication_preferences_2 | character varying | YES |  |
| communication_preferences_3 | character varying | YES |  |
| communication_preferences_4 | character varying | YES |  |
| social_media_handles | jsonb | YES |  |
| sponsor_name_1 | character varying | YES |  |
| sponsor_name_2 | character varying | YES |  |
| sponsor_name_3 | character varying | YES |  |
| sponsor_name_4 | character varying | YES |  |
| sponsor_name_5 | character varying | YES |  |
| phone_primary | character varying | YES |  |
| phone_secondary | character varying | YES |  |
| address_line1 | character varying | YES |  |
| address_line2 | character varying | YES |  |
| city | character varying | YES |  |
| postal_code | character varying | YES |  |
| country | character varying | YES |  |
| club_2 | character varying | YES |  |
| c_role_2 | character varying | YES |  |
| club_3 | character varying | YES |  |
| c_role_3 | character varying | YES |  |
| club_4 | character varying | YES |  |
| c_role_4 | character varying | YES |  |
| club_5 | character varying | YES |  |
| c_role_5 | character varying | YES |  |
| primary_club | character varying | YES |  |
| club_1_join_date | date | YES |  |
| club_2_join_date | date | YES |  |
| club_3_join_date | date | YES |  |
| club_4_join_date | date | YES |  |
| club_5_join_date | date | YES |  |
| club_1_member_status | character varying | YES |  |
| club_2_member_status | character varying | YES |  |
| club_3_member_status | character varying | YES |  |
| club_4_member_status | character varying | YES |  |
| club_5_member_status | character varying | YES |  |
| profile_photo_path | character varying | YES |  |
| parent_guardian_id | integer | YES |  |
| coach_1_sas_id | integer | YES |  |
| coach_2_sas_id | integer | YES |  |
| coach_3_sas_id | integer | YES |  |
| coach_4_sas_id | integer | YES |  |
| coach_5_sas_id | integer | YES |  |
| placeholder_1 | character varying | YES |  |
| placeholder_2 | character varying | YES |  |
| placeholder_3 | character varying | YES |  |
| placeholder_4 | character varying | YES |  |
| placeholder_5 | character varying | YES |  |
| placeholder_6 | character varying | YES |  |
| placeholder_7 | character varying | YES |  |
| placeholder_8 | character varying | YES |  |
| placeholder_9 | character varying | YES |  |
| placeholder_1_qual | character varying | YES |  |
| placeholder_2_qual | character varying | YES |  |
| placeholder_3_qual | character varying | YES |  |
| placeholder_4_qual | character varying | YES |  |
| placeholder_5_qual | character varying | YES |  |
| placeholder_6_qual | character varying | YES |  |
| placeholder_1_club | character varying | YES |  |
| placeholder_2_club | character varying | YES |  |
| placeholder_3_club | character varying | YES |  |
| placeholder_4_club | character varying | YES |  |
| placeholder_5_club | character varying | YES |  |
| placeholder_6_club | character varying | YES |  |
| placeholder_7_club | character varying | YES |  |
| placeholder_8_club | character varying | YES |  |
| placeholder_9_club | character varying | YES |  |
| sa_sailing_certifications_roles | character varying | YES |  |
| examiners_surveyors_3_types | character varying | YES |  |
| appointed_examiners | character varying | YES |  |
| appointed_examiners_status | character varying | YES |  |
| appointed_examiners_date | character varying | YES |  |
| national_senior_examiner | character varying | YES |  |
| national_senior_examiner_status | character varying | YES |  |
| national_senior_examiner_date | character varying | YES |  |
| samsa_vessel_surveyors | character varying | YES |  |
| samsa_vessel_surveyors_status | character varying | YES |  |
| samsa_vessel_surveyors_date | character varying | YES |  |
| safety_4_types | character varying | YES |  |
| national_senior_safety_officer | character varying | YES |  |
| national_senior_safety_officer_status | character varying | YES |  |
| national_senior_safety_officer_date | character varying | YES |  |
| sa_sailing_vessel_safety_officers | character varying | YES |  |
| sa_sailing_vessel_safety_officers_status | character varying | YES |  |
| sa_sailing_vessel_safety_officers_date | character varying | YES |  |
| sa_sailing_safety_boat_instructor | character varying | YES |  |
| sa_sailing_safety_boat_instructor_status | character varying | YES |  |
| sa_sailing_safety_boat_instructor_date | character varying | YES |  |
| safety_boat_operator | character varying | YES |  |
| regatta_1 | text | YES |  |
| regatta_2 | text | YES |  |
| regatta_3 | text | YES |  |
| regatta_4 | text | YES |  |
| regatta_5 | text | YES |  |
| regatta_6 | text | YES |  |
| regatta_7 | text | YES |  |
| regatta_8 | text | YES |  |
| regatta_9 | text | YES |  |
| regatta_10 | text | YES |  |
| regatta_11 | text | YES |  |
| regatta_12 | text | YES |  |
| regatta_13 | text | YES |  |
| regatta_14 | text | YES |  |
| regatta_15 | text | YES |  |
| regatta_16 | text | YES |  |
| regatta_17 | text | YES |  |
| regatta_18 | text | YES |  |
| regatta_19 | text | YES |  |
| regatta_20 | text | YES |  |
| regatta_21 | text | YES |  |
| regatta_22 | text | YES |  |
| regatta_23 | text | YES |  |
| regatta_24 | text | YES |  |
| regatta_25 | text | YES |  |
| regatta_26 | text | YES |  |
| regatta_27 | text | YES |  |
| regatta_28 | text | YES |  |
| regatta_29 | text | YES |  |
| regatta_30 | text | YES |  |
| regatta_31 | text | YES |  |
| regatta_32 | text | YES |  |
| regatta_33 | text | YES |  |
| regatta_34 | text | YES |  |
| regatta_35 | text | YES |  |
| regatta_36 | text | YES |  |
| regatta_37 | text | YES |  |
| regatta_38 | text | YES |  |
| regatta_39 | text | YES |  |
| regatta_40 | text | YES |  |
| regatta_41 | text | YES |  |
| regatta_42 | text | YES |  |
| regatta_43 | text | YES |  |
| regatta_44 | text | YES |  |
| regatta_45 | text | YES |  |
| regatta_46 | text | YES |  |
| regatta_47 | text | YES |  |
| regatta_48 | text | YES |  |
| regatta_49 | text | YES |  |
| regatta_50 | text | YES |  |
| regatta_51 | text | YES |  |
| regatta_52 | text | YES |  |
| regatta_53 | text | YES |  |
| regatta_54 | text | YES |  |
| regatta_55 | text | YES |  |
| regatta_56 | text | YES |  |
| regatta_57 | text | YES |  |
| regatta_58 | text | YES |  |
| regatta_59 | text | YES |  |
| regatta_60 | text | YES |  |
| regatta_61 | text | YES |  |
| regatta_62 | text | YES |  |
| regatta_63 | text | YES |  |
| regatta_64 | text | YES |  |
| regatta_65 | text | YES |  |
| regatta_66 | text | YES |  |
| regatta_67 | text | YES |  |
| regatta_68 | text | YES |  |
| regatta_69 | text | YES |  |
| regatta_70 | text | YES |  |
| regatta_71 | text | YES |  |
| regatta_72 | text | YES |  |
| regatta_73 | text | YES |  |
| regatta_74 | text | YES |  |
| regatta_75 | text | YES |  |
| regatta_76 | text | YES |  |
| regatta_77 | text | YES |  |
| regatta_78 | text | YES |  |
| regatta_79 | text | YES |  |
| regatta_80 | text | YES |  |
| regatta_81 | text | YES |  |
| regatta_82 | text | YES |  |
| regatta_83 | text | YES |  |
| regatta_84 | text | YES |  |
| regatta_85 | text | YES |  |
| regatta_86 | text | YES |  |
| regatta_87 | text | YES |  |
| regatta_88 | text | YES |  |
| regatta_89 | text | YES |  |
| regatta_90 | text | YES |  |
| regatta_91 | text | YES |  |
| regatta_92 | text | YES |  |
| regatta_93 | text | YES |  |
| regatta_94 | text | YES |  |
| regatta_95 | text | YES |  |
| regatta_96 | text | YES |  |
| regatta_97 | text | YES |  |
| regatta_98 | text | YES |  |
| regatta_99 | text | YES |  |
| regatta_100 | text | YES |  |
| regatta_101 | text | YES |  |
| regatta_102 | text | YES |  |
| regatta_103 | text | YES |  |
| regatta_104 | text | YES |  |
| regatta_105 | text | YES |  |
| regatta_106 | text | YES |  |
| regatta_107 | text | YES |  |
| regatta_108 | text | YES |  |
| regatta_109 | text | YES |  |
| regatta_110 | text | YES |  |
| regatta_111 | text | YES |  |
| regatta_112 | text | YES |  |
| regatta_113 | text | YES |  |
| regatta_114 | text | YES |  |
| regatta_115 | text | YES |  |
| regatta_116 | text | YES |  |
| regatta_117 | text | YES |  |
| regatta_118 | text | YES |  |
| regatta_119 | text | YES |  |
| regatta_120 | text | YES |  |
| regatta_121 | text | YES |  |
| regatta_122 | text | YES |  |
| regatta_123 | text | YES |  |
| regatta_124 | text | YES |  |
| regatta_125 | text | YES |  |
| regatta_126 | text | YES |  |
| regatta_127 | text | YES |  |
| regatta_128 | text | YES |  |
| regatta_129 | text | YES |  |
| regatta_130 | text | YES |  |
| regatta_131 | text | YES |  |
| regatta_132 | text | YES |  |
| regatta_133 | text | YES |  |
| regatta_134 | text | YES |  |
| regatta_135 | text | YES |  |
| regatta_136 | text | YES |  |
| regatta_137 | text | YES |  |
| regatta_138 | text | YES |  |
| regatta_139 | text | YES |  |
| regatta_140 | text | YES |  |
| regatta_141 | text | YES |  |
| regatta_142 | text | YES |  |
| regatta_143 | text | YES |  |
| regatta_144 | text | YES |  |
| regatta_145 | text | YES |  |
| regatta_146 | text | YES |  |
| regatta_147 | text | YES |  |
| regatta_148 | text | YES |  |
| regatta_149 | text | YES |  |
| regatta_150 | text | YES |  |
| regatta_151 | text | YES |  |
| regatta_152 | text | YES |  |
| regatta_153 | text | YES |  |
| regatta_154 | text | YES |  |
| regatta_155 | text | YES |  |
| regatta_156 | text | YES |  |
| regatta_157 | text | YES |  |
| regatta_158 | text | YES |  |
| regatta_159 | text | YES |  |
| regatta_160 | text | YES |  |
| regatta_161 | text | YES |  |
| regatta_162 | text | YES |  |
| regatta_163 | text | YES |  |
| regatta_164 | text | YES |  |
| regatta_165 | text | YES |  |
| regatta_166 | text | YES |  |
| regatta_167 | text | YES |  |
| regatta_168 | text | YES |  |
| regatta_169 | text | YES |  |
| regatta_170 | text | YES |  |
| regatta_171 | text | YES |  |
| regatta_172 | text | YES |  |
| regatta_173 | text | YES |  |
| regatta_174 | text | YES |  |
| regatta_175 | text | YES |  |
| regatta_176 | text | YES |  |
| regatta_177 | text | YES |  |
| regatta_178 | text | YES |  |
| regatta_179 | text | YES |  |
| regatta_180 | text | YES |  |
| regatta_181 | text | YES |  |
| regatta_182 | text | YES |  |
| regatta_183 | text | YES |  |
| regatta_184 | text | YES |  |
| regatta_185 | text | YES |  |
| regatta_186 | text | YES |  |
| regatta_187 | text | YES |  |
| regatta_188 | text | YES |  |
| regatta_189 | text | YES |  |
| regatta_190 | text | YES |  |
| regatta_191 | text | YES |  |
| regatta_192 | text | YES |  |
| regatta_193 | text | YES |  |
| regatta_194 | text | YES |  |
| regatta_195 | text | YES |  |
| regatta_196 | text | YES |  |
| regatta_197 | text | YES |  |
| regatta_198 | text | YES |  |
| regatta_199 | text | YES |  |
| regatta_200 | text | YES |  |
| regatta_201 | text | YES |  |
| regatta_202 | text | YES |  |
| regatta_203 | text | YES |  |
| regatta_204 | text | YES |  |
| regatta_205 | text | YES |  |
| regatta_206 | text | YES |  |
| regatta_207 | text | YES |  |
| regatta_208 | text | YES |  |
| regatta_209 | text | YES |  |
| regatta_210 | text | YES |  |
| regatta_211 | text | YES |  |
| regatta_212 | text | YES |  |
| regatta_213 | text | YES |  |
| regatta_214 | text | YES |  |
| regatta_215 | text | YES |  |
| regatta_216 | text | YES |  |
| regatta_217 | text | YES |  |
| regatta_218 | text | YES |  |
| regatta_219 | text | YES |  |
| regatta_220 | text | YES |  |
| regatta_221 | text | YES |  |
| regatta_222 | text | YES |  |
| regatta_223 | text | YES |  |
| regatta_224 | text | YES |  |
| regatta_225 | text | YES |  |
| regatta_226 | text | YES |  |
| regatta_227 | text | YES |  |
| regatta_228 | text | YES |  |
| regatta_229 | text | YES |  |
| regatta_230 | text | YES |  |
| regatta_231 | text | YES |  |
| regatta_232 | text | YES |  |
| regatta_233 | text | YES |  |
| regatta_234 | text | YES |  |
| regatta_235 | text | YES |  |
| regatta_236 | text | YES |  |
| regatta_237 | text | YES |  |
| regatta_238 | text | YES |  |
| regatta_239 | text | YES |  |
| regatta_240 | text | YES |  |
| regatta_241 | text | YES |  |
| regatta_242 | text | YES |  |
| regatta_243 | text | YES |  |
| regatta_244 | text | YES |  |
| regatta_245 | text | YES |  |
| regatta_246 | text | YES |  |
| regatta_247 | text | YES |  |
| regatta_248 | text | YES |  |
| regatta_249 | text | YES |  |
| regatta_250 | text | YES |  |
| regatta_251 | text | YES |  |
| regatta_252 | text | YES |  |
| regatta_253 | text | YES |  |
| regatta_254 | text | YES |  |
| regatta_255 | text | YES |  |
| regatta_256 | text | YES |  |
| regatta_257 | text | YES |  |
| regatta_258 | text | YES |  |
| regatta_259 | text | YES |  |
| regatta_260 | text | YES |  |
| regatta_261 | text | YES |  |
| regatta_262 | text | YES |  |
| regatta_263 | text | YES |  |
| regatta_264 | text | YES |  |
| regatta_265 | text | YES |  |
| regatta_266 | text | YES |  |
| regatta_267 | text | YES |  |
| regatta_268 | text | YES |  |
| regatta_269 | text | YES |  |
| regatta_270 | text | YES |  |
| regatta_271 | text | YES |  |
| regatta_272 | text | YES |  |
| regatta_273 | text | YES |  |
| regatta_274 | text | YES |  |
| regatta_275 | text | YES |  |
| regatta_276 | text | YES |  |
| regatta_277 | text | YES |  |
| regatta_278 | text | YES |  |
| regatta_279 | text | YES |  |
| regatta_280 | text | YES |  |
| regatta_281 | text | YES |  |
| regatta_282 | text | YES |  |
| regatta_283 | text | YES |  |
| regatta_284 | text | YES |  |
| regatta_285 | text | YES |  |
| regatta_286 | text | YES |  |
| regatta_287 | text | YES |  |
| regatta_288 | text | YES |  |
| regatta_289 | text | YES |  |
| regatta_290 | text | YES |  |
| regatta_291 | text | YES |  |
| regatta_292 | text | YES |  |
| regatta_293 | text | YES |  |
| regatta_294 | text | YES |  |
| regatta_295 | text | YES |  |
| regatta_296 | text | YES |  |
| regatta_297 | text | YES |  |
| regatta_298 | text | YES |  |
| regatta_299 | text | YES |  |
| regatta_300 | text | YES |  |
| regatta_301 | text | YES |  |
| regatta_302 | text | YES |  |
| regatta_303 | text | YES |  |
| regatta_304 | text | YES |  |
| regatta_305 | text | YES |  |
| regatta_306 | text | YES |  |
| regatta_307 | text | YES |  |
| regatta_308 | text | YES |  |
| regatta_309 | text | YES |  |
| regatta_310 | text | YES |  |
| regatta_311 | text | YES |  |
| regatta_312 | text | YES |  |
| regatta_313 | text | YES |  |
| regatta_314 | text | YES |  |
| regatta_315 | text | YES |  |
| regatta_316 | text | YES |  |
| regatta_317 | text | YES |  |
| regatta_318 | text | YES |  |
| regatta_319 | text | YES |  |
| regatta_320 | text | YES |  |
| regatta_321 | text | YES |  |
| regatta_322 | text | YES |  |
| regatta_323 | text | YES |  |
| regatta_324 | text | YES |  |
| regatta_325 | text | YES |  |
| regatta_326 | text | YES |  |
| regatta_327 | text | YES |  |
| regatta_328 | text | YES |  |
| regatta_329 | text | YES |  |
| regatta_330 | text | YES |  |
| regatta_331 | text | YES |  |
| regatta_332 | text | YES |  |
| regatta_333 | text | YES |  |
| regatta_334 | text | YES |  |
| regatta_335 | text | YES |  |
| regatta_336 | text | YES |  |
| regatta_337 | text | YES |  |
| regatta_338 | text | YES |  |
| regatta_339 | text | YES |  |
| regatta_340 | text | YES |  |
| regatta_341 | text | YES |  |
| regatta_342 | text | YES |  |
| regatta_343 | text | YES |  |
| regatta_344 | text | YES |  |
| regatta_345 | text | YES |  |
| regatta_346 | text | YES |  |
| regatta_347 | text | YES |  |
| regatta_348 | text | YES |  |
| regatta_349 | text | YES |  |
| regatta_350 | text | YES |  |
| regatta_351 | text | YES |  |
| regatta_352 | text | YES |  |
| regatta_353 | text | YES |  |
| regatta_354 | text | YES |  |
| regatta_355 | text | YES |  |
| regatta_356 | text | YES |  |
| regatta_357 | text | YES |  |
| regatta_358 | text | YES |  |
| regatta_359 | text | YES |  |
| regatta_360 | text | YES |  |
| regatta_361 | text | YES |  |
| regatta_362 | text | YES |  |
| regatta_363 | text | YES |  |
| regatta_364 | text | YES |  |
| regatta_365 | text | YES |  |
| regatta_366 | text | YES |  |
| regatta_367 | text | YES |  |
| regatta_368 | text | YES |  |
| regatta_369 | text | YES |  |
| regatta_370 | text | YES |  |
| regatta_371 | text | YES |  |
| regatta_372 | text | YES |  |
| regatta_373 | text | YES |  |
| regatta_374 | text | YES |  |
| regatta_375 | text | YES |  |
| regatta_376 | text | YES |  |
| regatta_377 | text | YES |  |
| regatta_378 | text | YES |  |
| regatta_379 | text | YES |  |
| regatta_380 | text | YES |  |
| regatta_381 | text | YES |  |
| regatta_382 | text | YES |  |
| regatta_383 | text | YES |  |
| regatta_384 | text | YES |  |
| regatta_385 | text | YES |  |
| regatta_386 | text | YES |  |
| regatta_387 | text | YES |  |
| regatta_388 | text | YES |  |
| regatta_389 | text | YES |  |
| regatta_390 | text | YES |  |
| regatta_391 | text | YES |  |
| regatta_392 | text | YES |  |
| regatta_393 | text | YES |  |
| regatta_394 | text | YES |  |
| regatta_395 | text | YES |  |
| regatta_396 | text | YES |  |
| regatta_397 | text | YES |  |
| regatta_398 | text | YES |  |
| regatta_399 | text | YES |  |
| regatta_400 | text | YES |  |
| regatta_401 | text | YES |  |
| regatta_402 | text | YES |  |
| regatta_403 | text | YES |  |
| regatta_404 | text | YES |  |
| regatta_405 | text | YES |  |
| regatta_406 | text | YES |  |
| regatta_407 | text | YES |  |
| regatta_408 | text | YES |  |
| regatta_409 | text | YES |  |
| regatta_410 | text | YES |  |
| regatta_411 | text | YES |  |
| regatta_412 | text | YES |  |
| regatta_413 | text | YES |  |
| regatta_414 | text | YES |  |
| regatta_415 | text | YES |  |
| regatta_416 | text | YES |  |
| regatta_417 | text | YES |  |
| regatta_418 | text | YES |  |
| regatta_419 | text | YES |  |
| regatta_420 | text | YES |  |
| regatta_421 | text | YES |  |
| regatta_422 | text | YES |  |
| regatta_423 | text | YES |  |
| regatta_424 | text | YES |  |
| regatta_425 | text | YES |  |
| regatta_426 | text | YES |  |
| regatta_427 | text | YES |  |
| regatta_428 | text | YES |  |
| regatta_429 | text | YES |  |
| regatta_430 | text | YES |  |
| regatta_431 | text | YES |  |
| regatta_432 | text | YES |  |
| regatta_433 | text | YES |  |
| regatta_434 | text | YES |  |
| regatta_435 | text | YES |  |
| regatta_436 | text | YES |  |
| regatta_437 | text | YES |  |
| regatta_438 | text | YES |  |
| regatta_439 | text | YES |  |
| regatta_440 | text | YES |  |
| regatta_441 | text | YES |  |
| regatta_442 | text | YES |  |
| regatta_443 | text | YES |  |
| regatta_444 | text | YES |  |
| regatta_445 | text | YES |  |
| regatta_446 | text | YES |  |
| regatta_447 | text | YES |  |
| regatta_448 | text | YES |  |
| regatta_449 | text | YES |  |
| regatta_450 | text | YES |  |
| regatta_451 | text | YES |  |
| regatta_452 | text | YES |  |
| regatta_453 | text | YES |  |
| regatta_454 | text | YES |  |
| regatta_455 | text | YES |  |
| regatta_456 | text | YES |  |
| regatta_457 | text | YES |  |
| regatta_458 | text | YES |  |
| regatta_459 | text | YES |  |
| regatta_460 | text | YES |  |
| regatta_461 | text | YES |  |
| regatta_462 | text | YES |  |
| regatta_463 | text | YES |  |
| regatta_464 | text | YES |  |
| regatta_465 | text | YES |  |
| regatta_466 | text | YES |  |
| regatta_467 | text | YES |  |
| regatta_468 | text | YES |  |
| regatta_469 | text | YES |  |
| regatta_470 | text | YES |  |
| regatta_471 | text | YES |  |
| regatta_472 | text | YES |  |
| regatta_473 | text | YES |  |
| regatta_474 | text | YES |  |
| regatta_475 | text | YES |  |
| regatta_476 | text | YES |  |
| regatta_477 | text | YES |  |
| regatta_478 | text | YES |  |
| regatta_479 | text | YES |  |
| regatta_480 | text | YES |  |
| regatta_481 | text | YES |  |
| regatta_482 | text | YES |  |
| regatta_483 | text | YES |  |
| regatta_484 | text | YES |  |
| regatta_485 | text | YES |  |
| regatta_486 | text | YES |  |
| regatta_487 | text | YES |  |
| regatta_488 | text | YES |  |
| regatta_489 | text | YES |  |
| regatta_490 | text | YES |  |
| regatta_491 | text | YES |  |
| regatta_492 | text | YES |  |
| regatta_493 | text | YES |  |
| regatta_494 | text | YES |  |
| regatta_495 | text | YES |  |
| regatta_496 | text | YES |  |
| regatta_497 | text | YES |  |
| regatta_498 | text | YES |  |
| regatta_499 | text | YES |  |
| regatta_500 | text | YES |  |
| safety_boat_operator_status | character varying | YES |  |
| safety_boat_operator_date | character varying | YES |  |
| instructors_training_4_types | character varying | YES |  |
| senior_instructor | character varying | YES |  |
| senior_instructor_status | character varying | YES |  |
| senior_instructor_date | character varying | YES |  |
| instructor_keelboat | character varying | YES |  |
| instructor_keelboat_status | character varying | YES |  |
| instructor_keelboat_date | character varying | YES |  |
| instructor_dinghy_multihull | character varying | YES |  |
| instructor_dinghy_multihull_status | character varying | YES |  |
| instructor_dinghy_multihull_date | character varying | YES |  |
| assistant_instructor | character varying | YES |  |
| assistant_instructor_status | character varying | YES |  |
| assistant_instructor_date | character varying | YES |  |
| coaching_4_types | character varying | YES |  |
| senior_race_coach | character varying | YES |  |
| senior_race_coach_status | character varying | YES |  |
| senior_race_coach_date | character varying | YES |  |
| race_coach_developer | character varying | YES |  |
| race_coach_developer_status | character varying | YES |  |
| race_coach_developer_date | character varying | YES |  |
| race_coach | character varying | YES |  |
| race_coach_status | character varying | YES |  |
| race_coach_date | character varying | YES |  |
| assistant_race_coach | character varying | YES |  |
| assistant_race_coach_status | character varying | YES |  |
| assistant_race_coach_date | character varying | YES |  |
| judiciary_multiple_levels | character varying | YES |  |
| judge_international_level_ij | character varying | YES |  |
| judge_international_level_ij_status | character varying | YES |  |
| judge_international_level_ij_date | character varying | YES |  |
| judge_national_level | character varying | YES |  |
| judge_national_level_status | character varying | YES |  |
| judge_national_level_date | character varying | YES |  |
| judge_regional_level | character varying | YES |  |
| judge_regional_level_status | character varying | YES |  |
| judge_regional_level_date | character varying | YES |  |
| judge_club_level | character varying | YES |  |
| judge_club_level_status | character varying | YES |  |
| judge_club_level_date | character varying | YES |  |
| judge_district_level | character varying | YES |  |
| judge_district_level_status | character varying | YES |  |
| judge_district_level_date | character varying | YES |  |
| umpire_national | character varying | YES |  |
| umpire_national_status | character varying | YES |  |
| umpire_national_date | character varying | YES |  |
| race_management | character varying | YES |  |
| race_officer_international_level | character varying | YES |  |
| race_officer_international_level_status | character varying | YES |  |
| race_officer_international_level_date | character varying | YES |  |
| race_officer_national_level | character varying | YES |  |
| race_officer_national_level_status | character varying | YES |  |
| race_officer_national_level_date | character varying | YES |  |
| race_officer_regional_level | character varying | YES |  |
| race_officer_regional_level_status | character varying | YES |  |
| race_officer_regional_level_date | character varying | YES |  |
| race_officer_club_level | character varying | YES |  |
| race_officer_club_level_status | character varying | YES |  |
| race_officer_club_level_date | character varying | YES |  |
| race_officer_assistant | character varying | YES |  |
| race_officer_assistant_status | character varying | YES |  |
| race_officer_assistant_date | character varying | YES |  |
| race_officer_facilitator | character varying | YES |  |
| race_officer_facilitator_status | character varying | YES |  |
| race_officer_facilitator_date | character varying | YES |  |
| other_qualifications | character varying | YES |  |
| measurer | character varying | YES |  |
| measurer_status | character varying | YES |  |
| measurer_date | character varying | YES |  |
| protest_committee | character varying | YES |  |
| protest_committee_status | character varying | YES |  |
| protest_committee_date | character varying | YES |  |
| technical_committee | character varying | YES |  |
| technical_committee_status | character varying | YES |  |
| technical_committee_date | character varying | YES |  |
| sa_sailing_return_to_play | character varying | YES |  |
| sa_sailing_return_to_play_status | character varying | YES |  |
| sa_sailing_return_to_play_date | character varying | YES |  |
| sa_sailing_return_to_play_authorisation | character varying | YES |  |
| club_roles | character varying | YES |  |
| commodore | character varying | YES |  |
| vice_commodore | character varying | YES |  |
| committee_member | character varying | YES |  |
| club_secretary | character varying | YES |  |
| club_treasurer | character varying | YES |  |
| club_chairman | character varying | YES |  |
| club_director | character varying | YES |  |
| club_manager | character varying | YES |  |
| member | character varying | YES |  |
| cr_other_1 | character varying | YES |  |
| cr_other_2 | character varying | YES |  |
| cr_other_3 | character varying | YES |  |
| cr_other_4 | character varying | YES |  |
| cr_other_5 | character varying | YES |  |
| cr_other_6 | character varying | YES |  |
| cr_other_7 | character varying | YES |  |
| cr_other_8 | character varying | YES |  |
| cr_other_9 | character varying | YES |  |
| cr_other_10 | character varying | YES |  |
| class_representative | character varying | YES |  |
| created_by | character varying | YES |  |
| personal_information | text | YES |  |
| nationality | character varying | YES |  |
| preferred_language | character varying | YES |  |
| province | character varying | YES |  |
| email | character varying | YES |  |
| date_of_birth | date | YES |  |
| nickname | character varying | YES |  |
| reserve_215 | text | YES |  |
| reserve_216 | text | YES |  |
| reserve_217 | text | YES |  |
| reserve_218 | text | YES |  |
| reserve_219 | text | YES |  |
| reserve_220 | text | YES |  |
| reserve_221 | text | YES |  |
| reserve_222 | text | YES |  |
| reserve_223 | text | YES |  |
| reserve_224 | text | YES |  |
| reserve_225 | text | YES |  |
| reserve_226 | text | YES |  |
| reserve_227 | text | YES |  |
| reserve_228 | text | YES |  |
| reserve_229 | text | YES |  |
| reserve_230 | text | YES |  |
| reserve_231 | text | YES |  |
| reserve_232 | text | YES |  |
| reserve_233 | text | YES |  |
| reserve_234 | text | YES |  |
| reserve_235 | text | YES |  |
| reserve_236 | text | YES |  |
| reserve_237 | text | YES |  |
| reserve_238 | text | YES |  |
| reserve_239 | text | YES |  |
| reserve_240 | text | YES |  |
| reserve_241 | text | YES |  |
| reserve_242 | text | YES |  |
| reserve_243 | text | YES |  |
| reserve_244 | text | YES |  |
| reserve_245 | text | YES |  |
| reserve_246 | text | YES |  |
| reserve_247 | text | YES |  |
| reserve_248 | text | YES |  |
| reserve_249 | text | YES |  |
| reserve_250 | text | YES |  |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### trusted_facebook_pages

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| page_id | text | NO |  |
| page_name | text | YES |  |
| page_username | text | YES |  |
| page_url | text | YES |  |
| category | text | NO | 'club'::text |
| active | boolean | NO | true |
| resolved_at | timestamp with time zone | NO | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### user_accounts

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| account_id | bigint | NO |  |
| sas_id | text | NO |  |
| login_method | text | NO |  |
| provider_id | text | YES |  |
| email | text | YES |  |
| email_verified | boolean | YES | false |
| first_name | text | YES |  |
| last_name | text | YES |  |
| full_name | text | YES |  |
| profile_picture_path | text | YES |  |
| verification_code | text | YES |  |
| verification_code_expires | timestamp with time zone | YES |  |
| password_hash | text | YES |  |
| provider_data | jsonb | YES |  |
| is_active | boolean | YES | true |
| last_login | timestamp with time zone | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

### user_sessions

**Columns**
| Column | Data type | Nullable | Default |
|--------|-----------|----------|---------|
| session_id | text | NO |  |
| account_id | bigint | NO |  |
| sas_id | text | NO |  |
| login_method | text | NO |  |
| created_at | timestamp with time zone | NO | now() |
| expires_at | timestamp with time zone | NO |  |
| last_activity | timestamp with time zone | NO | now() |
| user_agent | text | YES |  |
| ip_address | text | YES |  |
| is_active | boolean | YES | true |

**Primary key:** See Appendix 1A. **Indexes:** See Appendix 1B. **Constraints:** See Appendix 1C.

---

### Appendix 1A — Primary keys (LIVE public tables)

| Table | Primary key column(s) |
|-------|------------------------|
| audit_flags | flag_id |
| boats | boat_id |
| class_age_limits | id |
| class_aliases | alias |
| class_candidates | seen_text |
| class_group_members | group_id, class_id |
| class_groups | group_id |
| class_sailor_master_list | id |
| classes | class_id |
| club_aliases | alias |
| clubs | club_id |
| entries | entry_id |
| h2h_matrix_cache | id |
| imports_log | import_id |
| main_scores | id |
| master_list | id |
| member_roles | person_key, role_code |
| name_alias | base |
| people_club_history | person_key, club_id |
| processed_regattas | id |
| races | race_id |
| ranking_history | id |
| ranking_standings | id |
| regatta_blocks | block_id |
| regatta_public_mentions | id |
| regattas | regatta_id |
| result_match_overrides | result_id |
| result_match_suggestions | suggestion_id |
| results | result_id |
| results_staging | staging_id |
| roles | role_code |
| sailor_media_delete_requests | id |
| sailor_media_score | sa_id |
| sailor_projection_meta | sailor_id |
| sailor_public_mentions | id |
| sas_id_personal | (no PK; UNIQUE on sa_sailing_id) |
| sas_id_personal_backup | (structure as sas_id_personal) |
| schools | school_id |
| scrape_log | id |
| standing_list | id |
| standings_recalc_queue | class_name_normalized |
| temp_people | temp_id |
| trusted_facebook_pages | page_id |
| user_accounts | account_id |
| user_sessions | session_id |

### Appendix 1B — Indexes (LIVE public schema)

All indexes from `pg_indexes` where `schemaname = 'public'`. Each table has at least one index (primary key or unique). Non-PK indexes include: audit_flags (idx_audit_result_id, idx_audit_status); boats (idx_boats_class_name, idx_boats_sail_number); classes (idx_classes_class_name, ux_classes_name); clubs (ix_clubs_abbrev_lower, ix_clubs_full_lower, ux_clubs_abbrev); entries (idx_entries_regatta, idx_entries_sail_number); results (idx_results_helm_sas, idx_results_crew_sas, idx_results_regatta_id, ix_results_regatta, ix_results_helm_ids, ix_results_crew_ids, ix_results_class, ix_results_club, idx_results_sail_number_trgm, idx_results_boat_name_trgm, idx_results_sailor_regatta_helm, idx_results_sailor_regatta_crew, ix_results_racejson); sailor_public_mentions (idx_sailor_public_mentions_sa_id, idx_sailor_public_mentions_sa_id_url, idx_sailor_public_mentions_published_at, idx_sailor_public_mentions_is_valid); sas_id_personal (sas_id_personal_new_sa_sailing_id_key UNIQUE on sa_sailing_id); user_accounts (idx_user_accounts_sas_id, idx_user_accounts_email, idx_user_accounts_provider_id); user_sessions (idx_user_sessions_account_id, idx_user_sessions_sas_id, idx_user_sessions_expires). Full definitions: run `SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;` on LIVE.

### Appendix 1C — Constraints (LIVE public schema)

**Foreign keys:** audit_flags (result_id → results, entry_id → entries); class_aliases (class_id → classes); class_group_members (group_id → class_groups, class_id → classes); classes (parent_id → classes); club_aliases (club_id → clubs); entries (regatta_id → regattas); imports_log (regatta_id → regattas); people_club_history (club_id → clubs); regatta_blocks (regatta_id → regattas, class_id → classes); regattas (host_club_id → clubs); result_match_overrides (result_id → results); result_match_suggestions (result_id → results); results (regatta_id → regattas, block_id → regatta_blocks, class_id → classes, club_id → clubs, entry_id → entries); temp_people (preferred_club_id → clubs); user_accounts (sas_id → sas_id_personal via fk_sas_id); user_sessions (account_id → user_accounts).

**Unique constraints:** boats (sail_number, class_name); class_age_limits (class_name); class_groups (group_name); clubs (club_abbrev); h2h_matrix_cache (class_name, sailor_a_id, sailor_b_id); main_scores (sailor_id, class_name); master_list (class_name, sailor_id); processed_regattas (class_name, regatta_id); regatta_public_mentions (url); result_match_suggestions (result_id, role, candidate_id); sailor_media_delete_requests (confirm_token); sailor_public_mentions (sa_id, url); sas_id_personal (sa_sailing_id); schools (school_abbrev); standing_list (class_name, sailor_id); temp_people (temp_code, official_sa_sailing_id, normalized_name); user_accounts (sas_id, login_method, provider_id).

**Check constraints:** Per-table NOT NULL and domain checks (e.g. audit_flags severity/status; sailor_media_score valid_status; result_match_suggestions role_check; trusted_facebook_pages category_check; user_accounts login_method_check; regatta_public_mentions type_check; sailor_public_mentions type_check, source_added_check). Full list on LIVE: `SELECT conname, conrelid::regclass, pg_get_constraintdef(oid) FROM pg_constraint WHERE connamespace = 'public'::regnamespace AND contype = 'c';`

---

## 2. Foreign Key Relationship Map

**LIVE verification:** Hostname `vm103zuex.yourlocaldomain.com`, active database `sailors_master`.

### 2.1 Complete list of all 24 foreign keys

| # | Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|---|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| 1 | audit_flags_entry_id_fkey | audit_flags | entry_id | entries | entry_id | SET NULL | NO ACTION |
| 2 | audit_flags_result_id_fkey | audit_flags | result_id | results | result_id | CASCADE | NO ACTION |
| 3 | class_aliases_class_id_fkey | class_aliases | class_id | classes | class_id | NO ACTION | NO ACTION |
| 4 | class_group_members_class_id_fkey | class_group_members | class_id | classes | class_id | CASCADE | NO ACTION |
| 5 | class_group_members_group_id_fkey | class_group_members | group_id | class_groups | group_id | CASCADE | NO ACTION |
| 6 | classes_parent_id_fkey | classes | parent_id | classes | class_id | NO ACTION | NO ACTION |
| 7 | club_aliases_club_id_fkey | club_aliases | club_id | clubs | club_id | NO ACTION | NO ACTION |
| 8 | entries_regatta_id_fkey | entries | regatta_id | regattas | regatta_id | CASCADE | NO ACTION |
| 9 | imports_log_regatta_id_fkey | imports_log | regatta_id | regattas | regatta_id | SET NULL | NO ACTION |
| 10 | member_roles_role_code_fkey | member_roles | role_code | roles | role_code | NO ACTION | NO ACTION |
| 11 | people_club_history_club_id_fkey | people_club_history | club_id | clubs | club_id | CASCADE | NO ACTION |
| 12 | races_regatta_id_fkey | races | regatta_id | regattas | regatta_id | CASCADE | NO ACTION |
| 13 | regatta_blocks_class_id_fkey | regatta_blocks | class_id | classes | class_id | NO ACTION | NO ACTION |
| 14 | regatta_blocks_regatta_id_fkey | regatta_blocks | regatta_id | regattas | regatta_id | NO ACTION | NO ACTION |
| 15 | regattas_host_club_id_fkey | regattas | host_club_id | clubs | club_id | NO ACTION | NO ACTION |
| 16 | result_match_overrides_result_id_fkey | result_match_overrides | result_id | results | result_id | CASCADE | NO ACTION |
| 17 | result_match_suggestions_result_id_fkey | result_match_suggestions | result_id | results | result_id | CASCADE | NO ACTION |
| 18 | results_block_id_fkey | results | block_id | regatta_blocks | block_id | NO ACTION | NO ACTION |
| 19 | results_class_id_fkey | results | class_id | classes | class_id | NO ACTION | NO ACTION |
| 20 | results_club_id_fkey | results | club_id | clubs | club_id | NO ACTION | NO ACTION |
| 21 | results_entry_id_fkey | results | entry_id | entries | entry_id | SET NULL | NO ACTION |
| 22 | results_regatta_id_fkey | results | regatta_id | regattas | regatta_id | NO ACTION | NO ACTION |
| 23 | temp_people_preferred_club_id_fkey | temp_people | preferred_club_id | clubs | club_id | NO ACTION | NO ACTION |
| 24 | fk_sas_id | user_accounts | sas_id | sas_id_personal | sa_sailing_id | CASCADE | NO ACTION |
| 25 | user_sessions_account_id_fkey | user_sessions | account_id | user_accounts | account_id | CASCADE | NO ACTION |

(Complete list: 25 foreign keys on LIVE public schema.)

### 2.2 Grouped by logical domain

#### regattas

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| entries_regatta_id_fkey | entries | regatta_id | regattas | regatta_id | CASCADE | NO ACTION |
| imports_log_regatta_id_fkey | imports_log | regatta_id | regattas | regatta_id | SET NULL | NO ACTION |
| races_regatta_id_fkey | races | regatta_id | regattas | regatta_id | CASCADE | NO ACTION |
| regatta_blocks_regatta_id_fkey | regatta_blocks | regatta_id | regattas | regatta_id | NO ACTION | NO ACTION |
| results_regatta_id_fkey | results | regatta_id | regattas | regatta_id | NO ACTION | NO ACTION |
| regattas_host_club_id_fkey | regattas | host_club_id | clubs | club_id | NO ACTION | NO ACTION |

#### race_results (results and related)

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| results_block_id_fkey | results | block_id | regatta_blocks | block_id | NO ACTION | NO ACTION |
| results_class_id_fkey | results | class_id | classes | class_id | NO ACTION | NO ACTION |
| results_club_id_fkey | results | club_id | clubs | club_id | NO ACTION | NO ACTION |
| results_entry_id_fkey | results | entry_id | entries | entry_id | SET NULL | NO ACTION |
| results_regatta_id_fkey | results | regatta_id | regattas | regatta_id | NO ACTION | NO ACTION |
| audit_flags_result_id_fkey | audit_flags | result_id | results | result_id | CASCADE | NO ACTION |
| result_match_overrides_result_id_fkey | result_match_overrides | result_id | results | result_id | CASCADE | NO ACTION |
| result_match_suggestions_result_id_fkey | result_match_suggestions | result_id | results | result_id | CASCADE | NO ACTION |

#### sailors / people

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| fk_sas_id | user_accounts | sas_id | sas_id_personal | sa_sailing_id | CASCADE | NO ACTION |
| member_roles_role_code_fkey | member_roles | role_code | roles | role_code | NO ACTION | NO ACTION |
| people_club_history_club_id_fkey | people_club_history | club_id | clubs | club_id | CASCADE | NO ACTION |

#### clubs

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| club_aliases_club_id_fkey | club_aliases | club_id | clubs | club_id | NO ACTION | NO ACTION |
| people_club_history_club_id_fkey | people_club_history | club_id | clubs | club_id | CASCADE | NO ACTION |
| regattas_host_club_id_fkey | regattas | host_club_id | clubs | club_id | NO ACTION | NO ACTION |
| results_club_id_fkey | results | club_id | clubs | club_id | NO ACTION | NO ACTION |
| temp_people_preferred_club_id_fkey | temp_people | preferred_club_id | clubs | club_id | NO ACTION | NO ACTION |

#### users

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| fk_sas_id | user_accounts | sas_id | sas_id_personal | sa_sailing_id | CASCADE | NO ACTION |

#### sessions

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| user_sessions_account_id_fkey | user_sessions | account_id | user_accounts | account_id | CASCADE | NO ACTION |

#### audit / logging

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| audit_flags_entry_id_fkey | audit_flags | entry_id | entries | entry_id | SET NULL | NO ACTION |
| audit_flags_result_id_fkey | audit_flags | result_id | results | result_id | CASCADE | NO ACTION |
| imports_log_regatta_id_fkey | imports_log | regatta_id | regattas | regatta_id | SET NULL | NO ACTION |

#### classes (hierarchy and references)

| Constraint name | Source table | Source column(s) | Target table | Target column(s) | ON DELETE | ON UPDATE |
|-----------------|--------------|------------------|--------------|-----------------|----------|-----------|
| class_aliases_class_id_fkey | class_aliases | class_id | classes | class_id | NO ACTION | NO ACTION |
| class_group_members_class_id_fkey | class_group_members | class_id | classes | class_id | CASCADE | NO ACTION |
| class_group_members_group_id_fkey | class_group_members | group_id | class_groups | group_id | CASCADE | NO ACTION |
| classes_parent_id_fkey | classes | parent_id | classes | class_id | NO ACTION | NO ACTION |
| regatta_blocks_class_id_fkey | regatta_blocks | class_id | classes | class_id | NO ACTION | NO ACTION |
| results_class_id_fkey | results | class_id | classes | class_id | NO ACTION | NO ACTION |

### 2.3 Tables with no foreign keys (outbound)

Tables in `public` that do not reference any other table via a foreign key (no outbound FK):

- audit_flags (has outbound: entry_id, result_id — so it has FKs)
- boats
- class_age_limits
- class_aliases (has class_id)
- class_candidates
- class_group_members (has group_id, class_id)
- class_groups
- class_sailor_master_list
- classes (has parent_id)
- club_aliases (has club_id)
- clubs
- entries (has regatta_id)
- h2h_matrix_cache
- imports_log (has regatta_id)
- main_scores
- master_list
- member_roles (has role_code)
- name_alias
- people_club_history (has club_id)
- processed_regattas
- races (has regatta_id)
- ranking_history
- ranking_standings
- regatta_blocks (has regatta_id, class_id)
- regatta_public_mentions
- regattas (has host_club_id)
- result_match_overrides (has result_id)
- result_match_suggestions (has result_id)
- results (has regatta_id, block_id, class_id, club_id, entry_id)
- results_staging
- roles
- sailor_media_delete_requests
- sailor_media_score
- sailor_projection_meta
- sailor_public_mentions
- sas_id_personal
- sas_id_personal_backup
- schools
- scrape_log
- standing_list
- standings_recalc_queue
- temp_people (has preferred_club_id)
- trusted_facebook_pages
- user_accounts (has sas_id)
- user_sessions (has account_id)

**Tables with no outbound foreign keys (never appear as source of an FK):**

boats, class_age_limits, class_candidates, class_groups, class_sailor_master_list, clubs, h2h_matrix_cache, main_scores, master_list, name_alias, processed_regattas, ranking_history, ranking_standings, regatta_public_mentions, results_staging, roles, sailor_media_delete_requests, sailor_media_score, sailor_projection_meta, sailor_public_mentions, sas_id_personal, sas_id_personal_backup, schools, scrape_log, standing_list, standings_recalc_queue, trusted_facebook_pages.

(27 tables.)

### 2.4 Tables with more than 3 inbound references (high coupling risk)

Inbound FK count (number of foreign keys that reference this table):

- **regattas:** 5 (entries, imports_log, races, regatta_blocks, results).
- **classes:** 5 (class_aliases, class_group_members, classes.parent_id, regatta_blocks, results).
- **clubs:** 5 (club_aliases, people_club_history, regattas, results, temp_people).
- **results:** 3 (audit_flags, result_match_overrides, result_match_suggestions).

**Tables with >3 inbound references:** regattas, classes, clubs. (results has exactly 3.)

### 2.5 Orphan-risk tables (no inbound references)

Tables that are never the target of any foreign key (no other table references them via FK):

boats, class_age_limits, class_candidates, class_groups, class_sailor_master_list, club_aliases, h2h_matrix_cache, imports_log, main_scores, master_list, member_roles, name_alias, people_club_history, processed_regattas, races, ranking_history, ranking_standings, regatta_public_mentions, result_match_overrides, result_match_suggestions, results_staging, sailor_media_delete_requests, sailor_media_score, sailor_projection_meta, sailor_public_mentions, sas_id_personal_backup, schools, scrape_log, standing_list, standings_recalc_queue, temp_people, trusted_facebook_pages.

(32 tables have no inbound FK. Tables that are referenced by at least one FK: entries, results, classes, class_groups, regattas, clubs, roles, regatta_blocks, sas_id_personal, user_accounts.)

---

## 3. ORM / Model Definitions (Application Layer Mapping)

### 3.1 ORM usage

The application does **not** use any ORM for database access. There are no SQLAlchemy model classes, no Django ORM models, and no other table-mapping ORM layer. All database access is performed via **psycopg2** and **raw SQL** in `api.py` (and in standalone scripts where applicable). Connection is obtained via a DB URL (e.g. from environment) and cursors execute parameterised SQL strings.

**Pydantic** is used only for request/response schemas (DTOs), not for table mapping:

- **TempPersonCreate** (Pydantic BaseModel): request body for `POST /api/people/temp`; fields `full_name`, `club_code`, `notes`. Not backed by a table; used to call `create_temp_person(%s,%s,%s)`.
- **ResultPatch** (Pydantic BaseModel): request body for `PATCH /api/result/{result_id}`; fields `helm_key`, `crew_key`, `sail_number`, `club_code`, `class_name`, `boat_name`. Not backed by a table; used to call `set_result_person` and similar and to build ad-hoc UPDATEs on `results`.

No other Pydantic models in the application represent database tables. There are no hybrid properties, no ORM relationships, no ORM cascades, and no ORM save/update/delete overrides.

### 3.2 Tables that exist in the database but have no ORM model

Every table in the LIVE database is accessed only by raw SQL. There is no ORM model class for any table. The following are the **public base tables** present on LIVE (hostname: vm103zuex.yourlocaldomain.com, database: sailors_master) at the time of this baseline. All of them have **no ORM model**:

- audit_flags  
- boats  
- class_age_limits  
- class_aliases  
- class_candidates  
- class_group_members  
- class_groups  
- class_sailor_master_list  
- classes  
- club_aliases  
- clubs  
- entries  
- h2h_matrix_cache  
- imports_log  
- main_scores  
- master_list  
- member_roles  
- name_alias  
- people_club_history  
- processed_regattas  
- races  
- ranking_history  
- ranking_standings  
- regatta_blocks  
- regatta_public_mentions  
- regattas  
- result_match_overrides  
- result_match_suggestions  
- results  
- results_staging  
- roles  
- sailor_media_delete_requests  
- sailor_media_score  
- sailor_projection_meta  
- sailor_public_mentions  
- sas_id_personal  
- sas_id_personal_backup  
- schools  
- scrape_log  
- standing_list  
- standings_recalc_queue  
- temp_people  
- trusted_facebook_pages  
- user_accounts  
- user_sessions  

**Note on `sailing_id`:** Application code in `api.py` references a table (or object) named **sailing_id** in multiple places (e.g. `SELECT`/`UPDATE` in `bulk_auto_match_regatta`, member-finder scrape `INSERT INTO sailing_id`, `api_sa_id_stats` fallback `SELECT MAX(sa_sailing_id) FROM public.sailing_id`). On LIVE there is **no base table** named `sailing_id`. Only **sas_id_personal** exists as a base table for sailor identity. The code path that uses `sailing_id` may be intended for another environment, or may rely on a view/synonym not present in the baseline schema dump; on LIVE, `api_sa_id_stats` falls back to `sas_id_personal` when `sailing_id` is unavailable.

**Note on `result_participants`:** The application executes `INSERT INTO public.result_participants (result_id, person_id, role)` in `api.py`. The LIVE schema list above does **not** include a base table named `result_participants`. Either the table exists only in another schema/environment, or it is a view, or the insert is unused on LIVE.

### 3.3 Models that reference tables without foreign key constraints

Not applicable: there are no ORM models. The database has defined foreign key constraints as documented in Section 2; the application does not enforce relationships via an ORM layer.

### 3.4 Cascade deletes and delete behaviour in application code

There are no ORM models, so there is no ORM-level cascade or override of default delete behaviour. The following **explicit DELETE or delete-like behaviour** is implemented in application code (raw SQL):

1. **sailor_public_mentions**  
   - `DELETE FROM sailor_public_mentions WHERE sa_id::text = %s AND url = %s` (and variant with RETURNING).  
   - Used when a member deletes a media item (by URL) or when an admin confirms a delete via token.  
   - No application-level cascade to other tables; only this table is updated. The database does not define an ON DELETE CASCADE targeting this table from others.

2. **user_sessions**  
   - `DELETE FROM public.user_sessions` with conditions (e.g. by session id, or by account for logout, or for expiry).  
   - Used for logout and session invalidation.  
   - No application-level cascade; other tables are not explicitly deleted in the same flow. DB has `user_sessions_account_id_fkey` with ON DELETE CASCADE from `user_accounts`, so when an account is deleted at DB level, sessions are removed by the database.

3. **sas_id_personal**  
   - `DELETE FROM public.sas_id_personal` for a specific row (e.g. placeholder row when linking a Facebook identity to a real SAS ID).  
   - Application performs this delete explicitly; no other tables are deleted in the same code path. The database has `user_accounts.sas_id` → `sas_id_personal.sa_sailing_id` with ON DELETE CASCADE, so deletion of a row in `sas_id_personal` can cause the database to cascade to `user_accounts` (and possibly to `user_sessions` via account).

No other tables are targeted by explicit DELETE statements in the scanned `api.py` code. Database-level CASCADE behaviour is as documented in Section 2 (e.g. audit_flags, result_match_overrides, result_match_suggestions, people_club_history, class_group_members, user_sessions).

### 3.5 Tables and code paths by functional area

#### Regatta ingestion

Tables and code paths involved in regatta-related data ingestion, matching, and scraping:

- **results** — Updated and read in `bulk_auto_match_regatta` (club_id, helm_sa_sailing_id, crew_sa_sailing_id, helm_temp_id, crew_temp_id, match_status_helm, match_status_crew); `_ensure_snapshot_integrity` updates `as_at_time`; read in many endpoints (standings, search, site stats, etc.). Staging/import pipelines may use **results_staging** and then move data into **results** (not fully traced in this baseline).
- **regattas** — Read for regatta_id, event_name, host_club_id, dates; referenced in joins for standings, search, and news helpers. Not directly inserted/updated in the ingestion paths scanned; `as_at_time` is documented as set explicitly elsewhere, not by bulk_auto_match.
- **regatta_blocks** — Read and joined in bulk_auto_match and standings logic; updated in at least one path (`UPDATE regatta_blocks` around line 4240). Used for block-level grouping of results.
- **temp_people** — Used for temporary person identities when no SAS ID match is found; `_ensure_temp_person` inserts/updates via `INSERT INTO temp_people ... ON CONFLICT (normalized_name) DO UPDATE`; results reference temp persons via helm_temp_id/crew_temp_id.
- **sailing_id** / **sas_id_personal** — `bulk_auto_match_regatta` updates `sailing_id` (home_club_code) when a match is found; member-finder scrape code inserts into `sailing_id` and reads counts from it. On LIVE, only `sas_id_personal` exists as a base table; see note in 3.2.
- **clubs** — Read in `_resolve_club` (and aliases via club_aliases) to set `results.club_id` during bulk_auto_match.
- **classes** — Referenced for class_id/class_name in results and regatta_blocks.
- **scrape_log** — Inserted/updated by member-finder scrape (before_scrape_count, after_scrape_count, added_count, status, message); read in post-scrape log endpoint.
- **processed_regattas**, **imports_log** — Likely used by import/ingest pipelines (regatta_id referenced in Section 2); not traced in detail in api.py for this baseline.
- **result_participants** — Application performs `INSERT INTO public.result_participants (result_id, person_id, role)`; table not in LIVE base table list (see 3.2).

No ORM models are used; all of the above are raw SQL and parameterised queries.

#### Host assignment

- **regattas.host_club_id** — Denormalised host club; read in many queries.
- **clubs** — Joined as `LEFT JOIN clubs c ON c.club_id = r.host_club_id` (or equivalent) to resolve host_club_code, host_club_name, host_club_slug for regatta pages, search, and site stats. No separate “host assignment” ORM or model; assignment of host club to a regatta is done outside the scanned api.py (e.g. during import or admin tooling). Application code only reads and displays host club.

#### Club activity status logic

- **people_club_history** — Exists in the database with foreign key to clubs (ON DELETE CASCADE). No references to **people_club_history** were found in the scanned Python code (api.py or the checked scripts). No application logic in this codebase implements “club activity status” using this table; such logic may exist in other scripts, jobs, or SQL only.

#### News feed generation

- **Latest News / landing news feed** — Served by `GET /api/news/latest` and populated by `_fetch_latest_news_pipeline()`. The pipeline does **not** read news items from a database table; it aggregates from external sources (primary SA sites, Facebook Graph API, SerpAPI, RSS), filters and sorts in memory, and caches results in memory and on disk (`news_latest_cache.json`). The following tables are used **only to supply inputs** to the pipeline (sailor names, regatta names, trusted pages), not to store the news items themselves:
  - **regattas** — `_get_recent_regatta_names()`: `SELECT event_name FROM regattas WHERE end_date >= (CURRENT_DATE - INTERVAL '5 months')` for search queries and local/international categorisation.
  - **results** — Used by `get_recent_podium_sailors()`, `_load_podium_sailors_from_large_regattas()` (helm_name, crew_name, rank, regatta_id), and by `_load_sailor_names_for_news()` (via union of helm_sa_sailing_id/crew_sa_sailing_id with regattas join).
  - **regatta_blocks** — Used in `_load_podium_sailors_from_large_regattas()` with results and regattas to identify “large” regattas and podium names.
  - **sas_id_personal** — `_load_sailor_names_for_news()`: `SELECT first_name, last_name FROM sas_id_personal` (or equivalent) and joined with IDs from results for name list; also used in podium sailor lookups.
  - **trusted_facebook_pages** — `_get_trusted_fb_pages()`: `SELECT page_id, page_name FROM trusted_facebook_pages WHERE active = true` for Facebook-based news fetching (LOCAL).
- **regatta_public_mentions** — Table exists in the database. It is **not** referenced in the news pipeline in api.py. A separate script (`check_media_status.py`) reads from `regatta_public_mentions` for status checks; it is not used for the landing “Latest News” feed generation in the API.
- **sailor_public_mentions** / **sailor_media_score** — Used for the sailor profile “Media” tab and media scores, not for the landing news feed.

No ORM models are used in any of the above; all access is raw SQL and in-memory/file cache.

---

## 4. Full Route Map (API Surface)

All routes are defined in **api.py**. No other route-defining files are used by the running application. (QUICK_SECURITY_FIXES.py contains commented/debug routes and is not the live app.)

For duplicate paths (same method + path registered more than once in api.py), the **last** registered handler is the one that runs; the table below documents the effective handler and notes when a path is overridden.

**Auth legend:**  
- **Public** — No session, token, or role check.  
- **Auth required** — Valid session (cookie or query `session`) required; session must match resource (e.g. sa_id) where applicable.  
- **Role-restricted** — Admin token (ADMIN_TOKEN / Authorization / Admin-Token) or localhost required.

**Write operations:** INSERT, UPDATE, DELETE are listed per route.

---

### 4.1 Route table

| # | Method | Path | Function name | Tables read | Tables written | INSERT | UPDATE | DELETE | SELECT only | Public | Auth required | Role-restricted | Modifies regattas | Modifies results | Modifies clubs | Modifies classes | Modifies sas_id_personal | Unprotected write |
|---|--------|------|---------------|-------------|----------------|--------|--------|--------|-------------|--------|---------------|-----------------|--------------------|------------------|----------------|------------------|---------------------------|--------------------|
| 1 | GET | / | _root_redirect | (optional: sas_id_personal for redirect) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 2 | GET | /index.html | _index_redirect | (optional: sas_id_personal for redirect) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 3 | GET | /sailor/{slug} | _sailor_spa | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 4 | HEAD | /sailor/{slug} | _sailor_spa | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 5 | GET | /regatta/results.html | _regatta_results_html | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 6 | GET | /regatta/class/class-results.html | _regatta_class_results_html | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 7 | GET | /regatta/class/podium/podium.html | _regatta_podium_html | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 8 | GET | /about | _about_html | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 9 | GET | /regatta/{slug} | _regatta_standalone | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 10 | HEAD | /regatta/{slug} | _regatta_standalone | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 11 | GET | /club/{slug} | _club_standalone | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 12 | HEAD | /club/{slug} | _club_standalone | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 13 | GET | /sailing/{slug} | _sailing_to_sailor_redirect | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 14 | GET | /api/health | health | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 15 | GET | /api/site-stats | api_site_stats | results, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 16 | GET | /api/site-stats-audit | api_site_stats_audit | results, sas_id_personal, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 17 | GET | /api/thumbnail | api_thumbnail | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 18 | GET | /api/sailing-news | api_sailing_news | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 19 | GET | /api/news/sailing-magazine | api_news_sailing_magazine | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 20 | GET | /api/news/latest | api_news_latest | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 21 | POST | /api/news/refresh | api_news_refresh | (pipeline: regattas, results, regatta_blocks, sas_id_personal, trusted_facebook_pages) | — | No | No | No | Yes | No | No | Yes | No | No | No | No | No | No |
| 22 | GET | /api/classes | api_classes | classes, information_schema | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 23 | GET | /api/sa-id-stats | api_sa_id_stats | sailing_id, sas_id_personal, information_schema | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 24 | GET | /api/member/{sa_id}/public-mentions | api_member_public_mentions | sailor_public_mentions, sailor_media_score | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 25 | POST | /api/member/{sa_id}/add-media | api_member_add_media | sailor_public_mentions, user_sessions (session check), (get_sailor_name) | sailor_public_mentions | Yes | No | No | No | No | Yes | No | No | No | No | No | No | No |
| 26 | POST | /api/member/{sa_id}/refresh-media-item | api_member_refresh_media_item | sailor_public_mentions, user_sessions | sailor_public_mentions | No | Yes | No | No | No | Yes | No | No | No | No | No | No | No |
| 27 | PATCH | /api/member/{sa_id}/media | api_member_edit_media | sailor_public_mentions, user_sessions | sailor_public_mentions | No | Yes | No | No | No | Yes | No | No | No | No | No | No | No |
| 28 | DELETE | /api/member/{sa_id}/media | api_member_delete_media | sailor_public_mentions, user_sessions | sailor_public_mentions, sailor_media_delete_requests | Yes (delete_requests) | No | Yes (mentions) | No | No | Yes | No | No | No | No | No | No | No |
| 29 | GET | /api/admin/confirm-media-delete | api_admin_confirm_media_delete | sailor_media_delete_requests, sailor_public_mentions | sailor_public_mentions, sailor_media_delete_requests | No | Yes | Yes | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 30 | GET | /api/sailors/{sa_id}/media | api_sailors_media | (delegates to api_member_public_mentions) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 31 | GET | /api/member/{sa_id}/highlights | api_member_highlights | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No | No |
| 32 | GET | /api/member/{sa_id}/activity | api_member_activity | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 33 | GET | /api/member/{sa_id}/roles | api_member_roles | sa_ids, member_roles, roles | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 34 | GET | /api/member/{sa_id}/results | api_member_results | sas_id_personal, results, regattas, clubs, regatta_blocks | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 35 | GET | /api/results/lite | api_results_lite | (results, regattas, etc. via internal logic) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 36 | GET | /api/results/full | api_results_full | (results, regattas, etc.) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 37 | GET | /api/results/regatta/{regatta_id}/class/{class_id} | api_results_regatta_class | results, regatta_blocks, classes, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 38 | GET | /api/results/regatta/{regatta_id}/class/{class_id}/ | api_results_regatta_class | results, regatta_blocks, classes, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 39 | GET | /api/sa-id-stats | api_sa_id_stats | (duplicate path; same as #23; later registration may override) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 40 | GET | /api/classes | api_list_classes | classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 41 | GET | /api/provinces | api_list_provinces | provinces (view) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 42 | GET | /api/roles | api_list_roles | roles | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 43 | GET | /api/clubs | api_list_clubs | clubs | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 44 | GET | /api/member/search | api_search_members | sa_ids, id_aliases, member_roles | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 45 | POST | /api/id/temp | create_temp_id | (create_temp_person: temp_people) | temp_people (via function) | Yes | Yes (ON CONFLICT) | No | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 46 | POST | /api/id/promote | promote_temp | (promote_temp_alias_to_sas) | (function: temp_people / id resolution) | Yes | Yes | No | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 47 | POST | /api/result/attach-person | attach_person_to_result | (resolve_person_by_identifier) | result_participants | Yes | No | No | No | Yes | No | No | No | Yes (attach) | No | No | No | **Yes** |
| 48 | GET | /api/people/search | api_people_search | (delegates to api_search) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 49 | POST | /api/result/{result_id}/set_person | api_set_person | — | results | No | Yes | No | No | Yes | No | No | No | Yes | No | No | No | **Yes** |
| 50 | POST | /api/people/temp | create_temp | (create_temp_person) | temp_people (via function) | Yes | Yes | No | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 51 | PATCH | /api/result/{result_id} | patch_result | results | results | No | Yes | No | No | Yes | No | No | No | Yes | No | No | No | **Yes** |
| 52 | PATCH | /api/result/{result_id}/race | patch_race_score | results, regatta_blocks | results, regatta_blocks | No | Yes | No | No | Yes | No | No | No | Yes | No | No | No | **Yes** |
| 53 | GET | /api/clubs | list_clubs | clubs | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 54 | GET | /api/classes | list_classes | classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 55 | GET | /api/sa-id-stats | sa_id_stats | sailing_id, temp_people, scrape_log | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 56 | POST | /api/scrape-log/pre-scrape | log_pre_scrape | sailing_id | scrape_log | Yes | No | No | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 57 | POST | /api/run-daily-scrape | run_daily_scrape | sailing_id, scrape_log | sailing_id, scrape_log | Yes | Yes | No | No | Yes | No | No | No | No | No | No | Yes (sailing_id) | **Yes** |
| 58 | POST | /api/scrape-log/post-scrape | log_post_scrape | scrape_log | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 59 | GET | /api/search | api_search | sas_id_personal, results, regattas, clubs, regatta_blocks, classes, boats (optional) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 60 | GET | /api/isp-codes | api_isp_codes | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No | No |
| 61 | GET | /api/regattas/with-counts | api_regattas_with_counts | regattas, results, clubs | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 62 | GET | /api/regatta/{regatta_id}/class-entries | api_regatta_class_entries | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 63 | GET | /api/regatta/{regatta_id} | api_regatta | regattas, results, clubs, regatta_blocks, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 64 | GET | /api/regatta/{regatta_id}/podium.png | api_regatta_podium_png | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 65 | GET | /api/regattas/{regatta_id}/classes/{class_id}/results | api_regattas_class_results | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 66 | GET | /api/regattas/{regatta_id}/classes/{class_id}/podium | api_regattas_class_podium | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 67 | GET | /api/regattas/class/podium/overall/{overall_id}/class/{class_id}/regatta/{regatta_id} | api_regattas_class_podium_alt | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 68 | GET | /api/regattas/class/results/overall/{overall_id}/class/{class_id}/regatta/{regatta_id} | api_regattas_class_results_alt | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 69 | GET | /api/sailor/resolve | api_sailor_resolve | sas_id_personal, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 70 | GET | /api/sailor/results/{slug} | api_sailor_results_by_slug | sas_id_personal, results, regattas, clubs, regatta_blocks | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 71 | GET | /api/results/sailor/{slug} | api_results_sailor_by_slug | (same as sailor results) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 72 | GET | /api/results/sailor/{slug}/ | api_results_sailor_by_slug | (same) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 73 | GET | /api/regatta/results/{slug} | api_regatta_results_by_slug | regattas, results, regatta_blocks, classes, clubs | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 74 | GET | /api/sailor/{sailor_id} | api_sailor_details | sas_id_personal, results, regattas, clubs, regatta_blocks | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 75 | GET | /api/standings | api_standings | results, regatta_blocks, regattas, classes, sas_id_personal (or sailing_id) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 76 | GET | /api/open-regattas | api_open_regattas | regattas, results, regatta_blocks | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 77 | GET | /api/regatta/{regatta_id}/participants-classes | api_regatta_participants_classes | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 78 | GET | /api/standings/db | api_standings_db | ranking_standings, ranking_history, classes, etc. | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 79 | GET | /auth/session | check_session | user_sessions, sas_id_personal, sailing_id | user_sessions | No | No | Yes (expired) | No | Yes | No | No | No | No | No | No | No | **Yes** (DELETE expired) |
| 80 | POST | /auth/login | login | user_accounts, sas_id_personal, sailing_id | user_sessions | Yes | No | No | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 81 | POST | /auth/logout | logout | — | user_sessions | No | No | Yes | No | Yes | No | No | No | No | No | No | No | No | **Yes** |
| 82 | GET | /auth/facebook | facebook_auth | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 83 | GET | /auth/facebook/callback | facebook_auth_callback | user_accounts, sas_id_personal | user_accounts, user_sessions | Yes | No | No | No | Yes | No | No | No | No | No | No | No | **Yes** |
| 84 | POST | /profiles/search | profiles_search | (delegates to _perform_sailor_search: sas_id_personal, results, etc.) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 85 | GET | /api/facebook/search-sailors | facebook_search_sailors | (sas_id_personal, results, etc. via _perform_sailor_search) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 86 | GET | /api/facebook/search-sailors | facebook_search_sailors | (duplicate path) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 87 | POST | /api/facebook/confirm-link | facebook_confirm_link | user_accounts | user_accounts, sas_id_personal, user_sessions | Yes | Yes | Yes (sas_id_personal placeholder) | No | Yes | No | No | No | No | No | Yes | **Yes** |
| 88 | POST | /api/register-account | register_account | user_accounts | user_accounts, sas_id_personal, user_sessions | Yes | Yes | No | No | Yes | No | No | No | No | No | No | Yes | **Yes** |
| 89 | GET | /api/open-regattas | api_open_regattas | regattas, results, regatta_blocks | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 90 | GET | /api/regatta/{regatta_id}/participants-classes | api_regatta_participants_classes | results, regatta_blocks, regattas, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 91 | GET | /api/boat/classes/{sail_number} | boat_classes | results, boats, classes | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 92 | GET | /api/boat/info/{sail_number}/{class_name} | boat_info | boats, results, classes, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 93 | GET | /api/boat/pedigree/{sail_number}/{class_name} | boat_pedigree | boats, results, classes, regattas, regatta_blocks | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 94 | GET | /api/class_sailors/{class_name} | class_sailors | class_sailor_master_list, classes, results, sas_id_personal, regattas | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 95 | GET | /api/club-logo/{code} | api_club_logo | clubs | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 96 | GET | /sailingsa/news | redirect_sailingsa_news | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 97 | GET | /sailingsa | redirect_sailingsa_root | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 98 | GET | /sailingsa/ | redirect_sailingsa_root | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 99 | GET | /sailingsa/frontend | redirect_sailingsa_root | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 100 | GET | /sailingsa/frontend/ | redirect_sailingsa_root | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 101 | GET | /admin/regatta_viewer.html | serve_admin_regatta_viewer | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 102 | GET | /admin/search.html | serve_admin_search | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 103 | GET | /admin/boat_pedigree.html | serve_admin_boat_pedigree | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 104 | GET | /regatta_viewer.html | redirect_regatta_viewer | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 105 | GET | /search.html | redirect_search | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 106 | GET | /boat_pedigree.html | redirect_boat_pedigree | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 107 | GET | /sitemap.xml | serve_sitemap_xml | (sas_id_personal/slugs, regattas/slugs via helpers) | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No |
| 108 | GET | /robots.txt | serve_robots_txt | — | — | No | No | No | Yes | Yes | No | No | No | No | No | No | No | No | No |

---

### 4.2 Routes that modify regattas

None. No route performs INSERT or UPDATE on the **regattas** table. (patch_race_score updates **regatta_blocks** only: races_sailed, discard_count.)

---

### 4.3 Routes that modify results

- **POST /api/result/attach-person** (attach_person_to_result) — INSERT into result_participants (result linkage).
- **POST /api/result/{result_id}/set_person** (api_set_person) — UPDATE results (helm_sa_sailing_id, crew_sa_sailing_id, helm_temp_id, crew_temp_id, match_status_*, helm_name, crew_name).
- **PATCH /api/result/{result_id}** (patch_result) — UPDATE results (sail_number, club_raw, class_original, boat_name, helm/crew via set_result_person); calls _ensure_snapshot_integrity (UPDATE results SET as_at_time).
- **PATCH /api/result/{result_id}/race** (patch_race_score) — UPDATE results (race_scores, total_points_raw, nett_points_raw, rank, discards) and UPDATE regatta_blocks (races_sailed, discard_count).

---

### 4.4 Routes that modify clubs

None. No route performs INSERT, UPDATE, or DELETE on the **clubs** table.

---

### 4.5 Routes that modify classes

None. No route performs INSERT, UPDATE, or DELETE on the **classes** table. (patch_race_score updates **regatta_blocks** only: races_sailed, discard_count.)

---

### 4.6 Routes that modify sas_id_personal

- **POST /api/run-daily-scrape** (run_daily_scrape) — INSERT into sailing_id (code path; on LIVE sailing_id may be absent and scrape may fail or use sas_id_personal).
- **POST /api/facebook/confirm-link** (facebook_confirm_link) — UPDATE user_accounts; DELETE from sas_id_personal (placeholder FB_* row); UPDATE sas_id_personal (email, phone_primary).
- **POST /api/register-account** (register_account) — UPDATE sas_id_personal (email, phone_primary).

---

### 4.7 Routes lacking auth protection that perform write operations

The following routes perform INSERT, UPDATE, or DELETE and do **not** require a valid session or admin token (they are public or use only a one-time token in URL for admin confirm):

| Method | Path | Function | Writes |
|--------|------|----------|--------|
| POST | /api/news/refresh | api_news_refresh | None (read-only pipeline); protected by admin token or localhost. |
| GET | /api/admin/confirm-media-delete | api_admin_confirm_media_delete | sailor_public_mentions (DELETE), sailor_media_delete_requests (UPDATE). **Public** — anyone with the one-time token (e.g. from email link) can perform the delete. |
| POST | /api/id/temp | create_temp_id | temp_people (via create_temp_person). **Unprotected.** |
| POST | /api/id/promote | promote_temp | (function: temp/sas resolution). **Unprotected.** |
| POST | /api/result/attach-person | attach_person_to_result | result_participants. **Unprotected.** |
| POST | /api/result/{result_id}/set_person | api_set_person | results. **Unprotected.** |
| POST | /api/people/temp | create_temp | temp_people (via create_temp_person). **Unprotected.** |
| PATCH | /api/result/{result_id} | patch_result | results. **Unprotected.** |
| PATCH | /api/result/{result_id}/race | patch_race_score | results, regatta_blocks. **Unprotected.** |
| POST | /api/scrape-log/pre-scrape | log_pre_scrape | scrape_log. **Unprotected.** |
| POST | /api/run-daily-scrape | run_daily_scrape | sailing_id, scrape_log. **Unprotected.** |
| GET | /auth/session | check_session | user_sessions (DELETE expired). **Unprotected** (delete is side effect of session check). |
| POST | /auth/login | login | user_sessions (INSERT). **Unprotected** (intended for login). |
| POST | /auth/logout | logout | user_sessions (DELETE). **Unprotected** (intended for logout). |
| GET | /auth/facebook/callback | facebook_auth_callback | user_accounts, user_sessions. **Unprotected** (OAuth callback). |
| POST | /api/facebook/confirm-link | facebook_confirm_link | user_accounts, sas_id_personal, user_sessions. **Unprotected.** |
| POST | /api/register-account | register_account | user_accounts, sas_id_personal, user_sessions. **Unprotected.** |

Summary: **Unprotected write routes** (no session or admin check) that modify application/regatta data: **POST /api/id/temp**, **POST /api/id/promote**, **POST /api/result/attach-person**, **POST /api/result/{result_id}/set_person**, **POST /api/people/temp**, **PATCH /api/result/{result_id}**, **PATCH /api/result/{result_id}/race**, **POST /api/scrape-log/pre-scrape**, **POST /api/run-daily-scrape**. **GET /api/admin/confirm-media-delete** is public but requires a one-time token sent by email; anyone with that link can delete the media item.

---

## 5. Regatta Ingestion Logic (Full Data Flow)

Sources: **api.py** and ingestion-related standalone Python scripts in the project root (e.g. add_regatta_*.py, add_regattas_*.py, fix_*_host*.py, recalc_standings_after_upload.py, export_regatta_385_data.py). There is no dedicated ingestion service or background worker in the repo; ingestion is script-driven and (where applicable) triggered by API routes that perform sailor-ID scraping only, not regatta creation.

---

### 5.1 Entry points

#### Manual upload routes

There are **no** API routes in api.py that accept a manual upload of regatta data (no file upload, no POST body that creates regattas, regatta_blocks, or results). The application does not expose an HTTP endpoint for “create regatta” or “import regatta results.”

#### Scrape routes

- **POST /api/run-daily-scrape** (run_daily_scrape in api.py) — This is the only scrape route. It performs **sailor-ID scraping** (member finder): it reads and inserts into **sailing_id** (or, on environments where that table does not exist, the code path may fail or use **sas_id_personal**). It does **not** create or update regattas, regatta_blocks, or results. It does update **scrape_log**.
- No other scrape route in api.py touches regatta data.

#### Background tasks

There are **no** background tasks in api.py (or in the scanned codebase) that create or update regattas, regatta_blocks, or results. The news cache refresh thread and similar only read from the database for pipeline inputs; they do not perform regatta ingestion.

#### Standalone scripts (regatta ingestion)

Regatta and result data are introduced into the database by **standalone Python scripts** run outside the API (e.g. from the project root with DB_URL/DATABASE_URL set):

- **add_regattas_377_384_no_results.py** — Inserts rows into **regattas** (and optionally updates result_status/as_at_time). Does not insert regatta_blocks or results.
- **add_regatta_375_entries.py** — Inserts one row into **regattas**. Does not set host_club_id.
- **add_regatta_385_420_fleet.py**, **add_regatta_385_420_results.py**, and other **add_regatta_*_results.py** / **add_regatta_*_*_fleet.py** scripts — Assume the regatta row already exists. They insert into **regatta_blocks** (and optionally **results**), and update **regattas** (result_status, as_at_time). They do not create the regatta row.
- **export_regatta_385_data.py** — Export/restore utility: deletes then re-inserts **regattas**, **regatta_blocks**, and **results** for a given regatta (SQL dump/restore style). Not a live ingestion pipeline.
- **fix_hyc_host_club_id.py**, **fix_all_clubs_host_regattas.py** — Post-hoc scripts that **UPDATE regattas SET host_club_id** where NULL or wrong (inferred from event_name or patterns).
- **recalc_standings_after_upload.py** — After new results are uploaded (via scripts), optionally calls **fix_all_clubs_host_regattas.run_fix_host_clubs()**, which can overwrite **regattas.host_club_id**. It then recalculates standings; it does not insert regattas or results.

**bulk_auto_match_regatta(regatta_id)** in api.py is a **helper function** that, given an existing regatta_id, updates **results** (club_id, helm_sa_sailing_id, crew_sa_sailing_id, helm_temp_id, crew_temp_id, match_status_*), **temp_people** (via _ensure_temp_person), and **sailing_id** (home_club_code). It does not create regattas or regatta_blocks and does not insert results. It is **not** exposed as an API route and is **not** invoked from any other file in the repo; it is available for one-off or future use (e.g. from a script or a route that is not yet present).

---

### 5.2 Ingestion: tables INSERTed into and UPDATEd, and order

Ingestion is split between (1) scripts that create/update regattas and blocks and insert results, and (2) api.py logic that only updates existing rows (no regatta/block/result creation in api.py).

#### Scripts (typical order for a new regatta with results)

1. **regattas** — **INSERT** (in add_regattas_377_384_no_results.py or add_regatta_375_entries.py). Optional **UPDATE** in the same or a later script: result_status, as_at_time (and in add_regattas_377_384, host_club_id is set at insert time from a club map).
2. **regatta_blocks** — **INSERT** (in add_regatta_385_420_fleet.py, add_regatta_385_420_results.py, etc.). Some scripts use ON CONFLICT (block_id) DO UPDATE.
3. **regattas** — **UPDATE** result_status, as_at_time (in the same script that inserts blocks/results, e.g. add_regatta_385_420_fleet.py).
4. **results** — **INSERT** (in add_regatta_385_420_fleet.py, add_regatta_385_420_results.py, etc.). One script (add_regatta_385_420_results.py) does **DELETE FROM results WHERE block_id = %s** for that block before re-inserting results.

No script in the scanned set INSERTs into **regattas** and **results** in a single atomic “import”; the regatta row is created first (or assumed to exist), then blocks, then results.

#### api.py (post-ingestion or inline edits only)

- **results** — **UPDATE** (club_id, helm_sa_sailing_id, crew_sa_sailing_id, helm_temp_id, crew_temp_id, match_status_helm, match_status_crew) in **bulk_auto_match_regatta**; (as_at_time) in **_ensure_snapshot_integrity**; (race_scores, total_points_raw, nett_points_raw, rank, etc.) in **patch_race_score**; (sail_number, club_raw, class_original, boat_name, helm/crew) in **patch_result** and **api_set_person**.
- **regatta_blocks** — **UPDATE** (races_sailed, discard_count) in **patch_race_score**.
- **temp_people** — **INSERT** (and ON CONFLICT DO UPDATE) in **_ensure_temp_person**, called from bulk_auto_match_regatta.
- **sailing_id** — **UPDATE** (home_club_code) in bulk_auto_match_regatta. **INSERT** in **run_daily_scrape** (sailor IDs only; not regatta ingestion).
- **scrape_log** — **INSERT** / **UPDATE** in **log_pre_scrape** and **run_daily_scrape** (sailor scrape only).

**regattas** is **never** INSERTed into or UPDATEd in api.py. The only reference to writing regattas in api.py is a comment: “Do NOT overwrite regattas.as_at_time with NOW()” inside _ensure_snapshot_integrity (which only updates results.as_at_time).

---

### 5.3 Where regattas table is created; where host_club_id and club_id are set; where regatta_blocks and results are created

#### Where the regattas table row is created

- **add_regattas_377_384_no_results.py** — `INSERT INTO regattas (regatta_id, regatta_number, event_name, year, start_date, end_date, result_status, host_club_id) VALUES (...)` with `ON CONFLICT (regatta_id) DO NOTHING`. One row per regatta in the script’s list.
- **add_regatta_375_entries.py** — `INSERT INTO regattas (regatta_id, event_name, start_date, end_date, result_status) VALUES (...)`. Single regatta; host_club_id is not set (remains NULL unless updated elsewhere).
- **export_regatta_385_data.py** — On restore: `INSERT INTO regattas (...columns...) VALUES (...)` after a prior `DELETE FROM regattas WHERE regatta_id = '%s'`. This is export/restore, not the primary ingestion path.

All other add_regatta_* scripts assume the regatta row already exists and only **UPDATE** regattas (result_status, as_at_time).

#### Where regattas.host_club_id is set

- **At creation:** In **add_regattas_377_384_no_results.py** only. For each regatta, a hardcoded **club_code** (e.g. 'sas', 'rcyc', 'hyc', 'powc', 'ec') is looked up in **clubs** (by club_abbrev or club_fullname); the resulting **club_id** is passed as **host_club_id** in the INSERT. So host is set from a **hardcoded mapping** (regatta → club_code → clubs.club_id).
- **add_regatta_375_entries.py** does not set host_club_id (column not in INSERT list).
- **Post-hoc:** **fix_hyc_host_club_id.py** — `UPDATE regattas SET host_club_id = %s WHERE host_club_id IS NULL AND (UPPER(COALESCE(event_name,'')) LIKE '%HYC%' OR ... LIKE '%HERMANUS%')`. **fix_all_clubs_host_regattas.py** — `UPDATE regattas SET host_club_id = %s` where event_name matches a club’s abbrev or full-name pattern (or a hardcoded EVENT_PATTERN_TO_CLUB list). **recalc_standings_after_upload.py** optionally calls **run_fix_host_clubs()**, which performs the same fix_all_clubs_host_regattas logic and can overwrite host_club_id.

The **regattas** table has **no** column named **club_id**. It has **host_club_id**, **host_club_code**, and **host_club_name**. So “regattas.club_id” does not exist; only **host_club_id** (and denormalised host_club_code/host_club_name) are relevant.

#### Where regatta_blocks are created

- **add_regatta_385_420_fleet.py** — `INSERT INTO regatta_blocks (block_id, regatta_id, class_original, class_canonical, fleet_label, races_sailed, discard_count, to_count, scoring_system, block_label_raw) VALUES (...)` with `ON CONFLICT (block_id) DO UPDATE SET races_sailed = ..., discard_count = ..., to_count = ..., scoring_system = ...`.
- **add_regatta_385_420_results.py** — `INSERT INTO regatta_blocks (block_id, regatta_id, class_original, class_canonical, fleet_label, races_sailed, discard_count, to_count, scoring_system) VALUES (...)` with `ON CONFLICT (block_id) DO UPDATE SET ...`.
- **export_regatta_385_data.py** — On restore: INSERT into regatta_blocks after DELETE for that regatta.

Other add_regatta_* scripts that add fleets follow the same pattern (INSERT regatta_blocks, often with ON CONFLICT DO UPDATE).

#### Where results are created

- **add_regatta_385_420_fleet.py** — `INSERT INTO results (regatta_id, block_id, rank, fleet_label, class_original, class_canonical, sail_number, club_raw, club_id, helm_name, helm_sa_sailing_id, crew_name, crew_sa_sailing_id, races_sailed, discard_count, race_scores, total_points_raw, nett_points_raw, raced, as_at_time) VALUES (...)` per row. No ON CONFLICT; plain INSERT.
- **add_regatta_385_420_results.py** — First `DELETE FROM results WHERE block_id = %s`, then `INSERT INTO results (...)` for each result row.
- **export_regatta_385_data.py** — On restore: INSERT into results after DELETE for that regatta.

api.py does not INSERT results; it only UPDATEs existing results (and, in patch_race_score, UPDATEs regatta_blocks).

---

### 5.4 Host inference (how host is determined)

- **Regatta name (event_name):** Used by **fix_hyc_host_club_id.py** (event_name LIKE '%HYC%' or '%HERMANUS%' → host_club_id = HYC’s club_id) and by **fix_all_clubs_host_regattas.py** (event_name matched against each club’s abbrev or first word of full name, or against EVENT_PATTERN_TO_CLUB patterns such as '%MPUMALANGA%' → WYAC, '%FREE STATE%' → DAC). So host is **inferred from regatta name** in post-hoc fix scripts.
- **Club code in source:** At **regatta creation** time only in **add_regattas_377_384_no_results.py**: each regatta is associated with a **hardcoded** club_code (e.g. 'hyc', 'rcyc'); that code is resolved to **club_id** via `SELECT club_id FROM clubs WHERE LOWER(club_abbrev) = %s OR LOWER(club_fullname) ILIKE %s`. So for that script, host is effectively a **hardcoded mapping** (regatta → club_code → clubs), not “club code in the uploaded file.” Result rows have **club_raw** (e.g. 'ZVYC', 'HYC'); that is used to set **results.club_id** (and, in bulk_auto_match, sailing_id.home_club_code), not **regattas.host_club_id**.
- **First result row:** Not used to set **regattas.host_club_id** in any scanned script or api.py. The first result row’s club_raw/club_id can influence **results.club_id** and sailor home_club_code, but not the regatta’s host.
- **Hardcoded mapping:** **add_regattas_377_384_no_results.py** uses a fixed list of (regatta_number, year, club_code, slug, event_name, end_date); **fix_all_clubs_host_regattas.py** uses a hardcoded **EVENT_PATTERN_TO_CLUB** list for phase 2 (e.g. '%MPUMALANGA%' → WYAC).

---

### 5.5 Logic that overwrites host_club_id on re-import

- **fix_hyc_host_club_id.py** — Updates regattas where host_club_id IS NULL and event_name contains HYC/Hermanus. It does not run as part of “re-import”; it is run as a standalone fix. So on a “re-import” (re-running add_regatta scripts), this script does not run unless invoked separately; when run, it **overwrites** host_club_id only for NULL hosts matching the pattern.
- **fix_all_clubs_host_regattas.run_fix_host_clubs()** — Updates regattas where `(host_club_id IS NULL OR host_club_id != %s)` and event_name matches a club pattern. So it **can overwrite** an existing host_club_id if the event_name matches a different club’s pattern (e.g. wrong host was set at creation). It is invoked optionally from **recalc_standings_after_upload.py** after new results are uploaded. So on “re-import” (running add_regatta scripts then recalc_standings_after_upload), host_club_id **can be overwritten** by run_fix_host_clubs.
- **add_regattas_377_384_no_results.py** uses `ON CONFLICT (regatta_id) DO NOTHING`; it does **not** overwrite host_club_id on re-run. **add_regatta_375_entries.py** does not use ON CONFLICT (single INSERT); re-running would typically fail on duplicate key or be run once. **add_regatta_385_*` scripts only UPDATE regattas (result_status, as_at_time); they do not set host_club_id.

---

### 5.6 ON CONFLICT logic in ingestion

- **regattas:** **add_regattas_377_384_no_results.py** — `ON CONFLICT (regatta_id) DO NOTHING`. So re-running does not change an existing regatta row. **add_regatta_375_entries.py** — No ON CONFLICT (plain INSERT). **export_regatta_385_data.py** — Restore path: DELETE then INSERT (no ON CONFLICT).
- **regatta_blocks:** **add_regatta_385_420_fleet.py** — `ON CONFLICT (block_id) DO UPDATE SET races_sailed = EXCLUDED.races_sailed, discard_count = EXCLUDED.discard_count, to_count = EXCLUDED.to_count, scoring_system = EXCLUDED.scoring_system`. **add_regatta_385_420_results.py** — `ON CONFLICT (block_id) DO UPDATE SET races_sailed=5, discard_count=1, to_count=4, scoring_system='Appendix A'`. So blocks are upserted by block_id.
- **results:** **add_regatta_385_420_fleet.py** — No ON CONFLICT; plain INSERT (re-running could duplicate rows unless guarded externally). **add_regatta_385_420_results.py** — No ON CONFLICT; it first runs `DELETE FROM results WHERE block_id = %s`, then INSERTs, so re-run replaces all results for that block. Other add_regatta_* scripts may follow either “DELETE block then INSERT” or plain INSERT; no ON CONFLICT on results was found in the scanned scripts.
- **temp_people (api.py):** **_ensure_temp_person** (used by bulk_auto_match_regatta) — `INSERT INTO temp_people (full_name, normalized_name, notes) VALUES (...) ON CONFLICT (normalized_name) DO UPDATE SET full_name = EXCLUDED.full_name RETURNING temp_id`. So temp person ingestion uses ON CONFLICT on normalized_name.

---

### 5.7 Data-cleaning logic that may alter club assignment

- **api.py, bulk_auto_match_regatta:** For each result row, **club_raw** is resolved via **_resolve_club(cur, club_raw)** (clubs and club_aliases lookup). If a club_id is found, it runs `UPDATE results SET club_id=%s WHERE result_id=%s AND (club_id IS NULL OR club_id<>%s)`. So **results.club_id** can be set or changed from club_raw during auto-match. **sailing_id.home_club_code** is also set from the same club_code when a helm/crew is matched to a SAS ID. This does not alter **regattas.host_club_id**.
- **api.py, run_daily_scrape:** After sailor-ID scrape and sailing_id updates, a block runs: `UPDATE results SET club_id = c.club_id FROM clubs c JOIN regatta_blocks rb ON rb.block_id = results.block_id WHERE rb.regatta_id = %s AND results.club_raw = c.club_abbrev AND results.club_id IS DISTINCT FROM c.club_id`. So **results.club_id** is updated from **club_raw** by matching **club_raw** to **clubs.club_abbrev** for all results of a given regatta. This is **result-level** club assignment only; it does not touch regattas.host_club_id.
- **add_regatta_385_420_fleet.py:** Uses a **CLUB_MAP** (e.g. 'ZVYC' → 3, 'HYC' → 10) to set **results.club_id** at insert time from the sheet’s club code. **add_regatta_385_420_results.py** uses **find_club_id(cur, club_raw)** (clubs lookup by club_abbrev or club_fullname) to set results.club_id at insert. So club assignment for **results** is either hardcoded (CLUB_MAP) or resolved from club_raw at insert time; no separate “cleaning” step in those scripts beyond the initial insert.

---

### 5.8 SQL statements touching regattas during ingestion

The following are all SQL statements that **write** to the **regattas** table (INSERT, UPDATE, DELETE) in the context of ingestion or post-import fixes. **api.py** contains **no** such statements (only a comment that regattas.as_at_time must not be overwritten by the snapshot-integrity logic).

#### In standalone scripts

1. **add_regattas_377_384_no_results.py**  
   - `INSERT INTO regattas (regatta_id, regatta_number, event_name, year, start_date, end_date, result_status, host_club_id) VALUES (%s, %s, %s, %s, %s, %s, 'Provisional', %s) ON CONFLICT (regatta_id) DO NOTHING`  
   - `UPDATE regattas SET result_status = %s, as_at_time = %s::timestamptz WHERE regatta_id = %s`

2. **add_regatta_375_entries.py**  
   - `INSERT INTO regattas (regatta_id, event_name, start_date, end_date, result_status) VALUES (%s, 'SA Youth Nationals 2025', '2025-12-15', '2025-12-20', 'Final')`

3. **add_regatta_385_420_fleet.py**  
   - `UPDATE regattas SET result_status = %s, as_at_time = %s::timestamptz WHERE regatta_id = %s`

4. **add_regatta_385_420_results.py**  
   - `UPDATE regattas SET result_status = %s, as_at_time = %s::timestamptz WHERE regatta_id = %s`

5. **fix_hyc_host_club_id.py**  
   - `UPDATE regattas SET host_club_id = %s WHERE host_club_id IS NULL AND (UPPER(COALESCE(event_name, '')) LIKE '%HYC%' OR UPPER(COALESCE(event_name, '')) LIKE '%HERMANUS%')`

6. **fix_all_clubs_host_regattas.py**  
   - `UPDATE regattas SET host_club_id = %s WHERE event_name IS NOT NULL AND (host_club_id IS NULL OR host_club_id != %s) AND (UPPER(COALESCE(event_name, '')) LIKE %s [or similar patterns])`  
   - `UPDATE regattas SET host_club_id = %s WHERE host_club_id IS NULL AND event_name IS NOT NULL AND UPPER(event_name) LIKE %s` (phase 2, EVENT_PATTERN_TO_CLUB)

7. **export_regatta_385_data.py**  
   - `DELETE FROM results WHERE regatta_id = '%s'; DELETE FROM regatta_blocks WHERE regatta_id = '%s'; DELETE FROM regattas WHERE regatta_id = '%s'`  
   - `INSERT INTO regattas (regatta_id, regatta_number, event_name, year, regatta_type, host_club_id, host_club_code, host_club_name, ...) VALUES (...)` (on restore)

#### In api.py

- **None.** No INSERT, UPDATE, or DELETE targets the **regattas** table. The only mention is the comment in _ensure_snapshot_integrity (Do NOT overwrite regattas.as_at_time with NOW(); set explicitly or leave NULL).

---

## 6. Host Assignment Logic (Consolidated)

Sources: all ingestion and fix scripts that touch **regattas.host_club_id** (and optionally **host_club_code**, **host_club_name**). Environment: LIVE (hostname vm103zuex.yourlocaldomain.com, database sailors_master). Dry-run SELECT for mismatch list was run on LIVE; no updates were performed.

---

### 6.1 Scripts that set host_club_id

| Script | Action | When |
|--------|--------|------|
| **add_regattas_377_384_no_results.py** | Sets **host_club_id** at INSERT time from a hardcoded **club_code** per regatta (see 6.3). | When inserting new regatta rows; ON CONFLICT (regatta_id) DO NOTHING so re-run does not overwrite. |
| **add_regatta_375_entries.py** | Does **not** set host_club_id (column not in INSERT list). | N/A. |
| **export_regatta_385_data.py** | On **restore**, INSERTs regattas including **host_club_id**, **host_club_code**, **host_club_name** from the exported row. | Restore path only; not used for normal ingestion. |

---

### 6.2 Scripts that update host_club_id

| Script | Exact SQL statement shape | WHERE clause (conditions) | Overwrite allowed? |
|--------|----------------------------|---------------------------|---------------------|
| **fix_hyc_host_club_id.py** | `UPDATE regattas SET host_club_id = %s WHERE host_club_id IS NULL AND (UPPER(COALESCE(event_name, '')) LIKE '%%HYC%%' OR UPPER(COALESCE(event_name, '')) LIKE '%%HERMANUS%%')` | host_club_id IS NULL; event_name contains HYC or HERMANUS. | No — only updates when host_club_id IS NULL. |
| **fix_all_clubs_host_regattas.py** (Phase 1) | `UPDATE regattas SET host_club_id = %s WHERE event_name IS NOT NULL AND (host_club_id IS NULL OR host_club_id != %s) AND (UPPER(COALESCE(event_name, '')) LIKE %s [repeated OR ... LIKE %s per pattern])` | event_name IS NOT NULL; (host_club_id IS NULL OR host_club_id != target cid); event_name matches any of the club's patterns (abbrev or first word of full name). | **Yes** — condition includes `host_club_id != %s`, so existing host can be overwritten if event_name matches a different club. |
| **fix_all_clubs_host_regattas.py** (Phase 2) | `UPDATE regattas SET host_club_id = %s WHERE host_club_id IS NULL AND event_name IS NOT NULL AND UPPER(event_name) LIKE %s` | host_club_id IS NULL; event_name IS NOT NULL; event_name matches EVENT_PATTERN_TO_CLUB pattern. | No — only NULL host. |
| **fix_hyc_wrong_host.py** | `UPDATE regattas SET host_club_id = %s WHERE regatta_id = ANY(%s) AND host_club_id != %s` | regatta_id in hardcoded list IDS; host_club_id != HYC's club_id. | **Yes** — explicitly overwrites wrong host (e.g. 110) to HYC (10) for listed regatta_ids. |

---

### 6.3 EVENT_PATTERN_TO_CLUB mapping

Defined in **fix_all_clubs_host_regattas.py** (Phase 2). Used only when **host_club_id IS NULL**. Pattern is UPPER(event_name) LIKE pattern; club_abbrev is resolved to club_id via clubs table.

| Pattern (UPPER(event_name) LIKE) | club_abbrev |
|----------------------------------|-------------|
| %MPUMALANGA% | WYAC |
| %WEST COAST% | TCC |
| %FS PROVINCIALS% | DAC |
| %FS CHAMPS% | DAC |
| %FREE STATE% | DAC |
| %NKS GRAND PRIX% | RCYC |
| %TRIPLE CROWN% | HMYC |
| %STADT 23 WC% | RCYC |
| %GP14 NATIONAL% | RCYC |
| %FLYING FIFTEEN NATIONAL% | RCYC |
| %SOLING NATIONAL% | RCYC |
| %J22 NATIONAL% | PYC |
| %OPTIMIST FS% | DAC |

---

### 6.4 Hardcoded club_code mapping (at regatta creation)

**add_regattas_377_384_no_results.py** builds **club_map** at runtime by querying **clubs** for each code in `('sas', 'rcyc', 'powc', 'ec', 'hyc')`:

- `SELECT club_id FROM clubs WHERE LOWER(club_abbrev) = %s OR LOWER(club_fullname) ILIKE %s LIMIT 1` with `(code, f'%{code}%')`.

The **regatta to club_code** mapping is hardcoded in **REGRATTAS**:

| regatta_number | year | club_code | slug (suffix) | event_name |
|----------------|------|-----------|---------------|------------|
| 377 | 2025 | sas | sa-sailing-youth-national-championship | SA Sailing Youth National Championship - Final Results 19 Dec 2025 |
| 378 | 2026 | rcyc | gimco-inter-academy | Gimco - Inter Academy |
| 379 | 2026 | rcyc | gimco-cape-31 | Gimco - Cape 31 |
| 380 | 2026 | rcyc | gimco-class-c | Gimco - Class C |
| 381 | 2026 | rcyc | gimco-class-b | Gimco - Class B |
| 382 | 2026 | rcyc | gimco-class-a | Gimco - Class A |
| 383 | 2026 | powc | port-owen-river-race | Port Owen River Race Results |
| 384 | 2026 | ec | ec-regional-champs | EC Regional Champs Results |
| 385 | 2026 | hyc | cape-classic | Cape Classic |

**fix_hyc_wrong_host.py** uses a hardcoded list **IDS** of regatta_ids forced to HYC: e.g. 311-2025-hyc-cape-classic-ilca-4-16-results, 308-2025-hyc-cape-classic-mirror-results, 312-2025-hyc-cape-classic-dabchick-results, 310-2025-hyc-cape-classic-ilca-6-results, 309-2025-hyc-cape-classic-ilca-7-results.

---

### 6.5 All places where host_club_id may be overwritten

1. **fix_all_clubs_host_regattas.py**, Phase 1 — Updates rows where `host_club_id IS NULL OR host_club_id != %s` and event_name matches a club's abbrev or first-word-of-fullname pattern. So an existing non-NULL host can be overwritten if the script decides event_name matches a different club.
2. **fix_all_clubs_host_regattas.py**, Phase 2 — Only updates when `host_club_id IS NULL`; no overwrite of existing host.
3. **fix_hyc_host_club_id.py** — Only updates when `host_club_id IS NULL`; no overwrite.
4. **fix_hyc_wrong_host.py** — Overwrites host_club_id for a fixed list of regatta_ids to HYC (e.g. corrects wrong club 110 to 10).
5. **recalc_standings_after_upload.py** — Calls **run_fix_host_clubs(conn=conn, verbose=False)**; when recalc runs after upload, Phase 1 (and Phase 2 for NULL hosts) can run and overwrite host_club_id as in (1) and (2).

---

### 6.6 Script callable from other scripts

- **fix_all_clubs_host_regattas.run_fix_host_clubs(conn=None, verbose=True)** — Can be called with an existing connection. **recalc_standings_after_upload.py** imports and calls it: `from fix_all_clubs_host_regattas import run_fix_host_clubs` then `run_fix_host_clubs(conn=conn, verbose=False)`. So host assignment fix is run automatically after standings recalc unless SKIP_HOST_CLUB_FIX=1 or the import/call fails.

No other host-assignment script is imported or called from another script in the scanned codebase.

---

### 6.7 Whether host_club_code and host_club_name are modified

- **fix_hyc_host_club_id.py**, **fix_all_clubs_host_regattas.py**, **fix_hyc_wrong_host.py**, **add_regattas_377_384_no_results.py** — Only set **host_club_id**. They do **not** UPDATE **host_club_code** or **host_club_name** on regattas.
- **export_regatta_385_data.py** — On **restore**, the INSERT into regattas includes **host_club_code** and **host_club_name** from the exported row (so they are modified only in the sense of being restored from dump).
- **api.py** — Does not write to regattas; it reads host_club_name from a JOIN with clubs. The denormalised columns host_club_code and host_club_name on regattas are not updated by the fix or ingestion scripts and may be stale if written elsewhere or left from a restore.

---

### 6.8 Regattas where host_club_id != derived club from regatta name (dry-run SELECT only; no updates)

Derivation rule used: "derived club" = the club whose **club_abbrev** appears in **event_name** (case-insensitive), with longest abbrev match chosen when multiple match (ORDER BY LENGTH(c.club_abbrev) DESC LIMIT 1). This approximates Phase 1 of fix_all_clubs_host_regattas (abbrev match only).

Query run on LIVE (sailors_master):

```sql
SELECT r.regatta_id, r.event_name, r.host_club_id AS current_host, c.club_id AS derived_id, c.club_abbrev AS derived_abbrev
FROM regattas r
CROSS JOIN LATERAL (
  SELECT c2.club_id, c2.club_abbrev
  FROM clubs c2
  WHERE c2.club_abbrev IS NOT NULL AND TRIM(c2.club_abbrev) != ''
    AND UPPER(TRIM(COALESCE(r.event_name,''))) LIKE '%' || UPPER(TRIM(c2.club_abbrev)) || '%'
  ORDER BY LENGTH(c2.club_abbrev) DESC
  LIMIT 1
) c
WHERE r.host_club_id IS DISTINCT FROM c.club_id
ORDER BY r.regatta_id;
```

Result (LIVE, no updates applied):

| regatta_id | event_name | current_host | derived_id | derived_abbrev |
|------------|------------|--------------|------------|----------------|
| 186-2024-hmyc-grand-slam | HMYC Grand Slam | 127 | 98 | HMYC |
| 188-2024-hmyc-6hr-race-results | HMYC 6hr Race Results | 127 | 98 | HMYC |
| 197-2024-hmyc-autumn-series | HMYC Autumn Series | 127 | 98 | HMYC |
| 208-2024-hmyc-memorial-series | HMYC Memorial Series | 127 | 98 | HMYC |
| 228-2024-azalea-at-hmyc | AZALEA at HMYC | 127 | 98 | HMYC |
| 229-2024-von-klemperer-at-hmyc | VON KLEMPERER at HMYC | 127 | 98 | HMYC |
| 234-2024-hmyc-club-class-championships | HMYC Club Class Championships | 127 | 98 | HMYC |
| 243-2024-hmyc-club-class-championships | HMYC Club Class Championships | 127 | 98 | HMYC |
| 266-2024-glyc-interclubregatta | GLYC_InterClubRegatta | 120 | 97 | GLYC |
| 303-2025-hmyc-grand-slam-multihull-overall-final | HMYC Grand Slam_Multihull Overall_Final | 127 | 98 | HMYC |
| 304-2025-hmyc-grand-slam-final | HMYC Grand Slam | 127 | 98 | HMYC |
| 312-2025-hyc-cape-classic-dabchick-results | HYC Cape Classic Dabchick 2025 | 10 | 115 | DABC |
| 317-2025-hmyc-9-hr-endurance | HMYC 9 hr Endurance | 127 | 98 | HMYC |

So on LIVE there are **13** regattas where the current **host_club_id** differs from the club derived from event_name by abbrev match. For example, HMYC events have current_host 127 but derived HMYC club_id 98; one HYC Cape Classic Dabchick regatta has current 10 (HYC) but derived 115 (DABC) because "Dabchick" matches DABC. No UPDATE was performed.
