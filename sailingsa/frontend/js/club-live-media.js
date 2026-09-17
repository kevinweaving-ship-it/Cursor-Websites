/**
 * ZVYC gold live media: weather card, then cam/reels.
 * Location: directly under the identity panel, above About.
 * Same stacked full-width position on mobile and laptop. No-op on other clubs.
 */
(function () {
  'use strict';
  if (window.__SSA_CLUB_LIVE_MEDIA__) return;
  window.__SSA_CLUB_LIVE_MEDIA__ = true;

  var CLUB_SLUG = 'zvyc';
  var REGATTA_ID = '2026-09-13-zvyc-cape-classic';
  var HOST_ID = 'club-zvyc-live-media';
  var WX_ID = 'ssa-regatta-slot-card';
  var MM_ID = 'mmLiptonReels';
  var CSS_ID = 'club-live-media-css';
  var BRAND = '/assets/adverts/mm-powered-by-live.png?v=mmcc2';
  var JS_VER = 'clubmm3';

  function clubSlug() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    var m = path.match(/^\/club\/([^/]+)$/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      '.club-page .club-live-media{width:100%;max-width:100%;box-sizing:border-box;display:flex!important;flex-direction:column;gap:0;margin:0;padding:0;border:0;background:transparent;box-shadow:none;}' +
      '.club-page .club-live-media .ssa-regatta-slot-card{order:0!important;margin:0;width:100%;max-width:100%;}' +
      '.club-page .club-live-media .mm-lipton-reels{order:1!important;margin-top:10px;width:100%;max-width:100%;}' +
      '.club-page .club-story-inner > .club-live-media{max-width:100%;}';
    document.head.appendChild(s);
  }

  function ensureCssLink() {
    var href = '/css/mm-lipton-reels.css?v=' + JS_VER;
    if (document.querySelector('link[href*="mm-lipton-reels.css"]')) return;
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = href;
    document.head.appendChild(l);
  }

  function mmInnerHtml() {
    return (
      '<div class="mm-lipton-reels-compact">' +
      '<a class="mm-lipton-reels-brand" href="https://www.marinemegastore.co.za/" target="_blank" rel="noopener noreferrer">' +
      '<img src="' +
      BRAND +
      '" alt="Powered by Marine Megastore Live Streaming" width="320" height="213" loading="lazy" decoding="async">' +
      '</a>' +
      '<div class="mm-lipton-reels-rail-wrap">' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
      '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
      '</div></div>'
    );
  }

  function fillHost(host) {
    if (host.getAttribute('data-club-live-ready') === '1') {
      return orderWeatherAboveMm(host);
    }
    var wx = document.getElementById(WX_ID);
    if (!wx) {
      wx = document.createElement('section');
      wx.id = WX_ID;
      wx.className = 'card ssa-wx-card ssa-regatta-slot-card';
      wx.setAttribute('data-weather-club', 'ZVYC');
      wx.setAttribute('data-weather-role', 'venue');
      wx.setAttribute('aria-label', 'Venue wind');
    }
    var mm = document.getElementById(MM_ID);
    if (!mm) {
      mm = document.createElement('section');
      mm.id = MM_ID;
      mm.className = 'card mm-lipton-reels mm-lipton-reels--compact';
      mm.setAttribute('data-regatta-id', REGATTA_ID);
      mm.setAttribute('data-mm-poll', '1');
      mm.setAttribute('data-mm-club-page', '1');
      mm.setAttribute('data-mm-brand-soon', BRAND);
      mm.setAttribute('data-mm-brand-live', BRAND);
      mm.setAttribute(
        'data-mm-initial',
        JSON.stringify({
          enabled: true,
          feed_source: 'marine-megastore',
          fb_page: 'marin.megastoresa',
          videos: [],
        })
      );
      mm.innerHTML = mmInnerHtml();
    }
    host.appendChild(wx);
    host.appendChild(mm);
    host.setAttribute('data-club-live-ready', '1');
    return orderWeatherAboveMm(host);
  }

  function orderWeatherAboveMm(host) {
    var wx = document.getElementById(WX_ID);
    var mm = document.getElementById(MM_ID);
    if (host && wx && mm && wx.parentNode === host && mm.parentNode === host && wx.nextSibling !== mm) {
      host.insertBefore(wx, mm);
    }
    return host;
  }

  function placeHost() {
    var existing = document.getElementById(HOST_ID);
    if (existing) {
      moveHostToGold(existing);
      return fillHost(existing);
    }

    var host = document.createElement('div');
    host.id = HOST_ID;
    host.className = 'club-live-media';
    host.setAttribute('aria-label', 'Live weather and club camera');
    if (!moveHostToGold(host)) return null;
    return fillHost(host);
  }

  function moveHostToGold(host) {
    var ident = document.querySelector('.club-story-identity, .class-gold-identity-card');
    if (ident && ident.parentNode) {
      if (host.previousSibling !== ident) ident.parentNode.insertBefore(host, ident.nextSibling);
      return host;
    }

    var about = document.querySelector('.club-story-about');
    var aboutPanel = about && (about.closest('.club-story-panel') || about);
    if (aboutPanel && aboutPanel.parentNode) {
      aboutPanel.parentNode.insertBefore(host, aboutPanel);
      return host;
    }

    var inner = document.querySelector('.club-story-inner');
    if (inner) {
      var firstBlock = inner.querySelector('.club-story-block');
      if (firstBlock) {
        inner.insertBefore(host, firstBlock);
        return host;
      }
      inner.appendChild(host);
      return host;
    }

    var header = document.querySelector('.club-page .header, .club-page-header, .club-story-header');
    if (header && header.parentNode) {
      header.parentNode.insertBefore(host, header.nextSibling);
      return host;
    }

    var page = document.querySelector('.club-page');
    if (page) {
      page.insertBefore(host, page.firstChild);
      return host;
    }
    return null;
  }

  function loadScript(src) {
    return new Promise(function (resolve) {
      var base = src.split('?')[0];
      var found = document.querySelector('script[src*="' + base + '"]');
      if (found) {
        if (found.getAttribute('data-loaded') === '1' || found.readyState === 'complete') {
          resolve();
          return;
        }
        found.addEventListener('load', function () {
          resolve();
        });
        found.addEventListener('error', function () {
          resolve();
        });
        return;
      }
      var s = document.createElement('script');
      s.src = src;
      s.async = false;
      s.onload = function () {
        s.setAttribute('data-loaded', '1');
        resolve();
      };
      s.onerror = function () {
        resolve();
      };
      document.head.appendChild(s);
    });
  }

  function boot() {
    if (clubSlug() !== CLUB_SLUG) return;
    injectCss();
    ensureCssLink();
    if (!placeHost()) return;
    loadScript('/js/mm-lipton-reels-card.js?v=' + JS_VER)
      .then(function () {
        return loadScript('/js/regatta-slot-card.js?v=' + JS_VER);
      })
      .catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
