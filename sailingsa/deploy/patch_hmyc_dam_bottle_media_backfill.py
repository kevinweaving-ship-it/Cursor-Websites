#!/usr/bin/env python3
"""Pull HMYC media into Dam Bottle Event Reels. Does not touch gold api.py."""
from pathlib import Path
import hashlib
import re

DAM = "2026-10-10-hmyc-dam-bottle-sprints"
GOLD = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"
BOOT_VER = "dbs22"
REELS_VER = "hmycdbsmedia2"


def write(path, text):
    p = Path(path)
    p.write_text(text, encoding="utf-8")
    print("patched", p, p.stat().st_size)


def write_both(web, text):
    write(web, text)
    fp = Path(str(web).replace("/var/www/sailingsa/js/", "/var/www/sailingsa/frontend/js/"))
    if fp.is_file():
        write(fp, text)


# --- archive: documents / video notes / stickers ---
p = Path("/opt/arial-whatsapp-poc/event_group_archive.js")
t = p.read_text(encoding="utf-8")
old = (
    "  if (inner.imageMessage) return { kind: 'photo', node: inner.imageMessage, caption: inner.imageMessage.caption || '' };\n"
    "  if (inner.videoMessage) return { kind: 'video', node: inner.videoMessage, caption: inner.videoMessage.caption || '' };\n"
    "  if (inner.audioMessage) {\n"
)
new = (
    "  if (inner.imageMessage) return { kind: 'photo', node: inner.imageMessage, caption: inner.imageMessage.caption || '' };\n"
    "  if (inner.videoMessage) return { kind: 'video', node: inner.videoMessage, caption: inner.videoMessage.caption || '' };\n"
    "  if (inner.ptvMessage) return { kind: 'video', node: inner.ptvMessage, caption: inner.ptvMessage.caption || '' };\n"
    "  if (inner.documentMessage) {\n"
    "    const n = inner.documentMessage;\n"
    "    const mime = String(n.mimetype || '').toLowerCase();\n"
    "    if (mime.startsWith('image/')) return { kind: 'photo', node: n, caption: n.caption || n.fileName || '' };\n"
    "    if (mime.startsWith('video/')) return { kind: 'video', node: n, caption: n.caption || n.fileName || '' };\n"
    "  }\n"
    "  if (inner.stickerMessage) return { kind: 'photo', node: inner.stickerMessage, caption: '' };\n"
    "  if (inner.audioMessage) {\n"
)
if old in t:
    t = t.replace(old, new, 1)
    write(p, t)
elif "inner.ptvMessage" in t:
    print("archive classify already expanded")
else:
    raise SystemExit("archive classify block not found")

# --- poc: real-key history fetch ---
p = Path("/opt/arial-whatsapp-poc/poc.js")
t = p.read_text(encoding="utf-8")
old_fetch = (
    "      try { await sock.presenceSubscribe(JID); } catch (_) { /* none */ }\n"
    "      try { await sock.groupMetadata(JID); } catch (_) { /* none */ }\n"
    "      let op = null, err = null;\n"
    "      try {\n"
    "        op = await sock.fetchMessageHistory(80, { remoteJid: JID, fromMe: false, id: String(Date.now()) }, Date.now());\n"
    "      } catch (e) { err = String(e.message || e); }\n"
    "      event('fetch-group-history', { jid: JID, op, err });\n"
    "      return send(200, { ok: true, jid: JID, op, err });\n"
)
new_fetch = (
    "      const id = String(b.id || '').trim();\n"
    "      const participant = String(b.participant || '').trim();\n"
    "      const ts = Number(b.ts || 0);\n"
    "      const count = Math.min(Math.max(Number(b.count || 80), 1), 200);\n"
    "      try { await sock.presenceSubscribe(JID); } catch (_) { /* none */ }\n"
    "      try { await sock.groupMetadata(JID); } catch (_) { /* none */ }\n"
    "      const key = { remoteJid: JID, fromMe: !!b.fromMe, id: id || String(Date.now()) };\n"
    "      if (participant) key.participant = participant;\n"
    "      let op = null, err = null, resend = null;\n"
    "      try {\n"
    "        op = await sock.fetchMessageHistory(count, key, ts || Date.now());\n"
    "      } catch (e) { err = String(e.message || e); }\n"
    "      if (id && typeof sock.requestPlaceholderResend === 'function') {\n"
    "        try { resend = await sock.requestPlaceholderResend(key); }\n"
    "        catch (e2) { resend = String(e2.message || e2); }\n"
    "      }\n"
    "      event('fetch-group-history', { jid: JID, key, op, err, resend });\n"
    "      return send(200, { ok: true, jid: JID, key, op, err, resend });\n"
)
if old_fetch in t:
    t = t.replace(old_fetch, new_fetch, 1)
    write(p, t)
