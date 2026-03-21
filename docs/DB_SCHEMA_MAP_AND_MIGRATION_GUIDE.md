# DB_SCHEMA_MAP_AND_MIGRATION_GUIDE

Purpose:
This document explains how the current SA Sailing database is structured, what each table is for, and how to migrate/normalize legacy data into the new schema.
It is designed specifically for Cursor AI so it can safely create, query, and update database objects without breaking existing Cascade functionality.

## 1. OVERVIEW
The database follows a normalized structure designed for import and sync with the official SAS data source.
Legacy data is imported into `legacy.*`, transformed into canonical `public.*` tables, and exposed via API views used by the Cascade frontend.

## 2. CORE PERSON TABLES
### public.sa_ids
| Column             | Type        | Description                                  |
|--------------------|-------------|----------------------------------------------|
| person_id          | SERIAL PK   | Internal ID                                  |
| sa_registry_no     | INT UNIQUE  | Official SAS number                          |
| id_status          | TEXT        | valid, temp, pending, etc                    |
| first_name         | TEXT        | Sailor’s given name                          |
| last_name          | TEXT        | Sailor’s surname                             |
| dob                | DATE        | Derived from YoB (01-Jan-YYYY if year only)  |
| home_club_code     | TEXT        | Link to `public.clubs`                       |
| created_at         | TIMESTAMP   | Record tracking                              |
| updated_at         | TIMESTAMP   | Record tracking                              |

- ✅ All sailors (past + present) live here.
- ⚙️ Populated by `102_transform_legacy_to_final.sql`.
- TEMP IDs are stored separately in `public.id_aliases`.

## 3. DICTIONARY TABLES
### public.clubs
Canonical club reference list.

| Column         | Type             | Description                     |
|----------------|------------------|---------------------------------|
| club_code      | TEXT PK          | Club short code                 |
| club_name      | TEXT             | Full club name                  |
| province_code  | TEXT FK → provinces | Province/region code        |
| is_active      | BOOLEAN DEFAULT true | Active flag                 |
| source         | TEXT             | `legacy_import` / `manual`      |
| verified_by    | TEXT             | QA tracking                     |
| verified_at    | TIMESTAMP        | QA tracking                     |

### public.club_aliases
| Column    | Type     | Description                 |
|-----------|----------|-----------------------------|
| alias     | TEXT     | Alternate club name         |
| club_code | TEXT FK  | Points to `public.clubs`    |

Same pattern applies to:
- `public.classes`
- `public.class_aliases`
- `public.provinces`
- `public.province_aliases`

➡️ Cursor must preserve all existing club and class codes, and only insert new rows if they don’t already exist (`ON CONFLICT DO NOTHING`).

## 4. REGATTA & RESULTS DATA
### public.regattas
| Column       | Type      | Description              |
|--------------|-----------|--------------------------|
| regatta_id   | SERIAL PK | Event ID                 |
| name         | TEXT      | Event name               |
| club_code    | TEXT FK → clubs | Host club         |
| start_date   | DATE      | Start date               |
| end_date     | DATE      | End date                 |
| province_code| TEXT FK → provinces | Region        |

### public.results
| Column       | Type      | Description                 |
|--------------|-----------|-----------------------------|
| result_id    | SERIAL PK | Race result row             |
| regatta_id   | INT FK → regattas | Event link        |
| class_code   | TEXT FK → classes | Boat class        |
| sail_number  | TEXT      | Boat sail number           |
| rank         | INT       | Race position              |
| club_raw     | TEXT      | Imported club name         |
| helm_sa_id   | TEXT      | Original SA ID for helm    |
| crew_sa_id   | TEXT      | Original SA ID for crew    |
| notes        | TEXT      | Comments                   |
| created_at   | TIMESTAMP | Timestamp                  |

### public.result_participants
| Column     | Type        | Description              |
|------------|-------------|--------------------------|
| result_id  | INT FK → results | Result row         |
| person_id  | INT FK → sa_ids  | Linked sailor      |
| role       | TEXT        | `helm` / `crew`          |

➡️ Created from transform script that uses `public.resolve_person_by_identifier()`.

## 5. QUALIFICATIONS & ROLES
### public.roles
List of qualification types.

| Column          | Type      | Description                                  |
|-----------------|-----------|----------------------------------------------|
| role_id         | SERIAL PK | Qualification/role identifier                |
| role_code       | TEXT      | `INSTRUCTOR`, `JUDGE`, `RIB_DRIVER`, etc     |
| role_name       | TEXT      | Display label                                |
| category        | TEXT      | `safety`, `training`, `admin`                |
| validity_years  | INT       | Typical expiry period                        |

### public.member_qualifications
| Column     | Type       | Description                 |
|------------|------------|-----------------------------|
| person_id  | INT FK → sa_ids | Sailor link          |
| role_id    | INT FK → roles  | Qualification type    |
| issued_at  | DATE       | Issue date                  |
| valid_to   | DATE       | Expiry date                 |
| status     | TEXT       | `valid` / `expired` / `pending` |

➡️ Used to track SAS certificates and revalidations. Cascade UI shows via `vw_member_qualifications_summary`.

## 6. SYSTEM TABLES
| Table                     | Description                    |
|--------------------------|--------------------------------|
| public.id_aliases        | TEMP or external ID mappings   |
| public.sa_registry_ledger| Audit of SAS ID assignments    |
| public.sa_registry_counter| Keeps highest SAS number      |

## 7. RELATIONSHIP MAP
```
sa_ids
 ├─< member_qualifications (by person_id)
 ├─< result_participants (by person_id)
 ├─< id_aliases (aliases for TEMP)
 └─< person_club_memberships (by person_id → club_code)

results
 ├─< result_participants
 └─< regattas (by regatta_id)

clubs ─< regattas
classes ─< results
provinces ─< clubs
roles ─< member_qualifications
```

