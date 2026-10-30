-- 2026 ILCA KZN Regional Championships
-- Event page: https://www.laser.org.za/events/364968
-- Results PDF: https://cdn.revolutionise.com.au/site/ltjdspwjl1li4gni.pdf
-- Date-format URL: /regatta/2026-08-10-ilca-kzn-regional-championships
-- Header: generic ILCA class logo left, PYC host logo right (see header_icons JSON).
-- Status line: Results are Provisional as at 10 August 2026 at 17:25
-- Do not invent fleets / regatta_blocks / results — add those when the sheet is passed.
-- Results pass (validated classes only; never family Ilca/Laser):
--   Sheet "ILCA 4" / "Ilca 4" → class_canonical = 'Ilca 4.7'
--   Sheet "ILCA 6" → 'Ilca 6'; sheet "ILCA 7" → 'Ilca 7'
--   fleet_label = class as sailed (same as class_canonical). Not parent "ILCA".

INSERT INTO public.regattas (
  regatta_id,
  event_name,
  year,
  start_date,
  end_date,
  as_at_time,
  result_status,
  host_club_id,
  host_club_code,
  host_club_name,
  province_name,
  import_status,
  source_url
)
SELECT
  '2026-08-10-ilca-kzn-regional-championships',
  'ILCA KZN Regional Championships',
  2026,
  DATE '2026-08-08',
  DATE '2026-08-10',
  TIMESTAMPTZ '2026-08-10 17:25:00+02',
  'Provisional',
  c.club_id,
  c.club_abbrev,
  c.club_fullname,
  'KZN',
  'manual',
  'https://cdn.revolutionise.com.au/site/ltjdspwjl1li4gni.pdf'
FROM public.clubs c
WHERE UPPER(TRIM(c.club_abbrev)) = 'PYC'
LIMIT 1
ON CONFLICT (regatta_id) DO UPDATE SET
  event_name = EXCLUDED.event_name,
  year = EXCLUDED.year,
  start_date = EXCLUDED.start_date,
  end_date = EXCLUDED.end_date,
  as_at_time = EXCLUDED.as_at_time,
  result_status = EXCLUDED.result_status,
  host_club_id = EXCLUDED.host_club_id,
  host_club_code = EXCLUDED.host_club_code,
  host_club_name = EXCLUDED.host_club_name,
  province_name = EXCLUDED.province_name,
  import_status = EXCLUDED.import_status,
  source_url = EXCLUDED.source_url;

UPDATE public.events
SET regatta_id = '2026-08-10-ilca-kzn-regional-championships'
WHERE TRIM(event_name) = '2026 ILCA KZN Regional Championships'
  AND start_date = DATE '2026-08-08';
