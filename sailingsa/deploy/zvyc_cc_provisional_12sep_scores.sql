BEGIN;

-- ZVYC Cape Classic 12/13 Sept 2026 — Sailwave provisional as at 12 September 2026 at 17:46
-- Source: ZVYC Cape Classic Provisional Results 12 Sept.pdf
-- UPDATE existing rows only (plus restore 420 block + one new ILCA 6 rower Ross Walton).

UPDATE public.regattas SET
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE regatta_id = '2026-09-13-zvyc-cape-classic';

-- 420 fleet restored (boats currently sitting in Open)
INSERT INTO public.regatta_blocks (
  block_id, regatta_id, class_original, class_canonical, fleet_label,
  races_sailed, discard_count, to_count, scoring_system, block_label_raw,
  class_id, entries_raced, entries_closed, race_column_labels
) VALUES (
  '2026-09-13-zvyc-cape-classic:420-fleet',
  '2026-09-13-zvyc-cape-classic',
  '420', '420', '420',
  2, 0, 2, 'Appendix A', '420 Fleet',
  7, 4, false, '["R1","R2"]'::jsonb
) ON CONFLICT (block_id) DO UPDATE SET
  class_original = '420',
  class_canonical = '420',
  fleet_label = '420',
  block_label_raw = '420 Fleet',
  class_id = 7,
  races_sailed = 2,
  discard_count = 0,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 4,
  race_column_labels = '["R1","R2"]'::jsonb;

UPDATE public.results SET
  block_id = '2026-09-13-zvyc-cape-classic:420-fleet',
  fleet_label = '420',
  class_original = '420',
  class_canonical = '420',
  class_id = 7,
  rank = 1,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"1.0","R2":"1.0"}'::jsonb,
  total_points_raw = 2.0,
  nett_points_raw = 2.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21174; -- Amir Yaghya 5480

UPDATE public.results SET
  block_id = '2026-09-13-zvyc-cape-classic:420-fleet',
  fleet_label = '420',
  class_original = '420',
  class_canonical = '420',
  class_id = 7,
  rank = 2,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"3.0","R2":"2.0"}'::jsonb,
  total_points_raw = 5.0,
  nett_points_raw = 5.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21172; -- Abdull Alexander 1

UPDATE public.results SET
  block_id = '2026-09-13-zvyc-cape-classic:420-fleet',
  fleet_label = '420',
  class_original = '420',
  class_canonical = '420',
  class_id = 7,
  rank = 3,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"2.0","R2":"3.5"}'::jsonb,
  total_points_raw = 5.5,
  nett_points_raw = 5.5,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21175; -- Jemayne Wolmarans 52997

UPDATE public.results SET
  block_id = '2026-09-13-zvyc-cape-classic:420-fleet',
  fleet_label = '420',
  class_original = '420',
  class_canonical = '420',
  class_id = 7,
  rank = 4,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"4.0","R2":"3.5"}'::jsonb,
  total_points_raw = 7.5,
  nett_points_raw = 7.5,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21173; -- Renton Gedult 52998

-- Open: the five remaining boats (Sonnet / Fireball / Topaz)
UPDATE public.results SET
  fleet_label = 'Open',
  rank = 1,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"2.0","R2":"1.0"}'::jsonb,
  total_points_raw = 3.0,
  nett_points_raw = 3.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21161; -- Sean Kavanagh 585

UPDATE public.results SET
  fleet_label = 'Open',
  crew_name = 'Helen Haering',
  rank = 2,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"1.0","R2":"2.0"}'::jsonb,
  total_points_raw = 3.0,
  nett_points_raw = 3.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21156; -- Gordon Guthrie 589

UPDATE public.results SET
  fleet_label = 'Open',
  rank = 3,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"3.0","R2":"3.0"}'::jsonb,
  total_points_raw = 6.0,
  nett_points_raw = 6.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21157; -- Theodor Scheder-Bieschin 575

UPDATE public.results SET
  fleet_label = 'Open',
  rank = 4,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"4.0","R2":"4.0"}'::jsonb,
  total_points_raw = 8.0,
  nett_points_raw = 8.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21158; -- Ethan Robbertze 12971

