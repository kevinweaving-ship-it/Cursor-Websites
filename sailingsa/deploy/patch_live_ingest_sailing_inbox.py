#!/usr/bin/env python3
"""Drain SSA/TA sailing WhatsApp inbox + media into event_whatsapp_ingest.

Live ingest historically only read the Arial (GW/AN 076) inbox/media dir.
MAC Event Media is on the sailing box (060 856 0172). This adds a second
drain + media lookup without changing Arial behaviour.

Run on the box:
  python3 /opt/arial-whatsapp-poc/patch_live_ingest_sailing_inbox.py
  systemctl restart event-whatsapp-ingest
"""
from __future__ import annotations

from pathlib import Path

INGEST = Path("/opt/arial-whatsapp-poc/event_whatsapp_ingest.py")


def apply(text: str) -> str:
    old_const = (
        'INBOX = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/inbox.jsonl")\n'
        'OFFSET = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/ingest.offset")\n'
        'GROUPS = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/groups.json")\n'
    )
    new_const = (
        'INBOX = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/inbox.jsonl")\n'
        'INBOX_SAILING = Path("/opt/sailingsa-whatsapp-poc/state/event-whatsapp/inbox.jsonl")\n'
        'OFFSET = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/ingest.offset")\n'
        'OFFSET_SAILING = Path("/opt/sailingsa-whatsapp-poc/state/event-whatsapp/ingest.offset")\n'
        'GROUPS = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/groups.json")\n'
        'GROUPS_SAILING = Path("/opt/sailingsa-whatsapp-poc/state/event-whatsapp/groups.json")\n'
    )
    if "INBOX_SAILING" not in text:
        if old_const not in text:
            raise SystemExit("const block missing")
        text = text.replace(old_const, new_const, 1)
        print("patch constants")
    else:
        print("skip constants: already present")

    old_media = 'MEDIA_DIR = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/media")\n'
    new_media = (
        'MEDIA_DIR = Path("/opt/arial-whatsapp-poc/state/event-whatsapp/media")\n'
        'MEDIA_DIR_SAILING = Path("/opt/sailingsa-whatsapp-poc/state/event-whatsapp/media")\n'
    )
    if "MEDIA_DIR_SAILING" not in text:
        if old_media not in text:
            raise SystemExit("MEDIA_DIR missing")
        text = text.replace(old_media, new_media, 1)
        print("patch MEDIA_DIR_SAILING")
    else:
        print("skip MEDIA_DIR_SAILING: already present")

    old_src = (
        '    fname = o.get("media_filename") or ""\n'
        "    src = MEDIA_DIR / fname\n"
        "    if not fname or not src.is_file():\n"
        "        return\n"
    )
    new_src = (
        '    fname = o.get("media_filename") or ""\n'
        "    src = None\n"
        "    if fname:\n"
        "        for _mdir in (MEDIA_DIR, MEDIA_DIR_SAILING):\n"
        "            _cand = _mdir / fname\n"
        "            if _cand.is_file():\n"
        "                src = _cand\n"
        "                break\n"
        "    if not fname or src is None:\n"
        "        return\n"
    )
    if "for _mdir in (MEDIA_DIR, MEDIA_DIR_SAILING)" in text:
        print("skip src lookup: already present")
    elif old_src not in text:
        raise SystemExit("src lookup missing")
    else:
        text = text.replace(old_src, new_src, 1)
        print("patch src lookup")

    old_one = '''def one_pass() -> int:
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
'''
    new_one = '''def _drain(inbox: Path, offset_path: Path) -> int:
    if not inbox.exists():
        return 0
    try:
        off = int(offset_path.read_text().strip() or "0")
    except Exception:
        off = 0
    n = 0
    with inbox.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(off)
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                offset_path.parent.mkdir(parents=True, exist_ok=True)
                offset_path.write_text(str(pos))
                break
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            ingest_line(o)
            n += 1
            offset_path.write_text(str(f.tell()))
    return n


def one_pass() -> int:
    ensure_ddl()
    maybe_bind_groups_file()
    n = 0
    n += _drain(INBOX, OFFSET)
    n += _drain(INBOX_SAILING, OFFSET_SAILING)
    return n
'''
    if "def _drain(inbox: Path, offset_path: Path)" in text and "_drain(INBOX_SAILING, OFFSET_SAILING)" in text:
        print("skip one_pass: already present")
    elif old_one not in text:
        raise SystemExit("one_pass missing")
    else:
        text = text.replace(old_one, new_one, 1)
        print("patch one_pass dual drain")

    old_bind = '''def maybe_bind_groups_file() -> None:
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
'''
    new_bind = '''_groups_mtime_sailing = None


def _bind_groups_path(path: Path) -> None:
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        groups = data.get("groups") or []
        for g in groups:
            bind_group_to_live_event(str(g.get("jid") or ""), str(g.get("subject") or ""))
    except Exception as e:
        print("groups.json", path, e, file=sys.stderr)


def maybe_bind_groups_file() -> None:
    global _groups_mtime, _groups_mtime_sailing
    if GROUPS.exists():
        mt = GROUPS.stat().st_mtime
        if _groups_mtime is None or mt > _groups_mtime:
            _groups_mtime = mt
            _bind_groups_path(GROUPS)
    if GROUPS_SAILING.exists():
        mt = GROUPS_SAILING.stat().st_mtime
        if _groups_mtime_sailing is None or mt > _groups_mtime_sailing:
            _groups_mtime_sailing = mt
            _bind_groups_path(GROUPS_SAILING)
'''
    if "_bind_groups_path" in text:
        print("skip bind: already present")
    elif old_bind not in text:
        print("WARN: bind fn not exact; skip (MAC already bound)")
    else:
        text = text.replace(old_bind, new_bind, 1)
        print("patch bind sailing groups.json")

    need = (
        "INBOX_SAILING",
        "MEDIA_DIR_SAILING",
        "def _drain(inbox: Path, offset_path: Path)",
        "_drain(INBOX_SAILING, OFFSET_SAILING)",
        "for _mdir in (MEDIA_DIR, MEDIA_DIR_SAILING)",
    )
    missing = [k for k in need if k not in text]
    if missing:
        raise SystemExit("missing after patch: " + ", ".join(missing))
    return text


def main() -> int:
    text = INGEST.read_text()
    patched = apply(text)
    if patched != text:
        bak = INGEST.with_suffix(".py.bak_sailing_inbox")
        if not bak.exists():
            bak.write_text(text)
            print("backup", bak)
        INGEST.write_text(patched)
        print("wrote", INGEST)
    else:
        print("no file change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
