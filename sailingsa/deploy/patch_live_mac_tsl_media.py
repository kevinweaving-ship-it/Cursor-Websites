#!/usr/bin/env python3
"""Wire MAC TSL media card to the same 5-clip / WhatsApp path as HMYC Dart.

Patches on the box (never wholesale-replace live api.py):
  /var/www/sailingsa/js/mm-lipton-reels-card.js
  /opt/arial-whatsapp-poc/event_whatsapp_ingest.py
  live api.py script version 20261012a -> 20261012b

  python3 sailingsa/deploy/patch_live_mac_tsl_media.py
"""
from __future__ import annotations

from pathlib import Path

SLUG = "2026-10-17-mac-tsl-wc-team-sailing"
REELS = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
INGEST = Path("/opt/arial-whatsapp-poc/event_whatsapp_ingest.py")
ARCHIVE = Path("/opt/arial-whatsapp-poc/event_group_archive.js")
POC = Path("/opt/arial-whatsapp-poc/poc.js")
API = Path("/var/www/sailingsa/api/api.py")


def apply_one(text: str, anchor: str, insert: str, name: str) -> str:
    if insert in text:
        print(f"skip {name}: already present")
        return text
    if name == "reels-mac-logo" and "if (isMacTsl() && clubLogo)" in text:
        print(f"skip {name}: MAC logo hook already present")
        return text
    if anchor not in text:
        raise SystemExit(f"ERROR: anchor not found for {name}")
    if text.count(anchor) != 1:
        raise SystemExit(f"ERROR: anchor for {name} is not unique ({text.count(anchor)})")
    print(f"patch {name}")
    return text.replace(anchor, insert, 1)


def patch_reels(text: str) -> str:
    text = apply_one(
        text,
        """  function isDamBottle() {
    var root = cardEl();
    var id = (root && root.getAttribute('data-regatta-id')) || '';
    return id.indexOf('2026-10-10-hmyc-dam-bottle-sprints') === 0;
  }
  function isHmycCompact() {
    return isDartNats() || isDamBottle();
  }
""",
        """  function isDamBottle() {
    var root = cardEl();
    var id = (root && root.getAttribute('data-regatta-id')) || '';
    return id.indexOf('2026-10-10-hmyc-dam-bottle-sprints') === 0;
  }
  function isMacTsl() {
    var root = cardEl();
    var id = (root && root.getAttribute('data-regatta-id')) || '';
    return id === '2026-10-17-mac-tsl-wc-team-sailing';
  }
  function isHmycCompact() {
    return isDartNats() || isDamBottle() || isMacTsl();
  }
""",
        "reels-isMacTsl",
    )
    text = apply_one(
        text,
        """    if (isMidmar() || isDamBottle()) {
      var n = 5 - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
""",
        """    if (isMidmar() || isDamBottle() || isMacTsl()) {
      var n = 5 - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
""",
        "reels-placeholder",
    )
    text = apply_one(
        text,
        """    var url = (isMidmar() || isDamBottle())
      ? '/api/regatta/' + encodeURIComponent(rid) + '/mm-clips'
      : '/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed';
""",
        """    var url = (isMidmar() || isDamBottle() || isMacTsl())
      ? '/api/regatta/' + encodeURIComponent(rid) + '/mm-clips'
      : '/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed';
""",
        "reels-poll-url",
    )
    text = apply_one(
        text,
        """      if (isMidmar() || isDamBottle()) {
        if (clipIdKey(videos) === clipIdKey(payload.videos)) return;
""",
        """      if (isMidmar() || isDamBottle() || isMacTsl()) {
        if (clipIdKey(videos) === clipIdKey(payload.videos)) return;
""",
        "reels-apply",
    )
    text = apply_one(
        text,
        """      if (isCapeClassic() || isDartNats() || isDamBottle()) pollMs = 2000;
""",
        """      if (isCapeClassic() || isDartNats() || isDamBottle() || isMacTsl()) pollMs = 2000;
""",
        "reels-poll-ms",
    )
    text = apply_one(
        text,
        """    if (isDamBottle()) nFit = 5;
""",
        """    if (isDamBottle() || isMacTsl()) nFit = 5;
""",
        "reels-nfit",
    )
    text = apply_one(
        text,
        """    var clubLogo = root.getAttribute('data-mm-club-logo') || '';
    if (!img || !soon) return;
    // Club pages: cam belongs to the club, not Marine Megastore.
    if (isClubPage() && clubLogo) {
""",
        """    var clubLogo = root.getAttribute('data-mm-club-logo') || '';
    if (!img || !soon) return;
    if (isMacTsl() && clubLogo) {
      if (img.getAttribute('src') !== clubLogo) img.setAttribute('src', clubLogo);
      img.setAttribute('alt', root.getAttribute('data-mm-club-alt') || 'MAC');
      return;
    }
    // Club pages: cam belongs to the club, not Marine Megastore.
    if (isClubPage() && clubLogo) {
""",
        "reels-mac-logo",
    )
    text = apply_one(
        text,
        """    if (isMacTsl() && clubLogo) {
      if (img.getAttribute('src') !== clubLogo) img.setAttribute('src', clubLogo);
      img.setAttribute('alt', root.getAttribute('data-mm-club-alt') || 'MAC');
      return;
    }
""",
        """    if (isMacTsl() && clubLogo) {
      if (img.getAttribute('src') !== clubLogo) img.setAttribute('src', clubLogo);
      img.setAttribute('alt', root.getAttribute('data-mm-club-alt') || 'MAC');
      var macLink = img.closest && img.closest('.mm-lipton-reels-brand');
      var macHref = root.getAttribute('data-mm-club-href') || '/club/mac';
      if (macLink && macHref) macLink.setAttribute('href', macHref);
      return;
    }
""",
        "reels-mac-club-href",
    )
    text = apply_one(
        text,
        """      if (brand && isDartNats()) return;
""",
        """      if (brand && (isDartNats() || isMacTsl())) return;
""",
        "reels-mac-brand-click",
    )
    text = apply_one(
        text,
        """        brand.style.display = '';
        brand.style.width = innerH * art + border + 'px';
        brand.style.height = outerH + 'px';
      }
""",
        """        brand.style.display = '';
        brand.style.width = innerH * art + border + 'px';
        brand.style.height = outerH + 'px';
        if (isMacTsl()) {
          brand.style.boxSizing = 'border-box';
          brand.style.padding = '2px';
          brand.style.height = outerH + 'px';
          brand.style.width = Math.round(outerH * 2014 / 780) + 'px';
        }
      }
""",
        "reels-mac-logo-tile-aspect",
    )
    return text


