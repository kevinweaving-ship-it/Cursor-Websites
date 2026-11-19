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
REELS_CSS = Path("/var/www/sailingsa/css/mm-lipton-reels.css")
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


MAC_FIT_HELPERS = """  function isMobilePortrait() {
    return window.matchMedia('(max-width: 599px) and (orientation: portrait)').matches;
  }

  function isMobileLandscape() {
    return window.matchMedia('(orientation: landscape) and (max-height: 540px)').matches;
  }

  function macMediaFitCount() {
    if (isMobilePortrait()) return 1;
    if (isMobileLandscape()) return 4;
    if (window.matchMedia('(min-width: 1024px)').matches) return 5;
    return 4;
  }
"""

MAC_FIT_HELPERS_OLD = """  function isMobilePortrait() {
    return window.matchMedia('(max-width: 599px) and (orientation: portrait)').matches;
  }
"""

MAC_PLACEHOLDER_PAD5 = """    if (isMidmar() || isDamBottle() || isMacTsl()) {
      var n = 5 - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
"""

MAC_PLACEHOLDER_VIEWPORT = """    if (isMacTsl()) {
      var n = macMediaFitCount() - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
    if (isMidmar() || isDamBottle()) {
      var n = 5 - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
"""

MAC_NFIT_FORCE5 = "    if (isDamBottle() || isMacTsl()) nFit = 5;\n"
MAC_NFIT_VIEWPORT = (
    "    if (isDamBottle()) nFit = 5;\n"
    "    if (isMacTsl()) nFit = macMediaFitCount();\n"
)

MAC_WHEN_OLD = "    if (!isMidmar() && !isDartNats()) return '';"
MAC_WHEN_NEW = "    if (!isMidmar() && !isDartNats() && !isMacTsl()) return '';"
MAC_WHEN_FN_OLD = "  function thumbWhenHtml(v) {\n    if (!isMidmar() && !isDartNats()) return '';"
MAC_WHEN_FN_NEW = (
    "  function thumbWhenHtml(v) {\n    if (!isMidmar() && !isDartNats() && !isMacTsl()) return '';"
)

MAC_TAG_OLD = "    var tag = isDartNats() ? dartDayTag(v) : midmarDayTag(v);"
MAC_TAG_NEW = (
    "    var tag = isDartNats() ? dartDayTag(v) : "
    "(isMacTsl() ? macDayTag(v) : midmarDayTag(v));"
)

MAC_DAYLABEL_OLD = '    if (isDartNats()) dayLabel = String(p.day || "").replace(/\\s+\\d{2}$/, "");'
MAC_DAYLABEL_NEW = (
    '    if (isDartNats() || isMacTsl()) '
    'dayLabel = String(p.day || "").replace(/\\s+\\d{2}$/, "");'
)

MAC_MEET_FIRST_OLD = "      (isDartNats() && tag ? '<span class=\"mm-lipton-reels-when-meet\">' + esc(tag) + '</span>' : '') +"
MAC_MEET_FIRST_NEW = "      ((isDartNats() || isMacTsl()) && tag ? '<span class=\"mm-lipton-reels-when-meet\">' + esc(tag) + '</span>' : '') +"

MAC_MEET_LAST_OLD = "      (!isDartNats() && tag ? '<span class=\"mm-lipton-reels-when-meet\">' + esc(tag) + '</span>' : '') +"
MAC_MEET_LAST_NEW = "      (!isDartNats() && !isMacTsl() && tag ? '<span class=\"mm-lipton-reels-when-meet\">' + esc(tag) + '</span>' : '') +"

MAC_EMPTY_OLD = "    } else if (!isDamBottle()) {"
MAC_EMPTY_NEW = "    } else if (!isDamBottle() && !isMacTsl()) {"

MAC_COUNTKEY_OLD = (
    "      videoKey(videos) + ':' + extra + ':' + liveN + ':' + "
    "(isMobilePortrait() ? 'mp' : 'w');"
)
MAC_COUNTKEY_NEW = (
    "      videoKey(videos) + ':' + extra + ':' + liveN + ':' + "
    "(isMacTsl() ? ('mac' + macMediaFitCount()) : (isMobilePortrait() ? 'mp' : 'w'));"
)

MAC_CHROME_OLD = """      isSnapshotCam(v) || isMidmar()
        ? ''
        : latestChromeHtml(chromeSource(v, videos), isZvycCam(v) ? 'mm-lipton-reels-clip-chrome--zvyc' : '');"""
