#!/usr/bin/env python3
"""Patch live arial WhatsApp PoC to archive event *group* messages + media."""
from pathlib import Path
import sys

POC = Path("/opt/arial-whatsapp-poc/poc.js")

REPLACEMENTS = [
    (
        """const {
  default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion,
  fetchLatestWaWebVersion, Browsers, jidNormalizedUser,
} = require('@whiskeysockets/baileys');""",
        """const {
  default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion,
  fetchLatestWaWebVersion, Browsers, jidNormalizedUser,
} = require('@whiskeysockets/baileys');
const { archiveGroupMessage, listParticipatingGroups } = require('./event_group_archive');""",
    ),
    (
        """    if (u.connection === 'open') {
      st.qr = null; st.pairingCode = null; st.connectedAt = Date.now(); st.me = jidNormalizedUser(sock.user?.id || '') || null;
      try { fs.unlinkSync(QR_PNG); } catch (_) { /* none */ }
      setState('UP', { me: st.me });
    }""",
        """    if (u.connection === 'open') {
      st.qr = null; st.pairingCode = null; st.connectedAt = Date.now(); st.me = jidNormalizedUser(sock.user?.id || '') || null;
      try { fs.unlinkSync(QR_PNG); } catch (_) { /* none */ }
      setState('UP', { me: st.me });
      setTimeout(() => {
        listParticipatingGroups(sock).then((groups) => {
          event('event-groups', { n: (groups || []).length, names: (groups || []).map((g) => g.subject).slice(0, 20) });
        }).catch((e) => event('event-groups-failed', { error: String(e) }));
      }, 1200);
    }""",
    ),
    (
        """function onInbound(sock) {
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const m of messages || []) {
      try {
        if (!m?.key || m.key.fromMe) continue;
        const text = (m.message?.conversation || m.message?.extendedTextMessage?.text || '').trim();
        if (!/^power$/i.test(text)) continue;""",
        """function onInbound(sock) {
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify' && type !== 'append') return;
    for (const m of messages || []) {
      try {
        if (!m?.key) continue;
        try { await archiveGroupMessage(sock, m, log); } catch (eArch) { event('event-archive-error', { error: String(eArch) }); }
        if (m.key.fromMe) continue;
        const text = (m.message?.conversation || m.message?.extendedTextMessage?.text || '').trim();
        if (!/^power$/i.test(text)) continue;""",
    ),
]


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else POC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
