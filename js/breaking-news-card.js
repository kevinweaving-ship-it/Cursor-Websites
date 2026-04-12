/**
 * Breaking News card — isolated module for blank.html only.
 * Does not use hub spotlight, featured event, fleet pills, or other page globals.
 * Data: GET /api/events?blank_hub=1&breaking_news=1 → picks *which* regatta; GET /api/regatta/{id}/results-summary
 * is the single results-backed payload (entries, races, **fleet_stats** from `public.results` — same SQL family as main regatta).
 * Fleet pills are built from `summary.fleet_stats` (then merged when two rows share the same **pill label**, e.g. two
 * `class_id` groups under sheet fleet “Open” → one **Open>n** pill, **n** = sum of entries). Merged pills store **all**
 * `class_id`s; the podium fetches `/classes/{id}/results` for each and merges rows (same overall ordering as the main
 * regatta sheet, which uses `block_id` across boat classes in one fleet).
 * Podium: GET /api/regattas/{id}/classes/{classId}/results — not `/podium` (top-3 cap).
 *
 * Super Admin: Save calls PATCH /api/super-admin/regatta/{id}/breaking-news-meta → UPDATE ``regattas`` (name, host, dates,
 * result_status, as_at_time, blank_hub_news_* hero URL, blank_hub_news_show_hero, blank_hub_news_album JSON;
 * optional ``card_results_url`` / ``card_calendar_url`` when API persists hub link overrides). Upload POST uses
 * ``?target=hero`` (main image only) or ``?target=album`` (append; does not clear hero). Inline form opens from the **Event**
 * fleet pill when **Edit** pill mode is on. Server invalidates results-summary cache after save/upload.
 * Hub featured std slot (``#blank-hub-std-event-slot`` / ``data-blank-hub-std-event``): same Event + Edit pills; save uses
 * PATCH /api/super-admin/calendar-event/{event_id} → ``events`` table; then ``blankHubRefetchStdSlotOnly`` + ``bnCardRefreshAll``.
 *
 * Four slots on blank.html — same card template (`bn-card`); only `data-bn-slot` + section pill differ.
 * Each slot may render multiple `[data-bncard-root]` copies inside `[data-bncard-stack]` when several regattas
 * share the same hub badge (e.g. two “Top News” in DB), up to `MAX_HUB_NEWS_CARDS_PER_SLOT`.
 * `breaking` | `top` | `news` | `archive` | `upcoming event` (featured std slot, not a news column) ← `blank_hub_news_badge_label`.
 * Legacy “Old News” never matches.
 */
