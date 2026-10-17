-- Lipton 2026 URL: boats did race; year from start_date.
-- Does not change race scores, ranks, or Nett.
-- raced was NULL → results-summary entries_total=0 and class-entries={}.

BEGIN;

UPDATE public.results
SET raced = TRUE
WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
  AND raced IS NULL;

UPDATE public.regattas
SET year = 2026
WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
  AND year IS NULL;

DO $$
DECLARE
    n_raced int;
    n_rows int;
    y int;
BEGIN
    SELECT COUNT(*) INTO n_rows
    FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup';
    SELECT COUNT(*) INTO n_raced
    FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
      AND raced IS TRUE;
    IF n_rows <> 17 OR n_raced <> 17 THEN
        RAISE EXCEPTION 'Lipton 2026 raced expected 17/17, got rows=% raced=%', n_rows, n_raced;
    END IF;
    SELECT year INTO y
    FROM public.regattas
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup';
    IF y IS DISTINCT FROM 2026 THEN
        RAISE EXCEPTION 'Lipton 2026 year expected 2026, got %', y;
    END IF;
END $$;

COMMIT;
