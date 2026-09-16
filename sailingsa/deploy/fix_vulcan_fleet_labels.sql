-- Vulcan Challenge 2026: fleet titles are names only. Scoring stays on the sailed line.
UPDATE public.regatta_blocks
SET block_label_raw = fleet_label
WHERE regatta_id = '2026-09-13-vulcan-challenge'
  AND block_label_raw IS DISTINCT FROM fleet_label;

UPDATE public.regatta_blocks
SET fleet_label = 'Keelboat Fleet',
    block_label_raw = 'Keelboat Fleet'
WHERE block_id = '2026-09-13-vulcan-challenge:03-keelboats';

UPDATE public.results
SET fleet_label = 'Keelboat Fleet'
WHERE block_id = '2026-09-13-vulcan-challenge:03-keelboats'
  AND fleet_label IS DISTINCT FROM 'Keelboat Fleet';
