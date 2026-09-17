/**
 * Live cams — same grab as Voelklip.
 *
 * HOW:  import video-stream.js from go2rtc, append <video-stream> into a static .cam-cell.
 * WHERE: cell[data-cam] is the go2rtc stream name (garage, workshop, pool, driveway, hyc).
 * WHY:  one feed, used on a club URL and/or an MM event card. Never rewrite a cell
 *       that already has <video-stream> (that flash is what Voelklip does not do).
 *
 * Club page:  <div class="cam-cell" data-cam="hyc">
 * MM event:   same cell / same data-cam inside the MM card (data-live-cam="hyc").
 */
(function (global) {
  'use strict';
  if (global.SSALiveCam) return;

  var CAM = 'https://sailingsa.co.za:8443/';

  var SOURCES = {
    hyc: {
      id: 'hyc',
      src: 'hyc',
      label: 'HYC',
      why: 'HYC club live cam. Club page /club/hyc is a permanent card. Same data-cam=hyc is the video on an MM event card.',
      how: 'go2rtc',
      origin: CAM,
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
    'hyc-club': null,
    garage: {
      id: 'garage',
      src: 'garage',
      label: 'Garage',
      why: 'Voelklip reference cam.',
      how: 'go2rtc',
      origin: CAM,
      player: 'video-stream',
      mode: 'webrtc,mse',
      clubSurface: 'none',
      mmSurface: false,
      href: 'https://sailingsa.co.za/voelklip/',
    },
    workshop: {
      id: 'workshop',
      src: 'workshop',
      label: 'Workshop',
      why: 'Voelklip reference cam.',
      how: 'go2rtc',
      origin: CAM,
      player: 'video-stream',
      mode: 'webrtc,mse',
      clubSurface: 'none',
      mmSurface: false,
    },
    pool: {
      id: 'pool',
      src: 'pool',
      label: 'Pool',
      why: 'Voelklip reference cam.',
      how: 'go2rtc',
      origin: CAM,
      player: 'video-stream',
      mode: 'webrtc,mse',
      clubSurface: 'none',
      mmSurface: false,
    },
    driveway: {
      id: 'driveway',
      src: 'driveway',
      label: 'Driveway',
      why: 'Voelklip reference cam.',
      how: 'go2rtc',
      origin: CAM,
      player: 'video-stream',
      mode: 'webrtc,mse',
      clubSurface: 'none',
      mmSurface: false,
    },
    'hmyc-club': {
      id: 'hmyc-club',
      src: '',
      label: 'HMYC club cam',
      why: 'JPEG snapshot poll, not go2rtc. Club page keeps the snapshot MM card as deployed.',
      how: 'snapshot',
      still: 'https://hmyccam1.nwsza.net/latest.jpg',
      pollMs: 60000,
      clubSlug: 'hmyc',
      clubSurface: 'mm-snapshot',
      mmSurface: true,
      statusApi: '/api/club-cam/hmyc',
      href: 'https://agromet.ukzn.ac.za/midmar/index.html#canvas_container',
    },
  };
  SOURCES['hyc-club'] = SOURCES.hyc;

  function get(id) {
    var key = String(id || '').trim();
    if (key === 'hyc-club') key = 'hyc';
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
    return new URL('api/ws?src=' + src.src, src.origin || CAM).href;
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

  function cellsIn(box) {
    if (!box) return [];
    if (box.classList && box.classList.contains('cam-cell')) return [box];
    var nested = box.querySelectorAll('.cam-cell, [data-cam]');
    if (nested.length) return Array.prototype.slice.call(nested);
    if (box.getAttribute && box.getAttribute('data-cam')) return [box];
    return [];
  }

  /**
   * Voelklip loadStreams, copied. box is the card (or a single .cam-cell).
   * never rewrite: if the cell already has video-stream, skip it.
   */
  function start(box) {
    if (!box) return Promise.resolve(null);
    return import(CAM + 'video-stream.js')
      .then(function () {
        cellsIn(box).forEach(function (cell) {
          if (cell.querySelector('video-stream')) return;
          var name = cell.getAttribute('data-cam');
          if (!name) return;
          var el = document.createElement('video-stream');
          el.mode = 'webrtc,mse';
          el.background = false;
          el.src = new URL('api/ws?src=' + name, CAM);
          cell.appendChild(el);
          var v0 = el.video || el.querySelector('video');
          if (v0) {
            v0.controls = false;
            v0.removeAttribute('controls');
          }
        });
        return box;
      })
      .catch(function () {
        return null;
      });
  }

  function attach(cell, sourceId) {
    var src = get(sourceId);
    if (cell && src && src.src) cell.setAttribute('data-cam', src.src);
    if (cell && src) cell.setAttribute('data-live-cam', src.id);
    if (cell && src && src.how !== 'go2rtc') return Promise.resolve(src);
    return start(cell).then(function () {
      return src || null;
    });
  }

  global.SSALiveCam = {
    CAM: CAM,
    GO2RTC: CAM,
    SOURCES: SOURCES,
    get: get,
    forClub: forClub,
    wsUrl: wsUrl,
    mmVideo: mmVideo,
    eventVideo: mmVideo,
    attach: attach,
    start: start,
  };
})(window);
