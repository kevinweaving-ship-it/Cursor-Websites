-- Lipton 2026 URL identity: helm column = helm only; bow 63 club code IZI.
-- Does not change race scores, nett, or rank.

BEGIN;

UPDATE public.results
SET helm_name = TRIM(SPLIT_PART(helm_name, ' / ', 1))
WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
  AND helm_name LIKE '% / %';

UPDATE public.results
SET club_raw = 'IZI'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
  AND TRIM(bow_no::text) = '63'
  AND club_id = 28;

DO $$
DECLARE n_slash int; club63 text;
BEGIN
    SELECT COUNT(*) INTO n_slash FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND helm_name LIKE '% / %';
    IF n_slash <> 0 THEN RAISE EXCEPTION 'helm still has slash: %', n_slash; END IF;
    SELECT club_raw INTO club63 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '63';
    IF club63 IS DISTINCT FROM 'IZI' THEN RAISE EXCEPTION 'bow 63 club %', club63; END IF;
END $$;

COMMIT;