## 8. DATA IMPORT PIPELINE (Cursor to Automate)
| Step | File / Script                     | Description                               |
|------|-----------------------------------|-------------------------------------------|
| 1️⃣  | `100_stage_schema.sql`            | Ensure `legacy.*` tables exist             |
| 2️⃣  | `legacy_load.sql`                 | Copy from old tables to staging           |
| 3️⃣  | `102_transform_legacy_to_final.sql` | Populate `public.sa_ids`                 |
| 4️⃣  | `122_legacy_club_class_import.sql` | Normalize clubs/classes                   |
| 5️⃣  | `123_transform_legacy_results.sql` | Build results + participants               |
| 6️⃣  | `124_seed_member_qualifications.sql` | Insert qualifications                    |
| 7️⃣  | `verify_audit.sql`                | Run all verification counts/views         |

## 9. AUDIT & QA VIEWS
| View                              | Purpose                                      |
|-----------------------------------|----------------------------------------------|
| `vw_sas_audit_summary`            | Shows totals (valid, missing, highest_no)    |
| `vw_member_qualifications_summary`| Expiry status of each qualification          |
| `vw_results_summary`              | Linked results (helm, crew, class)           |

## 10. RULES FOR CURSOR
- Never drop or rename any Cascade-created tables.
- Only create new `legacy.*` or `migration_*` scripts.
- Always use `ON CONFLICT DO NOTHING` when inserting into `public.*`.
- Always checksum counts before/after import.
- Don’t touch `dob` except to auto-fill `01-Jan-YYYY` for year-only values.
- When linking people to results, prefer in order:
  - `sa_sailing_id_int`
  - fallback: `sa_sailing_id` (numeric text only)
  - fallback: match by name if no ID

---

## 11. CLUBS AND CLUB ALIASES (Migration Plan)

### Purpose
Normalize club names and preserve legacy variants for stable joins.

### Final schema (public)
```sql
CREATE TABLE IF NOT EXISTS public.clubs (
  club_code   TEXT PRIMARY KEY,
  club_name   TEXT NOT NULL,
  province_code TEXT REFERENCES public.provinces(province_code),
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  source      TEXT,
  verified_by TEXT,
  verified_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.club_aliases (
  alias      TEXT PRIMARY KEY,
  club_code  TEXT NOT NULL REFERENCES public.clubs(club_code) ON DELETE CASCADE
);
```

### Mapping (legacy → public)
- Source candidates: `legacy.legacy_sas_id_personal` (columns like `club_1`, `home_club_code`) and any scraped club lists.
- Generate a canonical `club_code` (stable slug) when missing.

### Import (idempotent)
```sql
-- Seed clubs
INSERT INTO public.clubs (club_code, club_name, province_code, source)
SELECT DISTINCT
  COALESCE(NULLIF(TRIM(home_club_code), ''), lower(regexp_replace(club_1, '[^a-zA-Z0-9]+','_','g'))) AS club_code,
  INITCAP(TRIM(club_1)) AS club_name,
  NULL::text AS province_code,
  'legacy_import' AS source
FROM legacy.legacy_sas_id_personal
WHERE COALESCE(TRIM(club_1), TRIM(home_club_code)) IS NOT NULL
ON CONFLICT (club_code) DO NOTHING;

-- Alias map
INSERT INTO public.club_aliases (alias, club_code)
SELECT DISTINCT
  TRIM(club_1) AS alias,
  COALESCE(NULLIF(TRIM(home_club_code), ''), lower(regexp_replace(club_1, '[^a-zA-Z0-9]+','_','g'))) AS club_code
FROM legacy.legacy_sas_id_personal
WHERE TRIM(club_1) IS NOT NULL
ON CONFLICT (alias) DO NOTHING;
```

### Verification
```sql
SELECT COUNT(*) FROM public.clubs;
SELECT COUNT(*) FROM public.club_aliases;
SELECT alias, club_code FROM public.club_aliases ORDER BY alias LIMIT 20;
```

---

## 12. CLASSES AND CLASS ALIASES (Migration Plan)

### Purpose
Normalize boat class names and link results to canonical classes.

### Final schema (public)
```sql
CREATE TABLE IF NOT EXISTS public.classes (
  class_canonical TEXT PRIMARY KEY,
  class_full_name TEXT NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  source          TEXT,
  verified_by     TEXT
);

CREATE TABLE IF NOT EXISTS public.class_aliases (
  alias           TEXT PRIMARY KEY,
  class_canonical TEXT NOT NULL REFERENCES public.classes(class_canonical) ON DELETE CASCADE
);
```

### Mapping (legacy → public)
- Source candidates: legacy results tables with free-text class fields (e.g., `legacy.legacy_results_new.class_raw`).
- Build a mapping table from frequent raw names → canonical.

### Import (idempotent)
```sql
-- Seed classes
INSERT INTO public.classes (class_canonical, class_full_name, source)
SELECT DISTINCT
  lower(regexp_replace(class_raw, '[^a-zA-Z0-9]+','_','g')) AS class_canonical,
  INITCAP(TRIM(class_raw)) AS class_full_name,
  'legacy_import'
FROM legacy.legacy_results_new
WHERE TRIM(class_raw) IS NOT NULL
ON CONFLICT (class_canonical) DO NOTHING;

-- Alias map
INSERT INTO public.class_aliases (alias, class_canonical)
SELECT DISTINCT
  TRIM(class_raw) AS alias,
  lower(regexp_replace(class_raw, '[^a-zA-Z0-9]+','_','g')) AS class_canonical
FROM legacy.legacy_results_new
WHERE TRIM(class_raw) IS NOT NULL
ON CONFLICT (alias) DO NOTHING;
```

