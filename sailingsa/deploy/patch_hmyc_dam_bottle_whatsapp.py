#!/usr/bin/env python3
"""Wire Dam Bottle Event Reels to the live HMYC Event Media WhatsApp ingest.

Runs on the live server. Does not touch gold api.py.
"""
from pathlib import Path
import hashlib
import re

DAM = "2026-10-10-hmyc-dam-bottle-sprints"
GOLD = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"


def must_contain(text, needle, label):
    if needle not in text:
        raise SystemExit(f"{label}: missing {needle!r}")


def write(path, text):
    p = Path(path)
    p.write_text(text, encoding="utf-8")
    print("patched", p, p.stat().st_size)


# --- ingest: post Dam Bottle clips and bind HMYC Event Media ---
p = Path("/opt/arial-whatsapp-poc/event_whatsapp_ingest.py")
t = p.read_text(encoding="utf-8")
if "DAM_WA_RID" not in t:
    t = t.replace(
        "    OR lower({sql_str(subject)}) LIKE '%hmyc%'\n",
        "    OR lower({sql_str(subject)}) LIKE '%hmyc%'\n"
        "    OR lower({sql_str(subject)}) LIKE '%event media%'\n"
        "    OR lower({sql_str(subject)}) LIKE '%dam bottle%'\n"
        "    OR lower({sql_str(subject)}) LIKE '%sprints%'\n",
        1,
    )
    t = t.replace(
        "  AND g.regatta_id IN ('2026-09-13-zvyc-cape-classic', '2026-09-19-hmyc-midmar-cup')\n",
        "  AND g.regatta_id IN (\n"
        "    '2026-09-13-zvyc-cape-classic',\n"
        "    '2026-09-19-hmyc-midmar-cup',\n"
        f"    '{DAM}'\n"
        "  )\n",
        1,
    )
    old = (
        'DART_WA_JID = "120363426250399531@g.us"\n'
        'DART_WA_RID = "2026-09-24-hmyc-dart-18-nationals"\n'
    )
    must_contain(t, old, "ingest dart ids")
    t = t.replace(
        old,
        old + f'DAM_WA_RID = "{DAM}"\n',
        1,
    )
    t = t.replace(
        "    if rid == DART_WA_RID:\n        pass\n    elif rid != MM_RID:\n        return\n",
        "    if rid == DART_WA_RID or rid == DAM_WA_RID:\n        pass\n    elif rid != MM_RID:\n        return\n",
        1,
    )
    # Date gate currently kills every non-Dart clip after Midmar cutoff.
    t = t.replace(
        "    _is_dart = str(o.get(\"group_jid\") or \"\") == DART_WA_JID\n",
        "    _is_dart = str(o.get(\"group_jid\") or \"\") == DART_WA_JID\n"
        "    _look_rid = \"\"\n"
        "    try:\n"
        "        _look_rid = psql(\n"
        "            f\"SELECT COALESCE(regatta_id,'') FROM public.event_whatsapp_groups "
        "WHERE is_current AND group_jid = {sql_str(str(o.get('group_jid') or ''))} LIMIT 1;\"\n"
        "        ).strip()\n"
        "    except Exception:\n"
        "        _look_rid = \"\"\n"
        "    _is_dam = _look_rid == DAM_WA_RID\n",
        1,
    )
    t = t.replace(
        "    if _is_dart:\n        if _now < _dart_open or _now > _dart_close:\n            return\n    elif _now >= _cutoff:  # MIDMAR_DROP_1801_v1\n        return\n",
        "    if _is_dart:\n"
        "        if _now < _dart_open or _now > _dart_close:\n            return\n"
        "    elif _is_dam:\n"
        "        pass\n"
        "    elif _now >= _cutoff:  # MIDMAR_DROP_1801_v1\n        return\n",
        1,
    )
    t = t.replace(
        "        if _is_dart:\n            if _when < _dart_open or _when > _dart_close:\n                return\n        elif _when > _cutoff:\n            return\n",
        "        if _is_dart:\n            if _when < _dart_open or _when > _dart_close:\n                return\n"
        "        elif _is_dam:\n            pass\n"
        "        elif _when > _cutoff:\n            return\n",
        1,
    )
    write(p, t)
else:
    print("ingest already has DAM_WA_RID")

# --- archive: treat HMYC Event Media as an event group ---
p = Path("/opt/arial-whatsapp-poc/event_group_archive.js")
t = p.read_text(encoding="utf-8")
if "event media" not in t:
    old = (
        "    || s.includes('midmar') || s.includes('hmyc') || s.includes('henley');\n"
    )
    must_contain(t, old, "archive eventLikeName")
    t = t.replace(
        old,
        "    || s.includes('midmar') || s.includes('hmyc') || s.includes('henley')\n"
        "    || s.includes('event media') || s.includes('dam bottle') || s.includes('sprints');\n",
        1,
    )
    write(p, t)
else:
    print("archive already has event media")

# --- poc: history backfill uses the allow-list (Dam Bottle included once detected) ---
p = Path("/opt/arial-whatsapp-poc/poc.js")
t = p.read_text(encoding="utf-8")
if "allowed: wanted.length" not in t:
    old = (
        "    const midmar = msgs.filter((m) => String(m?.key?.remoteJid || '') === '120363430436374375@g.us');\n"
        "    event('history-set', { n: msgs.length, midmar: midmar.length, isLatest: data.isLatest });\n"
        "    try {\n"
        "      const r = await archiveHistoryBatch(sock, midmar.length ? midmar : msgs, log);\n"
    )
    must_contain(t, old, "poc history-set")
    t = t.replace(
        old,
        "    let allow = new Set();\n"
        "    try {\n"
        "      allow = new Set((JSON.parse(fs.readFileSync(path.join(__dirname, 'state', 'event-whatsapp', 'allow.json'), 'utf8')).jids) || []);\n"
        "    } catch (_) { /* none */ }\n"
        "    const wanted = msgs.filter((m) => allow.has(String(m?.key?.remoteJid || '')));\n"
        "    event('history-set', { n: msgs.length, allowed: wanted.length, isLatest: data.isLatest });\n"
        "    try {\n"
        "      const r = await archiveHistoryBatch(sock, wanted.length ? wanted : msgs, log);\n",
        1,
    )
    write(p, t)
else:
    print("poc history already allow-list")

# --- Event Reels: poll Dam Bottle clips every 2s like Dart ---
for dest in (
    Path("/var/www/sailingsa/js/mm-lipton-reels-card.js"),
    Path("/var/www/sailingsa/frontend/js/mm-lipton-reels-card.js"),
):
    if not dest.is_file():
        continue
    t = dest.read_text(encoding="utf-8")
    t2 = t.replace(
        "if (isCapeClassic() || isDartNats()) pollMs = 2000;",
        "if (isCapeClassic() || isDartNats() || isDamBottle()) pollMs = 2000;",
    )
    if t2 != t:
        write(dest, t2)
    else:
        print("reels poll already dam", dest)

clips = Path(f"/var/www/sailingsa/assets/mm-clips/{DAM}")
clips.mkdir(parents=True, exist_ok=True)
print("clips dir", clips)

api = Path("/var/www/sailingsa/api/api.py").read_bytes()
digest = hashlib.sha256(api).hexdigest()
if digest != GOLD or len(api) != 3953427:
    raise SystemExit(f"api.py changed unexpectedly {digest} {len(api)}")
print("gold api.py unchanged", digest, len(api))
