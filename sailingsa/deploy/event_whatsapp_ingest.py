#!/usr/bin/env python3
"""Ingest event WhatsApp group inbox.jsonl into Postgres. Keep everything.

Kinds stored: text, voice, photo, video, audio, other, empty, group-list.
Usage:
  python3 event_whatsapp_ingest.py           # one pass
  python3 event_whatsapp_ingest.py --watch
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

INBOX = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/inbox.jsonl")
OFFSET = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/ingest.offset")
GROUPS = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/groups.json")

MESSAGES_DDL = r"""
CREATE TABLE IF NOT EXISTS public.event_whatsapp_messages (
  message_id bigserial PRIMARY KEY,
  event_whatsapp_id bigint,
  regatta_id text,
  group_jid text NOT NULL,
  wa_message_id text NOT NULL,
  from_me boolean,
  sender_jid text,
  sender_name text,
  kind text NOT NULL,
  body text,
  caption text,
  media_mime text,
  media_filename text,
  media_relpath text,
  media_bytes integer,
  duration_sec integer,
  media_error text,
  occurred_at timestamptz,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (group_jid, wa_message_id)
);
CREATE INDEX IF NOT EXISTS event_whatsapp_messages_regatta_idx
  ON public.event_whatsapp_messages (regatta_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS event_whatsapp_messages_group_idx
  ON public.event_whatsapp_messages (group_jid, occurred_at DESC);
"""


def psql(sql: str) -> str:
    r = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1", "-At"],
        input=sql,
        text=True,
        capture_output=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return r.stdout


def sql_str(v) -> str:
    if v is None:
        return "NULL"
    s = str(v).replace("'", "''")
    return "'" + s + "'"


def bind_group_to_live_event(jid: str, subject: str, force: bool = False) -> None:
    if not jid:
        return
    extra = "true" if force else f"""(
    lower({sql_str(subject)}) LIKE '%cape classic%'
    OR lower({sql_str(subject)}) LIKE '%zvyc%'
    OR lower({sql_str(subject)}) LIKE '%' || lower(COALESCE(g.event_name_snapshot,'')) || '%'
  )"""
    psql(
        f"""
UPDATE public.event_whatsapp_groups g
SET group_jid = {sql_str(jid)},
    group_name = COALESCE(NULLIF({sql_str(subject)}, ''), g.group_name)
WHERE g.is_current
  AND g.group_jid IS NULL
  AND CURRENT_DATE BETWEEN g.valid_from AND g.valid_until
  AND {extra};

UPDATE public.events e
SET extras = COALESCE(e.extras, '{{}}'::jsonb) || jsonb_build_object(
  'whatsapp', COALESCE(e.extras->'whatsapp', '{{}}'::jsonb) || jsonb_build_object(
    'group_jid', g.group_jid,
    'group_name', g.group_name
  )
)
FROM public.event_whatsapp_groups g
WHERE e.event_id = g.event_id
  AND g.regatta_id = '2026-09-13-zvyc-cape-classic'
  AND g.group_jid IS NOT NULL;
"""
    )


def ingest_line(o: dict) -> None:
    kind = o.get("kind") or "other"
    if kind == "group-list":
        groups = o.get("groups") or []
        for g in groups:
            bind_group_to_live_event(str(g.get("jid") or ""), str(g.get("subject") or ""))
        return
    jid = o.get("group_jid") or ""
    mid = o.get("wa_message_id") or ""
    if not jid or not mid:
        return
    occurred = o.get("occurred_at") or o.get("t")
    occurred_sql = "NULL"
    try:
        ms = int(occurred)
        if ms < 10**12:
            ms *= 1000
        occurred_sql = f"to_timestamp({ms / 1000.0})"
    except Exception:
        occurred_sql = "now()"
    mb = int(o["media_bytes"]) if o.get("media_bytes") is not None else None
    dur = int(o["duration_sec"]) if o.get("duration_sec") is not None else None
    psql(
        f"""
INSERT INTO public.event_whatsapp_messages (
  event_whatsapp_id, regatta_id, group_jid, wa_message_id, from_me,
  sender_jid, sender_name, kind, body, caption,
  media_mime, media_filename, media_relpath, media_bytes, duration_sec, media_error, occurred_at
) VALUES (
  (SELECT event_whatsapp_id FROM public.event_whatsapp_groups
    WHERE is_current AND group_jid = {sql_str(jid)} LIMIT 1),
  (SELECT regatta_id FROM public.event_whatsapp_groups
    WHERE is_current AND group_jid = {sql_str(jid)} LIMIT 1),
  {sql_str(jid)}, {sql_str(mid)}, {('true' if o.get('from_me') else 'false')},
  {sql_str(o.get('sender_jid'))}, {sql_str(o.get('sender_name'))}, {sql_str(kind)},
  {sql_str(o.get('body'))}, {sql_str(o.get('caption'))},
  {sql_str(o.get('media_mime'))}, {sql_str(o.get('media_filename'))}, {sql_str(o.get('media_relpath'))},
  {mb if mb is not None else 'NULL'},
  {dur if dur is not None else 'NULL'},
  {sql_str(o.get('media_error'))}, {occurred_sql}
)
ON CONFLICT (group_jid, wa_message_id) DO NOTHING;
"""
    )


def read_offset() -> int:
    try:
        return int(OFFSET.read_text().strip() or "0")
    except Exception:
        return 0


def write_offset(n: int) -> None:
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    OFFSET.write_text(str(n))


_ddl_done = False
_groups_mtime = None


def ensure_ddl() -> None:
    global _ddl_done
    if _ddl_done:
        return
    psql(MESSAGES_DDL)
    _ddl_done = True


def maybe_bind_groups_file() -> None:
    global _groups_mtime
    if not GROUPS.exists():
        return
    mt = GROUPS.stat().st_mtime
    if _groups_mtime is not None and mt <= _groups_mtime:
        return
    _groups_mtime = mt
    try:
        data = json.loads(GROUPS.read_text())
        groups = data.get("groups") or []
        for g in groups:
            bind_group_to_live_event(str(g.get("jid") or ""), str(g.get("subject") or ""))
            pass
    except Exception as e:
        print("groups.json", e, file=sys.stderr)


def one_pass() -> int:
    ensure_ddl()
    maybe_bind_groups_file()
    if not INBOX.exists():
        return 0
    off = read_offset()
    n = 0
    with INBOX.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(off)
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                write_offset(pos)
                break
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            ingest_line(o)
            n += 1
            write_offset(f.tell())
    return n


def main() -> int:
    watch = "--watch" in sys.argv
    while True:
        try:
            n = one_pass()
            if n:
                print("ingested", n, flush=True)
        except Exception as e:
            print("ingest error", e, file=sys.stderr, flush=True)
        if not watch:
            return 0
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
