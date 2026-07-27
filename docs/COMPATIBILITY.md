# Compatibility (Dev Only)

- Provides legacy views so existing tools keep working during migration.
- Drop this file and 090_compat_views_dev_only.sql before production.

Views:
- sas_id_personal → sa_ids projection (basic fields)
- results_legacy → results passthrough
- temp_people → id_aliases TEMP
- people_club_history → person_club_memberships
- member_roles → minimal stub
