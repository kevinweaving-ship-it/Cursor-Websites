/**
 * Live cam sources — one catalog for club pages and MM event cards.
 *
 * Each source answers:
 *   how  — player recipe (go2rtc video-stream | jpeg poll)
 *   where — origin + stream name, still URL, status API
 *   why  — club venue permanent view and/or MM event card video
 *
 * Surfaces:
 *   clubSurface 'permanent' → /club/{slug} card (not the MM reel)
 *   clubSurface 'mm-snapshot' → existing snapshot MM card (HMYC, leave as deployed)
 *   mmSurface true → same source id is a video on an MM-type event card
 *
 * Voelklip rule: never rewrite a cell that already has <video-stream>.
 * Super Admin show/hide uses statusApi + saPatch when present.
 */
(function (global) {
  'use strict';
  if (global.SSALiveCam) return;

  var GO2RTC = 'https://sailingsa.co.za:8443/';

  var SOURCES = {
    'hyc-club': {
      id: 'hyc-club',
      label: 'HYC club cam',
      why: 'Hermanus Yacht Club venue view. Same feed on /club/hyc (permanent card) or an MM event card (video source). Super Admin can hide it from the public. Stream name hyc is reserved; Cam 5 is not on the NVR yet.',
      how: 'go2rtc',
      origin: GO2RTC,
      src: 'hyc',
      player: 'video-stream',
      mode: 'webrtc,mse',
      clubSlug: 'hyc',
      clubCardId: 'hyc-club-cam',
      clubSurface: 'permanent',
      mmSurface: true,
      statusApi: '/api/club-cam/hyc',
      saPatch: '/api/super-admin/club-cam/hyc',
      href: 'https://www.hyc.co.za/',
    },
    'hmyc-club': {
      id: 'hmyc-club',
      label: 'HMYC club cam',
      why: 'Midmar still from Agromet. JPEG poll, not a live pass-through. Club page keeps the snapshot MM card as deployed.',
      how: 'snapshot',
      still: 'https://hmyccam1.nwsza.net/latest.jpg',
      pollMs: 60000,
      clubSlug: 'hmyc',
      clubSurface: 'mm-snapshot',
      mmSurface: true,
      statusApi: '/api/club-cam/hmyc',
      href: 'https://agromet.ukzn.ac.za/midmar/index.html#canvas_container',
    },
    'voelklip-garage': {
      id: 'voelklip-garage',
      label: 'Voelklip garage',
      why: 'Reference live recipe: static .cam-cell, import video-stream.js, mode webrtc,mse. Not a club-page cam.',
      how: 'go2rtc',
      origin: GO2RTC,
      src: 'garage',
      player: 'video-stream',
      mode: 'webrtc,mse',
      clubSurface: 'none',
      mmSurface: false,
      href: 'https://sailingsa.co.za/voelklip/',
    },
  };

  function get(id) {
    var key = String(id || '').trim();
    return key && SOURCES[key] ? SOURCES[key] : null;
  }

  function forClub(slug) {
    var want = String(slug || '').toLowerCase();
    var id;
    for (id in SOURCES) {
      if (SOURCES[id] && SOURCES[id].clubSlug === want) return SOURCES[id];
    }
    return null;
  }

  function wsUrl(src) {
    if (!src || src.how !== 'go2rtc' || !src.src) return '';
    try {
      return new URL('api/ws?src=' + encodeURIComponent(src.src), src.origin || GO2RTC).href;
    } catch (e) {
      return String(src.origin || GO2RTC).replace(/\/?$/, '/') + 'api/ws?src=' + encodeURIComponent(src.src);
    }
  }

  function mmVideo(id) {
    var src = get(id);
    if (!src || !src.mmSurface) return null;
    if (src.how === 'go2rtc') {
      return {
        id: src.id,
        kind: 'webcam',
        live_pass: true,
        live_cam: src.id,
        title: src.label || 'Club cam',
        stream_url: wsUrl(src),
        stream_kind: 'webrtc',
        url: src.href || '',
        status_api: src.statusApi || '',
        aspect: '16 / 9',
        width: 16,
        height: 9,
      };
    }
    if (src.how === 'snapshot') {
      return {
        id: src.id,
        kind: 'webcam',
        snapshot: true,
        live_cam: src.id,
        title: src.label || 'Club cam',
        thumb: src.still,
        live_snap: src.still,
        url: src.href || '',
        status_api: src.statusApi || '',
        aspect: '16 / 9',
        width: 16,
        height: 9,
      };
    }
    return null;
  }

  function muteVideo(node) {
    var v = node && (node.video || (node.querySelector && node.querySelector('video')));
    if (!v) return;
    v.controls = false;
    v.removeAttribute('controls');
    v.muted = true;
    v.playsInline = true;
    v.setAttribute('playsinline', '');
  }

  function attach(cell, sourceId) {
    var src = get(sourceId);
    if (!cell || !src) return Promise.resolve(null);
    cell.setAttribute('data-live-cam', src.id);
    if (src.src) cell.setAttribute('data-cam', src.src);
    if (src.how !== 'go2rtc') return Promise.resolve(src);
    if (cell.querySelector('video-stream')) return Promise.resolve(src);
    if (cell.getAttribute('data-live-cam-loading') === '1') return Promise.resolve(src);
    cell.setAttribute('data-live-cam-loading', '1');
    var origin = src.origin || GO2RTC;
    return import(origin + 'video-stream.js')
      .then(function () {
        if (!cell.isConnected) return src;
        if (cell.querySelector('video-stream')) return src;
        var el = document.createElement('video-stream');
        el.mode = src.mode || 'webrtc,mse';
        el.background = false;
        el.src = new URL('api/ws?src=' + encodeURIComponent(src.src), origin);
        cell.appendChild(el);
        muteVideo(el);
        return src;
      })
      .catch(function () {
        cell.removeAttribute('data-live-cam-loading');
        return null;
      });
  }

  global.SSALiveCam = {
    GO2RTC: GO2RTC,
    SOURCES: SOURCES,
    get: get,
    forClub: forClub,
    wsUrl: wsUrl,
    mmVideo: mmVideo,
    eventVideo: mmVideo,
    attach: attach,
  };
})(window);
