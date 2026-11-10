# Ingestion Pipeline Update Plan

**Status:** PLAN ONLY — No code changes yet  
**Priority:** Before any historical backfill  
**Goal:** All future imports follow: Source → Provenance → Event → Class → Fleet → Sailor → Boat → Results

---

## Current Ingestion Paths (Audit)

| Path | Script | Current Flow | Provenance? |
|------|--------|--------------|-------------|
| Results (manual) | `results_ingestion_common.py` | PDF → Parse → Results | ❌ No artifact |
| Events CSV | `load_events_csv_to_db.py` | CSV → Events | ❌ No artifact |
| SAS Events Scrape | `scrape_sas_events_list.py` | Scrape → CSV → Events | ❌ No artifact |
| SAS Member Scrape | `sas_member_scrape.py` | Scrape → sas_id_personal | ❌ No artifact |
| SAS Qualifications | `scrape_accreditation_quals.py` | Scrape → member_roles | ❌ No artifact |
| SAS Classes | `scrape_sas_classes.py` | Scrape → SQL → classes | ❌ No artifact |

---

## Target Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│  1. SOURCE CAPTURE                                                  │
│     ├─ Download/scrape raw file (PDF, HTML, CSV)                   │
│     ├─ Store locally with deterministic path                        │
│     └─ Compute checksum (MD5)                                       │
│                                                                     │
│  2. PROVENANCE RECORD                                               │
│     ├─ Create source_artifact (source_url, type, checksum, path)   │
│     ├─ Set authority_level, import_method                          │
│     └─ artifact_status = 'pending_parse'                           │
│                                                                     │
│  3. EVENT RESOLUTION                                                │
│     ├─ Match to existing event (source + source_event_id)          │
│     ├─ Or create new event with artifact_id                        │
│     └─ Link event → artifact                                        │
│                                                                     │
│  4. CLASS RESOLUTION                                                │
│     ├─ Exact match classes.class_name (normalized)                 │
│     ├─ Or match via class_aliases                                  │
│     ├─ Unknown class → ingestion_issues (BLOCK)                    │
│     └─ Never auto-create classes                                   │
│                                                                     │
│  5. FLEET/BLOCK RESOLUTION                                          │
│     ├─ Match existing regatta_blocks (regatta + class)             │
│     ├─ Or create new block with artifact reference                 │
│     └─ Respect fleet_label from source                             │
│                                                                     │
│  6. SAILOR RESOLUTION                                               │
│     ├─ Match via resolve_helm_to_sa_id()                           │
│     ├─ Exact name + sail_number match                              │
│     ├─ Or SAS ID lookup                                            │
│     ├─ Unknown → NULL helm_sa_sailing_id (review queue)            │
│     └─ Never auto-create fake SAS IDs                              │
│                                                                     │
│  7. BOAT RESOLUTION (NEW)                                           │
│     ├─ Match via boat_identifiers (sail_number + class_family)     │
│     ├─ Exact match only (no fuzzy)                                 │
│     ├─ Unknown → NULL boat_id (boat review queue)                  │
│     └─ Never auto-create boats without evidence                    │
│                                                                     │
│  8. RESULTS INSERT                                                  │
│     ├─ Insert result row with all resolved FKs                     │
│     ├─ Set original_artifact_id, current_artifact_id               │
│     ├─ Set row_validation_status = 'draft'                         │
│     └─ Create result_sources link                                  │
│                                                                     │
│  9. REGATTA SOURCE LINK                                             │
│     ├─ Create regatta_sources entry                                │
│     ├─ Set source_scope (regatta/class/fleet/race)                 │
│     ├─ Set is_original=TRUE for first source                       │
│     └─ validation_status = 'pending_review'                        │
│                                                                     │
│ 10. POST-INSERT VALIDATION                                          │
│     ├─ Run checksum queries (entry counts, points, discards)       │
│     ├─ Flag discrepancies in ingestion_issues                      │
│     └─ Update artifact_status = 'validated' or 'issues_found'      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Scripts Requiring Update

### 1. `results_ingestion_common.py` (HIGH PRIORITY)

**Current:** Inserts results directly without provenance tracking.

**Required Changes:**
```
□ Add create_or_get_source_artifact(source_url, source_type, import_method)
□ Add resolve_boat_id(sail_number, class_id, class_family_id)
□ Update insert logic to set original_artifact_id, current_artifact_id
□ Create regatta_sources link after regatta creation
□ Create result_sources link after result insert
□ Set row_validation_status = 'draft' on insert
□ Add artifact_status update after parse complete
```

**New Functions Needed:**
- `create_source_artifact()` → Returns artifact_id
- `link_regatta_to_artifact()` → Creates regatta_sources row
- `link_result_to_artifact()` → Creates result_sources row
- `resolve_boat_id()` → Matches or returns NULL
- `update_artifact_status()` → Sets validated/issues_found