elif "key.participant = participant" in t:
    print("poc fetch-group-history already real-key")
else:
    raise SystemExit("poc fetch-group-history block not found")

# --- Event Reels: Dam Bottle reads mm-clips, not the 404 FB feed ---
for dest in (
    Path("/var/www/sailingsa/js/mm-lipton-reels-card.js"),
    Path("/var/www/sailingsa/frontend/js/mm-lipton-reels-card.js"),
):
    if not dest.is_file():
        continue
    t = dest.read_text(encoding="utf-8")
    t2 = t.replace(
        "    var url = isMidmar()\n"
        "      ? '/api/regatta/' + encodeURIComponent(rid) + '/mm-clips'\n"
        "      : '/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed';",
        "    var url = (isMidmar() || isDamBottle())\n"
        "      ? '/api/regatta/' + encodeURIComponent(rid) + '/mm-clips'\n"
        "      : '/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed';",
    )
    t2 = t2.replace(
        "      if (isMidmar()) {\n        if (clipIdKey(videos) === clipIdKey(payload.videos)) return;",
        "      if (isMidmar() || isDamBottle()) {\n        if (clipIdKey(videos) === clipIdKey(payload.videos)) return;",
    )
    t2 = t2.replace(
        "      if (isDartNats() || isDamBottle()) {\n        jobs.push(",
        "      if (isDartNats()) {\n        jobs.push(",
    )
    t2 = t2.replace(
        "    if (!isMidmar() && !isDartNats()) return;\n    bindMidmarAutoEnd(root, payload, state);",
        "    if (!isMidmar() && !isDartNats() && !isDamBottle()) return;\n    bindMidmarAutoEnd(root, payload, state);",
    )
    t2 = t2.replace(
        "    if (!(isMidmar() || isDartNats()) || !root) return;",
        "    if (!(isMidmar() || isDartNats() || isDamBottle()) || !root) return;",
    )
    t2 = t2.replace(
        "      if (!(isMidmar() || isDartNats()) || !root._mmAutoPlaying) return;",
        "      if (!(isMidmar() || isDartNats() || isDamBottle()) || !root._mmAutoPlaying) return;",
    )
    if t2 != t:
        write(dest, t2)
    else:
        print("reels already mm-clips primary", dest)

# --- cache bust so browsers pick up the reels poll fix ---
p = Path("/var/www/sailingsa/js/midmar-live-media.js")
t = p.read_text(encoding="utf-8")
t2 = re.sub(
    r'loadScript\("/js/mm-lipton-reels-card\.js\?v=[^"]+"\)',
    f'loadScript("/js/mm-lipton-reels-card.js?v={REELS_VER}")',
    t,
)
t2 = re.sub(
    r'loadCss\("/css/mm-lipton-reels\.css\?v=[^"]+"\)',
    f'loadCss("/css/mm-lipton-reels.css?v={REELS_VER}")',
    t2,
)
if t2 != t:
    write_both(p, t2)
else:
    print("midmar-live-media cache already", REELS_VER)

p = Path("/var/www/sailingsa/js/hmyc-dam-bottle-live-boot.js")
t = p.read_text(encoding="utf-8")
t2 = re.sub(r"midmar-live-media\.js\?v=midmarwx60dbs\d+", "midmar-live-media.js?v=midmarwx60dbs5", t)
if t2 != t:
    write_both(p, t2)
else:
    print("boot media cache already dbs4")

p = Path("/var/www/sailingsa/js/regatta-pdf-share.js")
t = p.read_text(encoding="utf-8")
t2 = re.sub(r"hmyc-dam-bottle-live-boot\.js\?v=dbs\d+", f"hmyc-dam-bottle-live-boot.js?v={BOOT_VER}", t)
if t2 != t:
    write(p, t2)
    fp = Path("/var/www/sailingsa/frontend/js/regatta-pdf-share.js")
    if fp.is_file():
        write(fp, t2)
else:
    print("loader already", BOOT_VER)

api = Path("/var/www/sailingsa/api/api.py").read_bytes()
digest = hashlib.sha256(api).hexdigest()
if digest != GOLD or len(api) != 3953427:
    raise SystemExit(f"api.py changed unexpectedly {digest} {len(api)}")
print("gold api.py unchanged", digest, len(api))
