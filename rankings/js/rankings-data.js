/**
 * Rankings data provider — loads published audit JSON (no calculation).
 */
(function (global) {
  'use strict';

  var SSA_V2_PREVIEW_PARAM = 'ssa-v2';
  var SSA_V2_PREVIEW_DATA_URL = '/rankings/data/published.ssa-v2.preview.json';
  var SSA_V2_PREVIEW_NOTICE = 'SSA-v2 PREVIEW — NOT PUBLISHED';

  function wantMock() {
    var cfg = global.RankingsConfig || {};
    if (cfg.USE_MOCK_DATA) return true;
    try {
      var q = new URLSearchParams(global.location.search || '');
      return q.get('mock') === '1';
    } catch (e) {
      return false;
    }
  }

  function wantSsaV2Preview() {
    try {
      return new URLSearchParams(global.location.search || '').get('preview') === SSA_V2_PREVIEW_PARAM;
    } catch (e) {
      return false;
    }
  }

  function isValidPreviewPayload(payload) {
    return !!(
      payload &&
      typeof payload === 'object' &&
      !Array.isArray(payload) &&
      Array.isArray(payload.sailors) &&
      payload.sailors.length > 0 &&
      typeof payload.auditVersion === 'string' &&
      payload.auditVersion.trim()
    );
  }

  function applySsaV2PreviewChrome() {
    if (typeof document === 'undefined') return;
    var notice = document.getElementById('rkBetaNoticeText');
    if (notice) notice.textContent = SSA_V2_PREVIEW_NOTICE;
    var banner = document.getElementById('rkBetaBanner');
    if (banner) {
      banner.hidden = false;
      banner.removeAttribute('aria-hidden');
    }
    var robots = document.querySelector('meta[name="robots"]');
    if (robots) robots.setAttribute('content', 'noindex, nofollow');
  }

  function wrapPreviewUrlState() {
    if (!global.RankingsUrlState || global.RankingsUrlState.__ssaV2PreviewWrapped) return;
    var original = global.RankingsUrlState.writeState;
    if (typeof original !== 'function') return;
    global.RankingsUrlState.writeState = function (state, replace) {
      original.call(global.RankingsUrlState, state, replace);
      try {
        var params = new URLSearchParams(global.location.search || '');
        if (params.get('preview') === SSA_V2_PREVIEW_PARAM) return;
        params.set('preview', SSA_V2_PREVIEW_PARAM);
        var qs = params.toString();
        var url = (global.location.pathname || '/') + (qs ? '?' + qs : '') + (global.location.hash || '');
        if (replace) {
          global.history.replaceState(state, '', url);
        } else {
          global.history.pushState(state, '', url);
        }
      } catch (e) { /* ignore */ }
    };
    global.RankingsUrlState.__ssaV2PreviewWrapped = true;
  }

  function emptyBundle() {
    return {
      isMock: false,
      isPublished: false,
      auditVersion: null,
      formulaVersion: null,
      auditPopupEnabled: false,
      auditPopupAudit: null,
      exampleAliases: {},
      sailors: [],
      audits: [],
      classBoards: {},
      classOptions: [],
      classBoardForClass: function () { return []; },
      pointsBreakdownFor: function () { return []; }
    };
  }

  function mockBundle() {
    var m = global.RankingsMockData || {};
    return {
      isMock: true,
      isPublished: false,
      auditVersion: m.AUDIT_VERSION || null,
      formulaVersion: (global.RankingsConfig && global.RankingsConfig.FORMULA_VERSION) || null,
      auditPopupEnabled: false,
      auditPopupAudit: null,
      exampleAliases: {},
      sailors: (m.sailors || []).slice(),
      audits: (m.audits || []).slice(),
      classBoards: {},
      classOptions: [],
      classBoardForClass: function () { return []; },
      pointsBreakdownFor: typeof m.pointsBreakdownFor === 'function'
        ? m.pointsBreakdownFor
        : function () { return []; }
    };
  }

  function fromPublishedPayload(payload) {
    var year = payload.audit && payload.audit.calculatedAt
      ? String(payload.audit.calculatedAt).slice(0, 4)
      : '';
    var sailors = (payload.sailors || []).map(function (s) {
      return {
        rank: s.rank,
        points: s.points,
        name: s.name,
        slug: s.slug,
        sasId: s.sasId || '',
        club: s.club || '',
        clubCode: s.clubCode || '',
        className: s.className || '',
        classSlug: s.classSlug || '',
        sailNo: s.sailNo || '',
        previousRank: s.previousRank,
        rankChange: s.rankChange,
        ratedEvents: s.ratedEvents,
        ratedRaces: s.ratedRaces,
        year: s.year || year,
        overallRank: s.overallRank != null ? s.overallRank : s.rank,
        classRank: s.classRank != null ? s.classRank : null,
        classPoints: s.classPoints != null ? s.classPoints : null,
        overallPoints: s.overallPoints != null ? s.overallPoints : s.points,
        isAgedOut: !!s.isAgedOut,
        agedOutLabel: s.agedOutLabel || ''
      };
    });

    var audits = (payload.audits || []).map(function (a) {
      return {
        version: a.version,
        calculatedAt: a.calculatedAt,
        formulaVersion: a.formulaVersion,
        eventRatingVersion: a.eventRatingVersion,
        totalRankedSailors: a.totalRankedSailors,
        totalEventsIncluded: a.totalEventsIncluded,
        totalRacesIncluded: a.totalRacesIncluded,
        lastOfficialResultIncluded: a.lastOfficialResultIncluded,
        exclusions: a.exclusions || [],
        warnings: a.warnings || [],
        changelog: a.changelog || '',
        isPublished: !!a.isPublished
      };
    });

    var breakdowns = payload.breakdowns || {};
    var breakdownLists = {};
    Object.keys(breakdowns).forEach(function (slug) {
      breakdownLists[slug] = (breakdowns[slug] || []).map(function (r) {
        return {
          event: r.event,
          eventSlug: r.eventSlug,
          eventDate: r.eventDate || '',
          rating: r.rating,
          fleet: r.fleet,
          place: r.place,
          points: r.points,
          races: r.races,
          role: r.role,
          regattaId: r.regattaId,
          ageWeeks: r.ageWeeks,
          category: r.category,
          categoryName: r.categoryName || '',
          className: r.className || '',
          exampleSailorName: r.exampleSailorName || 'Example Sailor'
        };
      });
    });

    var classBoards = {};
    Object.keys(payload.classBoards || {}).forEach(function (classSlug) {
      var rows = payload.classBoards[classSlug] || [];
      classBoards[String(classSlug).toLowerCase()] = rows.map(function (s) {
        return {
          rank: s.rank,
          points: s.points,
          name: s.name,
          slug: s.slug,
          sasId: s.sasId || '',
          club: s.club || '',
          clubCode: s.clubCode || '',
          className: s.className || '',
          classSlug: s.classSlug || classSlug,
          sailNo: s.sailNo || '',
          previousRank: s.previousRank,
          rankChange: s.rankChange,
          ratedEvents: s.ratedEvents,
          ratedRaces: s.ratedRaces,
          year: s.year || year,
          sourceBoard: s.sourceBoard || '',
          overallRank: s.overallRank != null ? s.overallRank : null,
          classRank: s.classRank != null ? s.classRank : s.rank,
          classPoints: s.classPoints != null ? s.classPoints : s.points,
          overallPoints: s.overallPoints != null ? s.overallPoints : null,
          isAgedOut: !!s.isAgedOut,
          agedOutLabel: s.agedOutLabel || ''
        };
      });
    });

    var classOptions = (payload.classOptions || []).map(function (c) {
      return {
        className: c.className || '',
        classSlug: c.classSlug || '',
        sailorCount: c.sailorCount || 0,
        agedOutCount: c.agedOutCount || 0
      };
    });

    var exampleAliases = payload.exampleAliases || {};

    function classBoardForClass(classKey) {
      var key = String(classKey || '').trim().toLowerCase();
      if (!key) return [];
      if (classBoards[key]) return classBoards[key].slice();
      var match = classOptions.find(function (c) {
        return String(c.classSlug || '').toLowerCase() === key ||
          String(c.className || '').toLowerCase() === key;
      });
      if (!match) return [];
      return (classBoards[String(match.classSlug || '').toLowerCase()] || []).slice();
    }

    return {
      isMock: false,
      isPublished: !!payload.isPublished,
      auditVersion: payload.auditVersion || null,
      formulaVersion: payload.formulaVersion || null,
      auditPopupEnabled: false,
      auditPopupAudit: null,
      exampleAliases: exampleAliases,
      sailors: sailors,
      audits: audits,
      classBoards: classBoards,
      classOptions: classOptions,
      breakdowns: breakdownLists,
      classBoardForClass: classBoardForClass,
      pointsBreakdownFor: function (slug) {
        return (breakdownLists[slug] || []).slice();
      }
    };
  }

  function fetchJson(url) {
    return fetch(url, { credentials: 'same-origin', cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('data HTTP ' + res.status);
        return res.json();
      });
  }

  function loadPublished() {
    var cfg = global.RankingsConfig || {};
    var url = cfg.PUBLISHED_DATA_URL || '/rankings/data/published.json';
    return fetchJson(url).then(fromPublishedPayload);
  }

  function loadSsaV2Preview() {
    var url = SSA_V2_PREVIEW_DATA_URL + '?cb=' + Date.now();
    return fetchJson(url)
      .then(function (payload) {
        if (!isValidPreviewPayload(payload)) throw new Error('preview data invalid');
        var bundle = fromPublishedPayload(payload);
        bundle.isSsaV2Preview = true;
        applySsaV2PreviewChrome();
        wrapPreviewUrlState();
        return bundle;
      });
  }

  function loadRankingsBundle() {
    if (wantSsaV2Preview()) {
      return loadSsaV2Preview().catch(function () {
        return loadPublished();
      });
    }
    return loadPublished();
  }

  function loadAuditPopupCapability() {
    return fetch('/api/rankings/audit-popup-capability', { credentials: 'same-origin', cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('capability HTTP ' + res.status);
        return res.json();
      });
  }

  function load() {
    if (wantMock()) return Promise.resolve(mockBundle());
    return loadRankingsBundle()
      .then(function (bundle) {
        return loadAuditPopupCapability()
          .then(function (cap) {
            bundle.auditPopupEnabled = !!(cap && cap.enabled);
            bundle.auditPopupAudit = (cap && cap.audit) || null;
            return bundle;
          })
          .catch(function () {
            bundle.auditPopupEnabled = false;
            bundle.auditPopupAudit = null;
            return bundle;
          });
      })
      .catch(function () {
        return emptyBundle();
      });
  }

  global.RankingsData = {
    wantMock: wantMock,
    wantSsaV2Preview: wantSsaV2Preview,
    isValidPreviewPayload: isValidPreviewPayload,
    applySsaV2PreviewChrome: applySsaV2PreviewChrome,
    wrapPreviewUrlState: wrapPreviewUrlState,
    load: load,
    loadPublished: loadPublished,
    loadSsaV2Preview: loadSsaV2Preview,
    emptyBundle: emptyBundle,
    mockBundle: mockBundle,
    fromPublishedPayload: fromPublishedPayload,
    SSA_V2_PREVIEW_PARAM: SSA_V2_PREVIEW_PARAM,
    SSA_V2_PREVIEW_DATA_URL: SSA_V2_PREVIEW_DATA_URL,
    SSA_V2_PREVIEW_NOTICE: SSA_V2_PREVIEW_NOTICE
  };
})(typeof window !== 'undefined' ? window : this);
