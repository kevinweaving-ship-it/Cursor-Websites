-- Production apply: class_id 8 canonical name becomes ILCA 4.
-- Historical spellings stay aliases. class_original, block_id, regatta_id stay.
-- Does not insert classes or results. Does not touch ILCA 6 or ILCA 7.
-- Aborts if more than one class matches, or a family label is tied to another class_id.

BEGIN;
SET LOCAL client_min_messages TO ERROR;

CREATE OR REPLACE FUNCTION pg_temp.ilca4_spaced(t text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
  SELECT lower(trim(regexp_replace(
    regexp_replace(replace(coalesce(t, ''), ',', '.'), '\s+fleet$', '', 'i'),
    '\s+', ' ', 'g'
  )));
$$;

CREATE OR REPLACE FUNCTION pg_temp.ilca4_compact(t text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
  SELECT regexp_replace(pg_temp.ilca4_spaced(t), '[^a-z0-9]', '', 'g');
$$;

CREATE OR REPLACE FUNCTION pg_temp.ilca4_family(t text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
  SELECT pg_temp.ilca4_spaced(t) NOT IN (
        'ilca', 'ilca 6', 'ilca 7', 'laser', 'laser radial', 'laser standard', 'radial'
      )
    AND pg_temp.ilca4_compact(t) NOT IN (
        'ilca', 'ilca6', 'ilca7', 'laser', 'laserradial', 'laserstandard', 'radial'
      )
    AND (
      pg_temp.ilca4_spaced(t) IN ('ilca 4', 'ilca 4.7', 'laser 4', 'laser 4.7', 'laser radial 4.7')
      OR pg_temp.ilca4_compact(t) IN ('ilca4', 'ilca47', 'laser4', 'laser47', 'laserradial47')
    );
$$;

DO $$
DECLARE
  n int;
  detail text;
BEGIN
  CREATE TEMP TABLE ilca4_hits ON COMMIT DROP AS
  SELECT DISTINCT c.class_id, c.class_name
  FROM public.classes c
  LEFT JOIN public.class_aliases a ON a.class_id = c.class_id
  WHERE pg_temp.ilca4_family(c.class_name)
     OR pg_temp.ilca4_family(a.alias);

  SELECT COUNT(*) INTO n FROM ilca4_hits;
  IF n <> 1 THEN
    SELECT string_agg(class_id::text || ' ' || class_name, ', ' ORDER BY class_id)
      INTO detail FROM ilca4_hits;
    RAISE EXCEPTION 'ILCA 4 rename stopped. Expected one class, found %: %', n, COALESCE(detail, '(none)');
  END IF;

  IF EXISTS (SELECT 1 FROM ilca4_hits WHERE class_id <> 8) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. Family class is not class_id 8';
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.classes
    WHERE class_name = 'ILCA 4' AND class_id <> 8
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. Another class is already named ILCA 4';
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.class_aliases a
    WHERE pg_temp.ilca4_family(a.alias) AND a.class_id IS DISTINCT FROM 8
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. A family alias points at a different class_id';
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.results r
    WHERE pg_temp.ilca4_family(r.class_canonical)
      AND r.class_id IS NOT NULL AND r.class_id <> 8
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. results.class_canonical family label has another class_id';
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.regatta_blocks b
    WHERE pg_temp.ilca4_family(b.class_canonical)
      AND b.class_id IS NOT NULL AND b.class_id <> 8
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. regatta_blocks.class_canonical family label has another class_id';
  END IF;
END $$;

UPDATE public.classes
SET class_name = 'ILCA 4'
WHERE class_id = 8
  AND class_name IS DISTINCT FROM 'ILCA 4';

INSERT INTO public.class_aliases (alias, class_id, verified, notes)
SELECT v.alias, 8, true, 'Historical ILCA 4 name. Canonical class_name is ILCA 4.'
FROM (VALUES
  ('Ilca 4.7'),
  ('ILCA4.7'),
  ('ILCA 4,7'),
  ('Laser 4.7'),
  ('Laser Radial 4.7'),
  ('Laser 4')
) AS v(alias)
WHERE NOT EXISTS (
  SELECT 1 FROM public.class_aliases a
  WHERE lower(btrim(a.alias)) = lower(btrim(v.alias))
);

INSERT INTO public.class_alias (alias_name, class_name)
SELECT v.alias_name, 'ILCA 4'
FROM (VALUES
  ('Ilca 4.7'),
  ('ILCA 4.7'),
  ('Laser 4.7'),
  ('Laser 4'),
  ('Laser Radial 4.7'),
  ('ILCA 4')
) AS v(alias_name)
WHERE NOT EXISTS (
  SELECT 1 FROM public.class_alias a WHERE a.alias_name = v.alias_name
);

UPDATE public.class_alias
SET class_name = 'ILCA 4'
WHERE alias_name IN ('ILCA4', 'ILCA 4.7', 'Laser 4.7', 'Ilca 4.7', 'Laser 4', 'Laser Radial 4.7', 'ILCA 4')
  AND class_name IS DISTINCT FROM 'ILCA 4'
  AND class_name IS DISTINCT FROM 'ILCA 6'
  AND class_name IS DISTINCT FROM 'ILCA 7';

UPDATE public.results
SET class_canonical = 'ILCA 4'
WHERE class_id = 8
  AND class_canonical IS DISTINCT FROM 'ILCA 4'
  AND pg_temp.ilca4_family(class_canonical);

UPDATE public.results
SET class_id = 8, class_canonical = 'ILCA 4'
WHERE class_id IS NULL
  AND pg_temp.ilca4_family(class_canonical);

UPDATE public.results
SET fleet_label = 'ILCA 4'
WHERE class_id = 8
  AND pg_temp.ilca4_family(fleet_label)
  AND fleet_label IS DISTINCT FROM 'ILCA 4';

UPDATE public.regatta_blocks
SET class_canonical = 'ILCA 4'
WHERE class_id = 8
  AND class_canonical IS DISTINCT FROM 'ILCA 4'
  AND pg_temp.ilca4_family(class_canonical);

UPDATE public.regatta_blocks
SET class_id = 8, class_canonical = 'ILCA 4'
WHERE class_id IS NULL
  AND pg_temp.ilca4_family(class_canonical);

UPDATE public.regatta_blocks
SET fleet_label = 'ILCA 4'
WHERE class_id = 8
  AND pg_temp.ilca4_family(fleet_label)
  AND fleet_label IS DISTINCT FROM 'ILCA 4';

-- Identical twin rows (Ilca 4.7 and ILCA 4.7 for the same sailor) collapse to one before rename.
DELETE FROM public.standing_list a
USING public.standing_list b
WHERE a.class_name = 'Ilca 4.7'
  AND b.class_name = 'ILCA 4.7'
  AND a.sailor_id = b.sailor_id
  AND a.rank IS NOT DISTINCT FROM b.rank
  AND a.regattas_sailed IS NOT DISTINCT FROM b.regattas_sailed
  AND a.ranking_score IS NOT DISTINCT FROM b.ranking_score
  AND a.name IS NOT DISTINCT FROM b.name;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.standing_list a
    JOIN public.standing_list b ON a.sailor_id = b.sailor_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. standing_list would collapse two different rows';
  END IF;
END $$;

UPDATE public.standing_list
SET class_name = 'ILCA 4'
WHERE pg_temp.ilca4_family(class_name)
  AND class_name IS DISTINCT FROM 'ILCA 4';

DELETE FROM public.master_list a
USING public.master_list b
WHERE a.class_name = 'Ilca 4.7'
  AND b.class_name = 'ILCA 4.7'
  AND a.sailor_id = b.sailor_id
  AND a.is_active IS NOT DISTINCT FROM b.is_active
  AND a.name IS NOT DISTINCT FROM b.name;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.master_list a
    JOIN public.master_list b ON a.sailor_id = b.sailor_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. master_list would collapse two different rows';
  END IF;
END $$;

UPDATE public.master_list
SET class_name = 'ILCA 4'
WHERE pg_temp.ilca4_family(class_name)
  AND class_name IS DISTINCT FROM 'ILCA 4';

UPDATE public.ranking_standings
SET class_code = 'ILCA 4'
WHERE pg_temp.ilca4_family(class_code)
  AND class_code IS DISTINCT FROM 'ILCA 4';

UPDATE public.ranking_audit_entries
SET class_name = 'ILCA 4',
    class_slug = 'ilca-4'
WHERE pg_temp.ilca4_family(class_name)
   OR class_name = 'LASER 4.7/ ILCS 4';

UPDATE public.sas_id_personal
SET primary_class = 'ILCA 4'
WHERE pg_temp.ilca4_family(primary_class)
  AND primary_class IS DISTINCT FROM 'ILCA 4';

UPDATE public.event_edition_classes
SET class_display_name = 'ILCA 4'
WHERE pg_temp.ilca4_family(class_display_name)
  AND class_display_name IS DISTINCT FROM 'ILCA 4';

UPDATE public.event_edition_classes
SET fleet_label = 'ILCA 4'
WHERE pg_temp.ilca4_family(fleet_label)
  AND fleet_label IS DISTINCT FROM 'ILCA 4';

DO $$
BEGIN
  IF to_regclass('public.h2h_matrix_cache') IS NOT NULL THEN
    IF EXISTS (
      SELECT 1 FROM public.h2h_matrix_cache a
      JOIN public.h2h_matrix_cache b
        ON a.sailor_a_id = b.sailor_a_id AND a.sailor_b_id = b.sailor_b_id AND b.class_name = 'ILCA 4'
      WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
    ) THEN
      RAISE EXCEPTION 'ILCA 4 rename stopped. h2h_matrix_cache collision';
    END IF;
    UPDATE public.h2h_matrix_cache
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.main_scores') IS NOT NULL THEN
    IF EXISTS (
      SELECT 1 FROM public.main_scores a
      JOIN public.main_scores b ON a.sailor_id = b.sailor_id AND b.class_name = 'ILCA 4'
      WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
    ) THEN
      RAISE EXCEPTION 'ILCA 4 rename stopped. main_scores collision';
    END IF;
    UPDATE public.main_scores
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.processed_regattas') IS NOT NULL THEN
    IF EXISTS (
      SELECT 1 FROM public.processed_regattas a
      JOIN public.processed_regattas b ON a.regatta_id = b.regatta_id AND b.class_name = 'ILCA 4'
      WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
    ) THEN
      RAISE EXCEPTION 'ILCA 4 rename stopped. processed_regattas collision';
    END IF;
    UPDATE public.processed_regattas
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.class_sailor_master_list') IS NOT NULL THEN
    UPDATE public.class_sailor_master_list
    SET class_code = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_code) AND class_code IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.ranking_history') IS NOT NULL THEN
    UPDATE public.ranking_history
    SET class_code = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_code) AND class_code IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.class_age_limits') IS NOT NULL THEN
    UPDATE public.class_age_limits
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.sailor_projection_meta') IS NOT NULL THEN
    UPDATE public.sailor_projection_meta
    SET class_code = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_code) AND class_code IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.standings_recalc_queue') IS NOT NULL THEN
    -- PK is the normalised name. Canonical "ilca 4" is already queued.
    DELETE FROM public.standings_recalc_queue
    WHERE pg_temp.ilca4_family(class_name_normalized)
      AND class_name_normalized IS DISTINCT FROM 'ilca 4';
  END IF;
END $$;

COMMIT;

-- Applied after the rename. Class page lists only raced = true.
-- 60 class_id 8 rows already had ranks and scores but raced was null, so
-- those ILCA 4.7 regattas were missing from /class/ilca-4.
-- One Open Mono result kept its original text and fleet, and was linked to class 8.
UPDATE public.results
SET raced = TRUE
WHERE class_id = 8
  AND raced IS NOT TRUE
  AND rank IS NOT NULL;

UPDATE public.results
SET class_id = 8,
    class_canonical = 'ILCA 4'
WHERE class_id IS NULL
  AND class_original = 'LASER 4.7/ ILCS 4'
  AND class_canonical = 'LASER 4.7/ ILCS 4';
