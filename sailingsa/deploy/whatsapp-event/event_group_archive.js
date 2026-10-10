'use strict';
/**
 * Archive event WhatsApp *groups* only (not 1:1 alert chats).
 * Keeps: text, voice notes, photos, videos. Files under state/event-whatsapp/.
 */
const fs = require('fs');
const path = require('path');
const { downloadMediaMessage } = require('@whiskeysockets/baileys');

const ROOT = __dirname;
const DIR = path.join(ROOT, 'state', 'event-whatsapp');
const MEDIA = path.join(DIR, 'media');
const INBOX = path.join(DIR, 'inbox.jsonl');
const GROUPS = path.join(DIR, 'groups.json');
const MAX_BYTES = 200 * 1024 * 1024;

function ensureDirs() {
  fs.mkdirSync(MEDIA, { recursive: true, mode: 0o700 });
  try { fs.chmodSync(DIR, 0o700); } catch (_) { /* none */ }
}

function unwrap(msg) {
  if (!msg) return null;
  if (msg.ephemeralMessage) return unwrap(msg.ephemeralMessage.message);
  if (msg.viewOnceMessage) return unwrap(msg.viewOnceMessage.message);
  if (msg.viewOnceMessageV2) return unwrap(msg.viewOnceMessageV2.message);
  if (msg.viewOnceMessageV2Extension) return unwrap(msg.viewOnceMessageV2Extension.message);
  if (msg.documentWithCaptionMessage) return unwrap(msg.documentWithCaptionMessage.message);
  if (msg.editedMessage) return unwrap(msg.editedMessage.message);
  return msg;
}

function classify(inner) {
  if (!inner) return { kind: 'empty' };
  if (inner.conversation || inner.extendedTextMessage) return { kind: 'text', text: (inner.conversation || inner.extendedTextMessage.text || '').trim() };
  if (inner.imageMessage) return { kind: 'photo', node: inner.imageMessage, caption: inner.imageMessage.caption || '' };
  if (inner.videoMessage) return { kind: 'video', node: inner.videoMessage, caption: inner.videoMessage.caption || '' };
  if (inner.ptvMessage) return { kind: 'video', node: inner.ptvMessage, caption: inner.ptvMessage.caption || '' };
  if (inner.documentMessage) {
    const n = inner.documentMessage;
    const mime = String(n.mimetype || '').toLowerCase();
    if (mime.startsWith('image/')) return { kind: 'photo', node: n, caption: n.caption || n.fileName || '' };
    if (mime.startsWith('video/')) return { kind: 'video', node: n, caption: n.caption || n.fileName || '' };
  }
  if (inner.stickerMessage) return { kind: 'photo', node: inner.stickerMessage, caption: '' };
  if (inner.audioMessage) {
    const ptt = !!inner.audioMessage.ptt;
    return { kind: ptt ? 'voice' : 'audio', node: inner.audioMessage, caption: '' };
  }
  return { kind: 'other' };
}

function extFor(kind, mime) {
  const m = String(mime || '').toLowerCase();
  if (m.includes('jpeg') || m.includes('jpg')) return 'jpg';
  if (m.includes('png')) return 'png';
  if (m.includes('webp')) return 'webp';
  if (m.includes('mp4')) return 'mp4';
  if (m.includes('ogg') || m.includes('opus')) return 'ogg';
  if (m.includes('mpeg') || m.includes('mp3')) return 'mp3';
  if (kind === 'photo') return 'jpg';
  if (kind === 'video') return 'mp4';
  if (kind === 'voice' || kind === 'audio') return 'ogg';
  return 'bin';
}

function appendInbox(row) {
  ensureDirs();
  fs.appendFileSync(INBOX, JSON.stringify(row) + '\n', { mode: 0o600 });
}

async function saveMedia(sock, m, kind, node, log) {
  if (!node) return {};
  const mime = node.mimetype || '';
  const declared = Number(node.fileLength || 0);
  if (declared > MAX_BYTES) return { media_error: 'too_large', media_mime: mime, media_bytes: declared };
  try {
    const buf = await downloadMediaMessage(m, 'buffer', {}, { logger: log, reuploadRequest: sock.updateMediaMessage });
    if (!buf || !buf.length) return { media_error: 'empty', media_mime: mime };
    if (buf.length > MAX_BYTES) return { media_error: 'too_large', media_mime: mime, media_bytes: buf.length };
    const id = String(m.key.id || Date.now()).replace(/[^A-Za-z0-9_-]/g, '').slice(0, 48);
    const fname = `${Date.now()}_${id}.${extFor(kind, mime)}`;
    const abs = path.join(MEDIA, fname);
    fs.writeFileSync(abs, buf, { mode: 0o600 });
    return {
      media_mime: mime,
      media_filename: fname,
      media_relpath: path.join('media', fname),
      media_bytes: buf.length,
      duration_sec: node.seconds != null ? Number(node.seconds) : null,
    };
  } catch (e) {
    return { media_error: String(e.message || e), media_mime: mime };
  }
}

function isGroupJid(jid) {
  return String(jid || '').includes('@g.us');
}

function allowedJids() {
  try {
    const a = JSON.parse(fs.readFileSync(path.join(DIR, 'allow.json'), 'utf8'));
    return new Set(a.jids || []);
  } catch (_) {
    return new Set();
  }
}

