# Events/Results Source & Provenance Model — PLAN ONLY

**Date:** 2026-07-27  
**Status:** PLAN ONLY — No code or backfill yet  
**Purpose:** Define canonical source/provenance model for all events and results before boat backfill

---

## 1. Executive Summary

Before backfilling the boat register, we must establish a single, canonical model for tracking:
- **Original source** of every event and result
- **Import method** (how data entered the system)
- **Source URL/file** (artifact locator)
- **Authority level** (trust hierarchy for conflict resolution)
- **Validation status** (data lifecycle)
- **Manual parsing flag** (whether human interpretation was required)

This ensures the boat register inherits correct provenance and enables future auditing.

---

## 2. Current State Audit

### 2.1 Existing Source Fields

#### `regattas` table (regatta-level provenance)
| Column | Type | Current Usage |
|--------|------|---------------|
| `source_url` | text | URL of PDF/results artifact (e.g., `https://www.sailing.org.za/file/{hash}`) |
| `local_file_path` | text | Local PDF copy (rarely populated) |
| `file_type` | text | `'PDF'`, `'pdf'`, `'html'`, `'screenshot'` (inconsistent casing) |
| `doc_hash` | text | MD5 checksum; unique index (rarely populated) |
| `import_status` | text | `'pending'`, `'imported'`, `'manual'` (inconsistent defaults) |
| `source_platform` | text | **UNUSED** — column exists, no values set |

#### `results` table (row-level provenance)
| Column | Type | Current Usage |
|--------|------|---------------|
| `class_original` | text | Exact text from PDF/sheet (soft provenance) |
| `club_raw` | text | Club as printed on sheet |
| `validation_flag` | text | **DEAD COLUMN** — never written |
| `source_row_text` | text | **DEAD COLUMN** — never written |
| `match_status_helm` | text | How helm SAS ID was resolved (`auto_sas`, `chosen`, etc.) |
| `match_status_crew` | text | How crew SAS ID was resolved |

#### `results_staging` table (staging provenance)
| Column | Type | Current Usage |
|--------|------|---------------|
| `source_url` | text | Dedupe key for SAS PDFs (runtime-added column) |
| `source_title_raw` | text | Raw SAS listing title |
| `source_site` | text | Hardcoded `'SAS'` |
| `pdf_local_path` | text | Local PDF storage path |
| `validation_status` | text | `'PENDING'` only (no transitions implemented) |

#### `events` table (calendar provenance)
| Column | Type | Current Usage |
|--------|------|---------------|
| `source` | text | `'sas'`, `'external'` |
| `source_event_id` | text | SAS or external event ID |
| `source_url` | text | Details page URL |
| `scrape_run_id` | text | `YYYYMMDDHHMM` timestamp of scrape |
| `last_seen_at` | timestamptz | Last scrape detection |

### 2.2 Current Source Types (Implicit)

From code analysis:

| Context | Values Used |
|---------|-------------|
| `results_staging.source_site` | `'SAS'` (hardcoded) |
| `events.source` | `'sas'`, `'external'` |
| `regattas.import_status` | `'pending'`, `'imported'`, `'manual'` |
| Manual scripts | Implicit source tracking via script filename |

### 2.3 Identified Gaps

1. **No cell-level provenance** — cannot trace individual values to source sheet locations
2. **Dead columns** — `validation_flag`, `source_row_text` on `results` never populated
3. **No FK to source artifact** — cannot link results to their PDF/file
4. **Staging→production path missing** — no provenance carry-forward when promoting
5. **Inconsistent naming** — `source_platform` vs `source_site` vs `source`
6. **No authority hierarchy** — no way to resolve conflicts between sources
7. **No manual-parsing flag** — cannot distinguish OCR/AI-parsed from human-transcribed

---

## 3. Proposed Source Types (Authority Hierarchy)

### 3.1 Canonical Source Types

Listed in **authority order** (highest first):

