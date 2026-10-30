#!/usr/bin/env python3
"""Ingest event WhatsApp group inbox.jsonl into Postgres. Keep everything.

Kinds stored: text, voice, photo, video, audio, other, empty, group-list.
Usage:
  python3 event_whatsapp_ingest.py           # one pass
  python3 event_whatsapp_ingest.py --watch
"""
from __future__ import annotations

import json
import os
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
    (
      g.regatta_id = '2026-10-10-hmyc-dam-bottle-sprints'
      AND (
        lower({sql_str(subject)}) LIKE '%event media%'
        OR lower({sql_str(subject)}) LIKE '%hmyc media%'
        OR lower({sql_str(subject)}) LIKE '%dam bottle%'
        OR lower({sql_str(subject)}) LIKE '%sprints%'
      )
    ) OR (
      g.regatta_id <> '2026-10-10-hmyc-dam-bottle-sprints'
      AND (
        lower({sql_str(subject)}) LIKE '%cape classic%'
        OR lower({sql_str(subject)}) LIKE '%zvyc%'
        OR lower({sql_str(subject)}) LIKE '%midmar%'
        OR lower({sql_str(subject)}) LIKE '%' || lower(COALESCE(g.event_name_snapshot,'')) || '%'
      )
    )
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
  AND g.regatta_id IN (
    '2026-09-13-zvyc-cape-classic',
    '2026-09-19-hmyc-midmar-cup',
    '2026-10-10-hmyc-dam-bottle-sprints'
  )
  AND g.group_jid IS NOT NULL;
"""
    )



MEDIA_DIR = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/media")
MM_RID = "2026-09-19-hmyc-midmar-cup"
MM_STATIC = Path("/var/www/sailingsa")


DART_WA_JID = "120363426250399531@g.us"
DART_WA_RID = "2026-09-24-hmyc-dart-18-nationals"
DAM_WA_RID = "2026-10-10-hmyc-dam-bottle-sprints"

def maybe_post_midmar_mm_clip(o: dict) -> None:
    cap = str(o.get("caption") or o.get("body") or "")
    if cap.lower().startswith("leader board"):
        return
    """Copy a group photo/video onto the event media card."""
    from datetime import datetime as _dt, timezone as _tz
    from zoneinfo import ZoneInfo as _ZI
    _sast = _ZI("Africa/Johannesburg")
    kind = o.get("kind") or ""
    if kind not in ("photo", "video"):
        return
    jid = str(o.get("group_jid") or "")
    rid = psql(
        f"""SELECT COALESCE(regatta_id,'') FROM public.event_whatsapp_groups
            WHERE is_current AND group_jid = {sql_str(jid)} LIMIT 1;"""
    ).strip()
    _is_dart = rid == DART_WA_RID or jid == DART_WA_JID
    _is_dam = rid == DAM_WA_RID
    _is_mm = rid == MM_RID
    if not (_is_dart or _is_dam or _is_mm):
        return
    _cutoff = _dt(2026, 9, 20, 18, 0, tzinfo=_sast)
    _dart_open = _dt(2026, 9, 24, 0, 0, tzinfo=_sast)
    _dart_close = _dt(2026, 9, 27, 23, 59, tzinfo=_sast)
    _dam_open = _dt(2026, 10, 10, 0, 0, tzinfo=_sast)
    _dam_close = _dt(2026, 10, 12, 23, 59, tzinfo=_sast)
    _now = _dt.now(_sast)
    if _is_dart:
        if _now < _dart_open or _now > _dart_close:
            return
    elif _is_dam:
        if _now < _dam_open or _now > _dam_close:
            return
    elif _now >= _cutoff:  # MIDMAR_DROP_1801_v1
        return
    _occ = o.get("occurred_at") or o.get("t")
    try:
        _ms = int(_occ)
        if _ms < 10**12:
            _ms *= 1000
        _when = _dt.fromtimestamp(_ms / 1000, tz=_tz.utc).astimezone(_sast)
        if _is_dart:
            if _when < _dart_open or _when > _dart_close:
                return
        elif _is_dam:
            if _when < _dam_open or _when > _dam_close:
                return
        elif _when > _cutoff:
            return
    except Exception:
        pass
    if rid == DART_WA_RID or rid == DAM_WA_RID:
        pass
    elif rid != MM_RID:
        return
    fname = o.get("media_filename") or ""
    src = MEDIA_DIR / fname
    if not fname or not src.is_file():
        return
    body = src.read_bytes()
    if not body:
        return
    _fallback = "Dam Bottle" if _is_dam else ("Dart 18" if _is_dart else "Midmar")
    label = (o.get("caption") or o.get("body") or o.get("sender_name") or _fallback).strip()[:120] or _fallback
    occurred = o.get("occurred_at")
    started = ""
    try:
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI
        _sast = _ZI("Africa/Johannesburg")
        if kind == "photo":
            from PIL import Image
            from PIL.ExifTags import TAGS
            from io import BytesIO
            _im = Image.open(BytesIO(body))
            _exif = _im.getexif() or {}
            for _k, _v in _exif.items():
                if TAGS.get(_k) == "DateTimeOriginal" and _v:
                    started = _dt.strptime(str(_v), "%Y:%m:%d %H:%M:%S").replace(tzinfo=_sast).isoformat()
                    break
        elif kind == "video":
            import subprocess, tempfile, os
            _tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            try:
                _tmp.write(body)
                _tmp.close()
                _pr = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", _tmp.name], capture_output=True, text=True, timeout=20)
                _tags = (json.loads(_pr.stdout or "{}").get("format") or {}).get("tags") or {}
                _ct = _tags.get("creation_time") or ""
                if _ct:
                    started = _dt.fromisoformat(_ct.replace("Z", "+00:00")).astimezone(_sast).isoformat()
            finally:
                os.unlink(_tmp.name)
    except Exception:
        started = ""
    if not started and occurred:
        try:
            started = __import__("datetime").datetime.fromtimestamp(int(occurred) / 1000, tz=__import__("datetime").timezone.utc).isoformat()
        except Exception:
            started = ""
    w = h = 0
    if kind == "photo":
        try:
            from PIL import Image
            from io import BytesIO
            im = Image.open(BytesIO(body))
            w, h = im.size
        except Exception:
            w, h = 1280, 720
    else:
        w, h = 1280, 720
    import sys
    sys.path.insert(0, "/var/www/sailingsa")
    from sailingsa.backend.mm_event_clips import clip_from_upload
    clip_from_upload(
        rid=rid,
        filename=fname,
        content_type=o.get("media_mime") or ("image/jpeg" if kind == "photo" else "video/mp4"),
        body=body,
        thumb_body=None,
        thumb_name="",
        label=label,
        started_at_raw=started,
        width=w,
        height=h,
        static_dir=MM_STATIC,
    )
    print("midmar mm-clip", label, fname)

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
ON CONFLICT (group_jid, wa_message_id) DO UPDATE SET
  kind = EXCLUDED.kind,
  body = COALESCE(NULLIF(EXCLUDED.body, ''), event_whatsapp_messages.body),
  caption = COALESCE(NULLIF(EXCLUDED.caption, ''), event_whatsapp_messages.caption),
  media_mime = COALESCE(EXCLUDED.media_mime, event_whatsapp_messages.media_mime),
  media_filename = COALESCE(EXCLUDED.media_filename, event_whatsapp_messages.media_filename),
  media_relpath = COALESCE(EXCLUDED.media_relpath, event_whatsapp_messages.media_relpath),
  media_bytes = COALESCE(EXCLUDED.media_bytes, event_whatsapp_messages.media_bytes),
  duration_sec = COALESCE(EXCLUDED.duration_sec, event_whatsapp_messages.duration_sec),
  media_error = EXCLUDED.media_error,
  sender_name = COALESCE(NULLIF(EXCLUDED.sender_name, ''), event_whatsapp_messages.sender_name),
  event_whatsapp_id = COALESCE(EXCLUDED.event_whatsapp_id, event_whatsapp_messages.event_whatsapp_id),
  regatta_id = COALESCE(EXCLUDED.regatta_id, event_whatsapp_messages.regatta_id)
WHERE event_whatsapp_messages.kind IN ('empty', 'other')
   OR length(COALESCE(EXCLUDED.body, '')) > length(COALESCE(event_whatsapp_messages.body, ''));
"""
    )

    try:
        maybe_post_midmar_mm_clip(o)
    except Exception as e:
        print('midmar mm-clip skip', e, file=sys.stderr)


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