function eventLikeName(subject) {
  const s = String(subject || '').toLowerCase();
  return s.includes('cape classic') || s.includes('nationals') || s.includes('lipton') || s.includes('regatta')
    || s.includes('midmar') || s.includes('hmyc') || s.includes('henley')
    || s.includes('event media') || s.includes('dam bottle') || s.includes('sprints');
}

async function archiveGroupMessage(sock, m, log) {
  const jid = m?.key?.remoteJid || '';
  if (!isGroupJid(jid)) return false;
  const allow = allowedJids();
  if (allow.size && !allow.has(jid)) return false;
  if (!allow.size) {
    try {
      const data = JSON.parse(fs.readFileSync(GROUPS, 'utf8'));
      const g = (data.groups || []).find((x) => x.jid === jid);
      if (!g || !eventLikeName(g.subject)) return false;
    } catch (_) {
      return false;
    }
  }
  const inner = unwrap(m.message);
  const cls = classify(inner);
  if (cls.kind === 'empty' || cls.kind === 'other') {
    // Ciphertext / retry upserts often arrive empty first; wait for the decrypted body.
    return false;
  }
  const row = {
    t: Date.now(),
    group_jid: jid,
    wa_message_id: m.key.id || '',
    from_me: !!m.key.fromMe,
    sender_jid: m.key.participant || m.key.participantPn || m.participant || '',
    sender_name: m.pushName || '',
    kind: cls.kind,
    body: cls.text || '',
    caption: cls.caption || '',
    occurred_at: m.messageTimestamp ? Number(m.messageTimestamp) * 1000 : Date.now(),
  };
  if (cls.node) Object.assign(row, await saveMedia(sock, m, cls.kind, cls.node, log));
  appendInbox(row);
  return true;
}

async function listParticipatingGroups(sock) {
  ensureDirs();
  const map = await sock.groupFetchAllParticipating();
  const groups = Object.values(map || {}).map((g) => ({
    jid: g.id,
    subject: g.subject || '',
    size: (g.participants || []).length,
  }));
  fs.writeFileSync(GROUPS, JSON.stringify({ t: Date.now(), groups }, null, 2), { mode: 0o600 });
  const detected = groups.filter((g) => eventLikeName(g.subject)).map((g) => g.jid).filter(Boolean);
  let prev = [];
  try { prev = JSON.parse(fs.readFileSync(path.join(DIR, 'allow.json'), 'utf8')).jids || []; } catch (_) {}
  const pinned = ['120363177657630371@g.us', '120363430436374375@g.us', '120363426250399531@g.us'];
  const drop = new Set(['27826554919-1613720148@g.us']);
  const jids = Array.from(new Set([].concat(pinned, prev, detected).filter(Boolean))).filter((j) => !drop.has(j));
  fs.writeFileSync(path.join(DIR, 'allow.json'), JSON.stringify({ t: Date.now(), jids }, null, 2), { mode: 0o600 });
  appendInbox({ t: Date.now(), kind: 'group-list', groups });
  return groups;
}


function inboxHas(waId) {
  if (!waId || !fs.existsSync(INBOX)) return false;
  const raw = fs.readFileSync(INBOX, 'utf8');
  const needle = '"wa_message_id":"' + String(waId) + '"';
  if (!raw.includes(needle)) return false;
  // allow retry when the only rows for this id failed to save media
  const rows = raw.split('\n').filter((l) => l.includes(needle));
  return rows.some((l) => l.includes('"media_filename"') && !l.includes('"media_error"'));
}

async function archiveHistoryBatch(sock, messages, log) {
  const out = { seen: 0, archived: 0, media: 0, skipped: 0, errors: 0 };
  for (const m of messages || []) {
    out.seen += 1;
    const jid = m?.key?.remoteJid || '';
    if (!isGroupJid(jid)) { out.skipped += 1; continue; }
    const allow = allowedJids();
    if (allow.size && !allow.has(jid)) { out.skipped += 1; continue; }
    const inner = unwrap(m.message);
    const cls = classify(inner);
    if (cls.kind !== 'photo' && cls.kind !== 'video') { out.skipped += 1; continue; }
    if (inboxHas(m.key && m.key.id)) { out.skipped += 1; continue; }
    const ts = Number(m.messageTimestamp || 0);
    const row = {
      t: Date.now(),
      group_jid: jid,
      wa_message_id: m.key.id || '',
      from_me: !!m.key.fromMe,
      sender_jid: m.key.participant || m.key.participantPn || m.participant || '',
      sender_name: m.pushName || '',
      kind: cls.kind,
      body: cls.text || '',
      caption: cls.caption || '',
      occurred_at: ts ? (ts < 1e12 ? ts * 1000 : ts) : Date.now(),
    };
    try {
      if (cls.node) Object.assign(row, await saveMedia(sock, m, cls.kind, cls.node, log));
      appendInbox(row);
      out.archived += 1;
      if (row.media_filename) out.media += 1;
    } catch (e) {
      out.errors += 1;
      appendInbox(Object.assign(row, { media_error: String(e.message || e) }));
    }
  }
  return out;
}

module.exports = { archiveGroupMessage, archiveHistoryBatch, listParticipatingGroups, isGroupJid };