### Verification
```sql
SELECT COUNT(*) FROM public.classes;
SELECT COUNT(*) FROM public.class_aliases;
```

---

## 13. REGATTAS (Migration Plan)

### Purpose
Canonical registry of events. Links results to event metadata.

### Final schema (public)
```sql
CREATE TABLE IF NOT EXISTS public.regattas (
  regatta_id   SERIAL PRIMARY KEY,
  name         TEXT NOT NULL,
  club_code    TEXT REFERENCES public.clubs(club_code),
  start_date   DATE,
  end_date     DATE,
  province_code TEXT REFERENCES public.provinces(province_code),
  source       TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);
```

### Mapping (legacy → public)
- Source: legacy regatta tables or fields in `legacy.legacy_results_new` (event name/date spans).
- Deduplicate by normalized `name + date range`.

### Import (idempotent)
```sql
INSERT INTO public.regattas (name, club_code, start_date, end_date, province_code, source)
SELECT DISTINCT
  INITCAP(TRIM(event_name)) AS name,
  NULL::text AS club_code,
  MIN(race_date)::date AS start_date,
  MAX(race_date)::date AS end_date,
  NULL::text AS province_code,
  'legacy_import' AS source
FROM legacy.legacy_results_new
GROUP BY INITCAP(TRIM(event_name))
ON CONFLICT DO NOTHING;
```

### Verification
```sql
SELECT COUNT(*) FROM public.regattas;
SELECT name, start_date, end_date FROM public.regattas ORDER BY start_date DESC LIMIT 10;
```

---

## 14. RESULTS AND PARTICIPANTS (Migration Plan)

### Purpose
Store per-race entries and associate sailors as helm/crew.

### Final schema (public)
```sql
CREATE TABLE IF NOT EXISTS public.results (
  result_id   SERIAL PRIMARY KEY,
  regatta_id  INT REFERENCES public.regattas(regatta_id) ON DELETE CASCADE,
  class_code  TEXT REFERENCES public.classes(class_canonical),
  sail_number TEXT,
  rank        INT,
  club_raw    TEXT,
  notes       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.result_participants (
  result_id  INT NOT NULL REFERENCES public.results(result_id) ON DELETE CASCADE,
  person_id  INT NOT NULL REFERENCES public.sa_ids(person_id) ON DELETE RESTRICT,
  role       TEXT NOT NULL CHECK (role IN ('helm','crew')),
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (result_id, person_id, role)
);
```

### Mapping (legacy → public)
- Resolve class via `class_aliases`.
- Resolve people via preferred order:
  1) numeric SA ID field (`sa_sailing_id_int`)
  2) numeric text SA ID (`sa_sailing_id`)
  3) fallback name-matching (only where no ID present)

### Import (idempotent)
```sql
-- Results rows
INSERT INTO public.results (regatta_id, class_code, sail_number, rank, club_raw, notes)
SELECT
  r.regatta_id,
  c.class_canonical,
  lr.sail_no,
  lr.rank,
  lr.club_raw,
  NULL
FROM legacy.legacy_results_new lr
JOIN public.regattas r ON r.name = INITCAP(TRIM(lr.event_name))
LEFT JOIN public.class_aliases ca ON ca.alias = TRIM(lr.class_raw)
LEFT JOIN public.classes c ON c.class_canonical = COALESCE(ca.class_canonical, lower(regexp_replace(lr.class_raw,'[^a-zA-Z0-9]+','_','g')))
ON CONFLICT DO NOTHING;

-- Participants
-- Example: helm by exact SA ID where available
INSERT INTO public.result_participants (result_id, person_id, role)
SELECT res.result_id, s.person_id, 'helm'
FROM legacy.legacy_results_new lr
JOIN public.results res ON res.sail_number = lr.sail_no AND res.rank = lr.rank
JOIN public.sa_ids s ON s.sa_registry_no = lr.helm_sa_id_int
ON CONFLICT DO NOTHING;
```

### Verification
```sql
SELECT COUNT(*) FROM public.results;
SELECT COUNT(*) FROM public.result_participants;
SELECT * FROM public.results ORDER BY result_id DESC LIMIT 10;
```

---

## 15. ROLES AND MEMBER QUALIFICATIONS (Migration Plan)

### Purpose
Separate catalogue of role types and issued qualifications per sailor.

### Final schema (public)
```sql
-- Roles catalogue (idempotent)
CREATE TABLE IF NOT EXISTS public.roles (
  role_code  TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  category   TEXT NOT NULL
);

-- Person qualifications
CREATE TABLE IF NOT EXISTS public.member_qualifications (
  qual_id     SERIAL PRIMARY KEY,
  person_id   BIGINT NOT NULL REFERENCES public.sa_ids(person_id) ON DELETE CASCADE,
  role_code   TEXT   NOT NULL REFERENCES public.roles(role_code) ON DELETE CASCADE,
  issued_at   DATE,
  valid_to    DATE,
  status      TEXT CHECK (status IN ('valid','expired','revoked','pending')) DEFAULT 'valid',
  verified_by TEXT,
  notes       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(person_id, role_code, issued_at)
);
```

### Backfill (optional)
```sql
INSERT INTO public.member_qualifications (person_id, role_code, issued_at, valid_to, status)
SELECT mr.person_id, mr.role_code, mr.valid_from, mr.valid_to,
       CASE WHEN mr.valid_to IS NOT NULL AND mr.valid_to < CURRENT_DATE THEN 'expired' ELSE 'valid' END
FROM public.member_roles mr
ON CONFLICT DO NOTHING;
```

