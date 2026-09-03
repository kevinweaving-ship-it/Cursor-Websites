-- Lipton 2026 R5 from Vakaros T+ finish order (lowest elapsed = 1st).
-- No discards: nett = total of R1..R5. Rank = lowest nett, A8 ties.
-- Does not change R1–R4.

BEGIN;

UPDATE public.results r
SET race_scores = COALESCE(r.race_scores::jsonb, '{}'::jsonb) || jsonb_build_object('R5', m.r5)
FROM (VALUES
    ('26', '1'),
    ('32', '2'),
    ('23', '3'),
    ('8',  '4'),
    ('31', '5'),
    ('28', '6'),
    ('49', '7'),
    ('34', '8'),
    ('52', '9'),
    ('48', '10'),
    ('46', '11'),
    ('63', '12'),
    ('44', '13'),
    ('14', '14'),
    ('55', '15'),
    ('51', '16'),
    ('43', '17')
) AS m(bow_no, r5)
WHERE r.regatta_id = '2026-08-29-lipton-challenge-cup'
  AND TRIM(r.bow_no::text) = m.bow_no;

UPDATE public.results r
SET
    total_points_raw = t.tot,
    nett_points_raw = t.tot,
    rank = t.rk,
    raced = TRUE,
    result_status = 'Provisional',
    as_at_time = TIMEZONE('Africa/Johannesburg', NOW())
FROM (VALUES
    ('26', 18, 1),
    ('32', 21, 2),
    ('28', 23, 3),
    ('23', 30, 4),
    ('52', 31, 5),
    ('8',  33, 6),
    ('48', 34, 7),
    ('31', 34, 8),
    ('46', 37, 9),
    ('49', 37, 10),
    ('34', 40, 11),
    ('14', 62, 12),
    ('44', 69, 13),
    ('63', 70, 14),
    ('55', 71, 15),
    ('51', 73, 16),
    ('43', 82, 17)
) AS t(bow_no, tot, rk)
WHERE r.regatta_id = '2026-08-29-lipton-challenge-cup'
  AND TRIM(r.bow_no::text) = t.bow_no;

UPDATE public.regatta_blocks
SET races_sailed = 5, discard_count = 0, to_count = 5
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

UPDATE public.regattas
SET result_status = 'Provisional',
    as_at_time = NOW()
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

DO $$
DECLARE n_r5 int; n_rk int; wyac text; rae int;
BEGIN
    SELECT COUNT(*) INTO n_r5 FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
      AND COALESCE(race_scores->>'R5','') <> '';
    IF n_r5 <> 17 THEN RAISE EXCEPTION 'R5 rows %', n_r5; END IF;
    SELECT COUNT(*) INTO n_rk FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND rank BETWEEN 1 AND 17;
    IF n_rk <> 17 THEN RAISE EXCEPTION 'ranks %', n_rk; END IF;
    SELECT race_scores->>'R5' INTO wyac FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text)='43';
    IF wyac IS DISTINCT FROM '17' THEN RAISE EXCEPTION 'WYAC R5 %', wyac; END IF;
    SELECT rank INTO rae FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup' AND TRIM(bow_no::text)='26';
    IF rae IS DISTINCT FROM 1 THEN RAISE EXCEPTION 'Rae rank %', rae; END IF;
END $$;

COMMIT;
