# Events/Results Source & Provenance Model — PLAN ONLY

**Date:** 2026-07-27  
**Status:** PLAN ONLY — No code or backfill yet  
**Purpose:** Define canonical source/provenance model for all events and results before boat backfill

---

## 1. Executive Summary

Before backfilling the boat register, we must establish a single, canonical model for tracking:
- **Original source** of every event and result (preserved forever, never overwritten)
- **Import method** (how data entered the system)
- **Source URL/file** (artifact locator)
- **Authority level** (trust hierarchy for conflict resolution)
- **Validation status** (data lifecycle)
- **Manual parsing flag** (whether human interpretation was required)
- **Secondary sources** (can be added without replacing original)

**Key Design Principle**: The original source is IMMUTABLE. Secondary sources are ADDITIVE.

---

## 2. Current State Audit — Source URL Linking

### 2.1 Entity Relationship: Current Source Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CURRENT SOURCE URL LINKING                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     regatta_id      ┌──────────────┐     regatta_id     ┌──────────────┐
│    events    │ ──────────────────► │   regattas   │ ◄───────────────── │   results    │
│              │     (nullable FK)   │              │     (required FK)  │              │
│ source='sas' │                     │ source_url   │                    │ class_original│
│ source_event_│                     │ local_file_  │                    │ club_raw     │
│   id         │                     │   path       │                    │ (no source   │
│ source_url   │                     │ file_type    │                    │    columns)  │
└──────────────┘                     │ doc_hash     │                    └──────────────┘
       │                             │ import_status│                           │
       │                             └──────────────┘                           │
       │                                    │                                   │
       │                                    │ block_id                          │ entry_id
       │                                    ▼                                   │ (nullable)
       │                             ┌──────────────┐                           │
       │                             │regatta_blocks│                           │
       │                             │              │                           │
       │                             │ (no source   │                           │
       │                             │   columns)   │                           │
       │                             └──────────────┘                           │
       │                                                                        │
       │                                                                        ▼
       │                                                                 ┌──────────────┐
       │                                                                 │   entries    │
       │                                                                 │              │
       │                                                                 │ regatta_id   │
       │                                                                 │ (text, no FK)│
       │                                                                 │ (no source   │
       │                                                                 │   columns)   │
       │                                                                 └──────────────┘
       │
       │     SEPARATE STAGING PATH (not linked to above)
       │
       │     ┌──────────────────┐
       └───► │ results_staging  │
             │                  │
             │ source_url       │  ◄── SAS PDF URL (dedupe key)
             │ source_title_raw │
             │ source_site='SAS'│
             │ pdf_local_path   │
             │ regatta_id=      │  ◄── Placeholder 'RAW:SAS'
             │   'RAW:SAS'      │
             └──────────────────┘
