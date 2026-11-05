-- ILCA 4 canonical class.
-- Keeps ILCA 4.7, Laser 4.7 and Laser Radial 4.7 as aliases.
-- Does not insert classes, results, sailors, or events.
-- Does not change class_original, regatta_id, or block_id.
-- Does not touch ILCA 6 or ILCA 7.
-- If zero classes match, it changes nothing (does not create a class).
-- If two or more class_ids match, or a historical alias points at a different class,
-- the transaction rolls back and lists those ids.

BEGIN;

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
  chosen int;
  old_name text;
  alias_names text[] := ARRAY[
    'ILCA 4.7', 'Ilca 4.7', 'ILCA4.7', 'ILCA 4,7', 'Laser 4.7', 'Laser Radial 4.7'
  ];
  one_alias text;
  detail text;
BEGIN
  CREATE TEMP TABLE ilca4_hits ON COMMIT DROP AS
  SELECT DISTINCT c.class_id, c.class_name
  FROM public.classes c
  LEFT JOIN public.class_aliases a ON a.class_id = c.class_id
  WHERE pg_temp.ilca4_family(c.class_name)
     OR pg_temp.ilca4_family(a.alias);

  SELECT COUNT(*) INTO n FROM ilca4_hits;
  IF n = 0 THEN
    RAISE NOTICE 'ILCA 4: no existing class row. Nothing created.';
    RETURN;
  END IF;
  IF n > 1 THEN
    SELECT string_agg(class_id::text || ' ' || class_name, ', ' ORDER BY class_id)
      INTO detail FROM ilca4_hits;
    RAISE EXCEPTION 'ILCA 4 rename stopped. Competing class rows: %', detail;
  END IF;

  SELECT class_id, class_name INTO chosen, old_name FROM ilca4_hits;

  IF EXISTS (
    SELECT 1 FROM public.class_aliases a
    WHERE pg_temp.ilca4_family(a.alias)
      AND a.class_id IS DISTINCT FROM chosen
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. A historical alias points at a different class_id than %', chosen;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.results r
    WHERE pg_temp.ilca4_family(r.class_canonical)
      AND r.class_id IS NOT NULL
      AND r.class_id <> chosen
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. results.class_canonical is an ILCA 4 label but class_id is not %', chosen;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.regatta_blocks b
    WHERE pg_temp.ilca4_family(b.class_canonical)
      AND b.class_id IS NOT NULL
      AND b.class_id <> chosen
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. regatta_blocks.class_canonical is an ILCA 4 label but class_id is not %', chosen;
  END IF;

  IF old_name IS DISTINCT FROM 'ILCA 4' THEN
    alias_names := array_append(alias_names, old_name);
    UPDATE public.classes SET class_name = 'ILCA 4' WHERE class_id = chosen;
  END IF;

  FOREACH one_alias IN ARRAY alias_names LOOP
    IF one_alias IS NULL OR btrim(one_alias) = '' OR lower(btrim(one_alias)) = 'ilca 4' THEN
      CONTINUE;
    END IF;
    INSERT INTO public.class_aliases (alias, class_id, verified, notes)
    VALUES (
      one_alias,
      chosen,
      true,
      'Historical ILCA 4 name. Canonical class_name is ILCA 4.'
    )
    ON CONFLICT (alias) DO NOTHING;
  END LOOP;

  UPDATE public.results
  SET class_canonical = 'ILCA 4'
  WHERE class_id = chosen
    AND class_canonical IS DISTINCT FROM 'ILCA 4'
    AND pg_temp.ilca4_family(class_canonical);

  UPDATE public.results
  SET class_id = chosen, class_canonical = 'ILCA 4'
  WHERE class_id IS NULL
    AND pg_temp.ilca4_family(class_canonical);

  UPDATE public.results
  SET fleet_label = 'ILCA 4'
  WHERE class_id = chosen
    AND pg_temp.ilca4_family(fleet_label)
    AND fleet_label IS DISTINCT FROM 'ILCA 4';

  UPDATE public.regatta_blocks
  SET class_canonical = 'ILCA 4'
  WHERE class_id = chosen
    AND class_canonical IS DISTINCT FROM 'ILCA 4'
    AND pg_temp.ilca4_family(class_canonical);

  UPDATE public.regatta_blocks
  SET class_id = chosen, class_canonical = 'ILCA 4'
  WHERE class_id IS NULL
    AND pg_temp.ilca4_family(class_canonical);

  UPDATE public.regatta_blocks
  SET fleet_label = 'ILCA 4'
  WHERE class_id = chosen
    AND pg_temp.ilca4_family(fleet_label)
    AND fleet_label IS DISTINCT FROM 'ILCA 4';

  -- Text standings that key on the old class name. Abort if the new name already
  -- exists for the same sailor or boat, so two rows are not collapsed blindly.
  IF to_regclass('public.standing_list') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.standing_list a
    JOIN public.standing_list b ON a.sailor_id = b.sailor_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. standing_list already has ILCA 4 for a sailor who also has a 4.7-family row';
  END IF;
  IF to_regclass('public.standing_list') IS NOT NULL THEN
    UPDATE public.standing_list
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.master_list') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.master_list a
    JOIN public.master_list b ON a.sailor_id = b.sailor_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. master_list already has ILCA 4 for a sailor who also has a 4.7-family row';
  END IF;
  IF to_regclass('public.master_list') IS NOT NULL THEN
    UPDATE public.master_list
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.boats') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.boats a
    JOIN public.boats b ON a.sail_number = b.sail_number AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. boats already has ILCA 4 for a sail number that also has a 4.7-family row';
  END IF;
  IF to_regclass('public.boats') IS NOT NULL THEN
    UPDATE public.boats
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.h2h_matrix_cache') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.h2h_matrix_cache a
    JOIN public.h2h_matrix_cache b
      ON a.sailor_a_id = b.sailor_a_id AND a.sailor_b_id = b.sailor_b_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. h2h_matrix_cache already has ILCA 4 for a pair that also has a 4.7-family row';
  END IF;
  IF to_regclass('public.h2h_matrix_cache') IS NOT NULL THEN
    UPDATE public.h2h_matrix_cache
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.main_scores') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.main_scores a
    JOIN public.main_scores b ON a.sailor_id = b.sailor_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. main_scores already has ILCA 4 for a sailor who also has a 4.7-family row';
  END IF;
  IF to_regclass('public.main_scores') IS NOT NULL THEN
    UPDATE public.main_scores
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.processed_regattas') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.processed_regattas a
    JOIN public.processed_regattas b ON a.regatta_id = b.regatta_id AND b.class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_name) AND a.class_name IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. processed_regattas already has ILCA 4 for a regatta that also has a 4.7-family row';
  END IF;
  IF to_regclass('public.processed_regattas') IS NOT NULL THEN
    UPDATE public.processed_regattas
    SET class_name = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_name) AND class_name IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.class_sailor_master_list') IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.class_sailor_master_list a
    JOIN public.class_sailor_master_list b ON a.sailor_id = b.sailor_id AND b.class_code = 'ILCA 4'
    WHERE pg_temp.ilca4_family(a.class_code) AND a.class_code IS DISTINCT FROM 'ILCA 4'
  ) THEN
    RAISE EXCEPTION 'ILCA 4 rename stopped. class_sailor_master_list already has ILCA 4 for a sailor who also has a 4.7-family row';
  END IF;
  IF to_regclass('public.class_sailor_master_list') IS NOT NULL THEN
    UPDATE public.class_sailor_master_list
    SET class_code = 'ILCA 4'
    WHERE pg_temp.ilca4_family(class_code) AND class_code IS DISTINCT FROM 'ILCA 4';
  END IF;

  IF to_regclass('public.sas_id_personal') IS NOT NULL THEN
    UPDATE public.sas_id_personal
    SET primary_class = 'ILCA 4'
    WHERE pg_temp.ilca4_family(primary_class) AND primary_class IS DISTINCT FROM 'ILCA 4';
  END IF;

  RAISE NOTICE 'ILCA 4 canonical class_id % (previous name %)', chosen, old_name;
END $$;

COMMIT;
