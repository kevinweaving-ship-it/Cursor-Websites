# Boat Register / Boat Passport — End-to-End Architecture Plan

**Status:** PLAN ONLY — No production changes  
**Date:** 2026-07-27  
**Author:** Cursor Cloud Agent (audit for ChatGPT review)

---

## Executive Summary

This document provides a comprehensive architecture plan for implementing a **Boat Register** and **Boat Passport** system for SailingSA. The plan is based on a thorough audit of:
- Database schema (45+ tables in `public`, 15+ in `app`)
- Results ingestion pipeline
- Class/fleet structure
- Existing boat-related APIs
- Live production data

**Key Finding:** A `public.boats` table exists but is **completely unused**. All boat identity today is inferred from `(sail_number, class_id)` on `results` rows. The proposed architecture creates a normalized boat register while preserving results as the source of truth.

---

## Part 1: Existing Files, Routes, Tables, and Services Inspected

### 1.1 Database Tables Audited

| Schema | Tables | Boat-Relevant |
|--------|--------|---------------|
| `public` | ~45 tables | `results`, `regattas`, `regatta_blocks`, `classes`, `clubs`, `entries`, `boats` (unused), `sas_id_personal`, `temp_people` |
| `app` | ~15 tables | `regatta_*_results` (raw scrape), `events`, `fleets` |

### 1.2 Code Files Inspected

| File | Purpose | Lines |
|------|---------|-------|
| `/workspace/api.py` | Main FastAPI backend | ~26,800 |
| `/workspace/results_ingestion_common.py` | Ingestion helpers | ~1,200 |
| `/workspace/docs/DATABASE_ARCHITECTURE_DISCOVERY.md` | Schema documentation | Full |
| `/workspace/docs/SCHEMA.md` | Target data model | Full |
| `/workspace/docs/goals.md` | Project architecture goals | Full |
| `/workspace/docs/SYSTEM_BASELINE_v1.md` | Live system baseline | Full |
| 15+ table README files | Per-table documentation | Full |

### 1.3 API Routes Inspected

**Existing Boat Endpoints (query `results`, not `boats`):**
- `GET /api/boat/classes/{sail_number}` — classes a sail number has raced in
- `GET /api/boat/info/{sail_number}/{class_name}` — boat name + regatta count
- `GET /api/boat/pedigree/{sail_number}/{class_name}` — helm history

**Related Endpoints:**
- `GET /api/class/{id|slug}` — class page with sailor/boat aggregates
- `GET /api/member/{sa_id}/results` — sailor results with boat fields
- `PATCH /api/result/{id}` — admin edit including boat fields

### 1.4 Live Production Data (as of 2026-07-27)

| Metric | Value |
|--------|-------|
| Active Sailors | 2,365 |
| Classes | 176 |
| Regattas | 400 |
| Races | 9,598 |
| Clubs | 63 |

---

## Part 2: Current Results/Class/Event/Sailor/Club Relationships

### 2.1 Entity Relationship Diagram (Current State)

```
regattas (event)
    │
    ├── host_club_id → clubs
    │
    └── regatta_blocks (fleet/class block)
            │
            ├── class_id → classes
            │
            └── results (one row per finishing entry)
                    │
                    ├── class_id → classes
                    ├── club_id → clubs
                    ├── entry_id → entries (rarely used)
                    │
                    ├── helm_sa_sailing_id (INTEGER, no FK)
                    ├── crew_sa_sailing_id (INTEGER, no FK)
                    │
                    ├── sail_number (TEXT) ─────────────────┐
                    ├── boat_name (TEXT, optional)          │
                    ├── bow_no, jib_no, hull_no (TEXT)      │ De facto boat identity
                    └── class_id ───────────────────────────┘

classes
    │
    ├── parent_id → classes (self-reference for hierarchy)
    └── class_aliases.class_id → classes

clubs
    │
    └── club_aliases.club_id → clubs

sas_id_personal (sailor directory)
    │
    ├── sa_sailing_id (UNIQUE, no PK)
    ├── primary_class, primary_sailno (TEXT hints)
    └── user_accounts.sas_id → sas_id_personal

boats (EXISTS BUT UNUSED)
    │
    ├── sail_number (TEXT)
    ├── class_name (TEXT, not FK)
    └── UNIQUE(sail_number, class_name)
```

### 2.2 Current Boat Identity Model

**De facto boat key:** `(TRIM(sail_number), class_id)`

There is NO:
- Stable `boat_id` linked to results
- Ownership history
- Sail number allocation history
- Hull metadata (make, year, HIN)
- Normalized boat register

---

## Part 3: Every Boat-Related Field Found Internally

### 3.1 On `public.results` (Primary Source)

| Field | Type | Purpose | Populated |
|-------|------|---------|-----------|
| `sail_number` | TEXT | Primary boat identifier | High |
| `boat_name` | TEXT | Named boat | Sparse (~30%) |
| `bow_no` | TEXT | Bow number | Rare |
| `jib_no` | TEXT | Jib number | Rare |
| `hull_no` | TEXT | Hull number | Very rare |
| `class_id` | INTEGER FK | Class reference | High |
| `class_original` | TEXT | PDF text (audit) | High |
| `class_canonical` | TEXT | Validated class name | High |
| `nationality` | VARCHAR | Country prefix stripped | Sparse |