def patch_ingest(text: str) -> str:
    text = apply_one(
        text,
        """      g.regatta_id = '2026-10-10-hmyc-dam-bottle-sprints'
      AND (
        lower({sql_str(subject)}) LIKE '%event media%'
        OR lower({sql_str(subject)}) LIKE '%hmyc media%'
        OR lower({sql_str(subject)}) LIKE '%dam bottle%'
        OR lower({sql_str(subject)}) LIKE '%sprints%'
      )
    ) OR (
""",
        """      g.regatta_id = '2026-10-10-hmyc-dam-bottle-sprints'
      AND (
        lower({sql_str(subject)}) LIKE '%event media%'
        OR lower({sql_str(subject)}) LIKE '%hmyc media%'
        OR lower({sql_str(subject)}) LIKE '%dam bottle%'
        OR lower({sql_str(subject)}) LIKE '%sprints%'
      )
    ) OR (
      g.regatta_id = '2026-10-17-mac-tsl-wc-team-sailing'
      AND (
        lower({sql_str(subject)}) LIKE '%mac media%'
        OR lower({sql_str(subject)}) LIKE '%tsl%media%'
        OR lower({sql_str(subject)}) LIKE '%media%mac%'
      )
    ) OR (
""",
        "ingest-bind",
    )
    text = apply_one(
        text,
        """      g.regatta_id <> '2026-10-10-hmyc-dam-bottle-sprints'
      AND (
        lower({sql_str(subject)}) LIKE '%cape classic%'
""",
        """      g.regatta_id <> '2026-10-10-hmyc-dam-bottle-sprints'
      AND g.regatta_id <> '2026-10-17-mac-tsl-wc-team-sailing'
      AND (
        lower({sql_str(subject)}) LIKE '%cape classic%'
""",
        "ingest-no-steal",
    )
    text = apply_one(
        text,
        """    '2026-09-13-zvyc-cape-classic',
    '2026-09-19-hmyc-midmar-cup',
    '2026-10-10-hmyc-dam-bottle-sprints'
""",
        """    '2026-09-13-zvyc-cape-classic',
    '2026-09-19-hmyc-midmar-cup',
    '2026-10-10-hmyc-dam-bottle-sprints',
    '2026-10-17-mac-tsl-wc-team-sailing'
""",
        "ingest-extras",
    )
    text = apply_one(
        text,
        """DART_WA_JID = "120363426250399531@g.us"
DART_WA_RID = "2026-09-24-hmyc-dart-18-nationals"
DAM_WA_RID = "2026-10-10-hmyc-dam-bottle-sprints"
""",
        """DART_WA_JID = "120363426250399531@g.us"
DART_WA_RID = "2026-09-24-hmyc-dart-18-nationals"
DAM_WA_RID = "2026-10-10-hmyc-dam-bottle-sprints"
MAC_WA_RID = "2026-10-17-mac-tsl-wc-team-sailing"
""",
        "ingest-mac-rid",
    )
    text = apply_one(
        text,
        """    _is_dart = rid == DART_WA_RID or jid == DART_WA_JID
    _is_dam = rid == DAM_WA_RID
    _is_mm = rid == MM_RID
    if not (_is_dart or _is_dam or _is_mm):
        return
""",
        """    _is_dart = rid == DART_WA_RID or jid == DART_WA_JID
    _is_dam = rid == DAM_WA_RID
    _is_mm = rid == MM_RID
    _is_mac = rid == MAC_WA_RID
    if not (_is_dart or _is_dam or _is_mm or _is_mac):
        return
""",
        "ingest-mac-gate",
    )
    text = apply_one(
        text,
        """    _dam_open = _dt(2026, 10, 10, 0, 0, tzinfo=_sast)
    _dam_close = _dt(2026, 10, 12, 23, 59, tzinfo=_sast)
    _now = _dt.now(_sast)
""",
        """    _dam_open = _dt(2026, 10, 10, 0, 0, tzinfo=_sast)
    _dam_close = _dt(2026, 10, 12, 23, 59, tzinfo=_sast)
    _mac_open = _dt(2026, 10, 12, 0, 0, tzinfo=_sast)
    _mac_close = _dt(2026, 10, 19, 23, 59, tzinfo=_sast)
    _now = _dt.now(_sast)
""",
        "ingest-mac-window",
    )
    text = apply_one(
        text,
        """    elif _is_dam:
        if _now < _dam_open or _now > _dam_close:
            return
    elif _now >= _cutoff:  # MIDMAR_DROP_1801_v1
        return
""",
        """    elif _is_dam:
        if _now < _dam_open or _now > _dam_close:
            return
    elif _is_mac:
        if _now < _mac_open or _now > _mac_close:
            return
    elif _now >= _cutoff:  # MIDMAR_DROP_1801_v1
        return
""",
        "ingest-mac-now",
    )
    text = apply_one(
        text,
        """        elif _is_dam:
            if _when < _dam_open or _when > _dam_close:
                return
        elif _when > _cutoff:
            return
""",
        """        elif _is_dam:
            if _when < _dam_open or _when > _dam_close:
                return
        elif _is_mac:
            if _when < _mac_open or _when > _mac_close:
                return
        elif _when > _cutoff:
            return
""",
        "ingest-mac-when",
    )
    text = apply_one(
        text,
        """    if rid == DART_WA_RID or rid == DAM_WA_RID:
        pass
    elif rid != MM_RID:
        return
""",
        """    if rid == DART_WA_RID or rid == DAM_WA_RID or rid == MAC_WA_RID:
        pass
    elif rid != MM_RID:
        return
""",
        "ingest-mac-rid-ok",
    )
    text = apply_one(
        text,
        """    _fallback = "Dam Bottle" if _is_dam else ("Dart 18" if _is_dart else "Midmar")
""",
        """    _fallback = "MAC Media" if _is_mac else ("Dam Bottle" if _is_dam else ("Dart 18" if _is_dart else "Midmar"))
""",
        "ingest-mac-label",
    )
    text = apply_one(
        text,
        """        lower({sql_str(subject)}) LIKE '%mac media%'
        OR lower({sql_str(subject)}) LIKE '%tsl%media%'
        OR lower({sql_str(subject)}) LIKE '%media%mac%'
""",
        """        lower({sql_str(subject)}) LIKE '%mac%media%'
        OR lower({sql_str(subject)}) LIKE '%media%mac%'
        OR lower({sql_str(subject)}) LIKE '%tsl%media%'
""",
        "ingest-mac-name-loose",
    )
    text = apply_one(
        text,
        """  AND g.group_jid IS NULL
  AND CURRENT_DATE BETWEEN g.valid_from AND g.valid_until
""",
        """  AND (g.group_jid IS NULL OR btrim(COALESCE(g.group_jid, '')) = '')
  AND CURRENT_DATE BETWEEN g.valid_from AND g.valid_until
""",
        "ingest-empty-jid",
    )
    return text


