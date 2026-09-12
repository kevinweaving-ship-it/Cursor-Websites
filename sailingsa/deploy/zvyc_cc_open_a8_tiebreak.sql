-- Cape Classic Open: official Sailwave scores + Appendix A checksum.
-- 5 boats, 2 races, 0 discards. DNC = entries+1 = 6.
-- Sean 585 and Gordon 589 both nett 3.0.
-- A8.1: both have a 1 and a 2 → still tied.
-- A8.2: last race (R2) Sean 1.0 beats Gordon 2.0 → Sean rank 1.

BEGIN;

UPDATE public.results SET
  rank = 1,
  rank_ordinal = '1st',
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"2.0","R2":"1.0"}'::jsonb,
  total_points_raw = 3.0,
  nett_points_raw = 3.0
WHERE result_id = 21161
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results SET
  rank = 2,
  rank_ordinal = '2nd',
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"1.0","R2":"2.0"}'::jsonb,
  total_points_raw = 3.0,
  nett_points_raw = 3.0
WHERE result_id = 21156
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results SET rank = 3, rank_ordinal = '3rd' WHERE result_id = 21157 AND regatta_id = '2026-09-13-zvyc-cape-classic';
UPDATE public.results SET rank = 4, rank_ordinal = '4th' WHERE result_id = 21158 AND regatta_id = '2026-09-13-zvyc-cape-classic';
UPDATE public.results SET rank = 5, rank_ordinal = '5th' WHERE result_id = 21185 AND regatta_id = '2026-09-13-zvyc-cape-classic';

COMMIT;

SELECT result_id, rank, rank_ordinal, helm_name, sail_number, race_scores, total_points_raw, nett_points_raw
FROM public.results
WHERE regatta_id = '2026-09-13-zvyc-cape-classic'
  AND block_id = '2026-09-13-zvyc-cape-classic:open'
ORDER BY rank;