MAC_CHROME_NEW = """      isSnapshotCam(v) || isMidmar() || isMacTsl()
        ? ''
        : latestChromeHtml(chromeSource(v, videos), isZvycCam(v) ? 'mm-lipton-reels-clip-chrome--zvyc' : '');"""

MAC_DAY_TAG = """
  function macDayTag(v) {
    if (!isMacTsl() || !v) return '';
    var iso = String(v.started_at || '');
    var m = iso.match(/^(\\d{4}-\\d{2}-\\d{2})/);
    if (!m) {
      var stamp = String(v.stamp || v.fb_sub || '');
      var sm = stamp.match(/^([A-Za-z]{3})\\s+(\\d{1,2})\\s+([A-Za-z]{3})(?:\\s+(\\d{2,4}))?/);
      if (sm) {
        var mon = {Jan:'01',Feb:'02',Mar:'03',Apr:'04',May:'05',Jun:'06',Jul:'07',Aug:'08',Sep:'09',Oct:'10',Nov:'11',Dec:'12'}[sm[3]] || '10';
        var yr = sm[4] ? (sm[4].length === 2 ? '20' + sm[4] : sm[4]) : '2026';
        var dd = sm[2].length === 1 ? '0' + sm[2] : sm[2];
        m = [null, yr + '-' + mon + '-' + dd];
      }
    }
    if (!m) return '';
    var start = Date.parse('2026-10-17T00:00:00+02:00');
    var day = Date.parse(m[1] + 'T12:00:00+02:00');
    if (!start || !day) return '';
    var n = Math.floor((day - start) / 86400000 + 0.05) + 1;
    return n >= 1 && n <= 10 ? 'Day ' + n : '';
  }
"""

MAC_CSS_MARK = "/* mac-tsl-media-slots: match Dart/Midmar card chrome */"
MAC_CSS_BLOCK = """
/* mac-tsl-media-slots: match Dart/Midmar card chrome */
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .section-title{display:none}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-thumb{border:2px solid #001f3f!important;border-radius:8px!important;container-type:normal!important;overflow:hidden!important}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-compact .mm-lipton-reels-clip-chrome{display:none!important}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when{position:absolute;left:3px;right:3px;bottom:3px;z-index:5;display:flex;flex-direction:row;flex-wrap:wrap;align-items:baseline;gap:4px;padding:2px 5px;border-radius:3px;background:rgba(0,16,24,.74);color:#fff;pointer-events:none;box-sizing:border-box}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when-day,
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when-time,
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when-meet{font:700 8px/1.15 Arial,Helvetica,sans-serif;white-space:nowrap}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-thumb .mm-lipton-reels-play{
  position:absolute!important;left:50%!important;top:42%!important;width:22px!important;height:22px!important;margin:0!important;transform:translate(-50%,-50%)!important;border-width:2px!important;z-index:1!important
}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-thumb .mm-lipton-reels-play:after{border-width:5px 0 5px 8px!important}
.mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-tile[aria-label="View photo"] .mm-lipton-reels-play{display:none!important}
@media (max-width: 599px) and (orientation: portrait) {
  .mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when{left:2px;right:2px;bottom:2px;gap:2px;padding:0 2px;flex-wrap:nowrap;overflow:hidden}
  .mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when-day,
  .mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when-time,
  .mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-when-meet{font:700 6px/1.05 Arial,Helvetica,sans-serif}
  .mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-thumb .mm-lipton-reels-play{width:16px!important;height:16px!important;border-width:1.5px!important}
  .mm-lipton-reels[data-regatta-id="2026-10-17-mac-tsl-wc-team-sailing"] .mm-lipton-reels-thumb .mm-lipton-reels-play:after{border-width:3px 0 3px 5px!important}
}
"""


def _swap(text: str, old: str, new: str, name: str) -> str:
    if new in text:
        print(f"skip {name}: already present")
        return text
    if old not in text:
        print(f"skip {name}: anchor missing")
        return text
    if text.count(old) != 1:
        raise SystemExit(f"ERROR: {name} count={text.count(old)}")
    print(f"patch {name}")
    return text.replace(old, new, 1)


