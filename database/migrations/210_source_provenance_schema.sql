-- ============================================================================
-- SOURCE PROVENANCE SCHEMA MIGRATION
-- Version: 210
-- Date: 2026-07-27
-- Status: Schema + safe data migration (no destructive changes)
-- Depends on: 200_boat_register_schema.sql
-- ============================================================================

-- ============================================================================
-- BEGIN TRANSACTION
-- ============================================================================
BEGIN;

-- ============================================================================
-- STEP 1: Create lookup tables
-- ============================================================================

-- Source type enumeration with authority levels
CREATE TABLE IF NOT EXISTS source_types (
    source_type_code    TEXT PRIMARY KEY,
    source_type_name    TEXT NOT NULL,
    description         TEXT,
    authority_level     SMALLINT NOT NULL CHECK (authority_level BETWEEN 0 AND 100),
    is_external         BOOLEAN NOT NULL DEFAULT FALSE,
    requires_evidence   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Import method enumeration
CREATE TABLE IF NOT EXISTS import_methods (
    import_method_code  TEXT PRIMARY KEY,
    import_method_name  TEXT NOT NULL,
    description         TEXT,
    requires_manual_parsing BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Validation status enumeration
CREATE TABLE IF NOT EXISTS validation_statuses (
    status_code         TEXT PRIMARY KEY,
    status_name         TEXT NOT NULL,
    description         TEXT,
    is_terminal         BOOLEAN NOT NULL DEFAULT FALSE,
    display_order       SMALLINT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Artifact status enumeration
CREATE TABLE IF NOT EXISTS artifact_statuses (
    status_code         TEXT PRIMARY KEY,
    status_name         TEXT NOT NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Source scope enumeration (what level does this source cover?)
CREATE TABLE IF NOT EXISTS source_scopes (
    scope_code          TEXT PRIMARY KEY,
    scope_name          TEXT NOT NULL,
    description         TEXT,
    scope_level         SMALLINT NOT NULL,  -- Higher = more specific (REGATTA=1, RESULT=6)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- STEP 2: Seed lookup tables
-- ============================================================================

-- Source types (authority hierarchy)
INSERT INTO source_types (source_type_code, source_type_name, description, authority_level, is_external, requires_evidence) VALUES
('sas_official', 'SA Sailing Official', 'Official results from sailing.org.za with SAS verification', 100, FALSE, TRUE),
('sas_pdf', 'SA Sailing PDF', 'SAS-published PDF without explicit verification', 90, FALSE, TRUE),
('sailingsa_live', 'SailingSA Live', 'Our own live scoring system', 85, FALSE, FALSE),
('sailwave', 'Sailwave Export', 'Direct export from Sailwave race management software', 80, FALSE, TRUE),
('windsail', 'Windsail Export', 'Direct export from Windsail system', 80, FALSE, TRUE),
('club_official', 'Club Official', 'Direct from club with authorized representative', 75, FALSE, TRUE),
('club_upload', 'Club Upload', 'Club-uploaded without explicit authorization', 60, FALSE, TRUE),
('external_scrape', 'External Scrape', 'Scraped from external sites', 50, TRUE, TRUE),
('external_manual', 'External Manual', 'Manually transcribed from external source', 40, TRUE, TRUE),
('manual_admin', 'Manual Admin', 'Admin-entered data with no external source', 30, FALSE, FALSE),
('unknown', 'Unknown', 'Legacy data with no source tracking', 0, FALSE, FALSE)
ON CONFLICT (source_type_code) DO NOTHING;

-- Import methods
INSERT INTO import_methods (import_method_code, import_method_name, description, requires_manual_parsing) VALUES
('scrape_auto', 'Automated Scrape', 'Fully automated web scraping', FALSE),
('scrape_manual', 'Manual Scrape', 'Human-assisted web scraping', TRUE),
('pdf_ocr', 'PDF OCR', 'Optical character recognition from PDF', TRUE),
('pdf_table_extract', 'PDF Table Extract', 'Structured table extraction from PDF', FALSE),
('csv_import', 'CSV Import', 'Direct CSV/Excel file import', FALSE),
('sailwave_xml', 'Sailwave XML', 'Native Sailwave .blw/.xml format', FALSE),
('api_sync', 'API Sync', 'Real-time or batch API integration', FALSE),
('manual_entry', 'Manual Entry', 'Human keyboard entry into admin UI', TRUE),
('live_capture', 'Live Capture', 'Real-time capture from SailingSA Live', FALSE),
('migration', 'Migration', 'Data migrated from legacy system', FALSE)
ON CONFLICT (import_method_code) DO NOTHING;

-- Validation statuses
INSERT INTO validation_statuses (status_code, status_name, description, is_terminal, display_order) VALUES
('draft', 'Draft', 'Initial state, not reviewed', FALSE, 10),
('pending_review', 'Pending Review', 'Awaiting human verification', FALSE, 20),
('validated', 'Validated', 'Human-verified correct', FALSE, 30),
('rejected', 'Rejected', 'Rejected as incorrect/duplicate', TRUE, 90),
('conflict', 'Conflict', 'Conflicting with other source', FALSE, 40),
('resolved', 'Resolved', 'Conflict resolved', FALSE, 50),
('superseded', 'Superseded', 'Replaced by newer data', TRUE, 80)
ON CONFLICT (status_code) DO NOTHING;

-- Artifact statuses
INSERT INTO artifact_statuses (status_code, status_name, description) VALUES
('active', 'Active', 'Artifact is valid and in use'),
('archived', 'Archived', 'Artifact retained for audit but no longer primary'),
('corrupted', 'Corrupted', 'File integrity check failed'),
('deleted_source', 'Source Deleted', 'Original URL no longer accessible'),
('pending_retrieval', 'Pending Retrieval', 'Scheduled for download/refresh')
ON CONFLICT (status_code) DO NOTHING;

-- Source scopes (granularity levels)
INSERT INTO source_scopes (scope_code, scope_name, description, scope_level) VALUES
('regatta', 'Regatta', 'Source covers entire regatta (all classes, races, results)', 1),
('class', 'Class', 'Source covers one class/fleet within regatta', 2),
('fleet', 'Fleet', 'Source covers one fleet/division within class', 3),
('race', 'Race', 'Source covers one race only', 4),
('entry', 'Entry', 'Source covers one entry/competitor', 5),
('result', 'Result', 'Source covers one result row', 6),
('boat', 'Boat', 'Source covers boat identity/registration', 7)
ON CONFLICT (scope_code) DO NOTHING;

-- ============================================================================
-- STEP 3: Create helper function for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 4: Create source_artifacts table
-- ============================================================================

CREATE TABLE IF NOT EXISTS source_artifacts (
    artifact_id         BIGSERIAL PRIMARY KEY,
    
    -- Source identification
    source_type         TEXT NOT NULL REFERENCES source_types(source_type_code),
    import_method       TEXT NOT NULL REFERENCES import_methods(import_method_code),
    
    -- Authority & Status
    authority_level     SMALLINT NOT NULL CHECK (authority_level BETWEEN 0 AND 100),
    artifact_status     TEXT NOT NULL DEFAULT 'active' REFERENCES artifact_statuses(status_code),
    
    -- Source locators (IMMUTABLE once set)
    source_url          TEXT,
    
    -- Raw file retention (permanent archive)
    raw_file_path       TEXT,
    raw_file_retained   BOOLEAN NOT NULL DEFAULT FALSE,
    retention_policy    TEXT DEFAULT 'permanent',
    
    -- Working copy (may be updated/regenerated)
    working_file_path   TEXT,
    source_filename     TEXT,
    
    -- Version & Retrieval timestamps
    artifact_version    INTEGER NOT NULL DEFAULT 1,
    first_retrieved_at  TIMESTAMPTZ,
    last_retrieved_at   TIMESTAMPTZ,
    last_verified_at    TIMESTAMPTZ,
    source_modified_at  TIMESTAMPTZ,
    
    -- File metadata
    mime_type           TEXT,
    byte_size           BIGINT,
    checksum_md5        TEXT,
    checksum_sha256     TEXT,
    
    -- Parser info
    parser_name         TEXT,
    parser_version      TEXT,
    parse_timestamp     TIMESTAMPTZ,
    
    -- Manual parsing
    manually_parsed     BOOLEAN NOT NULL DEFAULT FALSE,
    parsed_by           TEXT,
    parse_notes         TEXT,
    
    -- Live session/device provenance (for SailingSA Live)
    live_session_id     TEXT,
    live_device_id      TEXT,
    live_device_type    TEXT,
    live_gps_lat        NUMERIC(9,6),
    live_gps_lng        NUMERIC(9,6),
    live_captured_by_user TEXT,
    
    -- Audit (IMMUTABLE core fields)
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    captured_by         TEXT NOT NULL DEFAULT 'system',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_source_artifacts_source_type ON source_artifacts(source_type);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_status ON source_artifacts(artifact_status);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_checksum ON source_artifacts(checksum_md5) WHERE checksum_md5 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_artifacts_url ON source_artifacts(source_url) WHERE source_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_artifacts_live_session ON source_artifacts(live_session_id) WHERE live_session_id IS NOT NULL;

-- Immutability trigger for source_artifacts
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

-- ============================================================================
-- STEP 5: Create regatta_sources table
-- ============================================================================

CREATE TABLE IF NOT EXISTS regatta_sources (
    regatta_source_id   BIGSERIAL PRIMARY KEY,
    regatta_id          TEXT NOT NULL REFERENCES regattas(regatta_id) ON DELETE CASCADE,
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE RESTRICT,
    
    -- Source scope: what level does this source cover?
    source_scope        TEXT NOT NULL DEFAULT 'regatta' REFERENCES source_scopes(scope_code),
    
    -- Scope-specific references (populated based on source_scope)
    -- For scope='class': which class this source covers
    scope_class_id      INTEGER REFERENCES classes(class_id),
    -- For scope='fleet': which fleet (block) this source covers
    scope_block_id      TEXT,
    -- For scope='race': which race number(s) this source covers
    scope_race_numbers  INTEGER[],
    -- For scope='entry': which entry this source covers
    scope_entry_id      BIGINT REFERENCES entries(entry_id),
    -- For scope='result': which result this source covers
    scope_result_id     BIGINT REFERENCES results(result_id),
    -- For scope='boat': which boat this source covers
    scope_boat_id       BIGINT REFERENCES boats(boat_id),
    
    -- Original vs Secondary (is_original is IMMUTABLE)
    is_original         BOOLEAN NOT NULL DEFAULT FALSE,
    is_primary          BOOLEAN NOT NULL DEFAULT FALSE,
    superseded_by       BIGINT REFERENCES source_artifacts(artifact_id),
    superseded_at       TIMESTAMPTZ,
    
    -- Authority
    authority_level     SMALLINT NOT NULL,
    authority_override  SMALLINT,
    
    -- Validation
    validation_status   TEXT NOT NULL DEFAULT 'draft' REFERENCES validation_statuses(status_code),
    validated_by        TEXT,
    validated_at        TIMESTAMPTZ,
    validation_notes    TEXT,
    
    -- Partial scope fields (for scope='regatta' when not covering everything)
    covers_all_classes  BOOLEAN NOT NULL DEFAULT TRUE,
    class_ids_covered   INTEGER[],
    covers_all_races    BOOLEAN NOT NULL DEFAULT TRUE,
    race_numbers_covered INTEGER[],
    covers_series_only  BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Coverage confidence (0-100, NULL = not assessed)
    coverage_confidence SMALLINT CHECK (coverage_confidence IS NULL OR coverage_confidence BETWEEN 0 AND 100),
    coverage_verified_by TEXT,
    coverage_verified_at TIMESTAMPTZ,
    
    -- Correction/audit fields
    correction_reason   TEXT,
    correction_type     TEXT CHECK (correction_type IS NULL OR correction_type IN (
                            'initial', 'correction', 'amendment', 'protest_result',
                            'redress', 'disqualification', 'reinstatement', 'rescore')),
    correction_reference TEXT,
    
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          TEXT,
    notes               TEXT,
    
    UNIQUE (regatta_id, artifact_id, source_scope, COALESCE(scope_class_id, -1), 
            COALESCE(scope_block_id, ''), COALESCE(scope_entry_id, -1), 
            COALESCE(scope_result_id, -1), COALESCE(scope_boat_id, -1))
);

-- Validate scope references match scope type
CREATE OR REPLACE FUNCTION validate_regatta_source_scope()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate scope-specific fields are populated correctly
    IF NEW.source_scope = 'regatta' THEN
        IF NEW.scope_class_id IS NOT NULL OR NEW.scope_entry_id IS NOT NULL OR 
           NEW.scope_result_id IS NOT NULL OR NEW.scope_boat_id IS NOT NULL THEN
            RAISE EXCEPTION 'Regatta-scope source should not have class/entry/result/boat scope references';
        END IF;
    ELSIF NEW.source_scope = 'class' THEN
        IF NEW.scope_class_id IS NULL THEN
            RAISE EXCEPTION 'Class-scope source requires scope_class_id';
        END IF;
    ELSIF NEW.source_scope = 'fleet' THEN
        IF NEW.scope_block_id IS NULL THEN
            RAISE EXCEPTION 'Fleet-scope source requires scope_block_id';
        END IF;
    ELSIF NEW.source_scope = 'race' THEN
        IF NEW.scope_race_numbers IS NULL OR array_length(NEW.scope_race_numbers, 1) = 0 THEN
            RAISE EXCEPTION 'Race-scope source requires scope_race_numbers';
        END IF;
    ELSIF NEW.source_scope = 'entry' THEN
        IF NEW.scope_entry_id IS NULL THEN
            RAISE EXCEPTION 'Entry-scope source requires scope_entry_id';
        END IF;
    ELSIF NEW.source_scope = 'result' THEN
        IF NEW.scope_result_id IS NULL THEN
            RAISE EXCEPTION 'Result-scope source requires scope_result_id';
        END IF;
    ELSIF NEW.source_scope = 'boat' THEN
        IF NEW.scope_boat_id IS NULL THEN
            RAISE EXCEPTION 'Boat-scope source requires scope_boat_id';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_regatta_source_scope
BEFORE INSERT OR UPDATE ON regatta_sources
FOR EACH ROW EXECUTE FUNCTION validate_regatta_source_scope();

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS uq_regatta_original_source ON regatta_sources(regatta_id, source_scope, 
    COALESCE(scope_class_id, -1), COALESCE(scope_result_id, -1)) WHERE is_original = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_regatta_primary_source ON regatta_sources(regatta_id, source_scope,
    COALESCE(scope_class_id, -1), COALESCE(scope_result_id, -1)) WHERE is_primary = TRUE;
CREATE INDEX IF NOT EXISTS idx_regatta_sources_artifact ON regatta_sources(artifact_id);
CREATE INDEX IF NOT EXISTS idx_regatta_sources_validation ON regatta_sources(validation_status);
CREATE INDEX IF NOT EXISTS idx_regatta_sources_regatta ON regatta_sources(regatta_id);
CREATE INDEX IF NOT EXISTS idx_regatta_sources_scope ON regatta_sources(source_scope);
CREATE INDEX IF NOT EXISTS idx_regatta_sources_class ON regatta_sources(scope_class_id) WHERE scope_class_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_regatta_sources_result ON regatta_sources(scope_result_id) WHERE scope_result_id IS NOT NULL;

-- Prevent changing is_original
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

-- Auto-supersede previous primary when setting new primary
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

-- Deferred constraint: exactly one primary per regatta+scope combination where sources exist
CREATE OR REPLACE FUNCTION check_exactly_one_primary_per_regatta_scope()
RETURNS TRIGGER AS $$
DECLARE
    primary_count INTEGER;
    source_count INTEGER;
    check_regatta_id TEXT;
    check_scope TEXT;
    check_class_id INTEGER;
    check_result_id BIGINT;
BEGIN
    check_regatta_id := COALESCE(NEW.regatta_id, OLD.regatta_id);
    check_scope := COALESCE(NEW.source_scope, OLD.source_scope);
    check_class_id := COALESCE(NEW.scope_class_id, OLD.scope_class_id);
    check_result_id := COALESCE(NEW.scope_result_id, OLD.scope_result_id);
    
    -- Count sources and primaries for this regatta+scope combination
    SELECT COUNT(*), COUNT(*) FILTER (WHERE is_primary = TRUE)
    INTO source_count, primary_count
    FROM regatta_sources
    WHERE regatta_id = check_regatta_id
      AND source_scope = check_scope
      AND COALESCE(scope_class_id, -1) = COALESCE(check_class_id, -1)
      AND COALESCE(scope_result_id, -1) = COALESCE(check_result_id, -1);
    
    IF source_count > 0 AND primary_count != 1 THEN
        RAISE EXCEPTION 'Regatta % scope % has % sources but % primary (must be exactly 1)',
            check_regatta_id, check_scope, source_count, primary_count;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_check_exactly_one_primary_per_regatta_scope
AFTER INSERT OR UPDATE OR DELETE ON regatta_sources
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION check_exactly_one_primary_per_regatta_scope();

-- Auto-update updated_at
CREATE TRIGGER trg_regatta_sources_updated_at
BEFORE UPDATE ON regatta_sources
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 6: Create source_conflicts table
-- ============================================================================

CREATE TABLE IF NOT EXISTS source_conflicts (
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
    authority_a         SMALLINT NOT NULL,
    authority_b         SMALLINT NOT NULL,
    
    -- Conflict details
    conflict_type       TEXT NOT NULL CHECK (conflict_type IN (
                            'value_mismatch', 'duplicate_source', 'authority_tie',
                            'partial_overlap', 'contradictory_correction', 'missing_data',
                            'checksum_mismatch', 'date_conflict', 'identity_conflict')),
    conflict_severity   TEXT NOT NULL DEFAULT 'medium' CHECK (conflict_severity IN (
                            'low', 'medium', 'high', 'critical')),
    field_name          TEXT,
    value_a             TEXT,
    value_b             TEXT,
    value_a_locator     TEXT,
    value_b_locator     TEXT,
    conflict_details    JSONB,
    
    -- Resolution workflow
    resolution_status   TEXT NOT NULL DEFAULT 'pending' CHECK (resolution_status IN (
                            'pending', 'in_review', 'resolved', 'deferred', 'ignored', 'escalated')),
    assigned_to         TEXT,
    assigned_at         TIMESTAMPTZ,
    due_date            DATE,
    priority            SMALLINT DEFAULT 50 CHECK (priority BETWEEN 0 AND 100),
    
    -- Resolution outcome
    resolved_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    resolution_action   TEXT CHECK (resolution_action IS NULL OR resolution_action IN (
                            'accept_a', 'accept_b', 'accept_higher_authority',
                            'merge', 'manual_value', 'create_correction',
                            'defer', 'ignore', 'escalate', 'split')),
    resolved_value      TEXT,
    resolution_details  JSONB,
    
    -- Resolution audit
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    resolution_reason   TEXT NOT NULL DEFAULT '',
    resolution_reference TEXT,
    resolution_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    
    -- Review/escalation
    reviewed_by         TEXT,
    reviewed_at         TIMESTAMPTZ,
    review_notes        TEXT,
    escalated_to        TEXT,
    escalated_at        TIMESTAMPTZ,
    escalation_reason   TEXT,
    
    -- History tracking
    previous_resolution_id BIGINT REFERENCES source_conflicts(conflict_id),
    reopen_count        INTEGER NOT NULL DEFAULT 0,
    last_reopened_at    TIMESTAMPTZ,
    last_reopened_by    TEXT,
    last_reopened_reason TEXT,
    
    -- Detection audit
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detected_by         TEXT NOT NULL DEFAULT 'system',
    detection_method    TEXT DEFAULT 'auto' CHECK (detection_method IN (
                            'auto', 'manual_report', 'audit_scan', 'import_check')),
    detection_context   JSONB,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_conflict_has_entity CHECK (
        regatta_id IS NOT NULL OR result_id IS NOT NULL OR 
        entry_id IS NOT NULL OR boat_id IS NOT NULL
    )
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_source_conflicts_pending ON source_conflicts(resolution_status) 
    WHERE resolution_status IN ('pending', 'in_review');
CREATE INDEX IF NOT EXISTS idx_source_conflicts_regatta ON source_conflicts(regatta_id) WHERE regatta_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_conflicts_result ON source_conflicts(result_id) WHERE result_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_conflicts_assigned ON source_conflicts(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_conflicts_priority ON source_conflicts(priority DESC, created_at) 
    WHERE resolution_status = 'pending';
CREATE INDEX IF NOT EXISTS idx_source_conflicts_artifact_a ON source_conflicts(artifact_a_id);
CREATE INDEX IF NOT EXISTS idx_source_conflicts_artifact_b ON source_conflicts(artifact_b_id);

CREATE TRIGGER trg_source_conflicts_updated_at
BEFORE UPDATE ON source_conflicts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 7: Create result_sources table
-- ============================================================================

CREATE TABLE IF NOT EXISTS result_sources (
    result_source_id    BIGSERIAL PRIMARY KEY,
    result_id           BIGINT NOT NULL REFERENCES results(result_id) ON DELETE CASCADE,
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE RESTRICT,
    
    -- Original vs Secondary
    is_original         BOOLEAN NOT NULL DEFAULT FALSE,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_by       BIGINT REFERENCES source_artifacts(artifact_id),
    superseded_at       TIMESTAMPTZ,
    
    -- Source locator within artifact
    source_locator      TEXT,
    
    -- Partial scope
    fields_from_source  TEXT[],
    race_numbers_from_source INTEGER[],
    
    -- Correction/audit fields
    correction_reason   TEXT,
    correction_type     TEXT CHECK (correction_type IS NULL OR correction_type IN (
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

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS uq_result_original_source ON result_sources(result_id) WHERE is_original = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_result_current_source ON result_sources(result_id) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_result_sources_artifact ON result_sources(artifact_id);
CREATE INDEX IF NOT EXISTS idx_result_sources_result ON result_sources(result_id);

CREATE TRIGGER trg_prevent_result_original_flag_change
BEFORE UPDATE ON result_sources
FOR EACH ROW EXECUTE FUNCTION prevent_original_flag_change();

-- Auto-supersede previous current when setting new current
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

-- Deferred constraint: exactly one current per result where sources exist
CREATE OR REPLACE FUNCTION check_exactly_one_current_per_result()
RETURNS TRIGGER AS $$
DECLARE
    current_count INTEGER;
    source_count INTEGER;
    check_result_id BIGINT;
BEGIN
    check_result_id := COALESCE(NEW.result_id, OLD.result_id);
    
    SELECT COUNT(*), COUNT(*) FILTER (WHERE is_current = TRUE)
    INTO source_count, current_count
    FROM result_sources
    WHERE result_id = check_result_id;
    
    IF source_count > 0 AND current_count != 1 THEN
        RAISE EXCEPTION 'Result % has % sources but % current (must be exactly 1)',
            check_result_id, source_count, current_count;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_check_exactly_one_current_per_result
AFTER INSERT OR UPDATE OR DELETE ON result_sources
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION check_exactly_one_current_per_result();

CREATE TRIGGER trg_result_sources_updated_at
BEFORE UPDATE ON result_sources
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 8: Create result_source_mappings table (cell-level provenance)
-- ============================================================================

CREATE TABLE IF NOT EXISTS result_source_mappings (
    mapping_id          BIGSERIAL PRIMARY KEY,
    result_id           BIGINT NOT NULL REFERENCES results(result_id) ON DELETE CASCADE,
    field_name          TEXT NOT NULL,
    artifact_id         BIGINT NOT NULL REFERENCES source_artifacts(artifact_id) ON DELETE RESTRICT,
    source_locator      TEXT,
    raw_value           TEXT,
    normalized_value    TEXT,
    is_original         BOOLEAN NOT NULL DEFAULT TRUE,
    supersedes_mapping_id BIGINT REFERENCES result_source_mappings(mapping_id),
    correction_reason   TEXT,
    correction_type     TEXT,
    extraction_confidence SMALLINT CHECK (extraction_confidence IS NULL OR extraction_confidence BETWEEN 0 AND 100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_result_source_mappings_result ON result_source_mappings(result_id);
CREATE INDEX IF NOT EXISTS idx_result_source_mappings_artifact ON result_source_mappings(artifact_id);
CREATE INDEX IF NOT EXISTS idx_result_source_mappings_field ON result_source_mappings(result_id, field_name);

-- ============================================================================
-- STEP 9: Add columns to existing tables
-- ============================================================================

-- Add to regattas
ALTER TABLE regattas
    ADD COLUMN IF NOT EXISTS original_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS primary_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS provenance_status TEXT DEFAULT 'migrated',
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;

-- Add to results
ALTER TABLE results
    ADD COLUMN IF NOT EXISTS original_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS current_artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS row_validation_status TEXT DEFAULT 'validated',
    ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN NOT NULL DEFAULT FALSE;

-- Add to entries
ALTER TABLE entries
    ADD COLUMN IF NOT EXISTS original_artifact_id BIGINT REFERENCES source_artifacts(artifact_id);

-- Add to regatta_blocks
ALTER TABLE regatta_blocks
    ADD COLUMN IF NOT EXISTS artifact_id BIGINT REFERENCES source_artifacts(artifact_id);

-- Add to results_staging (if columns don't exist from runtime additions)
DO $$
BEGIN
    ALTER TABLE results_staging ADD COLUMN IF NOT EXISTS source_type TEXT;
    ALTER TABLE results_staging ADD COLUMN IF NOT EXISTS import_method TEXT;
    ALTER TABLE results_staging ADD COLUMN IF NOT EXISTS artifact_id BIGINT;
    ALTER TABLE results_staging ADD COLUMN IF NOT EXISTS manually_parsed BOOLEAN DEFAULT FALSE;
    ALTER TABLE results_staging ADD COLUMN IF NOT EXISTS source_locator TEXT;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Some results_staging columns may already exist: %', SQLERRM;
END $$;

-- ============================================================================
-- STEP 10: Migrate existing source data (CONSERVATIVE - unknown stays NULL)
-- ============================================================================

-- PRINCIPLE: Unknown provenance stays NULL/unlinked. No placeholders.
-- PRINCIPLE: Results only linked if regatta source coverage is verified.
-- PRINCIPLE: Explicit confidence/status based on source quality.

-- 10a. Create artifacts ONLY for regattas with valid, identifiable source_url
INSERT INTO source_artifacts (
    source_type,
    import_method,
    authority_level,
    artifact_status,
    source_url,
    working_file_path,
    first_retrieved_at,
    captured_at,
    captured_by,
    parse_notes
)
SELECT DISTINCT ON (r.source_url)
    CASE 
        WHEN r.source_url LIKE '%sailing.org.za%' THEN 'sas_pdf'
        ELSE 'external_scrape'  -- Only external with URL, not 'unknown'
    END,
    CASE 
        WHEN r.source_url LIKE '%sailing.org.za%' THEN 'pdf_table_extract'
        ELSE 'scrape_auto'
    END,
    CASE 
        WHEN r.source_url LIKE '%sailing.org.za%' THEN 90
        ELSE 50  -- External sources get medium authority
    END,
    'active',
    r.source_url,
    r.local_file_path,
    r.created_at,
    COALESCE(r.created_at, NOW()),
    'migration_210',
    'Migrated from regattas.source_url - coverage assumed full but not verified'
FROM regattas r
WHERE r.source_url IS NOT NULL
  AND r.source_url != ''
  AND LENGTH(TRIM(r.source_url)) > 10  -- Must be a real URL
  AND NOT EXISTS (
      SELECT 1 FROM source_artifacts sa WHERE sa.source_url = r.source_url
  );

-- 10b. Create regatta_sources links with explicit migration status
-- Coverage is ASSUMED but flagged for verification
-- source_scope='regatta' indicates this source claims to cover the entire regatta
INSERT INTO regatta_sources (
    regatta_id,
    artifact_id,
    source_scope,
    is_original,
    is_primary,
    authority_level,
    validation_status,
    correction_type,
    covers_all_classes,
    covers_all_races,
    coverage_confidence,
    created_by,
    notes
)
SELECT 
    r.regatta_id,
    sa.artifact_id,
    'regatta',  -- Explicit scope: entire regatta
    TRUE,   -- is_original
    TRUE,   -- is_primary
    sa.authority_level,
    'pending_review',  -- NOT 'validated' - needs verification
    'initial',
    TRUE,   -- ASSUMED full coverage (unverified)
    TRUE,   -- ASSUMED full coverage (unverified)
    NULL,   -- coverage_confidence=NULL means not assessed
    'migration_210',
    'Migrated from regattas.source_url - scope=regatta assumed, coverage unverified'
FROM regattas r
JOIN source_artifacts sa ON sa.source_url = r.source_url
WHERE r.source_url IS NOT NULL
  AND r.source_url != ''
  AND NOT EXISTS (
      SELECT 1 FROM regatta_sources rs WHERE rs.regatta_id = r.regatta_id AND rs.artifact_id = sa.artifact_id
  );

-- 10c. Update regattas with artifact references (only those with valid sources)
UPDATE regattas r
SET original_artifact_id = rs.artifact_id,
    primary_artifact_id = rs.artifact_id,
    provenance_status = 'migrated_pending_verification'
FROM regatta_sources rs
WHERE rs.regatta_id = r.regatta_id 
  AND rs.is_original = TRUE
  AND r.original_artifact_id IS NULL;

-- 10d. Regattas WITHOUT source_url: mark status but DO NOT create placeholder
-- These stay NULL/unlinked until source is identified
UPDATE regattas
SET provenance_status = 'unknown_source'
WHERE (source_url IS NULL OR source_url = '' OR LENGTH(TRIM(source_url)) <= 10)
  AND provenance_status IS NULL;

-- 10e. DO NOT auto-link results to regatta artifacts
-- Results will only be linked when:
--   1. Regatta source has covers_all_classes=TRUE AND covers_all_races=TRUE AND validation_status='validated', OR
--   2. Result's class_id is in regatta_sources.class_ids_covered, OR
--   3. Manual verification confirms coverage
-- For now, results stay unlinked (NULL artifact references)

-- 10f. Update results to indicate migration status (no artifact link yet)
UPDATE results r
SET row_validation_status = 
    CASE 
        WHEN reg.provenance_status = 'migrated_pending_verification' THEN 'pending_review'
        WHEN reg.provenance_status = 'unknown_source' THEN 'draft'
        ELSE 'draft'
    END
FROM regattas reg
WHERE reg.regatta_id = r.regatta_id
  AND r.row_validation_status IS NULL;

-- ============================================================================
-- STEP 10g: Function to link results ONLY when coverage is verified
-- Call this after manual verification of regatta_sources
-- ============================================================================
CREATE OR REPLACE FUNCTION link_results_to_verified_regatta_source(
    p_regatta_id TEXT
) RETURNS TABLE(linked_count INTEGER, skipped_count INTEGER) AS $$
DECLARE
    v_artifact_id BIGINT;
    v_covers_all_classes BOOLEAN;
    v_covers_all_races BOOLEAN;
    v_class_ids INTEGER[];
    v_linked INTEGER := 0;
    v_skipped INTEGER := 0;
BEGIN
    -- Get the validated primary source for this regatta
    SELECT rs.artifact_id, rs.covers_all_classes, rs.covers_all_races, rs.class_ids_covered
    INTO v_artifact_id, v_covers_all_classes, v_covers_all_races, v_class_ids
    FROM regatta_sources rs
    WHERE rs.regatta_id = p_regatta_id
      AND rs.is_primary = TRUE
      AND rs.validation_status = 'validated';
    
    IF v_artifact_id IS NULL THEN
        RAISE EXCEPTION 'No validated primary source for regatta %', p_regatta_id;
    END IF;
    
    -- Link results based on coverage
    IF v_covers_all_classes AND v_covers_all_races THEN
        -- Full coverage: link all results
        INSERT INTO result_sources (result_id, artifact_id, is_original, is_current, correction_type, created_by, notes)
        SELECT r.result_id, v_artifact_id, TRUE, TRUE, 'initial', 'verified_link',
               'Linked after regatta source validation - full coverage'
        FROM results r
        WHERE r.regatta_id = p_regatta_id
          AND NOT EXISTS (SELECT 1 FROM result_sources rs WHERE rs.result_id = r.result_id);
        
        GET DIAGNOSTICS v_linked = ROW_COUNT;
        
        UPDATE results
        SET original_artifact_id = v_artifact_id,
            current_artifact_id = v_artifact_id,
            row_validation_status = 'validated'
        WHERE regatta_id = p_regatta_id
          AND original_artifact_id IS NULL;
    ELSE
        -- Partial coverage: only link results in covered classes
        INSERT INTO result_sources (result_id, artifact_id, is_original, is_current, correction_type, created_by, notes)
        SELECT r.result_id, v_artifact_id, TRUE, TRUE, 'initial', 'verified_link',
               'Linked after regatta source validation - partial coverage (class matched)'
        FROM results r
        WHERE r.regatta_id = p_regatta_id
          AND r.class_id = ANY(v_class_ids)
          AND NOT EXISTS (SELECT 1 FROM result_sources rs WHERE rs.result_id = r.result_id);
        
        GET DIAGNOSTICS v_linked = ROW_COUNT;
        
        UPDATE results
        SET original_artifact_id = v_artifact_id,
            current_artifact_id = v_artifact_id,
            row_validation_status = 'validated'
        WHERE regatta_id = p_regatta_id
          AND class_id = ANY(v_class_ids)
          AND original_artifact_id IS NULL;
        
        -- Count skipped (not in coverage)
        SELECT COUNT(*) INTO v_skipped
        FROM results r
        WHERE r.regatta_id = p_regatta_id
          AND (r.class_id IS NULL OR NOT (r.class_id = ANY(v_class_ids)))
          AND r.original_artifact_id IS NULL;
    END IF;
    
    RETURN QUERY SELECT v_linked, v_skipped;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION link_results_to_verified_regatta_source IS 
'Links results to regatta source ONLY after validation_status=validated. 
Respects partial coverage (class_ids_covered). Call after manual verification.';

-- ============================================================================
-- STEP 11: Migrate events source data (CONSERVATIVE)
-- ============================================================================

-- Events have their own source tracking (source, source_event_id, source_url)
-- These are CALENDAR events, not results sources
-- Only create artifacts for events with valid URLs

-- Add event_artifact_id to events if not exists
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS artifact_id BIGINT REFERENCES source_artifacts(artifact_id),
    ADD COLUMN IF NOT EXISTS provenance_status TEXT;

-- Create artifacts ONLY for events with valid, identifiable source_url
-- Note: events.source_url is the EVENT LISTING page, not results PDF
INSERT INTO source_artifacts (
    source_type,
    import_method,
    authority_level,
    artifact_status,
    source_url,
    first_retrieved_at,
    captured_at,
    captured_by,
    parse_notes
)
SELECT DISTINCT ON (e.source_url)
    CASE 
        WHEN e.source = 'sas' THEN 'sas_pdf'
        ELSE 'external_scrape'
    END,
    'scrape_auto',
    50,  -- Calendar events have medium authority (not results)
    'active',
    e.source_url,
    e.created_at,
    COALESCE(e.created_at, NOW()),
    'migration_210_events',
    'Event calendar source - NOT results data'
FROM events e
WHERE e.source_url IS NOT NULL
  AND e.source_url != ''
  AND LENGTH(TRIM(e.source_url)) > 10
  AND NOT EXISTS (
      SELECT 1 FROM source_artifacts sa WHERE sa.source_url = e.source_url
  );

-- Link events to their artifacts (those with valid URLs only)
UPDATE events e
SET artifact_id = sa.artifact_id,
    provenance_status = 'migrated'
FROM source_artifacts sa
WHERE sa.source_url = e.source_url
  AND e.source_url IS NOT NULL
  AND e.source_url != ''
  AND e.artifact_id IS NULL;

-- Mark events without valid source_url
UPDATE events
SET provenance_status = 'unknown_source'
WHERE (source_url IS NULL OR source_url = '' OR LENGTH(TRIM(source_url)) <= 10)
  AND provenance_status IS NULL;

-- ============================================================================
-- STEP 12: Migrate results_staging source data (CONSERVATIVE)
-- ============================================================================

-- results_staging has source_url for SAS PDFs - these ARE results sources
-- Create artifacts but mark as pending (not yet promoted to results)

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'results_staging' AND column_name = 'source_url') THEN
        
        -- Create artifacts for staging rows with valid source_url
        INSERT INTO source_artifacts (
            source_type,
            import_method,
            authority_level,
            artifact_status,
            source_url,
            working_file_path,
            captured_by,
            parse_notes
        )
        SELECT DISTINCT ON (rs.source_url)
            CASE 
                WHEN rs.source_site = 'SAS' OR rs.source_url LIKE '%sailing.org.za%' THEN 'sas_pdf'
                ELSE 'external_scrape'
            END,
            'pdf_table_extract',
            CASE 
                WHEN rs.source_site = 'SAS' OR rs.source_url LIKE '%sailing.org.za%' THEN 90
                ELSE 50
            END,
            'pending_retrieval',  -- Staging = not yet processed
            rs.source_url,
            rs.pdf_local_path,
            'migration_210_staging',
            'Staging source - pending promotion to results'
        FROM results_staging rs
        WHERE rs.source_url IS NOT NULL
          AND rs.source_url != ''
          AND LENGTH(TRIM(rs.source_url)) > 10
          AND NOT EXISTS (
              SELECT 1 FROM source_artifacts sa WHERE sa.source_url = rs.source_url
          );
        
        -- Link staging to artifacts
        UPDATE results_staging rs
        SET artifact_id = sa.artifact_id,
            source_type = CASE 
                WHEN rs.source_site = 'SAS' OR rs.source_url LIKE '%sailing.org.za%' THEN 'sas_pdf'
                ELSE 'external_scrape'
            END,
            import_method = 'pdf_table_extract'
        FROM source_artifacts sa
        WHERE sa.source_url = rs.source_url
          AND rs.source_url IS NOT NULL
          AND rs.source_url != ''
          AND rs.artifact_id IS NULL;
    END IF;
END $$;

-- ============================================================================
-- COMMIT TRANSACTION
-- ============================================================================
COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (run after migration)
-- ============================================================================
/*
-- Check tables created
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('source_types', 'import_methods', 'validation_statuses', 'artifact_statuses',
                   'source_scopes', 'source_artifacts', 'regatta_sources', 'result_sources', 
                   'result_source_mappings', 'source_conflicts');

-- Check source scopes
SELECT * FROM source_scopes ORDER BY scope_level;

-- Check lookup data
SELECT * FROM source_types ORDER BY authority_level DESC;
SELECT * FROM import_methods;
SELECT * FROM validation_statuses ORDER BY display_order;
SELECT * FROM artifact_statuses;

-- Check artifact counts
SELECT source_type, COUNT(*) FROM source_artifacts GROUP BY source_type;

-- Check regatta linkage
SELECT 
    (SELECT COUNT(*) FROM regattas) AS total_regattas,
    (SELECT COUNT(*) FROM regattas WHERE original_artifact_id IS NOT NULL) AS linked_regattas,
    (SELECT COUNT(*) FROM regatta_sources) AS regatta_source_links,
    (SELECT COUNT(*) FROM regatta_sources WHERE is_original = TRUE) AS original_sources,
    (SELECT COUNT(*) FROM regatta_sources WHERE is_primary = TRUE) AS primary_sources;

-- Check result linkage
SELECT 
    (SELECT COUNT(*) FROM results) AS total_results,
    (SELECT COUNT(*) FROM results WHERE original_artifact_id IS NOT NULL) AS linked_results,
    (SELECT COUNT(*) FROM result_sources) AS result_source_links;

-- Verify exactly-one constraints
SELECT regatta_id, COUNT(*) FILTER (WHERE is_primary) AS primary_count
FROM regatta_sources
GROUP BY regatta_id
HAVING COUNT(*) FILTER (WHERE is_primary) != 1;
-- Should return 0 rows

-- Check triggers exist
SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_%' AND tgname LIKE '%source%';
*/

-- ============================================================================
-- ROLLBACK PROCEDURE (execute in order if rollback needed)
-- ============================================================================
/*
BEGIN;

-- ROLLBACK STEP 1: Remove columns from existing tables
ALTER TABLE regattas DROP COLUMN IF EXISTS original_artifact_id;
ALTER TABLE regattas DROP COLUMN IF EXISTS primary_artifact_id;
ALTER TABLE regattas DROP COLUMN IF EXISTS provenance_status;
ALTER TABLE regattas DROP COLUMN IF EXISTS manually_parsed;

ALTER TABLE results DROP COLUMN IF EXISTS original_artifact_id;
ALTER TABLE results DROP COLUMN IF EXISTS current_artifact_id;
ALTER TABLE results DROP COLUMN IF EXISTS row_validation_status;
ALTER TABLE results DROP COLUMN IF EXISTS manually_parsed;

ALTER TABLE entries DROP COLUMN IF EXISTS original_artifact_id;
ALTER TABLE regatta_blocks DROP COLUMN IF EXISTS artifact_id;
ALTER TABLE events DROP COLUMN IF EXISTS artifact_id;
ALTER TABLE events DROP COLUMN IF EXISTS provenance_status;

ALTER TABLE results_staging DROP COLUMN IF EXISTS source_type;
ALTER TABLE results_staging DROP COLUMN IF EXISTS import_method;
ALTER TABLE results_staging DROP COLUMN IF EXISTS artifact_id;
ALTER TABLE results_staging DROP COLUMN IF EXISTS manually_parsed;
ALTER TABLE results_staging DROP COLUMN IF EXISTS source_locator;

-- ROLLBACK STEP 2: Drop triggers
DROP TRIGGER IF EXISTS trg_check_exactly_one_current_per_result ON result_sources;
DROP TRIGGER IF EXISTS trg_enforce_single_current_result_source ON result_sources;
DROP TRIGGER IF EXISTS trg_prevent_result_original_flag_change ON result_sources;
DROP TRIGGER IF EXISTS trg_result_sources_updated_at ON result_sources;

DROP TRIGGER IF EXISTS trg_source_conflicts_updated_at ON source_conflicts;

DROP TRIGGER IF EXISTS trg_check_exactly_one_primary_per_regatta_scope ON regatta_sources;
DROP TRIGGER IF EXISTS trg_validate_regatta_source_scope ON regatta_sources;
DROP TRIGGER IF EXISTS trg_enforce_single_primary_regatta_source ON regatta_sources;
DROP TRIGGER IF EXISTS trg_prevent_regatta_original_flag_change ON regatta_sources;
DROP TRIGGER IF EXISTS trg_regatta_sources_updated_at ON regatta_sources;

DROP TRIGGER IF EXISTS trg_prevent_artifact_immutable_modification ON source_artifacts;

-- ROLLBACK STEP 3: Drop functions
DROP FUNCTION IF EXISTS link_results_to_verified_regatta_source(TEXT);
DROP FUNCTION IF EXISTS check_exactly_one_current_per_result();
DROP FUNCTION IF EXISTS enforce_single_current_result_source();
DROP FUNCTION IF EXISTS check_exactly_one_primary_per_regatta_scope();
DROP FUNCTION IF EXISTS validate_regatta_source_scope();
DROP FUNCTION IF EXISTS enforce_single_primary_regatta_source();
DROP FUNCTION IF EXISTS prevent_original_flag_change();
DROP FUNCTION IF EXISTS prevent_artifact_immutable_modification();
DROP FUNCTION IF EXISTS update_updated_at_column();

-- ROLLBACK STEP 4: Drop tables (order matters due to FKs)
DROP TABLE IF EXISTS result_source_mappings CASCADE;
DROP TABLE IF EXISTS result_sources CASCADE;
DROP TABLE IF EXISTS source_conflicts CASCADE;
DROP TABLE IF EXISTS regatta_sources CASCADE;
DROP TABLE IF EXISTS source_artifacts CASCADE;
DROP TABLE IF EXISTS source_scopes CASCADE;
DROP TABLE IF EXISTS artifact_statuses CASCADE;
DROP TABLE IF EXISTS validation_statuses CASCADE;
DROP TABLE IF EXISTS import_methods CASCADE;
DROP TABLE IF EXISTS source_types CASCADE;

COMMIT;

-- Verify rollback
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('source_types', 'import_methods', 'validation_statuses', 'artifact_statuses',
                   'source_artifacts', 'regatta_sources', 'result_sources', 
                   'result_source_mappings', 'source_conflicts');
-- Should return 0 rows
*/