### Views (for API/UI)
```sql
CREATE OR REPLACE VIEW public.vw_member_qualifications AS
SELECT
  q.qual_id,
  i.person_id,
  i.sa_registry_no,
  i.first_name,
  i.last_name,
  r.role_code,
  r.name AS role_name,
  r.category,
  q.issued_at,
  q.valid_to,
  q.status,
  q.verified_by
FROM public.member_qualifications q
JOIN public.sa_ids i ON i.person_id = q.person_id
JOIN public.roles r  ON r.role_code = q.role_code;

CREATE OR REPLACE VIEW public.vw_qualifications_stats AS
SELECT
  r.role_code,
  r.name AS role_name,
  COUNT(*) FILTER (WHERE q.status='valid')   AS active_count,
  COUNT(*) FILTER (WHERE q.status='expired') AS expired_count,
  COUNT(*)                                   AS total_count
FROM public.member_qualifications q
JOIN public.roles r ON r.role_code = q.role_code
GROUP BY r.role_code, r.name
ORDER BY r.name;
```

### Verification
```sql
SELECT COUNT(*) AS total_quals, COUNT(DISTINCT person_id) AS members_with_quals FROM public.member_qualifications;
TABLE public.vw_member_qualifications LIMIT 10;
TABLE public.vw_qualifications_stats;
```

---

## Part 2 — Cursor-Ready Domain Specs (Verbatim)

### 11. Clubs & Aliases
Purpose:
Canonical list of SA Sailing clubs; provides clean join targets for sailors and regattas.

```sql
CREATE TABLE IF NOT EXISTS public.clubs (
  club_id SERIAL PRIMARY KEY,
  club_code TEXT UNIQUE,
  club_name TEXT NOT NULL,
  province TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  source TEXT,
  verified_by TEXT,
  verified_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.club_aliases (
  alias TEXT PRIMARY KEY,
  club_code TEXT NOT NULL REFERENCES public.clubs(club_code) ON DELETE CASCADE
);
```

Mapping (legacy → new):
```sql
INSERT INTO public.clubs (club_code, club_name)
SELECT DISTINCT COALESCE(home_club_code, club_1), club_1
FROM legacy.legacy_sas_id_personal
WHERE club_1 IS NOT NULL;

INSERT INTO public.club_aliases (alias, club_code)
SELECT DISTINCT club_1, home_club_code
FROM legacy.legacy_sas_id_personal
WHERE home_club_code IS NOT NULL AND club_1 IS NOT NULL;
```

Relations:
- `public.sa_ids.home_club_code → public.clubs.club_code`
- `public.regattas.host_club → public.clubs.club_code`

### 12. Classes & Aliases
Purpose:
Normalizes boat classes and alternate labels appearing in regatta results.

```sql
CREATE TABLE IF NOT EXISTS public.classes (
  class_id SERIAL PRIMARY KEY,
  class_code TEXT UNIQUE,
  class_name TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  source TEXT,
  verified_by TEXT,
  verified_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.class_aliases (
  alias TEXT PRIMARY KEY,
  class_code TEXT NOT NULL REFERENCES public.classes(class_code) ON DELETE CASCADE
);
```

Mapping:
```sql
INSERT INTO public.classes (class_code, class_name)
SELECT DISTINCT LOWER(TRIM(class_name)), INITCAP(class_name)
FROM legacy.legacy_results_new
WHERE class_name IS NOT NULL;
```

Relations:
- `public.regattas.class_code → public.classes.class_code`
- `public.results.class_code → public.classes.class_code`

### 13. Regattas & Blocks
Purpose:
Stores metadata for every event (title, host, date range).

```sql
CREATE TABLE IF NOT EXISTS public.regattas (
  regatta_id SERIAL PRIMARY KEY,
  regatta_name TEXT NOT NULL,
  host_club TEXT REFERENCES public.clubs(club_code),
  province TEXT,
  start_date DATE,
  end_date DATE,
  status TEXT DEFAULT 'verified',
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.regatta_blocks (
  block_id SERIAL PRIMARY KEY,
  regatta_id INT REFERENCES public.regattas(regatta_id) ON DELETE CASCADE,
  class_code TEXT REFERENCES public.classes(class_code),
  race_count INT,
  entries_count INT,
  notes TEXT
);
```

Mapping:
```sql
INSERT INTO public.regattas (regatta_name, host_club, start_date, end_date, province)
SELECT DISTINCT regatta_name, club_code, start_date, end_date, province
FROM legacy.legacy_results_new;
```

### 14. Results & Participants
Purpose:
Holds per-race outcomes and links sailors (via sa_ids) to regattas.

```sql
CREATE TABLE IF NOT EXISTS public.results (
  result_id SERIAL PRIMARY KEY,
  regatta_id INT REFERENCES public.regattas(regatta_id) ON DELETE CASCADE,
  class_code TEXT REFERENCES public.classes(class_code),
  sa_sailing_id TEXT,
  helm_sa_id TEXT,
  crew_sa_id TEXT,
  position INT,
  total_points NUMERIC,
  race_data JSONB,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS public.result_participants (
  result_id INT REFERENCES public.results(result_id) ON DELETE CASCADE,
  person_id INT REFERENCES public.sa_ids(person_id) ON DELETE CASCADE,
  role TEXT CHECK (role IN ('helm','crew')),
  PRIMARY KEY (result_id, person_id, role)
);
```