UPDATE public.results SET
  fleet_label = 'Open',
  rank = 5,
  raced = true,
  races_sailed = 2,
  discard_count = 0,
  ranks_sailed = 2,
  race_scores = '{"R1":"6.0 DNC","R2":"6.0 DNC"}'::jsonb,
  total_points_raw = 12.0,
  nett_points_raw = 12.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21185; -- Jay Carter 9630

UPDATE public.regatta_blocks SET
  class_original = 'Open',
  class_canonical = 'Open',
  fleet_label = 'Open',
  block_label_raw = 'Open Fleet',
  class_id = 60,
  races_sailed = 2,
  discard_count = 0,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 5,
  race_column_labels = '["R1","R2"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:open';

-- Extra (19 boats, 3 races, 1 discard). DNC = 20. Keep SAS helm names.
UPDATE public.results SET sail_number = '883', fleet_label = 'Extra', rank = 6, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"5.0","R2":"(7.0)","R3":"4.0"}'::jsonb, total_points_raw = 16.0, nett_points_raw = 9.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21139; -- Kevin Foreman (PDF 883)

UPDATE public.results SET sail_number = '894', fleet_label = 'Extra', rank = 19, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"17.0","R2":"(20.0 DNC)","R3":"20.0 DNC"}'::jsonb, total_points_raw = 57.0, nett_points_raw = 37.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21141; -- Robert Foreman (PDF 894)

UPDATE public.results SET fleet_label = 'Extra', rank = 1, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"1.0","R2":"(6.0)","R3":"1.0"}'::jsonb, total_points_raw = 8.0, nett_points_raw = 2.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21143; -- Stephen Du Toit 833

UPDATE public.results SET fleet_label = 'Extra', rank = 2, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(20.0 DNC)","R2":"1.0","R3":"3.0"}'::jsonb, total_points_raw = 24.0, nett_points_raw = 4.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21189; -- Ryan Collins 891

UPDATE public.results SET fleet_label = 'Extra', rank = 3, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"2.0","R2":"2.0","R3":"(5.0)"}'::jsonb, total_points_raw = 9.0, nett_points_raw = 4.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21137; -- Ian MacRobert 886

UPDATE public.results SET fleet_label = 'Extra', rank = 4, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"3.0","R2":"(4.0)","R3":"2.0"}'::jsonb, total_points_raw = 9.0, nett_points_raw = 5.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21187; -- Markus Progli 888

UPDATE public.results SET fleet_label = 'Extra', rank = 5, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(6.0)","R2":"3.0","R3":"6.0"}'::jsonb, total_points_raw = 15.0, nett_points_raw = 9.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21140; -- Richard Nankin 881 (PDF Joshua Nankin — SAS name kept)

UPDATE public.results SET fleet_label = 'Extra', rank = 7, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"4.0","R2":"(20.0 DNC)","R3":"7.0"}'::jsonb, total_points_raw = 31.0, nett_points_raw = 11.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21136; -- Henning Kock 892

UPDATE public.results SET fleet_label = 'Extra', rank = 8, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(8.0)","R2":"5.0","R3":"8.0"}'::jsonb, total_points_raw = 21.0, nett_points_raw = 13.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21138; -- Jason Deane 905

UPDATE public.results SET fleet_label = 'Extra', rank = 9, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"7.0","R2":"(20.0 DNC)","R3":"11.0"}'::jsonb, total_points_raw = 38.0, nett_points_raw = 18.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21134; -- David Mair 911

UPDATE public.results SET fleet_label = 'Extra', rank = 10, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"10.0","R2":"(20.0 DNC)","R3":"9.0"}'::jsonb, total_points_raw = 39.0, nett_points_raw = 19.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21133; -- Arran Graham 902

UPDATE public.results SET fleet_label = 'Extra', rank = 11, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"14.0","R2":"(20.0 DNC)","R3":"10.0"}'::jsonb, total_points_raw = 44.0, nett_points_raw = 24.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21176; -- Nicholas Breedt 867

UPDATE public.results SET fleet_label = 'Extra', rank = 12, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"11.0","R2":"(20.0 DNC)","R3":"13.0"}'::jsonb, total_points_raw = 44.0, nett_points_raw = 24.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21135; -- Eugene Julius 913