SHOW_DDL = r"""
ALTER TABLE public.event_whatsapp_groups
  ADD COLUMN IF NOT EXISTS show_on_event boolean NOT NULL DEFAULT false;
GRANT SELECT, INSERT, UPDATE ON public.event_whatsapp_groups TO sailors_user;
GRANT SELECT, INSERT, UPDATE ON public.event_whatsapp_messages TO sailors_user;
"""


def ensure_ddl() -> None:
    global _ddl_done
    if _ddl_done:
        return
    psql(MESSAGES_DDL)
    psql(SHOW_DDL)
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


LIVE_JSON = Path("/var/www/sailingsa/js/event-whatsapp-live.json")
DUMP_SQL = r"""
SELECT json_build_object(
  'ok', true,
  'regatta_id', '2026-09-13-zvyc-cape-classic',
  'show', COALESCE((
    SELECT g.show_on_event
    FROM public.event_whatsapp_groups g
    WHERE g.regatta_id = '2026-09-13-zvyc-cape-classic' AND g.is_current
    LIMIT 1
  ), false),
  'messages', '[]'::json
);
"""


def dump_live_json() -> None:
    raw = (psql(DUMP_SQL) or "").strip()
    if not raw:
        return
    LIVE_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = LIVE_JSON.with_suffix(".json.tmp")
    tmp.write_text(raw + "\n", encoding="utf-8")
    tmp.replace(LIVE_JSON)
    try:
        os.chmod(LIVE_JSON, 0o644)
    except Exception:
        pass


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
    force_dump = "--dump" in sys.argv
    while True:
        try:
            n = one_pass()
            if n:
                print("ingested", n, flush=True)
            try:
                if n or force_dump or not LIVE_JSON.exists():
                    dump_live_json()
            except Exception as dump_err:
                print("live json", dump_err, file=sys.stderr, flush=True)
        except Exception as e:
            print("ingest error", e, file=sys.stderr, flush=True)
        if not watch:
            return 0
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
