-- Lipton 2026: Attacke (bow 51) Allers have no row in sas_id_personal.
-- Record them as admin_confirmed_no_sas so the sheet can link NAME: profiles
-- without inventing SAS IDs. Does not change race scores, nett, or rank.

BEGIN;

INSERT INTO public.identity_pending_sailors
    (display_name, role, normalized_name, sail_number_hint, result_row_count, regatta_ids, status, admin_confirmed_at, updated_at)
VALUES
    ('Nikolai Allers', 'helm', 'nikolai allers', '51', 1,
     ARRAY['2026-08-29-lipton-challenge-cup']::text[], 'admin_confirmed_no_sas', NOW(), NOW()),
    ('Pascal Allers', 'crew', 'pascal allers', '51', 1,
     ARRAY['2026-08-29-lipton-challenge-cup']::text[], 'admin_confirmed_no_sas', NOW(), NOW()),
    ('Florian Allers', 'crew', 'florian allers', '51', 1,
     ARRAY['2026-08-29-lipton-challenge-cup']::text[], 'admin_confirmed_no_sas', NOW(), NOW())
ON CONFLICT (normalized_name, role) DO UPDATE
SET display_name = EXCLUDED.display_name,
    sail_number_hint = EXCLUDED.sail_number_hint,
    result_row_count = GREATEST(public.identity_pending_sailors.result_row_count, EXCLUDED.result_row_count),
    regatta_ids = (
        SELECT ARRAY(SELECT DISTINCT x FROM unnest(
            public.identity_pending_sailors.regatta_ids || EXCLUDED.regatta_ids
        ) AS x)
    ),
    status = 'admin_confirmed_no_sas',
    admin_confirmed_at = COALESCE(public.identity_pending_sailors.admin_confirmed_at, NOW()),
    updated_at = NOW();

DO $$
DECLARE n int;
BEGIN
    SELECT COUNT(*) INTO n
    FROM public.identity_pending_sailors
    WHERE status = 'admin_confirmed_no_sas'
      AND normalized_name IN ('nikolai allers', 'pascal allers', 'florian allers');
    IF n <> 3 THEN
        RAISE EXCEPTION 'expected 3 confirmed Allers rows, got %', n;
    END IF;
END $$;

COMMIT;