| Code | Name | Description | Authority Level |
|------|------|-------------|-----------------|
| `sas_official` | SA Sailing Official | Official results from sailing.org.za with SAS verification | 100 (highest) |
| `sas_pdf` | SA Sailing PDF | SAS-published PDF without explicit verification | 90 |
| `sailwave` | Sailwave Export | Direct export from Sailwave race management software | 80 |
| `windsail` | Windsail Export | Direct export from Windsail system | 80 |
| `sailingsa_live` | SailingSA Live | Future: our own live scoring (when implemented) | 85 |
| `club_official` | Club Official | Direct from club with authorized representative confirmation | 75 |
| `club_upload` | Club Upload | Club-uploaded without explicit authorization | 60 |
| `external_scrape` | External Scrape | Scraped from external sites (laser.org.za, revolutionise, etc.) | 50 |
| `external_manual` | External Manual | Manually transcribed from external source | 40 |
| `manual_admin` | Manual Admin | Admin-entered data with no external source | 30 |
| `unknown` | Unknown | Legacy data with no source tracking | 0 (lowest) |

### 3.2 Authority Level Usage

- **Conflict resolution**: Higher authority wins when merging/deduplicating
- **Display**: Show source badge on results pages
- **Audit**: Filter by authority for data quality reports
- **Boat matching**: Higher-authority results create more confident boat records

---

## 4. Proposed Import Methods

### 4.1 Import Method Types

| Code | Name | Description | Manual Parsing? |
|------|------|-------------|-----------------|
| `scrape_auto` | Automated Scrape | Fully automated web scraping | No |
| `scrape_manual` | Manual Scrape | Human-assisted web scraping | Yes |
| `pdf_ocr` | PDF OCR | Optical character recognition from PDF | Yes (AI-assisted) |
| `pdf_table_extract` | PDF Table Extract | Structured table extraction from PDF | Partial |
| `csv_import` | CSV Import | Direct CSV/Excel file import | No |
| `sailwave_xml` | Sailwave XML | Native Sailwave .blw/.xml format | No |
| `api_sync` | API Sync | Real-time or batch API integration | No |
| `manual_entry` | Manual Entry | Human keyboard entry into admin UI | Yes |
| `migration` | Migration | Data migrated from legacy system | N/A |

### 4.2 Import Method + Source Combinations

Common valid combinations:

| Source Type | Valid Import Methods |
|-------------|---------------------|
| `sas_official` | `scrape_auto`, `pdf_table_extract` |
| `sas_pdf` | `pdf_ocr`, `pdf_table_extract`, `scrape_manual` |
| `sailwave` | `sailwave_xml`, `csv_import` |
| `windsail` | `csv_import`, `api_sync` |
| `club_official` | `csv_import`, `manual_entry` |
| `club_upload` | `csv_import`, `pdf_ocr` |
| `external_scrape` | `scrape_auto`, `scrape_manual` |
| `manual_admin` | `manual_entry` |

---

## 5. Proposed Validation Status Lifecycle

### 5.1 Status Values

| Status | Description | Transitions To |
|--------|-------------|----------------|
| `draft` | Initial state, not reviewed | `pending_review`, `rejected` |
| `pending_review` | Awaiting human verification | `validated`, `rejected`, `conflict` |
| `validated` | Human-verified correct | `conflict`, `superseded` |
| `rejected` | Rejected as incorrect/duplicate | (terminal) |
| `conflict` | Conflicting with other source | `resolved`, `rejected` |
| `resolved` | Conflict resolved | `validated` |
| `superseded` | Replaced by newer data | (terminal) |

### 5.2 Status Transition Rules

```
draft → pending_review  (auto, when import completes)
draft → rejected        (auto, when validation fails)

pending_review → validated  (manual, admin approval)
pending_review → rejected   (manual, admin rejection)
pending_review → conflict   (auto, when duplicate detected)

validated → conflict    (auto, when conflicting source arrives)
validated → superseded  (auto, when newer authoritative source arrives)

conflict → resolved     (manual, admin resolution)
conflict → rejected     (manual, discard this version)

resolved → validated    (auto, after conflict resolution)
```

---

## 6. Proposed Schema Changes

### 6.1 New Lookup Tables