Migration sample:
```sql
INSERT INTO public.results (regatta_id, class_code, sa_sailing_id, position, total_points)
SELECT r.regatta_id, lr.class_name, lr.sa_sailing_id, lr.rank, lr.total_points
FROM legacy.legacy_results_new lr
JOIN public.regattas r ON r.regatta_name = lr.regatta_name;

-- Link numeric SA IDs to persons
INSERT INTO public.result_participants (result_id, person_id, role)
SELECT res.result_id, p.person_id, 'helm'
FROM public.results res
JOIN public.sa_ids p ON p.sa_registry_no::text = res.sa_sailing_id
ON CONFLICT DO NOTHING;
```

### 15. Roles & Member Roles
Purpose:
Stores qualifications and their assignment to members.

```sql
CREATE TABLE IF NOT EXISTS public.roles (
  role_id SERIAL PRIMARY KEY,
  role_code TEXT UNIQUE,
  role_name TEXT NOT NULL,
  category TEXT,
  requires_renewal BOOLEAN DEFAULT FALSE,
  valid_years INT DEFAULT 3,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.member_roles (
  person_id INT REFERENCES public.sa_ids(person_id) ON DELETE CASCADE,
  role_id INT REFERENCES public.roles(role_id) ON DELETE CASCADE,
  status TEXT CHECK (status IN ('valid','expired','pending')),
  valid_from DATE,
  valid_to DATE,
  issued_by TEXT,
  notes TEXT,
  PRIMARY KEY (person_id, role_id)
);
```

Examples:
```sql
-- populate roles dictionary
INSERT INTO public.roles (role_code, role_name, category)
VALUES
  ('SAFETY_OFF','Safety Officer','Safety'),
  ('COACH_L1','Coach Level 1','Coaching'),
  ('MEASURER','Class Measurer','Technical')
ON CONFLICT DO NOTHING;

-- example assignment
INSERT INTO public.member_roles (person_id, role_id, status, valid_from, valid_to)
SELECT p.person_id, r.role_id, 'valid', '2024-01-01', '2026-01-01'
FROM public.sa_ids p
JOIN public.roles r ON r.role_code='COACH_L1'
WHERE p.sa_registry_no=12345;
```

Relations:
- `public.member_roles.person_id → public.sa_ids.person_id`
- `public.member_roles.role_id → public.roles.role_id`

✅ Next Step
You can now give this full schema guide to Cursor with the instruction:
“Use this DB schema map as authoritative. Create or update any missing tables exactly as defined. Populate new tables from the existing legacy or scraped data sources as mapped.”


---

## 16. Relationships Overview (Entity Map)

### Core Links
| From (Table.Column) | → To (Table.Column) | Purpose |
|---------------------|---------------------|---------|
| `public.sa_ids.home_club_code` | `public.clubs.club_code` | each sailor’s home club |
| `public.regattas.host_club` | `public.clubs.club_code` | regatta venue |
| `public.regatta_blocks.class_code` | `public.classes.class_code` | class sailed at event |
| `public.results.class_code` | `public.classes.class_code` | result’s boat class |
| `public.results.regatta_id` | `public.regattas.regatta_id` | which regatta |
| `public.result_participants.person_id` | `public.sa_ids.person_id` | sailor(s) in a result |
| `public.member_roles.person_id` | `public.sa_ids.person_id` | qualifications owned |
| `public.member_roles.role_id` | `public.roles.role_id` | qualification type |
| `public.id_aliases.person_id` | `public.sa_ids.person_id` | TMP / legacy mappings |
| `public.sa_registry_ledger.registry_no` | `public.sa_registry_counter.last_no` | next-ID tracking |


## 17. Audit & QA Views

### `vw_sas_audit_summary`
Purpose: drives Finder header and `/api/sa-id-stats`.

```sql
CREATE OR REPLACE VIEW public.vw_sas_audit_summary AS
SELECT
  (SELECT COUNT(*) FROM public.sa_ids WHERE id_status='valid')                        AS total_valid,
  (SELECT MAX(sa_registry_no) FROM public.sa_ids WHERE id_status='valid')            AS highest_no,
  GREATEST(
     COALESCE((SELECT MAX(sa_registry_no) FROM public.sa_ids WHERE id_status='valid'),0)
     - COALESCE((SELECT COUNT(*) FROM public.sa_ids WHERE id_status='valid'),0),
     0
  ) AS missing_count;
```

### `vw_result_integrity`
Purpose: detect orphaned or inconsistent race data.

```sql
CREATE OR REPLACE VIEW public.vw_result_integrity AS
SELECT
  r.result_id,
  r.regatta_id,
  r.class_code,
  r.sa_sailing_id,
  CASE
    WHEN p.person_id IS NULL THEN 'missing_person'
    WHEN r.class_code IS NULL THEN 'missing_class'
    WHEN r.regatta_id IS NULL THEN 'missing_regatta'
    ELSE 'ok'
  END AS integrity_status
FROM public.results r
LEFT JOIN public.sa_ids p ON p.sa_registry_no::text = r.sa_sailing_id;
```

### `vw_role_expiry_check`
Purpose: flag expired or near-expiry qualifications.

```sql
CREATE OR REPLACE VIEW public.vw_role_expiry_check AS
SELECT
  mr.person_id,
  r.role_name,
  mr.valid_to,
  CASE
    WHEN mr.valid_to < CURRENT_DATE THEN 'expired'
    WHEN mr.valid_to < CURRENT_DATE + INTERVAL '90 days' THEN 'expiring_soon'
    ELSE 'valid'
  END AS expiry_status
FROM public.member_roles mr
JOIN public.roles r ON r.role_id = mr.role_id;
```


## 18. Counters & Triggers

Purpose: keep `sa_registry_counter` synchronized with actual maximum ID.

