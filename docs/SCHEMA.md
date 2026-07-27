# Schema (Core 4 + Support)

- **sa_ids**: person_id (PK identity), sa_registry_no (INT UNIQUE), id_status ('temp','valid','inactive','merged'), names, dob, club_id, class_id, created_at, updated_at.
- **results**: regatta results header per boat/entry.
- **result_participants**: per-person roles on a result.
- **race_results**: per-race scores linked to a result.
- **sa_registry_counter/ledger**: allocator + audit for SAS numbers.
- **id_aliases / id_merge_log**: support TEMP codes, merges.
- **clubs / classes / regattas / regatta_blocks**: references.