### 3.2 On `public.boats` (Unused Schema)

| Field | Type | Purpose |
|-------|------|---------|
| `boat_id` | BIGINT PK | Stable identifier |
| `sail_number` | TEXT NOT NULL | Sail number |
| `class_name` | TEXT NOT NULL | Class (not FK) |
| `boat_name` | TEXT | Named boat |
| `make` | TEXT | Manufacturer/builder |
| `built_in` | TEXT | Build location |
| `year_made` | INTEGER | Build year |

**Constraint:** `UNIQUE(sail_number, class_name)`

### 3.3 On `public.entries` (Underused)

| Field | Type | Purpose |
|-------|------|---------|
| `sail_number` | TEXT | Entry sail |
| `boat_name` | TEXT | Entry boat name |
| `helm_sas_id` | TEXT | Helm (different type than results!) |
| `crew_sas_id` | TEXT | Crew |

### 3.4 On `public.sas_id_personal` (Sailor Directory)

| Field | Type | Purpose |
|-------|------|---------|
| `primary_class` | VARCHAR | Sailor's main class |
| `primary_sailno` | VARCHAR | Sailor's main sail number |

### 3.5 On `app.regatta_*_results` (Raw Scrape)

| Field | Type | Purpose |
|-------|------|---------|
| `boat_name` | TEXT | Raw boat name |
| `class` | TEXT | Raw class |
| `sail_no` | TEXT | Raw sail number |
| `jib_no` | TEXT | Raw jib number |

### 3.6 Boat-Related API Responses

| Endpoint | Returns |
|----------|---------|
| `/api/boat/classes/{sail}` | `{classes: ["Optimist A", "Optimist B"]}` |
| `/api/boat/info/{sail}/{class}` | `{sail_number, boat_name, class_name, regatta_count}` |
| `/api/boat/pedigree/{sail}/{class}` | `{pedigree: [{helm_name, helm_sa_sailing_id, regatta_id, event_name, dates}]}` |

---

## Part 4: Proposed Tables and Columns

### 4.1 Core Boat Register Tables

#### `boats` (Repurposed/Enhanced)

```sql
CREATE TABLE public.boats (
    boat_id             BIGSERIAL PRIMARY KEY,
    
    -- Identity (canonical key)
    class_id            INTEGER NOT NULL REFERENCES classes(class_id),
    sail_number_normalized TEXT NOT NULL,
    
    -- Display/audit
    sail_number_original TEXT,
    boat_name           TEXT,
    
    -- Lifecycle
    first_seen_date     DATE NOT NULL,
    last_seen_date      DATE NOT NULL,
    first_seen_regatta_id TEXT REFERENCES regattas(regatta_id),
    last_seen_regatta_id TEXT REFERENCES regattas(regatta_id),
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'retired', 
                                          'lost', 'exported', 'unknown')),
    
    -- Statistics (derived, cached)
    events_count        INTEGER NOT NULL DEFAULT 0,
    races_count         INTEGER NOT NULL DEFAULT 0,
    
    -- Confidence scores (0-100)
    identity_confidence     SMALLINT DEFAULT 50,
    completeness_score      SMALLINT DEFAULT 0,
    ownership_confidence    SMALLINT DEFAULT 0,
    class_confidence        SMALLINT DEFAULT 100,
    
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Uniqueness
    CONSTRAINT uq_boats_class_sail UNIQUE (class_id, sail_number_normalized)
);
```

#### `boat_identifiers` (Hull Numbers, Aliases)

```sql
CREATE TABLE public.boat_identifiers (
    identifier_id       BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    identifier_type     TEXT NOT NULL CHECK (identifier_type IN (
                            'sail_number', 'bow_no', 'jib_no', 'hull_no', 
                            'hin', 'measurement_id', 'alias')),
    identifier_value    TEXT NOT NULL,
    is_primary          BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from          DATE,
    valid_to            DATE,
    source_regatta_id   TEXT REFERENCES regattas(regatta_id),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_boat_identifier UNIQUE (boat_id, identifier_type, identifier_value)
);
```

#### `boat_names` (Name History)

```sql
CREATE TABLE public.boat_names (
    name_id             BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    boat_name           TEXT NOT NULL,
    is_current          BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_date     DATE NOT NULL,
    last_seen_date      DATE NOT NULL,
    occurrence_count    INTEGER NOT NULL DEFAULT 1,
    source_regatta_id   TEXT REFERENCES regattas(regatta_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_boat_name UNIQUE (boat_id, boat_name)
);
```

#### `boat_ownership` (Ownership History)