```sql
CREATE OR REPLACE FUNCTION public.sync_sa_registry_counter() RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.sa_registry_counter
  SET last_no = GREATEST(
    last_no,
    (SELECT COALESCE(MAX(sa_registry_no),0) FROM public.sa_ids)
  )
  WHERE id = 1;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_counter_after_insert
AFTER INSERT ON public.sa_ids
FOR EACH STATEMENT
EXECUTE FUNCTION public.sync_sa_registry_counter();
```


## 19. Validation Queries for Cursor QA

```sql
-- sanity counts
SELECT COUNT(*) AS sailors FROM public.sa_ids;
SELECT COUNT(*) AS clubs FROM public.clubs;
SELECT COUNT(*) AS classes FROM public.classes;
SELECT COUNT(*) AS regattas FROM public.regattas;
SELECT COUNT(*) AS results FROM public.results;

-- integrity checks
TABLE public.vw_sas_audit_summary;
TABLE public.vw_result_integrity;
TABLE public.vw_role_expiry_check;

-- counter alignment
SELECT (SELECT MAX(sa_registry_no) FROM public.sa_ids) AS max_no,
       (SELECT last_no FROM public.sa_registry_counter WHERE id=1) AS counter_no;
```


## 20. API & UI Dependence Summary

| API Endpoint | Backing View/Table | Shown In |
|--------------|--------------------|----------|
| `/api/sa-id-stats` | `vw_sas_audit_summary` | Finder header (“Latest • Total • Missing”) |
| `/api/result/attach-person` | `result_participants` + `id_aliases` | result-entry UI |
| `/api/id/promote` | `sa_registry_counter`, `sa_registry_ledger` | TMP → real SAS workflow |
| `/api/role-status` (planned) | `vw_role_expiry_check` | member-profile badges |

 ✅ Next Step:
 Tell Cursor →
 “Sync DB to this global schema (Parts 1–3).
 Ensure all tables, views, and triggers exist.
 Populate clubs, classes, regattas, results, and roles from legacy or scraped sources as mapped.”


---

## 21. Migration & Seeding Order (Run-book)

Each stage has a single responsibility: create → populate → validate.

| #Phase | Source | Target | Purpose |
|--------|--------|--------|---------|
| 1 | Stage Schemas — | legacy.* | Create holding tables from old system |
| 2 | Import SA IDs | legacy.legacy_sas_id_personal | public.sa_ids, public.id_aliases, public.sa_registry_ledger, public.sa_registry_counter | Load all sailor records first |
| 3 | Import Clubs | legacy.legacy_clubs | public.clubs | Master club list for linking |
| 4 | Import Classes | legacy.legacy_classes | public.classes | All boat classes used in regattas |
| 5 | Import Regattas & Blocks | legacy.legacy_regattas, legacy.legacy_blocks | public.regattas, public.regatta_blocks | Event metadata |
| 6 | Import Results | legacy.legacy_results_new | public.results, public.result_participants | Race outcomes + linked sailors |
| 7 | Import Qualifications | legacy.legacy_roles, legacy.legacy_member_roles | public.roles, public.member_roles | Populate qualification types + assignments |
| 8 | Final Integrity Checks — | Views vw_sas_audit_summary, vw_result_integrity, vw_role_expiry_check | Verify cross-table consistency |

## 22. Seed Templates

Cursor should create small CSV/SQL seed files per table so you can test with minimal data before full import.

Example `public.clubs_seed.csv`

    club_code,club_name,province,is_active
    HYC,Hermanus Yacht Club,WC,true
    ZVYC,ZVYC,WC,true

Example `public.classes_seed.csv`

    class_code,class_name,is_active
    OPT,Optimist,true
    ILCA,ILCA 6,true
    420,420,true

Example `public.roles_seed.csv`

    role_name,role_type,description,is_active
    Safety Officer,Qualification,Certified Safety Officer,true
    Race Officer,Qualification,Race Management,true
    Coach Level 1,Qualification,SAS Coaching Level 1,true

Cursor can load these with:

    psql -d sa_portal_dev -c "\copy public.clubs FROM 'seed/clubs_seed.csv' CSV HEADER"

## 23. Safe Execution Order (Cursor Tasks)

    # 1️⃣ Ensure baseline
    bash admin/tools/migrate.sh

    # 2️⃣ Import SA IDs
    bash admin/import_stage_sas.sh

    # 3️⃣ Import reference dictionaries
    bash admin/import_stage_clubs.sh
    bash admin/import_stage_classes.sh

    # 4️⃣ Import events + results
    bash admin/import_stage_regattas.sh
    bash admin/import_stage_results.sh

    # 5️⃣ Import roles + assignments
    bash admin/import_stage_roles.sh
    bash admin/import_stage_member_roles.sh

    # 6️⃣ Run QA
    psql -d sa_portal_dev -f qa/verify_integrity.sql

## 24. Data Integrity Rules (Cursor Must Keep)

- **[one_person_one_id]** 1 SA ID = 1 person: unique `sa_registry_no`.
- **[dict_first]** Clubs and Classes must exist before `regattas`/`results` insert.
- **[results_fk]** Results must link to existing `regatta` + `class` + `sa_id`.
- **[roles_fk]** Roles must exist before `member_roles` insert.
- **[on_error]** Foreign key errors: log → `legacy.legacy_conflicts`.
- **[skip_and_log]** On fail: skip row and record in `legacy_conflicts`.

## 25. Post-Import QA Checklist

| Check | Expected |
|-------|----------|
| `vw_sas_audit_summary.total_valid` | > 0 ✅ |
| `vw_result_integrity.integrity_status` | 'ok' ✅ |
| `vw_role_expiry_check.expiry_status` | Mostly 'valid' |
| clubs & classes non-empty | ✅ |
| Counter alignment (`max_no = counter_no`) | ✅ |