def patch_reels_slot_counts(text: str) -> str:
    """MP logo+1, ML logo+4, PC logo+5 (>=1024) else 4. Dart/Midmar card chrome."""
    text = _swap(text, MAC_FIT_HELPERS_OLD, MAC_FIT_HELPERS, "reels-mac-fit-helpers")
    if "function macDayTag" not in text:
        text = _swap(
            text,
            MAC_WHEN_FN_OLD,
            MAC_DAY_TAG + "\n" + MAC_WHEN_FN_NEW,
            "reels-mac-day-tag",
        )
    else:
        text = _swap(text, MAC_WHEN_OLD, MAC_WHEN_NEW, "reels-mac-when-gate")
    text = _swap(text, MAC_PLACEHOLDER_PAD5, MAC_PLACEHOLDER_VIEWPORT, "reels-mac-placeholder-viewport")
    text = _swap(text, MAC_NFIT_FORCE5, MAC_NFIT_VIEWPORT, "reels-mac-nfit-viewport")
    text = _swap(text, MAC_TAG_OLD, MAC_TAG_NEW, "reels-mac-when-tag")
    text = _swap(text, MAC_DAYLABEL_OLD, MAC_DAYLABEL_NEW, "reels-mac-when-day")
    text = _swap(text, MAC_MEET_FIRST_OLD, MAC_MEET_FIRST_NEW, "reels-mac-meet-first")
    text = _swap(text, MAC_MEET_LAST_OLD, MAC_MEET_LAST_NEW, "reels-mac-meet-last")
    text = _swap(text, MAC_EMPTY_OLD, MAC_EMPTY_NEW, "reels-mac-empty-pad")
    text = _swap(text, MAC_COUNTKEY_OLD, MAC_COUNTKEY_NEW, "reels-mac-countkey")
    text = _swap(text, MAC_CHROME_OLD, MAC_CHROME_NEW, "reels-mac-skip-chrome")
    return text


def patch_reels_css(text: str) -> str:
    if MAC_CSS_MARK in text:
        print("skip reels-css-mac-slots: already present")
        return text
    print("patch reels-css-mac-slots")
    return text.rstrip() + "\n" + MAC_CSS_BLOCK


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
    text = _swap(
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
    text = patch_reels_slot_counts(text)
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
    text = _swap(
        text,
        """    if (isDamBottle()) nFit = 5;
""",
        """    if (isDamBottle()) nFit = 5;
    if (isMacTsl()) nFit = macMediaFitCount();
""",
        "reels-nfit-fresh",
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
    bad_wide = """        if (isMacTsl()) {
          brand.style.boxSizing = 'border-box';
          brand.style.padding = '2px';
          brand.style.height = outerH + 'px';
          brand.style.width = Math.round(outerH * 2014 / 780) + 'px';
        }
"""
    if bad_wide in text:
        text = text.replace(bad_wide, "", 1)
        print("revert reels-mac-logo-tile-aspect (keep HMYC brand width)")
    text = apply_one(
        text,
        "if (!(isMidmar() || isDartNats() || isDamBottle()) || !root._mmAutoPlaying) return;",
        "if (!(isMidmar() || isDartNats() || isDamBottle() || isMacTsl()) || !root._mmAutoPlaying) return;",
        "reels-mac-auto-end",
    )
    text = apply_one(
        text,
        "if (!(isMidmar() || isDartNats() || isDamBottle()) || !root) return;",
        "if (!(isMidmar() || isDartNats() || isDamBottle() || isMacTsl()) || !root) return;",
        "reels-mac-mark-browse",
    )
    text = apply_one(
        text,
        "if (!isMidmar() && !isDartNats() && !isDamBottle()) return;",
        "if (!isMidmar() && !isDartNats() && !isDamBottle() && !isMacTsl()) return;",
        "reels-mac-queue-fresh",
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
    # Do not add a 120s group poll. It rate-limits the box and knocks
    # signup Request Code offline (connectionReplaced / not UP).
    return text


def main() -> int:
    reels = REELS.read_text(encoding="utf-8")
    new_reels = patch_reels(reels)
    if new_reels != reels:
        REELS.write_text(new_reels, encoding="utf-8")
        print(f"Wrote {REELS}")
    if REELS_CSS.is_file():
        css = REELS_CSS.read_text(encoding="utf-8")
        new_css = patch_reels_css(css)
        if new_css != css:
            REELS_CSS.write_text(new_css, encoding="utf-8")
            print(f"Wrote {REELS_CSS}")
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
        new_api = api
        for old_pin, new_pin in (
            ("mac-tsl-live-cards.js?v=20261012p", "mac-tsl-live-cards.js?v=20261015c"),
            ("mac-tsl-live-cards.js?v=20261012a", "mac-tsl-live-cards.js?v=20261015c"),
            ("mac-tsl-live-cards.js?v=20261012b", "mac-tsl-live-cards.js?v=20261015c"),
        ):
            if old_pin in new_api:
                new_api = new_api.replace(old_pin, new_pin)
        if new_api != api:
            print("patch api script ver")
            API.write_text(new_api, encoding="utf-8")
        else:
            print("skip api script ver")
    print("MAC TSL media patches done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
