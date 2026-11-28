#!/usr/bin/env python3
"""Event WhatsApp groups — store every event group; use only while live.

Plan (later: they will say how the event page uses these):
- One row per assignment in public.event_whatsapp_groups (never delete after the event).
- events.extras.whatsapp is the copy on the event row.
- Active for use only when CURRENT_DATE is in [valid_from, valid_until]
  (event period / while live). History stays queryable with is_live=false.

This weekend: ZVYC Cape Classic (event_id 202735, regatta 2026-09-13-zvyc-cape-classic)
uses SailingSA monitor 27762639937. Group JID/invite still unknown — fill when known.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

DDL = r"""
CREATE TABLE IF NOT EXISTS public.event_whatsapp_groups (
  event_whatsapp_id bigserial PRIMARY KEY,
  event_id integer,
  regatta_id text,
  event_name_snapshot text,
  group_jid text,
  group_invite_url text,
  group_name text,
  display_number text,
  monitor_number text,
  valid_from date NOT NULL,
  valid_until date NOT NULL,
  is_current boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  retired_at timestamptz,
  notes text,
  show_on_event boolean NOT NULL DEFAULT false,
  CONSTRAINT event_whatsapp_groups_window CHECK (valid_until >= valid_from)
);

CREATE INDEX IF NOT EXISTS event_whatsapp_groups_event_id_idx
  ON public.event_whatsapp_groups (event_id);
CREATE INDEX IF NOT EXISTS event_whatsapp_groups_regatta_id_idx
  ON public.event_whatsapp_groups (regatta_id);
CREATE INDEX IF NOT EXISTS event_whatsapp_groups_live_idx
  ON public.event_whatsapp_groups (valid_from, valid_until)
  WHERE is_current;

CREATE OR REPLACE VIEW public.event_whatsapp_groups_live AS
SELECT
  g.*,
  (g.is_current
   AND CURRENT_DATE >= g.valid_from
   AND CURRENT_DATE <= g.valid_until) AS is_live
FROM public.event_whatsapp_groups g;
"""

CAPE_CLASSIC = {
    "event_id": 202735,
    "regatta_id": "2026-09-13-zvyc-cape-classic",
    "event_name_snapshot": "ZVYC Cape Classic",
    "group_jid": None,
    "group_invite_url": None,
    "group_name": None,
    "display_number": "27762639937",
    "monitor_number": "27762639937",
    "valid_from": date(2026, 9, 12),
    "valid_until": date(2026, 9, 13),
    "notes": (
        "SailingSA WhatsApp 076 263 9937 added to the event group. "
        "Group JID / invite not stored yet. Usable only 12–13 Sep 2026."
    ),
}


def whatsapp_is_live(valid_from: date, valid_until: date, today: Optional[date] = None) -> bool:
    """True only during the event window (inclusive)."""
    today = today or date.today()
    return valid_from <= today <= valid_until


def public_payload(row: dict[str, Any], today: Optional[date] = None) -> Optional[dict[str, Any]]:
    """What the event may use now. None outside the live window (row is still in DB)."""
    vf = row.get("valid_from")
    vu = row.get("valid_until")
    if not vf or not vu:
        return None
    if not whatsapp_is_live(vf, vu, today):
        return None
    return {
        "group_jid": row.get("group_jid"),
        "group_invite_url": row.get("group_invite_url"),
        "group_name": row.get("group_name"),
        "display_number": row.get("display_number"),
        "monitor_number": row.get("monitor_number"),
        "valid_from": str(vf),
        "valid_until": str(vu),
        "is_live": True,
        "wa_me": (
            "https://wa.me/" + str(row.get("display_number") or row.get("monitor_number") or "").replace("+", "")
            if (row.get("display_number") or row.get("monitor_number"))
            else None
        ),
    }


SEED_SQL = r"""
INSERT INTO public.event_whatsapp_groups (
  event_id, regatta_id, event_name_snapshot,
  group_jid, group_invite_url, group_name,
  display_number, monitor_number,
  valid_from, valid_until, is_current, notes
)
SELECT
  202735,
  '2026-09-13-zvyc-cape-classic',
  'ZVYC Cape Classic',
  NULL,
  NULL,
  NULL,
  '27762639937',
  '27762639937',
  DATE '2026-09-12',
  DATE '2026-09-13',
  true,
  'SailingSA WhatsApp 076 263 9937 added to the event group. Group JID / invite not stored yet. Usable only 12–13 Sep 2026.'
WHERE NOT EXISTS (
  SELECT 1 FROM public.event_whatsapp_groups
  WHERE is_current
    AND regatta_id = '2026-09-13-zvyc-cape-classic'
);

UPDATE public.events
SET extras = COALESCE(extras, '{}'::jsonb) || jsonb_build_object(
  'whatsapp', jsonb_build_object(
    'display_number', '27762639937',
    'monitor_number', '27762639937',
    'group_jid', NULL,
    'group_invite_url', NULL,
    'group_name', NULL,
    'valid_from', '2026-09-12',
    'valid_until', '2026-09-13',
    'active_only_when_live', true
  )
)
WHERE event_id = 202735;
"""


def main() -> int:
    import subprocess
    import sys

    sql = DDL + "\n" + SEED_SQL + r"""
SELECT event_whatsapp_id, event_id, regatta_id, display_number,
       valid_from, valid_until,
       (is_current AND CURRENT_DATE BETWEEN valid_from AND valid_until) AS is_live
FROM public.event_whatsapp_groups
WHERE regatta_id = '2026-09-13-zvyc-cape-classic';

SELECT event_id, extras->'whatsapp' AS whatsapp
FROM public.events WHERE event_id = 202735;
"""
    r = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1"],
        input=sql,
        text=True,
        capture_output=True,
    )
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