---

## 21. Final Instruction for Cursor

**Objective:**
Finalize database build for `sa_portal_dev` by creating all required new tables, mapping data from the old source tables (`public.sas_id_personal`, `public.results`, `public.clubs`, `public.classes`, etc.), and running all transforms so the platform is live and queryable by the API.

**Step 1 – Confirm and Align Schema**

    psql -d sa_portal_dev -v ON_ERROR_STOP=1 -f database/migrations/100_stage_schema.sql

Then, in order:

    102_transform_legacy_to_final.sql
    103_roles_init.sql
    105_member_roles_indexes.sql
    108_add_home_club_code.sql
    109_dictionaries_provinces.sql
    110_dictionary_suggestions.sql
    112_legacy_schema_coverage.sql
    113_temp_id_workflow.sql
    114_sa_ids_hardening.sql

(Use `bash admin/tools/migrate.sh` to apply all automatically.)

**Step 2 – Import from Old Data**

Cursor should pull directly from the old database tables (already checksummed) into staging `legacy.*` schemas, then transform.

For example:

    TRUNCATE legacy.legacy_sas_id_personal;

    INSERT INTO legacy.legacy_sas_id_personal (
      sa_sailing_id, first_name, given_names, last_name, surname,
      date_of_birth, year_of_birth, home_club_code, club_1, email,
      created_at, updated_at
    )
    SELECT
      COALESCE(sa_sailing_id_int, sa_sailing_id::int) AS sa_sailing_id,
      first_name,
      NULL AS given_names,
      last_name,
      last_name AS surname,
      NULL::date AS date_of_birth,
      year_of_birth,
      NULL::text AS home_club_code,
      club_1,
      NULL::text AS email,
      NULL::timestamp AS created_at,
      NULL::timestamp AS updated_at
    FROM public.sas_id_personal;

Then:

    psql -d sa_portal_dev -v ON_ERROR_STOP=1 -f database/migrations/102_transform_legacy_to_final.sql
    psql -d sa_portal_dev -c "TABLE public.vw_sas_audit_summary;"

**Step 3 – Create & Populate Supporting Tables**

Cursor must now check whether these exist and populate if empty:

| Table | Purpose | Source |
|-------|---------|--------|
| `public.clubs` | All sailing clubs in SA | old clubs or `results.club_1` distinct |
| `public.classes` | Boat classes (Optimist, 420, etc.) | old `results.class` |
| `public.regattas` | Regatta meta info (name, club, dates) | old results headers |
| `public.results` | Individual race results per regatta | old results tables |
| `public.roles` | Qualification and certification types | new seed file or legacy system |
| `public.member_roles` | Mapping of SA IDs to roles/quals | link to `public.sa_ids` |
| `public.person_class_affiliations` | Which sailors belong to which classes | derived from results and class tables |
| `public.person_club_memberships` | Which sailors are members of which clubs | derived from `results.club_1` or member records |

Cursor must automatically infer the mappings by column name similarity (`club_1` → `club_name`, `class` → `boat_class`, etc.). If a column doesn’t exist, create it with appropriate type (usually TEXT, INT, or TIMESTAMPTZ).

**Step 4 – Data Verification**

    -- Verify SAS IDs imported
    SELECT COUNT(*) FROM public.sa_ids WHERE id_status='valid';

    -- Verify unique count matches legacy checksum
    SELECT COUNT(DISTINCT sa_registry_no) FROM public.sa_ids;

    -- Verify club + class tables have entries
    SELECT COUNT(*) FROM public.clubs;
    SELECT COUNT(*) FROM public.classes;

    -- Verify linkage of results to SA IDs
    SELECT COUNT(*) FROM public.result_participants;

**Step 5 – API Verification**

    uvicorn api:app --host 0.0.0.0 --port 8082 --reload
    curl -s http://localhost:8082/api/sa-id-stats

✅ Output should show valid `highest_no`, `total_valid`, and `missing_count`.

**Final Deliverables**

Cursor should:
- Confirm all new tables exist and contain data.
- Report total rows imported for each.
- Commit final migrations with tag:

    git tag -a v1.0-schema-sync-complete -m "Legacy DB fully migrated to sa_portal_dev"
    git push origin v1.0-schema-sync-complete

---

## 26. MASTER EXECUTION BRIEF — SA PORTAL DATABASE FINALIZATION

**Objective:**
Fully build and synchronize `sa_portal_dev` by creating, aligning, and populating all tables from the legacy SA Sailing database (checked against sailing.org).
Cascade has already handled API + HTML integration. Cursor must now handle schema creation, migration execution, and data import/transformation from legacy tables.

**CORE PIPELINE SUMMARY**

- **Schemas in use:**
  - `public` → live/production tables for API
  - `legacy` → staging buffer for old data import
  - `support` → internal helpers (views, counters, functions)
- **Primary tables already defined:**
  - `public.sa_ids` — master list of sailors
  - `public.id_aliases` — alt IDs and TMP mapping
  - `public.sa_registry_ledger` — SAS number ledger
  - `public.sa_registry_counter` — registry auto-counter
  - `legacy.legacy_sas_id_personal` — staging for old sas_id_personal
  - `public.results`, `public.classes`, `public.clubs`, `public.roles`, `public.member_roles`, `public.person_club_memberships`, `public.person_class_affiliations`
- **Goal:**
  - All `public` tables must be populated from the corresponding legacy sources.
  - Transformations must preserve row number = SAS, no duplicates, and keep year_of_birth logic intact (DOB = YYYY-01-01 placeholder).