def patch_archive(text: str) -> str:
    return apply_one(
        text,
        """    || s.includes('event media') || s.includes('dam bottle') || s.includes('sprints');
""",
        """    || s.includes('event media') || s.includes('dam bottle') || s.includes('sprints')
    || s.includes('mac media') || s.includes('team sailing') || s.includes('tsl');
""",
        "archive-mac-name",
    )


def patch_archive_loose(text: str) -> str:
    return apply_one(
        text,
        """    || s.includes('mac media') || s.includes('team sailing') || s.includes('tsl');
""",
        """    || (s.includes('mac') && s.includes('media')) || s.includes('team sailing') || s.includes('tsl');
""",
        "archive-mac-name-loose",
    )


def patch_poc(text: str) -> str:
    text = apply_one(
        text,
        """    if (req.method === 'POST' && url.pathname === '/fetch-group-history') {
""",
        """    if (req.method === 'POST' && url.pathname === '/refresh-groups') {
      if (!sock || st.state !== 'UP') throw new Error('whatsapp not UP');
      const groups = await listParticipatingGroups(sock);
      event('event-groups', { n: (groups || []).length, names: (groups || []).map((g) => g.subject).slice(0, 20), via: 'http' });
      return send(200, { ok: true, n: (groups || []).length, names: (groups || []).map((g) => g.subject) });
    }
    if (req.method === 'POST' && url.pathname === '/fetch-group-history') {
""",
        "poc-refresh-groups",
    )
    text = apply_one(
        text,
        """setInterval(writeHealth, 10000);
""",
        """setInterval(writeHealth, 10000);
setInterval(() => {
  if (!sock || st.state !== 'UP') return;
  listParticipatingGroups(sock).then((groups) => {
    event('event-groups', { n: (groups || []).length, names: (groups || []).map((g) => g.subject).slice(0, 20), via: 'poll' });
  }).catch((e) => event('event-groups-failed', { error: String(e), via: 'poll' }));
}, 120000);
""",
        "poc-group-poll",
    )
    return text


