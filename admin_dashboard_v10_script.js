(function () {
  window.API_BASE = (window.location && window.location.origin) ? window.location.origin.replace(/\/$/, '') : '';

  var REFRESH_MS = 12000;

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function pathToHref(path) {
    var p = (path == null ? '' : String(path)).trim();
    if (!p || p === '—') return '';
    if (/^https?:\/\//i.test(p)) return p;
    if (p.charAt(0) === '/') return window.API_BASE + p;
    return window.API_BASE + '/' + p.replace(/^\//, '');
  }

  /** Optional map normalized path → full label when data is already loaded elsewhere (no extra fetches). */
  var pathLabelOverrides = {};

  var PATH_LABEL_MAX = 30;

  function safeDecodeURIComponent(s) {
    try {
      return decodeURIComponent(s);
    } catch (e) {
      return s;
    }
  }

  function slugToReadableName(slug) {
    if (slug == null || slug === '') return '';
    return String(slug)
      .split(/[-_]+/g)
      .filter(Boolean)
      .map(function (w) {
        if (/^\d+$/.test(w)) return w;
        return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
      })
      .join(' ');
  }

  function truncateLabel(s, maxLen) {
    var m = maxLen != null ? maxLen : PATH_LABEL_MAX;
    var t = String(s == null ? '' : s).trim();
    if (t.length <= m) return t;
    if (m <= 1) return '…';
    return t.slice(0, m - 1) + '…';
  }

  /**
   * Readable short label for dashboard paths. Uses pathLabelOverrides[normalizedPath] when set.
   * No network calls; unknown routes get a shortened path fallback.
   */
  function pathToLabel(path) {
    var raw = path == null ? '' : String(path).trim();
    if (!raw || raw === '—') return '—';
    var noQ = raw.split('?')[0].split('#')[0];
    var p = noQ;
    if (!p.startsWith('/')) p = '/' + p.replace(/^\/+/, '');
    p = p.replace(/\/+$/, '') || '/';

    var ov = pathLabelOverrides[p] || pathLabelOverrides[raw];
    if (ov) return truncateLabel(String(ov));

    if (p === '/sailors') return truncateLabel('Sailors (list)');
    if (p === '/regattas') return truncateLabel('Regattas (list)');
    if (p === '/classes') return truncateLabel('Classes (list)');
    if (p === '/stats') return truncateLabel('Stats');
    if (p === '/' || p === '') return truncateLabel('Home');

    var m;
    m = /^\/sailor\/([^/?#]+)/i.exec(p);
    if (m) {
      var sn = safeDecodeURIComponent(m[1]);
      var sname = slugToReadableName(sn);
      return truncateLabel('Sailor: ' + (sname || sn));
    }
    m = /^\/regatta\/([^/?#]+)/i.exec(p);
    if (m) {
      return truncateLabel('Regatta');
    }
    m = /^\/club\/([^/?#]+)/i.exec(p);
    if (m) {
      var cs = safeDecodeURIComponent(m[1]);
      return truncateLabel('Club: ' + (slugToReadableName(cs) || cs));
    }
    m = /^\/class\/([^/?#]+)/i.exec(p);
    if (m) {
      var cls = safeDecodeURIComponent(m[1]);
      var clsTail = cls.replace(/^\d+-/, '');
      var cnm = slugToReadableName(clsTail || cls);
      return truncateLabel('Class: ' + (cnm || cls));
    }

    var fb = p.length > 28 ? p.slice(0, 27) + '…' : p;
    return truncateLabel(fb);
  }

  function pathCellHtml(path) {
    var raw = path == null ? '' : String(path);
    var href = pathToHref(raw);
    var esc = escapeHtml(raw);
    if (!href) return esc;
    return '<a href="' + escapeHtml(href) + '">' + esc + '</a>';
  }

  /** Same as pathCellHtml but shows pathToLabel text; title = raw path for hover. */
  function pathLabelHtml(path) {
    var raw = path == null ? '' : String(path);
    var href = pathToHref(raw);
    var lab = escapeHtml(pathToLabel(raw));
    var title = escapeHtml(raw);
    if (!href) return lab;
    return '<a href="' + escapeHtml(href) + '" title="' + title + '">' + lab + '</a>';
  }

  function sortCountDesc(rows) {
    return (rows || []).slice().sort(function (a, b) {
      return Number(b.count || 0) - Number(a.count || 0);
    });
  }

  /** Same as index.html: #menuBtn + #navMenuOverlay (display flex/none). */
  var adminV10SecondHeaderLogoutWired = false;

  function wireAdminV10SecondHeaderLogout() {
    if (adminV10SecondHeaderLogoutWired) return;
    var b = document.getElementById('adminV10SecondHeaderLogoutBtn');
    if (!b) return;
    adminV10SecondHeaderLogoutWired = true;
    b.addEventListener('click', async function (e) {
      e.preventDefault();
      if (typeof handleLogout === 'function') {
        await handleLogout();
      }
    });
  }

  /** 2nd header: name + SAS | avatar | Logout (one row); same session + handleLogout as main header */
  async function syncAdminV10SecondHeader() {
    var wrap = document.getElementById('adminV10SecondHeaderUser');
    var nm = document.getElementById('adminV10SecondHeaderName');
    var sasEl = document.getElementById('adminV10SecondHeaderSas');
    var av = document.getElementById('adminV10SecondHeaderAvatar');
    if (!wrap || !nm || !sasEl || !av) return;
    wireAdminV10SecondHeaderLogout();
    try {
      var pathQs = '';
      try {
        if (window.location && window.location.pathname) {
          pathQs = '?path=' + encodeURIComponent(window.location.pathname || '/');
        }
      } catch (e0) { /* ignore */ }
      var r = await fetch(window.API_BASE + '/auth/session' + pathQs, { credentials: 'include', cache: 'no-store' });
      var s = await r.json();
      if (!s || !s.valid || !s.user) {
        wrap.setAttribute('hidden', '');
        av.removeAttribute('src');
        av.style.display = 'none';
        nm.textContent = '';
        sasEl.textContent = '';
        return;
      }
      var u = s.user || {};
      var full = (u.full_name || [u.first_name, u.last_name].filter(Boolean).join(' ') || 'Member').trim();
      nm.textContent = full;
      sasEl.textContent = s.sas_id != null ? 'SAS ID: ' + String(s.sas_id) : 'SAS ID: —';
      if (s.sas_id != null && typeof applySailingAvatarToImg === 'function') {
        applySailingAvatarToImg(av, s.sas_id, full, {
          apiBase: (window.API_BASE || '').replace(/\/$/, ''),
          headerMode: true,
          includeMediaCache: false
        });
      } else if (s.sas_id != null) {
        av.src = window.API_BASE + '/assets/avatars/' + String(s.sas_id) + '.png';
        av.style.display = 'block';
        av.onerror = function () { av.style.display = 'none'; };
      } else {
        av.removeAttribute('src');
        av.style.display = 'none';
      }
      wrap.removeAttribute('hidden');
    } catch (e) {
      wrap.setAttribute('hidden', '');
    }
  }

  function wireBlankHeaderNav() {
    var menuBtn = document.getElementById('menuBtn');
    var navOverlay = document.getElementById('navMenuOverlay');
    if (!menuBtn || !navOverlay) return;
    menuBtn.addEventListener('click', function () {
      var hidden = navOverlay.style.display === 'none';
      navOverlay.style.display = hidden ? 'flex' : 'none';
      navOverlay.setAttribute('aria-hidden', hidden ? 'false' : 'true');
    });
    var regattaLink = navOverlay.querySelector('a[data-mode="regatta"]');
    if (regattaLink) {
      regattaLink.addEventListener('click', function (e) {
        e.preventDefault();
        window.location.href = '/?mode=regatta';
      });
    }
    navOverlay.addEventListener('click', function (e) {
      if (e.target && e.target.tagName === 'A') {
        navOverlay.style.display = 'none';
        navOverlay.setAttribute('aria-hidden', 'true');
      }
    });
  }

  async function refreshHeaderAuth() {
    if (typeof updateHeaderAuthStatus === 'function') {
      try {
        await updateHeaderAuthStatus();
      } catch (e) { /* ignore */ }
    }
    await syncAdminV10SecondHeader();
  }

  var dashboardPayload = null;
  var liveCache = { online: [] };
  var restartPollTimer = null;
  var scrapeRowsDelegated = false;
  var systemMid = '';
  var systemVer = '';
  var loginCountBySas = {};

  async function refreshLoginMap() {
    loginCountBySas = {};
    try {
      var r = await fetch(window.API_BASE + '/admin/list/registered-users', { credentials: 'include', cache: 'no-store' });
      var j = await r.json();
      (j.rows || []).forEach(function (row) {
        var id = String(row.sas_id != null ? row.sas_id : '').trim();
        if (!id) return;
        var lc = row.login_count != null ? String(row.login_count).trim() : '0';
        loginCountBySas[id] = lc || '0';
      });
    } catch (e) {}
  }

  function aggregateSessionPaths(onlineUsers) {
    var m = {};
    (onlineUsers || []).forEach(function (u) {
      var p = String(u.current_page || u.last_path || '').trim() || '/';
      m[p] = (m[p] || 0) + 1;
    });
    return Object.keys(m).map(function (k) { return { path: k, count: m[k] }; });
  }

  function aggregateSessionPathsV10() {
    var m = {};
    buildV10LiveSessionRows().forEach(function (x) {
      var p = x.page;
      if (!p) return;
      m[p] = (m[p] || 0) + 1;
    });
    return Object.keys(m).map(function (k) { return { path: k, count: m[k] }; });
  }

  function formatShortDuration(sec) {
    if (sec == null || isNaN(sec) || sec < 0) return '0m';
    var s = Math.floor(sec);
    var m = Math.floor(s / 60);
    if (m < 60) return m + 'm';
    var h = Math.floor(m / 60);
    return h + 'h ' + (m % 60) + 'm';
  }

  function formatUptimeFromStart(ts) {
    if (ts == null || isNaN(ts)) return '';
    var sec = Math.max(0, Math.floor(Date.now() / 1000) - ts);
    var d = Math.floor(sec / 86400);
    var h = Math.floor((sec % 86400) / 3600);
    var m = Math.floor((sec % 3600) / 60);
    var s = sec % 60;
    return (d ? d + 'd ' : '') + h + 'h ' + m + 'm ' + s + 's';
  }

  function tickSystemLine() {
    var el = document.getElementById('v10SystemLine');
    if (!el) return;
    var ts = parseInt(el.getAttribute('data-start-ts'), 10);
    var up = formatUptimeFromStart(ts);
    var parts = [];
    if (up) parts.push('Uptime ' + up);
    if (systemMid) parts.push(systemMid.replace(/^\s*\|\s*/, ''));
    if (systemVer) parts.push(systemVer.replace(/^\s*\|\s*/, ''));
    el.textContent = parts.join(' | ');
  }

  function setStatTiles(d) {
    function set(id, v) {
      var el = document.getElementById(id);
      if (!el) return;
      el.textContent = v != null && v !== '' ? String(v) : '';
    }
    if (!d) return;
    set('v10TileSailors', d.active_sailors);
    set('v10TileClasses', d.classes_sailed);
    set('v10TileRegattas', d.regattas_sailed);
    set('v10TileRaces', d.races_raced);
  }

  /** Remove public blank.html news block (API feed); this page uses #news-container only. */
  function removeBlankLandingNewsFeed() {
    var sec = document.getElementById('blank-news-section');
    if (sec && sec.parentNode) sec.parentNode.removeChild(sec);
  }

  /** Same ordering as public /events upcoming: blank_hub bundle + series_years_count. */
  function adminUpcomingDisplaySort(a, b) {
    function entSort(ev) {
      if (ev.entries_for_sort != null && ev.entries_for_sort !== '') {
        var n = Number(ev.entries_for_sort);
        if (isFinite(n)) return n;
      }
      return Math.max(Number(ev.entries || 0) || 0, Number(ev.entries_max_series || 0) || 0);
    }
    var syA = Number(a.series_years_count || 0) || 0;
    var syB = Number(b.series_years_count || 0) || 0;
    var estA = syA >= 2 ? 0 : 1;
    var estB = syB >= 2 ? 0 : 1;
    if (estA !== estB) return estA - estB;
    var entA = entSort(a);
    var entB = entSort(b);
    if (entB !== entA) return entB - entA;
    if (syB !== syA) return syB - syA;
    var sa = String(a.start_date || '').slice(0, 10);
    var sb = String(b.start_date || '').slice(0, 10);
    var dc = sa.localeCompare(sb);
    if (dc !== 0) return dc;
    var na = String(a.event_name || '').localeCompare(String(b.event_name || ''));
    if (na !== 0) return na;
    return String(a.regatta_id || '').localeCompare(String(b.regatta_id || ''));
  }

  /** DB: GET /api/events?blank_hub=1 (events[] + series_years_count; same sort as site). */
  async function loadNews() {
    var el = document.getElementById('news-container');
    if (!el) return;
    try {
      var res = await fetch(window.API_BASE + '/api/events?blank_hub=1', {
        credentials: 'include',
        cache: 'no-store'
      });
      if (!res.ok) {
        el.innerHTML = '';
        return;
      }
      var data = await res.json();
      var events = Array.isArray(data.events) ? data.events : Array.isArray(data) ? data : [];

      var today = new Date().toISOString().slice(0, 10);

      events.forEach(function (e) {
        e.races_sailed = e.races_sailed || 0;
        e.entries = e.entries || 0;
        e.has_results =
          e.races_sailed > 0 || e.entries > 0 ? 1 : 0;
        var sd = String(e.start_date || '').slice(0, 10);
        var ed = String(e.end_date || e.start_date || '').slice(0, 10);
        e.start_date = sd;
        e.end_date = ed;
        e.is_live = sd !== '' && ed !== '' && sd <= today && today <= ed;
      });

      var live = events.filter(function (e) {
        return e.is_live;
      });

      live.sort(function (a, b) {
        return (
          (b.has_results - a.has_results) ||
          (b.races_sailed - a.races_sailed) ||
          (b.entries - a.entries)
        );
      });

      renderNews(live, events, today);
    } catch (err) {
      if (el) el.innerHTML = '';
    }
  }

  /** True when calendar row is linked to real results (races sailed or entry rows). */
  function eventHasResults(e) {
    return (e.races_sailed || 0) > 0 || (e.entries || 0) > 0;
  }

  /**
   * GET /api/events?blank_hub=1: each item includes regatta_id when events.regatta_id column exists (api.py ~9770–9771); value may be null.
   * If the key is missing (no column) or value is empty → no href (UI shows NOT FOUND).
   */
  function eventManageHref(e) {
    if (!e || !Object.prototype.hasOwnProperty.call(e, 'regatta_id')) return null;
    var rid = e.regatta_id;
    if (rid == null || String(rid).trim() === '') return null;
    return '/admin/event-manage/' + encodeURIComponent(String(rid).trim());
  }

  /**
   * Hero / “breaking” slot: live + results only. Live with no results goes in the row list (next section), not the big card.
   */
  function renderNews(live, events, today) {
    var container = document.getElementById('news-container');
    if (!container) return;

    container.innerHTML = '';

    var upcoming = events
      .filter(function (e) {
        return String(e.start_date || '').slice(0, 10) >= today;
      })
      .sort(adminUpcomingDisplaySort);

    var liveWithResults = live.filter(eventHasResults);
    var liveNoResults = live.filter(function (e) {
      return !eventHasResults(e);
    });

    var top = null;
    var rest = [];

    if (liveWithResults.length) {
      top = liveWithResults[0];
      rest = liveWithResults
        .slice(1)
        .concat(liveNoResults)
        .concat(upcoming);
    } else {
      var hi = -1;
      for (var i = 0; i < upcoming.length; i++) {
        var u = upcoming[i];
        if (u.is_live && !eventHasResults(u)) continue;
        hi = i;
        break;
      }
      top = hi >= 0 ? upcoming[hi] : null;
      rest =
        liveNoResults.concat(
          hi >= 0
            ? upcoming.slice(0, hi).concat(upcoming.slice(hi + 1))
            : upcoming
        );
    }

    var maxRows = 4;
    if (!top) {
      maxRows = 5;
    }

    if (!top && !rest.length) return;

    if (top) {
      var topHref = eventManageHref(top);
      var main = topHref ? document.createElement('a') : document.createElement('div');
      main.className = 'news-main-card' + (topHref ? ' news-event-manage-link' : '');
      if (topHref) main.href = topHref;
      var breakingLive = top.is_live && eventHasResults(top);
      var topTag = breakingLive ? '🔴 LIVE' : top.is_live ? '🔴 LIVE' : 'EVENT';
      var topTitle = escapeHtml(top.event_name || '');
      var topSub = eventHasResults(top)
        ? escapeHtml(String(top.races_sailed || 0)) +
          ' races · ' +
          escapeHtml(String(top.entries || 0)) +
          ' entries'
        : 'No results yet';
      main.innerHTML =
        '<div class="news-tag' +
        (breakingLive ? '' : ' news-tag--event') +
        '">' +
        escapeHtml(topTag) +
        '</div>' +
        '<div class="news-title">' +
        topTitle +
        '</div>' +
        '<div class="news-sub">' +
        topSub +
        '</div>' +
        (topHref ? '' : '<div class="news-manage-missing">NOT FOUND</div>');
      container.appendChild(main);
    }

    rest.slice(0, maxRows).forEach(function (e) {
      var rowHref = eventManageHref(e);
      var row = rowHref ? document.createElement('a') : document.createElement('div');
      row.className = 'news-row' + (rowHref ? ' news-event-manage-link' : '');
      if (rowHref) row.href = rowHref;
      var rowLive = !!e.is_live;
      var rowHasRes = eventHasResults(e);
      var rowTag = rowLive ? '🔴 LIVE' : 'EVENT';
      var muted = !rowLive || !rowHasRes;
      row.innerHTML =
        '<div class="news-row-tag' +
        (muted ? ' news-row-tag--muted' : '') +
        '">' +
        escapeHtml(rowTag) +
        '</div>' +
        '<div class="news-row-title">' +
        escapeHtml(e.event_name || '') +
        '</div>' +
        (rowHref ? '' : '<span class="news-manage-missing">NOT FOUND</span>');
      container.appendChild(row);
    });
  }

  var newsSearchToggleWired = false;
  function wireNewsStatsSearchToggle() {
    if (newsSearchToggleWired) return;
    var searchInput = document.querySelector('#searchInput, input[type="search"], input[placeholder*="Search"]');
    var newsSection = document.getElementById('news-stats-section');
    if (!searchInput || !newsSection) return;
    newsSearchToggleWired = true;
    function sync() {
      newsSection.style.display = String(searchInput.value || '').length > 0 ? 'none' : 'block';
    }
    searchInput.addEventListener('input', sync);
    sync();
  }

  function liveUserFirstName(fullName) {
    var s = String(fullName || '').trim();
    if (!s) return '';
    return s.split(/\s+/)[0] || '';
  }

  /** DB-backed only: optional device_name column; device_type → 📱 Mobile / 💻 Desktop. No UA parsing. */
  function liveUserDeviceSegment(u) {
    var name = String(u.device_name || '').trim();
    var dt = String(u.device_type || '').toLowerCase();
    var isMobile = dt === 'mobile' || dt === 'tablet' || dt === 'phone';
    var isDesktop = dt === 'desktop' || dt === 'laptop';
    if (name) {
      var ic = isMobile ? '📱' : (isDesktop ? '💻' : '');
      return ic ? ic + ' ' + name : name;
    }
    if (isMobile) return '📱 Mobile';
    if (isDesktop) return '💻 Desktop';
    return '';
  }

  /** Max seconds shown for "active now" duration and avg-session (not total login age). */
  var ACTIVE_DURATION_CAP_SEC = 30 * 60;

  /** COALESCE(last_activity, session_start, created_at) in Unix — session row uses created_at as login. */
  function liveDurationAnchorUnix(u) {
    var la = u.last_activity_unix;
    if (la != null && la !== '' && !isNaN(Number(la))) return Number(la);
    var ss = u.session_start_unix;
    if (ss != null && ss !== '' && !isNaN(Number(ss))) return Number(ss);
    return NaN;
  }

  function liveSessionActiveDurationSec(now, u) {
    var anchor = liveDurationAnchorUnix(u);
    if (isNaN(anchor)) return 0;
    var raw = Math.max(0, now - anchor);
    return Math.min(ACTIVE_DURATION_CAP_SEC, raw);
  }

  /** Valid live rows: session_id, current_page, last_seen_unix; deduped by session_id; sort by capped active duration. */
  function buildV10LiveSessionRows() {
    var online = liveCache.online || [];
    var now = Math.floor(Date.now() / 1000);
    var ranked = [];
    (online || []).forEach(function (u) {
      var sid = String(u.sas_id || '').trim();
      var page = String(u.current_page || u.last_path || '').trim() || '/';
      var ls = u.last_seen_unix != null ? Number(u.last_seen_unix) : NaN;
      var sessId = String(u.session_id || '').trim();
      if (!sessId || isNaN(ls)) return;
      if (isNaN(liveDurationAnchorUnix(u))) return;
      var dur = liveSessionActiveDurationSec(now, u);
      ranked.push({ u: u, dur: dur, sid: sid, page: page });
    });
    ranked.sort(function (a, b) { return b.dur - a.dur; });
    var seen = {};
    return ranked.filter(function (x) {
      var id = String(x.u.session_id || '').trim();
      if (!id || seen[id]) return false;
      seen[id] = true;
      return true;
    });
  }

  function renderLiveUsers() {
    var line = document.getElementById('v10LiveActiveLine');
    var box = document.getElementById('v10LiveUserLines');
    var allRows = buildV10LiveSessionRows();
    var n = allRows.length;
    if (line) line.textContent = n ? ('Active now: ' + n + ' (refreshes ~' + Math.round(REFRESH_MS / 1000) + 's)') : 'Active now: 0';
    if (!box) return;
    if (!n) {
      box.innerHTML = '';
      return;
    }
    var ranked = allRows.slice(0, 5);
    box.innerHTML = ranked.map(function (x) {
      var u = x.u;
      var sid = x.sid;
      var fn = liveUserFirstName(u.name);
      if (!fn && !sid) return '';
      var who = fn ? escapeHtml(fn) + ' (' + escapeHtml(sid) + ')' : '(' + escapeHtml(sid) + ')';
      var devSeg = liveUserDeviceSegment(u);
      var devHtml = devSeg ? escapeHtml(devSeg) + ' · ' : '';
      var pageHtml = pathLabelHtml(x.page);
      var loginPart = '';
      if (sid && loginCountBySas[sid] != null && loginCountBySas[sid] !== '') {
        loginPart = ' · ' + escapeHtml(String(loginCountBySas[sid])) + ' logins';
      }
      return '<p class="v10-one-line">' + devHtml + who + ' · ' + pageHtml + ' · ' + formatShortDuration(x.dur) + loginPart + '</p>';
    }).filter(Boolean).join('');
  }

  function renderBehaviourSnapshot() {
    var card = document.getElementById('v10BehaviourCard');
    var body = document.getElementById('v10BehaviourBody');
    if (!body || !card) return;
    var lines = [];
    var liveTop = sortCountDesc(aggregateSessionPathsV10());
    if (liveTop.length) {
      var t = liveTop[0];
      lines.push('<p class="v10-one-line">Top page (active sessions): ' + pathLabelHtml(t.path) + ' (' + Number(t.count || 0) + ')</p>');
    }
    var liveRows = buildV10LiveSessionRows();
    var durations = liveRows.map(function (x) { return x.dur; });
    if (durations.length) {
      var sum = durations.reduce(function (a, b) { return a + b; }, 0);
      var avg = Math.floor(sum / durations.length);
      var am = Math.floor(avg / 60);
      var as = avg % 60;
      lines.push('<p class="v10-one-line">Avg session (active): ' + am + 'm ' + as + 's</p>');
    }
    if (liveRows.length) {
      lines.push('<p class="v10-one-line">Active now: ' + liveRows.length + '</p>');
    }
    body.innerHTML = lines.join('');
    card.classList.toggle('v10-hidden', lines.length === 0);
  }

  function setPartialBanner() {
    var el = document.getElementById('trafficPartialLabel');
    if (!el) return;
    el.classList.add('v10-hidden');
    el.textContent = '';
  }

  function renderTrafficBlock() {
    var container = document.getElementById('v10TrafficLines');
    if (!container) return;
    setPartialBanner();
    var parts = [];
    var fromApi = dashboardPayload && dashboardPayload.traffic_top_paths;
    var livePages = sortCountDesc(
      fromApi && fromApi.length ? fromApi : aggregateSessionPathsV10()
    ).slice(0, 5);
    if (livePages.length) {
      parts.push('<div class="v10-subtle">Top pages (same data as Live users)</div>');
      livePages.forEach(function (p) {
        parts.push('<p class="v10-one-line-traffic">' + pathLabelHtml(p.path) + ' (' + Number(p.count || 0) + ')</p>');
      });
    }
    container.innerHTML = parts.join('');
  }

  function applyDashboardMeta(d) {
    if (!d) return;
    dashboardPayload = d;
    liveCache.online = d.online_users || [];
    var st = d.server_start_timestamp;
    if (st != null) {
      var sys = document.getElementById('v10SystemLine');
      if (sys) sys.setAttribute('data-start-ts', String(st));
      tickSystemLine();
    }
    setStatTiles(d);
  }

  function adminDashboardDataUrl() {
    var pathQs = '';
    try {
      if (window.location && window.location.pathname) {
        pathQs = '&path=' + encodeURIComponent(window.location.pathname || '/');
      }
    } catch (e) { /* ignore */ }
    return window.API_BASE + '/admin/dashboard-data?t=' + Date.now() + pathQs;
  }

  async function loadDashboardData() {
    var r = await fetch(adminDashboardDataUrl(), { credentials: 'include', cache: 'no-store' });
    var d = await r.json();
    applyDashboardMeta(d);
    return d;
  }

  function renderAllDynamic() {
    renderLiveUsers();
    renderBehaviourSnapshot();
    renderTrafficBlock();
    loadScrapes();
    loadNews();
  }

  async function loadVersion() {
    try {
      var r = await fetch(window.API_BASE + '/admin/api/version', { credentials: 'include', cache: 'no-store' });
      var v = await r.json();
      var lr = v.api_start_time || '';
      systemMid = lr ? ('Last restart: ' + lr) : '';
      systemVer = v.deploy_marker ? String(v.deploy_marker) : '';
      tickSystemLine();
    } catch (e) {
      systemMid = '';
      systemVer = '';
      tickSystemLine();
    }
  }

  async function loadReviewIssues() {
    var dataEl = document.getElementById('v10DataLine');
    if (!dataEl) return;
    try {
      var r = await fetch(window.API_BASE + '/admin/review/issues', { credentials: 'include', cache: 'no-store' });
      var d = await r.json();
      var ns = (d.sailors || []).length;
      var nc = (d.classes || []).length;
      var clubs = d.unknown_clubs_distinct != null ? Number(d.unknown_clubs_distinct) : 0;
      dataEl.textContent = 'Unresolved: ' + ns + ' | Clubs: ' + clubs + ' | Classes: ' + nc;
    } catch (e) {
      dataEl.textContent = '';
    }
  }

  /** Dashboard scrape row: OK / FAIL / RUN / — from API status string only. */
  function scrapeStatusDisplay(status) {
    var s = String(status || '');
    if (s === 'Failed') return 'FAIL';
    if (s === 'Running') return 'RUN';
    if (s === 'Never Run') return '—';
    return 'OK';
  }

  function fmtScrapeInt(v) {
    if (v == null || v === '') return '—';
    var n = Number(v);
    if (!isFinite(n)) return '—';
    if (Math.floor(n) !== n) return '—';
    return String(n);
  }

  function fmtShortIso(iso) {
    if (!iso) return '—';
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso).slice(0, 16);
      return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '—';
    }
  }

  async function loadScrapes() {
    var wrap = document.getElementById('scpRows');
    if (!wrap) return;
    try {
      var r = await fetch(window.API_BASE + '/admin/api/scrape-status', { credentials: 'include', cache: 'no-store' });
      var d = await r.json();
      var list = (d.scrapes) ? d.scrapes : [];
      wrap.innerHTML = '';
      list.forEach(function (s) {
        var row = document.createElement('div');
        row.className = 'scrape-row';
        row.setAttribute('role', 'group');
        var name = escapeHtml(s.scrape_name || '—');
        var stDisp = scrapeStatusDisplay(s.status);
        var lastAt = fmtShortIso(s.last_run_at || s.last_successful_run || s.last_run);
        var nextAt = fmtShortIso(s.next_run_at || s.next_scheduled_run);
        var newVal = fmtScrapeInt(s.new_records);
        var totVal = fmtScrapeInt(s.total_records);
        var actionBits = [];
        if (s.audit_url) actionBits.push('<a href="' + escapeHtml(s.audit_url) + '">Audit</a>');
        if (s.log_url) actionBits.push('<a href="' + escapeHtml(s.log_url) + '">Log</a>');
        if (s.run_implemented && s.run_key) {
          actionBits.push(
            '<button type="button" class="blank-stat" data-scrape-run="' +
              escapeHtml(String(s.run_key)) +
              '"><span class="blank-stat-val">Run</span></button>'
          );
        }
        var actionsLine = actionBits.length ? actionBits.join(' ') : '—';
        row.innerHTML =
          '<div class="scrape-main">' +
          '<div class="v10-scrape-name">' + name + '</div>' +
          '<div class="v10-one-line">Status: ' + escapeHtml(stDisp) + '</div>' +
          '<div class="v10-one-line">Last: ' + escapeHtml(lastAt) + '</div>' +
          '<div class="v10-one-line">Next: ' + escapeHtml(nextAt) + '</div>' +
          '<div class="v10-one-line">New: ' + escapeHtml(newVal) + '</div>' +
          '<div class="v10-one-line">Total: ' + escapeHtml(totVal) + '</div>' +
          '<div class="v10-one-line">Actions: ' + actionsLine + '</div>' +
          '</div>';
        wrap.appendChild(row);
      });
    } catch (e) {
      wrap.innerHTML = '';
    }
  }

  function wireScrapeRunDelegation() {
    if (scrapeRowsDelegated) return;
    var wrap = document.getElementById('scpRows');
    if (!wrap) return;
    scrapeRowsDelegated = true;
    wrap.addEventListener('click', async function (ev) {
      var btn = ev.target && ev.target.closest && ev.target.closest('button[data-scrape-run]');
      if (!btn) return;
      var key = btn.getAttribute('data-scrape-run');
      if (!key || !window.confirm('Run scrape "' + key + '" now?')) return;
      try {
        var resp = await fetch(window.API_BASE + '/admin/api/run-scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ scrape: key })
        });
        if (resp.ok) await loadScrapes();
      } catch (err) {}
    });
  }

  async function refreshAll() {
    await refreshHeaderAuth();
    await loadDashboardData();
    await refreshLoginMap();
    renderLiveUsers();
    renderBehaviourSnapshot();
    renderTrafficBlock();
    await loadScrapes();
    await loadNews();
  }

  function wireRestart() {
    var btn = document.getElementById('adminRestartBtn');
    var statusEl = document.getElementById('restartStatus');
    if (!btn) return;
    btn.addEventListener('click', async function () {
      if (!window.confirm('Restart the API process on this server?')) return;
      if (restartPollTimer) {
        window.clearInterval(restartPollTimer);
        restartPollTimer = null;
      }
      var initialEl = document.getElementById('v10SystemLine');
      var initial = initialEl ? parseInt(initialEl.getAttribute('data-start-ts'), 10) : NaN;
      btn.disabled = true;
      if (statusEl) {
        statusEl.style.visibility = 'visible';
        statusEl.textContent = '';
      }
      try {
        await fetch(window.API_BASE + '/admin/api/restart', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: '{}' });
      } catch (e) {}
      var tries = 0;
      restartPollTimer = window.setInterval(async function () {
        tries += 1;
        if (tries > 60) {
          window.clearInterval(restartPollTimer);
          restartPollTimer = null;
          btn.disabled = false;
          return;
        }
        try {
          var r = await fetch(adminDashboardDataUrl(), { credentials: 'include', cache: 'no-store' });
          var d = await r.json();
          var st = d.server_start_timestamp != null ? Number(d.server_start_timestamp) : NaN;
          if (!isNaN(st) && !isNaN(initial) && st !== initial) {
            window.clearInterval(restartPollTimer);
            restartPollTimer = null;
            applyDashboardMeta(d);
            await loadVersion();
            await refreshLoginMap();
            renderAllDynamic();
            btn.disabled = false;
            if (statusEl) {
              statusEl.textContent = '';
              statusEl.style.visibility = 'hidden';
            }
          }
        } catch (e) {}
      }, 2000);
    });
  }

  wireBlankHeaderNav();
  removeBlankLandingNewsFeed();
  refreshHeaderAuth().catch(function () {});

  wireRestart();
  wireScrapeRunDelegation();
  wireNewsStatsSearchToggle();
  window.setInterval(tickSystemLine, 1000);

  Promise.all([
    refreshHeaderAuth(),
    loadDashboardData(),
    refreshLoginMap(),
    loadVersion(),
    loadReviewIssues()
  ]).then(function () {
    renderLiveUsers();
    renderBehaviourSnapshot();
    renderTrafficBlock();
    return loadScrapes();
  }).then(function () {
    return loadNews();
  });

  window.setInterval(function () {
    refreshAll();
  }, REFRESH_MS);
})();
