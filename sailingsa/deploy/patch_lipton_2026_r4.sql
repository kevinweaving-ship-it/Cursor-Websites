-- Lipton 2026 R4 only.
-- Source: https://liptoncup.com/backend/wp-content/uploads/2026/08/Lipton-Cup-2026-Race-04.pdf
-- Overall: https://liptoncup.com/backend/wp-content/uploads/2026/08/Overall-after-4-Races.pdf
-- as_at from Race 04 PDF Last-Modified: 2026-08-27 14:09:26 GMT = 16:09 SAST.
-- Match boats by bow_no. Do not change sail numbers / identities.

BEGIN;

UPDATE public.results r
SET race_scores = COALESCE(r.race_scores::jsonb, '{}'::jsonb) || jsonb_build_object('R4', m.r4)
FROM (VALUES
    ('52', '1'),
    ('28', '2'),
    ('48', '3'),
    ('26', '4'),
    ('49', '5'),
    ('14', '6'),
    ('8',  '7'),
    ('23', '8'),
    ('31', '9'),
    ('46', '10'),
    ('34', '11'),
    ('32', '12'),
    ('51', '13'),
    ('55', '14'),
    ('63', '15'),
    ('44', '16'),
    ('43', '17')
) AS m(bow_no, r4)
WHERE r.regatta_id = '2026-08-29-lipton-challenge-cup'
  AND TRIM(r.bow_no::text) = m.bow_no;

UPDATE public.results r
SET
    total_points_raw = t.tot,
    nett_points_raw = t.tot,
    rank = t.rk,
    as_at_time = TIMESTAMP WITH TIME ZONE '2026-08-27 16:09:00+02',
    result_status = 'Provisional'
FROM (VALUES
    ('26', 17, 1),
    ('28', 17, 2),
    ('32', 19, 3),
    ('52', 22, 4),
    ('48', 24, 5),
    ('46', 26, 6),
    ('23', 27, 7),
    ('31', 29, 8),
    ('8',  29, 9),
    ('49', 30, 10),
    ('34', 32, 11),
    ('14', 48, 12),
    ('44', 56, 13),
    ('55', 56, 14),
    ('51', 57, 15),
    ('63', 58, 16),
    ('43', 65, 17)
) AS t(bow_no, tot, rk)
WHERE r.regatta_id = '2026-08-29-lipton-challenge-cup'
  AND TRIM(r.bow_no::text) = t.bow_no;

UPDATE public.regatta_blocks
SET races_sailed = 4, discard_count = 0, to_count = 4
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

UPDATE public.regattas
SET result_status = 'Provisional',
    as_at_time = TIMESTAMP WITH TIME ZONE '2026-08-27 16:09:00+02'
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

-- Fail the transaction if R4 is incomplete.
DO $$
DECLARE
    n int;
    n_r4 int;
    wyac_r4 text;
    wyac_rank int;
BEGIN
    SELECT COUNT(*) INTO n
    FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup';
    IF n <> 17 THEN
        RAISE EXCEPTION 'expected 17 results, got %', n;
    END IF;

    SELECT COUNT(*) INTO n_r4
    FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
      AND race_scores ? 'R4';
    IF n_r4 <> 17 THEN
        RAISE EXCEPTION 'expected 17 R4 scores, got %', n_r4;
    END IF;

    SELECT race_scores->>'R4', rank INTO wyac_r4, wyac_rank
    FROM public.results
    WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
      AND TRIM(bow_no::text) = '43';
    IF wyac_r4 IS DISTINCT FROM '17' OR wyac_rank IS DISTINCT FROM 17 THEN
        RAISE EXCEPTION 'WYAC bow 43 expected R4=17 rank=17, got R4=% rank=%', wyac_r4, wyac_rank;
    END IF;
END $$;

SELECT TRIM(bow_no::text) AS bow, rank, helm_name, club_raw,
       race_scores->>'R1' AS r1, race_scores->>'R2' AS r2,
       race_scores->>'R3' AS r3, race_scores->>'R4' AS r4,
       total_points_raw, nett_points_raw
FROM public.results
WHERE regatta_id = '2026-08-29-lipton-challenge-cup'
ORDER BY rank;

SELECT races_sailed, discard_count, to_count
FROM public.regatta_blocks
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

SELECT result_status, as_at_time
FROM public.regattas
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

COMMIT;