---

### 2. `load_events_csv_to_db.py` (MEDIUM PRIORITY)

**Current:** Upserts events without provenance.

**Required Changes:**
```
□ Create source_artifact for the CSV file itself
□ Set events.artifact_id on insert/update
□ Track source_url from CSV rows → individual artifacts if external
□ Set provenance_status on insert
```

---

### 3. `scrape_sas_events_list.py` (MEDIUM PRIORITY)

**Current:** Scrapes to CSV without provenance.

**Required Changes:**
```
□ Create source_artifact for each scrape run (scrape_auto method)
□ Store raw HTML/response as artifact
□ Pass artifact_id to CSV for loader to reference
□ Record scrape timestamp in artifact
```

---

### 4. `sas_member_scrape.py` (LOW PRIORITY - not results)

**Current:** Scrapes SAS member data.

**Required Changes:**
```
□ Create source_artifact for each scrape batch
□ Link sas_id_personal records to artifact (optional)
□ Track source reliability for sailor matching
```

---

### 5. Future: `SailingSA Live` Ingestion Path

**New Path:** Phone → Live Server → Database

**Required Components:**
```
□ Live session tracking (session_id, device, GPS)
□ Source_type = 'sailingsa_live'
□ Import_method = 'live_entry'
□ Real-time artifact creation
□ Immediate regatta_sources/result_sources linking
□ Conflict detection if race already has results
```

---

## New Shared Functions (to add to `results_ingestion_common.py`)

```python
def create_source_artifact(conn, source_url, source_type, import_method, 
                           authority_level, raw_file_path=None, checksum=None):
    """Create or get existing source_artifact, return artifact_id."""
    
def link_regatta_to_artifact(conn, regatta_id, artifact_id, source_scope='regatta',
                             is_original=True, is_primary=True):
    """Create regatta_sources entry with proper scope."""
    
def link_result_to_artifact(conn, result_id, artifact_id, is_original=True):
    """Create result_sources entry."""
    
def resolve_boat_id(cur, sail_number, class_id, class_family_id=None):
    """
    Resolve sail_number + class to boat_id via boat_identifiers.
    - Exact normalized match only
    - Class-family aware (ILCA rigs share hull)
    - Returns boat_id or None (review queue)
    """
    
def update_artifact_status(conn, artifact_id, status, notes=None):
    """Update artifact_status after parse/validation."""
```

---

## Boat Resolution Logic

```python
def resolve_boat_id(cur, sail_number, class_id, class_family_id=None):
    """
    1. Normalize sail_number (uppercase, strip whitespace)
    2. Get class_family_id if not provided
    3. Search boat_identifiers:
       - sail_number_normalized = normalized
       - class_id matches OR shares class_family
       - identifier_status = 'active'
    4. If exactly one match → return boat_id
    5. If multiple matches → return None (conflict, needs review)
    6. If no match → return None (new boat candidate)
    """
```

---

## Migration Sequence

| Step | Action | Blocks |
|------|--------|--------|
| 1 | Add shared provenance functions to `results_ingestion_common.py` | — |
| 2 | Update `results_ingestion_common.py` insert flow | Step 1 |
| 3 | Add boat resolution to `results_ingestion_common.py` | Step 1 |
| 4 | Update `load_events_csv_to_db.py` | Step 1 |
| 5 | Update `scrape_sas_events_list.py` | Step 4 |
| 6 | Test full pipeline with new regatta | Steps 1-5 |
| 7 | Design SailingSA Live ingestion path | Steps 1-3 |
| 8 | Begin historical backfill | Steps 1-6 complete |

---

## Validation Checklist (per import)

```
□ source_artifact created with checksum
□ artifact.raw_file_path points to stored file
□ regatta.original_artifact_id set
□ regatta_sources entry created (is_original=TRUE)
□ All results have original_artifact_id
□ result_sources entries created
□ Unknown classes → ingestion_issues (not inserted)
□ Unknown sailors → helm_sa_sailing_id = NULL
□ Unknown boats → boat_id = NULL
□ Entry counts match source document
□ Points/discards validated
```

---

## Benefits

1. **No duplicate boats** — Exact match only, unknown goes to review
2. **No duplicate sailors** — Existing logic preserved, NULL for unknown
3. **No duplicate classes** — Strict matching, block unknown
4. **Full provenance** — Every result traces to exact source document
5. **Audit trail** — artifact_status, validation_status, timestamps
6. **Conflict detection** — Multiple sources flagged, not silently merged

---

*Created: 2026-07-27*  
*Status: Awaiting approval before implementation*
