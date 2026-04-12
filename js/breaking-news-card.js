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
 * ``?target=hero`` (main image only) or ``?target=album`` (append; does not clear hero). With **Edit** mode on, the event
 * meta form stays open; fleet pills choose podium scope. **Columns visible to public** (tick row) shows when Edit + a fleet
 * pill is active; prefs are stored in ``localStorage`` until a server field exists. Server invalidates results-summary cache after save/upload.
 * Hub featured std slot (``#blank-hub-std-event-slot`` / ``data-blank-hub-std-event``): fleet pills + Edit; save uses
 * PATCH /api/super-admin/calendar-event/{event_id} → ``events`` table; then ``blankHubRefetchStdSlotOnly`` + ``bnCardRefreshAll``.
 *
 * Four slots on blank.html — same card template (`bn-card`); only `data-bn-slot` + section pill differ.
 * Each slot may render multiple `[data-bncard-root]` copies inside `[data-bncard-stack]` when several regattas
 * share the same hub badge (e.g. two “Top News” in DB), up to `MAX_HUB_NEWS_CARDS_PER_SLOT`.
 * `breaking` | `top` | `news` | `archive` | `upcoming event` (featured std slot, not a news column) ← `blank_hub_news_badge_label`.
 * Legacy “Old News” never matches.
 *
 * **Global dedupe:** A regatta may appear only once across all five slots (and at most once per slot).
 * Slots refresh in page order; `findAllSlotWinners` skips `regatta_id`s already reserved by an earlier slot.
 */
(function () {
  'use strict';

  /**
   * Never assign window.API_BASE here — hub pages set origin for /auth/session and /api/*. A relative value
   * (e.g. '/admin') breaks checkSession + header sync after this script runs (defer).
   */
  window.BN_FORCE_SOURCE = '/admin/dashboard-data';

  var NS = 'bncard';

  function baseUrl() {
    var b = typeof window.API_BASE === 'string' ? window.API_BASE : '';
    if (b && /^https?:\/\//i.test(b)) {
      return b.replace(/\/$/, '');
    }
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

  /** Add calendar days to YYYY-MM-DD (noon local) for hub window math. */
  function bnYmdAddDays(ymd, deltaDays) {
    var s = ymdSlice(ymd);
    if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return '';
    var d = new Date(s + 'T12:00:00');
    if (isNaN(d.getTime())) return '';
    d.setDate(d.getDate() + (parseInt(deltaDays, 10) || 0));
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  /**
   * Anchor YMD for upcoming slot filter/sort. Uses **start** for future-only events; for **ongoing**
   * multi-day regattas (start ≤ today ≤ end) uses **today** so rows are not dropped when start is already past.
   */
  function bnAnchorYmdForUpcomingCandidate(e, today) {
    if (!e || typeof e !== 'object' || !today) return '';
    var s = ymdSlice(e.start_date);
    var eEnd = ymdSlice(e.end_date || e.start_date);
    if (!s && !eEnd) return '';
    if (!s) s = eEnd;
    if (!eEnd) eEnd = s;
    if (s <= today && today <= eEnd) return today;
    if (s > today) return s;
    return '';
  }

  /**
   * Hub upcoming-events column: calendar rows use anchor / 7-day / next-future heuristics.
   * Rows with DB ``Upcoming Event`` on ``blank_hub_news_badge_label`` bypass that (must show; sort rules later).
   * Card count is capped later by findAllSlotWinners (MAX_HUB_NEWS_CARDS_PER_SLOT).
   */
  function bnFilterUpcomingSlotVisibleCandidates(candidates, today) {
    if (!Array.isArray(candidates) || !today) return [];
    var explicitUe = [];
    var rest = [];
    var ix;
    for (ix = 0; ix < candidates.length; ix++) {
      var cx = candidates[ix];
      if (cx && normalizeHubNewsBadge({ blank_hub_news_badge_label: cx.blank_hub_news_badge_label }) === 'Upcoming Event') {
        explicitUe.push(cx);
      } else {
        rest.push(cx);
      }
    }
    var weekEnd = bnYmdAddDays(today, 7);
    var withDates = rest.filter(function (c) {
      return c && bnAnchorYmdForUpcomingCandidate(c, today);
    });
    var filteredRest = [];
    if (withDates.length) {
      var inSeven = withDates.filter(function (c) {
        var sd = bnAnchorYmdForUpcomingCandidate(c, today);
        return sd >= today && sd <= weekEnd;
      });
      inSeven.sort(function (a, b) {
        return bnAnchorYmdForUpcomingCandidate(a, today).localeCompare(bnAnchorYmdForUpcomingCandidate(b, today));
      });
      if (inSeven.length) {
        filteredRest = inSeven;
      } else {
        var future = withDates.filter(function (c) {
          return bnAnchorYmdForUpcomingCandidate(c, today) >= today;
        });
        future.sort(function (a, b) {
          return bnAnchorYmdForUpcomingCandidate(a, today).localeCompare(bnAnchorYmdForUpcomingCandidate(b, today));
        });
        filteredRest = future.length ? [future[0]] : [];
      }
    }
    var seenM = Object.create(null);
    var merged = [];
    var j;
    for (j = 0; j < explicitUe.length; j++) {
      var ex = explicitUe[j];
      var ridE = ex && ex.regatta_id != null ? String(ex.regatta_id).trim() : '';
      if (!ridE || seenM[ridE]) continue;
      seenM[ridE] = true;
      merged.push(ex);
    }
    for (j = 0; j < filteredRest.length; j++) {
      var fr = filteredRest[j];
      var ridF = fr && fr.regatta_id != null ? String(fr.regatta_id).trim() : '';
      if (!ridF || seenM[ridF]) continue;
      seenM[ridF] = true;
      merged.push(fr);
    }
    return merged;
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

  /**
   * Calendar row shape for hub: normalized dates + result counts for **sorting candidates only**.
   * Do **not** derive “Live vs Past” here — that is only `bnPaintHubLiveDayRaceBadges` (pills), not slot routing.
   */
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
      regatta_id: 'live-2026-overberg-sailing-champs-tsc',
      match: function (e) {
        var n = String(e.event_name || e.regatta_event_name || '').trim().toLowerCase();
        if (n.indexOf('overberg') !== -1 && n.indexOf('champ') !== -1) return true;
        return n === 'overberg sailing champs' || n.indexOf('overberg sailing champs') === 0;
      }
    },
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

  /** Calendar row matches a hub ``BN_HUB_REGATTA_FALLBACK`` (e.g. Overberg) — use when API has not set ``Upcoming Event`` badge yet. */
  function bnCalendarRowMatchesHubUpcomingFallback(e) {
    if (!e || typeof e !== 'object') return false;
    var i;
    for (i = 0; i < BN_HUB_REGATTA_FALLBACK.length; i++) {
      try {
        if (BN_HUB_REGATTA_FALLBACK[i].match(e)) return true;
      } catch (err) {
        /* ignore */
      }
    }
    return false;
  }

  /**
   * Flat candidate list for hub slots: **no** “live vs past” buckets (that is pill-only).
   * 1) One row per `regatta_id` (first wins from fetch order).
   * 2) Rows with DB hub card type first — `prioritizeCandidatesByEventHubBadge` then refines per slot.
   * 3) Others sorted by results signal + recency only (not whether the event is “live” today).
   */
  function buildCandidateList(events, today) {
    var norm = normalizeEvents(events, today);
    var byRid = Object.create(null);
    var order = [];
    var ni;
    for (ni = 0; ni < norm.length; ni++) {
      var ev = norm[ni];
      var rid = ev && ev.regatta_id != null ? String(ev.regatta_id).trim() : '';
      if (!rid) continue;
      if (!byRid[rid]) {
        byRid[rid] = ev;
        order.push(rid);
      }
    }
    var explicitRows = [];
    var restRows = [];
    var oi;
    for (oi = 0; oi < order.length; oi++) {
      var row = byRid[order[oi]];
      var bx = normalizeHubNewsBadge({ blank_hub_news_badge_label: row.blank_hub_news_badge_label });
      if (bx) explicitRows.push(row);
      else restRows.push(row);
    }
    restRows.sort(function (a, b) {
      return (
        (b.has_results || 0) - (a.has_results || 0) ||
        (b.entries || 0) - (a.entries || 0) ||
        (b.races_sailed || 0) - (a.races_sailed || 0) ||
        String(b.end_date || b.start_date || '').localeCompare(String(a.end_date || a.start_date || ''))
      );
    });
    return explicitRows.concat(restRows);
  }

  /**
   * `/api/events` can list the same `regatta_id` twice (multiple calendar rows). Keep first row
   * per id so each hub slot paints at most one card per regatta.
   */
  function dedupeCandidatesByRegattaId(candidates) {
    if (!Array.isArray(candidates) || !candidates.length) return candidates || [];
    var seen = Object.create(null);
    var out = [];
    var i;
    for (i = 0; i < candidates.length; i++) {
      var c = candidates[i];
      var rid = c && c.regatta_id != null ? String(c.regatta_id).trim() : '';
      if (!rid) continue;
      if (seen[rid]) continue;
      seen[rid] = true;
      out.push(c);
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
   * ``None``, ``--None--``, “not set”, etc. are **not** a card choice — same as unset (empty string).
   * Unknown strings are treated as unset so they never match a slot as a fake “custom” type.
   */
  function normalizeHubNewsBadge(summary) {
    var raw = String(summary && summary.blank_hub_news_badge_label != null ? summary.blank_hub_news_badge_label : '').trim();
    if (!raw) return '';
    var lower = raw.toLowerCase();
    if (
      lower === 'none' ||
      lower === 'null' ||
      lower === 'n/a' ||
      lower === 'na' ||
      /^[\s\-—–]*none[\s\-—–]*$/i.test(raw) ||
      /^[\s\-—–]*not\s*set\s*[\s\-—–]*$/i.test(raw)
    ) {
      return '';
    }
    if (/^top\s*news$/i.test(raw)) return 'Top News';
    if (/^breaking\s*news$/i.test(raw)) return 'Breaking News';
    if (/^news$/i.test(raw)) return 'News';
    if (/^archive$/i.test(raw)) return 'Archive';
    if (/^upcoming\s*events?$/i.test(raw)) return 'Upcoming Event';
    return '';
  }

  /** Legacy hub label — not used for Breaking/Top cards; SA should save “Top News” instead. */
  function isLegacyOldNewsBadgeLabel(b) {
    return /^\s*old\s*news\s*$/i.test(String(b || '').trim());
  }

  /**
   * True when today is within [start, end] — used for **auto** slot picks (e.g. untagged Breaking) and Top fallback.
   * **Not** used for the Live vs Past **pill**; that is `bnPaintHubLiveDayRaceBadges` only.
   */
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

  /**
   * Upcoming-events slot: ``Upcoming Event`` on results-summary, **or** a hub fallback calendar row
   * (``BN_HUB_REGATTA_FALLBACK``) when summary is still News/empty — so featured regattas show before SA sets badge.
   */
  function matchesUpcomingEventsSlot(summary, candidate, today) {
    var bs = normalizeHubNewsBadge(summary);
    if (bs === 'Upcoming Event') return true;
    if (bs === 'Top News' || bs === 'Archive') return false;
    if (bs === 'Breaking News') return false;
    if (candidate && bnCalendarRowMatchesHubUpcomingFallback(candidate)) return true;
    return false;
  }

  /**
   * Future Overberg (etc.) rows are not in buildCandidateList; results-summary may be null before entries exist.
   * Minimal summary so the upcoming-events slot can render News-style chrome + dates.
   */
  function buildSyntheticUpcomingSummaryFromCalendar(candidate) {
    var rid = String(candidate && candidate.regatta_id != null ? candidate.regatta_id : '').trim();
    if (!rid) return null;
    var calName = String(candidate.event_name != null ? candidate.event_name : '').trim();
    var regName = String(candidate.regatta_event_name != null ? candidate.regatta_event_name : '').trim();
    var name = regName || calName || 'Event';
    return {
      regatta_id: rid,
      blank_hub_news_badge_label: 'Upcoming Event',
      result_name: name,
      event_name: calName || regName || name,
      result_status: '',
      as_at_time: null,
      start_date: candidate.start_date,
      end_date: candidate.end_date,
      entries_total: 0,
      races_total: 0,
      fleet_stats: [],
      host_club_code: String(candidate.host_club_code || '').trim(),
      host_club_name: String(candidate.host_club_name || '').trim(),
      host_club_id: candidate.host_club_id != null ? candidate.host_club_id : null,
      category: candidate.category != null ? candidate.category : null,
      event_id: candidate.event_id != null ? candidate.event_id : null
    };
  }

  /**
   * Upcoming-events column: always show card type + sane defaults. Force **Upcoming Event** badge and
   * **None** results status when the summary has no entries/races/fleet_stats yet (API may still say Final).
   */
  function bnFinalizeUpcomingSlotSummary(summary) {
    if (!summary || typeof summary !== 'object') return summary;
    var out = Object.assign({}, summary);
    out.blank_hub_news_badge_label = 'Upcoming Event';
    var et = parseInt(out.entries_total, 10);
    var rt = parseInt(out.races_total, 10);
    var fs = out.fleet_stats;
    var hasFleet = Array.isArray(fs) && fs.length > 0;
    var hasBacked = (isFinite(et) && et > 0) || (isFinite(rt) && rt > 0) || hasFleet;
    if (!hasBacked) {
      out.result_status = 'None';
      if (out.as_at_time == null || String(out.as_at_time).trim() === '') {
        out.as_at_time = null;
      }
    }
    return out;
  }

  /** Calendar row (events table) may carry host/dates while results-summary is sparse — keep standard BN card lines + SA. */
  function mergeCalendarRowIntoUpcomingSummary(summary, candidate) {
    if (!summary || typeof summary !== 'object') return summary;
    if (!candidate || typeof candidate !== 'object') return summary;
    if (!String(summary.event_name || '').trim() && candidate.event_name) {
      summary.event_name = candidate.event_name;
    }
    if (!String(summary.result_name || '').trim()) {
      summary.result_name =
        candidate.regatta_event_name != null
          ? String(candidate.regatta_event_name).trim()
          : candidate.event_name != null
            ? String(candidate.event_name).trim()
            : summary.result_name;
    }
    if (summary.start_date == null && candidate.start_date != null) summary.start_date = candidate.start_date;
    if (summary.end_date == null && candidate.end_date != null) summary.end_date = candidate.end_date;
    if (!String(summary.host_club_code || '').trim() && candidate.host_club_code) {
      summary.host_club_code = String(candidate.host_club_code).trim();
    }
    if (!String(summary.host_club_name || '').trim() && candidate.host_club_name) {
      summary.host_club_name = String(candidate.host_club_name).trim();
    }
    if (summary.host_club_id == null && candidate.host_club_id != null) {
      summary.host_club_id = candidate.host_club_id;
    }
    if (summary.event_id == null && candidate.event_id != null) {
      summary.event_id = candidate.event_id;
    }
    return summary;
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

  /** Hub BN cards: host line shows **club code only** when present (same rule on every slot). */
  function formatBnCardHostCodeOnly(summary) {
    var c = String(summary && summary.host_club_code != null ? summary.host_club_code : '').trim();
    if (c) return 'Host: ' + c;
    var n = String(summary && summary.host_club_name != null ? summary.host_club_name : '').trim();
    if (n) return 'Host: ' + n;
    return '';
  }

  /** One line: event window + optional first-gun time from calendar/results-summary. */
  function formatBnEventScheduleLine(summary, eventCandidate) {
    var sd = ymdSlice(
      eventCandidate && eventCandidate.start_date != null
        ? eventCandidate.start_date
        : summary && summary.start_date != null
          ? summary.start_date
          : ''
    );
    var ed = ymdSlice(
      eventCandidate && eventCandidate.end_date != null
        ? eventCandidate.end_date
        : summary && summary.end_date != null
          ? summary.end_date
          : ''
    );
    if (!sd) return '';
    if (!ed) ed = sd;
    var monShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    function one(y) {
      var p = String(y || '')
        .trim()
        .slice(0, 10)
        .split('-');
      if (p.length < 3) return '';
      var d = parseInt(p[2], 10);
      var m = parseInt(p[1], 10) - 1;
      if (!isFinite(d) || m < 0 || m > 11) return '';
      return d + ' ' + monShort[m] + ' ' + p[0];
    }
    var a = one(sd);
    var b = one(ed);
    if (!a) return '';
    var range = a === b ? a : a + ' – ' + b;
    var st = String(
      (eventCandidate && eventCandidate.start_time) ||
        (summary && summary.start_time) ||
        ''
    ).trim();
    if (st) range = range + ' · First gun ' + st;
    return range;
  }

  /** Prefer calendar row times; summary (e.g. SA form merge) overrides stored event dates while editing. */
  function bnEventCandidateForSchedule(root, summary) {
    var ec =
      root._bncardEventCandidate && typeof root._bncardEventCandidate === 'object'
        ? Object.assign({}, root._bncardEventCandidate)
        : {};
    if (summary && typeof summary === 'object') {
      if (summary.start_date != null) ec.start_date = summary.start_date;
      if (summary.end_date != null) ec.end_date = summary.end_date;
      if (summary.start_time != null) ec.start_time = summary.start_time;
      if (summary.end_time != null) ec.end_time = summary.end_time;
    }
    return Object.keys(ec).length ? ec : null;
  }

  function formatBnScheduleLineOrPlaceholder(summary, eventCandidate) {
    var s = formatBnEventScheduleLine(summary, eventCandidate);
    if (s) return s;
    return '\u2014 \u00b7 \u2014';
  }

  function formatBnAsAtLineOrPlaceholder(asAtIso) {
    var s = formatBnAsAtLine(asAtIso);
    return s || '\u2014';
  }

  /** Insert schedule row between host/results line and as-at line (templates pre-date this row). */
  function ensureBnCardScheduleLine(root) {
    if (!root) return;
    var detail1 = root.querySelector('[data-' + NS + '-detail-line]');
    if (!detail1 || !detail1.parentNode) return;
    if (root.querySelector('[data-' + NS + '-schedule-line]')) return;
    var detail2 = root.querySelector('[data-' + NS + '-detail-line2]');
    var sch = document.createElement('p');
    sch.setAttribute('data-' + NS + '-schedule-line', '');
    sch.className = 'bn-card__detail-line bn-card__detail-line--schedule';
    sch.hidden = true;
    if (detail2) {
      detail1.parentNode.insertBefore(sch, detail2);
    } else {
      detail1.parentNode.appendChild(sch);
    }
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

  /** Hub SA: column ticks + preview table under fleet pills when Edit is on (localStorage until API stores prefs). */
  var BN_FLEET_COL_DEF = {
    rank: true,
    fleet: false,
    class: true,
    sail_no: true,
    boat_name: false,
    jib_no: false,
    bow_no: false,
    hull_no: false,
    club: true,
    helm: true,
    crew: true,
    race_scores: false,
    total: false,
    nett: false
  };

  /** No results / entry preview: Class, Sail No, Club, Helm, Crew — no rank or race columns (same SA UI as other cards). */
  var BN_FLEET_COL_DEF_ENTRY = {
    rank: false,
    fleet: false,
    class: true,
    sail_no: true,
    boat_name: false,
    jib_no: false,
    bow_no: false,
    hull_no: false,
    club: true,
    helm: true,
    crew: true,
    race_scores: false,
    total: false,
    nett: false
  };

  /** When Edit is on but there are no fleet pills yet (upcoming / zero entries), use this class key + entry column defaults. */
  var BN_FLEET_CLASS_KEY_ENTRY_PREVIEW = '__entry_preview__';

  var BN_FLEET_COL_ROWS = [
    ['rank', 'Rank'],
    ['fleet', 'Fleet'],
    ['class', 'Class'],
    ['sail_no', 'Sail No'],
    ['boat_name', 'Boat Name'],
    ['jib_no', 'Jib No'],
    ['bow_no', 'Bow No'],
    ['hull_no', 'Hull No'],
    ['club', 'Club'],
    ['helm', 'Helm'],
    ['crew', 'Crew'],
    ['race_scores', 'Race scores (R1…)'],
    ['total', 'Total'],
    ['nett', 'Nett']
  ];

  function bnFleetColLsKey(rid, classKey) {
    return 'sailsa_bncard_fleet_pub_cols_' + rid + '_' + classKey;
  }

  function bnLoadFleetColPrefs(rid, classKey) {
    var base =
      classKey === BN_FLEET_CLASS_KEY_ENTRY_PREVIEW ||
      (classKey && String(classKey).indexOf('hmanual:') === 0)
        ? BN_FLEET_COL_DEF_ENTRY
        : BN_FLEET_COL_DEF;
    var o = Object.assign({}, base);
    if (!rid || !classKey) return o;
    try {
      var raw = localStorage.getItem(bnFleetColLsKey(rid, classKey));
      if (raw) {
        var p = JSON.parse(raw);
        if (p && typeof p === 'object') {
          var k;
          for (k in o) {
            if (Object.prototype.hasOwnProperty.call(p, k)) o[k] = !!p[k];
          }
        }
      }
    } catch (e) {
      /* ignore */
    }
    return o;
  }

  /** Server + UI: SA “claim” entries for hub preview (not public.results). Persisted via ``blank_hub_sa_manual_entries`` on PATCH breaking-news-meta. */
  function bnNewManualEntryId() {
    return 'hm_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);
  }

  function bnNormalizeHubManualEntries(raw) {
    var out = { fleets: {} };
    if (!raw || typeof raw !== 'object') return out;
    if (raw.fleets && typeof raw.fleets === 'object') {
      try {
        out.fleets = JSON.parse(JSON.stringify(raw.fleets));
      } catch (e) {
        out.fleets = {};
      }
      return out;
    }
    return out;
  }

  function bnHubManualTotalRows(book) {
    var b = bnNormalizeHubManualEntries(book);
    var fk;
    var n = 0;
    for (fk in b.fleets) {
      if (!Object.prototype.hasOwnProperty.call(b.fleets, fk)) continue;
      var rows = b.fleets[fk] && Array.isArray(b.fleets[fk].rows) ? b.fleets[fk].rows : [];
      n += rows.length;
    }
    return n;
  }

  function bnMergeManualIntoClassEntries(classEntriesObj, manualBook) {
    var out = Object.assign({}, classEntriesObj || {});
    var manual = bnNormalizeHubManualEntries(manualBook);
    var fk;
    for (fk in manual.fleets) {
      if (!Object.prototype.hasOwnProperty.call(manual.fleets, fk)) continue;
      var pack = manual.fleets[fk];
      var rows = pack && Array.isArray(pack.rows) ? pack.rows : [];
      if (!rows.length) continue;
      var safeK = String(fk).replace(/[^a-z0-9]+/gi, '_');
      var key = '_hub_manual_' + safeK;
      out[key] = {
        name: String(fk).trim(),
        fleet_label: String(fk).trim(),
        entries: rows.length,
        hub_manual_fleet: true,
        hub_manual_key: String(fk).trim()
      };
    }
    return out;
  }

  function bnManualRowToApiShape(row) {
    if (!row || typeof row !== 'object') return {};
    return {
      class_name: row.class != null ? String(row.class) : '',
      sail_number: row.sail_no != null ? String(row.sail_no) : '',
      club_abbrev: row.club != null ? String(row.club) : '',
      helm_name: row.helm != null ? String(row.helm) : '',
      crew_name: row.crew != null ? String(row.crew) : '',
      hub_manual_row_id: row.id
    };
  }

  /** Parse “420 52997 ZVYC Jemayne Wolmarans Dillan Swarts” — splits remainder evenly between helm / crew. */
  function bnParseManualEntryLine(line) {
    var parts = String(line || '')
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (parts.length < 4) return null;
    var cls = parts[0];
    var sail = parts[1];
    var club = parts[2];
    var rest = parts.slice(3);
    var helm;
    var crew;
    if (rest.length === 0) return null;
    if (rest.length === 1) {
      helm = rest[0];
      crew = '';
    } else {
      var mid = Math.floor(rest.length / 2);
      helm = rest.slice(0, mid).join(' ');
      crew = rest.slice(mid).join(' ');
    }
    return { class: cls, sail_no: sail, club: club, helm: helm, crew: crew };
  }

  function bnFleetClassKeyFromManualFleetBtn(btn) {
    var v = btn && btn.getAttribute('data-hub-manual-fleet');
    return v && String(v).trim() !== '' ? String(v).trim() : '';
  }

  function bnFleetKeyFromClassKey(classKey) {
    if (!classKey || String(classKey).indexOf('hmanual:') !== 0) return '';
    try {
      return decodeURIComponent(String(classKey).replace(/^hmanual:/, ''));
    } catch (e) {
      return '';
    }
  }

  var bnHubClassNameCache = null;
  var bnHubClubListCache = null;
  var bnHubLookupTimers = Object.create(null);

  function bnHubManualRemoveTt(root) {
    if (!root) return;
    var nodes = root.querySelectorAll('[data-' + NS + '-manual-tt]');
    var i;
    for (i = 0; i < nodes.length; i++) {
      try {
        if (nodes[i].parentNode) nodes[i].parentNode.removeChild(nodes[i]);
      } catch (eR) {}
    }
  }

  function bnSailorHitName(m) {
    if (!m || typeof m !== 'object') return '';
    var n = [m.first_name || m.first_names, m.last_name || m.surname].filter(Boolean).join(' ').trim();
    if (n) return n;
    return String(m.full_name || m.sailor_name || '').trim();
  }

  function bnSailorHitSasLine(m) {
    if (!m || typeof m !== 'object') return '';
    var sid =
      m.sa_sailing_id != null
        ? String(m.sa_sailing_id)
        : m.sas_id != null
          ? String(m.sas_id)
          : m.sa_id != null
            ? String(m.sa_id)
            : '';
    return sid ? 'SAS ' + sid : '';
  }

  function bnIsSailorSearchHit(x) {
    if (!x || typeof x !== 'object') return false;
    if (x.type && String(x.type).toLowerCase() === 'sailor') return true;
    if (bnSailorHitName(x) && (x.sas_id != null || x.sa_sailing_id != null || x.sa_id != null)) return true;
    return !!(x.surname && x.first_names);
  }

  async function bnEnsureClassNameCache(b) {
    if (bnHubClassNameCache && bnHubClassNameCache.length) return bnHubClassNameCache;
    bnHubClassNameCache = [];
    var res = await fetch(b + '/api/classes/list', { credentials: 'include', cache: 'no-store' });
    if (!res.ok) return bnHubClassNameCache;
    var j = await res.json();
    var arr = j && Array.isArray(j.classes) ? j.classes : [];
    var ci;
    for (ci = 0; ci < arr.length; ci++) {
      var nm = String(arr[ci].class_name || '').trim();
      if (nm) bnHubClassNameCache.push(nm);
    }
    bnHubClassNameCache.sort(function (a, xb) {
      return a.localeCompare(xb);
    });
    return bnHubClassNameCache;
  }

  async function bnEnsureClubListCache(b) {
    if (bnHubClubListCache && bnHubClubListCache.length) return bnHubClubListCache;
    bnHubClubListCache = [];
    var res = await fetch(b + '/api/clubs', { credentials: 'include', cache: 'no-store' });
    if (!res.ok) return bnHubClubListCache;
    var j = await res.json();
    if (Array.isArray(j)) bnHubClubListCache = j;
    else if (j && Array.isArray(j.clubs)) bnHubClubListCache = j.clubs;
    return bnHubClubListCache;
  }

  function bnHubManualShowDropdown(anchorInp, items, onPick) {
    var root = anchorInp.closest('[data-' + NS + '-root]');
    if (!root) return;
    bnHubManualRemoveTt(root);
    if (!items || !items.length) return;
    var wrap = anchorInp.closest('.bn-card__fleet-manual-tt');
    if (!wrap) return;
    var ul = document.createElement('ul');
    ul.className = 'bn-card__hub-tt';
    ul.setAttribute('data-' + NS + '-manual-tt', '');
    ul.setAttribute('role', 'listbox');
    var ii;
    for (ii = 0; ii < items.length; ii++) {
      (function (item) {
        var li = document.createElement('li');
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'bn-card__hub-tt__btn';
        btn.innerHTML =
          '<span class="bn-card__hub-tt__line1">' +
          escapeHtml(item.line1) +
          '</span>' +
          (item.line2
            ? '<span class="bn-card__hub-tt__line2">' + escapeHtml(item.line2) + '</span>'
            : '');
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          onPick(item);
          bnHubManualRemoveTt(root);
        });
        li.appendChild(btn);
        ul.appendChild(li);
      })(items[ii]);
    }
    wrap.appendChild(ul);
  }

  function bnHubManualSortSavedRows(rows, sortKey) {
    var sk = String(sortKey || 'fleet').toLowerCase();
    var copy = rows.slice();
    copy.sort(function (a, b) {
      function val(row, k) {
        var rw = row.row;
        if (k === 'fleet') return String(row.fleet || '').toLowerCase();
        if (k === 'class') return String(rw.class || '').toLowerCase();
        if (k === 'sail_no') return String(rw.sail_no || '').toLowerCase();
        if (k === 'club') return String(rw.club || '').toLowerCase();
        if (k === 'helm') return String(rw.helm || '').toLowerCase();
        if (k === 'crew') return String(rw.crew || '').toLowerCase();
        return String(row.fleet || '').toLowerCase();
      }
      return val(a, sk).localeCompare(val(b, sk)) || String(a.fleet || '').localeCompare(String(b.fleet || ''));
    });
    return copy;
  }

  function bnHubManualCollectSavedRowObjs(book, showAll, onlyFleet) {
    var out = [];
    var fk;
    for (fk in book.fleets) {
      if (!Object.prototype.hasOwnProperty.call(book.fleets, fk)) continue;
      if (!showAll && onlyFleet && fk !== onlyFleet) continue;
      var rows = book.fleets[fk].rows || [];
      var ri;
      for (ri = 0; ri < rows.length; ri++) {
        out.push({ fleet: fk, row: rows[ri] });
      }
    }
    return out;
  }

  async function bnHubManualRunLookup(inp, root) {
    var kind = inp.getAttribute('data-' + NS + '-manual-lookup');
    if (!kind) return;
    var b = baseUrl();
    if (!b) return;
    var q = String(inp.value || '').trim();
    if (q.length < 1) {
      bnHubManualRemoveTt(root);
      return;
    }
    try {
      if (kind === 'class') {
        var names = await bnEnsureClassNameCache(b);
        var low = q.toLowerCase();
        var hits = names
          .filter(function (nm) {
            return String(nm).toLowerCase().indexOf(low) !== -1;
          })
          .slice(0, 22);
        bnHubManualShowDropdown(
          inp,
          hits.map(function (nm) {
            return { line1: nm, line2: '', value: nm };
          }),
          function (item) {
            inp.value = item.value;
          }
        );
        return;
      }
      if (kind === 'club') {
        var url =
          b +
          '/api/super-admin/clubs-search?q=' +
          encodeURIComponent(q) +
          '&limit=28';
        var res = await fetch(url, { credentials: 'include', cache: 'no-store' });
        var data = res.ok ? await res.json() : { clubs: [] };
        var arr = data && Array.isArray(data.clubs) ? data.clubs : [];
        if (!arr.length) {
          var fallback = await bnEnsureClubListCache(b);
          var t = q.toLowerCase();
          arr = fallback
            .filter(function (c) {
              var code = String(c.code || c.club_abbrev || '').toLowerCase();
              var name = String(c.name || c.club_fullname || '').toLowerCase();
              return code.indexOf(t) !== -1 || name.indexOf(t) !== -1;
            })
            .slice(0, 22)
            .map(function (c) {
              return {
                code: String(c.code || c.club_abbrev || '').trim(),
                name: String(c.name || c.club_fullname || '').trim(),
                club_id: c.club_id
              };
            });
        }
        bnHubManualShowDropdown(
          inp,
          arr.map(function (club) {
            var code = String(club.code || '').trim();
            var name = String(club.name || '').trim();
            return {
              line1: code || name || '—',
              line2: code && name && code !== name ? name : '',
              value: code || name
            };
          }),
          function (item) {
            inp.value = item.value;
          }
        );
        return;
      }
      if (kind === 'helm' || kind === 'crew') {
        var resS = await fetch(
          b + '/api/search?q=' + encodeURIComponent(q) + '&hub=1&limit=40',
          { credentials: 'include', cache: 'no-store' }
        );
        if (!resS.ok) return;
        var sr = await resS.json();
        var raw = Array.isArray(sr)
          ? sr
          : sr && Array.isArray(sr.sailors)
            ? sr.sailors
            : sr && Array.isArray(sr.results)
              ? sr.results
              : [];
        var sailors = raw.filter(bnIsSailorSearchHit);
        bnHubManualShowDropdown(
          inp,
          sailors.slice(0, 22).map(function (m) {
            var name = bnSailorHitName(m);
            var sub = bnSailorHitSasLine(m);
            return { line1: name || '—', line2: sub, value: name };
          }),
          function (item) {
            inp.value = item.value;
          }
        );
      }
    } catch (e) {
      try {
        bnHubManualRemoveTt(root);
      } catch (e2) {}
    }
  }

  function initBnHubManualLookupDelegatesOnce() {
    if (window.__bnHubManualLookupDelegatesBound) return;
    window.__bnHubManualLookupDelegatesBound = true;
    document.addEventListener(
      'input',
      function (ev) {
        var inp = ev.target;
        if (!inp || !inp.getAttribute || !inp.getAttribute('data-' + NS + '-manual-lookup')) return;
        var root = inp.closest('[data-' + NS + '-root]');
        if (!root) return;
        var key = inp.getAttribute('data-' + NS + '-manual-lookup');
        if (!key || key === 'sail_no') return;
        var id = String(inp.getAttribute('data-' + NS + '-manual-lookup-id') || '');
        if (!id) {
          id = 'lk_' + Math.random().toString(36).slice(2);
          inp.setAttribute('data-' + NS + '-manual-lookup-id', id);
        }
        if (bnHubLookupTimers[id]) clearTimeout(bnHubLookupTimers[id]);
        bnHubLookupTimers[id] = setTimeout(function () {
          bnHubLookupTimers[id] = null;
          bnHubManualRunLookup(inp, root);
        }, 200);
      },
      false
    );
    document.addEventListener(
      'focusin',
      function (ev) {
        var inp = ev.target;
        if (!inp || !inp.getAttribute || !inp.getAttribute('data-' + NS + '-manual-lookup')) return;
        var root = inp.closest('[data-' + NS + '-root]');
        if (!root) return;
        if (String(inp.value || '').trim().length >= 1) {
          bnHubManualRunLookup(inp, root);
        }
      },
      true
    );
    document.addEventListener(
      'change',
      function (ev) {
        var sel = ev.target;
        if (!sel || !sel.getAttribute || !sel.getAttribute('data-' + NS + '-manual-sort')) return;
        var root = sel.closest('[data-' + NS + '-root]');
        if (!root) return;
        root._bncardManualListSort = String(sel.value || 'fleet');
        try {
          updateBnFleetPublicColumnBar(root);
        } catch (eUp) {}
      },
      false
    );
    document.addEventListener(
      'click',
      function (ev) {
        var t = ev.target;
        if (t && t.closest && t.closest('[data-' + NS + '-manual-tt]')) return;
        if (t && t.closest && t.closest('.bn-card__fleet-manual-tt')) return;
        var roots = document.querySelectorAll('[data-' + NS + '-root]');
        var ri;
        for (ri = 0; ri < roots.length; ri++) {
          bnHubManualRemoveTt(roots[ri]);
        }
      },
      true
    );
  }

  function renderBnHubManualEntryFormAndListHtml(root, prefs, classKey) {
    var book = root._bncardHubManual || { fleets: {} };
    var keys = bnFleetEnabledKeysInOrder(prefs);
    var goldCells = '';
    var entryKeys = ['class', 'sail_no', 'club', 'helm', 'crew'];
    var gi;
    for (gi = 0; gi < entryKeys.length; gi++) {
      var ek = entryKeys[gi];
      if (keys.indexOf(ek) === -1) continue;
      var lk =
        ek === 'sail_no'
          ? ''
          : ' data-' +
            NS +
            '-manual-lookup="' +
            escapeHtml(ek).replace(/"/g, '&quot;') +
            '"';
      goldCells +=
        '<td class="bn-card__fleet-manual-gold__td bn-card__fleet-manual-gold__td--tt"><div class="bn-card__fleet-manual-tt">' +
        '<input type="text" class="bn-card__fleet-manual-gold__input" data-' +
        NS +
        '-manual-field="' +
        escapeHtml(ek).replace(/"/g, '&quot;') +
        '"' +
        lk +
        ' aria-label="' +
        escapeHtml(bnFleetColHeaderLabel(ek)) +
        '" autocomplete="off" spellcheck="false" /></div></td>';
    }
    var goldRow =
      '<div class="table-container bn-card__fleet-manual-gold-wrap"><table class="table bn-card__fleet-manual-gold-table"><thead><tr>';
    var hi;
    for (hi = 0; hi < entryKeys.length; hi++) {
      var hk = entryKeys[hi];
      if (keys.indexOf(hk) === -1) continue;
      goldRow += '<th>' + escapeHtml(bnFleetColHeaderLabel(hk)) + '</th>';
    }
    goldRow +=
      '<th class="bn-card__fleet-manual-gold__th-save" scope="col">Save</th></tr></thead><tbody><tr data-' +
      NS +
      '-manual-gold-row="">' +
      goldCells +
      '<td class="bn-card__fleet-manual-gold__td bn-card__fleet-manual-gold__td--save">' +
      '<button type="button" class="bn-card__fleet-manual-save" data-' +
      NS +
      '-manual-save>Save entry</button></td></tr></tbody></table></div>';
    var showAll = classKey === BN_FLEET_CLASS_KEY_ENTRY_PREVIEW;
    var onlyFleet = bnFleetKeyFromClassKey(classKey);
    var sortKey = root._bncardManualListSort || 'fleet';
    var rowObjs = bnHubManualCollectSavedRowObjs(book, showAll, onlyFleet);
    rowObjs = bnHubManualSortSavedRows(rowObjs, sortKey);
    var listParts = [
      '<div class="bn-card__fleet-manual-sort-row">' +
        '<label class="bn-card__fleet-manual-sort-label">Sort</label>' +
        '<select class="bn-card__fleet-manual-sort" data-' +
        NS +
        '-manual-sort aria-label="Sort saved entries">' +
        '<option value="fleet"' +
        (sortKey === 'fleet' ? ' selected' : '') +
        '>Fleet</option>' +
        '<option value="class"' +
        (sortKey === 'class' ? ' selected' : '') +
        '>Class</option>' +
        '<option value="sail_no"' +
        (sortKey === 'sail_no' ? ' selected' : '') +
        '>Sail No</option>' +
        '<option value="club"' +
        (sortKey === 'club' ? ' selected' : '') +
        '>Club</option>' +
        '<option value="helm"' +
        (sortKey === 'helm' ? ' selected' : '') +
        '>Helm</option>' +
        '<option value="crew"' +
        (sortKey === 'crew' ? ' selected' : '') +
        '>Crew</option>' +
        '</select></div>',
      '<ul class="bn-card__fleet-manual-saved">'
    ];
    var si;
    for (si = 0; si < rowObjs.length; si++) {
      var so = rowObjs[si];
      var fk = so.fleet;
      var rw = so.row;
      var lbl =
        [rw.class, rw.sail_no, rw.club, rw.helm, rw.crew].filter(function (x) {
          return x && String(x).trim();
        }).join(' · ') || 'Entry';
      listParts.push(
        '<li class="bn-card__fleet-manual-saved__item"><span class="bn-card__fleet-manual-saved__fleet">' +
          escapeHtml(fk) +
          '</span> — ' +
          escapeHtml(lbl) +
          ' <button type="button" class="bn-card__fleet-manual-del" data-' +
          NS +
          '-manual-delete data-' +
          NS +
          '-manual-fleet="' +
          escapeHtml(fk).replace(/"/g, '&quot;') +
          '" data-' +
          NS +
          '-manual-row-id="' +
          escapeHtml(String(rw.id || '')).replace(/"/g, '&quot;') +
          '">Delete</button></li>'
      );
    }
    listParts.push('</ul>');
    return (
      '<div class="bn-card__fleet-manual-block" data-' +
      NS +
      '-manual-block>' +
      '<p class="bn-card__fleet-manual-intro">Tick columns above · type to filter lists · first word of a line = class / fleet.</p>' +
      '<label class="bn-card__fleet-manual-quick-label">One line</label>' +
      '<textarea class="bn-card__fleet-manual-quick" rows="1" data-' +
      NS +
      '-manual-quick placeholder="420 52997 ZVYC …" spellcheck="false"></textarea>' +
      goldRow +
      listParts.join('') +
      '</div>'
    );
  }

  function bnCollectManualInputsFromGoldRow(root) {
    var inps = root.querySelectorAll('[data-' + NS + '-manual-field]');
    var o = {};
    var i;
    for (i = 0; i < inps.length; i++) {
      var inp = inps[i];
      var k = inp.getAttribute('data-' + NS + '-manual-field');
      if (k) o[k] = String(inp.value || '').trim();
    }
    if (o.class && o.sail_no && o.club) {
      return {
        class: o.class,
        sail_no: o.sail_no,
        club: o.club,
        helm: o.helm || '',
        crew: o.crew || ''
      };
    }
    return null;
  }

  function bnHubManualAppendParsed(root, parsed) {
    if (!parsed || !parsed.class) return false;
    if (!root._bncardHubManual) root._bncardHubManual = { fleets: {} };
    var fk = String(parsed.class).trim();
    if (!root._bncardHubManual.fleets[fk]) root._bncardHubManual.fleets[fk] = { rows: [] };
    parsed.id = bnNewManualEntryId();
    root._bncardHubManual.fleets[fk].rows.push(parsed);
    return true;
  }

  function bnHubManualDeleteRow(root, fleetKey, rowId) {
    var book = root._bncardHubManual;
    if (!book || !book.fleets || !book.fleets[fleetKey]) return;
    book.fleets[fleetKey].rows = (book.fleets[fleetKey].rows || []).filter(function (r) {
      return String(r.id) !== String(rowId);
    });
    if (!book.fleets[fleetKey].rows.length) delete book.fleets[fleetKey];
  }

  /**
   * Same field set as ``saveBnSaInlineEdit`` PATCH so manual-only saves are accepted server-side
   * (minimal JSON was rejected or ignored).
   * @returns {{ body: object }|{ error: string }}
   */
  function bnBuildFullBreakingNewsPatchBody(root) {
    var summary = root._bncardSummary;
    if (!summary) return { error: 'Missing card summary.' };
    var formEl = root.querySelector('[data-' + NS + '-sa-form]');
    var merged = summary;
    if (formEl && !formEl.hidden) {
      merged = bnMergedSummaryFromHubSaForm(summary, formEl) || summary;
    }

    var eventName = '';
    if (formEl && !formEl.hidden) {
      var nm = formEl.querySelector('[name="event_name"]');
      if (nm) eventName = String(nm.value || '').trim();
    }
    if (!eventName) {
      eventName =
        String(merged.event_name != null ? merged.event_name : '').trim() ||
        stripLeadingYearFromResultName(String(merged.result_name || summary.result_name || '').trim()) ||
        '';
    }
    if (!eventName) {
      return {
        error:
          'Event name is missing. Open Edit and save meta once, or reload the card so the name is available.'
      };
    }

    var asIso = null;
    if (formEl && !formEl.hidden) {
      var asDIn = formEl.querySelector('[name="results_as_at_date"]');
      var asTIn = formEl.querySelector('[name="results_as_at_time"]');
      var rawAs = bnLocalDateAndTimeToAsAtIso(
        asDIn ? asDIn.value : '',
        asTIn ? asTIn.value : ''
      );
      if (rawAs && rawAs !== '') {
        asIso = rawAs;
      }
    }
    if (asIso == null || asIso === '') {
      if (merged && merged.as_at_time != null && String(merged.as_at_time).trim()) {
        asIso = String(merged.as_at_time).trim();
      } else if (summary.as_at_time != null && String(summary.as_at_time).trim()) {
        asIso = String(summary.as_at_time).trim();
      } else {
        asIso = new Date().toISOString();
      }
    }

    var rsIn = formEl && !formEl.hidden ? formEl.querySelector('[name="result_status"]') : null;
    var rsVal = rsIn
      ? String(rsIn.value || '').trim()
      : String(merged.result_status != null ? merged.result_status : 'Final').trim() || 'Final';

    var sdIn = formEl && !formEl.hidden ? formEl.querySelector('[name="start_date"]') : null;
    var edIn = formEl && !formEl.hidden ? formEl.querySelector('[name="end_date"]') : null;
    var body = {
      event_name: eventName,
      result_status: rsVal,
      as_at_time: asIso,
      start_date: sdIn ? bnSaFormYmd(sdIn) : merged.start_date != null ? merged.start_date : summary.start_date || null,
      end_date: edIn ? bnSaFormYmd(edIn) : merged.end_date != null ? merged.end_date : summary.end_date || null
    };

    var hidIn = formEl && !formEl.hidden ? formEl.querySelector('[name="host_club_id"]') : null;
    var clubSearch = formEl && !formEl.hidden ? formEl.querySelector('.bn-card__sa-club-search') : null;
    var typedClub = clubSearch && String(clubSearch.value || '').trim();
    if (typedClub && clubSearch.getAttribute('data-bn-club-resolved') !== '1') {
      var hcx = merged.host_club_id != null ? merged.host_club_id : summary.host_club_id;
      if (hcx != null && String(hcx).trim() !== '') {
        var nx = parseInt(String(hcx), 10);
        body.host_club_id = isFinite(nx) ? nx : null;
      } else {
        body.host_club_id = null;
      }
    } else {
      var hidVal = hidIn ? String(hidIn.value || '').trim() : '';
      if (hidVal && /^\d+$/.test(hidVal)) {
        body.host_club_id = parseInt(hidVal, 10);
      } else if (!hidIn && (merged.host_club_id != null || summary.host_club_id != null)) {
        var hcs = merged.host_club_id != null ? merged.host_club_id : summary.host_club_id;
        var n2 = parseInt(String(hcs), 10);
        body.host_club_id = isFinite(n2) ? n2 : null;
      } else {
        body.host_club_id = null;
      }
    }

    var bs = formEl && !formEl.hidden ? formEl.querySelector('[name="blank_hub_news_badge_label"]') : null;
    if (bs) {
      var bsv = String(bs.value || '').trim();
      body.blank_hub_news_badge_label = bsv ? bsv : null;
    } else {
      var bFallback = merged.blank_hub_news_badge_label != null
        ? merged.blank_hub_news_badge_label
        : summary.blank_hub_news_badge_label;
      var bStr = String(bFallback != null ? bFallback : '').trim();
      body.blank_hub_news_badge_label = bStr ? bStr : null;
    }

    var iuIn = formEl && !formEl.hidden ? formEl.querySelector('[name="blank_hub_news_image_url"]') : null;
    if (iuIn) {
      body.blank_hub_news_image_url = String(iuIn.value || '').trim() || null;
    } else {
      var iuu = merged.blank_hub_news_image_url != null ? merged.blank_hub_news_image_url : summary.blank_hub_news_image_url;
      body.blank_hub_news_image_url = iuu != null && String(iuu).trim() ? String(iuu).trim() : null;
    }

    var hidAlbum = formEl && !formEl.hidden ? formEl.querySelector('[name="blank_hub_news_album_json"]') : null;
    if (hidAlbum) {
      try {
        var parsedA = JSON.parse(String(hidAlbum.value || '').trim() || '[]');
        body.blank_hub_news_album = Array.isArray(parsedA) ? parsedA : [];
      } catch (eAl) {
        body.blank_hub_news_album = [];
      }
    } else {
      var al = merged.blank_hub_news_album != null ? merged.blank_hub_news_album : summary.blank_hub_news_album;
      body.blank_hub_news_album = Array.isArray(al) ? al : [];
    }

    var shIn = formEl && !formEl.hidden ? formEl.querySelector('[name="blank_hub_news_show_hero"]') : null;
    if (shIn) {
      body.blank_hub_news_show_hero = !!shIn.checked;
    } else {
      var sh = merged.blank_hub_news_show_hero;
      if (sh === undefined) sh = summary.blank_hub_news_show_hero;
      body.blank_hub_news_show_hero = sh !== false;
    }

    var b = baseUrl();
    var crIn = formEl && !formEl.hidden ? formEl.querySelector('[name="card_results_url"]') : null;
    var ceIn = formEl && !formEl.hidden ? formEl.querySelector('[name="card_calendar_url"]') : null;
    var crv = '';
    if (crIn) {
      crv = String(crIn.value || '').trim();
    } else {
      crv = String(
        merged.card_results_url ||
          merged.results_page_url ||
          summary.card_results_url ||
          summary.results_page_url ||
          ''
      ).trim();
    }
    if (bnHubManualTotalRows(root._bncardHubManual) > 0 && !crv && b) {
      crv = bnCanonicalRegattaPageUrl(b, summary);
      if (crIn) crIn.value = crv;
    }
    body.card_results_url = crv || null;

    if (ceIn) {
      body.card_calendar_url = String(ceIn.value || '').trim() || null;
    } else {
      var cev = merged.card_calendar_url != null ? merged.card_calendar_url : summary.card_calendar_url;
      body.card_calendar_url = cev != null && String(cev).trim() ? String(cev).trim() : null;
      if (!body.card_calendar_url) {
        var calU = bnCalendarEventUrlFromSummary(merged);
        if (!calU) calU = bnCalendarEventUrlFromSummary(summary);
        body.card_calendar_url = calU && String(calU).trim() ? String(calU).trim() : null;
      }
    }

    body.blank_hub_sa_manual_entries =
      root._bncardHubManual && typeof root._bncardHubManual === 'object'
        ? root._bncardHubManual
        : { fleets: {} };

    return { body: body };
  }

  function bnFlashManualGoldInputs(root) {
    var inps = root.querySelectorAll('[data-' + NS + '-manual-field]');
    var i;
    for (i = 0; i < inps.length; i++) {
      if (!String(inps[i].value || '').trim()) continue;
      var el = inps[i];
      el.classList.remove('bn-card__fleet-manual-gold__input--flash');
      void el.offsetWidth;
      el.classList.add('bn-card__fleet-manual-gold__input--flash');
    }
  }

  async function saveBnHubManualPatch(root, msgEl) {
    var summary = root._bncardSummary;
    if (!summary || !bnSaCanEdit()) return false;
    var rid = String(summary.regatta_id || root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
    var b = baseUrl();
    if (!b || !rid) return false;
    var built = bnBuildFullBreakingNewsPatchBody(root);
    if (built.error) {
      if (msgEl) {
        msgEl.textContent = built.error;
        msgEl.hidden = false;
      }
      return false;
    }
    var body = built.body;
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
            typeof err === 'string'
              ? err
              : Array.isArray(err)
                ? err.map(function (x) {
                    return x.msg || x;
                  }).join(' ')
                : 'Save failed';
          msgEl.hidden = false;
        }
        return false;
      }
      if (j && j.blank_hub_sa_manual_entries) {
        root._bncardHubManual = bnNormalizeHubManualEntries(j.blank_hub_sa_manual_entries);
      }
      try {
        localStorage.setItem('sailsa_hub_manual_' + rid, JSON.stringify(root._bncardHubManual));
      } catch (eLs) {}
      try {
        localStorage.setItem('sailsa_hub_news_dirty', String(Date.now()));
      } catch (eD) {}
      return true;
    } catch (e) {
      if (msgEl) {
        msgEl.textContent = 'Save failed';
        msgEl.hidden = false;
      }
      return false;
    }
  }

  function bnTeardownPodiumStack(root) {
    var pod = root.querySelector('[data-' + NS + '-podium]');
    if (!pod || !pod.parentElement) return;
    var stack = pod.closest('.bn-card__podium-stack');
    if (!stack || !stack.parentElement) return;
    var row = stack.parentElement;
    row.insertBefore(pod, stack);
    stack.remove();
  }

  /** SA fleet panel: ticks + preview table — lives under fleet pills (not in image/podium row). */
  function ensureBnFleetSaPanel(root) {
    var heroCol = root.querySelector('.bn-card__split-right .bn-card__hero-col');
    if (!heroCol) return null;
    var panel = heroCol.querySelector('[data-' + NS + '-fleet-sa-panel]');
    if (!panel) {
      panel = document.createElement('div');
      panel.setAttribute('data-' + NS + '-fleet-sa-panel', '');
      panel.className = 'bn-card__fleet-sa-panel';
      panel.hidden = true;
      heroCol.appendChild(panel);
    }
    return panel;
  }

  function bnFleetEnabledKeysInOrder(prefs) {
    var out = [];
    var i;
    for (i = 0; i < BN_FLEET_COL_ROWS.length; i++) {
      var key = BN_FLEET_COL_ROWS[i][0];
      if (prefs[key]) out.push(key);
    }
    return out;
  }

  function bnFleetColHeaderLabel(key) {
    var i;
    for (i = 0; i < BN_FLEET_COL_ROWS.length; i++) {
      if (BN_FLEET_COL_ROWS[i][0] === key) return BN_FLEET_COL_ROWS[i][1];
    }
    return key;
  }

  function bnFleetPreviewCell(row, key) {
    if (!row || typeof row !== 'object') return '';
    var rs;
    var rk;
    switch (key) {
      case 'rank': {
        var pr = bnParseRankInt(row);
        return pr != null ? String(pr) : rowField(row, ['rank', 'Rank']);
      }
      case 'fleet':
        return rowField(row, ['fleet_label', 'block_fleet_label']);
      case 'class':
        return rowField(row, ['class_name', 'class_canonical', 'class_original']);
      case 'sail_no':
        return rowField(row, ['sail_number', 'Sail_number']);
      case 'boat_name':
        return rowField(row, ['boat_name', 'Boat_name']);
      case 'jib_no':
        return rowField(row, ['jib_no', 'Jib_no']);
      case 'bow_no':
        return rowField(row, ['bow_no', 'Bow_no']);
      case 'hull_no':
        return rowField(row, ['hull_no', 'Hull_no']);
      case 'club':
        return rowField(row, ['club_abbrev', 'club_code', 'club_raw']);
      case 'helm':
        return rowField(row, ['helm_name', 'Helm_name']);
      case 'crew':
        return rowField(row, ['crew_name', 'Crew_name']);
      case 'race_scores':
        rs = row.race_scores;
        if (!rs || typeof rs !== 'object') return '';
        rk = Object.keys(rs)
          .filter(function (k) {
            return /^R\d+$/i.test(k);
          })
          .sort(function (a, b) {
            return parseInt(a.replace(/\D/g, ''), 10) - parseInt(b.replace(/\D/g, ''), 10);
          });
        return rk
          .map(function (k) {
            return k + ':' + String(rs[k] != null ? rs[k] : '').trim();
          })
          .join(' ');
      case 'total':
        return rowField(row, ['total_points_raw', 'total_points', 'Total_points_raw']);
      case 'nett':
        return formatNett(row);
      default:
        return '';
    }
  }

  function bnFleetPreviewRowsSorted(rows) {
    if (!rows || !rows.length) return [];
    var top = rows.filter(function (r) {
      if (!r) return false;
      if (rowField(r, ['result_id', 'Result_id'])) return true;
      return bnParseRankInt(r) != null && rowField(r, ['helm_name', 'Helm_name']) !== '';
    });
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
    return top;
  }

  function bnActiveFleetPillLabel(active) {
    if (!active) return '—';
    var t = String(active.textContent || '').trim();
    return t || '—';
  }

  function renderBnFleetPreviewTableHtml(rows, prefs) {
    var keys = bnFleetEnabledKeysInOrder(prefs);
    if (!keys.length) {
      return (
        '<p class="bn-card__fleet-preview-hint">Tick at least one column for a preview table.</p>'
      );
    }
    var sorted = bnFleetPreviewRowsSorted(rows);
    var maxRows = 12;
    var slice = sorted.slice(0, maxRows);
    var parts = [];
    parts.push(
      '<div class="table-container bn-card__fleet-preview-scroll">' +
        '<table class="table bn-card__fleet-preview-table"><thead><tr>'
    );
    var hi;
    for (hi = 0; hi < keys.length; hi++) {
      parts.push('<th>' + escapeHtml(bnFleetColHeaderLabel(keys[hi])) + '</th>');
    }
    parts.push('</tr></thead><tbody>');
    var ri;
    for (ri = 0; ri < slice.length; ri++) {
      var row = slice[ri];
      parts.push('<tr>');
      var ki;
      for (ki = 0; ki < keys.length; ki++) {
        var cell = bnFleetPreviewCell(row, keys[ki]);
        parts.push('<td>' + escapeHtml(cell) + '</td>');
      }
      parts.push('</tr>');
    }
    if (!slice.length) {
      parts.push(
        '<tr><td colspan="' +
          keys.length +
          '" class="bn-card__fleet-preview-empty">No rows yet — entries and results appear when racing starts.</td></tr>'
      );
    }
    parts.push('</tbody></table></div>');
    return parts.join('');
  }

  function bnFleetClassKeyFromActive(active) {
    if (!active || active.getAttribute('data-' + NS + '-scope') === 'edit') return '';
    var mf = bnFleetClassKeyFromManualFleetBtn(active);
    if (mf) return 'hmanual:' + encodeURIComponent(mf);
    var m = active.getAttribute('data-class-ids');
    if (m && String(m).trim() !== '') return 'm:' + String(m).trim().replace(/\s+/g, '');
    var c = active.getAttribute('data-class-id');
    return c && String(c).trim() !== '' ? 'c:' + String(c).trim() : '';
  }

  function renderBnFleetColumnBarInner(prefs, classKey) {
    var parts = [];
    parts.push(
      '<strong class="bn-card__fleet-col-bar__title">Public columns</strong>' +
        '<div class="bn-card__fleet-col-bar__row" role="group" aria-label="Public columns">'
    );
    var i;
    for (i = 0; i < BN_FLEET_COL_ROWS.length; i++) {
      var key = BN_FLEET_COL_ROWS[i][0];
      var lbl = BN_FLEET_COL_ROWS[i][1];
      var ck = escapeHtml(key).replace(/"/g, '&quot;');
      var ckk = escapeHtml(classKey).replace(/"/g, '&quot;');
      parts.push(
        '<label class="bn-card__fleet-col-bar__item">' +
          '<input type="checkbox" data-' +
          NS +
          '-fleet-col="' +
          ck +
          '" data-' +
          NS +
          '-fleet-class-key="' +
          ckk +
          '"' +
          (prefs[key] ? ' checked' : '') +
          '> ' +
          escapeHtml(lbl) +
          '</label>'
      );
    }
    parts.push('</div>');
    return parts.join('');
  }

  function updateBnFleetPublicColumnBar(root) {
    if (!root) return;
    var wrap = root.querySelector('[data-' + NS + '-fleet-wrap]');
    var active = wrap && wrap.querySelector('.bn-card__fleet-pill.bn-card__fleet-pill--active');
    var editOn = root.getAttribute('data-' + NS + '-sa-edit-mode') === '1' && bnSaCanEdit();
    var classKey = bnFleetClassKeyFromActive(active);
    var sum0 = root._bncardSummary || {};
    var ce0 = root._bncardClassEntries || {};
    var noResults = !bnSummaryHasResultsBackedData(sum0, ce0);
    if (editOn && !classKey && noResults) {
      classKey = BN_FLEET_CLASS_KEY_ENTRY_PREVIEW;
    }
    var showPanel = !!(editOn && classKey);
    var panel = ensureBnFleetSaPanel(root);
    if (!panel) return;
    if (!showPanel) {
      panel.hidden = true;
      panel.innerHTML = '';
      return;
    }
    var rid = (root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
    var prefs = bnLoadFleetColPrefs(rid, classKey);
    var rows = root._bncardFleetResultRows;
    if (!Array.isArray(rows)) rows = [];
    var barHtml = renderBnFleetColumnBarInner(prefs, classKey);
    var tableHtml = renderBnFleetPreviewTableHtml(rows, prefs);
    var fleetLbl =
      classKey === BN_FLEET_CLASS_KEY_ENTRY_PREVIEW
        ? 'Entry preview (no fleet yet)'
        : bnActiveFleetPillLabel(active);
    var ctxHtml =
      '<div class="bn-card__fleet-sa-context" role="status">' +
      '<span class="bn-card__fleet-sa-context__label">Viewing</span> ' +
      '<strong class="bn-card__fleet-sa-context__fleet">' +
      escapeHtml(fleetLbl) +
      '</strong></div>';
    var dupHtml =
      '<div class="bn-card__fleet-sa-dup" aria-hidden="true">' +
      '<span class="bn-card__fleet-pill bn-card__fleet-pill--active bn-card__fleet-pill--dup" title="Selected fleet">' +
      escapeHtml(fleetLbl) +
      '</span></div>';
    var manualExtra = '';
    if (editOn) {
      manualExtra = renderBnHubManualEntryFormAndListHtml(root, prefs, classKey);
    }
    panel.hidden = false;
    panel.innerHTML =
      ctxHtml +
      '<div data-' +
      NS +
      '-fleet-column-bar="" class="bn-card__fleet-col-bar">' +
      barHtml +
      '</div>' +
      dupHtml +
      tableHtml +
      manualExtra;
  }

  function initBnHubManualFleetDelegateOnce() {
    if (window.__bnHubManualFleetBound) return;
    window.__bnHubManualFleetBound = true;
    document.addEventListener(
      'click',
      function (ev) {
        var t = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-manual-save]') : null;
        var d = ev.target && ev.target.closest ? ev.target.closest('[data-' + NS + '-manual-delete]') : null;
        if (!t && !d) return;
        var root =
          (t || d) && (t || d).closest ? (t || d).closest('[data-' + NS + '-root]') : null;
        if (!root) return;
        var msgEl = root.querySelector('[data-' + NS + '-sa-msg]');
        if (d) {
          ev.preventDefault();
          var fk = d.getAttribute('data-' + NS + '-manual-fleet');
          var rid = d.getAttribute('data-' + NS + '-manual-row-id');
          bnHubManualDeleteRow(root, fk, rid);
          saveBnHubManualPatch(root, msgEl).then(function (ok) {
            if (!ok) return;
            bnReconcileManualFleetsIntoPills(root);
            if (typeof window.bnCardRefreshAll === 'function') window.bnCardRefreshAll();
          });
          return;
        }
        if (t) {
          ev.preventDefault();
          var q = root.querySelector('[data-' + NS + '-manual-quick]');
          var parsed = null;
          if (q && String(q.value || '').trim()) {
            parsed = bnParseManualEntryLine(q.value);
          }
          if (!parsed) parsed = bnCollectManualInputsFromGoldRow(root);
          if (!parsed) {
            if (msgEl) {
              msgEl.textContent = 'Enter a full line or all gold-row fields (class, sail no, club, …).';
              msgEl.hidden = false;
            }
            return;
          }
          bnHubManualAppendParsed(root, parsed);
          if (q) q.value = '';
          saveBnHubManualPatch(root, msgEl).then(function (ok) {
            if (!ok) return;
            bnReconcileManualFleetsIntoPills(root);
            bnFlashManualGoldInputs(root);
            var gold = root.querySelectorAll('[data-' + NS + '-manual-field]');
            var gi;
            for (gi = 0; gi < gold.length; gi++) {
              gold[gi].value = '';
            }
            setTimeout(function () {
              if (typeof window.bnCardRefreshAll === 'function') window.bnCardRefreshAll();
            }, 700);
          });
        }
      },
      false
    );
  }

  function initBnFleetColumnBarDelegateOnce() {
    if (window.__bnFleetColBarDelegateBound) return;
    window.__bnFleetColBarDelegateBound = true;
    document.addEventListener(
      'change',
      function (ev) {
        var t = ev.target;
        if (!t || t.type !== 'checkbox') return;
        if (!t.getAttribute || !t.getAttribute('data-' + NS + '-fleet-col')) return;
        var root = t.closest('[data-' + NS + '-root]');
        if (!root) return;
        var rid = (root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
        var ck = t.getAttribute('data-' + NS + '-fleet-class-key');
        if (!rid || !ck) return;
        var bar = t.closest('[data-' + NS + '-fleet-column-bar]');
        if (!bar) return;
        var prefs = bnLoadFleetColPrefs(rid, ck);
        var inputs = bar.querySelectorAll('input[type="checkbox"][data-' + NS + '-fleet-col]');
        var ii;
        for (ii = 0; ii < inputs.length; ii++) {
          var inp = inputs[ii];
          var k = inp.getAttribute('data-' + NS + '-fleet-col');
          if (k && Object.prototype.hasOwnProperty.call(prefs, k)) prefs[k] = !!inp.checked;
        }
        try {
          localStorage.setItem(bnFleetColLsKey(rid, ck), JSON.stringify(prefs));
        } catch (eLs) {
          /* ignore */
        }
        try {
          updateBnFleetPublicColumnBar(root);
        } catch (eUp) {
          /* ignore */
        }
      },
      false
    );
  }

  async function loadPodiumForActiveFleet(root) {
    try {
      var podiumEl = root.querySelector('[data-' + NS + '-podium]');
      if (!podiumEl) return;
      try {
        root._bncardFleetResultRows = null;
      } catch (eClr) {
        /* ignore */
      }
      var rid = (root.getAttribute('data-' + NS + '-regatta-id') || '').trim();
      var wrap = root.querySelector('[data-' + NS + '-fleet-wrap]');
      var active = wrap && wrap.querySelector('.bn-card__fleet-pill.bn-card__fleet-pill--active');
      var b = baseUrl();
      var mfleet = active && bnFleetClassKeyFromManualFleetBtn(active);
      if (mfleet && root._bncardHubManual && root._bncardHubManual.fleets && root._bncardHubManual.fleets[mfleet]) {
        var mrows = root._bncardHubManual.fleets[mfleet].rows || [];
        root._bncardFleetResultRows = mrows.map(bnManualRowToApiShape);
        podiumEl.innerHTML = '';
        podiumEl.hidden = true;
        return;
      }
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
      try {
        root._bncardFleetResultRows = rows;
      } catch (eR) {
        /* ignore */
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
    } finally {
      try {
        if (root) updateBnFleetPublicColumnBar(root);
      } catch (eBar) {
        /* ignore */
      }
    }
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
      /** Only merge multiple rows into one pill for **Open** divisions — never merge duplicate labels like two Dabchick blocks (mixed podiums). */
      var firstLabel = arr[0] && arr[0].data ? fleetDisplayNameFromEntry(arr[0].data, arr[0].key) : '';
      var firstDisplay = bnBreakingNewsFleetPillDisplay(firstLabel);
      if (!bnIsOpenADivisionLabel(firstDisplay) && String(firstDisplay || '').trim().toLowerCase() !== 'open') {
        var si;
        for (si = 0; si < arr.length; si++) {
          out['split_' + mj + '_' + si + '_' + k.replace(/[^a-z0-9]+/g, '_')] = classEntriesObj[arr[si].key];
        }
        mj++;
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
        var hubManualFleet = !!(data && typeof data === 'object' && data.hub_manual_fleet);
        var hubManualKey =
          data && typeof data === 'object' && data.hub_manual_key != null
            ? String(data.hub_manual_key).trim()
            : '';
        return {
          label: label,
          displayLabel: displayLabel,
          boatClassName: boatNm,
          classIdFromApi: apiCid,
          classIdsFromApi: apiCids,
          entries: isFinite(ent) ? ent : 0,
          sort: displayLabel.toLowerCase(),
          hub_manual_fleet: hubManualFleet,
          hub_manual_key: hubManualKey
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

  /** Always show a stats line on BN cards (placeholders when no data yet). */
  function formatBnEntriesStatsLineOrPlaceholder(summary, classEntriesObj) {
    var s = formatBnEntriesStatsLine(summary, classEntriesObj);
    if (s) return s;
    return '\u2014 entries \u00b7 \u2014 fleets \u00b7 \u2014 races';
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
    if (badgeIn) {
      var bmv = String(badgeIn.value || '').trim();
      m.blank_hub_news_badge_label = bmv ? bmv : null;
    }
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
    ensureBnCardScheduleLine(root);
    var scheduleLineEl = root.querySelector('[data-' + NS + '-schedule-line]');
    var detailLineEl = root.querySelector('[data-' + NS + '-detail-line]');
    var detailLine2El = root.querySelector('[data-' + NS + '-detail-line2]');
    var resultsLinkEl = root.querySelector('[data-' + NS + '-results-link]');
    var b = baseUrl();
    var rid = String(summary.regatta_id || '').trim();
    var resultName = String(summary.result_name != null ? summary.result_name : '').trim();
    var title = stripLeadingYearFromResultName(resultName) || '—';
    var ecSched = bnEventCandidateForSchedule(root, summary);
    if (scheduleLineEl) {
      scheduleLineEl.textContent = formatBnScheduleLineOrPlaceholder(summary, ecSched);
      scheduleLineEl.hidden = false;
    }
    var hl = formatBnCardHostCodeOnly(summary);
    if (!hl) hl = 'Host: \u2014';
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
    var asAtLine = formatBnAsAtLineOrPlaceholder(summary.as_at_time);
    var line1Bits = [];
    line1Bits.push(hl);
    if (statusShort) line1Bits.push(statusShort);
    var detailLine1 = line1Bits.join(' \u00b7 ');
    if (detailLineEl) {
      detailLineEl.textContent = detailLine1;
      detailLineEl.hidden = false;
    }
    if (detailLine2El) {
      detailLine2El.textContent = asAtLine;
      detailLine2El.hidden = false;
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

  /** Full-width slot title bar — same label + colour family as the section pill (`bnPaintHubSectionBadgeFromLabel`). */
  function bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge) {
    if (!cardSection || !sectionBadge) return;
    var hdr = cardSection.querySelector('[data-' + NS + '-slot-header]');
    if (!hdr) return;
    hdr.textContent = sectionBadge.textContent;
    var h = 'bn-card__slot-header';
    if (sectionBadge.classList.contains('blank-hub-hero-badge--top-news')) {
      h += ' bn-card__slot-header--top-news';
    } else if (sectionBadge.classList.contains('blank-hub-hero-badge--hub-news')) {
      h += ' bn-card__slot-header--hub-news';
    } else if (sectionBadge.classList.contains('blank-hub-hero-badge--hub-archive')) {
      h += ' bn-card__slot-header--hub-archive';
    } else {
      h += ' bn-card__slot-header--breaking';
    }
    hdr.className = h;
  }

  /** Section pill (Breaking / Top / … / Upcoming) from `blank_hub_news_badge_label` — render + SA preview. */
  function bnPaintHubSectionBadgeFromLabel(root, mergedSummary) {
    var cardSection = root.closest('[data-blank-bn-card]') || root.closest('.blank-breaking-news-card');
    if (!cardSection || !mergedSummary) return;
    var sectionBadge = cardSection.querySelector('[data-' + NS + '-section-badge]');
    if (!sectionBadge) return;
    var lab = normalizeHubNewsBadge(mergedSummary);
    var slot = (cardSection.getAttribute('data-bn-slot') || '').trim();
    /** No DB card type: pill follows this column’s slot (auto picks), not a literal “Breaking News” everywhere. */
    if (!lab) {
      if (slot === 'top') {
        sectionBadge.textContent = 'Top News';
        sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--top-news';
        cardSection.setAttribute('aria-label', 'Top News');
        bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge);
        return;
      }
      if (slot === 'news') {
        sectionBadge.textContent = 'News';
        sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-news';
        cardSection.setAttribute('aria-label', 'News');
        bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge);
        return;
      }
      if (slot === 'archive') {
        sectionBadge.textContent = 'Archive';
        sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-archive';
        cardSection.setAttribute('aria-label', 'Archive');
        bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge);
        return;
      }
      if (slot === 'upcoming-events') {
        sectionBadge.textContent = 'Upcoming Events';
        sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-news';
        cardSection.setAttribute('aria-label', 'Upcoming Events');
        bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge);
        return;
      }
      sectionBadge.textContent = 'Breaking News';
      sectionBadge.className =
        'blank-hub-hero-badge blank-hub-hero-badge--live blank-hub-hero-badge--pulse';
      cardSection.setAttribute('aria-label', 'Breaking News');
      bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge);
      return;
    }
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
      if (slot === 'upcoming-events') {
        sectionBadge.textContent = 'Upcoming Events';
        sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-news';
        cardSection.setAttribute('aria-label', 'Upcoming Events');
      } else {
        sectionBadge.textContent = 'Upcoming Event';
        sectionBadge.className = 'blank-hub-hero-badge blank-hub-hero-badge--hub-news';
        cardSection.setAttribute('aria-label', 'Upcoming Event');
      }
    } else {
      sectionBadge.textContent = 'Breaking News';
      sectionBadge.className =
        'blank-hub-hero-badge blank-hub-hero-badge--live blank-hub-hero-badge--pulse';
      cardSection.setAttribute('aria-label', 'Breaking News');
    }
    bnSyncHubSlotHeaderFromSectionBadge(cardSection, sectionBadge);
  }

  /**
   * **Live / Past** (and Day N, R#): **chrome only** — the row of pills on the card.
   * Dates here do **not** decide whether a regatta appears in a hub column; that is DB hub badge + slot matchers
   * (`matches*Slot` / `findAllSlotWinners`). Only use this for what readers see next to Results.
   */
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
      } else if (it.hub_manual_fleet && it.hub_manual_key) {
        btn.setAttribute('data-hub-manual-fleet', String(it.hub_manual_key));
      } else if (cid) {
        btn.setAttribute('data-class-id', cid);
      }
      wrap.appendChild(btn);
    }
    if (saEdit) {
      var editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'bn-card__fleet-pill bn-card__fleet-pill--edit';
      editBtn.textContent = 'Edit';
      editBtn.setAttribute('data-' + NS + '-scope', 'edit');
      editBtn.setAttribute(
        'aria-label',
        'Toggle Super Admin edit mode: event fields stay in the card; tap a fleet pill to show that fleet’s podium beside the form'
      );
      editBtn.setAttribute(
        'title',
        'Edit mode on: event meta form stays open. Tap fleet pills to preview podium data without closing the form. Tap Edit again to turn off.'
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
      if (root._bncardSummary) {
        openBnSaInlineEdit(root, root._bncardSummary);
      }
      loadPodiumForActiveFleet(root);
    }
    var editBtn = root.querySelector('[data-' + NS + '-scope="edit"]');
    if (editBtn) editBtn.setAttribute('aria-pressed', wasOn ? 'false' : 'true');
    try {
      updateBnFleetPublicColumnBar(root);
    } catch (eCol) {
      /* ignore */
    }
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
        if (root && root.getAttribute('data-' + NS + '-sa-edit-mode') !== '1') {
          exitBnSaInlineEdit(root);
        }
        if (root) loadPodiumForActiveFleet(root);
      },
      false
    );
  }

  async function loadResultsSummary(b, rid) {
    var url = b + '/api/regatta/' + encodeURIComponent(String(rid).trim()) + '/results-summary';
    var j = await fetchJson(url);
    if (!j || typeof j !== 'object') return null;
    var hubB = normalizeHubNewsBadge(j);
    if (
      hubB === 'Top News' ||
      hubB === 'Breaking News' ||
      hubB === 'News' ||
      hubB === 'Archive' ||
      hubB === 'Upcoming Event'
    ) {
      return j;
    }
    var et = parseInt(j.entries_total, 10);
    var rt = parseInt(j.races_total, 10);
    var fs = j.fleet_stats;
    var fsOk = Array.isArray(fs) && fs.length > 0;
    if (
      (!isFinite(et) || et <= 0) &&
      (!isFinite(rt) || rt <= 0) &&
      !fsOk
    ) {
      return null;
    }
    return j;
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

  function bnStripHubManualKeysFromClassEntries(obj) {
    if (!obj || typeof obj !== 'object') return {};
    var out = Object.assign({}, obj);
    var k;
    for (k in out) {
      if (!Object.prototype.hasOwnProperty.call(out, k)) continue;
      if (String(k).indexOf('_hub_manual_') === 0) delete out[k];
    }
    return out;
  }

  /**
   * After manual entry save/delete: rebuild pills + preview table the same way as API fleet_stats fleets.
   * Requires ``buildFleetItems`` to pass ``hub_manual_*`` so pills get ``data-hub-manual-fleet`` for row load.
   */
  function bnReconcileManualFleetsIntoPills(root) {
    if (!root) return;
    try {
      var base = bnStripHubManualKeysFromClassEntries(root._bncardClassEntries || {});
      var merged = bnMergeManualIntoClassEntries(base, root._bncardHubManual || { fleets: {} });
      merged = mergeDuplicateFleetPillDisplayKeys(merged);
      root._bncardClassEntries = merged;
      renderFleetPillLines(root, merged, root._bncardFleetClasses || []);
      loadPodiumForActiveFleet(root);
    } catch (eRf) {
      try {
        console.error('[bncard] bnReconcileManualFleetsIntoPills', eRf);
      } catch (e2) {}
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
  /** SA event meta edit: Edit pill opens inline form; fleet pills choose podium scope (form stays open). */
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
    var curBadgeNorm = normalizeHubNewsBadge(summary);
    var curBadge = curBadgeNorm;
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
      '<option value="">— Not set —</option>';
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
      var statsLineEl = root.querySelector('[data-' + NS + '-stats-line]');
      if (statsLineEl) {
        statsLineEl.textContent = formatBnEntriesStatsLineOrPlaceholder(
          merged,
          root._bncardClassEntries || {}
        );
        statsLineEl.hidden = false;
      }
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
    if (root._bncardHubManual && bnHubManualTotalRows(root._bncardHubManual) > 0) {
      var crPre = formEl.querySelector('[name="card_results_url"]');
      if (crPre && !String(crPre.value || '').trim()) {
        crPre.value = bnCanonicalRegattaPageUrl(b, summary);
      }
    }
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
    if (bs) {
      var bsv2 = String(bs.value || '').trim();
      body.blank_hub_news_badge_label = bsv2 ? bsv2 : null;
    }
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
    if (root._bncardHubManual && typeof root._bncardHubManual === 'object') {
      body.blank_hub_sa_manual_entries = root._bncardHubManual;
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
    bnTeardownPodiumStack(root);
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
    var statsText = formatBnEntriesStatsLineOrPlaceholder(summary, classEntriesObj);
    if (statsLineEl) {
      statsLineEl.textContent = statsText;
      statsLineEl.hidden = false;
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
        im.onerror = function () {
          try {
            this.onerror = null;
          } catch (eOn) {}
          try {
            if (this.parentNode) this.parentNode.removeChild(this);
          } catch (eRm) {}
          var sp = document.createElement('span');
          sp.className = 'bn-card__image-slot-label';
          sp.textContent = 'Image';
          imgSlot.appendChild(sp);
        };
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

  /** Event end (else start) YYYY-MM-DD — for ordering multiple cards in one hub slot. */
  function bnHubWinnerRecencyYmd(w) {
    if (!w || typeof w !== 'object') return '';
    var s = w.summary;
    var c = w.winningCandidate;
    var y =
      ymdSlice(s && s.end_date) ||
      ymdSlice(c && c.end_date) ||
      ymdSlice(s && s.start_date) ||
      ymdSlice(c && c.start_date) ||
      '';
    return y;
  }

  /** When a slot shows more than one regatta, most recent (by end/start date) renders on top. */
  function sortHubWinnersMostRecentFirst(winners) {
    if (!Array.isArray(winners) || winners.length < 2) return winners;
    return winners.slice().sort(function (a, b) {
      return bnHubWinnerRecencyYmd(b).localeCompare(bnHubWinnerRecencyYmd(a));
    });
  }

  function resetBnCardRootClone(el) {
    if (!el) return;
    el.removeAttribute('data-' + NS + '-sa-edit-mode');
    try {
      exitBnSaInlineEdit(el);
    } catch (eEx) {
      /* ignore */
    }
    try {
      bnTeardownPodiumStack(el);
    } catch (eTd) {
      /* ignore */
    }
    var fsp = el.querySelector('[data-' + NS + '-fleet-sa-panel]');
    if (fsp) {
      fsp.hidden = true;
      fsp.innerHTML = '';
    }
    try {
      delete el._bncardFleetResultRows;
    } catch (eFr) {
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
      delete el._bncardHubManual;
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
   * @param {Object|null} globalReserved optional map regatta_id → true: already shown in an earlier hub column (no cross-slot dupes).
   */
  async function findAllSlotWinners(b, candidates, today, slot, globalReserved) {
    var gr = globalReserved && typeof globalReserved === 'object' ? globalReserved : null;
    function ridTakenGlobally(rid) {
      var r = rid != null ? String(rid).trim() : '';
      return !!(r && gr && gr[r]);
    }
    var matchFn =
      slot === 'upcoming-events'
        ? matchesUpcomingEventsSlot
        : slot === 'top'
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
          if (!rid || seenE[rid] || ridTakenGlobally(rid)) continue;
          seenE[rid] = true;
          explicit.push({ summary: s, winningCandidate: cnd });
        }
      }
      if (explicit.length) return sortHubWinnersMostRecentFirst(explicit);
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
          if (!rid || ridTakenGlobally(rid)) continue;
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
        if (
          slot === 'upcoming-events' &&
          (!s2 || typeof s2 !== 'object') &&
          c2 &&
          String(c2.regatta_id || '').trim()
        ) {
          s2 = buildSyntheticUpcomingSummaryFromCalendar(c2);
        }
        if (slot === 'upcoming-events' && s2 && c2) {
          s2 = mergeCalendarRowIntoUpcomingSummary(s2, c2);
          s2 = bnFinalizeUpcomingSlotSummary(s2);
        }
        if (!s2 || !matchFn(s2, c2, today)) continue;
        var rid2 = bnWinnerRegattaId(s2, c2);
        if (!rid2 || seen[rid2] || ridTakenGlobally(rid2)) continue;
        seen[rid2] = true;
        out.push({ summary: s2, winningCandidate: c2 });
      }
    }
    return sortHubWinnersMostRecentFirst(out);
  }

  async function renderOneBnWinner(b, root, found) {
    if (!root || !found || !found.summary) return;
    var summary = found.summary;
    var winningCandidate = found.winningCandidate;
    var rid = String(summary.regatta_id || '').trim();
    var manualBook = bnNormalizeHubManualEntries(summary.blank_hub_sa_manual_entries);
    try {
      if (!manualBook.fleets || !Object.keys(manualBook.fleets).length) {
        try {
          var lsRaw = localStorage.getItem('sailsa_hub_manual_' + rid);
          if (lsRaw) manualBook = bnNormalizeHubManualEntries(JSON.parse(lsRaw));
        } catch (eLs) {}
      }
    } catch (eO) {}
    try {
      root._bncardHubManual = manualBook;
    } catch (eR) {}
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
    classEntriesObj = bnMergeManualIntoClassEntries(classEntriesObj, manualBook);
    classEntriesObj = mergeDuplicateFleetPillDisplayKeys(classEntriesObj);
    var mt = bnHubManualTotalRows(manualBook);
    if (mt > 0) {
      summary = Object.assign({}, summary);
      var et0 = parseInt(summary.entries_total, 10);
      summary.entries_total = (isFinite(et0) ? et0 : 0) + mt;
    }
    setVisibility(root, 'qualified');
    await render(root, summary, winningCandidate, classEntriesObj, fleetClasses);
  }

  async function refreshSlot(b, candidates, today, slot, globalReserved) {
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

      var winners = await findAllSlotWinners(b, candidates, today, slot, globalReserved);
      var wx;
      for (wx = 0; wx < winners.length; wx++) {
        var wrid = bnWinnerRegattaId(winners[wx].summary, winners[wx].winningCandidate);
        if (wrid && globalReserved) globalReserved[wrid] = true;
      }
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
    /** Full hub calendar (bundle index 2) — Overberg etc. may be absent from ``breaking_news=1`` only. */
    var eventsHubAll = events;
    if (bundleResolved && bundleResolved.length > 2 && bundleResolved[2] != null) {
      try {
        eventsHubAll = parseEventsPayload(bundleResolved[2]);
        applyBnHubRegattaFallback(eventsHubAll);
      } catch (eHubAll) {
        eventsHubAll = events;
      }
    } else {
      try {
        var hubOnlyPayload = await fetchJson(b + '/api/events?blank_hub=1');
        var hubParsed = parseEventsPayload(hubOnlyPayload);
        if (hubParsed.length) {
          eventsHubAll = hubParsed;
          applyBnHubRegattaFallback(eventsHubAll);
        }
      } catch (eHubFetch) {
        /* keep breaking_news-only list */
      }
    }
    var candidates = dedupeCandidatesByRegattaId(buildCandidateList(events, today));
    var candidatesTop = prioritizeCandidatesByEventHubBadge(candidates, events, 'Top News');
    var candidatesNews = prioritizeCandidatesByEventHubBadge(candidates, events, 'News');
    var candidatesArchive = prioritizeCandidatesByEventHubBadge(candidates, events, 'Archive');
    var candidatesBreaking = prioritizeCandidatesByEventHubBadge(candidates, events, 'Breaking News');
    var normUeAll = normalizeEvents(eventsHubAll, today);
    var upcomingFromCalendar = normUeAll.filter(function (e) {
      if (!e || e.regatta_id == null || String(e.regatta_id).trim() === '') return false;
      var eb = normalizeHubNewsBadge({ blank_hub_news_badge_label: e.blank_hub_news_badge_label });
      if (eb === 'Upcoming Event') return true;
      var ped = String(e.end_date || e.start_date || '').slice(0, 10);
      if (!ped || ped < today) return false;
      return bnCalendarRowMatchesHubUpcomingFallback(e);
    });
    var candidatesUpcomingEvents = prioritizeCandidatesByEventHubBadge(
      upcomingFromCalendar,
      eventsHubAll,
      'Upcoming Event'
    );
    if (!candidatesUpcomingEvents.length) {
      candidatesUpcomingEvents = prioritizeCandidatesByEventHubBadge(candidates, events, 'Upcoming Event');
    }
    candidatesUpcomingEvents = bnFilterUpcomingSlotVisibleCandidates(candidatesUpcomingEvents, today);

    /** One regatta_id / upcoming row per hub page — earlier columns win (Breaking → Top → News → Archive → Upcoming). */
    var hubUsedRegattaIds = Object.create(null);
    await refreshSlot(b, candidatesBreaking, today, 'breaking', hubUsedRegattaIds);
    await refreshSlot(b, candidatesTop, today, 'top', hubUsedRegattaIds);
    await refreshSlot(b, candidatesNews, today, 'news', hubUsedRegattaIds);
    await refreshSlot(b, candidatesArchive, today, 'archive', hubUsedRegattaIds);
    var reservedBeforeUpcoming = Object.assign(Object.create(null), hubUsedRegattaIds);
    await refreshSlot(b, candidatesUpcomingEvents, today, 'upcoming-events', hubUsedRegattaIds);

    try {
      /* Featured std slot: first upcoming candidate not already shown in a column above. */
      var ueList = candidatesUpcomingEvents.slice();
      var prefUE = null;
      var uei;
      for (uei = 0; uei < ueList.length; uei++) {
        var ueRow = ueList[uei];
        var ueRid = ueRow && ueRow.regatta_id != null ? String(ueRow.regatta_id).trim() : '';
        if (ueRid && !reservedBeforeUpcoming[ueRid]) {
          prefUE = ueRow;
          break;
        }
      }
      if (!prefUE && ueList.length) prefUE = ueList[0];
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
    initBnFleetColumnBarDelegateOnce();
    initBnHubManualFleetDelegateOnce();
    initBnHubManualLookupDelegatesOnce();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', refreshAll);
    } else {
      refreshAll();
    }
  }

  init();
})();
