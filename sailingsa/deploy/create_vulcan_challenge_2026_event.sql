-- Create SailingSA Event URL for VULCAN Challenge 2026
-- Planned Saturday 12 Sep 2026; postponed and sailed Sunday 13 Sep 2026.
-- Standard URL: /regatta/YYYY-MM-DD-slug
-- Results will be loaded in a later pass.

BEGIN;

INSERT INTO public.regattas (
    regatta_id,
    event_name,
    year,
    host_club_id,
    host_club_code,
    host_club_name,
    start_date,
    end_date,
    result_status,
    source_url,
    import_status,
    class_layout,
    scoring_system,
    scoring_mode
) VALUES (
    '2026-09-13-vulcan-challenge',
    '2026 VULCAN Challenge',
    2026,
    8,
    'HBYC',
    'Hout Bay Yacht Club',
    '2026-09-13',
    '2026-09-13',
    'event_page',
    'https://www.sailing.org.za/events/370405',
    'pending',
    'single',
    'Appendix A',
    'appendix_a_low_point'
)
ON CONFLICT (regatta_id) DO UPDATE SET
    event_name = EXCLUDED.event_name,
    year = EXCLUDED.year,
    host_club_id = EXCLUDED.host_club_id,
    host_club_code = EXCLUDED.host_club_code,
    host_club_name = EXCLUDED.host_club_name,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date,
    result_status = EXCLUDED.result_status,
    source_url = EXCLUDED.source_url,
    updated_at = now();

UPDATE public.events
SET regatta_id = '2026-09-13-vulcan-challenge',
    start_date = '2026-09-13',
    end_date = '2026-09-13'
WHERE event_id = 152787
  AND lower(event_name) LIKE '%vulcan%';

COMMIT;

-- Verify
SELECT r.regatta_id, r.event_name, r.start_date, r.end_date, r.host_club_code, r.result_status, r.source_url
FROM public.regattas r
WHERE r.regatta_id = '2026-09-13-vulcan-challenge';

SELECT e.event_id, e.event_name, e.start_date, e.end_date, e.regatta_id, e.source_url
FROM public.events e
WHERE e.event_id = 152787;