UPDATE public.results SET fleet_label = 'Extra', rank = 13, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"13.0","R2":"(20.0 DNC)","R3":"12.0"}'::jsonb, total_points_raw = 45.0, nett_points_raw = 25.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21180; -- Aaron Biagio 868

UPDATE public.results SET fleet_label = 'Extra', rank = 14, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(20.0 DNC)","R2":"8.0","R3":"20.0 DNC"}'::jsonb, total_points_raw = 48.0, nett_points_raw = 28.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21188; -- Brent Hayward 878

UPDATE public.results SET fleet_label = 'Extra', rank = 15, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"9.0","R2":"(20.0 DNC)","R3":"20.0 DNC"}'::jsonb, total_points_raw = 49.0, nett_points_raw = 29.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21142; -- Robert Wood 903

UPDATE public.results SET fleet_label = 'Extra', rank = 16, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"16.0","R2":"(20.0 DNC)","R3":"14.0"}'::jsonb, total_points_raw = 50.0, nett_points_raw = 30.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21132; -- Andrew Jones 880

UPDATE public.results SET fleet_label = 'Extra', rank = 17, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"12.0","R2":"(20.0 DNC)","R3":"20.0 DNC"}'::jsonb, total_points_raw = 52.0, nett_points_raw = 32.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21130; -- Alan Everett 875

UPDATE public.results SET fleet_label = 'Extra', rank = 18, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"15.0","R2":"(20.0 DNC)","R3":"20.0 DNC"}'::jsonb, total_points_raw = 55.0, nett_points_raw = 35.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21131; -- Alan Gie 896

UPDATE public.regatta_blocks SET
  fleet_label = 'Extra',
  block_label_raw = 'Extra Fleet',
  races_sailed = 3,
  discard_count = 1,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 19,
  race_column_labels = '["R1","R2","R3"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:extra-fleet';

-- ILCA 4: Joshua Keytel moves here from ILCA 6. DNF = 6 (entries 5 + 1)
UPDATE public.results SET
  block_id = '2026-09-13-zvyc-cape-classic:ilca-4.7-fleet',
  fleet_label = 'ILCA 4',
  class_original = 'ILCA 4',
  class_canonical = 'Ilca 4.7',
  class_id = 8,
  sail_number = '191090',
  club_raw = 'ZVYC',
  rank = 1,
  raced = true,
  races_sailed = 3,
  discard_count = 1,
  ranks_sailed = 3,
  race_scores = '{"R1":"(3.0)","R2":"1.0","R3":"1.0"}'::jsonb,
  total_points_raw = 5.0,
  nett_points_raw = 2.0,
  result_status = 'Provisional',
  as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21149; -- Joshua Keytel

UPDATE public.results SET fleet_label = 'ILCA 4', class_original = 'ILCA 4', rank = 2, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"1.0","R2":"(2.0)","R3":"2.0"}'::jsonb, total_points_raw = 5.0, nett_points_raw = 3.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21145; -- Isabella Keytel

UPDATE public.results SET fleet_label = 'ILCA 4', class_original = 'ILCA 4', rank = 3, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"2.0","R2":"(3.0)","R3":"3.0"}'::jsonb, total_points_raw = 8.0, nett_points_raw = 5.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21182; -- Nathan McCombe

UPDATE public.results SET sail_number = '43947', fleet_label = 'ILCA 4', class_original = 'ILCA 4', rank = 4, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(4.0)","R2":"4.0","R3":"4.0"}'::jsonb, total_points_raw = 12.0, nett_points_raw = 8.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21181; -- Dwayne McCombe (PDF sail 43947)

UPDATE public.results SET fleet_label = 'ILCA 4', class_original = 'ILCA 4', rank = 5, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"5.0","R2":"(6.0 DNF)","R3":"6.0 DNF"}'::jsonb, total_points_raw = 17.0, nett_points_raw = 11.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21146; -- Patrick Jackson

UPDATE public.regatta_blocks SET
  class_original = 'ILCA 4',
  fleet_label = 'ILCA 4',
  block_label_raw = 'ILCA 4 Fleet',
  races_sailed = 3,
  discard_count = 1,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 5,
  race_column_labels = '["R1","R2","R3"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:ilca-4.7-fleet';