def main() -> int:
    reels = REELS.read_text(encoding="utf-8")
    new_reels = patch_reels(reels)
    if new_reels != reels:
        REELS.write_text(new_reels, encoding="utf-8")
        print(f"Wrote {REELS}")
    ingest = INGEST.read_text(encoding="utf-8")
    new_ingest = patch_ingest(ingest)
    if new_ingest != ingest:
        INGEST.write_text(new_ingest, encoding="utf-8")
        print(f"Wrote {INGEST}")
    if ARCHIVE.is_file():
        archive = ARCHIVE.read_text(encoding="utf-8")
        new_archive = patch_archive(archive)
        if new_archive != archive:
            ARCHIVE.write_text(new_archive, encoding="utf-8")
            print(f"Wrote {ARCHIVE}")
        loose = patch_archive_loose(ARCHIVE.read_text(encoding="utf-8"))
        if loose != ARCHIVE.read_text(encoding="utf-8"):
            ARCHIVE.write_text(loose, encoding="utf-8")
            print(f"Wrote {ARCHIVE} loose")
    if POC.is_file():
        poc = POC.read_text(encoding="utf-8")
        new_poc = patch_poc(poc)
        if new_poc != poc:
            POC.write_text(new_poc, encoding="utf-8")
            print(f"Wrote {POC}")
    if API.is_file():
        api = API.read_text(encoding="utf-8")
        new_api = api.replace(
            "/js/mac-tsl-live-cards.js?v=20261012a",
            "/js/mac-tsl-live-cards.js?v=20261012b",
        )
        if new_api != api:
            print("patch api script ver")
            API.write_text(new_api, encoding="utf-8")
        else:
            print("skip api script ver")
    print("MAC TSL media patches done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