```

### 2.2 Existing Source Fields by Table

#### `events` table (calendar/event listing)
| Column | Type | Current Usage | Populated? |
|--------|------|---------------|------------|
| `source` | text | `'sas'`, `'external'` | ✅ Yes |
| `source_event_id` | text | SAS event ID or external event ID | ✅ Yes |
| `source_url` | text | Details page URL (not results PDF) | ✅ Yes |
| `regatta_id` | text FK | Link to regattas (when results exist) | Partial |
| `scrape_run_id` | text | `YYYYMMDDHHMM` timestamp of scrape | ✅ Yes |
| `last_seen_at` | timestamptz | Last scrape detection | ✅ Yes |

**Note**: `events.source_url` is the EVENT LISTING page, NOT the results PDF.

#### `regattas` table (regatta-level provenance)
| Column | Type | Current Usage | Populated? |
|--------|------|---------------|------------|
| `source_url` | text | URL of PDF/results artifact | Partial (~30%) |
| `local_file_path` | text | Local PDF copy path | Rare |
| `file_type` | text | `'PDF'`, `'pdf'`, `'html'`, `'screenshot'` | Rare |
| `doc_hash` | text | MD5 checksum; unique index | Rare |
| `import_status` | text | `'pending'`, `'imported'`, `'manual'` | ✅ Default only |
| `source_platform` | text | **UNUSED** — column exists, no values | ❌ Never |

**Critical**: `regattas.source_url` is the ONLY field that can trace back to the original document.

#### `regatta_blocks` table (fleet/class grouping)
| Column | Type | Current Usage | Populated? |
|--------|------|---------------|------------|
| `regatta_id` | text FK | Link to parent regatta | ✅ Yes |
| `class_id` | int FK | Link to class | ✅ Yes |
| (no source columns) | — | — | — |

**Gap**: No way to trace a block to a specific source if regatta has multiple sources.

#### `results` table (individual result rows)
| Column | Type | Current Usage | Populated? |
|--------|------|---------------|------------|
| `regatta_id` | text FK | Link to regatta (inherits source) | ✅ Yes |
| `block_id` | text FK | Link to regatta_block | ✅ Yes |
| `entry_id` | int FK | Link to entries (nullable) | Partial |
| `class_original` | text | Exact text from PDF/sheet | ✅ Yes |
| `club_raw` | text | Club as printed on sheet | ✅ Yes |
| `validation_flag` | text | **DEAD COLUMN** — never written | ❌ Never |
| `source_row_text` | text | **DEAD COLUMN** — never written | ❌ Never |
| `match_status_helm` | text | Identity resolution audit | ✅ Yes |
| `match_status_crew` | text | Identity resolution audit | ✅ Yes |

**Gap**: Results inherit source only via `regatta_id` → `regattas.source_url`. If a regatta has multiple sources (e.g., SAS PDF + Sailwave correction), cannot trace which source a result came from.

#### `entries` table (regatta entries)
| Column | Type | Current Usage | Populated? |
|--------|------|---------------|------------|
| `regatta_id` | text | Link to regatta (NOT an FK!) | ✅ Yes |
| `block_id` | text | Block identifier | ✅ Yes |
| (no source columns) | — | — | — |

**Gap**: `entries.regatta_id` is text, not a proper FK. No source tracking.

#### `results_staging` table (staging for ingestion)
| Column | Type | Current Usage | Populated? |
|--------|------|---------------|------------|
| `source_url` | text | SAS PDF URL (dedupe key) | ✅ Yes (runtime) |
| `source_title_raw` | text | Raw SAS listing title | ✅ Yes (runtime) |
| `source_site` | text | Hardcoded `'SAS'` | ✅ Yes (runtime) |
| `pdf_local_path` | text | Local PDF storage path | ✅ Yes (runtime) |
| `validation_status` | text | `'PENDING'` only | ✅ Default only |
| `regatta_id` | text | Placeholder `'RAW:SAS'` | ✅ Placeholder |

**Gap**: Staging has source info, but it's LOST when promoting to `results` (no carry-forward).

### 2.3 Current Source Types (Implicit Values)

From code analysis:

| Context | Column | Values Used |
|---------|--------|-------------|
| `events` | `source` | `'sas'`, `'external'` |
| `results_staging` | `source_site` | `'SAS'` (hardcoded) |
| `regattas` | `import_status` | `'pending'`, `'imported'`, `'manual'` |
| `regattas` | `file_type` | `'PDF'`, `'pdf'`, `'html'`, `'screenshot'` |
| Manual scripts | (none) | Implicit via script filename in `imports_log.source_file` |

### 2.4 Critical Gaps

1. **Single source per regatta** — `regattas.source_url` is scalar; if updated, original is lost
2. **No result→source link** — Results trace via regatta, but if regatta has multiple sources, cannot distinguish
3. **Staging provenance lost** — `results_staging` has source info; promoting to `results` loses it
4. **Dead columns** — `validation_flag`, `source_row_text` on `results` never populated
5. **entries not FK'd** — `entries.regatta_id` is text, not FK; no source tracking
6. **No import method** — Cannot tell if data was scraped, uploaded, manually entered
7. **No authority hierarchy** — Cannot resolve conflicts between sources
8. **No manual-parsing flag** — Cannot distinguish OCR/AI-parsed from human-transcribed
9. **No secondary source support** — Adding a correction source would overwrite original

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

### 6.1 Design Principles for Provenance

**PRINCIPLE 1: Original Source is Immutable**
- Once recorded, the ORIGINAL source artifact is NEVER modified or deleted
- The `is_original` flag marks the first source that created a record
- Existing `regattas.source_url` is migrated as the original source

**PRINCIPLE 2: Secondary Sources are Additive**
- Additional sources (corrections, Sailwave exports, club uploads) are ADDED, not replaced
- Each source gets its own artifact record with relationship to the regatta/result
- `is_original=FALSE` distinguishes secondary sources

**PRINCIPLE 3: Every Result Traces to Exact Source**
- Results link to specific artifact, not just regatta
- Cell-level provenance (optional) traces individual values to source locations
- Import method and parser version are captured

**PRINCIPLE 4: Authority Determines Precedence, Not Replacement**
- Higher-authority sources take precedence for DISPLAY
- Lower-authority originals are PRESERVED for audit
- Conflict resolution creates new records, doesn't overwrite

### 6.2 New Lookup Tables

```sql
-- Source type enumeration with authority
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

