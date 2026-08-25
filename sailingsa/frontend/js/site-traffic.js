/**
 * SailingSA real-traffic beacon (humans only; bots rarely run this).
 * Posts to POST /api/traffic/collect → public.site_traffic_events.
 * Does not use login sessions.
 */
(function () {
  'use strict';
  if (window.__SSA_TRAFFIC__) return;
  window.__SSA_TRAFFIC__ = true;

  var IDLE_MS = 5 * 60 * 1000;
  var HEARTBEAT_MS = 15000;
  var SCROLL_MARKS = [25, 50, 75, 100];
  var COLLECT = '/api/traffic/collect';
  var LS_VISITOR = 'ssa_tid';
  var SS_VISIT = 'ssa_vid';
  var SS_SOURCE = 'ssa_src';

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function qs(name) {
    try {
      return new URLSearchParams(window.location.search).get(name) || '';
    } catch (e) {
      return '';
    }
  }

  function getVisitorId() {
    try {
      var id = localStorage.getItem(LS_VISITOR);
      if (!id) {
        id = uuid();
        localStorage.setItem(LS_VISITOR, id);
      }
      return id;
    } catch (e) {
      return uuid();
    }
  }

  function getVisitId(isNew) {
    try {
      var id = sessionStorage.getItem(SS_VISIT);
      if (!id || isNew) {
        id = uuid();
        sessionStorage.setItem(SS_VISIT, id);
      }
      return id;
    } catch (e) {
      return uuid();
    }
  }

  function classifySource(ref, utmSource, utmMedium) {
    var medium = (utmMedium || '').toLowerCase();
    var source = (utmSource || '').toLowerCase();
    if (medium === 'cpc' || medium === 'ppc' || source === 'google' || source === 'googleads') return 'google';
    if (medium === 'social' || /facebook|instagram|twitter|^x$|linkedin|tiktok|youtube/.test(source)) return 'social';
    var host = '';
    try {
      if (ref) host = (new URL(ref)).hostname.toLowerCase();
    } catch (e) {}
    var selfHost = (location.hostname || '').toLowerCase();
    if (host && (host === selfHost || host.endsWith('.' + selfHost))) return 'direct';
    if (/google\./.test(host) || host.indexOf('google.') === 0) return 'google';
    if (/(facebook|instagram|twitter|t\.co|x\.com|linkedin|tiktok|youtube|youtu\.be|whatsapp|reddit)/.test(host)) return 'social';
    if (!host) return 'direct';
    return 'referral';
  }

  var visitorId = getVisitorId();
  var visitId = getVisitId(false);
  var utmSource = qs('utm_source');
  var utmMedium = qs('utm_medium');
  var utmCampaign = qs('utm_campaign');
  var referrer = document.referrer || '';
  var sourceChannel = classifySource(referrer, utmSource, utmMedium);
  try {
    var cached = sessionStorage.getItem(SS_SOURCE);
    if (cached) sourceChannel = cached;
    else sessionStorage.setItem(SS_SOURCE, sourceChannel);
  } catch (e) {}

  var pageEntered = Date.now();
  var visibleMs = 0;
  var visibleSince = document.visibilityState === 'visible' ? Date.now() : null;
  var lastActivity = Date.now();
  var idleSent = false;
  var exited = false;
  var scrollSent = {};
  var queue = [];
  var flushTimer = null;

  function pathNow() {
    return (location.pathname || '/') + (location.search || '');
  }

  function visibleAccum() {
    var n = visibleMs;
    if (visibleSince) n += Date.now() - visibleSince;
    return n;
  }

  function enqueue(ev) {
    if (exited && ev.event_type !== 'exit') return;
    ev.visitor_id = visitorId;
    ev.visit_id = visitId;
    ev.path = ev.path || pathNow();
    ev.referrer = referrer;
    ev.source_channel = sourceChannel;
    ev.utm_source = utmSource || undefined;
    ev.utm_medium = utmMedium || undefined;
    ev.utm_campaign = utmCampaign || undefined;
    ev.page_visible_ms = visibleAccum();
    ev.duration_ms = Date.now() - pageEntered;
    queue.push(ev);
    if (!flushTimer) flushTimer = setTimeout(flush, 400);
  }

  function flush(sync) {
    flushTimer = null;
    if (!queue.length) return;
    var batch = queue.splice(0, 40);
    var body = JSON.stringify({ events: batch });
    try {
      if (sync && navigator.sendBeacon) {
        navigator.sendBeacon(COLLECT, new Blob([body], { type: 'application/json' }));
        return;
      }
    } catch (e) {}
    try {
      fetch(COLLECT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body,
        credentials: 'omit',
        keepalive: !!sync,
        cache: 'no-store',
      }).catch(function () {});
    } catch (e) {}
  }

  function touchActivity() {
    lastActivity = Date.now();
    if (idleSent) idleSent = false;
  }

  // New tab/session visit
  var visitFresh = false;
  try {
    visitFresh = !sessionStorage.getItem('ssa_vs');
    sessionStorage.setItem('ssa_vs', '1');
  } catch (e) {
    visitFresh = true;
  }
  if (visitFresh) {
    visitId = getVisitId(true);
    enqueue({ event_type: 'visit_start' });
  }
  enqueue({ event_type: 'page_view' });

  // Scroll milestones
  function onScroll() {
    touchActivity();
    var el = document.documentElement;
    var max = (el.scrollHeight - el.clientHeight) || 1;
    var pct = Math.min(100, Math.round((window.scrollY / max) * 100));
    for (var i = 0; i < SCROLL_MARKS.length; i++) {
      var m = SCROLL_MARKS[i];
      if (pct >= m && !scrollSent[m]) {
        scrollSent[m] = true;
        enqueue({ event_type: 'scroll', scroll_pct: m });
      }
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  // Clicks → what + where
  document.addEventListener(
    'click',
    function (e) {
      touchActivity();
      var t = e.target;
      if (!t) return;
      var a = t.closest ? t.closest('a,button,[role="button"],input[type="submit"]') : null;
      if (!a) a = t;
      var href = '';
      if (a.tagName === 'A' && a.href) href = a.href;
      var text = (a.innerText || a.value || a.getAttribute('aria-label') || '').trim().slice(0, 160);
      var sel = a.id ? '#' + a.id : a.tagName ? a.tagName.toLowerCase() : 'node';
      if (a.className && typeof a.className === 'string') {
        sel += '.' + a.className.trim().split(/\s+/).slice(0, 2).join('.');
      }
      enqueue({
        event_type: 'click',
        click_href: href || undefined,
        click_text: text || undefined,
        click_selector: sel.slice(0, 180),
      });
    },
    true
  );

  ['mousemove', 'keydown', 'touchstart'].forEach(function (ev) {
    window.addEventListener(ev, touchActivity, { passive: true });
  });

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') {
      if (visibleSince) {
        visibleMs += Date.now() - visibleSince;
        visibleSince = null;
      }
      enqueue({ event_type: 'page_leave' });
      flush(true);
    } else {
      visibleSince = Date.now();
      touchActivity();
    }
  });

  function sendExit() {
    if (exited) return;
    exited = true;
    enqueue({ event_type: 'exit' });
    flush(true);
  }
  window.addEventListener('pagehide', sendExit);
  window.addEventListener('beforeunload', sendExit);

  setInterval(function () {
    if (document.visibilityState !== 'visible') return;
    enqueue({ event_type: 'heartbeat' });
    if (!idleSent && Date.now() - lastActivity >= IDLE_MS) {
      idleSent = true;
      enqueue({ event_type: 'inactive' });
    }
  }, HEARTBEAT_MS);

  // SPA path changes
  var lastPath = pathNow();
  setInterval(function () {
    var p = pathNow();
    if (p === lastPath) return;
    enqueue({ event_type: 'page_leave', path: lastPath });
    lastPath = p;
    pageEntered = Date.now();
    scrollSent = {};
    enqueue({ event_type: 'page_view', path: p });
  }, 1000);
})();
