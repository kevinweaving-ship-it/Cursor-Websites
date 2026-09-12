-- Cape Classic 2026-09-13: fill crew_sa_sailing_id on boats that already
-- have a SAS catalogue match. Do not invent IDs for names with no row.
--
-- Matched:
--   Julia Walton          24649  (Sean Kavanagh Open/Sonnet)
--   Anna Scheder-Bieschin 12797
--   Jesse Anderson        21497
--   Thaakir Martin        24190
--   Zavier Stone PDF   -> Xavier Stone 24218 (same 420 sailor)
--   Dylan Swartz PDF   -> Dillan Swarts 26465 (Jemayne Wolmarans crew)
-- Already set: Helen Haering 28208
-- No SAS row: Sulaiman Almand, Ayrton Pask — left NULL

BEGIN;

UPDATE public.results
SET crew_sa_sailing_id = 24649,
    crew_name = 'Julia Walton',
    match_status_crew = 'sas'
WHERE result_id = 21161
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results
SET crew_sa_sailing_id = 12797,
    crew_name = 'Anna Scheder-Bieschin',
    match_status_crew = 'sas'
WHERE result_id = 21157
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results
SET crew_sa_sailing_id = 21497,
    crew_name = 'Jesse Anderson',
    match_status_crew = 'sas'
WHERE result_id = 21185
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results
SET crew_sa_sailing_id = 24190,
    crew_name = 'Thaakir Martin',
    match_status_crew = 'sas'
WHERE result_id = 21173
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results
SET crew_sa_sailing_id = 24218,
    crew_name = 'Xavier Stone',
    match_status_crew = 'sas'
WHERE result_id = 21174
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

UPDATE public.results
SET crew_sa_sailing_id = 26465,
    crew_name = 'Dillan Swarts',
    match_status_crew = 'sas'
WHERE result_id = 21175
  AND regatta_id = '2026-09-13-zvyc-cape-classic';

COMMIT;

SELECT result_id, fleet_label, rank, helm_name, crew_name, crew_sa_sailing_id, match_status_crew
FROM public.results
WHERE regatta_id = '2026-09-13-zvyc-cape-classic'
  AND crew_name IS NOT NULL AND btrim(crew_name) <> ''
ORDER BY fleet_label, rank;