**STEP 1 — RUN ALL MIGRATIONS (BASE STRUCTURE)**

Run once from project root:

    bash admin/tools/migrate.sh

This applies:

    100_stage_schema.sql
    102_transform_legacy_to_final.sql
    103_roles_init.sql
    105_member_roles_indexes.sql
    108_add_home_club_code.sql
    109_dictionaries_provinces.sql
    110_dictionary_suggestions.sql
    112_legacy_schema_coverage.sql
    113_temp_id_workflow.sql
    114_sa_ids_hardening.sql

All NOTICE: already exists messages are normal — continue.

**STEP 2 — IMPORT LEGACY SA-IDS**

    psql -d sa_portal_dev -v ON_ERROR_STOP=1 -c "TRUNCATE legacy.legacy_sas_id_personal;"

    psql -d sa_portal_dev -v ON_ERROR_STOP=1 <<'SQL'
    INSERT INTO legacy.legacy_sas_id_personal (
      sa_sailing_id, first_name, given_names, last_name, surname,
      date_of_birth, year_of_birth, home_club_code, club_1, email,
      created_at, updated_at
    )
    SELECT
      COALESCE(sa_sailing_id_int, sa_sailing_id::int) AS sa_sailing_id,
      first_name,
      NULL AS given_names,
      last_name,
      last_name AS surname,
      NULL::date AS date_of_birth,
      year_of_birth,
      NULL::text AS home_club_code,
      club_1,
      NULL::text AS email,
      NULL::timestamp AS created_at,
      NULL::timestamp AS updated_at
    FROM public.sas_id_personal;
    SQL

    psql -d sa_portal_dev -v ON_ERROR_STOP=1 -f database/migrations/102_transform_legacy_to_final.sql
    psql -d sa_portal_dev -c "TABLE public.vw_sas_audit_summary;"

✅ Confirms: valid IDs imported, counter updated, ledger written.

**STEP 3 — CREATE AND POPULATE SUPPORTING TABLES**

1) Clubs

    INSERT INTO public.clubs (club_code, club_name)
    SELECT DISTINCT
      LOWER(REPLACE(club_1, ' ', '_')) AS club_code,
      club_1 AS club_name
    FROM public.sas_id_personal
    WHERE club_1 IS NOT NULL
    ON CONFLICT (club_code) DO NOTHING;

2) Classes

    INSERT INTO public.classes (class_canonical, class_full_name)
    SELECT DISTINCT
      LOWER(REPLACE(class, ' ', '_')) AS class_canonical,
      class AS class_full_name
    FROM public.results
    WHERE class IS NOT NULL
    ON CONFLICT (class_canonical) DO NOTHING;

3) Regattas + Results

- `public.regattas`: from results.regatta_id, event_id, or header fields.
- `public.results`: full per-race record.
- `public.result_participants`: link SAS to helm/crew using:

    INSERT INTO public.result_participants (result_id, person_id, role)
    SELECT r.result_id, s.person_id, 'helm'
    FROM public.results r
    JOIN public.sa_ids s ON s.sa_registry_no::text = r.helm_sa_id::text
    WHERE r.helm_sa_id IS NOT NULL
    ON CONFLICT DO NOTHING;

    INSERT INTO public.result_participants (result_id, person_id, role)
    SELECT r.result_id, s.person_id, 'crew'
    FROM public.results r
    JOIN public.sa_ids s ON s.sa_registry_no::text = r.crew_sa_id::text
    WHERE r.crew_sa_id IS NOT NULL
    ON CONFLICT DO NOTHING;

4) Roles + Member Roles (Qualifications)

    INSERT INTO public.roles (role_code, role_name, description)
    VALUES
      ('safety_officer','Safety Officer','SA Sailing Vessel Safety qualification'),
      ('coach_lvl1','Coach Level 1','SA Sailing coaching qualification'),
      ('race_officer','Race Officer','Official race officer accreditation'),
      ('measurer','Measurer','Class measurer qualification')
    ON CONFLICT (role_code) DO NOTHING;

    INSERT INTO public.member_roles (person_id, role_id, valid_from, valid_to, status)
    SELECT s.person_id, r.role_id, NULL, NULL, 'unknown'
    FROM public.sa_ids s
    CROSS JOIN public.roles r
    ON CONFLICT DO NOTHING;

**STEP 4 — VERIFY DATA INTEGRITY**

    SELECT COUNT(*) AS total_sailors FROM public.sa_ids;
    SELECT COUNT(*) AS total_clubs FROM public.clubs;
    SELECT COUNT(*) AS total_classes FROM public.classes;
    SELECT COUNT(*) AS total_results FROM public.results;
    SELECT COUNT(*) AS total_roles FROM public.roles;
    SELECT COUNT(*) AS total_member_roles FROM public.member_roles;
    SELECT * FROM public.vw_sas_audit_summary;

**STEP 5 — RUN AND VERIFY API**

    uvicorn api:app --host 0.0.0.0 --port 8082 --reload
    curl -s http://localhost:8082/api/sa-id-stats

Expected JSON:

    {
      "latest": 277700,
      "total_valid": <count>,
      "missing": <count>
    }

**FINAL TASK**

After data loads and API verifies, commit and tag:

    git add database/migrations/*
    git commit -m "Complete legacy migration and data alignment for sa_portal_dev"
    git tag -a v1.0-schema-sync-complete -m "Legacy DB fully migrated to sa_portal_dev"
    git push origin main --tags

**SUCCESS CRITERIA**

- All public tables populated with correct row counts.
- `/api/sa-id-stats` shows real totals.
- Finder header updates with latest counts.
- No schema or transform errors.
- Tag `v1.0-schema-sync-complete` created successfully.