-- ILCA 6 (7 boats inc Ross Walton). DNC = 8
UPDATE public.results SET fleet_label = 'ILCA 6', class_original = 'ILCA 6', rank = 1, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(2.0)","R2":"2.0","R3":"1.0"}'::jsonb, total_points_raw = 5.0, nett_points_raw = 3.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21163; -- Aaron Ward

UPDATE public.results SET fleet_label = 'ILCA 6', class_original = 'ILCA 6', rank = 2, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"1.0","R2":"(3.0)","R3":"2.0"}'::jsonb, total_points_raw = 6.0, nett_points_raw = 3.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21179; -- Noah Clulow

UPDATE public.results SET fleet_label = 'ILCA 6', class_original = 'ILCA 6', rank = 3, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(3.0)","R2":"1.0","R3":"3.0"}'::jsonb, total_points_raw = 7.0, nett_points_raw = 4.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21160; -- Blake Madel

UPDATE public.results SET fleet_label = 'ILCA 6', class_original = 'ILCA 6', rank = 4, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(5.0)","R2":"5.0","R3":"4.0"}'::jsonb, total_points_raw = 14.0, nett_points_raw = 9.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21186; -- Richard Carter

INSERT INTO public.results (
  regatta_id, block_id, rank, fleet_label, class_original, class_canonical, class_id,
  sail_number, club_raw, club_id, helm_name, helm_sa_sailing_id,
  races_sailed, discard_count, ranks_sailed, race_scores, total_points_raw, nett_points_raw,
  raced, result_status, as_at_time, row_validation_status, manually_parsed
) VALUES (
  '2026-09-13-zvyc-cape-classic',
  '2026-09-13-zvyc-cape-classic:ilca-6-fleet',
  5, 'ILCA 6', 'ILCA 6', 'Ilca 6', 45,
  '25', 'HYC', 10, 'Ross Walton', '24648',
  3, 1, 3, '{"R1":"(6.0)","R2":"4.0","R3":"5.0"}'::jsonb, 15.0, 9.0,
  true, 'Provisional', TIMESTAMP '2026-09-12 17:46:00', 'validated', false
);

UPDATE public.results SET fleet_label = 'ILCA 6', class_original = 'ILCA 6', rank = 6, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"4.0","R2":"(6.0)","R3":"6.0"}'::jsonb, total_points_raw = 16.0, nett_points_raw = 10.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21148; -- Jens Dugas

UPDATE public.results SET fleet_label = 'ILCA 6', class_original = 'ILCA 6', rank = 7, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(8.0 DNC)","R2":"8.0 DNC","R3":"8.0 DNC"}'::jsonb, total_points_raw = 24.0, nett_points_raw = 16.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21147; -- Jacques Dugas

UPDATE public.regatta_blocks SET
  class_original = 'ILCA 6',
  fleet_label = 'ILCA 6',
  block_label_raw = 'ILCA 6 Fleet',
  races_sailed = 3,
  discard_count = 1,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 7,
  race_column_labels = '["R1","R2","R3"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:ilca-6-fleet';

-- ILCA 7. DNC = 5
UPDATE public.results SET fleet_label = 'ILCA 7', class_original = 'ILCA 7', rank = 1, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(1.0)","R2":"1.0","R3":"1.0"}'::jsonb, total_points_raw = 3.0, nett_points_raw = 2.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21151; -- Alistair Keytel

UPDATE public.results SET fleet_label = 'ILCA 7', class_original = 'ILCA 7', rank = 2, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"(3.0)","R2":"3.0","R3":"2.0"}'::jsonb, total_points_raw = 8.0, nett_points_raw = 5.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21152; -- Dylan le Roux

UPDATE public.results SET fleet_label = 'ILCA 7', class_original = 'ILCA 7', rank = 3, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"4.0","R2":"2.0","R3":"(5.0 DNC)"}'::jsonb, total_points_raw = 11.0, nett_points_raw = 6.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21150; -- Alan Keen

UPDATE public.results SET fleet_label = 'ILCA 7', class_original = 'ILCA 7', rank = 4, raced = true, races_sailed = 3, discard_count = 1, ranks_sailed = 3,
  race_scores = '{"R1":"2.0","R2":"4.0","R3":"(5.0 DNC)"}'::jsonb, total_points_raw = 11.0, nett_points_raw = 6.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21159; -- Peter Wilson