```sql
CREATE TABLE public.boat_ownership (
    ownership_id        BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    owner_sa_sailing_id INTEGER,  -- FK to sas_id_personal when exists
    owner_name          TEXT,     -- For unresolved owners
    owner_club_id       INTEGER REFERENCES clubs(club_id),
    ownership_type      TEXT CHECK (ownership_type IN (
                            'owner', 'primary_helm', 'club_boat', 
                            'charter', 'borrowed', 'unknown')),
    valid_from          DATE NOT NULL,
    valid_to            DATE,
    is_current          BOOLEAN NOT NULL DEFAULT FALSE,
    confidence          SMALLINT DEFAULT 50,
    source_regatta_id   TEXT REFERENCES regattas(regatta_id),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `boat_metadata` (Hull Details - Future)

```sql
CREATE TABLE public.boat_metadata (
    metadata_id         BIGSERIAL PRIMARY KEY,
    boat_id             BIGINT NOT NULL REFERENCES boats(boat_id) ON DELETE CASCADE,
    
    -- Manufacturer/Model
    manufacturer        TEXT,
    brand               TEXT,
    model               TEXT,
    hull_type           TEXT,
    
    -- Build
    year_built          INTEGER,
    build_location      TEXT,
    builder_name        TEXT,
    
    -- Equipment
    rig_type            TEXT,
    sail_maker          TEXT,
    
    -- Measurement
    measurement_cert_no TEXT,
    measurement_date    DATE,
    
    -- Provenance
    source_type         TEXT,
    source_url          TEXT,
    confidence          SMALLINT DEFAULT 50,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.2 Linking Tables

#### `results.boat_id` (Add Column)

```sql
ALTER TABLE public.results 
ADD COLUMN boat_id BIGINT REFERENCES boats(boat_id);

CREATE INDEX idx_results_boat_id ON results(boat_id);
```

#### `entries.boat_id` (Add Column)

```sql
ALTER TABLE public.entries
ADD COLUMN boat_id BIGINT REFERENCES boats(boat_id);
```

### 4.3 Audit/Provenance Tables

#### `boat_match_log` (Matching Decisions)

```sql
CREATE TABLE public.boat_match_log (
    log_id              BIGSERIAL PRIMARY KEY,
    result_id           BIGINT REFERENCES results(result_id),
    boat_id             BIGINT REFERENCES boats(boat_id),
    match_type          TEXT NOT NULL CHECK (match_type IN (
                            'auto_exact', 'auto_fuzzy', 'auto_created',
                            'manual_linked', 'manual_merged', 'manual_split',
                            'conflict_flagged', 'override')),
    confidence          SMALLINT,
    match_details       JSONB,
    matched_by          TEXT,  -- 'system' or admin user
    matched_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `boat_conflicts` (Uncertain Matches)

```sql
CREATE TABLE public.boat_conflicts (
    conflict_id         BIGSERIAL PRIMARY KEY,
    result_id           BIGINT REFERENCES results(result_id),
    candidate_boat_ids  BIGINT[],
    conflict_type       TEXT NOT NULL CHECK (conflict_type IN (
                            'multiple_boats', 'name_mismatch', 
                            'class_change', 'sail_reuse', 'duplicate')),
    conflict_details    JSONB,
    resolution_status   TEXT NOT NULL DEFAULT 'pending'
                        CHECK (resolution_status IN ('pending', 'resolved', 'ignored')),
    resolved_boat_id    BIGINT REFERENCES boats(boat_id),
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Part 5: Foreign Keys, Indexes, and Uniqueness Rules

### 5.1 Primary Keys

| Table | Primary Key |
|-------|-------------|
| `boats` | `boat_id` (BIGSERIAL) |
| `boat_identifiers` | `identifier_id` (BIGSERIAL) |
| `boat_names` | `name_id` (BIGSERIAL) |
| `boat_ownership` | `ownership_id` (BIGSERIAL) |
| `boat_metadata` | `metadata_id` (BIGSERIAL) |

### 5.2 Foreign Keys

| From | To | On Delete |
|------|-----|-----------|
| `boats.class_id` | `classes.class_id` | RESTRICT |
| `boats.first_seen_regatta_id` | `regattas.regatta_id` | SET NULL |
| `boats.last_seen_regatta_id` | `regattas.regatta_id` | SET NULL |
| `boat_identifiers.boat_id` | `boats.boat_id` | CASCADE |
| `boat_names.boat_id` | `boats.boat_id` | CASCADE |
| `boat_ownership.boat_id` | `boats.boat_id` | CASCADE |
| `boat_ownership.owner_club_id` | `clubs.club_id` | SET NULL |
| `boat_metadata.boat_id` | `boats.boat_id` | CASCADE |
| `results.boat_id` | `boats.boat_id` | SET NULL |
| `entries.boat_id` | `boats.boat_id` | SET NULL |

### 5.3 Unique Constraints

| Table | Constraint | Columns |
|-------|------------|---------|
| `boats` | `uq_boats_class_sail` | `(class_id, sail_number_normalized)` |
| `boat_identifiers` | `uq_boat_identifier` | `(boat_id, identifier_type, identifier_value)` |
| `boat_names` | `uq_boat_name` | `(boat_id, boat_name)` |

### 5.4 Indexes

```sql
-- Boats
CREATE INDEX idx_boats_sail_normalized ON boats(sail_number_normalized);
CREATE INDEX idx_boats_sail_normalized_trgm ON boats USING gin(sail_number_normalized gin_trgm_ops);
CREATE INDEX idx_boats_boat_name_trgm ON boats USING gin(boat_name gin_trgm_ops);
CREATE INDEX idx_boats_class_id ON boats(class_id);
CREATE INDEX idx_boats_status ON boats(status);
CREATE INDEX idx_boats_last_seen ON boats(last_seen_date DESC);

-- Results linking
CREATE INDEX idx_results_boat_id ON results(boat_id);
CREATE INDEX idx_results_sail_class ON results(sail_number, class_id);

-- Ownership
CREATE INDEX idx_boat_ownership_owner ON boat_ownership(owner_sa_sailing_id);
CREATE INDEX idx_boat_ownership_current ON boat_ownership(boat_id) WHERE is_current = TRUE;
```

---

## Part 6: Sail Number Normalization and Boat Matching Rules

### 6.1 Sail Number Normalization Algorithm

```python
def normalize_sail_number(raw: str, class_id: int = None) -> tuple[str, str, dict]:
    """
    Returns: (normalized, original, metadata)
    
    Rules:
    1. TRIM whitespace
    2. Extract and remove country prefix (RSA-, GBR-, etc.)
    3. Preserve alphanumeric suffix (R, A, B)
    4. No zero-padding normalization
    5. Case-insensitive storage (uppercase)
    """
    original = raw.strip() if raw else ''
    
    # Country prefix patterns
    country_pattern = r'^([A-Z]{2,3})-?(\d+.*)$'
    match = re.match(country_pattern, original.upper())
    
    if match:
        country = match.group(1)
        number = match.group(2)
        normalized = number.upper()
        metadata = {'country_prefix': country, 'extracted': True}
    else:
        normalized = original.upper()
        metadata = {'country_prefix': None, 'extracted': False}
    
    return normalized, original, metadata
```

### 6.2 Boat Matching Algorithm

```python
def match_or_create_boat(sail_number: str, class_id: int, 
                         result_row: dict) -> tuple[int, str]:
    """
    Returns: (boat_id, match_type)
    
    Priority:
    1. Exact match: (normalized_sail, class_id) → existing boat
    2. Fuzzy match: same class, similar sail (typo tolerance)
    3. Create new: if no match found
    """
    normalized, original, meta = normalize_sail_number(sail_number, class_id)
    
    # Step 1: Exact match
    boat = db.query("""
        SELECT boat_id FROM boats 
        WHERE class_id = %s AND sail_number_normalized = %s
    """, (class_id, normalized))
    
    if boat:
        return boat.boat_id, 'auto_exact'
    
    # Step 2: Fuzzy match (same class, similarity > 0.85)
    candidates = db.query("""
        SELECT boat_id, sail_number_normalized,
               similarity(sail_number_normalized, %s) as sim
        FROM boats
        WHERE class_id = %s
          AND similarity(sail_number_normalized, %s) > 0.85
        ORDER BY sim DESC
        LIMIT 3
    """, (normalized, class_id, normalized))
    
    if len(candidates) == 1 and candidates[0].sim > 0.95:
        return candidates[0].boat_id, 'auto_fuzzy'
    elif len(candidates) > 1:
        # Multiple candidates → flag for review
        create_conflict(result_row, [c.boat_id for c in candidates], 'multiple_boats')
        return None, 'conflict_flagged'
    
    # Step 3: Create new boat
    boat_id = db.insert("""
        INSERT INTO boats (class_id, sail_number_normalized, sail_number_original,
                          boat_name, first_seen_date, last_seen_date,
                          first_seen_regatta_id, events_count, races_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 1)
        RETURNING boat_id
    """, (class_id, normalized, original,
          result_row.get('boat_name'),
          result_row['regatta_date'], result_row['regatta_date'],
          result_row['regatta_id']))
    
    return boat_id, 'auto_created'
```

### 6.3 Conflict Detection Rules

| Conflict Type | Detection Rule |
|---------------|----------------|
| `multiple_boats` | Same sail+class matches >1 boat (fuzzy) |
| `name_mismatch` | Same sail+class, different boat_name |
| `class_change` | Same sail, different class (legitimate transfer) |
| `sail_reuse` | Same sail+class, different owner in same season |
| `duplicate` | Two boats likely same hull (merge candidate) |

---

## Part 7: Duplicate/Conflict/Manual Review Workflow

### 7.1 Review Queue States

```
PENDING → RESOLVED (linked/merged/split)
        → IGNORED (legitimate variation)
        → ESCALATED (needs admin decision)
```

### 7.2 Admin Review Endpoints

```
GET  /admin/boats/conflicts              — List pending conflicts
GET  /admin/boats/conflicts/{id}         — Conflict details
POST /admin/boats/conflicts/{id}/resolve — Resolve: link/merge/split/ignore
POST /admin/boats/merge                  — Merge two boats into one
POST /admin/boats/split                  — Split one boat into two
PATCH /admin/boats/{id}                  — Edit boat metadata
```

### 7.3 Merge Algorithm

```python
def merge_boats(keep_boat_id: int, remove_boat_id: int, admin_user: str):
    """
    Merge remove_boat into keep_boat:
    1. Update all results.boat_id from remove → keep
    2. Merge boat_names (combine histories)
    3. Merge boat_identifiers
    4. Merge boat_ownership (adjust date ranges)
    5. Recalculate keep_boat statistics
    6. Log the merge
    7. Delete remove_boat
    """
    with db.transaction():
        # Transfer results
        db.execute("""
            UPDATE results SET boat_id = %s WHERE boat_id = %s
        """, (keep_boat_id, remove_boat_id))
        
        # Merge names
        db.execute("""
            INSERT INTO boat_names (boat_id, boat_name, first_seen_date, 
                                    last_seen_date, occurrence_count)
            SELECT %s, boat_name, first_seen_date, last_seen_date, occurrence_count
            FROM boat_names WHERE boat_id = %s
            ON CONFLICT (boat_id, boat_name) DO UPDATE SET
                occurrence_count = boat_names.occurrence_count + EXCLUDED.occurrence_count,
                first_seen_date = LEAST(boat_names.first_seen_date, EXCLUDED.first_seen_date),
                last_seen_date = GREATEST(boat_names.last_seen_date, EXCLUDED.last_seen_date)
        """, (keep_boat_id, remove_boat_id))
        
        # Log merge
        db.execute("""
            INSERT INTO boat_match_log (boat_id, match_type, match_details, matched_by)
            VALUES (%s, 'manual_merged', %s, %s)
        """, (keep_boat_id, json.dumps({'merged_from': remove_boat_id}), admin_user))
        
        # Delete removed boat (cascades identifiers, names, ownership)
        db.execute("DELETE FROM boats WHERE boat_id = %s", (remove_boat_id,))
        
        # Recalculate statistics
        recalculate_boat_stats(keep_boat_id)
```

---

## Part 8: Historical Backfill Plan

### 8.1 Phases

| Phase | Scope | Duration Est. |
|-------|-------|---------------|
| **Phase 0** | Schema migration (add tables, columns) | 1 run |
| **Phase 1** | Extract distinct (sail, class) from results | ~5 min |
| **Phase 2** | Create boat records | ~10 min |
| **Phase 3** | Link results to boats | ~30 min |
| **Phase 4** | Extract boat names | ~10 min |
| **Phase 5** | Infer ownership from helm frequency | ~15 min |
| **Phase 6** | Generate conflicts for review | ~5 min |

### 8.2 Backfill Script (Idempotent)

```python
def backfill_boat_register(dry_run: bool = True):
    """
    Idempotent backfill from results to boats.
    Safe to run multiple times.
    """
    log = []
    
    # Phase 1: Extract distinct boats
    boats_to_create = db.query("""
        SELECT DISTINCT
            r.class_id,
            UPPER(TRIM(r.sail_number)) as sail_norm,
            r.sail_number as sail_orig,
            MIN(reg.start_date) as first_seen,
            MAX(reg.end_date) as last_seen,
            MIN(r.regatta_id) as first_regatta,
            MAX(r.regatta_id) as last_regatta,
            COUNT(DISTINCT r.regatta_id) as events,
            COUNT(*) as races
        FROM results r
        JOIN regattas reg ON reg.regatta_id = r.regatta_id
        WHERE r.sail_number IS NOT NULL
          AND TRIM(r.sail_number) != ''
          AND r.class_id IS NOT NULL
        GROUP BY r.class_id, UPPER(TRIM(r.sail_number)), r.sail_number
    """)
    
    log.append(f"Found {len(boats_to_create)} distinct (sail, class) combinations")
    
    if dry_run:
        return {'phase': 'extract', 'boats_found': len(boats_to_create), 'log': log}
    
    # Phase 2: Insert boats (skip existing)
    created = 0
    for b in boats_to_create:
        exists = db.query("""
            SELECT boat_id FROM boats 
            WHERE class_id = %s AND sail_number_normalized = %s
        """, (b.class_id, b.sail_norm))
        
        if not exists:
            db.execute("""
                INSERT INTO boats (class_id, sail_number_normalized, sail_number_original,
                                  first_seen_date, last_seen_date,
                                  first_seen_regatta_id, last_seen_regatta_id,
                                  events_count, races_count, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        CASE WHEN %s > CURRENT_DATE - INTERVAL '3 years' 
                             THEN 'active' ELSE 'inactive' END)
            """, (b.class_id, b.sail_norm, b.sail_orig,
                  b.first_seen, b.last_seen,
                  b.first_regatta, b.last_regatta,
                  b.events, b.races, b.last_seen))
            created += 1
    
    log.append(f"Created {created} boat records")
    
    # Phase 3: Link results to boats
    linked = db.execute("""
        UPDATE results r
        SET boat_id = b.boat_id
        FROM boats b
        WHERE b.class_id = r.class_id
          AND b.sail_number_normalized = UPPER(TRIM(r.sail_number))
          AND r.boat_id IS NULL
    """)
    
    log.append(f"Linked {linked} result rows to boats")
    
    # Phase 4: Extract boat names
    db.execute("""
        INSERT INTO boat_names (boat_id, boat_name, first_seen_date, last_seen_date, 
                               occurrence_count, is_current)
        SELECT 
            b.boat_id,
            r.boat_name,
            MIN(reg.start_date),
            MAX(reg.end_date),
            COUNT(*),
            FALSE
        FROM results r
        JOIN boats b ON b.boat_id = r.boat_id
        JOIN regattas reg ON reg.regatta_id = r.regatta_id
        WHERE r.boat_name IS NOT NULL AND TRIM(r.boat_name) != ''
        GROUP BY b.boat_id, r.boat_name
        ON CONFLICT (boat_id, boat_name) DO NOTHING
    """)
    
    # Set most common name as current
    db.execute("""
        UPDATE boat_names bn
        SET is_current = TRUE
        WHERE name_id = (
            SELECT name_id FROM boat_names
            WHERE boat_id = bn.boat_id
            ORDER BY occurrence_count DESC, last_seen_date DESC
            LIMIT 1
        )
    """)
    
    # Update boats.boat_name from current name
    db.execute("""
        UPDATE boats b
        SET boat_name = (
            SELECT boat_name FROM boat_names
            WHERE boat_id = b.boat_id AND is_current = TRUE
            LIMIT 1
        )
    """)
    
    # Phase 5: Infer primary ownership from helm frequency
    db.execute("""
        INSERT INTO boat_ownership (boat_id, owner_sa_sailing_id, owner_name,
                                   ownership_type, valid_from, is_current, confidence)
        SELECT DISTINCT ON (b.boat_id)
            b.boat_id,
            r.helm_sa_sailing_id,
            r.helm_name,
            'primary_helm',
            MIN(reg.start_date),
            TRUE,
            CASE WHEN COUNT(*) > 5 THEN 80 
                 WHEN COUNT(*) > 2 THEN 60 
                 ELSE 40 END
        FROM boats b
        JOIN results r ON r.boat_id = b.boat_id
        JOIN regattas reg ON reg.regatta_id = r.regatta_id
        WHERE r.helm_sa_sailing_id IS NOT NULL
        GROUP BY b.boat_id, r.helm_sa_sailing_id, r.helm_name
        ORDER BY b.boat_id, COUNT(*) DESC
        ON CONFLICT DO NOTHING
    """)
    
    return {'phases_completed': 5, 'log': log}
```

### 8.3 Rollback Procedure

```sql
-- Rollback Phase 3 (unlink results)
UPDATE results SET boat_id = NULL;

-- Rollback Phases 2-5 (delete boat data)
TRUNCATE boat_ownership, boat_names, boat_identifiers, boat_metadata, 
         boat_match_log, boat_conflicts, boats CASCADE;

-- Rollback Phase 0 (drop tables)
-- Only if needed: DROP TABLE boat_*, ALTER TABLE results DROP COLUMN boat_id;
```

---

## Part 9: New Result Automatic Linking Flow

### 9.1 Integration Point

In `results_ingestion_common.py`, after result INSERT:

```python
def insert_result(result_row: dict) -> int:
    # ... existing INSERT logic ...
    result_id = cursor.lastrowid
    
    # NEW: Boat linking
    if result_row.get('sail_number') and result_row.get('class_id'):
        boat_id, match_type = match_or_create_boat(
            result_row['sail_number'],
            result_row['class_id'],
            result_row
        )
        
        if boat_id:
            db.execute("""
                UPDATE results SET boat_id = %s WHERE result_id = %s
            """, (boat_id, result_id))
            
            # Update boat statistics
            update_boat_stats(boat_id, result_row)
        
        # Log the match
        log_boat_match(result_id, boat_id, match_type, result_row)
    
    return result_id
```

### 9.2 Boat Statistics Update

```python
def update_boat_stats(boat_id: int, result_row: dict):
    """Update boat statistics after new result linked."""
    db.execute("""
        UPDATE boats SET
            last_seen_date = GREATEST(last_seen_date, %s),
            last_seen_regatta_id = CASE 
                WHEN %s > last_seen_date THEN %s 
                ELSE last_seen_regatta_id END,
            events_count = events_count + 1,
            races_count = races_count + COALESCE(%s, 1),
            status = 'active',
            updated_at = NOW()
        WHERE boat_id = %s
    """, (result_row['regatta_date'], result_row['regatta_date'],
          result_row['regatta_id'], result_row.get('races_sailed', 1),
          boat_id))
```

---

## Part 10: Boat Register and Boat Passport Route/API Plan

### 10.1 Public Routes

| Route | Purpose |
|-------|---------|
| `/boats` | Boat Register home (search, filters) |
| `/boats/class/{class_slug}` | Per-class boat register |
| `/boat/{class_slug}/{sail_number}` | **Boat Passport** page |

### 10.2 Canonical URL Rules

```
/boat/{class_slug}/{sail_number_normalized}

Examples:
  /boat/optimist-a/1365
  /boat/420/54808
  /boat/ilca-6/218429
```

### 10.3 Redirects

| Scenario | Redirect |
|----------|----------|
| Sail number correction | 301 → canonical URL |
| Class change (sail transferred) | 301 → new class URL |
| Merged boat | 301 → surviving boat URL |
| Old URL format | 301 → new format |

### 10.4 API Endpoints

```
# Public
GET  /api/boats                          — Search/filter boats
GET  /api/boats/class/{class_id}         — Boats in a class
GET  /api/boat/{boat_id}                 — Boat passport data
GET  /api/boat/by-sail/{class_id}/{sail} — Lookup by sail+class

# Admin
GET  /admin/api/boats                    — Admin boat list
POST /admin/api/boats                    — Create boat manually
PATCH /admin/api/boats/{id}              — Edit boat
DELETE /admin/api/boats/{id}             — Soft delete (set status)
POST /admin/api/boats/{id}/merge         — Merge boats
GET  /admin/api/boats/conflicts          — Review queue
```

### 10.5 Boat Passport Response Shape

```json
{
  "boat_id": 12345,
  "class": {
    "class_id": 62,
    "class_name": "Optimist A",
    "class_slug": "optimist-a"
  },
  "sail_number": "1365",
  "sail_number_original": "1365",
  "boat_name": "Kookaburra",
  "status": "active",
  
  "lifecycle": {
    "first_seen": "2021-04-05",
    "last_seen": "2026-04-06",
    "events_count": 19,
    "races_count": 127
  },
  
  "names": [
    {"name": "Kookaburra", "first_seen": "2021-04-05", "is_current": true}
  ],
  
  "ownership": [
    {
      "owner_name": "Timothy Weaving",
      "owner_sa_sailing_id": 21172,
      "type": "primary_helm",
      "from": "2024-02-11",
      "is_current": true
    },
    {
      "owner_name": "Joshua Nankin",
      "owner_sa_sailing_id": 8704,
      "type": "primary_helm",
      "from": "2021-04-05",
      "to": "2023-04-10"
    }
  ],
  
  "pedigree": [
    {"helm": "Cameron Starke", "sa_id": 23001, "regatta": "WC Dinghy Champs 2026", "date": "2026-04-06"},
    {"helm": "Timothy Weaving", "sa_id": 21172, "regatta": "HYC Cape Classic 2026", "date": "2026-02-16"}
  ],
  
  "confidence": {
    "identity": 95,
    "completeness": 70,
    "ownership": 80,
    "class": 100
  },
  
  "canonical_url": "https://sailingsa.co.za/boat/optimist-a/1365",
  "seo": {
    "title": "Optimist A Sail 1365 'Kookaburra' - SailingSA Boat Register",
    "description": "Racing history and ownership for Optimist A sail number 1365, currently named 'Kookaburra'. 19 regattas, 127 races since 2021."
  }
}
```

### 10.6 SEO & Structured Data

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Optimist A Sail 1365 - Kookaburra",
  "category": "Sailboat",
  "brand": "Optimist",
  "identifier": "SAIL:1365",
  "url": "https://sailingsa.co.za/boat/optimist-a/1365"
}
</script>
```

### 10.7 Mobile-First Layout

```
┌─────────────────────────────────────┐
│ ← Back to Optimist A Register       │
├─────────────────────────────────────┤
│ 🚤 Sail 1365                        │
│ "Kookaburra"                        │
│ Optimist A · Active                 │
├─────────────────────────────────────┤
│ STATS                               │
│ 19 Events · 127 Races · Since 2021  │
├─────────────────────────────────────┤
│ CURRENT HELM                        │
│ Timothy Weaving (HYC) since Feb 24  │
├─────────────────────────────────────┤
│ RACING HISTORY                      │
│ ┌─────────────────────────────────┐ │
│ │ WC Dinghy Champs 2026           │ │
│ │ Cameron Starke · 4th            │ │
│ ├─────────────────────────────────┤ │
│ │ HYC Cape Classic 2026           │ │
│ │ Timothy Weaving · 3rd           │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## Part 11: Ranking Integration Points (No Changes)

### 11.1 Future Ranking Weights Available from Boat Register

| Metric | Source | Potential Use |
|--------|--------|---------------|
| Active national class size | `COUNT(boats) WHERE status='active' AND class_id=X` | Class strength weighting |
| Event participation % | `boats.events_count / class_events_count` | Consistency bonus |
| Returning boats | `boats WHERE first_seen < season_start AND last_seen IN season` | Fleet stability |
| New boats | `boats WHERE first_seen IN season` | Growth indicator |
| Travelling boats | `boats with results in multiple provinces` | Competitiveness |
| Provincial representation | `DISTINCT province FROM boat_ownership` | Geographic coverage |
| Historical attendance | Time-series from `boat_match_log` | Trend analysis |
| Class growth/maturity | `new_boats / total_boats` per season | Fleet health |

### 11.2 No Ranking Code Changes in This Plan

Rankings remain unchanged. The boat register provides data that **future** ranking enhancements can consume via JOIN queries.

---

## Part 12: Risks to Existing Production Behavior

### 12.1 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `results.boat_id` column addition | LOW - nullable, no constraint | Add as nullable, no default |
| Existing boat APIs break | MEDIUM - current queries work | Maintain current queries, add new |
| Backfill timeout | MEDIUM - large table | Run in batches with checkpoints |
| Duplicate boat creation | MEDIUM - data quality | Unique constraint + conflict detection |
| Performance degradation | LOW - indexed queries | Add indexes before backfill |
| Rollback needed | LOW - reversible | Document rollback procedure |

### 12.2 Production Safeguards

1. **Additive only:** No existing columns removed or renamed
2. **Nullable FK:** `results.boat_id` is nullable - no constraint violations
3. **Existing APIs unchanged:** Current `/api/boat/*` endpoints continue to work
4. **Backfill is idempotent:** Safe to run multiple times
5. **Conflict isolation:** Uncertain matches flagged, not auto-resolved
6. **Admin review:** Manual resolution for conflicts
7. **Rollback tested:** Procedure documented and verified

---

## Part 13: Migration Sequence, Tests, and Acceptance Criteria

### 13.1 Migration Sequence

| Step | Description | Reversible |
|------|-------------|------------|
| 1 | Create `boats` table (or repurpose existing) | DROP TABLE |
| 2 | Create supporting tables | DROP TABLEs |
| 3 | Add `results.boat_id` column | DROP COLUMN |
| 4 | Add indexes | DROP INDEXes |
| 5 | Backfill boats from results (dry run) | N/A |
| 6 | Backfill boats from results (real) | TRUNCATE |
| 7 | Link results to boats | SET NULL |
| 8 | Extract names and ownership | TRUNCATE |
| 9 | Generate conflicts | TRUNCATE |
| 10 | Deploy API changes | Rollback code |
| 11 | Deploy UI changes | Rollback code |

### 13.2 Test Cases

| Test | Expected Result |
|------|-----------------|
| Create boat from new result | boat_id returned, result linked |
| Match existing boat | Same boat_id, stats updated |
| Detect name conflict | Conflict created, result linked |
| Merge two boats | One boat remains, all results linked |
| Boat passport API | Complete JSON response |
| Class register API | List of boats with filters |
| Search by sail number | Matching boats returned |
| Status lifecycle | Active → Inactive after 3 years |

### 13.3 Acceptance Criteria

- [ ] All existing results have `boat_id` populated (where sail_number exists)
- [ ] No duplicate boats for same (sail, class)
- [ ] Boat passport page loads for any boat
- [ ] Boat register page loads with search/filters
- [ ] Conflicts flagged for review (not auto-resolved)
- [ ] Existing `/api/boat/*` endpoints unchanged
- [ ] No ranking calculation changes
- [ ] Rollback procedure verified

---

## Part 14: First Single-File Implementation Step (After Approval)

### Recommended First Step: Schema Migration Only

**File:** `/workspace/database/migrations/200_boat_register_schema.sql`

**Contents:**
- CREATE TABLE `boats` (if not repurposing existing)
- CREATE TABLE `boat_identifiers`
- CREATE TABLE `boat_names`
- CREATE TABLE `boat_ownership`
- CREATE TABLE `boat_match_log`
- CREATE TABLE `boat_conflicts`
- ALTER TABLE `results` ADD COLUMN `boat_id`
- CREATE INDEXes

**Why this first:**
1. Schema can be deployed without code changes
2. Existing production unaffected (nullable column)
3. Enables testing backfill in staging
4. Reversible via DROP statements

**NOT included in first step:**
- No Python code changes
- No API changes
- No UI changes
- No backfill execution
- No ranking changes

---

## Appendix A: Entity Separation Reference

### Proposed Entity Hierarchy

```
MANUFACTURER (future)
  └── BRAND (future)
       └── BOAT MODEL / HULL (future)
            └── PARENT HULL FAMILY (classes.parent_id)
                 └── CLASS (classes)
                      └── RIG VARIANT (class_aliases or future)
                           └── PHYSICAL BOAT (boats)
                                └── EVENT FLEET (fleet_label - contextual only)
```

### Current Implementation Focus

For Boat Register v1, focus on:
- **CLASS** → `classes` table (existing)
- **PHYSICAL BOAT** → `boats` table (new/enhanced)
- **EVENT FLEET** → `fleet_label` on results (existing, not part of boat identity)

Future tables (not in this plan):
- `manufacturers`
- `brands`
- `hull_models`
- `rig_variants`

---

## Appendix B: Confidence Score Calculations

### Identity Confidence (0-100)

```python
def calc_identity_confidence(boat: dict) -> int:
    score = 50  # Base
    
    # Positive signals
    if boat['events_count'] > 10: score += 20
    elif boat['events_count'] > 5: score += 10
    
    if boat['boat_name']: score += 10
    if has_single_owner(boat): score += 10
    if no_conflicts(boat): score += 10
    
    # Negative signals
    if has_name_variations(boat): score -= 10
    if has_owner_disputes(boat): score -= 15
    
    return min(100, max(0, score))
```

### Completeness Score (0-100)

```python
def calc_completeness_score(boat: dict) -> int:
    fields = {
        'sail_number': 20,
        'class_id': 20,
        'boat_name': 15,
        'owner': 15,
        'first_seen': 10,
        'last_seen': 10,
        'hull_metadata': 10
    }
    
    score = 0
    for field, weight in fields.items():
        if boat.get(field):
            score += weight
    
    return score
```

---

## Appendix C: Geographic Reconciliation

### Home Club Inference

```python
def infer_home_club(boat_id: int) -> tuple[int, int]:
    """
    Returns: (club_id, confidence)
    
    Rules:
    1. Club with most results for this boat
    2. If tie, most recent club
    3. If owner has club, prefer that
    """
    results = db.query("""
        SELECT r.club_id, COUNT(*) as count, MAX(reg.end_date) as last_seen
        FROM results r
        JOIN regattas reg ON reg.regatta_id = r.regatta_id
        WHERE r.boat_id = %s AND r.club_id IS NOT NULL
        GROUP BY r.club_id
        ORDER BY count DESC, last_seen DESC
    """, (boat_id,))
    
    if not results:
        return None, 0
    
    top = results[0]
    total = sum(r['count'] for r in results)
    confidence = int((top['count'] / total) * 100) if total > 0 else 0
    
    return top['club_id'], confidence
```

### Province/National Rollup

```
Club (club_id) → Province (clubs.province) → Country (ZA)
```

---

## Document End

**Status:** PLAN ONLY — No production changes made  
**Next Step:** Review with ChatGPT, then approve first migration step

---

*Generated by Cursor Cloud Agent audit on 2026-07-27*
