#!/usr/bin/env python3
"""Per-event admin flag: show or hide WhatsApp messages on the event page.

Column: event_whatsapp_groups.show_on_event
Copy:   events.extras.whatsapp.show_on_event

Cape Classic first migrate turns it ON (icon already live for testing).
Later deploys do not override an admin Hide.
"""
from __future__ import annotations

import subprocess
import sys

DDL = r"""
ALTER TABLE public.event_whatsapp_groups
  ADD COLUMN IF NOT EXISTS show_on_event boolean NOT NULL DEFAULT false;

UPDATE public.event_whatsapp_groups g
SET show_on_event = true
FROM public.events e
WHERE e.event_id = g.event_id
  AND g.is_current
  AND g.regatta_id = '2026-09-13-zvyc-cape-classic'
  AND (e.extras -> 'whatsapp' -> 'show_on_event') IS NULL;

UPDATE public.events e
SET extras = COALESCE(e.extras, '{}'::jsonb) || jsonb_build_object(
  'whatsapp',
  COALESCE(e.extras->'whatsapp', '{}'::jsonb)
    || jsonb_build_object('show_on_event', to_jsonb(g.show_on_event))
)
FROM public.event_whatsapp_groups g
WHERE e.event_id = g.event_id
  AND g.is_current
  AND g.regatta_id = '2026-09-13-zvyc-cape-classic';
"""


def main() -> int:
    r = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1"],
        input=DDL,
        text=True,
        capture_output=True,
    )
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
