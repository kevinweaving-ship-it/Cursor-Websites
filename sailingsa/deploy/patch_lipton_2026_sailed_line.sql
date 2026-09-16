-- Fix Lipton Challenge Cup 2026 sailed line
-- Change from: Sailed: 1, Discards: 0, To count: 0
-- Change to:   Sailed: 3, Discards: 0, To count: 3

BEGIN;

UPDATE public.regatta_blocks
SET races_sailed = 3,
    discard_count = 0,
    to_count = 3
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';

COMMIT;

-- Verify
SELECT block_id, regatta_id, fleet_label, races_sailed, discard_count, to_count, entries, scoring_system
FROM public.regatta_blocks
WHERE regatta_id = '2026-08-29-lipton-challenge-cup';
