-- Cape Classic Open: checksum official scores + Appendix A8.2 ranks.
-- Official PDF = truth for fleet/rank/R1/R2/total/nett (names may differ).
-- Sean 585: 2,1 tot 3 nett 3 rank 1. Gordon 589: 1,2 tot 3 nett 3 rank 2.
-- A8.1 identical 1+2; A8.2 last race R2 Sean 1 beats Gordon 2.

SELECT
  sail_number,
  rank,
  rank_ordinal,
  race_scores->>'R1' AS r1,
  race_scores->>'R2' AS r2,
  total_points_raw,
  nett_points_raw,
  CASE
    WHEN sail_number = '585' AND rank = 1 AND total_points_raw = 3 AND nett_points_raw = 3
         AND race_scores->>'R1' = '2.0' AND race_scores->>'R2' = '1.0' THEN 'PASS'
    WHEN sail_number = '589' AND rank = 2 AND total_points_raw = 3 AND nett_points_raw = 3
         AND race_scores->>'R1' = '1.0' AND race_scores->>'R2' = '2.0' THEN 'PASS'
    WHEN sail_number = '575' AND rank = 3 AND total_points_raw = 6 AND nett_points_raw = 6 THEN 'PASS'
    WHEN sail_number = '12971' AND rank = 4 AND total_points_raw = 8 AND nett_points_raw = 8 THEN 'PASS'
    WHEN sail_number = '9630' AND rank = 5 AND total_points_raw = 12 AND nett_points_raw = 12 THEN 'PASS'
    ELSE 'FAIL'
  END AS checksum
FROM public.results
WHERE block_id = '2026-09-13-zvyc-cape-classic:open'
ORDER BY rank;
