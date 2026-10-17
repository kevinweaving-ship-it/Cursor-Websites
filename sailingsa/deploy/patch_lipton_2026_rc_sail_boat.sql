-- Lipton 2026: align sail numbers and boat names to official Overall after 5 Races.
-- Source: Overall_after_5_Races.pdf / Lipton Cup 2026 - Race 05.pdf
-- Does NOT change race_scores, total, nett, or rank.

BEGIN;

-- Snapshot scores so we can prove they did not move.
CREATE TEMP TABLE _lipton_score_snap AS
SELECT result_id, bow_no, rank, race_scores, total_points_raw, nett_points_raw
FROM public.results
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

UPDATE public.results SET sail_number = '766', boat_name = 'Amtec Racing'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '26';

UPDATE public.results SET sail_number = '1571', boat_name = 'Nitro Juice'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '32';

UPDATE public.results SET sail_number = '768', boat_name = 'Ullman Racing'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '28';

UPDATE public.results SET sail_number = '763', boat_name = 'Phantom'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '23';

UPDATE public.results SET sail_number = '1277', boat_name = '22-ATE'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '52';

UPDATE public.results SET sail_number = '173', boat_name = 'J-Walker powered by North Sails'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '8';

UPDATE public.results SET sail_number = '1169', boat_name = 'Ullman Sails Camissa'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '48';

UPDATE public.results SET sail_number = '774', boat_name = 'Nitro Maverick'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '31';

UPDATE public.results SET sail_number = '1167', boat_name = 'Wildcard'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '46';

UPDATE public.results SET sail_number = '1175', boat_name = 'Nitro Monkey'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '49';

UPDATE public.results SET sail_number = '1116', boat_name = 'G''day J'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '34';

UPDATE public.results SET sail_number = '185', boat_name = 'Andiamo'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '14';

UPDATE public.results SET sail_number = '1139', boat_name = 'H2O Tech'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '44';

UPDATE public.results SET sail_number = '771', boat_name = 'Donna Mia Forever'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '63';

UPDATE public.results SET sail_number = '1239', boat_name = 'CaCanny'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '55';

UPDATE public.results SET sail_number = '1237', boat_name = 'Attacke'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '51';

UPDATE public.results SET sail_number = '1138', boat_name = 'Laugh a minute'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '43';

DO $$
DECLARE n int; s26 text; s8 text; b23 text; b34 text; b63 text;
BEGIN
    SELECT COUNT(*) INTO n
    FROM public.results r
    JOIN _lipton_score_snap s ON s.result_id = r.result_id
    WHERE r.regatta_id = '2026-08-29-lipton-challenge-cup'
      AND (r.rank IS DISTINCT FROM s.rank
           OR r.total_points_raw IS DISTINCT FROM s.total_points_raw
           OR r.nett_points_raw IS DISTINCT FROM s.nett_points_raw
           OR r.race_scores IS DISTINCT FROM s.race_scores);
    IF n <> 0 THEN
        RAISE EXCEPTION 'scores changed for % rows', n;
    END IF;

    SELECT sail_number INTO s26 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '26';
    SELECT sail_number INTO s8 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '8';
    SELECT boat_name INTO b23 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '23';
    SELECT boat_name INTO b34 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '34';
    SELECT boat_name INTO b63 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text) = '63';

    IF s26 IS DISTINCT FROM '766' THEN RAISE EXCEPTION 'bow 26 sail %', s26; END IF;
    IF s8 IS DISTINCT FROM '173' THEN RAISE EXCEPTION 'bow 8 sail %', s8; END IF;
    IF b23 IS DISTINCT FROM 'Phantom' THEN RAISE EXCEPTION 'bow 23 boat %', b23; END IF;
    IF b34 IS DISTINCT FROM 'G''day J' THEN RAISE EXCEPTION 'bow 34 boat %', b34; END IF;
    IF b63 IS DISTINCT FROM 'Donna Mia Forever' THEN RAISE EXCEPTION 'bow 63 boat %', b63; END IF;
END $$;

COMMIT;
