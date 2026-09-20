#!/usr/bin/env python3
"""Create / match HMYC Dart 18 Nationals Event URL (live DB).

Event URL: /regatta/2026-09-24-hmyc-dart-18-nationals
Source: https://www.hmyc.org.za/events/367984
Inherits HMYC cards from /regatta/2026-09-19-hmyc-midmar-cup

Landing search reads public.regattas (GET /api/regattas/with-counts).
Hub upcoming-with-history needs events.regatta_id plus series key
"dart 18 nationals" (same pattern as 420 Nationals → 2026-09-25-tsc-420-nationals).

Until this script is applied on live, the calendar row stays rid=null,
search misses 2026, and the hub card has no Event URL / prior-year entries.

On the live box (see sailingsa/deploy/SSH_LIVE.md):

  export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
  python3 /var/www/sailingsa/deploy/create_2026_hmyc_dart_18_nationals.py --apply
"""

from __future__ import annotations

import os
import sys

SLUG = "2026-09-24-hmyc-dart-18-nationals"
SOURCE_EVENT_ID = "367984"
EVENT_NAME = "Dart 18 Nationals incorporating the KZN provincials"

SQL = """
BEGIN;

INSERT INTO public.regattas (
    regatta_id,
    event_name,
    year,
    start_date,
    end_date,
    as_at_time,
    result_status,
    host_club_id,
    province_name,
    import_status,
    regatta_number
)
SELECT
    '2026-09-24-hmyc-dart-18-nationals',
    'Dart 18 Nationals incorporating the KZN provincials',
    2026,
    DATE '2026-09-24',
    DATE '2026-09-27',
    TIMESTAMPTZ '2026-09-24 11:00:00+02',
    'Provisional',
    c.club_id,
    COALESCE(NULLIF(TRIM(c.province), ''), 'KZN'),
    'manual',
    999010
FROM public.clubs c
WHERE UPPER(TRIM(c.club_abbrev)) = 'HMYC'
ORDER BY c.club_id
LIMIT 1
ON CONFLICT (regatta_id) DO UPDATE
SET
    event_name = EXCLUDED.event_name,
    year = EXCLUDED.year,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date,
    as_at_time = EXCLUDED.as_at_time,
    result_status = EXCLUDED.result_status,
    host_club_id = EXCLUDED.host_club_id,
    province_name = EXCLUDED.province_name,
    regatta_number = COALESCE(public.regattas.regatta_number, EXCLUDED.regatta_number);

DO $$
DECLARE
  has_handicap BOOLEAN;
  has_scoring BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'regatta_blocks' AND column_name = 'handicap_system'
  ) INTO has_handicap;
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'regatta_blocks' AND column_name = 'scoring_system'
  ) INTO has_scoring;

  IF has_handicap AND has_scoring THEN
    INSERT INTO public.regatta_blocks (
      block_id, regatta_id, class_original, class_canonical, fleet_label,
      races_sailed, discard_count, to_count, handicap_system, scoring_system, block_label_raw
    ) VALUES (
      '2026-09-24-hmyc-dart-18-nationals:dart-18',
      '2026-09-24-hmyc-dart-18-nationals',
      'Dart 18', 'Dart 18', 'Dart 18',
      0, 0, 0, 'Appendix A', 'Appendix A', 'Dart 18 Fleet'
    )
    ON CONFLICT (block_id) DO UPDATE SET
      class_original = EXCLUDED.class_original,
      class_canonical = EXCLUDED.class_canonical,
      fleet_label = EXCLUDED.fleet_label,
      handicap_system = EXCLUDED.handicap_system,
      scoring_system = EXCLUDED.scoring_system,
      block_label_raw = EXCLUDED.block_label_raw;
  ELSIF has_scoring THEN
    INSERT INTO public.regatta_blocks (
      block_id, regatta_id, class_original, class_canonical, fleet_label,
      races_sailed, discard_count, to_count, scoring_system, block_label_raw
    ) VALUES (
      '2026-09-24-hmyc-dart-18-nationals:dart-18',
      '2026-09-24-hmyc-dart-18-nationals',
      'Dart 18', 'Dart 18', 'Dart 18',
      0, 0, 0, 'Appendix A', 'Dart 18 Fleet'
    )
    ON CONFLICT (block_id) DO UPDATE SET
      class_original = EXCLUDED.class_original,
      class_canonical = EXCLUDED.class_canonical,
      fleet_label = EXCLUDED.fleet_label,
      scoring_system = EXCLUDED.scoring_system,
      block_label_raw = EXCLUDED.block_label_raw;
  ELSE
    INSERT INTO public.regatta_blocks (
      block_id, regatta_id, class_original, class_canonical, fleet_label,
      races_sailed, discard_count, to_count, handicap_system, block_label_raw
    ) VALUES (
      '2026-09-24-hmyc-dart-18-nationals:dart-18',
      '2026-09-24-hmyc-dart-18-nationals',
      'Dart 18', 'Dart 18', 'Dart 18',
      0, 0, 0, 'Appendix A', 'Dart 18 Fleet'
    )
    ON CONFLICT (block_id) DO UPDATE SET
      class_original = EXCLUDED.class_original,
      class_canonical = EXCLUDED.class_canonical,
      fleet_label = EXCLUDED.fleet_label,
      handicap_system = EXCLUDED.handicap_system,
      block_label_raw = EXCLUDED.block_label_raw;
  END IF;
END $$;

UPDATE public.events
SET regatta_id = '2026-09-24-hmyc-dart-18-nationals'
WHERE (
    CAST(source_event_id AS TEXT) = '367984'
    OR COALESCE(source_url, '') ILIKE '%/events/367984%'
    OR COALESCE(event_name, '') ILIKE 'Dart 18 Nationals incorporating the KZN provincials'
    OR (
        COALESCE(event_name, '') ILIKE '%Dart 18 Nationals%'
        AND start_date = DATE '2026-09-24'
    )
)
AND (regatta_id IS NULL OR BTRIM(regatta_id) = '');

COMMIT;
"""


def main() -> int:
    apply = "--apply" in sys.argv
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not apply:
        sys.stdout.write(SQL)
        return 0
    if not url:
        sys.stderr.write("Set DB_URL or DATABASE_URL first (see sailingsa/deploy/SSH_LIVE.md).\n")
        return 2
    import subprocess

    r = subprocess.run(["psql", url, "-v", "ON_ERROR_STOP=1"], input=SQL, text=True)
    if r.returncode != 0:
        return r.returncode
    print("ok", SLUG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