-- Artifact status (lifecycle of the artifact itself)
CREATE TABLE artifact_statuses (
    status_code         TEXT PRIMARY KEY,
    status_name         TEXT NOT NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO artifact_statuses (status_code, status_name, description) VALUES
('active', 'Active', 'Artifact is valid and in use'),
('archived', 'Archived', 'Artifact retained for audit but no longer primary'),
('corrupted', 'Corrupted', 'File integrity check failed'),
('deleted_source', 'Source Deleted', 'Original URL no longer accessible'),
('pending_retrieval', 'Pending Retrieval', 'Scheduled for download/refresh');
```

### 6.3 Source Artifacts Table (Immutable Record of Each Source)

```sql
CREATE TABLE source_artifacts (
    artifact_id         BIGSERIAL PRIMARY KEY,
    
    -- Source identification
    source_type         TEXT NOT NULL REFERENCES source_types(source_type_code),
    import_method       TEXT NOT NULL REFERENCES import_methods(import_method_code),
    
    -- Authority & Status
    authority_level     SMALLINT NOT NULL CHECK (authority_level BETWEEN 0 AND 100),
    artifact_status     TEXT NOT NULL DEFAULT 'active' REFERENCES artifact_statuses(status_code),
    
    -- Source locators (IMMUTABLE once set)
    source_url          TEXT,                   -- Original URL (SAS PDF, external page)
    
    -- Raw file retention
    raw_file_path       TEXT,                   -- Permanent local archive path (never deleted)
    raw_file_retained   BOOLEAN NOT NULL DEFAULT FALSE,
    retention_policy    TEXT DEFAULT 'permanent', -- 'permanent', '5_years', 'until_superseded'
    
    -- Working copy (may be updated/regenerated)
    working_file_path   TEXT,                   -- Current working copy path
    source_filename     TEXT,                   -- Original filename
    
    -- Version & Retrieval timestamps
    artifact_version    INTEGER NOT NULL DEFAULT 1,
    first_retrieved_at  TIMESTAMPTZ,            -- When first downloaded/captured
    last_retrieved_at   TIMESTAMPTZ,            -- Last successful retrieval
    last_verified_at    TIMESTAMPTZ,            -- Last integrity check
    source_modified_at  TIMESTAMPTZ,            -- Last-Modified header from source
    
    -- File metadata
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
    
    -- Live session/device provenance (for future SailingSA Live)
    live_session_id     TEXT,                   -- Live scoring session identifier
    live_device_id      TEXT,                   -- Device that captured data
    live_device_type    TEXT,                   -- 'ios_app', 'android_app', 'web', 'hardware'
    live_gps_lat        NUMERIC(9,6),           -- GPS coordinates at capture
    live_gps_lng        NUMERIC(9,6),
    live_captured_by_user TEXT,                 -- User account on Live system
    
    -- Audit (IMMUTABLE core fields)
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    captured_by         TEXT NOT NULL DEFAULT 'system',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NOTE: No updated_at for core fields - use artifact_version for changes
);

-- Indexes
CREATE INDEX idx_source_artifacts_source_type ON source_artifacts(source_type);
CREATE INDEX idx_source_artifacts_status ON source_artifacts(artifact_status);
CREATE INDEX idx_source_artifacts_checksum ON source_artifacts(checksum_md5) WHERE checksum_md5 IS NOT NULL;
CREATE INDEX idx_source_artifacts_url ON source_artifacts(source_url) WHERE source_url IS NOT NULL;
CREATE INDEX idx_source_artifacts_live_session ON source_artifacts(live_session_id) WHERE live_session_id IS NOT NULL;

-- Prevent modification of immutable source locators after creation
CREATE OR REPLACE FUNCTION prevent_artifact_immutable_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.source_url IS NOT NULL AND NEW.source_url IS DISTINCT FROM OLD.source_url THEN
        RAISE EXCEPTION 'Cannot modify source_url on existing artifact (id=%)', OLD.artifact_id;
    END IF;
    IF OLD.raw_file_path IS NOT NULL AND NEW.raw_file_path IS DISTINCT FROM OLD.raw_file_path THEN
        RAISE EXCEPTION 'Cannot modify raw_file_path on existing artifact (id=%)', OLD.artifact_id;
    END IF;
    IF OLD.checksum_md5 IS NOT NULL AND NEW.checksum_md5 IS DISTINCT FROM OLD.checksum_md5 THEN
        RAISE EXCEPTION 'Cannot modify checksum_md5 on existing artifact (id=%)', OLD.artifact_id;
    END IF;
    IF OLD.first_retrieved_at IS NOT NULL AND NEW.first_retrieved_at IS DISTINCT FROM OLD.first_retrieved_at THEN
        RAISE EXCEPTION 'Cannot modify first_retrieved_at on existing artifact (id=%)', OLD.artifact_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_artifact_immutable_modification
BEFORE UPDATE ON source_artifacts
FOR EACH ROW EXECUTE FUNCTION prevent_artifact_immutable_modification();
```

### 6.4 Regatta Source Link Table (Many-to-Many, Exactly One Primary)

```sql
-- Link regattas to their source artifacts (many-to-many for multiple sources)
-- ORIGINAL source is preserved; secondary sources are added
CREATE TABLE regatta_sources (
    regatta_source_id   BIGSERIAL PRIMARY KEY,
    regatta_id          TEXT NOT NULL REFERENCES regattas(regatta_id) ON DELETE CASCADE,
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE RESTRICT,
    
    -- Original vs Secondary (is_original is IMMUTABLE)
    is_original         BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = first source that created this regatta
    is_primary          BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = current authoritative source for display
    superseded_by       BIGINT REFERENCES source_artifacts(artifact_id),
    superseded_at       TIMESTAMPTZ,
    
    -- Authority
    authority_level     SMALLINT NOT NULL,               -- Copied from artifact at link time
    authority_override  SMALLINT,                        -- Override if needed
    
    -- Validation
    validation_status   TEXT NOT NULL DEFAULT 'draft' REFERENCES validation_statuses(status_code),
    validated_by        TEXT,
    validated_at        TIMESTAMPTZ,
    validation_notes    TEXT,
    
    -- Partial scope fields
    covers_all_classes  BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE = partial source
    class_ids_covered   INTEGER[],                       -- Specific class_ids if partial
    covers_all_races    BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE = partial races
    race_numbers_covered INTEGER[],                      -- Specific race numbers if partial
    covers_series_only  BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = series totals only, no race-by-race
    
    -- Correction/audit fields
    correction_reason   TEXT,                            -- Why this source was added (if secondary)
    correction_type     TEXT CHECK (correction_type IN (
                            'initial', 'correction', 'amendment', 'protest_result',
                            'redress', 'disqualification', 'reinstatement', 'rescore')),
    correction_reference TEXT,                           -- Reference to official notice/decision
    
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          TEXT,
    notes               TEXT,
    
    UNIQUE (regatta_id, artifact_id)
);

-- Only one original source per regatta (the first one)
CREATE UNIQUE INDEX uq_regatta_original_source ON regatta_sources(regatta_id) WHERE is_original = TRUE;

-- At most one primary source per regatta (uniqueness constraint)
CREATE UNIQUE INDEX uq_regatta_primary_source ON regatta_sources(regatta_id) WHERE is_primary = TRUE;

CREATE INDEX idx_regatta_sources_artifact ON regatta_sources(artifact_id);
CREATE INDEX idx_regatta_sources_validation ON regatta_sources(validation_status);
CREATE INDEX idx_regatta_sources_regatta ON regatta_sources(regatta_id);

-- Prevent changing is_original after creation
CREATE OR REPLACE FUNCTION prevent_original_flag_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_original = TRUE AND NEW.is_original = FALSE THEN
        RAISE EXCEPTION 'Cannot unset is_original flag (id=%)', OLD.regatta_source_id;
    END IF;
    IF OLD.is_original = FALSE AND NEW.is_original = TRUE THEN
        RAISE EXCEPTION 'Cannot set is_original flag on existing non-original source (id=%)', OLD.regatta_source_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_regatta_original_flag_change
BEFORE UPDATE ON regatta_sources
FOR EACH ROW EXECUTE FUNCTION prevent_original_flag_change();

-- When setting is_primary=TRUE, supersede previous primary (at-most-one enforcement)
CREATE OR REPLACE FUNCTION enforce_single_primary_regatta_source()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_primary = TRUE THEN
        UPDATE regatta_sources
        SET is_primary = FALSE, 
            superseded_by = NEW.artifact_id, 
            superseded_at = NOW(),
            updated_at = NOW()
        WHERE regatta_id = NEW.regatta_id 
          AND regatta_source_id != COALESCE(NEW.regatta_source_id, -1)
          AND is_primary = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_single_primary_regatta_source
BEFORE INSERT OR UPDATE OF is_primary ON regatta_sources
FOR EACH ROW 
WHEN (NEW.is_primary = TRUE)
EXECUTE FUNCTION enforce_single_primary_regatta_source();

-- ============================================================================
-- DEFERRED CONSTRAINT: Exactly one primary per regatta (where sources exist)
-- Checked at transaction COMMIT, not at statement time
-- ============================================================================
CREATE OR REPLACE FUNCTION check_exactly_one_primary_per_regatta()
RETURNS TRIGGER AS $$
DECLARE
    primary_count INTEGER;
    source_count INTEGER;
BEGIN
    -- Count sources and primaries for this regatta
    SELECT COUNT(*), COUNT(*) FILTER (WHERE is_primary = TRUE)
    INTO source_count, primary_count
    FROM regatta_sources
    WHERE regatta_id = COALESCE(NEW.regatta_id, OLD.regatta_id);
    
    -- If sources exist, exactly one must be primary
    IF source_count > 0 AND primary_count != 1 THEN
        RAISE EXCEPTION 'Regatta % has % sources but % primary (must be exactly 1)',
            COALESCE(NEW.regatta_id, OLD.regatta_id), source_count, primary_count;
    END IF;
    
    RETURN NULL; -- CONSTRAINT TRIGGER returns NULL
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_check_exactly_one_primary_per_regatta
AFTER INSERT OR UPDATE OR DELETE ON regatta_sources
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION check_exactly_one_primary_per_regatta();
```

### 6.5 Source Conflicts Table (Conflict Records with Full Audit)

```sql
-- Track conflicts between sources for admin resolution
CREATE TABLE source_conflicts (
    conflict_id         BIGSERIAL PRIMARY KEY,
    
    -- What entity is conflicted
    entity_type         TEXT NOT NULL CHECK (entity_type IN ('regatta', 'result', 'entry', 'boat')),
    regatta_id          TEXT REFERENCES regattas(regatta_id) ON DELETE CASCADE,
    result_id           BIGINT REFERENCES results(result_id) ON DELETE CASCADE,
    entry_id            BIGINT REFERENCES entries(entry_id) ON DELETE CASCADE,
    boat_id             BIGINT REFERENCES boats(boat_id) ON DELETE CASCADE,
    
    -- Conflicting artifacts
    artifact_a_id       BIGINT NOT NULL REFERENCES source_artifacts(artifact_id),
    artifact_b_id       BIGINT NOT NULL REFERENCES source_artifacts(artifact_id),
    authority_a         SMALLINT NOT NULL,      -- Authority level of artifact A at detection
    authority_b         SMALLINT NOT NULL,      -- Authority level of artifact B at detection
    
    -- Conflict details
    conflict_type       TEXT NOT NULL CHECK (conflict_type IN (
                            'value_mismatch', 'duplicate_source', 'authority_tie',
                            'partial_overlap', 'contradictory_correction', 'missing_data',
                            'checksum_mismatch', 'date_conflict', 'identity_conflict')),
    conflict_severity   TEXT NOT NULL DEFAULT 'medium' CHECK (conflict_severity IN (
                            'low', 'medium', 'high', 'critical')),
    field_name          TEXT,                   -- Which field conflicts (if applicable)
    value_a             TEXT,                   -- Value from artifact A
    value_b             TEXT,                   -- Value from artifact B
    value_a_locator     TEXT,                   -- Source locator for value A
    value_b_locator     TEXT,                   -- Source locator for value B
    conflict_details    JSONB,                  -- Additional context (full row diff, etc.)
    
    -- Resolution workflow
    resolution_status   TEXT NOT NULL DEFAULT 'pending' CHECK (resolution_status IN (
                            'pending', 'in_review', 'resolved', 'deferred', 'ignored', 'escalated')),
    assigned_to         TEXT,                   -- Admin assigned to resolve
    assigned_at         TIMESTAMPTZ,
    due_date            DATE,                   -- Resolution deadline
    priority            SMALLINT DEFAULT 50 CHECK (priority BETWEEN 0 AND 100),
    
    -- Resolution outcome
    resolved_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    resolution_action   TEXT CHECK (resolution_action IN (
                            'accept_a', 'accept_b', 'accept_higher_authority',
                            'merge', 'manual_value', 'create_correction',
                            'defer', 'ignore', 'escalate', 'split')),
    resolved_value      TEXT,                   -- Final value if manual
    resolution_details  JSONB,                  -- Full resolution context
    
    -- Resolution audit
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    resolution_reason   TEXT NOT NULL DEFAULT '',
    resolution_reference TEXT,                  -- Link to official decision/notice/protest
    resolution_artifact_id BIGINT REFERENCES source_artifacts(artifact_id), -- New artifact if correction created
    
    -- Review/escalation
    reviewed_by         TEXT,                   -- Second reviewer if escalated
    reviewed_at         TIMESTAMPTZ,
    review_notes        TEXT,
    escalated_to        TEXT,                   -- Higher authority for escalation
    escalated_at        TIMESTAMPTZ,
    escalation_reason   TEXT,
    
    -- History tracking
    previous_resolution_id BIGINT REFERENCES source_conflicts(conflict_id), -- If reopened
    reopen_count        INTEGER NOT NULL DEFAULT 0,
    last_reopened_at    TIMESTAMPTZ,
    last_reopened_by    TEXT,
    last_reopened_reason TEXT,
    
    -- Detection audit
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detected_by         TEXT NOT NULL DEFAULT 'system',
    detection_method    TEXT DEFAULT 'auto' CHECK (detection_method IN (
                            'auto', 'manual_report', 'audit_scan', 'import_check')),
    detection_context   JSONB,                  -- What triggered detection
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure at least one entity reference
    CONSTRAINT chk_conflict_has_entity CHECK (
        regatta_id IS NOT NULL OR result_id IS NOT NULL OR 
        entry_id IS NOT NULL OR boat_id IS NOT NULL
    )
);

-- Indexes
CREATE INDEX idx_source_conflicts_pending ON source_conflicts(resolution_status) 
    WHERE resolution_status IN ('pending', 'in_review');
CREATE INDEX idx_source_conflicts_regatta ON source_conflicts(regatta_id) WHERE regatta_id IS NOT NULL;
CREATE INDEX idx_source_conflicts_result ON source_conflicts(result_id) WHERE result_id IS NOT NULL;
CREATE INDEX idx_source_conflicts_assigned ON source_conflicts(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_source_conflicts_priority ON source_conflicts(priority DESC, created_at) 
    WHERE resolution_status = 'pending';
CREATE INDEX idx_source_conflicts_artifact_a ON source_conflicts(artifact_a_id);
CREATE INDEX idx_source_conflicts_artifact_b ON source_conflicts(artifact_b_id);

-- Auto-update updated_at
CREATE TRIGGER trg_source_conflicts_updated_at
BEFORE UPDATE ON source_conflicts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Helper function (create if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 6.6 Result Source Link Table (Result → Artifact Traceability)

```sql
-- Link results to their source artifacts (one result can have multiple source records)
-- ORIGINAL source is preserved; corrections/updates create new artifact links
CREATE TABLE result_sources (
    result_source_id    BIGSERIAL PRIMARY KEY,
    result_id           BIGINT NOT NULL REFERENCES results(result_id) ON DELETE CASCADE,
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE RESTRICT,
    
    -- Original vs Secondary (is_original is IMMUTABLE)
    is_original         BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = first source that created this result
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,   -- TRUE = current version of this result
    superseded_by       BIGINT REFERENCES source_artifacts(artifact_id),
    superseded_at       TIMESTAMPTZ,
    
    -- Source locator within artifact
    source_locator      TEXT,                   -- 'pdf:p3:r12', 'csv:row45', 'sailwave:competitor:123'
    
    -- Partial scope: what this source provided
    fields_from_source  TEXT[],                 -- ['sail_number', 'helm_name', 'R1', 'R2', 'total_points']
    race_numbers_from_source INTEGER[],         -- [1, 2, 3] if partial races
    
    -- Correction/audit fields
    correction_reason   TEXT,
    correction_type     TEXT CHECK (correction_type IN (
                            'initial', 'correction', 'amendment', 'protest_result',
                            'redress', 'disqualification', 'reinstatement', 'rescore')),
    correction_reference TEXT,
    
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          TEXT,
    notes               TEXT,
    
    UNIQUE (result_id, artifact_id)
);

-- Only one original source per result
CREATE UNIQUE INDEX uq_result_original_source ON result_sources(result_id) WHERE is_original = TRUE;

-- At most one current source per result (uniqueness constraint)
CREATE UNIQUE INDEX uq_result_current_source ON result_sources(result_id) WHERE is_current = TRUE;

CREATE INDEX idx_result_sources_artifact ON result_sources(artifact_id);
CREATE INDEX idx_result_sources_result ON result_sources(result_id);

-- Prevent changing is_original after creation
CREATE TRIGGER trg_prevent_result_original_flag_change
BEFORE UPDATE ON result_sources
FOR EACH ROW EXECUTE FUNCTION prevent_original_flag_change();

-- When setting is_current=TRUE, supersede previous current (at-most-one enforcement)
CREATE OR REPLACE FUNCTION enforce_single_current_result_source()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = TRUE THEN
        UPDATE result_sources
        SET is_current = FALSE, 
            superseded_by = NEW.artifact_id, 
            superseded_at = NOW(),
            updated_at = NOW()
        WHERE result_id = NEW.result_id 
          AND result_source_id != COALESCE(NEW.result_source_id, -1)
          AND is_current = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_single_current_result_source
BEFORE INSERT OR UPDATE OF is_current ON result_sources
FOR EACH ROW 
WHEN (NEW.is_current = TRUE)
EXECUTE FUNCTION enforce_single_current_result_source();

-- ============================================================================
-- DEFERRED CONSTRAINT: Exactly one current per result (where sources exist)
-- Checked at transaction COMMIT, not at statement time
-- ============================================================================
CREATE OR REPLACE FUNCTION check_exactly_one_current_per_result()
RETURNS TRIGGER AS $$
DECLARE
    current_count INTEGER;
    source_count INTEGER;
BEGIN
    -- Count sources and currents for this result
    SELECT COUNT(*), COUNT(*) FILTER (WHERE is_current = TRUE)
    INTO source_count, current_count
    FROM result_sources
    WHERE result_id = COALESCE(NEW.result_id, OLD.result_id);
    
    -- If sources exist, exactly one must be current
    IF source_count > 0 AND current_count != 1 THEN
        RAISE EXCEPTION 'Result % has % sources but % current (must be exactly 1)',
            COALESCE(NEW.result_id, OLD.result_id), source_count, current_count;
    END IF;
    
    RETURN NULL; -- CONSTRAINT TRIGGER returns NULL
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_check_exactly_one_current_per_result
AFTER INSERT OR UPDATE OR DELETE ON result_sources
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION check_exactly_one_current_per_result();
```

### 6.7 Result Source Mapping Table (Cell-Level Provenance — Optional)

```sql
-- Optional: cell-level provenance for results (M2 from goals.md)
-- Traces individual field values to exact source locations
CREATE TABLE result_source_mappings (
    mapping_id          BIGSERIAL PRIMARY KEY,
    -- Target
    result_id           BIGINT NOT NULL REFERENCES results(result_id) ON DELETE CASCADE,
    field_name          TEXT NOT NULL,          -- 'sail_number', 'helm_name', 'R1', 'total_points', etc.
    -- Source
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE RESTRICT,
    source_locator      TEXT,                   -- 'pdf:p3:r12:c8', 'csv:row45:col_D', 'sailwave:competitor:123:race5'
    -- Values (both preserved)
    raw_value           TEXT,                   -- Exact value from source
    normalized_value    TEXT,                   -- Value after normalization
    -- Is this the original value or a correction?
    is_original         BOOLEAN NOT NULL DEFAULT TRUE,
    supersedes_mapping_id BIGINT REFERENCES result_source_mappings(mapping_id),
    -- Correction audit
    correction_reason   TEXT,
    correction_type     TEXT,
    -- Confidence
    extraction_confidence SMALLINT CHECK (extraction_confidence BETWEEN 0 AND 100),
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX idx_result_source_mappings_result ON result_source_mappings(result_id);
CREATE INDEX idx_result_source_mappings_artifact ON result_source_mappings(artifact_id);
CREATE INDEX idx_result_source_mappings_field ON result_source_mappings(result_id, field_name);
```

### 6.7 Modify Existing Tables

```sql
-- Add to regattas (augment existing columns)
-- NOTE: Existing source_url is preserved for backward compatibility
--       New provenance flows through regatta_sources table
ALTER TABLE regattas
    ADD COLUMN IF NOT EXISTS original_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS primary_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'validated' REFERENCES validation_statuses(status_code),
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;

-- IMPORTANT: Do NOT drop or clear existing source_url - it becomes the original artifact

-- Add to results (revive dead columns with proper semantics)
ALTER TABLE results
    ADD COLUMN IF NOT EXISTS original_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS current_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS row_validation_status TEXT DEFAULT 'validated' REFERENCES validation_statuses(status_code),
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;

-- Existing validation_flag will be deprecated in favor of row_validation_status
-- Existing source_row_text remains for raw row capture (activate in ingestion)

-- Add to entries (add FK and source tracking)
ALTER TABLE entries
    ADD COLUMN IF NOT EXISTS original_artifact_id BIGINT REFERENCES source_artifacts(artifact_id);
-- NOTE: entries.regatta_id should become a proper FK in future migration

-- Add to results_staging (full provenance before promotion)
ALTER TABLE results_staging
    ADD COLUMN IF NOT EXISTS source_type TEXT REFERENCES source_types(source_type_code),
    ADD COLUMN IF NOT EXISTS import_method TEXT REFERENCES import_methods(import_method_code),
    ADD COLUMN IF NOT EXISTS artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS source_locator TEXT;  -- Position within artifact

-- Add to regatta_blocks (block-level source when different from regatta)
ALTER TABLE regatta_blocks
    ADD COLUMN IF NOT EXISTS artifact_id BIGINT REFERENCES source_artifacts(artifact_id);
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

## 8. Provenance Chain — Tracing Results to Original Source

### 8.1 Complete Trace Path

Every result can trace back to its exact original source via:

```
result_id
    │
    ├─► result_sources (is_original=TRUE)
    │       │
    │       └─► artifact_id ───► source_artifacts
    │                               │
    │                               ├── source_url (ORIGINAL URL - immutable)
    │                               ├── source_file_path (local copy)
    │                               ├── checksum_md5 (integrity check)
    │                               ├── source_type (authority level)
    │                               ├── import_method (how it entered)
    │                               ├── parser_version (what processed it)
    │                               └── manually_parsed (human involvement)
    │
    └─► result_source_mappings (optional cell-level)
            │
            ├── field_name ('sail_number', 'R1', etc.)
            ├── source_locator ('pdf:p3:r12:c8')
            ├── raw_value (exact from source)
            └── normalized_value (after processing)
```

### 8.2 Query Examples

**Trace result to original source URL:**
```sql
SELECT r.result_id, r.helm_name, r.sail_number,
       sa.source_url AS original_source_url,
       sa.source_type, sa.import_method,
       sa.captured_at, sa.parser_version
FROM results r
JOIN result_sources rs ON rs.result_id = r.result_id AND rs.is_original = TRUE
JOIN source_artifacts sa ON sa.artifact_id = rs.artifact_id
WHERE r.result_id = 12345;
```

**Find all sources for a regatta (original + secondary):**
```sql
SELECT reg.regatta_id, reg.event_name,
       rs.is_original, rs.is_primary, rs.superseded_at,
       sa.source_url, sa.source_type, sa.import_method
FROM regattas reg
JOIN regatta_sources rs ON rs.regatta_id = reg.regatta_id
JOIN source_artifacts sa ON sa.artifact_id = rs.artifact_id
WHERE reg.regatta_id = 'R-2026-001'
ORDER BY rs.is_original DESC, rs.created_at;
```

**Audit: which results came from which source:**
```sql
SELECT sa.source_url, sa.source_type, COUNT(*) AS result_count
FROM results r
JOIN result_sources rs ON rs.result_id = r.result_id AND rs.is_current = TRUE
JOIN source_artifacts sa ON sa.artifact_id = rs.artifact_id
WHERE r.regatta_id = 'R-2026-001'
GROUP BY sa.artifact_id, sa.source_url, sa.source_type;
```

### 8.3 Adding Secondary Sources (Without Replacing Original)

When a correction or update source is added:

```sql
-- 1. Create new artifact for the correction source
INSERT INTO source_artifacts (source_type, import_method, source_url, ...)
VALUES ('sailwave', 'sailwave_xml', 'https://club.com/results.blw', ...)
RETURNING artifact_id;  -- e.g., 456

-- 2. Mark old regatta_source as superseded (but DON'T delete)
UPDATE regatta_sources
SET is_primary = FALSE, superseded_by = 456, superseded_at = NOW()
WHERE regatta_id = 'R-2026-001' AND is_primary = TRUE;

-- 3. Add new regatta_source as primary (original stays intact)
INSERT INTO regatta_sources (regatta_id, artifact_id, is_original, is_primary, ...)
VALUES ('R-2026-001', 456, FALSE, TRUE, ...);

-- Original source (is_original=TRUE) is NEVER modified
```

---

## 9. Migration Strategy

### 9.1 Phase 1: Schema Only (No Data Changes)

1. Create lookup tables:
   - `source_types` (with authority levels)
   - `import_methods`
   - `validation_statuses`
   - `artifact_statuses`
2. Seed all lookup tables with defined values
3. Create core tables:
   - `source_artifacts` (with immutability triggers)
   - `regatta_sources` (with single-primary enforcement)
   - `result_sources` (with single-current enforcement)
   - `source_conflicts` (conflict tracking)
   - `result_source_mappings` (optional cell-level)
4. Add new columns to existing tables:
   - `regattas`: `original_artifact_id`, `primary_artifact_id`, `validation_status`, `manually_parsed`
   - `results`: `original_artifact_id`, `current_artifact_id`, `row_validation_status`, `manually_parsed`
   - `entries`: `original_artifact_id`
   - `results_staging`: `source_type`, `import_method`, `artifact_id`, `manually_parsed`, `source_locator`
   - `regatta_blocks`: `artifact_id`
5. Create all triggers:
   - `trg_prevent_artifact_immutable_modification`
   - `trg_prevent_regatta_original_flag_change`
   - `trg_enforce_single_primary_regatta_source`
   - `trg_prevent_result_original_flag_change`
   - `trg_enforce_single_current_result_source`
6. **Do not populate provenance on existing data yet**

### 9.2 Phase 2: Backfill Existing Data (Preserve Original Sources)

**CRITICAL**: Existing `regattas.source_url` values are the ORIGINAL sources. They must be preserved.

```sql
-- 2a. Create source_artifact for each regatta with source_url
INSERT INTO source_artifacts (
    source_type, import_method, source_url, source_file_path, 
    captured_at, captured_by
)
SELECT 
    CASE 
        WHEN source_url LIKE '%sailing.org.za%' THEN 'sas_pdf'
        WHEN import_status = 'manual' THEN 'manual_admin'
        ELSE 'unknown'
    END,
    CASE 
        WHEN source_url LIKE '%sailing.org.za%' THEN 'pdf_table_extract'
        WHEN import_status = 'manual' THEN 'manual_entry'
        ELSE 'migration'
    END,
    source_url,
    local_file_path,
    COALESCE(created_at, NOW()),
    'migration'
FROM regattas
WHERE source_url IS NOT NULL;

-- 2b. Link regattas to artifacts as ORIGINAL source
INSERT INTO regatta_sources (
    regatta_id, artifact_id, is_original, is_primary, validation_status, created_by
)
SELECT 
    r.regatta_id, 
    sa.artifact_id,
    TRUE,   -- is_original
    TRUE,   -- is_primary (original is primary until superseded)
    'validated',
    'migration'
FROM regattas r
JOIN source_artifacts sa ON sa.source_url = r.source_url
WHERE r.source_url IS NOT NULL;

-- 2c. Update regattas with artifact references
UPDATE regattas r
SET original_artifact_id = rs.artifact_id,
    primary_artifact_id = rs.artifact_id
FROM regatta_sources rs
WHERE rs.regatta_id = r.regatta_id AND rs.is_original = TRUE;

-- 2d. Create result_sources for all results (inherit from regatta)
INSERT INTO result_sources (
    result_id, artifact_id, is_original, is_current, created_by
)
SELECT 
    r.result_id,
    reg.original_artifact_id,
    TRUE,   -- is_original
    TRUE,   -- is_current
    'migration'
FROM results r
JOIN regattas reg ON reg.regatta_id = r.regatta_id
WHERE reg.original_artifact_id IS NOT NULL;

-- 2e. Update results with artifact references
UPDATE results r
SET original_artifact_id = rs.artifact_id,
    current_artifact_id = rs.artifact_id
FROM result_sources rs
WHERE rs.result_id = r.result_id AND rs.is_original = TRUE;
```

### 9.3 Phase 3: Activate New Pipelines

1. Update `results_ingestion_common.py` to create source_artifacts
2. Update staging→production promotion to carry forward provenance
3. Set `is_original=TRUE` for newly created records
4. Update admin UI to capture source info on manual entry
5. Deploy and monitor

### 9.4 Handling Regattas Without source_url

For regattas where `source_url IS NULL`:

```sql
-- Create placeholder artifact for unknown sources
INSERT INTO source_artifacts (source_type, import_method, captured_by)
VALUES ('unknown', 'migration', 'migration')
RETURNING artifact_id;  -- use this for orphan regattas

-- Link orphan regattas to placeholder
INSERT INTO regatta_sources (regatta_id, artifact_id, is_original, is_primary, ...)
SELECT regatta_id, <placeholder_artifact_id>, TRUE, TRUE, ...
FROM regattas WHERE source_url IS NULL;
```

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

### 9.4 Artifact Statuses Seed

```sql
INSERT INTO artifact_statuses (status_code, status_name, description) VALUES
('active', 'Active', 'Artifact is valid and in use'),
('archived', 'Archived', 'Artifact retained for audit but no longer primary'),
('corrupted', 'Corrupted', 'File integrity check failed'),
('deleted_source', 'Source Deleted', 'Original URL no longer accessible'),
('pending_retrieval', 'Pending Retrieval', 'Scheduled for download/refresh');
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
