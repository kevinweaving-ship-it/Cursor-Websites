-- ============================================================================
-- BOAT REGISTER SCHEMA MIGRATION
-- Version: 200
-- Date: 2026-07-27
-- Status: Schema only - no backfill, no API changes
-- ============================================================================

-- ============================================================================
-- PRE-MIGRATION DEPENDENCY AUDIT (run these queries first, review results)
-- ============================================================================
/*
-- Foreign keys referencing boats:
SELECT tc.table_name, kcu.column_name, tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'boats';

-- Views referencing boats:
SELECT viewname, definition FROM pg_views WHERE definition ILIKE '%boats%';

-- Triggers on boats:
SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE tgrelid = 'boats'::regclass;

-- Sequences owned by boats:
SELECT s.relname AS sequence_name
FROM pg_class s
JOIN pg_depend d ON d.objid = s.oid
JOIN pg_class t ON d.refobjid = t.oid
WHERE s.relkind = 'S' AND t.relname = 'boats';

-- Indexes on boats:
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'boats';

-- Functions referencing boats:
SELECT proname FROM pg_proc WHERE prosrc ILIKE '%[^_]boats[^_]%';
*/

-- ============================================================================
-- BEGIN TRANSACTION
-- ============================================================================
BEGIN;

-- ============================================================================
-- STEP 1: Rename existing boats table to boats_legacy
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'boats') THEN
        -- Drop triggers first
        DROP TRIGGER IF EXISTS trg_boats_updated_at ON boats;
        
        -- Drop constraints (which will drop associated indexes)
        ALTER TABLE public.boats DROP CONSTRAINT IF EXISTS boats_sail_number_class_name_key;
        
        -- Drop remaining indexes
        DROP INDEX IF EXISTS idx_boats_sail_number;
        DROP INDEX IF EXISTS idx_boats_class_name;
        
        -- Rename table
        ALTER TABLE public.boats RENAME TO boats_legacy;
        
        -- Rename sequence if exists
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'boats_boat_id_seq') THEN
            ALTER SEQUENCE boats_boat_id_seq RENAME TO boats_legacy_boat_id_seq;
        END IF;
        
        RAISE NOTICE 'Renamed boats to boats_legacy';
    ELSE
        RAISE NOTICE 'No existing boats table found';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Create class_hull_families (no dependencies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.class_hull_families (
    family_id           SERIAL PRIMARY KEY,
    family_name         TEXT NOT NULL UNIQUE,
    description         TEXT,
    share_sail_identity BOOLEAN NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE public.class_hull_families IS 'Hull families where sail numbers may be shared across class variants (e.g., ILCA rigs)';
COMMENT ON COLUMN public.class_hull_families.share_sail_identity IS 'TRUE = same sail number across family classes represents same physical boat';

-- ============================================================================
-- STEP 3: Create class_family_members (depends on class_hull_families, classes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.class_family_members (
    family_id           INTEGER NOT NULL REFERENCES class_hull_families(family_id) ON DELETE CASCADE,
    class_id            INTEGER NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    is_rig_variant      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (family_id, class_id)
);

COMMENT ON TABLE public.class_family_members IS 'Maps classes to hull families';
COMMENT ON COLUMN public.class_family_members.is_rig_variant IS 'TRUE = this class is a rig variant of the family hull (e.g., ILCA 6 vs ILCA 7)';

-- ============================================================================
-- STEP 4: Create hull_models (depends on class_hull_families)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.hull_models (
    hull_model_id       SERIAL PRIMARY KEY,
    model_name          TEXT NOT NULL,
    manufacturer        TEXT,
    hull_family_id      INTEGER REFERENCES class_hull_families(family_id) ON DELETE SET NULL,
    year_introduced     INTEGER,
    year_discontinued   INTEGER,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.hull_models IS 'Physical hull model definitions';

-- ============================================================================
-- STEP 5: Create boats (depends on hull_models)
-- ============================================================================
CREATE TABLE public.boats (
    boat_id             BIGSERIAL PRIMARY KEY,
    hull_model_id       INTEGER REFERENCES hull_models(hull_model_id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    created_source      TEXT NOT NULL DEFAULT 'migration' 
                        CHECK (created_source IN ('result', 'entry', 'manual', 'import', 'migration')),
    created_evidence    JSONB,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          TEXT,
    notes               TEXT
);

COMMENT ON TABLE public.boats IS 'Permanent boat identity register. boat_id is the only stable identity.';

-- ============================================================================
-- STEP 6: Create boat_identifiers (depends on boats, classes, regattas)
-- ============================================================================
CREATE TABLE public.boat_identifiers (
    identifier_id       BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    identifier_type     TEXT NOT NULL 
                        CHECK (identifier_type IN (
                            'sail_number', 'bow_no', 'jib_no', 'hull_no',
                            'hin', 'measurement_id', 'builder_plate', 'alias')),
    identifier_value    TEXT NOT NULL,
    country_code        TEXT,
    class_id            INTEGER REFERENCES classes(class_id) ON DELETE SET NULL,
    valid_from          DATE NOT NULL,
    valid_to            DATE,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    source_type         TEXT NOT NULL 
                        CHECK (source_type IN (
                            'result', 'entry', 'manual', 'import',
                            'measurement_cert', 'class_association', 'external')),
    source_regatta_id   TEXT REFERENCES regattas(regatta_id) ON DELETE SET NULL,
    source_url          TEXT,
    source_document     TEXT,
    evidence            JSONB,
    confidence          SMALLINT DEFAULT 50 CHECK (confidence BETWEEN 0 AND 100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          TEXT,
    notes               TEXT,
    
    CONSTRAINT chk_valid_date_range CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

COMMENT ON TABLE public.boat_identifiers IS 'Sail numbers, hull numbers, and other identifiers with validity periods';
COMMENT ON COLUMN public.boat_identifiers.country_code IS 'ISO country code from sail number prefix (e.g., RSA, GBR)';
COMMENT ON COLUMN public.boat_identifiers.is_current IS 'TRUE = this identifier is currently active for this boat';

-- Prevent multiple current sail identifiers per boat+class
CREATE UNIQUE INDEX uq_boat_current_sail_per_class
ON boat_identifiers (boat_id, class_id)
WHERE identifier_type = 'sail_number' AND is_current = TRUE;

-- ============================================================================
-- STEP 7: Create family-aware overlap trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION check_identifier_overlap()
RETURNS TRIGGER AS $$
DECLARE
    family_class_ids INTEGER[];
    shares_identity BOOLEAN;
BEGIN
    -- Get family info for this class
    SELECT 
        ARRAY_AGG(DISTINCT cfm2.class_id),
        COALESCE(bool_or(chf.share_sail_identity), FALSE)
    INTO family_class_ids, shares_identity
    FROM class_family_members cfm
    JOIN class_hull_families chf ON chf.family_id = cfm.family_id
    JOIN class_family_members cfm2 ON cfm2.family_id = cfm.family_id
    WHERE cfm.class_id = NEW.class_id;

    -- If no family found, single-class scope
    IF family_class_ids IS NULL THEN
        family_class_ids := ARRAY[NEW.class_id];
        shares_identity := FALSE;
    END IF;

    -- Check for overlapping validity periods with DIFFERENT boats
    IF EXISTS (
        SELECT 1 FROM boat_identifiers bi
        WHERE bi.identifier_id != COALESCE(NEW.identifier_id, -1)
          AND bi.identifier_type = NEW.identifier_type
          AND bi.identifier_value = NEW.identifier_value
          AND bi.country_code IS NOT DISTINCT FROM NEW.country_code
          AND bi.boat_id != NEW.boat_id
          AND (
              CASE WHEN shares_identity THEN
                  -- Shared family: conflict if ANY family class has same sail for different boat
                  bi.class_id = ANY(family_class_ids)
              ELSE
                  -- Non-shared: conflict only if SAME class has same sail for different boat
                  bi.class_id = NEW.class_id
              END
          )
          AND daterange(bi.valid_from, bi.valid_to, '[]') &&
              daterange(NEW.valid_from, NEW.valid_to, '[]')
    ) THEN
        RAISE EXCEPTION 'Overlapping identifier: type=%, value=%, country=%, class_id=%, conflicts with different boat in %',
            NEW.identifier_type, 
            NEW.identifier_value, 
            NEW.country_code,
            NEW.class_id,
            CASE WHEN shares_identity THEN 'shared family' ELSE 'same class' END;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_identifier_overlap
BEFORE INSERT OR UPDATE ON boat_identifiers
FOR EACH ROW EXECUTE FUNCTION check_identifier_overlap();

-- ============================================================================
-- STEP 8: Create boat_names (depends on boats, regattas)
-- ============================================================================
CREATE TABLE public.boat_names (
    name_id             BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    boat_name           TEXT NOT NULL,
    first_seen_date     DATE NOT NULL,
    last_seen_date      DATE NOT NULL,
    source_type         TEXT NOT NULL 
                        CHECK (source_type IN ('result', 'entry', 'manual', 'import', 'external')),
    source_regatta_id   TEXT REFERENCES regattas(regatta_id) ON DELETE SET NULL,
    source_url          TEXT,
    evidence            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    notes               TEXT,
    
    CONSTRAINT chk_name_date_range CHECK (last_seen_date >= first_seen_date)
);

COMMENT ON TABLE public.boat_names IS 'Boat name history - boats can change names over time';

-- ============================================================================
-- STEP 9: Create boat_associations (depends on boats, clubs, regattas)
-- ============================================================================
CREATE TABLE public.boat_associations (
    association_id      BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    sa_sailing_id       INTEGER,
    person_name         TEXT,
    club_id             INTEGER REFERENCES clubs(club_id) ON DELETE SET NULL,
    association_type    TEXT NOT NULL 
                        CHECK (association_type IN (
                            'primary_helm', 'registered_owner', 'club_boat',
                            'charter', 'borrowed', 'seller', 'buyer')),
    valid_from          DATE NOT NULL,
    valid_to            DATE,
    is_current          BOOLEAN NOT NULL DEFAULT FALSE,
    source_type         TEXT NOT NULL 
                        CHECK (source_type IN (
                            'manual', 'sale_record', 'registration',
                            'measurement_cert', 'external')),
    source_regatta_id   TEXT REFERENCES regattas(regatta_id) ON DELETE SET NULL,
    source_url          TEXT,
    source_document     TEXT,
    evidence            JSONB,
    confidence          SMALLINT DEFAULT 50 CHECK (confidence BETWEEN 0 AND 100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT 'system',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          TEXT,
    notes               TEXT
);

COMMENT ON TABLE public.boat_associations IS 'Sailor/owner associations with boats - requires explicit evidence for ownership claims';
COMMENT ON COLUMN public.boat_associations.association_type IS 'primary_helm is derived; registered_owner requires evidence';

-- ============================================================================
-- STEP 10: Create boat_match_log (depends on boats, results, entries)
-- ============================================================================
CREATE TABLE public.boat_match_log (
    log_id              BIGSERIAL PRIMARY KEY,
    result_id           BIGINT REFERENCES results(result_id) ON DELETE SET NULL,
    entry_id            BIGINT REFERENCES entries(entry_id) ON DELETE SET NULL,
    boat_id             BIGINT REFERENCES boats(boat_id) ON DELETE SET NULL,
    match_type          TEXT NOT NULL 
                        CHECK (match_type IN (
                            'exact_match', 'family_match', 'created_new',
                            'manual_link', 'manual_merge', 'manual_split',
                            'manual_unlink', 'conflict_pending', 'conflict_resolved')),
    match_details       JSONB NOT NULL,
    confidence          SMALLINT CHECK (confidence BETWEEN 0 AND 100),
    decided_by          TEXT NOT NULL,
    decided_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_reason     TEXT
);

COMMENT ON TABLE public.boat_match_log IS 'Audit trail for all boat matching decisions';

-- ============================================================================
-- STEP 11: Create boat_conflicts (depends on boats, results, entries, classes, regattas)
-- ============================================================================
CREATE TABLE public.boat_conflicts (
    conflict_id         BIGSERIAL PRIMARY KEY,
    result_id           BIGINT REFERENCES results(result_id) ON DELETE SET NULL,
    entry_id            BIGINT REFERENCES entries(entry_id) ON DELETE SET NULL,
    input_sail_number   TEXT NOT NULL,
    input_country_code  TEXT,
    input_class_id      INTEGER REFERENCES classes(class_id) ON DELETE SET NULL,
    input_boat_name     TEXT,
    input_helm_sa_id    INTEGER,
    input_regatta_id    TEXT REFERENCES regattas(regatta_id) ON DELETE SET NULL,
    input_date          DATE,
    candidate_boat_ids  BIGINT[],
    conflict_type       TEXT NOT NULL 
                        CHECK (conflict_type IN (
                            'multiple_candidates', 'fuzzy_sail_match',
                            'country_ambiguous', 'class_family_ambiguous',
                            'contradictory_evidence', 'manual_review_requested')),
    conflict_details    JSONB NOT NULL,
    resolution_status   TEXT NOT NULL DEFAULT 'pending'
                        CHECK (resolution_status IN ('pending', 'resolved', 'ignored', 'escalated')),
    resolved_boat_id    BIGINT REFERENCES boats(boat_id) ON DELETE SET NULL,
    resolution_action   TEXT 
                        CHECK (resolution_action IN (
                            'linked_existing', 'created_new', 'merged',
                            'split', 'ignored', 'deferred')),
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    resolution_reason   TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.boat_conflicts IS 'Review queue for boat matching conflicts';

-- ============================================================================
-- STEP 12: Add boat_id to results and entries
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'results' AND column_name = 'boat_id'
    ) THEN
        ALTER TABLE public.results ADD COLUMN boat_id BIGINT REFERENCES boats(boat_id) ON DELETE SET NULL;
        RAISE NOTICE 'Added boat_id column to results';
    ELSE
        RAISE NOTICE 'boat_id column already exists on results';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'entries' AND column_name = 'boat_id'
    ) THEN
        ALTER TABLE public.entries ADD COLUMN boat_id BIGINT REFERENCES boats(boat_id) ON DELETE SET NULL;
        RAISE NOTICE 'Added boat_id column to entries';
    ELSE
        RAISE NOTICE 'boat_id column already exists on entries';
    END IF;
END $$;

-- ============================================================================
-- STEP 13: Create indexes
-- ============================================================================

-- Boat identifiers
CREATE INDEX idx_boat_identifiers_lookup
ON boat_identifiers(identifier_type, identifier_value, class_id, country_code)
WHERE is_current = TRUE;

CREATE INDEX idx_boat_identifiers_boat ON boat_identifiers(boat_id);
CREATE INDEX idx_boat_identifiers_class ON boat_identifiers(class_id);
CREATE INDEX idx_boat_identifiers_validity ON boat_identifiers(valid_from, valid_to);

-- Boat names
CREATE INDEX idx_boat_names_boat ON boat_names(boat_id);
CREATE INDEX idx_boat_names_dates ON boat_names(first_seen_date, last_seen_date);
CREATE INDEX idx_boat_names_name ON boat_names(boat_name);

-- Boat associations
CREATE INDEX idx_boat_associations_boat ON boat_associations(boat_id);
CREATE INDEX idx_boat_associations_current ON boat_associations(boat_id) WHERE is_current = TRUE;
CREATE INDEX idx_boat_associations_sailor ON boat_associations(sa_sailing_id) WHERE sa_sailing_id IS NOT NULL;

-- Boat match log
CREATE INDEX idx_boat_match_log_result ON boat_match_log(result_id) WHERE result_id IS NOT NULL;
CREATE INDEX idx_boat_match_log_entry ON boat_match_log(entry_id) WHERE entry_id IS NOT NULL;
CREATE INDEX idx_boat_match_log_boat ON boat_match_log(boat_id) WHERE boat_id IS NOT NULL;

-- Boat conflicts
CREATE INDEX idx_boat_conflicts_pending ON boat_conflicts(resolution_status) WHERE resolution_status = 'pending';
CREATE INDEX idx_boat_conflicts_input ON boat_conflicts(input_sail_number, input_class_id);

-- Results and entries boat_id
CREATE INDEX idx_results_boat_id ON results(boat_id) WHERE boat_id IS NOT NULL;
CREATE INDEX idx_results_unlinked ON results(result_id) WHERE boat_id IS NULL AND sail_number IS NOT NULL;
CREATE INDEX idx_entries_boat_id ON entries(boat_id) WHERE boat_id IS NOT NULL;

-- ============================================================================
-- STEP 14: Create derived view
-- ============================================================================
CREATE OR REPLACE VIEW public.boat_summary AS
WITH effective_identifiers AS (
    SELECT DISTINCT ON (bi.boat_id)
        bi.boat_id,
        bi.identifier_value AS current_sail_number,
        bi.country_code AS current_country_code,
        bi.class_id AS current_class_id,
        bi.valid_from AS identifier_valid_from
    FROM boat_identifiers bi
    WHERE bi.identifier_type = 'sail_number'
      AND bi.is_current = TRUE
    ORDER BY bi.boat_id, bi.valid_from DESC, bi.created_at DESC
),
effective_names AS (
    SELECT DISTINCT ON (bn.boat_id)
        bn.boat_id,
        bn.boat_name AS current_boat_name
    FROM boat_names bn
    ORDER BY bn.boat_id, bn.last_seen_date DESC, bn.first_seen_date DESC, bn.created_at DESC
),
boat_stats AS (
    SELECT
        r.boat_id,
        MIN(reg.start_date) AS first_seen_date,
        MAX(reg.end_date) AS last_seen_date,
        COUNT(DISTINCT r.regatta_id) AS events_count,
        SUM(
            (SELECT COUNT(*) 
             FROM jsonb_object_keys(COALESCE(r.race_scores, '{}'::jsonb)) k 
             WHERE k ~ '^R[0-9]+$')
        ) AS races_count,
        MAX(reg.end_date) > CURRENT_DATE - INTERVAL '3 years' AS is_active
    FROM results r
    JOIN regattas reg ON reg.regatta_id = r.regatta_id
    WHERE r.boat_id IS NOT NULL
    GROUP BY r.boat_id
),
primary_helms AS (
    SELECT DISTINCT ON (sub.boat_id)
        sub.boat_id,
        sub.helm_sa_sailing_id AS primary_helm_sa_id,
        sub.helm_name AS primary_helm_name
    FROM (
        SELECT r.boat_id, r.helm_sa_sailing_id, r.helm_name, COUNT(*) AS cnt
        FROM results r
        WHERE r.boat_id IS NOT NULL AND r.helm_sa_sailing_id IS NOT NULL
        GROUP BY r.boat_id, r.helm_sa_sailing_id, r.helm_name
    ) sub
    ORDER BY sub.boat_id, sub.cnt DESC
)
SELECT
    b.boat_id,
    b.hull_model_id,
    ei.current_sail_number,
    ei.current_country_code,
    ei.current_class_id,
    c.class_name AS current_class_name,
    en.current_boat_name,
    bs.first_seen_date,
    bs.last_seen_date,
    COALESCE(bs.events_count, 0) AS events_count,
    COALESCE(bs.races_count, 0) AS races_count,
    CASE WHEN COALESCE(bs.is_active, FALSE) THEN 'active' ELSE 'inactive' END AS status,
    ph.primary_helm_sa_id,
    ph.primary_helm_name,
    b.created_at,
    b.notes
FROM boats b
LEFT JOIN effective_identifiers ei ON ei.boat_id = b.boat_id
LEFT JOIN effective_names en ON en.boat_id = b.boat_id
LEFT JOIN boat_stats bs ON bs.boat_id = b.boat_id
LEFT JOIN primary_helms ph ON ph.boat_id = b.boat_id
LEFT JOIN classes c ON c.class_id = ei.current_class_id;

COMMENT ON VIEW public.boat_summary IS 'Derived view for boat passport data - all counts and status are computed, not stored';

-- ============================================================================
-- STEP 15: Seed class hull families (ILCA, Optimist)
-- ============================================================================
INSERT INTO class_hull_families (family_name, share_sail_identity, description)
VALUES 
    ('ILCA/Laser', TRUE, 'Same hull, different rigs (4.7/Radial/Standard). Same sail number = same boat.'),
    ('Optimist', TRUE, 'Same hull, age divisions (A/B/C). Same sail number = same boat.'),
    ('49er', FALSE, '49er and 49erFX are different hull designs.')
ON CONFLICT (family_name) DO NOTHING;

-- Link ILCA classes to family (will fail silently if classes don't exist)
DO $$
DECLARE
    ilca_family_id INTEGER;
    optimist_family_id INTEGER;
BEGIN
    SELECT family_id INTO ilca_family_id FROM class_hull_families WHERE family_name = 'ILCA/Laser';
    SELECT family_id INTO optimist_family_id FROM class_hull_families WHERE family_name = 'Optimist';
    
    -- ILCA variants
    INSERT INTO class_family_members (family_id, class_id, is_rig_variant)
    SELECT ilca_family_id, class_id, TRUE
    FROM classes 
    WHERE class_name IN ('Ilca 4.7', 'Ilca 6', 'Ilca 7', 'ILCA 4.7', 'ILCA 6', 'ILCA 7', 
                         'Laser Radial', 'Laser Standard', 'Laser 4.7')
      AND ilca_family_id IS NOT NULL
    ON CONFLICT DO NOTHING;
    
    -- Optimist divisions
    INSERT INTO class_family_members (family_id, class_id, is_rig_variant)
    SELECT optimist_family_id, class_id, FALSE
    FROM classes 
    WHERE class_name IN ('Optimist A', 'Optimist B', 'Optimist C')
      AND optimist_family_id IS NOT NULL
    ON CONFLICT DO NOTHING;
    
    RAISE NOTICE 'Seeded class family members';
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
AND table_name IN ('boats', 'boat_identifiers', 'boat_names', 'boat_associations', 
                   'boat_match_log', 'boat_conflicts', 'class_hull_families', 
                   'class_family_members', 'hull_models', 'boats_legacy');

-- Check columns added
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'results' AND column_name = 'boat_id';

SELECT column_name, data_type FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'entries' AND column_name = 'boat_id';

-- Check view created
SELECT viewname FROM pg_views WHERE viewname = 'boat_summary';

-- Check trigger created
SELECT tgname FROM pg_trigger WHERE tgname = 'trg_check_identifier_overlap';

-- Check class families seeded
SELECT * FROM class_hull_families;
SELECT cfm.*, c.class_name 
FROM class_family_members cfm 
JOIN classes c ON c.class_id = cfm.class_id;
*/

-- ============================================================================
-- ROLLBACK PROCEDURE (execute in order if rollback needed)
-- ============================================================================
/*
-- ROLLBACK STEP 1: Remove FK columns from results/entries
ALTER TABLE results DROP COLUMN IF EXISTS boat_id;
ALTER TABLE entries DROP COLUMN IF EXISTS boat_id;

-- ROLLBACK STEP 2: Drop view
DROP VIEW IF EXISTS boat_summary;

-- ROLLBACK STEP 3: Drop trigger and function
DROP TRIGGER IF EXISTS trg_check_identifier_overlap ON boat_identifiers;
DROP FUNCTION IF EXISTS check_identifier_overlap();

-- ROLLBACK STEP 4: Drop boat tables (order matters - CASCADE for boats)
DROP TABLE IF EXISTS boat_conflicts CASCADE;
DROP TABLE IF EXISTS boat_match_log CASCADE;
DROP TABLE IF EXISTS boat_associations CASCADE;
DROP TABLE IF EXISTS boat_names CASCADE;
DROP TABLE IF EXISTS boat_identifiers CASCADE;
DROP TABLE IF EXISTS boats CASCADE;
DROP TABLE IF EXISTS hull_models CASCADE;
DROP TABLE IF EXISTS class_family_members CASCADE;
DROP TABLE IF EXISTS class_hull_families CASCADE;

-- ROLLBACK STEP 5: Restore legacy table
ALTER TABLE boats_legacy RENAME TO boats;

-- ROLLBACK STEP 6: Recreate legacy indexes and constraints
CREATE UNIQUE INDEX boats_sail_number_class_name_key ON boats(sail_number, class_name);
CREATE INDEX idx_boats_sail_number ON boats(sail_number);
CREATE INDEX idx_boats_class_name ON boats(class_name);

-- ROLLBACK STEP 7: Verify
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'boat%';
-- Should show only: boats
*/