```sql
-- Source type enumeration
CREATE TABLE source_types (
    source_type_code    TEXT PRIMARY KEY,
    source_type_name    TEXT NOT NULL,
    description         TEXT,
    authority_level     SMALLINT NOT NULL CHECK (authority_level BETWEEN 0 AND 100),
    is_external         BOOLEAN NOT NULL DEFAULT FALSE,
    requires_evidence   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Import method enumeration
CREATE TABLE import_methods (
    import_method_code  TEXT PRIMARY KEY,
    import_method_name  TEXT NOT NULL,
    description         TEXT,
    requires_manual_parsing BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Validation status enumeration
CREATE TABLE validation_statuses (
    status_code         TEXT PRIMARY KEY,
    status_name         TEXT NOT NULL,
    description         TEXT,
    is_terminal         BOOLEAN NOT NULL DEFAULT FALSE,
    display_order       SMALLINT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6.2 Source Artifacts Table (from goals.md)

```sql
CREATE TABLE source_artifacts (
    artifact_id         BIGSERIAL PRIMARY KEY,
    -- Source identification
    source_type         TEXT NOT NULL REFERENCES source_types(source_type_code),
    import_method       TEXT NOT NULL REFERENCES import_methods(import_method_code),
    -- Source locators
    source_url          TEXT,                   -- Original URL (SAS PDF, external page)
    source_file_path    TEXT,                   -- Local storage path
    source_filename     TEXT,                   -- Original filename
    -- Metadata
    mime_type           TEXT,                   -- 'application/pdf', 'text/csv', etc.
    byte_size           BIGINT,
    checksum_md5        TEXT,                   -- MD5 hash for deduplication
    checksum_sha256     TEXT,                   -- SHA256 for integrity
    -- Parser info
    parser_name         TEXT,                   -- 'sas_pdf_extractor_v2', 'sailwave_importer'
    parser_version      TEXT,                   -- '1.2.3'
    parse_timestamp     TIMESTAMPTZ,
    -- Manual parsing
    manually_parsed     BOOLEAN NOT NULL DEFAULT FALSE,
    parsed_by           TEXT,                   -- User who did manual parsing
    parse_notes         TEXT,                   -- Notes about parsing difficulties
    -- Audit
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    captured_by         TEXT NOT NULL DEFAULT 'system',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_source_artifacts_source_type ON source_artifacts(source_type);
CREATE INDEX idx_source_artifacts_checksum ON source_artifacts(checksum_md5) WHERE checksum_md5 IS NOT NULL;
CREATE INDEX idx_source_artifacts_url ON source_artifacts(source_url) WHERE source_url IS NOT NULL;
```

### 6.3 Regatta Source Link Table

```sql
-- Link regattas to their source artifacts (many-to-many for multiple sources)
CREATE TABLE regatta_sources (
    regatta_source_id   BIGSERIAL PRIMARY KEY,
    regatta_id          TEXT NOT NULL REFERENCES regattas(regatta_id) ON DELETE CASCADE,
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE CASCADE,
    -- Authority
    is_primary          BOOLEAN NOT NULL DEFAULT FALSE, -- Primary authoritative source
    authority_override  SMALLINT,                       -- Override source_type authority if needed
    -- Validation
    validation_status   TEXT NOT NULL DEFAULT 'draft' REFERENCES validation_statuses(status_code),
    validated_by        TEXT,
    validated_at        TIMESTAMPTZ,
    validation_notes    TEXT,
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    UNIQUE (regatta_id, artifact_id)
);

-- Only one primary source per regatta
CREATE UNIQUE INDEX uq_regatta_primary_source ON regatta_sources(regatta_id) WHERE is_primary = TRUE;
```

### 6.4 Result Source Mapping Table (Cell-Level Provenance)

```sql
-- Optional: cell-level provenance for results (M2 from goals.md)
CREATE TABLE result_source_mappings (
    mapping_id          BIGSERIAL PRIMARY KEY,
    -- Target
    result_id           BIGINT NOT NULL REFERENCES results(result_id) ON DELETE CASCADE,
    field_name          TEXT NOT NULL,          -- 'sail_number', 'helm_name', 'R1', 'total_points', etc.
    -- Source
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE CASCADE,
    source_locator      TEXT,                   -- 'pdf:p3:r12:c8', 'csv:row45:col_D', 'sailwave:competitor:123:race5'
    -- Values
    raw_value           TEXT,                   -- Exact value from source
    normalized_value    TEXT,                   -- Value after normalization
    -- Confidence
    extraction_confidence SMALLINT CHECK (extraction_confidence BETWEEN 0 AND 100),
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_result_source_mappings_result ON result_source_mappings(result_id);
CREATE INDEX idx_result_source_mappings_artifact ON result_source_mappings(artifact_id);
```

### 6.5 Modify Existing Tables

```sql
-- Add to regattas (augment existing columns)
ALTER TABLE regattas
    ADD COLUMN IF NOT EXISTS primary_source_type TEXT REFERENCES source_types(source_type_code),
    ADD COLUMN IF NOT EXISTS primary_import_method TEXT REFERENCES import_methods(import_method_code),
    ADD COLUMN IF NOT EXISTS primary_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'draft' REFERENCES validation_statuses(status_code),
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;

-- Add to results (revive dead columns with proper semantics)
ALTER TABLE results
    ADD COLUMN IF NOT EXISTS source_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS row_validation_status TEXT DEFAULT 'validated' REFERENCES validation_statuses(status_code),
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;

-- Existing validation_flag will be deprecated in favor of row_validation_status
-- Existing source_row_text remains for raw row capture (activate in ingestion)

-- Add to results_staging
ALTER TABLE results_staging
    ADD COLUMN IF NOT EXISTS source_type TEXT REFERENCES source_types(source_type_code),
    ADD COLUMN IF NOT EXISTS import_method TEXT REFERENCES import_methods(import_method_code),
    ADD COLUMN IF NOT EXISTS artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;
```

---

## 7. Ingestion Path Updates

### 7.1 SAS PDF Pipeline (Primary)

```
1. Scrape sailing.org.za/events → detect new result PDFs
2. Download PDF → compute checksum → create source_artifact record
3. Parse PDF (OCR/table extract) → set manually_parsed=TRUE if human intervention
4. Stage to results_staging with artifact_id reference
5. Promote to regattas/results with provenance carry-forward
```

**Source Type**: `sas_pdf` (authority 90)  
**Import Method**: `pdf_table_extract` or `pdf_ocr`

### 7.2 Sailwave Import Pipeline

```
1. Admin uploads .blw or exported CSV
2. Create source_artifact (file stored locally, checksum computed)
3. Parse native format → create regatta/results
4. Link via regatta_sources
```

**Source Type**: `sailwave` (authority 80)  
**Import Method**: `sailwave_xml` or `csv_import`

### 7.3 Club Upload Pipeline

```
1. Club representative uploads CSV/Excel/PDF
2. Create source_artifact
3. Verify club authorization level
4. If authorized: source_type='club_official', else 'club_upload'
5. Parse and ingest with appropriate authority
```

**Source Type**: `club_official` (75) or `club_upload` (60)  
**Import Method**: varies by file type

### 7.4 Manual Admin Entry Pipeline

```
1. Admin enters data via UI
2. Create source_artifact with source_type='manual_admin'
3. Capture admin user as captured_by
4. Set manually_parsed=TRUE
5. Lower authority (30) unless evidence provided
```

### 7.5 Future: SailingSA Live Pipeline

```
1. Real-time scoring via our app
2. Each race creates source_artifact
3. source_type='sailingsa_live', authority=85
4. No manual parsing (direct entry)
```

---

## 8. Migration Strategy

### 8.1 Phase 1: Schema Only (No Data Changes)

1. Create lookup tables (`source_types`, `import_methods`, `validation_statuses`)
2. Seed lookup tables with defined values
3. Create `source_artifacts`, `regatta_sources`, `result_source_mappings` tables
4. Add new columns to `regattas`, `results`, `results_staging`
5. **Do not populate provenance on existing data yet**

### 8.2 Phase 2: Backfill Existing Data

1. Create source_artifact records for all known `source_url` values on regattas
2. Link regattas to artifacts via `regatta_sources`
3. Set `primary_source_type` based on heuristics:
   - If `source_url` contains `sailing.org.za` → `sas_pdf`
   - If `import_status = 'manual'` → `manual_admin`
   - Else → `unknown`
4. Set `validation_status = 'validated'` for all existing data (trusted baseline)

### 8.3 Phase 3: Activate New Pipelines

1. Update `results_ingestion_common.py` to create source_artifacts
2. Update staging→production promotion to carry forward provenance
3. Update admin UI to capture source info on manual entry
4. Deploy and monitor

---

## 9. Seed Data

### 9.1 Source Types Seed

```sql
INSERT INTO source_types (source_type_code, source_type_name, description, authority_level, is_external, requires_evidence) VALUES
('sas_official', 'SA Sailing Official', 'Official results from sailing.org.za with SAS verification', 100, FALSE, TRUE),
('sas_pdf', 'SA Sailing PDF', 'SAS-published PDF without explicit verification', 90, FALSE, TRUE),
('sailwave', 'Sailwave Export', 'Direct export from Sailwave race management software', 80, FALSE, TRUE),
('windsail', 'Windsail Export', 'Direct export from Windsail system', 80, FALSE, TRUE),
('sailingsa_live', 'SailingSA Live', 'Our own live scoring system', 85, FALSE, FALSE),
('club_official', 'Club Official', 'Direct from club with authorized representative', 75, FALSE, TRUE),
('club_upload', 'Club Upload', 'Club-uploaded without explicit authorization', 60, FALSE, TRUE),
('external_scrape', 'External Scrape', 'Scraped from external sites', 50, TRUE, TRUE),
('external_manual', 'External Manual', 'Manually transcribed from external source', 40, TRUE, TRUE),
('manual_admin', 'Manual Admin', 'Admin-entered data with no external source', 30, FALSE, FALSE),
('unknown', 'Unknown', 'Legacy data with no source tracking', 0, FALSE, FALSE);
```

### 9.2 Import Methods Seed

```sql
INSERT INTO import_methods (import_method_code, import_method_name, description, requires_manual_parsing) VALUES
('scrape_auto', 'Automated Scrape', 'Fully automated web scraping', FALSE),
('scrape_manual', 'Manual Scrape', 'Human-assisted web scraping', TRUE),
('pdf_ocr', 'PDF OCR', 'Optical character recognition from PDF', TRUE),
('pdf_table_extract', 'PDF Table Extract', 'Structured table extraction from PDF', FALSE),
('csv_import', 'CSV Import', 'Direct CSV/Excel file import', FALSE),
('sailwave_xml', 'Sailwave XML', 'Native Sailwave .blw/.xml format', FALSE),
('api_sync', 'API Sync', 'Real-time or batch API integration', FALSE),
('manual_entry', 'Manual Entry', 'Human keyboard entry into admin UI', TRUE),
('migration', 'Migration', 'Data migrated from legacy system', FALSE);
```

### 9.3 Validation Statuses Seed

```sql
INSERT INTO validation_statuses (status_code, status_name, description, is_terminal, display_order) VALUES
('draft', 'Draft', 'Initial state, not reviewed', FALSE, 10),
('pending_review', 'Pending Review', 'Awaiting human verification', FALSE, 20),
('validated', 'Validated', 'Human-verified correct', FALSE, 30),
('rejected', 'Rejected', 'Rejected as incorrect/duplicate', TRUE, 90),
('conflict', 'Conflict', 'Conflicting with other source', FALSE, 40),
('resolved', 'Resolved', 'Conflict resolved', FALSE, 50),
('superseded', 'Superseded', 'Replaced by newer data', TRUE, 80);
```

---

## 10. Integration with Boat Register

### 10.1 Boat Matching Provenance

When boat matching runs:

1. **Source tracking**: `boat_identifiers.source_type` uses same enum as `source_types`
2. **Evidence**: `boat_identifiers.evidence` JSONB includes `artifact_id` reference
3. **Confidence inheritance**: Boat confidence inherits from result source authority
4. **Conflict resolution**: Higher-authority sources win in boat matching conflicts

### 10.2 Backfill Order

1. **Phase 1**: Create source/provenance schema (this plan)
2. **Phase 2**: Backfill regatta source artifacts
3. **Phase 3**: Run boat matching with provenance awareness
4. **Phase 4**: Audit boat matches by source authority

---

## 11. Open Questions for Review

1. **Cell-level provenance**: Implement full `result_source_mappings` now, or defer to M2?
2. **Authority overrides**: Allow per-regatta authority overrides, or strict hierarchy?
3. **Sailwave native format**: Parse .blw files directly, or require CSV export?
4. **Club authorization**: How to verify "club_official" vs "club_upload"?
5. **Conflict UI**: What admin interface for resolving source conflicts?

---

## 12. Files to Modify (When Approved)

| File | Changes |
|------|---------|
| `database/migrations/210_source_provenance_schema.sql` | New tables, seed data |
| `results_ingestion_common.py` | Create source_artifacts, link to staging |
| `api.py` | Admin endpoints for source management |
| `load_events_csv_to_db.py` | Create artifacts for event imports |
| `docs/README_RESULTS_INGESTION.md` | Document provenance requirements |
| `admin_dashboard_v10_main.html` | Source/provenance display in admin |

---

## 13. Summary

This plan establishes:

- **Canonical source types** with authority hierarchy (SAS highest, unknown lowest)
- **Import method tracking** with manual-parsing flag
- **Validation lifecycle** for data quality management
- **Source artifact storage** for audit trail
- **Cell-level provenance** (optional) for full traceability
- **Integration path** with boat register provenance fields

**Next step**: Review and approve, then create migration 210.