UPDATE public.regatta_blocks SET
  class_original = 'ILCA 7',
  fleet_label = 'ILCA 7',
  block_label_raw = 'ILCA 7 Fleet',
  races_sailed = 3,
  discard_count = 1,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 4,
  race_column_labels = '["R1","R2","R3"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:ilca-7-fleet';

-- Optimist A. DNF = 6
UPDATE public.results SET fleet_label = 'Optimist A', rank = 1, raced = true, races_sailed = 2, discard_count = 0, ranks_sailed = 2,
  race_scores = '{"R1":"1.0","R2":"1.0"}'::jsonb, total_points_raw = 2.0, nett_points_raw = 2.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21153; -- Bazolele Mseswa 1441 (PDF Lele — SAS name kept)

UPDATE public.results SET fleet_label = 'Optimist A', rank = 2, raced = true, races_sailed = 2, discard_count = 0, ranks_sailed = 2,
  race_scores = '{"R1":"2.0","R2":"2.0"}'::jsonb, total_points_raw = 4.0, nett_points_raw = 4.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21162; -- Liam Geldenhuys 1445

UPDATE public.results SET fleet_label = 'Optimist A', rank = 3, raced = true, races_sailed = 2, discard_count = 0, ranks_sailed = 2,
  race_scores = '{"R1":"3.0","R2":"3.0"}'::jsonb, total_points_raw = 6.0, nett_points_raw = 6.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21178; -- Benjamin Fourie 1480

UPDATE public.results SET fleet_label = 'Optimist A', rank = 4, raced = true, races_sailed = 2, discard_count = 0, ranks_sailed = 2,
  race_scores = '{"R1":"6.0 DNF","R2":"4.0"}'::jsonb, total_points_raw = 10.0, nett_points_raw = 10.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21177; -- Sebastian Fourie 1384

UPDATE public.results SET fleet_label = 'Optimist A', rank = 5, raced = true, races_sailed = 2, discard_count = 0, ranks_sailed = 2,
  race_scores = '{"R1":"6.0 DNF","R2":"5.0"}'::jsonb, total_points_raw = 11.0, nett_points_raw = 11.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21183; -- Maximus Taylor 1261

UPDATE public.regatta_blocks SET
  fleet_label = 'Optimist A',
  block_label_raw = 'Optimist A Fleet',
  races_sailed = 2,
  discard_count = 0,
  to_count = 2,
  scoring_system = 'Appendix A',
  entries_raced = 5,
  race_column_labels = '["R1","R2"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:optimist-a-fleet';

-- Optimist B. RET = 4
UPDATE public.results SET fleet_label = 'Optimist B', rank = 1, raced = true, races_sailed = 1, discard_count = 0, ranks_sailed = 1,
  race_scores = '{"R1":"1.0"}'::jsonb, total_points_raw = 1.0, nett_points_raw = 1.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21154; -- Hanwen Lu 348

UPDATE public.results SET fleet_label = 'Optimist B', rank = 2, raced = true, races_sailed = 1, discard_count = 0, ranks_sailed = 1,
  race_scores = '{"R1":"2.0"}'::jsonb, total_points_raw = 2.0, nett_points_raw = 2.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21155; -- Matthew Starke 1267

UPDATE public.results SET fleet_label = 'Optimist B', rank = 3, raced = true, races_sailed = 1, discard_count = 0, ranks_sailed = 1,
  race_scores = '{"R1":"4.0 RET"}'::jsonb, total_points_raw = 4.0, nett_points_raw = 4.0,
  result_status = 'Provisional', as_at_time = TIMESTAMP '2026-09-12 17:46:00'
WHERE result_id = 21184; -- Bastien Taylor 1400

UPDATE public.regatta_blocks SET
  fleet_label = 'Optimist B',
  block_label_raw = 'Optimist B Fleet',
  races_sailed = 1,
  discard_count = 0,
  to_count = 1,
  scoring_system = 'Appendix A',
  entries_raced = 3,
  race_column_labels = '["R1"]'::jsonb
WHERE block_id = '2026-09-13-zvyc-cape-classic:optimist-b-fleet';

COMMIT;