(function () {
  'use strict';
abs
  var NS = 'bncard';

  function baseUrl() {
    var b = typeof window.API_BASE === 'string' ? window.API_BASE : '';
    if (b) return b.replace(/\/$/, '');
    try {
      return window.location && window.location.origin ? window.location.origin.replace(/\/$/, '') : '';
    } catch (e) {
      return '';
    }
  }

  function todayYmd() {
    try {
      var d = new Date();
      var y = d.getFullYear();
      var m = String(d.getMonth() + 1).padStart(2, '0');
      var day = String(d.getDate()).padStart(2, '0');
      return y + '-' + m + '-' + day;
    } catch (e) {
      return '';
    }
  }

  /** Calendar day in Africa/Johannesburg — matches DB/event dates for “live” regattas (avoids TZ false negatives). */
  function todayYmdSast() {
    try {
      var s = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Africa/Johannesburg',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).format(new Date());
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    } catch (e) {}
    return todayYmd();
  }

  function ymdSlice(d) {
    if (d == null || d === '') return '';
    return String(d).slice(0, 10);
  }

  /** Today (YYYY-MM-DD) within event window [start, end] inclusive. */
  function isTodayWithinEventRange(today, startYmd, endYmd) {
    var s = ymdSlice(startYmd);
    var e = ymdSlice(endYmd || startYmd) || s;
    if (!s) return false;
    return today >= s && today <= e;
  }

  /** Start date = Day 1. Only when today is within [start, end]. */
  function eventDayNumber(todayYmd, startYmd, endYmd) {
    var s = ymdSlice(startYmd);
    var e = ymdSlice(endYmd || startYmd) || s;
    if (!s || !todayYmd) return null;
    if (todayYmd < s || todayYmd > e) return null;
    var d0 = new Date(s + 'T12:00:00');
    var d1 = new Date(todayYmd + 'T12:00:00');
    if (isNaN(d0.getTime()) || isNaN(d1.getTime())) return null;
    var diff = Math.round((d1 - d0) / 86400000);
    return diff + 1;
  }

  /** Inclusive calendar days from start through end (shown as “Day N” when not in live window). */
  function eventSpanDaysInclusive(startYmd, endYmd) {
    var s = ymdSlice(startYmd);
    var e = ymdSlice(endYmd || startYmd) || s;
    if (!s || !e) return null;
    var d0 = new Date(s + 'T12:00:00');
    var d1 = new Date(e + 'T12:00:00');
    if (isNaN(d0.getTime()) || isNaN(d1.getTime())) return null;
    var diff = Math.round((d1 - d0) / 86400000) + 1;
    return diff > 0 ? diff : 1;
  }

  /** Canonical public regatta page (same slug as the rest of the site). */
  function bnCanonicalRegattaPageUrl(b, summary) {
    if (!b || !summary || typeof summary !== 'object') return '';
    var r = String(summary.regatta_id || '').trim();
    if (!r) return '';
    return String(b).replace(/\/$/, '') + '/regatta/' + encodeURIComponent(r);
  }

  /** Calendar / SAS event page from results-summary merge (keys vary by API version). */
  function bnCalendarEventUrlFromSummary(summary) {
    if (!summary || typeof summary !== 'object') return '';
    var u =
      summary.event_details_url ||
      summary.details_url ||
      summary.source_url ||
      summary.calendar_source_url ||
      '';
    return String(u || '').trim();
  }

  /** Results URL field: saved override if present, else canonical /regatta/{slug}. */
  function bnResultsUrlFieldValue(b, summary) {
    if (!summary || typeof summary !== 'object') return bnCanonicalRegattaPageUrl(b, summary);
    var o = summary.card_results_url || summary.results_page_url || summary.hub_card_results_url;
    if (o != null && String(o).trim()) return String(o).trim();
    return bnCanonicalRegattaPageUrl(b, summary);
  }

  /** Events URL field: saved override if present, else linked calendar row URLs from summary. */
  function bnEventsUrlFieldValue(summary) {
    if (!summary || typeof summary !== 'object') return '';
    var s = summary.card_calendar_url || summary.calendar_event_page_url;
    if (s != null && String(s).trim()) return String(s).trim();
    return bnCalendarEventUrlFromSummary(summary);
  }

  /** Same calendar shape as blank hub: is_live + has_results from dates + counts. */
  function normalizeEvents(events, today) {
    if (!Array.isArray(events)) return [];
    return events.map(function (e) {
      var o = Object.assign({}, e);
      o.races_sailed = o.races_sailed || 0;
      o.entries = o.entries || 0;
      var sd = String(o.start_date || '').slice(0, 10);
      var ed = String(o.end_date || o.start_date || '').slice(0, 10);
      o.start_date = sd;
      o.end_date = ed;
      o.is_live = sd !== '' && ed !== '' && sd <= today && today <= ed;
      o.has_results = o.races_sailed > 0 || o.entries > 0 ? 1 : 0;
      return o;
    });
  }

  function parseEventsPayload(payload) {
    if (payload && typeof payload === 'object' && !Array.isArray(payload) && Array.isArray(payload.events)) {
      return payload.events;
    }
    return Array.isArray(payload) ? payload : [];
  }

  /** Same rules as blank.html — link scraped calendar rows to known regatta_id when missing (29er Nationals → live slug). */
  function bnHubEventLooksLikeWcDinghy(e) {
    if (!e || typeof e !== 'object') return false;
    var rid = String(e.regatta_id || '').trim();
    if (rid === 'live-2026-wc-dinghy-champs-sbyc') return true;
    var blob = (String(e.event_name || '') + ' ' + String(e.regatta_event_name || '')).toLowerCase();
    if (/\bwcdc\s*26\b/.test(blob)) return true;
    if (blob.indexOf('western cape') !== -1 && blob.indexOf('dinghy') !== -1) return true;
    if (blob.indexOf('wc dinghy') !== -1 && blob.indexOf('champ') !== -1) return true;
    return false;
  }

  var BN_HUB_REGATTA_FALLBACK = [
    {
      regatta_id: 'live-2026-wc-dinghy-champs-sbyc',
      match: function (e) {
        return bnHubEventLooksLikeWcDinghy(e);
      }
    },
    {
      regatta_id: 'live-2026-29er-rsa-nationals-sbyc',
      podium_class_id: 3,
      match: function (e) {
        var n = String(e.event_name || '').toLowerCase();
        return /\b29er\b/.test(n) && (n.indexOf('national') !== -1 || n.indexOf('sa ') !== -1 || n.indexOf('championship') !== -1);
      }
    }
  ];

  function applyBnHubRegattaFallback(events) {
    (events || []).forEach(function (e) {
      if (e.regatta_id) return;
      var i;
      for (i = 0; i < BN_HUB_REGATTA_FALLBACK.length; i++) {
        var f = BN_HUB_REGATTA_FALLBACK[i];
        if (f.match(e)) {
          e.regatta_id = f.regatta_id;
          if (f.podium_class_id != null && f.podium_class_id !== '') {
            e.podium_class_id = f.podium_class_id;
          }
          return;
        }
      }
    });
  }

  /**
   * Ordered candidates: live with calendar “has_results”, other live, then recent past with results.
   * Same ordering idea as featured row; duplicates by regatta_id removed.
   */
  function buildCandidateList(events, today) {
    var norm = normalizeEvents(events, today);
    var live = norm.filter(function (e) {
      return e.is_live;
    });
    live.sort(function (a, b) {
      return b.has_results - a.has_results || b.entries - a.entries || b.races_sailed - a.races_sailed;
    });
    var liveWith = live.filter(function (e) {
      return e.has_results && e.regatta_id;
    });
    var liveRest = live.filter(function (e) {
      return e.regatta_id && !e.has_results;
    });
    var pastWith = norm
      .filter(function (e) {
        var end = String(e.end_date || e.start_date || '').slice(0, 10);
        return !e.is_live && e.has_results && end && end < today && e.regatta_id;
      })
      .sort(function (a, b) {
        return String(b.end_date || b.start_date || '').localeCompare(String(a.end_date || a.start_date || ''));
      });
    var out = [];
    var seen = Object.create(null);
    function pushArr(arr) {
      var i;
      for (i = 0; i < arr.length; i++) {
        var e = arr[i];
        var rid = e && e.regatta_id != null ? String(e.regatta_id).trim() : '';
        if (!rid || seen[rid]) continue;
        seen[rid] = true;
        out.push(e);
      }
    }
    pushArr(liveWith);
    pushArr(liveRest);
    pushArr(live.filter(function (e) {
      return e.regatta_id;
    }));
    pushArr(pastWith);
    if (!out.length) {
      var anyResults = norm
        .filter(function (e) {
          var rid = e && e.regatta_id != null ? String(e.regatta_id).trim() : '';
          return rid && e.has_results;
        })
        .sort(function (a, b) {
          return String(b.start_date || '').localeCompare(String(a.start_date || ''));
        });
      pushArr(anyResults);
    }
    return out;
  }

  /**
   * Move regattas whose events row already carries the target hub badge (``regattas`` join on
   * ``/api/events?blank_hub=1&breaking_news=1``) to the front of the candidate list.
   * Without this, SA-tagged “Top News” regattas buried after many live events never appear in
   * the first parallel batch of ``results-summary`` fetches — the Top card stayed empty.
   */
  function prioritizeCandidatesByEventHubBadge(candidates, events, targetBadge) {
    if (!Array.isArray(candidates) || !candidates.length || !targetBadge) return candidates;
    var badgeByRid = Object.create(null);
    (events || []).forEach(function (e) {
      if (!e || e.regatta_id == null) return;
      var rid = String(e.regatta_id).trim();
      if (!rid) return;
      var b = normalizeHubNewsBadge({ blank_hub_news_badge_label: e.blank_hub_news_badge_label });
      if (b) badgeByRid[rid] = b;
    });
    var pri = [];
    var rest = [];
    var i;
    for (i = 0; i < candidates.length; i++) {
      var c = candidates[i];
      var crid = c && c.regatta_id != null ? String(c.regatta_id).trim() : '';
      if (crid && badgeByRid[crid] === targetBadge) pri.push(c);
      else rest.push(c);
    }
    return pri.concat(rest);
  }

  /**
   * Canonical labels from `blank_hub_news_badge_label` so SA “Top News” / “Breaking News”
   * (any casing) route to the right slot.
   */
  function normalizeHubNewsBadge(summary) {
    var raw = String(summary && summary.blank_hub_news_badge_label != null ? summary.blank_hub_news_badge_label : '').trim();
    if (!raw) return '';
    if (/^top\s*news$/i.test(raw)) return 'Top News';
    if (/^breaking\s*news$/i.test(raw)) return 'Breaking News';
    if (/^news$/i.test(raw)) return 'News';
    if (/^archive$/i.test(raw)) return 'Archive';
    if (/^upcoming\s*event$/i.test(raw)) return 'Upcoming Event';
    return raw;
  }

  /** Legacy hub label — not used for Breaking/Top cards; SA should save “Top News” instead. */
  function isLegacyOldNewsBadgeLabel(b) {
    return /^\s*old\s*news\s*$/i.test(String(b || '').trim());
  }

  /** True when today is within the event window (event row or results-summary dates). */
  function eventWindowForCard(eventCandidate, summary, today) {
    var startY = ymdSlice(
      eventCandidate && eventCandidate.start_date != null ? eventCandidate.start_date : summary.start_date
    );
    var endY = ymdSlice(
      eventCandidate && eventCandidate.end_date != null ? eventCandidate.end_date : summary.end_date
    );
    if (!endY && startY) endY = startY;
    return isTodayWithinEventRange(today, startY, endY);
  }

  /**
   * Breaking News slot: explicit SA “Breaking News” (``regattas.blank_hub_news_badge_label`` on results-summary)
   * wins regardless of event dates — hub visibility is DB-driven, not “past = hide”.
   * Unset (auto): still require today within [start, end] so automated picks stay in-window.
   */
  function matchesBreakingSlot(summary, candidate, today) {
    var b = normalizeHubNewsBadge(summary);
    if (isLegacyOldNewsBadgeLabel(b)) return false;
    if (b === 'Upcoming Event') return false;
    if (b === 'Top News' || b === 'News' || b === 'Archive') return false;
    if (b !== 'Breaking News' && b !== '') return false;
    if (b === 'Breaking News') return true;
    return eventWindowForCard(candidate, summary, today);
  }

  /**
   * Top News slot only (Breaking slot logic is separate — do not change together).
   * Matches: SA “Top News” (any time); or past event with Breaking News / unset (auto).
   * Live in-window regattas do not match Top unless explicitly tagged Top News — so WC stays Breaking-only;
   * 29er (or any regatta) with Top News in DB wins via tryExplicitTop + results-summary badge.
   */
  function matchesTopSlot(summary, candidate, today) {
    var b = normalizeHubNewsBadge(summary);
    if (isLegacyOldNewsBadgeLabel(b)) return false;
    if (b === 'Upcoming Event') return false;
    if (b === 'News' || b === 'Archive') return false;
    if (b === 'Top News') return true;
    var inW = eventWindowForCard(candidate, summary, today);
    if (inW) return false;
    return b === 'Breaking News' || b === '';
  }

  function matchesNewsSlot(summary, candidate, today) {
    return normalizeHubNewsBadge(summary) === 'News';
  }

  function matchesArchiveSlot(summary, candidate, today) {
    return normalizeHubNewsBadge(summary) === 'Archive';
  }

  /** docs/RESULTS_HTML_STATUS_LINE_RULE.md — "Results are … as at …" */
  function formatResultsAreLine(status, asAtIso) {
    var raw = String(status || '').trim();
    var st;
    if (!raw) {
      st = 'Provisional';
    } else if (/^final$/i.test(raw)) {
      st = 'Final';
    } else if (/^prov/i.test(raw)) {
      st = 'Provisional';
    } else {
      st = raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
    }
    if (!asAtIso) return 'Results are ' + st;
    var dt = new Date(asAtIso);
    if (isNaN(dt.getTime())) return 'Results are ' + st;
    var mon = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    var day = String(dt.getDate()).padStart(2, '0');
    var month = mon[dt.getMonth()];
    var year = dt.getFullYear();
    var hh = String(dt.getHours()).padStart(2, '0');
    var mm = String(dt.getMinutes()).padStart(2, '0');
    return 'Results are ' + st + ' as at ' + day + ' ' + month + ' ' + year + ' at ' + hh + ':' + mm;
  }

  function formatHostLine(code, name) {
    var c = String(code || '').trim();
    var n = String(name || '').trim();
    if (c && n) {
      if (c.toLowerCase() === n.toLowerCase()) return 'Host: ' + c;
      return 'Host: ' + c + ' — ' + n;
    }
    if (c) return 'Host: ' + c;
    if (n) return 'Host: ' + n;
    return '';
  }

  /** Display title from results sheet: drop leading year so calendar/regatta header year does not duplicate. */
  function stripLeadingYearFromResultName(name) {
    return String(name || '')
      .trim()
      .replace(/^\d{4}\s+/, '');
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /** Two visual lines: all words but last, then last word (e.g. WC Dinghy / Champs). One word = one line. */
  function formatBreakingNewsTitleHtml(title) {
    var t = String(title || '').trim();
    if (!t || t === '—') return escapeHtml(t);
    var parts = t.split(/\s+/).filter(function (w) {
      return w.length;
    });
    if (parts.length <= 1) return escapeHtml(parts[0] || t);
    var last = parts[parts.length - 1];
    var first = parts.slice(0, -1).join(' ');
    return escapeHtml(first) + '<br>' + escapeHtml(last);
  }

  /** "Results Final" / "Results Provisional" (no date). Empty when stored status is None. */
  function formatResultsStatusShort(status) {
    var raw = String(status || '').trim();
    if (/^none$/i.test(raw)) return '';
    var st;
    if (!raw) {
      st = 'Provisional';
    } else if (/^final$/i.test(raw)) {
      st = 'Final';
    } else if (/^prov/i.test(raw)) {
      st = 'Provisional';
    } else {
      st = raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
    }
    return 'Results ' + st;
  }

  /** Second line only: "Mon 6 April 2026 at 14:26". */
  function formatBnAsAtLine(asAtIso) {
    if (!asAtIso) return '';
    var dt = new Date(asAtIso);
    if (isNaN(dt.getTime())) return '';
    var wdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    var mons = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    var wk = wdays[dt.getDay()];
    var mon = mons[dt.getMonth()];
    var day = dt.getDate();
    var y = dt.getFullYear();
    var hh = String(dt.getHours()).padStart(2, '0');
    var mm = String(dt.getMinutes()).padStart(2, '0');
    return wk + ' ' + day + ' ' + mon + ' ' + y + ' at ' + hh + ':' + mm;
  }

  /** Split results-summary ``as_at_time`` ISO into ``<input type="date|time">`` values (browser local). */
  function bnResultsAsAtToDateAndTime(asAtIso) {
    var out = { date: '', time: '' };
    if (!asAtIso) return out;
    var dt = new Date(asAtIso);
    if (isNaN(dt.getTime())) return out;
    var y = dt.getFullYear();
    var m = String(dt.getMonth() + 1).padStart(2, '0');
    var d = String(dt.getDate()).padStart(2, '0');
    var hh = String(dt.getHours()).padStart(2, '0');
    var mm = String(dt.getMinutes()).padStart(2, '0');
    out.date = y + '-' + m + '-' + d;
    out.time = hh + ':' + mm;
    return out;
  }

  /**
   * Combine local date + time to ISO for PATCH ``as_at_time`` (stored as timestamptz).
   * @returns {string|null} ISO string; null if both empty (clear DB); '' if only one set (invalid).
   */
  function bnLocalDateAndTimeToAsAtIso(dateStr, timeStr) {
    var ds = String(dateStr || '').trim();
    var ts = String(timeStr || '').trim();
    if (!ds && !ts) return null;
    if (!ds || !ts) return '';
    var d = new Date(ds + 'T' + ts + ':00');
    if (isNaN(d.getTime())) return '';
    return d.toISOString();
  }

  async function fetchJson(url) {
    try {
    var res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) return null;
    try {
      return await res.json();
    } catch (e) {
      return null;
      }
    } catch (e) {
      return null;
    }
  }

  /**
   * Full class results for Breaking News podium paging (3 ranks per swipe).
   * Do not use /classes/.../podium — that endpoint is capped at top 3 only.
   */
  async function fetchClassResultsForBreakingNewsPodium(b, regattaId, classId) {
    var url =
      b +
      '/api/regattas/' +
      encodeURIComponent(String(regattaId).trim()) +
      '/classes/' +
      encodeURIComponent(String(classId).trim()) +
      '/results';
    var res = await fetch(url, { cache: 'no-store' });
    if (res.status === 404) return [];
    if (!res.ok) return null;
    try {
      var j = await res.json();
      if (!Array.isArray(j)) return [];
      var cap = 150;
      if (j.length > cap) j = j.slice(0, cap);
      return j;
    } catch (e) {
      return null;
    }
  }

  /**
   * Multi-class fleets (e.g. Open: Tera + Saldanha): one pill, several `class_id`s — fetch each class endpoint and merge
   * rows so overall rank 1 (any boat class) appears on the podium.
   */
  async function fetchMergedClassResultsForBreakingNewsPodium(b, regattaId, classIds) {
    if (!classIds || !classIds.length) return [];
    var rid = String(regattaId || '').trim();
    if (!rid) return [];
    var uniq = [];
    var ui;
    for (ui = 0; ui < classIds.length; ui++) {
      var raw = String(classIds[ui] || '').trim();
      if (!raw || uniq.indexOf(raw) !== -1) continue;
      uniq.push(raw);
    }
    if (uniq.length === 0) return [];
    if (uniq.length === 1) {
      return fetchClassResultsForBreakingNewsPodium(b, rid, uniq[0]);
    }
    var parts = await Promise.all(
      uniq.map(function (cid) {
        return fetchClassResultsForBreakingNewsPodium(b, rid, cid);
      })
    );
    var merged = [];
    var seen = Object.create(null);
    var pi;
    for (pi = 0; pi < parts.length; pi++) {
      if (parts[pi] === null) return null;
      var arr = parts[pi];
      var aj;
      for (aj = 0; aj < arr.length; aj++) {
        var row = arr[aj];
        var rk = rowField(row, ['result_id', 'Result_id']);
        var key = rk !== '' ? 'r:' + rk : 'row:' + pi + ':' + aj;
        if (seen[key]) continue;
        seen[key] = 1;
        merged.push(row);
      }
    }
    return merged;
  }

  function rowField(row, keys) {
    var i;
    for (i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (row && row[k] != null && String(row[k]).trim() !== '') return String(row[k]).trim();
    }
    return '';
  }

  /**
   * Integer rank for sort + medals. Handles number from API, "1st", leading digits; avoids bogus sort
   * that sent rank 1 to the end (parseInt-only on odd strings).
   */
  function bnParseRankInt(row) {
    if (!row || typeof row !== 'object') return null;
    var v = row.rank != null ? row.rank : row.Rank;
    if (v == null || v === '') return null;
    if (typeof v === 'number' && isFinite(v)) {
      var rn = Math.round(v);
      return rn > 0 ? rn : null;
    }
    var s = String(v).trim();
    var m = s.match(/^(\d+)/);
    if (m) {
      var n = parseInt(m[1], 10);
      if (isFinite(n) && n > 0) return n;
    }
    return null;
  }

  function ordinalPlace(rank) {
    var n = parseInt(rank, 10);
    if (!isFinite(n)) return String(rank || '').trim();
    var v = n % 100;
    if (v >= 11 && v <= 13) return n + 'th';
    var d = n % 10;
    if (d === 1) return n + 'st';
    if (d === 2) return n + 'nd';
    if (d === 3) return n + 'rd';
    return n + 'th';
  }

  function formatNett(row) {
    var raw = rowField(row, ['nett_points_raw', 'nett_points', 'Nett_points_raw']);
    if (raw === '') return '';
    var x = parseFloat(String(raw).replace(/,/g, ''));
    if (!isFinite(x)) return raw;
    if (Math.abs(x - Math.round(x)) < 1e-6) return String(Math.round(x));
    return String(x);
  }

  /** Same URL rules as blankSailorHref / blankSailorLinkHtml in blank.html (hub podium). */
  function bnSlugFromName(name) {
    var s = String(name || '').trim().toLowerCase();
    s = s.replace(/[^a-z0-9\s-]/g, '');
    s = s.replace(/\s+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    return s;
  }

  function bnSailorHref(name, sasId) {
    var base = bnSlugFromName(name);
    if (!base) return '';
    var sid = String(sasId || '').trim();
    return '/sailor/' + encodeURIComponent(/^\d+$/.test(sid) ? base + '-' + sid : base);
  }

  function bnSailorLinkHtml(name, sasId) {
    var nm = String(name || '').trim();
    if (!nm) return '';
    var href = bnSailorHref(nm, sasId);
    var safe = escapeHtml(nm);
    return href ? '<a href="' + href + '">' + safe + '</a>' : safe;
  }

  function rankNumFromRow(r, fallback) {
    var p = bnParseRankInt(r);
    if (p != null) return p;
    return fallback;
  }

  function medalMoHtml(rankNum, medals) {
    if (rankNum >= 1 && rankNum <= 3) {
      return (
        '<span class="bn-card__podium-medal" aria-hidden="true">' +
        medals[rankNum - 1] +
        '</span>'
      );
    }
    return '<span class="bn-card__podium-medal bn-card__podium-medal--none" aria-hidden="true"></span>';
  }

  /**
   * Pages of 3 ranks; swipe horizontally for 4–6, 7–9, … Same two-line layout when crew.
   * Medals only for overall ranks 1–3; later pages use a spacer where the emoji was.
   */
  function renderBreakingNewsPodiumHtml(rows) {
    if (!rows || !rows.length) return '';
    var medals = ['🥇', '🥈', '🥉'];
    var top = rows.filter(function (r) {
      if (!r) return false;
      if (rowField(r, ['result_id', 'Result_id'])) return true;
      return bnParseRankInt(r) != null && rowField(r, ['helm_name', 'Helm_name']) !== '';
    });
    if (!top.length) return '';
    top.sort(function (a, b) {
      var ra = bnParseRankInt(a);
      var rb = bnParseRankInt(b);
      if (ra == null) ra = 999999;
      if (rb == null) rb = 999999;
      if (ra !== rb) return ra - rb;
      var ida = rowField(a, ['result_id', 'Result_id']);
      var idb = rowField(b, ['result_id', 'Result_id']);
      return String(ida).localeCompare(String(idb));
    });
    var pageSize = 3;
    var pageCount = Math.ceil(top.length / pageSize);
    var parts = [];
    parts.push('<div class="bn-card__podium-outer">');
    parts.push('<div class="bn-card__podium-pages" data-' + NS + '-podium-pages="1">');
    var pi;
    for (pi = 0; pi < pageCount; pi++) {
      parts.push('<div class="bn-card__podium-page">');
      var j;
      for (j = 0; j < pageSize; j++) {
        var idx = pi * pageSize + j;
        if (idx >= top.length) break;
        var r = top[idx];
        var rankNum = rankNumFromRow(r, idx + 1);
        var ord = ordinalPlace(rankNum);
        var helm = rowField(r, ['helm_name', 'Helm_name']);
        var crew = rowField(r, ['crew_name', 'Crew_name']);
        var helmId = rowField(r, ['helm_sa_sailing_id', 'helm_sas_id', 'helm_id']);
        var crewId = rowField(r, ['crew_sa_sailing_id', 'crew_sas_id', 'crew_id']);
        var nett = formatNett(r);
        var hasCrew = crew !== '';
        var mo = medalMoHtml(rankNum, medals);

        parts.push('<div class="bn-card__podium-block">');
        parts.push('<div class="bn-card__podium-grid">');
        parts.push(
          '<div class="bn-card__podium-g-mo">' +
            mo +
            ' <span class="bn-card__podium-ord">' +
            escapeHtml(ord) +
            '</span></div>'
        );
        parts.push('<div class="bn-card__podium-g-helm">' + bnSailorLinkHtml(helm, helmId) + '</div>');
        if (nett !== '') {
          parts.push('<div class="bn-card__podium-g-nett">· Nett ' + escapeHtml(nett) + '</div>');
        } else {
          parts.push('<div class="bn-card__podium-g-nett bn-card__podium-g-nett--empty" aria-hidden="true"></div>');
        }
        if (hasCrew) {
          parts.push('<div class="bn-card__podium-g-crew">' + bnSailorLinkHtml(crew, crewId) + '</div>');
        }
        parts.push('</div>');
        parts.push('</div>');
      }
      parts.push('</div>');
    }
    parts.push('</div>');
    if (pageCount > 1) {
      parts.push('<div class="bn-card__podium-dots" data-' + NS + '-podium-dots="1" aria-hidden="true">');
      var di;
      for (di = 0; di < pageCount; di++) {
        parts.push(
          '<span class="bn-card__podium-dot' +
            (di === 0 ? ' is-active' : '') +
            '" data-dot-idx="' +
            di +
            '"></span>'
        );
      }
      parts.push('</div>');
    }
    parts.push('</div>');
    return parts.join('');
  }

  /** Horizontal scroll + dot indicator (hub blank-podium pattern). Re-bind after each podium load. */
  function bindBreakingNewsPodiumCarousel(podiumEl) {
    var pages = podiumEl.querySelector('[data-' + NS + '-podium-pages]');
    if (!pages) return;
    try {
      pages.scrollLeft = 0;
    } catch (eSl) {}
    if (podiumEl._bnPodiumRo) {
      try {
        podiumEl._bnPodiumRo.disconnect();
      } catch (eD) {
        /* ignore */
      }
      podiumEl._bnPodiumRo = null;
    }
    if (podiumEl._bnPodiumResize) {
      try {
        window.removeEventListener('resize', podiumEl._bnPodiumResize);
      } catch (eR0) {
        /* ignore */
      }
      podiumEl._bnPodiumResize = null;
    }
    var dotsWrap = podiumEl.querySelector('[data-' + NS + '-podium-dots]');
    var dots = dotsWrap ? dotsWrap.querySelectorAll('.bn-card__podium-dot') : [];
    function syncDots() {
      if (!dots || !dots.length) return;
      var w = Math.max(1, pages.clientWidth);
      var page = Math.round(pages.scrollLeft / w);
      if (page < 0) page = 0;
      if (page > dots.length - 1) page = dots.length - 1;
      var i;
      for (i = 0; i < dots.length; i++) {
        if (i === page) dots[i].classList.add('is-active');
        else dots[i].classList.remove('is-active');
      }
    }
    pages.addEventListener('scroll', syncDots, { passive: true });
    if (dotsWrap && dots.length) {
      dotsWrap.addEventListener('click', function (ev) {
        var t = ev.target && ev.target.closest ? ev.target.closest('.bn-card__podium-dot') : null;
        if (!t || !dotsWrap.contains(t)) return;
        var ix = parseInt(t.getAttribute('data-dot-idx'), 10);
        if (!isFinite(ix)) return;
        var w = Math.max(1, pages.clientWidth);
        pages.scrollTo({ left: ix * w, behavior: 'smooth' });
      });
    }
    if (typeof ResizeObserver !== 'undefined') {
      podiumEl._bnPodiumRo = new ResizeObserver(syncDots);
      try {
        podiumEl._bnPodiumRo.observe(pages);
      } catch (eR) {
        podiumEl._bnPodiumRo = null;
      }
    }
    if (!podiumEl._bnPodiumRo) {
      podiumEl._bnPodiumResize = syncDots;
      window.addEventListener('resize', podiumEl._bnPodiumResize, { passive: true });
    }
    syncDots();
  }

  /** WC / open division: hub pill must read "Open", not "Open A" / "Open A Fleet". */
  function bnIsOpenADivisionLabel(s) {
    var t = String(s || '').trim().toLowerCase();
    if (!t || t === 'opening') return false;
    return t === 'open' || t === 'open fleet' || t.startsWith('open a');
  }

  function bnBreakingNewsFleetPillDisplay(raw) {
    var s = String(raw || '').trim();
    if (!s) return s;
    return bnIsOpenADivisionLabel(s) ? 'Open' : s;
  }

  /** Normalize boat/fleet text for comparison (ignore spaces/case — ILCA4 vs ILCA 4). */
  function bnNormalizeBoatLabel(s) {
    return String(s || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '');
  }

  /**
   * Podium needs numeric class_id on each pill. Primary path: `fleet_stats` includes `class_id` per results row group.
   * If `fleetClasses` is passed (fallback when summary has no fleet_stats), **Open** disambiguates boat `name`
   * against rows whose fleet_label is also Open. Do not use boat-first matching for non-Open pills.
   */
  function resolveClassIdForFleetLabel(fleetClasses, pillLabel, boatClassNameFromEntries) {
    if (!fleetClasses || !Array.isArray(fleetClasses)) return null;
    var L = String(pillLabel || '').trim().toLowerCase();
    var boatKey = bnNormalizeBoatLabel(boatClassNameFromEntries);
    var i;
    if (bnIsOpenADivisionLabel(L) && boatKey) {
      for (i = 0; i < fleetClasses.length; i++) {
        var fcb = fleetClasses[i];
        if (!fcb || fcb.class_id == null || String(fcb.class_id).trim() === '') continue;
        var flOpen = String(fcb.fleet_label || '').trim().toLowerCase();
        if (!bnIsOpenADivisionLabel(flOpen)) continue;
        var cnb = bnNormalizeBoatLabel(fcb.class_name);
        var btb = bnNormalizeBoatLabel(fcb.boat_class_name);
        if (cnb === boatKey || btb === boatKey) return String(fcb.class_id);
      }
    }
    if (!L) return null;
    for (i = 0; i < fleetClasses.length; i++) {
      var fc = fleetClasses[i];
      if (!fc || fc.class_id == null || String(fc.class_id).trim() === '') continue;
      var fl = String(fc.fleet_label || '').trim().toLowerCase();
      var cn = String(fc.class_name || '').trim().toLowerCase();
      var boat = String(fc.boat_class_name || '').trim().toLowerCase();
      if (fl && fl === L) return String(fc.class_id);
      if (cn === L) return String(fc.class_id);
      if (boat && boat === L) return String(fc.class_id);
    }
    if (bnIsOpenADivisionLabel(L)) {
      for (i = 0; i < fleetClasses.length; i++) {
        var fc2 = fleetClasses[i];
        if (!fc2 || fc2.class_id == null || String(fc2.class_id).trim() === '') continue;
        var fl2 = String(fc2.fleet_label || '').trim().toLowerCase();
        var cn2 = String(fc2.class_name || '').trim().toLowerCase();
        var boat2 = String(fc2.boat_class_name || '').trim().toLowerCase();
        if (
          bnIsOpenADivisionLabel(fl2) ||
          bnIsOpenADivisionLabel(cn2) ||
          bnIsOpenADivisionLabel(boat2)
        ) {
          return String(fc2.class_id);
        }
      }
    }
    return null;
  }

  /** SA edit only: compact copy for mobile-first editing (99% on phone). */
  function renderBnSaRegattaScopePlaceholderHtml() {
    return (
      '<div class="bn-card__podium-sa-scope bn-card__podium-sa-scope--regatta" role="status">' +
      '<p class="bn-card__podium-sa-scope__hint">General scope — hero &amp; album here. Tap a fleet pill for podium.</p>' +
      '</div>'
    );
  }

  async function loadPodiumForActiveFleet(root) {
    var podiumEl = root.querySelector('[data-' + NS + '-podium]');
    if (!podiumEl) return;
    var rid = (root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
    var wrap = root.querySelector('[data-' + NS + '-fleet-wrap]');
    var active = wrap && wrap.querySelector('.bn-card__fleet-pill.bn-card__fleet-pill--active');
    var b = baseUrl();
    var scopeRegatta =
      active && active.getAttribute('data-' + NS + '-scope') === 'regatta';
    if (scopeRegatta && bnSaCanEdit()) {
      podiumEl.innerHTML = renderBnSaRegattaScopePlaceholderHtml();
      podiumEl.hidden = false;
      return;
    }
    var cid = active && active.getAttribute('data-class-id');
    var multi = active && active.getAttribute('data-class-ids');
    var hasMulti = multi && String(multi).trim() !== '';
    if (!b || !rid || !active || (!cid && !hasMulti)) {
      podiumEl.innerHTML = '';
      podiumEl.hidden = true;
      return;
    }
    var rows;
    if (hasMulti) {
      var ids = String(multi)
        .split(',')
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
      rows = await fetchMergedClassResultsForBreakingNewsPodium(b, rid, ids);
    } else {
      rows = await fetchClassResultsForBreakingNewsPodium(b, rid, cid);
    }
    if (rows === null) {
      podiumEl.innerHTML = '';
      podiumEl.hidden = true;
      return;
    }
    var html = renderBreakingNewsPodiumHtml(rows);
    if (!html) {
      podiumEl.innerHTML = '';
      podiumEl.hidden = true;
      return;
    }
    podiumEl.innerHTML = html;
    podiumEl.hidden = false;
    var pagesScroll = podiumEl.querySelector('[data-' + NS + '-podium-pages]');
    if (pagesScroll) pagesScroll.scrollLeft = 0;
    bindBreakingNewsPodiumCarousel(podiumEl);
  }

  /** Fleet display name: fleet_label when set, else class name (regatta division, not global class table). */
  function fleetDisplayNameFromEntry(data, key) {
    if (data && typeof data === 'object') {
      var fl = String(data.fleet_label || '').trim();
      if (fl) return fl;
      if (data.name) return String(data.name).trim();
    }
    return String(key || '').trim();
  }

  /**
   * `fleet_stats` / class-entries are one row per **class_id**; the sheet can show one “Open” fleet with several classes
   * → duplicate pill text (“Open>1”, “Open>2”). Merge rows that share the same **display** label (after WC Open rules),
   * sum entries, collect **every** `class_id` for the merged pill (podium merges `/classes/{id}/results` for each).
   */
  function mergeDuplicateFleetPillDisplayKeys(classEntriesObj) {
    if (!classEntriesObj || typeof classEntriesObj !== 'object') return classEntriesObj || {};
    var buckets = Object.create(null);
    var k;
    for (k in classEntriesObj) {
      if (!Object.prototype.hasOwnProperty.call(classEntriesObj, k)) continue;
      var data = classEntriesObj[k];
      if (!data || typeof data !== 'object') continue;
      var label = fleetDisplayNameFromEntry(data, k);
      var displayLabel = bnBreakingNewsFleetPillDisplay(label);
      var mkey = String(displayLabel || '').trim().toLowerCase();
      if (!mkey) continue;
      if (!buckets[mkey]) buckets[mkey] = [];
      var ent = parseInt(data.entries, 10);
      if (!isFinite(ent)) ent = 0;
      buckets[mkey].push({ key: k, data: data, ent: ent });
    }
    var out = {};
    var mj = 0;
    for (k in buckets) {
      if (!Object.prototype.hasOwnProperty.call(buckets, k)) continue;
      var arr = buckets[k];
      if (arr.length === 1) {
        out[arr[0].key] = classEntriesObj[arr[0].key];
        continue;
      }
      var sum = 0;
      var bi;
      var best = arr[0];
      var classIdsCollected = [];
      for (bi = 0; bi < arr.length; bi++) {
        sum += arr[bi].ent;
        if (arr[bi].ent > best.ent) best = arr[bi];
        var dx = arr[bi].data;
        if (dx && dx.class_id != null && String(dx.class_id).trim() !== '') {
          var cxs = String(dx.class_id).trim();
          if (classIdsCollected.indexOf(cxs) === -1) classIdsCollected.push(cxs);
        }
      }
      var bd = best.data;
      var merged = {
        name: String(bd.name || '').trim() || String(bd.fleet_label || '').trim(),
        fleet_label: String(bd.fleet_label || '').trim(),
        entries: sum
      };
      if (classIdsCollected.length > 1) {
        merged.class_ids = classIdsCollected;
      } else if (bd.class_id != null && String(bd.class_id).trim() !== '') {
        merged.class_id = bd.class_id;
      }
      out['merged_' + mj + '_' + k.replace(/[^a-z0-9]+/g, '_')] = merged;
      mj++;
    }
    return out;
  }

  /** Alphabetical list for wrap layout (flex-wrap fills row then next row). */
  function buildFleetItems(classEntriesObj) {
    if (!classEntriesObj || typeof classEntriesObj !== 'object') return [];
    return Object.keys(classEntriesObj)
      .map(function (k) {
        var data = classEntriesObj[k];
        var ent = typeof data === 'object' ? parseInt(data.entries, 10) : parseInt(data, 10);
        var label = fleetDisplayNameFromEntry(data, k);
        var displayLabel = bnBreakingNewsFleetPillDisplay(label);
        var boatNm =
          data && typeof data === 'object' && data.name != null ? String(data.name).trim() : '';
        if (!boatNm && k) boatNm = String(k).replace(/_/g, ' ').trim();
        var apiCid = '';
        var apiCids = null;
        if (data && typeof data === 'object') {
          if (Array.isArray(data.class_ids) && data.class_ids.length > 1) {
            apiCids = data.class_ids
              .map(function (x) {
                return String(x).trim();
              })
              .filter(Boolean);
          } else if (data.class_id != null && String(data.class_id).trim() !== '') {
            apiCid = String(data.class_id).trim();
          }
        }
        return {
          label: label,
          displayLabel: displayLabel,
          boatClassName: boatNm,
          classIdFromApi: apiCid,
          classIdsFromApi: apiCids,
          entries: isFinite(ent) ? ent : 0,
          sort: displayLabel.toLowerCase()
        };
      })
      .filter(function (x) {
        return x.entries > 0 && x.label;
      })
      .sort(function (a, b) {
        return a.sort.localeCompare(b.sort);
      });
  }

  /** Aggregate line + root data-*; requires buildFleetItems (above). */
  function formatBnEntriesStatsLine(summary, classEntriesObj) {
    var et = parseInt(summary && summary.entries_total, 10);
    var rt = parseInt(summary && summary.races_total, 10);
    var items = buildFleetItems(classEntriesObj || {});
    var parts = [];
    if (isFinite(et) && et > 0) parts.push(et + (et === 1 ? ' entry' : ' entries'));
    if (items.length > 0) {
      parts.push(items.length + (items.length === 1 ? ' fleet' : ' fleets'));
    }
    if (isFinite(rt) && rt > 0) parts.push('R' + rt + ' sailed');
    return parts.join(' · ');
  }

  /** True if results-summary / class entries give something to show (entries, fleets, or races). */
  function bnSummaryHasResultsBackedData(summary, classEntriesObj) {
    var et = parseInt(summary && summary.entries_total, 10);
    var rt = parseInt(summary && summary.races_total, 10);
    var fleets = buildFleetItems(classEntriesObj || {}).length;
    if (isFinite(et) && et > 0) return true;
    if (isFinite(rt) && rt > 0) return true;
    if (fleets > 0) return true;
    return false;
  }

  /**
   * Red “no results” pill: explicit None, no navigable results URL, or URL/regatta with no backed results rows
   * (e.g. Upcoming Event card before racing).
   */
  function bnEffectiveNoResults(summary, classEntriesObj, resultsHref) {
    var h = String(resultsHref || '').trim();
    var hasUrl = h && h !== '#';
    var rs = String(summary && summary.result_status != null ? summary.result_status : '').trim();
    if (/^none$/i.test(rs)) return true;
    if (!hasUrl) return true;
    if (!bnSummaryHasResultsBackedData(summary, classEntriesObj)) return true;
    return false;
  }

  function formatResultsStatusForDetailLine(summary, classEntriesObj, resultsHref) {
    if (bnEffectiveNoResults(summary, classEntriesObj, resultsHref)) return '';
    return formatResultsStatusShort(summary.result_status);
  }

  /** Merge live SA form fields onto summary for pill/detail preview while editing. */
  function bnMergedSummaryFromHubSaForm(summary, formEl) {
    if (!summary || !formEl) return summary;
    var m = Object.assign({}, summary);
    var rsIn = formEl.querySelector('[name="result_status"]');
    var crIn = formEl.querySelector('[name="card_results_url"]');
    var asDIn = formEl.querySelector('[name="results_as_at_date"]');
    var asTIn = formEl.querySelector('[name="results_as_at_time"]');
    var sdIn = formEl.querySelector('[name="start_date"]');
    var edIn = formEl.querySelector('[name="end_date"]');
    var badgeIn = formEl.querySelector('[name="blank_hub_news_badge_label"]');
    if (rsIn) m.result_status = String(rsIn.value || '').trim();
    if (crIn) {
      var cv = String(crIn.value || '').trim();
      m.card_results_url = cv ? cv : null;
    }
    var asIso = bnLocalDateAndTimeToAsAtIso(
      asDIn ? asDIn.value : '',
      asTIn ? asTIn.value : ''
    );
    if (asIso === null) {
      m.as_at_time = null;
    } else if (asIso !== '') {
      m.as_at_time = asIso;
    }
    if (badgeIn) m.blank_hub_news_badge_label = String(badgeIn.value || '').trim();
    if (sdIn) {
      var sdy = bnSaFormYmd(sdIn);
      m.start_date = sdy ? sdy : null;
    }
    if (edIn) {
      var edy = bnSaFormYmd(edIn);
      m.end_date = edy ? edy : null;
    }
    return m;
  }

  /** Results pill + host / “Results …” detail lines (render + SA inline preview). */
  function bnPaintHubBreakingNewsResultsUi(root, summary, classEntriesObj) {
    var detailLineEl = root.querySelector('[data-' + NS + '-detail-line]');
    var detailLine2El = root.querySelector('[data-' + NS + '-detail-line2]');
    var resultsLinkEl = root.querySelector('[data-' + NS + '-results-link]');
    var b = baseUrl();
    var rid = String(summary.regatta_id || '').trim();
    var resultName = String(summary.result_name != null ? summary.result_name : '').trim();
    var title = stripLeadingYearFromResultName(resultName) || '—';
    var hl = formatHostLine(summary.host_club_code, summary.host_club_name);
    var crOverride = summary && String(summary.card_results_url || '').trim();
    var resultsHref = '#';
    if (crOverride && (/^https?:\/\//i.test(crOverride) || crOverride.indexOf('/') === 0)) {
      resultsHref =
        crOverride.indexOf('/') === 0 && b ? String(b).replace(/\/$/, '') + crOverride : crOverride;
    } else if (b && rid) {
      resultsHref = b + '/regatta/' + encodeURIComponent(rid);
    }
    var effectiveNr = bnEffectiveNoResults(summary, classEntriesObj, resultsHref);
    var statusShort = formatResultsStatusForDetailLine(summary, classEntriesObj, resultsHref);
    var asAtLine = formatBnAsAtLine(summary.as_at_time);
    var line1Bits = [];
    if (hl) line1Bits.push(hl);
    if (statusShort) line1Bits.push(statusShort);
    var detailLine1 = line1Bits.join(' - ');
    if (detailLineEl) {
      detailLineEl.textContent = detailLine1;
      detailLineEl.hidden = !detailLine1;
    }
    if (detailLine2El) {
      detailLine2El.textContent = asAtLine;
      detailLine2El.hidden = !asAtLine || effectiveNr;
    }
    if (resultsLinkEl) {
      var provLabel = resultsLinkEl.querySelector('.blank-hub-hero-prov-label');
      var provCheck = resultsLinkEl.querySelector('.blank-hub-hero-prov-check');
      var greenPill = !effectiveNr;
      if (resultsHref !== '#') {
        resultsLinkEl.setAttribute('href', resultsHref);
        resultsLinkEl.setAttribute(
          'aria-label',
          'Open results for ' + (title !== '—' ? title : resultName || rid)
        );
      } else {
        resultsLinkEl.setAttribute('href', '#');
        resultsLinkEl.setAttribute('aria-label', 'No results');
      }
      if (greenPill) {
        resultsLinkEl.className =
          'blank-hub-hero-badge blank-hub-hero-badge--prov blank-hub-hero-badge--pulse';
        resultsLinkEl.removeAttribute('data-bncard-results-none');
        if (provCheck) provCheck.hidden = false;
        if (provLabel) provLabel.textContent = 'Results';
      } else {
        resultsLinkEl.className = 'blank-hub-hero-badge blank-hub-hero-badge--results-none';
        resultsLinkEl.setAttribute('data-bncard-results-none', '1');
        if (provCheck) provCheck.hidden = true;
        if (provLabel) provLabel.textContent = 'No results';
      }
    }
  }

  /** Section pill (Breaking / Top / … / Upcoming) from `blank_hub_news_badge_label` — render + SA preview. */
  function bnPaintHubSectionBadgeFromLabel(root, mergedSummary) {
    var cardSection = root.closest('[data-blank-bn-card]') || root.closest('.blank-breaking-news-card');
    if (!cardSection || !mergedSummary) return;
    var sectionBadge = cardSection.querySelector('[data-' + NS + '-section-badge]');
    if (!sectionBadge) return;
    var lab = normalizeHubNewsBadge(mergedSummary);
    if (lab === 'Top News') {
      sectionBadge.textContent = 'Top News';
      sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--top-news';
      cardSection.setAttribute('aria-label', 'Top News');
    } else if (lab === 'News') {
      sectionBadge.textContent = 'News';
      sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-news';
      cardSection.setAttribute('aria-label', 'News');
    } else if (lab === 'Archive') {
      sectionBadge.textContent = 'Archive';
      sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-archive';
      cardSection.setAttribute('aria-label', 'Archive');
    } else if (lab === 'Upcoming Event') {
      sectionBadge.textContent = 'Upcoming Event';
      sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-news';
      cardSection.setAttribute('aria-label', 'Upcoming Event');
    } else {
      sectionBadge.textContent = 'Breaking News';
      sectionBadge.className =
        'blank-hub-hero-badge blank-hub-hero-badge--live blank-hub-hero-badge--pulse';
      cardSection.setAttribute('aria-label', 'Breaking News');
    }
  }

  /** Live / Past, Day N, R# — same logic as render (uses event row when regatta ids differ). */
  function bnPaintHubLiveDayRaceBadges(root, summary, eventCandidate) {
    var liveBadgeEl = root.querySelector('[data-' + NS + '-live-badge]');
    var dayBadgeEl = root.querySelector('[data-' + NS + '-day-badge]');
    var raceBadgeEl = root.querySelector('[data-' + NS + '-race-badge]');
    var today = todayYmdSast();
    var ridSum = summary && String(summary.regatta_id || '').trim();
    var ridEv = eventCandidate && String(eventCandidate.regatta_id || '').trim();
    var useRegattaCardDates =
      ridSum &&
      (summary.start_date != null || summary.end_date != null) &&
      (!ridEv || ridEv === ridSum);
    var startY = ymdSlice(
      useRegattaCardDates
        ? summary.start_date != null
          ? summary.start_date
          : eventCandidate && eventCandidate.start_date
        : eventCandidate && eventCandidate.start_date != null
          ? eventCandidate.start_date
          : summary.start_date
    );
    var endY = ymdSlice(
      useRegattaCardDates
        ? summary.end_date != null
          ? summary.end_date
          : eventCandidate && eventCandidate.end_date
        : eventCandidate && eventCandidate.end_date != null
          ? eventCandidate.end_date
          : summary.end_date
    );
    if (!endY && startY) endY = startY;
    var inEventWindow = isTodayWithinEventRange(today, startY, endY);
    var dayNum = eventDayNumber(today, startY, endY);
    var spanDays = startY && endY ? eventSpanDaysInclusive(startY, endY) : null;
    var isBeforeStart = startY && today < startY;
    var isAfterEnd = endY && today > endY;

    if (liveBadgeEl) {
      if (!startY || !endY) {
        liveBadgeEl.hidden = true;
        liveBadgeEl.classList.remove('blank-hub-hero-badge--past', 'blank-hub-hero-badge--live', 'blank-hub-hero-badge--pulse');
      } else if (isBeforeStart) {
        liveBadgeEl.hidden = true;
        liveBadgeEl.classList.remove('blank-hub-hero-badge--past');
        liveBadgeEl.classList.add('blank-hub-hero-badge--live', 'blank-hub-hero-badge--pulse');
        liveBadgeEl.textContent = 'Live';
      } else if (inEventWindow) {
        liveBadgeEl.hidden = false;
        liveBadgeEl.classList.remove('blank-hub-hero-badge--past');
        liveBadgeEl.classList.add('blank-hub-hero-badge--live', 'blank-hub-hero-badge--pulse');
        liveBadgeEl.textContent = 'Live';
      } else if (isAfterEnd) {
        liveBadgeEl.hidden = false;
        liveBadgeEl.classList.remove('blank-hub-hero-badge--live', 'blank-hub-hero-badge--pulse');
        liveBadgeEl.classList.add('blank-hub-hero-badge--past');
        liveBadgeEl.textContent = 'Past';
      } else {
        liveBadgeEl.hidden = true;
        liveBadgeEl.classList.remove('blank-hub-hero-badge--past', 'blank-hub-hero-badge--live', 'blank-hub-hero-badge--pulse');
      }
    }

    if (dayBadgeEl) {
      if (inEventWindow && dayNum != null) {
        dayBadgeEl.hidden = false;
        dayBadgeEl.textContent = 'Day ' + dayNum;
      } else if (!inEventWindow && spanDays != null) {
        dayBadgeEl.hidden = false;
        dayBadgeEl.textContent = 'Day ' + spanDays;
      } else {
        dayBadgeEl.hidden = true;
      }
    }

    var racesN = parseInt(summary.races_total, 10);
    if (raceBadgeEl) {
      if (isFinite(racesN) && racesN > 0) {
        raceBadgeEl.hidden = false;
        raceBadgeEl.textContent = 'R' + racesN;
        raceBadgeEl.setAttribute('aria-label', 'Last race R' + racesN);
      } else {
        raceBadgeEl.hidden = true;
      }
    }
  }

  function renderFleetPillLines(root, classEntriesObj, fleetClasses) {
    var block = root.querySelector('[data-' + NS + '-fleet-block]');
    var wrap = root.querySelector('[data-' + NS + '-fleet-wrap]');
    if (!block || !wrap) return;
    var saEdit = bnSaCanEdit();
    if (!saEdit) {
      try {
        root.removeAttribute('data-' + NS + '-sa-edit-mode');
      } catch (eClr) {}
    }
    wrap.innerHTML = '';
    var fc = Array.isArray(fleetClasses) ? fleetClasses : [];
    var items = buildFleetItems(classEntriesObj);
    var i;
    for (i = 0; i < items.length; i++) {
      var it = items[i];
      var cid = it.classIdFromApi || resolveClassIdForFleetLabel(fc, it.label, it.boatClassName);
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bn-card__fleet-pill' + (i === 0 ? ' bn-card__fleet-pill--active' : '');
      btn.textContent = it.displayLabel + '>' + it.entries;
      btn.setAttribute('aria-label', it.displayLabel + ' fleet, ' + it.entries + ' entries');
      btn.setAttribute('aria-pressed', i === 0 ? 'true' : 'false');
      if (it.classIdsFromApi && it.classIdsFromApi.length > 1) {
        btn.setAttribute('data-class-ids', it.classIdsFromApi.join(','));
      } else if (cid) {
        btn.setAttribute('data-class-id', cid);
      }
      wrap.appendChild(btn);
    }
    if (saEdit) {
      var regBtn = document.createElement('button');
      regBtn.type = 'button';
      var onlyRegatta = items.length === 0;
      regBtn.className =
        'bn-card__fleet-pill bn-card__fleet-pill--regatta' +
        (onlyRegatta ? ' bn-card__fleet-pill--active' : '');
      regBtn.textContent = 'Event';
      regBtn.setAttribute('title', 'Regatta / event — general hero & album (not fleet)');
      regBtn.setAttribute('aria-label', 'Regatta and event: general editing scope');
      regBtn.setAttribute('aria-pressed', onlyRegatta ? 'true' : 'false');
      regBtn.setAttribute('data-' + NS + '-scope', 'regatta');
      wrap.appendChild(regBtn);
      var editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'bn-card__fleet-pill bn-card__fleet-pill--edit';
      editBtn.textContent = 'Edit';
      editBtn.setAttribute('data-' + NS + '-scope', 'edit');
      editBtn.setAttribute(
        'aria-label',
        'Toggle Super Admin edit mode: then choose Event or a fleet as the edit target'
      );
      editBtn.setAttribute(
        'title',
        'Edit mode: green pulse = on. Then select Event or a fleet pill to edit that scope. Tap again to turn off.'
      );
      var editOn = root.getAttribute('data-' + NS + '-sa-edit-mode') === '1';
      editBtn.setAttribute('aria-pressed', editOn ? 'true' : 'false');
      wrap.appendChild(editBtn);
    }
    block.hidden = items.length === 0 && !saEdit;
  }

  function toggleBnSaEditModeForRoot(root) {
    if (!root || !bnSaCanEdit()) return;
    var wasOn = root.getAttribute('data-' + NS + '-sa-edit-mode') === '1';
    if (wasOn) {
      root.removeAttribute('data-' + NS + '-sa-edit-mode');
      exitBnSaInlineEdit(root);
    } else {
      root.setAttribute('data-' + NS + '-sa-edit-mode', '1');
      var wrapT = root.querySelector('[data-' + NS + '-fleet-wrap]');
      var activeP =
        wrapT && wrapT.querySelector('.bn-card__fleet-pill.bn-card__fleet-pill--active');
      if (
        activeP &&
        activeP.getAttribute('data-' + NS + '-scope') === 'regatta' &&
        root._bncardSummary
      ) {
        openBnSaInlineEdit(root, root._bncardSummary);
      }
    }
    var editBtn = root.querySelector('[data-' + NS + '-scope="edit"]');
    if (editBtn) editBtn.setAttribute('aria-pressed', wasOn ? 'false' : 'true');
    try {
      root.dispatchEvent(
        new CustomEvent('bncard-sa-edit-mode', { bubbles: true, detail: { on: !wasOn } })
      );
    } catch (eEv) {}
  }

  /**
   * Delegated clicks on fleet pills (including dynamically cloned hub cards).
   * One listener so extra Breaking/Top/News/Archive card roots do not miss handlers.
   */
  function initFleetPillToggleOnce() {
    if (window.__bnCardFleetDelegateBound) return;
    window.__bnCardFleetDelegateBound = true;
    document.addEventListener(
      'click',
      function (ev) {
        var wrap = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-fleet-wrap]') : null;
        if (!wrap) return;
        var inBn = wrap.closest('[data-blank-bn-card]');
        var inStd = wrap.closest('[data-blank-hub-std-event="1"]');
        if (!inBn && !inStd) return;
        var t = ev.target && ev.target.closest ? ev.target.closest('.bn-card__fleet-pill') : null;
        if (!t || !wrap.contains(t)) return;
        var root = wrap.closest('[data-' + NS + '-root]');
        if (t.getAttribute('data-' + NS + '-scope') === 'edit') {
          ev.preventDefault();
          if (root) toggleBnSaEditModeForRoot(root);
          return;
        }
        var pills = wrap.querySelectorAll('.bn-card__fleet-pill');
        var j;
        for (j = 0; j < pills.length; j++) {
          var pj = pills[j];
          if (pj.getAttribute('data-' + NS + '-scope') === 'edit') continue;
          pj.classList.remove('bn-card__fleet-pill--active');
          pj.setAttribute('aria-pressed', 'false');
        }
        t.classList.add('bn-card__fleet-pill--active');
        t.setAttribute('aria-pressed', 'true');
        var scope = t.getAttribute('data-' + NS + '-scope');
        if (scope !== 'regatta') {
          exitBnSaInlineEdit(root);
        }
        if (root) loadPodiumForActiveFleet(root);
        if (
          scope === 'regatta' &&
          root &&
          root.getAttribute('data-' + NS + '-sa-edit-mode') === '1' &&
          bnSaCanEdit() &&
          root._bncardSummary
        ) {
          openBnSaInlineEdit(root, root._bncardSummary);
        }
      },
      false
    );
  }

  async function loadResultsSummary(regattaId) {
    try {
      const data = await fetchJson(`/api/regatta/${regattaId}/class-entries`);
      return { classes: data };
    } catch (e) {
      console.error("Fallback class-entries failed", e);
      return null;
    }
  }

  /**
   * qualified: show results body. notQualified: show empty line (card stays visible).
   * hidden: hide entire card (no API base).
   */
  function setVisibility(root, mode) {
    var emptyEl = root.querySelector('[data-' + NS + '-empty]');
    var bodyEl = root.querySelector('[data-' + NS + '-body]');
    var cardSection = root.closest('[data-blank-bn-card]');
    if (mode === 'hidden') {
      if (emptyEl) emptyEl.hidden = true;
      if (bodyEl) bodyEl.hidden = true;
      if (cardSection) cardSection.hidden = true;
      return;
    }
    if (mode === 'notQualified') {
      if (emptyEl) emptyEl.hidden = false;
      if (bodyEl) bodyEl.hidden = true;
      if (cardSection) cardSection.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    if (bodyEl) bodyEl.hidden = false;
    if (cardSection) cardSection.hidden = false;
  }

  /**
   * Build the same shape `buildFleetItems` expects, from results-summary `fleet_stats` (API aggregates public.results).
   * Keys are synthetic — only `name`, `fleet_label`, `entries`, `class_id` matter.
   */
  function classEntriesShapeFromFleetStats(summary) {
    var fs = summary && Array.isArray(summary.fleet_stats) ? summary.fleet_stats : [];
    if (!fs.length) return {};
    var out = {};
    var i;
    for (i = 0; i < fs.length; i++) {
      var row = fs[i];
      if (!row) continue;
      var ent = parseInt(row.entries, 10);
      if (!isFinite(ent) || ent <= 0) continue;
      var boat = String(row.boat_class_name || row.class_name || '').trim();
      var fl = String(row.fleet_label || '').trim();
      if (!boat && !fl) continue;
      var cid = row.class_id;
      var key = 'fs_' + i + '_c' + (cid != null ? String(cid) : 'x');
      var o = {
        name: boat,
        fleet_label: fl,
        entries: ent
      };
      if (cid != null && String(cid).trim() !== '') o.class_id = cid;
      out[key] = o;
    }
    return out;
  }

  function bnSaCanEdit() {
    try {
      return typeof window.blankHubSaViewAllowsEdit === 'function' && window.blankHubSaViewAllowsEdit();
    } catch (e) {
      return false;
    }
  }

  /** Rebuild fleet + SA Regatta pill when Public ↔ SA (edit) toggles; restores public-only pill set. */
  function refreshBreakingNewsFleetPillsForRoot(root) {
    if (!root || !root._bncardSummary) return;
    try {
      renderFleetPillLines(root, root._bncardClassEntries || {}, root._bncardFleetClasses || []);
      loadPodiumForActiveFleet(root);
    } catch (eRf) {
      /* ignore */
    }
  }

  /** Call after session / SA view bar loads (race: card renders before SAILINGSA_SESSION_ROLE is set). */
  /** SA event meta edit: use Edit pill + Event pill (not title line). */
  function applyBnSaTitleChromeForRoot(root) {
    if (!root) return;
    var titleLineEl = root.querySelector('[data-' + NS + '-title-line]');
    if (titleLineEl && !titleLineEl.hidden) {
      titleLineEl.classList.remove('bn-card__title-line--sa-editable');
      titleLineEl.removeAttribute('role');
      titleLineEl.removeAttribute('tabindex');
      titleLineEl.removeAttribute('title');
    }
    refreshBreakingNewsFleetPillsForRoot(root);
  }

  function applyBnSaTitleChrome() {
    var nodes = document.querySelectorAll('[data-blank-bn-card] [data-' + NS + '-root]');
    var ni;
    for (ni = 0; ni < nodes.length; ni++) {
      applyBnSaTitleChromeForRoot(nodes[ni]);
    }
    try {
      if (typeof window.blankHubStdSlotWireFleetPills === 'function') {
        window.blankHubStdSlotWireFleetPills();
      }
    } catch (eStd) {
      /* ignore */
    }
  }

  window.bnCardApplySaChrome = applyBnSaTitleChrome;

  /** True when Breaking News card SA “Edit” pill mode is on (choose Event / fleet as edit target). */
  window.bnCardBreakingNewsSaEditModeIsOn = function (optRoot) {
    if (optRoot) {
      return !!(optRoot.getAttribute('data-' + NS + '-sa-edit-mode') === '1');
    }
    var nodes = typeof document !== 'undefined'
      ? document.querySelectorAll('[data-blank-bn-card] [data-' + NS + '-root]')
      : [];
    var ni;
    for (ni = 0; ni < nodes.length; ni++) {
      if (nodes[ni].getAttribute('data-' + NS + '-sa-edit-mode') === '1') return true;
    }
    return false;
  };

  function exitBnSaInlineEdit(root) {
    if (!root) return;
    if (root._bnFormResultsSync) {
      try {
        root._bnFormResultsSync();
      } catch (eFr) {
        /* ignore */
      }
      root._bnFormResultsSync = null;
    }
    if (root._bnClubDocClose) {
      try {
        document.removeEventListener('click', root._bnClubDocClose, true);
      } catch (eRm) {
        /* ignore */
      }
      root._bnClubDocClose = null;
    }
    var viewB = root.querySelector('[data-' + NS + '-view-block]');
    var formEl = root.querySelector('[data-' + NS + '-sa-form]');
    var msgEl = root.querySelector('[data-' + NS + '-sa-msg]');
    if (viewB) viewB.hidden = false;
    if (formEl) {
      try {
        formEl.classList.remove('bn-card__sa-form--open');
      } catch (eRm) {}
      formEl.hidden = true;
      formEl.innerHTML = '';
    }
    if (msgEl) {
      msgEl.textContent = '';
      msgEl.hidden = true;
    }
  }

  function resultStatusSelectValue(raw) {
    var s = String(raw || '').trim().toLowerCase();
    if (s === 'none' || s === 'null') return 'None';
    if (s.indexOf('prov') >= 0) return 'Provisional';
    return 'Final';
  }

  var BN_BADGE_OPTIONS = ['Breaking News', 'Top News', 'News', 'Archive', 'Upcoming Event'];

  function bnHostClubDisplayLabel(summary) {
    var c = String(summary.host_club_code || '').trim();
    var n = String(summary.host_club_name || '').trim();
    if (c && n) {
      if (c.toLowerCase() === n.toLowerCase()) return c;
      return c + ' — ' + n;
    }
    if (c) return c;
    if (n) return n;
    return '';
  }

  function bnCloseClubList(listEl) {
    if (!listEl) return;
    listEl.classList.remove('is-open');
    listEl.innerHTML = '';
  }

  function wireBnSaClubAutocomplete(formEl, b, summary, root) {
    var searchInp = formEl.querySelector('.bn-card__sa-club-search');
    var hiddenInp = formEl.querySelector('[name="host_club_id"]');
    var listEl = formEl.querySelector('[data-' + NS + '-sa-club-list]');
    if (!searchInp || !hiddenInp || !listEl || !root) return;
    if (root._bnClubDocClose) {
      try {
        document.removeEventListener('click', root._bnClubDocClose, true);
      } catch (eR0) {
        /* ignore */
      }
      root._bnClubDocClose = null;
    }
    var resolvedLabel = bnHostClubDisplayLabel(summary);
    var resolvedId =
      summary.host_club_id != null && String(summary.host_club_id).trim() !== ''
        ? String(summary.host_club_id).trim()
        : '';
    searchInp.value = resolvedLabel;
    hiddenInp.value = resolvedId;
    searchInp.setAttribute('data-bn-club-resolved', resolvedId ? '1' : '0');

    function setResolved(club) {
      if (!club) {
        hiddenInp.value = '';
        searchInp.setAttribute('data-bn-club-resolved', '0');
        return;
      }
      hiddenInp.value = String(club.club_id);
      var code = String(club.code || '').trim();
      var name = String(club.name || '').trim();
      var lbl = code && name ? (code.toLowerCase() === name.toLowerCase() ? code : code + ' — ' + name) : code || name;
      searchInp.value = lbl;
      searchInp.setAttribute('data-bn-club-resolved', '1');
      bnCloseClubList(listEl);
    }

    var tmr = null;
    function runSearch(q) {
      var url =
        b +
        '/api/super-admin/clubs-search?q=' +
        encodeURIComponent(q) +
        '&limit=50';
      fetch(url, { credentials: 'include', cache: 'no-store' })
        .then(function (r) {
          return r.ok ? r.json() : { clubs: [] };
        })
        .then(function (data) {
          var arr = data && Array.isArray(data.clubs) ? data.clubs : [];
          listEl.innerHTML = '';
          if (!arr.length) {
            listEl.classList.remove('is-open');
            return;
          }
          var i;
          for (i = 0; i < arr.length; i++) {
            (function (club) {
              var li = document.createElement('li');
              var btn = document.createElement('button');
              btn.type = 'button';
              var code = String(club.code || '').trim();
              var name = String(club.name || '').trim();
              btn.innerHTML =
                '<span class="bn-card__sa-club-code">' +
                escapeHtml(code || '—') +
                '</span>' +
                '<span>' +
                escapeHtml(name || '') +
                '</span>';
              btn.addEventListener('click', function (e) {
                e.preventDefault();
                setResolved(club);
              });
              li.appendChild(btn);
              listEl.appendChild(li);
            })(arr[i]);
          }
          listEl.classList.add('is-open');
        })
        .catch(function () {
          bnCloseClubList(listEl);
        });
    }

    searchInp.addEventListener('input', function () {
      searchInp.setAttribute('data-bn-club-resolved', '0');
      hiddenInp.value = '';
      if (tmr) clearTimeout(tmr);
      var q = String(searchInp.value || '').trim();
      tmr = setTimeout(function () {
        tmr = null;
        runSearch(q);
      }, 220);
    });
    searchInp.addEventListener('focus', function () {
      var q = String(searchInp.value || '').trim();
      runSearch(q);
    });
    root._bnClubDocClose = function (ev) {
      if (!formEl.contains(ev.target)) bnCloseClubList(listEl);
    };
    document.addEventListener('click', root._bnClubDocClose, true);
  }

  /** iOS often gives empty file.type; do not rely on name extension only for “looks like image”. */
  function bnSaImageLooksLikeImage(file) {
    if (!file) return false;
    var t = String(file.type || '').toLowerCase();
    if (t.indexOf('image/') === 0) return true;
    var n = String(file.name || '').toLowerCase();
    return /\.(jpe?g|png|gif|webp|heic|heif|bmp)$/i.test(n);
  }

  function bnSaUploadErrDetail(j, status, text) {
    var d = j && j.detail;
    if (Array.isArray(d)) {
      return d
        .map(function (x) {
          return typeof x === 'object' && x != null ? x.msg || JSON.stringify(x) : String(x);
        })
        .join(' ');
    }
    if (d != null && d !== '') return String(d);
    if (j && j.error) return String(j.error);
    if (status === 413)
      return 'Upload blocked by server size limit (nginx or API). Try a smaller photo or ask ops to raise client_max_body_size.';
    if (text && /413|Request Entity Too Large|too large/i.test(text))
      return 'Upload blocked by server size limit. Try a smaller original or ask ops to raise the upload cap.';
    return status ? 'Upload failed (HTTP ' + status + ').' : 'Upload failed.';
  }

  /**
   * Read YYYY-MM-DD from a date input for PATCH.
   * WebKit (esp. iOS) often does not update .value until the control blurs — use valueAsDate fallback.
   */
  function bnSaFormYmd(inp) {
    if (!inp) return '';
    var v = String(inp.value != null ? inp.value : '').trim();
    if (
      !v &&
      typeof inp.valueAsDate !== 'undefined' &&
      inp.valueAsDate instanceof Date &&
      !isNaN(inp.valueAsDate.getTime())
    ) {
      var d = inp.valueAsDate;
      return (
        d.getFullYear() +
        '-' +
        String(d.getMonth() + 1).padStart(2, '0') +
        '-' +
        String(d.getDate()).padStart(2, '0')
      );
    }
    if (!v) return '';
    var m = v.match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$/);
    if (m) {
      return (
        m[1] +
        '-' +
        String(m[2]).padStart(2, '0') +
        '-' +
        String(m[3]).padStart(2, '0')
      );
    }
    return v.length >= 10 ? v.slice(0, 10) : v;
  }

  function bnSaAlbumFromSummary(summary) {
    var a = summary && summary.blank_hub_news_album;
    if (!Array.isArray(a)) return [];
    var out = [];
    for (var ai = 0; ai < a.length; ai++) {
      var x = a[ai];
      var u = String(x && x.url != null ? x.url : '').trim();
      if (!u) continue;
      out.push({ url: u, carousel: !!(x && x.carousel) });
    }
    return out;
  }

  function bnSaSyncAlbumHiddenFromDom(listWrap, hiddenInp) {
    if (!listWrap || !hiddenInp) return;
    var rows = listWrap.querySelectorAll('[data-' + NS + '-sa-album-item]');
    var out = [];
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri];
      var u = row.getAttribute('data-url') || '';
      var cb = row.querySelector('input[type="checkbox"]');
      out.push({ url: u, carousel: !!(cb && cb.checked) });
    }
    hiddenInp.value = JSON.stringify(out);
  }

  function renderBnSaAlbumEditor(listWrap, hiddenInp, albumArr, b) {
    if (!listWrap || !hiddenInp) return;
    listWrap.innerHTML = '';
    for (var i = 0; i < albumArr.length; i++) {
      var it = albumArr[i];
      var u = String(it && it.url || '').trim();
      if (!u) continue;
      var row = document.createElement('div');
      row.className = 'bn-card__sa-album-item';
      row.setAttribute('data-' + NS + '-sa-album-item', '');
      row.setAttribute('data-url', u);
      var src = /^https?:\/\//i.test(u) ? u : b + (u.indexOf('/') === 0 ? u : '/' + u);
      var carOn = !!(it && it.carousel);
      row.innerHTML =
        '<img class="bn-card__sa-album-thumb" src="' +
        escapeHtml(src).replace(/"/g, '&quot;') +
        '" alt="">' +
        '<label class="bn-card__sa-album-carousel"><input type="checkbox"' +
        (carOn ? ' checked' : '') +
        '> Carousel strip</label>' +
        '<button type="button" class="bn-card__sa-album-remove" data-' +
        NS +
        '-sa-album-remove>Remove</button>';
      var cb = row.querySelector('input[type="checkbox"]');
      if (cb) {
        cb.addEventListener('change', function () {
          bnSaSyncAlbumHiddenFromDom(listWrap, hiddenInp);
        });
      }
      var rm = row.querySelector('[data-' + NS + '-sa-album-remove]');
      if (rm) {
        rm.addEventListener('click', function (e) {
          e.preventDefault();
          row.remove();
          bnSaSyncAlbumHiddenFromDom(listWrap, hiddenInp);
        });
      }
      listWrap.appendChild(row);
    }
    bnSaSyncAlbumHiddenFromDom(listWrap, hiddenInp);
  }

  function wireBnSaImageDrop(formEl, b, rid, msgEl) {
    var drop = formEl.querySelector('[data-' + NS + '-sa-image-drop]');
    var fileInp = formEl.querySelector('[data-' + NS + '-sa-image-file]');
    var prev = formEl.querySelector('[data-' + NS + '-sa-image-preview]');
    var hiddenUrl = formEl.querySelector('[name="blank_hub_news_image_url"]');
    var btnPick = formEl.querySelector('[data-' + NS + '-sa-image-pick]');
    var btnClear = formEl.querySelector('[data-' + NS + '-sa-image-clear]');
    if (!drop || !fileInp || !prev || !hiddenUrl) return;

    function showMsg(t) {
      if (msgEl && t) {
        msgEl.textContent = t;
        msgEl.hidden = false;
      }
    }

    function setPreviewFromUrl(urlPath) {
      hiddenUrl.value = urlPath || '';
      if (!urlPath) {
        prev.removeAttribute('src');
        prev.hidden = true;
        return;
      }
      var src = /^https?:\/\//i.test(urlPath) ? urlPath : b + (urlPath.indexOf('/') === 0 ? urlPath : '/' + urlPath);
      prev.src = src;
      prev.hidden = false;
    }

    if (btnPick) {
      btnPick.addEventListener('click', function (e) {
        e.preventDefault();
        fileInp.click();
      });
    }
    if (btnClear) {
      btnClear.addEventListener('click', function (e) {
        e.preventDefault();
        setPreviewFromUrl('');
      });
    }

    function uploadFile(file) {
      if (!file) return;
      if (file.size === 0 && !bnSaImageLooksLikeImage(file)) {
        showMsg('Choose a photo (JPEG, PNG, HEIC, …).');
        return;
      }
      var fd = new FormData();
      var fname = file.name && String(file.name).trim();
      fd.append('file', file, fname || 'photo.jpg');
      fetch(
        b +
          '/api/super-admin/regatta/' +
          encodeURIComponent(String(rid).trim()) +
          '/breaking-news-image?target=' +
          encodeURIComponent('hero'),
        { method: 'POST', credentials: 'include', body: fd }
      )
        .then(function (r) {
          return r.text().then(function (text) {
            var j = {};
            try {
              j = text ? JSON.parse(text) : {};
            } catch (e) {
              j = {};
            }
            return { ok: r.ok, j: j, status: r.status, text: text || '' };
          });
        })
        .then(function (x) {
          if (!x.ok) {
            showMsg(bnSaUploadErrDetail(x.j, x.status, x.text));
            return;
          }
          var u = x.j && x.j.image_url;
          if (u) setPreviewFromUrl(u);
          if (msgEl) {
            msgEl.textContent = '';
            msgEl.hidden = true;
          }
        })
        .catch(function () {
          showMsg('Upload failed — check your connection and try again.');
        });
    }

    fileInp.addEventListener('change', function () {
      var f = fileInp.files && fileInp.files[0];
      if (f) uploadFile(f);
      fileInp.value = '';
    });
    ['dragenter', 'dragover'].forEach(function (evn) {
      drop.addEventListener(evn, function (e) {
        e.preventDefault();
        e.stopPropagation();
        drop.classList.add('bn-card__sa-image-drop--drag');
      });
    });
    ['dragleave', 'drop'].forEach(function (evn) {
      drop.addEventListener(evn, function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (evn === 'dragleave') drop.classList.remove('bn-card__sa-image-drop--drag');
      });
    });
    drop.addEventListener('drop', function (e) {
      drop.classList.remove('bn-card__sa-image-drop--drag');
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) uploadFile(f);
    });
  }

  function wireBnSaAlbumDrop(formEl, b, rid, msgEl) {
    var drop = formEl.querySelector('[data-' + NS + '-sa-album-drop]');
    var fileInp = formEl.querySelector('[data-' + NS + '-sa-album-file]');
    var listWrap = formEl.querySelector('[data-' + NS + '-sa-album-list]');
    var hiddenInp = formEl.querySelector('[name="blank_hub_news_album_json"]');
    var btnPick = formEl.querySelector('[data-' + NS + '-sa-album-pick]');
    if (!drop || !fileInp || !listWrap || !hiddenInp) return;

    function showMsg(t) {
      if (msgEl && t) {
        msgEl.textContent = t;
        msgEl.hidden = false;
      }
    }

    function uploadFile(file) {
      if (!file) return;
      if (file.size === 0 && !bnSaImageLooksLikeImage(file)) {
        showMsg('Choose a photo (JPEG, PNG, HEIC, …).');
        return;
      }
      var fd = new FormData();
      var fname = file.name && String(file.name).trim();
      fd.append('file', file, fname || 'photo.jpg');
      fetch(
        b +
          '/api/super-admin/regatta/' +
          encodeURIComponent(String(rid).trim()) +
          '/breaking-news-image?target=' +
          encodeURIComponent('album'),
        { method: 'POST', credentials: 'include', body: fd }
      )
        .then(function (r) {
          return r.text().then(function (text) {
            var j = {};
            try {
              j = text ? JSON.parse(text) : {};
            } catch (e) {
              j = {};
            }
            return { ok: r.ok, j: j, status: r.status, text: text || '' };
          });
        })
        .then(function (x) {
          if (!x.ok) {
            showMsg(bnSaUploadErrDetail(x.j, x.status, x.text));
            return;
          }
          var alb = x.j && x.j.album;
          if (Array.isArray(alb)) {
            renderBnSaAlbumEditor(listWrap, hiddenInp, alb, b);
          }
          if (msgEl) {
            msgEl.textContent = '';
            msgEl.hidden = true;
          }
        })
        .catch(function () {
          showMsg('Upload failed — check your connection and try again.');
        });
    }

    if (btnPick) {
      btnPick.addEventListener('click', function (e) {
        e.preventDefault();
        fileInp.click();
      });
    }
    fileInp.addEventListener('change', function () {
      var f = fileInp.files && fileInp.files[0];
      if (f) uploadFile(f);
      fileInp.value = '';
    });
    ['dragenter', 'dragover'].forEach(function (evn) {
      drop.addEventListener(evn, function (e) {
        e.preventDefault();
        e.stopPropagation();
        drop.classList.add('bn-card__sa-image-drop--drag');
      });
    });
    ['dragleave', 'drop'].forEach(function (evn) {
      drop.addEventListener(evn, function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (evn === 'dragleave') drop.classList.remove('bn-card__sa-image-drop--drag');
      });
    });
    drop.addEventListener('drop', function (e) {
      drop.classList.remove('bn-card__sa-image-drop--drag');
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) uploadFile(f);
    });
  }

  function openBnSaCalendarRowInlineEdit(root, summary) {
    var viewB = root.querySelector('[data-' + NS + '-view-block]');
    var formEl = root.querySelector('[data-' + NS + '-sa-form]');
    var msgEl = root.querySelector('[data-' + NS + '-sa-msg]');
    if (!viewB || !formEl) return;
    var b = baseUrl();
    var fullName = String(summary.event_name || '').trim();
    var sd = String(summary.start_date || '').slice(0, 10);
    var ed = String(summary.end_date || summary.start_date || '').slice(0, 10);
    var cat = String(summary.category || '').trim();
    var clubHtml =
      '<div class="bn-card__sa-field bn-card__sa-club-field"><label for="' +
      NS +
      '-std-club-search">Host club</label>' +
      '<input type="hidden" name="host_club_id" value="">' +
      '<input type="text" id="' +
      NS +
      '-std-club-search" class="bn-card__sa-club-search" autocomplete="off" placeholder="Type club name or code — pick from list">' +
      '<ul class="bn-card__sa-club-list" data-' +
      NS +
      '-sa-club-list="" role="listbox" aria-label="Matching clubs"></ul></div>';
    formEl.innerHTML =
      '<div class="bn-card__sa-name-row">' +
      '<input type="text" class="bn-card__sa-name-input" name="event_name" maxlength="500" value="' +
      escapeHtml(fullName).replace(/"/g, '&quot;') +
      '" aria-label="Event name">' +
      '<button type="button" class="bn-card__title-save" data-' +
      NS +
      '-sa-save>Save</button></div>' +
      clubHtml +
      '<div class="bn-card__sa-field"><label for="' +
      NS +
      '-std-category">Category</label>' +
      '<input type="text" id="' +
      NS +
      '-std-category" name="category" maxlength="500" value="' +
      escapeHtml(cat).replace(/"/g, '&quot;') +
      '" placeholder="e.g. Regional, Nationals" aria-label="Category"></div>' +
      '<div class="bn-card__sa-dates">' +
      '<div class="bn-card__sa-field"><label>Start date</label>' +
      '<input type="date" name="start_date" value="' +
      escapeHtml(sd).replace(/"/g, '&quot;') +
      '"></div>' +
      '<div class="bn-card__sa-field"><label>End date</label>' +
      '<input type="date" name="end_date" value="' +
      escapeHtml(ed).replace(/"/g, '&quot;') +
      '"></div></div>' +
      '<p class="bn-card__sa-hint">SAS calendar row (events table). Breaking News hero for the linked regatta is edited on the hub news cards.</p>';
    viewB.hidden = true;
    formEl.hidden = false;
    try {
      formEl.classList.add('bn-card__sa-form--open');
    } catch (eCl) {}
    if (msgEl) {
      msgEl.hidden = true;
      msgEl.textContent = '';
    }
    var sdEl = formEl.querySelector('[name="start_date"]');
    var edEl = formEl.querySelector('[name="end_date"]');
    function bnSaSyncEndMinFromStartStd() {
      if (sdEl && edEl && sdEl.value) {
        edEl.setAttribute('min', sdEl.value);
      }
    }
    bnSaSyncEndMinFromStartStd();
    if (sdEl) {
      sdEl.addEventListener('change', bnSaSyncEndMinFromStartStd);
      sdEl.addEventListener('input', bnSaSyncEndMinFromStartStd);
    }
    if (b) wireBnSaClubAutocomplete(formEl, b, summary, root);
    formEl.onclick = async function (ev) {
      var sv = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-sa-save]') : null;
      if (!sv || !formEl.contains(sv)) return;
      ev.preventDefault();
      await saveBnSaInlineEdit(root, summary);
    };
  }

  async function saveBnSaCalendarRowInlineEdit(root, summary) {
    var formEl = root.querySelector('[data-' + NS + '-sa-form]');
    var msgEl = root.querySelector('[data-' + NS + '-sa-msg]');
    if (!formEl || !summary || !summary.event_id) return;
    var eid = parseInt(String(summary.event_id), 10);
    if (!isFinite(eid) || eid < 1) return;
    var sdBlur = formEl.querySelector('[name="start_date"]');
    var edBlur = formEl.querySelector('[name="end_date"]');
    try {
      if (sdBlur) sdBlur.blur();
      if (edBlur) edBlur.blur();
    } catch (eBl) {}
    await new Promise(function (resolve) {
      setTimeout(resolve, 80);
    });
    var b = baseUrl();
    if (!b) return;
    var nm = formEl.querySelector('[name="event_name"]');
    var hidIn = formEl.querySelector('[name="host_club_id"]');
    var clubSearch = formEl.querySelector('.bn-card__sa-club-search');
    var sdIn = formEl.querySelector('[name="start_date"]');
    var edIn = formEl.querySelector('[name="end_date"]');
    var catIn = formEl.querySelector('[name="category"]');
    var eventName = nm ? String(nm.value || '').trim() : '';
    if (!eventName) {
      if (msgEl) {
        msgEl.textContent = 'Name is required.';
        msgEl.hidden = false;
      }
      return;
    }
    var sdVal = bnSaFormYmd(sdIn);
    var edVal = bnSaFormYmd(edIn);
    if (!sdVal) {
      if (msgEl) {
        msgEl.textContent = 'Start date is required.';
        msgEl.hidden = false;
      }
      return;
    }
    if (!edVal) edVal = sdVal;
    var typedClub = clubSearch && String(clubSearch.value || '').trim();
    if (typedClub && clubSearch.getAttribute('data-bn-club-resolved') !== '1') {
      if (msgEl) {
        msgEl.textContent = 'Pick a host club from the list (or clear the field to remove host).';
        msgEl.hidden = false;
      }
      return;
    }
    var hidVal = hidIn ? String(hidIn.value || '').trim() : '';
    var body = {
      event_name: eventName,
      start_date: sdVal,
      end_date: edVal
    };
    if (catIn) {
      var cv = String(catIn.value || '').trim();
      body.category = cv || null;
    }
    if (hidVal && /^\d+$/.test(hidVal)) {
      body.host_club_id = parseInt(hidVal, 10);
    } else {
      body.host_club_id = null;
    }
    try {
      var res = await fetch(
        b + '/api/super-admin/calendar-event/' + encodeURIComponent(String(eid)),
        {
          method: 'PATCH',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        }
      );
      var j = null;
      try {
        j = await res.json();
      } catch (eJ) {
        j = null;
      }
      if (!res.ok) {
        var err = (j && j.detail) || res.statusText || 'Save failed';
        if (msgEl) {
          msgEl.textContent =
            typeof err === 'string'
              ? err
              : Array.isArray(err)
                ? err
                    .map(function (x) {
                      return x.msg || x;
                    })
                    .join(' ')
                : 'Save failed';
          msgEl.hidden = false;
        }
        return;
      }
      exitBnSaInlineEdit(root);
      try {
        localStorage.setItem('sailsa_hub_news_dirty', String(Date.now()));
      } catch (eLs) {}
      try {
        window.__blankHubPrimaryBundlePromise = null;
      } catch (eClr) {}
      if (typeof window.blankHubRefetchStdSlotOnly === 'function') {
        await window.blankHubRefetchStdSlotOnly();
      }
      if (typeof window.bnCardRefreshAll === 'function') {
        await window.bnCardRefreshAll();
      }
    } catch (e) {
      if (msgEl) {
        msgEl.textContent = 'Save failed';
        msgEl.hidden = false;
      }
    }
  }

  function openBnSaInlineEdit(root, summary) {
    if (!root || !summary) return;
    if (summary._calendarRowEdit && summary.event_id) {
      openBnSaCalendarRowInlineEdit(root, summary);
      return;
    }
    var viewB = root.querySelector('[data-' + NS + '-view-block]');
    var formEl = root.querySelector('[data-' + NS + '-sa-form]');
    var msgEl = root.querySelector('[data-' + NS + '-sa-msg]');
    if (!viewB || !formEl) return;
    if (root._bnFormResultsSync) {
      try {
        root._bnFormResultsSync();
      } catch (ePrev) {
        /* ignore */
      }
      root._bnFormResultsSync = null;
    }
    var b = baseUrl();
    var fullName = String(summary.result_name != null ? summary.result_name : summary.event_name || '').trim();
    var rs = resultStatusSelectValue(summary.result_status);
    var sd = String(summary.start_date || '').slice(0, 10);
    var ed = String(summary.end_date || '').slice(0, 10);
    var curBadge = String(summary.blank_hub_news_badge_label || '').trim() || 'Breaking News';
    var curImg = String(summary.blank_hub_news_image_url || '').trim();
    var showHero = summary.blank_hub_news_show_hero !== false;
    var asAtParts = bnResultsAsAtToDateAndTime(summary.as_at_time);
    var urlResultsVal = escapeHtml(bnResultsUrlFieldValue(b, summary)).replace(/"/g, '&quot;');
    var urlEventsVal = escapeHtml(bnEventsUrlFieldValue(summary)).replace(/"/g, '&quot;');

    var bi;
    var badgeSelectHtml =
      '<div class="bn-card__sa-field"><label for="' +
      NS +
      '-sa-badge">Card Type News/Upcoming Event</label>' +
      '<select id="' +
      NS +
      '-sa-badge" name="blank_hub_news_badge_label" aria-label="Card Type News/Upcoming Event">' +
      '';
    for (bi = 0; bi < BN_BADGE_OPTIONS.length; bi++) {
      var opt = BN_BADGE_OPTIONS[bi];
      badgeSelectHtml +=
        '<option value="' +
        escapeHtml(opt).replace(/"/g, '&quot;') +
        '"' +
        (opt === curBadge ? ' selected' : '') +
        '>' +
        escapeHtml(opt) +
        '</option>';
    }
    badgeSelectHtml += '</select></div>';

    var clubHtml =
      '<div class="bn-card__sa-field bn-card__sa-club-field"><label for="' +
      NS +
      '-club-search">Host club</label>' +
      '<input type="hidden" name="host_club_id" value="">' +
      '<input type="text" id="' +
      NS +
      '-club-search" class="bn-card__sa-club-search" autocomplete="off" placeholder="Type club name or code — pick from list">' +
      '<ul class="bn-card__sa-club-list" data-' +
      NS +
      '-sa-club-list="" role="listbox" aria-label="Matching clubs"></ul></div>';

    var prevSrc = '';
    if (curImg && b) {
      prevSrc = /^https?:\/\//i.test(curImg)
        ? curImg
        : b + (curImg.indexOf('/') === 0 ? curImg : '/' + curImg);
    }
    var imageHtml =
      '<div class="bn-card__sa-field"><label>Hero image</label>' +
      '<input type="hidden" name="blank_hub_news_image_url" value="' +
      escapeHtml(curImg).replace(/"/g, '&quot;') +
      '">' +
      '<div class="bn-card__sa-image-drop" data-' +
      NS +
      '-sa-image-drop tabindex="0">' +
      '<span class="bn-card__sa-image-hint">Main card photo — server shrinks to JPEG. Does not remove album photos.</span>' +
      '<img class="bn-card__sa-image-preview" data-' +
      NS +
      '-sa-image-preview alt=""' +
      (prevSrc ? ' src="' + escapeHtml(prevSrc).replace(/"/g, '&quot;') + '"' : '') +
      (prevSrc ? '' : ' hidden') +
      '>' +
      '<div class="bn-card__sa-image-actions">' +
      '<input type="file" class="bn-card__sa-image-file" data-' +
      NS +
      '-sa-image-file accept="image/*,.heic,.heif">' +
      '<button type="button" data-' +
      NS +
      '-sa-image-pick>Choose hero photo</button>' +
      '<button type="button" data-' +
      NS +
      '-sa-image-clear>Remove hero</button>' +
      '</div></div></div>';

    var heroToggleHtml =
      '<div class="bn-card__sa-field bn-card__sa-field--hero-toggle">' +
      '<label class="bn-card__sa-inline-check"><input type="checkbox" name="blank_hub_news_show_hero"' +
      (showHero ? ' checked' : '') +
      '> Show hero on card</label>' +
      '<span class="bn-card__sa-hint">Off hides the main slot; album strip still works for “Carousel” items.</span>' +
      '</div>';

    var albumJson0 = JSON.stringify(bnSaAlbumFromSummary(summary));
    var albumHtml =
      '<div class="bn-card__sa-field"><label>Image album</label>' +
      '<span class="bn-card__sa-image-hint">Add extras here — kept when you change hero. Tick <strong>Carousel strip</strong> for the scroll row below the image row.</span>' +
      '<input type="hidden" name="blank_hub_news_album_json" value="' +
      escapeHtml(albumJson0) +
      '">' +
      '<div class="bn-card__sa-album-list" data-' +
      NS +
      '-sa-album-list></div>' +
      '<div class="bn-card__sa-image-drop bn-card__sa-album-drop" data-' +
      NS +
      '-sa-album-drop tabindex="0">' +
      '<span class="bn-card__sa-image-hint">Drop or choose — adds to album (does not replace hero).</span>' +
      '<div class="bn-card__sa-image-actions">' +
      '<input type="file" class="bn-card__sa-image-file" data-' +
      NS +
      '-sa-album-file accept="image/*,.heic,.heif">' +
      '<button type="button" data-' +
      NS +
      '-sa-album-pick>Add to album</button>' +
      '</div></div></div>';

    formEl.innerHTML =
      '<div class="bn-card__sa-field bn-card__sa-field--event-name">' +
      '<label for="' +
      NS +
      '-sa-event-name">Event name</label>' +
      '<div class="bn-card__sa-name-row">' +
      '<input type="text" class="bn-card__sa-name-input" id="' +
      NS +
      '-sa-event-name" name="event_name" maxlength="500" value="' +
      escapeHtml(fullName).replace(/"/g, '&quot;') +
      '" aria-label="Event name">' +
      '<button type="button" class="bn-card__title-save" data-' +
      NS +
      '-sa-save>Save</button></div></div>' +
      '<div class="bn-card__sa-field">' +
      '<label for="' +
      NS +
      '-sa-card-results-url">Results URL</label>' +
      '<span class="bn-card__sa-hint">SailingSA results page for this card (editable). Default = public /regatta link.</span>' +
      '<input type="url" class="bn-card__sa-name-input" id="' +
      NS +
      '-sa-card-results-url" name="card_results_url" value="' +
      urlResultsVal +
      '" placeholder="https://sailingsa.co.za/regatta/…" autocomplete="off" inputmode="url">' +
      '<div class="bn-card__sa-url-actions">' +
      '<button type="button" class="bn-card__sa-url-btn" data-' +
      NS +
      '-sa-use-regatta-url>Use SailingSA /regatta link</button> ' +
      '<button type="button" class="bn-card__sa-url-btn" data-' +
      NS +
      '-sa-open-url="results">Open</button>' +
      '</div></div>' +
      '<div class="bn-card__sa-field">' +
      '<label for="' +
      NS +
      '-sa-card-events-url">Events URL</label>' +
      '<span class="bn-card__sa-hint">External / SAS calendar event page when linked (from events row when API provides it).</span>' +
      '<input type="url" class="bn-card__sa-name-input" id="' +
      NS +
      '-sa-card-events-url" name="card_calendar_url" value="' +
      urlEventsVal +
      '" placeholder="https://www.sailing.org.za/events/…" autocomplete="off" inputmode="url">' +
      '<div class="bn-card__sa-url-actions">' +
      '<button type="button" class="bn-card__sa-url-btn" data-' +
      NS +
      '-sa-open-url="events">Open</button>' +
      '</div></div>' +
      badgeSelectHtml +
      clubHtml +
      '<div class="bn-card__sa-field"><label>Results</label>' +
      '<select name="result_status" aria-label="Final, Provisional, or None">' +
      '<option value="Final"' +
      (rs === 'Final' ? ' selected' : '') +
      '>Final</option>' +
      '<option value="Provisional"' +
      (rs === 'Provisional' ? ' selected' : '') +
      '>Provisional</option>' +
      '<option value="None"' +
      (rs === 'None' ? ' selected' : '') +
      '>None</option></select>' +
      '<span class="bn-card__sa-hint">“Results are … as at …” on the card uses the date and time below.</span></div>' +
      '<div class="bn-card__sa-dates bn-card__sa-asat-row" role="group" aria-label="Results as at">' +
      '<div class="bn-card__sa-field"><label for="' +
      NS +
      '-sa-results-asat-date">As at date</label>' +
      '<input type="date" id="' +
      NS +
      '-sa-results-asat-date" name="results_as_at_date" value="' +
      escapeHtml(asAtParts.date).replace(/"/g, '&quot;') +
      '"></div>' +
      '<div class="bn-card__sa-field"><label for="' +
      NS +
      '-sa-results-asat-time">Time</label>' +
      '<input type="time" id="' +
      NS +
      '-sa-results-asat-time" name="results_as_at_time" step="60" value="' +
      escapeHtml(asAtParts.time).replace(/"/g, '&quot;') +
      '"></div></div>' +
      '<div class="bn-card__sa-dates">' +
      '<div class="bn-card__sa-field"><label>Start date</label>' +
      '<input type="date" name="start_date" value="' +
      escapeHtml(sd).replace(/"/g, '&quot;') +
      '"></div>' +
      '<div class="bn-card__sa-field"><label>End date</label>' +
      '<input type="date" name="end_date" value="' +
      escapeHtml(ed).replace(/"/g, '&quot;') +
      '"></div></div>' +
      imageHtml +
      heroToggleHtml +
      albumHtml;
    viewB.hidden = true;
    formEl.hidden = false;
    try {
      formEl.classList.add('bn-card__sa-form--open');
    } catch (eCl2) {}
    if (msgEl) {
      msgEl.hidden = true;
      msgEl.textContent = '';
    }
    var sdEl = formEl.querySelector('[name="start_date"]');
    var edEl = formEl.querySelector('[name="end_date"]');
    function bnSaSyncEndMinFromStart() {
      if (sdEl && edEl && sdEl.value) {
        edEl.setAttribute('min', sdEl.value);
      }
    }
    bnSaSyncEndMinFromStart();
    if (sdEl) {
      sdEl.addEventListener('change', bnSaSyncEndMinFromStart);
      sdEl.addEventListener('input', bnSaSyncEndMinFromStart);
    }
    if (b) wireBnSaClubAutocomplete(formEl, b, summary, root);
    if (b) {
      var ridImg = String(summary.regatta_id || root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
      if (ridImg) {
        wireBnSaImageDrop(formEl, b, ridImg, msgEl);
        wireBnSaAlbumDrop(formEl, b, ridImg, msgEl);
      }
      var listW = formEl.querySelector('[data-' + NS + '-sa-album-list]');
      var hidA = formEl.querySelector('[name="blank_hub_news_album_json"]');
      if (listW && hidA) {
        renderBnSaAlbumEditor(listW, hidA, bnSaAlbumFromSummary(summary), b);
      }
    }
    function bnFormHubSaChromePreview() {
      if (!root._bncardSummary || !formEl || formEl.hidden) return;
      var merged = bnMergedSummaryFromHubSaForm(root._bncardSummary, formEl);
      bnPaintHubBreakingNewsResultsUi(root, merged, root._bncardClassEntries || {});
      bnPaintHubSectionBadgeFromLabel(root, merged);
      bnPaintHubLiveDayRaceBadges(root, merged, root._bncardEventCandidate);
    }
    formEl.onclick = async function (ev) {
      var op = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-sa-open-url]') : null;
      if (op && formEl.contains(op)) {
        var which = op.getAttribute('data-' + NS + '-sa-open-url');
        var inpOpen =
          which === 'events'
            ? formEl.querySelector('[name="card_calendar_url"]')
            : formEl.querySelector('[name="card_results_url"]');
        if (inpOpen && String(inpOpen.value || '').trim()) {
          try {
            window.open(inpOpen.value.trim(), '_blank', 'noopener,noreferrer');
          } catch (eOp) {}
        }
        return;
      }
      var useR = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-sa-use-regatta-url]') : null;
      if (useR && formEl.contains(useR)) {
        var inpR = formEl.querySelector('[name="card_results_url"]');
        if (inpR && b) inpR.value = bnCanonicalRegattaPageUrl(b, summary);
        bnFormHubSaChromePreview();
        return;
      }
      var sv = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-sa-save]') : null;
      if (!sv || !formEl.contains(sv)) return;
      ev.preventDefault();
      await saveBnSaInlineEdit(root, summary);
    };
    bnFormHubSaChromePreview();
    formEl.addEventListener('change', bnFormHubSaChromePreview);
    formEl.addEventListener('input', bnFormHubSaChromePreview);
    root._bnFormResultsSync = function () {
      formEl.removeEventListener('change', bnFormHubSaChromePreview);
      formEl.removeEventListener('input', bnFormHubSaChromePreview);
    };
  }

  async function saveBnSaInlineEdit(root, summary) {
    var formEl = root.querySelector('[data-' + NS + '-sa-form]');
    var msgEl = root.querySelector('[data-' + NS + '-sa-msg]');
    if (!formEl || !summary) return;
    if (summary._calendarRowEdit && summary.event_id) {
      await saveBnSaCalendarRowInlineEdit(root, summary);
      return;
    }
    var sdBlur = formEl.querySelector('[name="start_date"]');
    var edBlur = formEl.querySelector('[name="end_date"]');
    try {
      if (sdBlur) sdBlur.blur();
      if (edBlur) edBlur.blur();
    } catch (eBl) {}
    await new Promise(function (resolve) {
      setTimeout(resolve, 80);
    });
    var rid = String(summary.regatta_id || root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
    var b = baseUrl();
    if (!b || !rid) return;
    var nm = formEl.querySelector('[name="event_name"]');
    var hidIn = formEl.querySelector('[name="host_club_id"]');
    var clubSearch = formEl.querySelector('.bn-card__sa-club-search');
    var rsIn = formEl.querySelector('[name="result_status"]');
    var sdIn = formEl.querySelector('[name="start_date"]');
    var edIn = formEl.querySelector('[name="end_date"]');
    var asDIn = formEl.querySelector('[name="results_as_at_date"]');
    var asTIn = formEl.querySelector('[name="results_as_at_time"]');
    var asIso = bnLocalDateAndTimeToAsAtIso(
      asDIn ? asDIn.value : '',
      asTIn ? asTIn.value : ''
    );
    var rsVal = rsIn ? String(rsIn.value || '').trim() : 'Final';
    if (asIso === '') {
      if (msgEl) {
        msgEl.textContent = 'Set both “As at date” and “Time”, or clear both.';
        msgEl.hidden = false;
      }
      return;
    }
    var body = {
      event_name: nm ? String(nm.value || '').trim() : '',
      result_status: rsVal,
      as_at_time: asIso,
      start_date: bnSaFormYmd(sdIn),
      end_date: bnSaFormYmd(edIn)
    };
    if (!body.event_name) {
      if (msgEl) {
        msgEl.textContent = 'Name is required.';
        msgEl.hidden = false;
      }
      return;
    }
    var typedClub = clubSearch && String(clubSearch.value || '').trim();
    if (typedClub && clubSearch.getAttribute('data-bn-club-resolved') !== '1') {
      if (msgEl) {
        msgEl.textContent = 'Pick a host club from the list (or clear the field to remove host).';
        msgEl.hidden = false;
      }
      return;
    }
    var hidVal = hidIn ? String(hidIn.value || '').trim() : '';
    if (hidVal && /^\d+$/.test(hidVal)) {
      body.host_club_id = parseInt(hidVal, 10);
    } else {
      body.host_club_id = null;
    }
    var bs = formEl.querySelector('[name="blank_hub_news_badge_label"]');
    if (bs) body.blank_hub_news_badge_label = String(bs.value || '').trim();
    var iuIn = formEl.querySelector('[name="blank_hub_news_image_url"]');
    if (iuIn) body.blank_hub_news_image_url = String(iuIn.value || '').trim() || null;
    var hidAlbum = formEl.querySelector('[name="blank_hub_news_album_json"]');
    if (hidAlbum) {
      try {
        var parsedA = JSON.parse(String(hidAlbum.value || '').trim() || '[]');
        body.blank_hub_news_album = Array.isArray(parsedA) ? parsedA : [];
      } catch (eAl) {
        body.blank_hub_news_album = [];
      }
    }
    var shIn = formEl.querySelector('[name="blank_hub_news_show_hero"]');
    if (shIn) body.blank_hub_news_show_hero = !!shIn.checked;
    var crIn = formEl.querySelector('[name="card_results_url"]');
    var ceIn = formEl.querySelector('[name="card_calendar_url"]');
    if (crIn) {
      var crv = String(crIn.value || '').trim();
      body.card_results_url = crv || null;
    }
    if (ceIn) {
      var cev = String(ceIn.value || '').trim();
      body.card_calendar_url = cev || null;
    }
    try {
      var res = await fetch(
        b + '/api/super-admin/regatta/' + encodeURIComponent(rid) + '/breaking-news-meta',
        {
          method: 'PATCH',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        }
      );
      var j = null;
      try {
        j = await res.json();
      } catch (eJ) {
        j = null;
      }
      if (!res.ok) {
        var err = (j && j.detail) || res.statusText || 'Save failed';
        if (msgEl) {
          msgEl.textContent =
            typeof err === 'string' ? err : Array.isArray(err) ? err.map(function (x) { return x.msg || x; }).join(' ') : 'Save failed';
          msgEl.hidden = false;
        }
        return;
      }
      exitBnSaInlineEdit(root);
      try {
        localStorage.setItem('sailsa_hub_news_dirty', String(Date.now()));
      } catch (eLs) {}
      await refreshAll();
    } catch (e) {
      if (msgEl) {
        msgEl.textContent = 'Save failed';
        msgEl.hidden = false;
      }
    }
  }

  async function render(root, summary, eventCandidate, classEntriesObj, fleetClasses) {
    exitBnSaInlineEdit(root);
    root._bncardSummary = summary;
    root._bncardClassEntries = classEntriesObj || {};
    root._bncardFleetClasses = Array.isArray(fleetClasses) ? fleetClasses : [];
    root._bncardEventCandidate = eventCandidate || null;
    var titleLineEl = root.querySelector('[data-' + NS + '-title-line]');
    var b = baseUrl();
    var rid = String(summary.regatta_id || '').trim();
    root.setAttribute('data-' + NS + '-regatta-id', rid);
    var resultName = String(summary.result_name != null ? summary.result_name : '').trim();
    var title = stripLeadingYearFromResultName(resultName) || '—';
    if (titleLineEl) {
      titleLineEl.innerHTML = formatBreakingNewsTitleHtml(title);
      titleLineEl.hidden = false;
      applyBnSaTitleChromeForRoot(root);
    }
    bnPaintHubBreakingNewsResultsUi(root, summary, classEntriesObj);
    bnPaintHubSectionBadgeFromLabel(root, summary);
    var statsLineEl = root.querySelector('[data-' + NS + '-stats-line]');
    var statsText = formatBnEntriesStatsLine(summary, classEntriesObj);
    if (statsLineEl) {
      statsLineEl.textContent = statsText;
      statsLineEl.hidden = !statsText;
    }
    var etAttr = parseInt(summary.entries_total, 10);
    var rtAttr = parseInt(summary.races_total, 10);
    var pillN = buildFleetItems(classEntriesObj || {}).length;
    root.setAttribute(
      'data-' + NS + '-entries-total',
      isFinite(etAttr) && etAttr > 0 ? String(etAttr) : ''
    );
    root.setAttribute(
      'data-' + NS + '-races-total',
      isFinite(rtAttr) && rtAttr > 0 ? String(rtAttr) : ''
    );
    root.setAttribute('data-' + NS + '-fleet-pills', pillN > 0 ? String(pillN) : '');

    var imgSlot = root.querySelector('[data-' + NS + '-image-placeholder]');
    var podiumRow = root.querySelector('.bn-card__image-podium-row');
    var showHeroCard = summary.blank_hub_news_show_hero !== false;
    if (imgSlot) {
      var iu = String(summary.blank_hub_news_image_url || '').trim();
      imgSlot.innerHTML = '';
      if (showHeroCard && iu) {
        var im = document.createElement('img');
        im.src = /^https?:\/\//i.test(iu) ? iu : b + (iu.indexOf('/') === 0 ? iu : '/' + iu);
        im.alt = '';
        im.className = 'bn-card__bn-hero-img';
        imgSlot.appendChild(im);
      } else if (!showHeroCard && iu) {
        var spH = document.createElement('span');
        spH.className = 'bn-card__image-slot-label';
        spH.textContent = 'Hero hidden';
        imgSlot.appendChild(spH);
      } else {
        var sp = document.createElement('span');
        sp.className = 'bn-card__image-slot-label';
        sp.textContent = 'Image';
        imgSlot.appendChild(sp);
      }
    }
    var albumList = Array.isArray(summary.blank_hub_news_album) ? summary.blank_hub_news_album : [];
    var carItems = albumList.filter(function (x) {
      return x && x.carousel && String(x.url || '').trim();
    });
    if (podiumRow) {
      var existingStrip = podiumRow.querySelector('[data-' + NS + '-album-strip]');
      if (!carItems.length) {
        if (existingStrip) existingStrip.remove();
      } else {
        var stripEl = existingStrip;
        if (!stripEl) {
          stripEl = document.createElement('div');
          stripEl.setAttribute('data-' + NS + '-album-strip', '');
          stripEl.className = 'bn-card__bn-album-strip';
          stripEl.setAttribute('aria-label', 'Album carousel');
          podiumRow.appendChild(stripEl);
        }
        stripEl.innerHTML = '';
        for (var ci = 0; ci < carItems.length; ci++) {
          var cu = String(carItems[ci].url || '').trim();
          if (!cu) continue;
          var tim = document.createElement('img');
          tim.className = 'bn-card__bn-album-thumb';
          tim.alt = '';
          tim.src = /^https?:\/\//i.test(cu) ? cu : b + (cu.indexOf('/') === 0 ? cu : '/' + cu);
          stripEl.appendChild(tim);
        }
      }
    }

    bnPaintHubLiveDayRaceBadges(root, summary, eventCandidate);

    renderFleetPillLines(root, classEntriesObj, fleetClasses);
    await loadPodiumForActiveFleet(root);
  }

  function setLoading(root, on) {
    var ld = root.querySelector('[data-' + NS + '-loading]');
    var sec = root.closest('[data-blank-bn-card]');
    if (ld) ld.hidden = !on;
    if (sec && on) sec.hidden = false;
  }

  /** Cap extra hub cards per slot (avoids dozens of parallel results-summary loads). */
  var MAX_HUB_NEWS_CARDS_PER_SLOT = 10;

  function bnWinnerRegattaId(summary, candidate) {
    var r = (summary && summary.regatta_id) || (candidate && candidate.regatta_id);
    return r != null ? String(r).trim() : '';
  }

  function resetBnCardRootClone(el) {
    if (!el) return;
    el.removeAttribute('data-' + NS + '-sa-edit-mode');
    try {
      exitBnSaInlineEdit(el);
    } catch (eEx) {
      /* ignore */
    }
    var wrap = el.querySelector('[data-' + NS + '-fleet-wrap]');
    if (wrap) {
      wrap.removeAttribute('data-' + NS + '-fleet-toggle');
      wrap.innerHTML = '';
    }
    var pod = el.querySelector('[data-' + NS + '-podium]');
    if (pod) {
      pod.innerHTML = '';
      pod.hidden = true;
    }
    try {
      delete el._bncardSummary;
      delete el._bncardClassEntries;
      delete el._bncardFleetClasses;
    } catch (eDel) {
      /* ignore */
    }
    var ld = el.querySelector('[data-' + NS + '-loading]');
    var emptyEl = el.querySelector('[data-' + NS + '-empty]');
    var bodyEl = el.querySelector('[data-' + NS + '-body]');
    if (ld) ld.hidden = false;
    if (emptyEl) emptyEl.hidden = true;
    if (bodyEl) bodyEl.hidden = true;
  }

  function syncBnSlotRootCount(stack, n) {
    var first = stack.querySelector('[data-' + NS + '-root]');
    if (!first) return;
    n = Math.max(1, Math.min(n, MAX_HUB_NEWS_CARDS_PER_SLOT));
    var roots;
    var i;
    roots = stack.querySelectorAll('[data-' + NS + '-root]');
    for (i = roots.length - 1; i >= n; i--) {
      var r = roots[i];
      if (r === first) continue;
      try {
        exitBnSaInlineEdit(r);
      } catch (eRm) {
        /* ignore */
      }
      if (r.parentNode) r.parentNode.removeChild(r);
      roots = stack.querySelectorAll('[data-' + NS + '-root]');
    }
    while (stack.querySelectorAll('[data-' + NS + '-root]').length < n) {
      var clone = first.cloneNode(true);
      resetBnCardRootClone(clone);
      stack.appendChild(clone);
    }
  }

  /**
   * All qualifying regattas for a hub slot (e.g. two DB “Top News” → two cards).
   * Top: every explicit “Top News” match, else legacy single auto (past Breaking/unset).
   */
  async function findAllSlotWinners(b, candidates, today, slot) {
    var matchFn =
      slot === 'top'
        ? matchesTopSlot
        : slot === 'news'
          ? matchesNewsSlot
          : slot === 'archive'
            ? matchesArchiveSlot
            : matchesBreakingSlot;
    var maxParallel = 10;

    if (slot === 'top') {
      var explicit = [];
      var seenE = Object.create(null);
      var ci;
      for (ci = 0; ci < candidates.length && explicit.length < MAX_HUB_NEWS_CARDS_PER_SLOT; ci += maxParallel) {
        var chunk = candidates.slice(ci, ci + maxParallel);
        var batch = await Promise.all(
          chunk.map(function (c) {
            return loadResultsSummary(b, c.regatta_id);
          })
        );
        var bi;
        for (bi = 0; bi < chunk.length && explicit.length < MAX_HUB_NEWS_CARDS_PER_SLOT; bi++) {
          var s = batch[bi];
          var cnd = chunk[bi];
          if (!s || normalizeHubNewsBadge(s) !== 'Top News') continue;
          if (!matchFn(s, cnd, today)) continue;
          var rid = bnWinnerRegattaId(s, cnd);
          if (!rid || seenE[rid]) continue;
          seenE[rid] = true;
          explicit.push({ summary: s, winningCandidate: cnd });
        }
      }
      if (explicit.length) return explicit;
      for (ci = 0; ci < candidates.length; ci += maxParallel) {
        chunk = candidates.slice(ci, ci + maxParallel);
        batch = await Promise.all(
          chunk.map(function (c) {
            return loadResultsSummary(b, c.regatta_id);
          })
        );
        for (bi = 0; bi < chunk.length; bi++) {
          s = batch[bi];
          cnd = chunk[bi];
          if (!s) continue;
          if (normalizeHubNewsBadge(s) === 'Top News') continue;
          if (!matchFn(s, cnd, today)) continue;
          rid = bnWinnerRegattaId(s, cnd);
          if (!rid) continue;
          return [{ summary: s, winningCandidate: cnd }];
        }
      }
      return [];
    }

    var out = [];
    var seen = Object.create(null);
    for (var cj = 0; cj < candidates.length && out.length < MAX_HUB_NEWS_CARDS_PER_SLOT; cj += maxParallel) {
      var chunk2 = candidates.slice(cj, cj + maxParallel);
      var batch2 = await Promise.all(
        chunk2.map(function (c) {
          return loadResultsSummary(b, c.regatta_id);
        })
      );
      var bj;
      for (bj = 0; bj < chunk2.length && out.length < MAX_HUB_NEWS_CARDS_PER_SLOT; bj++) {
        var s2 = batch2[bj];
        var c2 = chunk2[bj];
        if (!s2 || !matchFn(s2, c2, today)) continue;
        var rid2 = bnWinnerRegattaId(s2, c2);
        if (!rid2 || seen[rid2]) continue;
        seen[rid2] = true;
        out.push({ summary: s2, winningCandidate: c2 });
      }
    }
    return out;
  }

  async function renderOneBnWinner(b, root, found) {
    if (!root || !found || !found.summary) return;
    var summary = found.summary;
    var winningCandidate = found.winningCandidate;
    var rid = String(summary.regatta_id || '').trim();
    var classEntriesObj = classEntriesShapeFromFleetStats(summary);
    var fleetClasses = [];
    if (rid && Object.keys(classEntriesObj).length === 0) {
      var pair = await Promise.all([
        fetchJson(b + '/api/regatta/' + encodeURIComponent(rid) + '/class-entries'),
        fetchJson(b + '/api/regatta/' + encodeURIComponent(rid) + '/fleet-classes')
      ]);
      if (pair[0] && typeof pair[0] === 'object' && !Array.isArray(pair[0])) classEntriesObj = pair[0];
      if (Array.isArray(pair[1])) fleetClasses = pair[1];
    }
    classEntriesObj = mergeDuplicateFleetPillDisplayKeys(classEntriesObj);
    setVisibility(root, 'qualified');
    await render(root, summary, winningCandidate, classEntriesObj, fleetClasses);
  }

  async function refreshSlot(b, candidates, today, slot) {
    var section = document.querySelector('[data-blank-bn-card][data-bn-slot="' + slot + '"]');
    if (!section) return;
    var stack = section.querySelector('[data-bncard-stack]') || section;
    var rootsList = stack.querySelectorAll('[data-' + NS + '-root]');
    var ri;
    for (ri = 0; ri < rootsList.length; ri++) {
      setLoading(rootsList[ri], true);
    }
    try {
      if (!b) {
        syncBnSlotRootCount(stack, 1);
        var rHidden = stack.querySelector('[data-' + NS + '-root]');
        if (rHidden) setVisibility(rHidden, 'hidden');
        return;
      }

      var winners = await findAllSlotWinners(b, candidates, today, slot);
      var want = Math.max(1, winners.length);
      syncBnSlotRootCount(stack, want);
      var roots = stack.querySelectorAll('[data-' + NS + '-root]');

      if (!winners.length) {
        if (roots[0]) setVisibility(roots[0], 'notQualified');
        return;
      }

      await Promise.all(
        winners.map(function (w, idx) {
          return (async function () {
            try {
              await renderOneBnWinner(b, roots[idx], w);
            } catch (e) {
              try {
                console.error('[bncard] render failed', e);
              } catch (e2) {}
              if (roots[idx]) setVisibility(roots[idx], 'notQualified');
            }
          })();
        })
      );
    } catch (eSlot) {
      try {
        console.error('[bncard] refreshSlot failed', slot, eSlot);
      } catch (e3) {}
      var rootsErr = stack.querySelectorAll('[data-' + NS + '-root]');
      for (ri = 0; ri < rootsErr.length; ri++) {
        setVisibility(rootsErr[ri], 'notQualified');
      }
    } finally {
      var rootsEnd = stack.querySelectorAll('[data-' + NS + '-root]');
      for (ri = 0; ri < rootsEnd.length; ri++) {
        setLoading(rootsEnd[ri], false);
      }
    }
  }

  async function refreshAll() {
    var roots = document.querySelectorAll('[data-blank-bn-card] [data-' + NS + '-root]');
    var b = baseUrl();
    var ri;
    if (!b) {
      for (ri = 0; ri < roots.length; ri++) {
        setLoading(roots[ri], false);
        setVisibility(roots[ri], 'hidden');
      }
      return;
    }

    var evPayload = null;
    var bundleResolved = null;
    var bundleP = window.__blankHubPrimaryBundlePromise;
    if (bundleP) {
      try {
        bundleResolved = await bundleP;
        if (bundleResolved && bundleResolved.length > 3 && bundleResolved[3] != null) {
          evPayload = bundleResolved[3];
        }
      } catch (eBund) {
        evPayload = null;
      }
    }
    if (evPayload == null) {
      evPayload = await fetchJson(b + '/api/events?blank_hub=1&breaking_news=1');
    }
    var events = parseEventsPayload(evPayload);
    applyBnHubRegattaFallback(events);
    var today = todayYmdSast();
    /** Full hub calendar (bundle index 2) — used to pick ``Upcoming Event`` for featured std slot (not in breaking_news-only feed). */
    var eventsHubAll = events;
    if (bundleResolved && bundleResolved.length > 2 && bundleResolved[2] != null) {
      try {
        eventsHubAll = parseEventsPayload(bundleResolved[2]);
        applyBnHubRegattaFallback(eventsHubAll);
      } catch (eHubAll) {
        eventsHubAll = events;
      }
    }
    var candidates = buildCandidateList(events, today);
    var candidatesTop = prioritizeCandidatesByEventHubBadge(candidates, events, 'Top News');
    var candidatesNews = prioritizeCandidatesByEventHubBadge(candidates, events, 'News');
    var candidatesArchive = prioritizeCandidatesByEventHubBadge(candidates, events, 'Archive');
    var candidatesBreaking = prioritizeCandidatesByEventHubBadge(candidates, events, 'Breaking News');

    await Promise.all([
      refreshSlot(b, candidatesBreaking, today, 'breaking'),
      refreshSlot(b, candidatesTop, today, 'top'),
      refreshSlot(b, candidatesNews, today, 'news'),
      refreshSlot(b, candidatesArchive, today, 'archive')
    ]);

    try {
      var ueList = (eventsHubAll || []).filter(function (pe) {
        if (!pe) return false;
        if (normalizeHubNewsBadge({ blank_hub_news_badge_label: pe.blank_hub_news_badge_label }) !== 'Upcoming Event') {
          return false;
        }
        var ped = String(pe.end_date || pe.start_date || '').slice(0, 10);
        return !!(ped && ped >= today);
      });
      ueList.sort(function (a, xb) {
        return String(a.start_date || '').slice(0, 10).localeCompare(String(xb.start_date || '').slice(0, 10));
      });
      var prefUE = ueList.length ? ueList[0] : null;
      try {
        window.__blankHubUpcomingEventFeatured = prefUE;
      } catch (eW) {
        /* ignore */
      }
      try {
        document.dispatchEvent(
          new CustomEvent('sailingsa-std-slot-preference', {
            bubbles: true,
            detail: { event: prefUE, today: today }
          })
        );
      } catch (eD) {
        /* ignore */
      }
      if (typeof window.blankHubApplyStdSlotPreference === 'function') {
        try {
          window.blankHubApplyStdSlotPreference(prefUE, today);
        } catch (eAp) {
          /* ignore */
        }
      }
    } catch (ePref) {
      /* ignore */
    }

    try {
      applyBnSaTitleChrome();
    } catch (e) {}
  }

  try {
    window.bnCardRefreshAll = refreshAll;
  } catch (eW) {}

  try {
    window.addEventListener('storage', function (ev) {
      if (ev.key !== 'sailsa_hub_news_dirty' || ev.newValue == null) return;
      try {
        window.__blankHubPrimaryBundlePromise = null;
      } catch (eClr) { /* ignore */ }
      if (typeof window.bnCardRefreshAll === 'function') {
        window.bnCardRefreshAll();
      }
    });
  } catch (eSt) {}

  function init() {
    initFleetPillToggleOnce();
    document.querySelectorAll(".breaking-news-card").forEach(el => {
      el.innerHTML = "TEST OK";
    });
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', refreshAll);
    } else {
      refreshAll();
    }
  }

  init();
})();
