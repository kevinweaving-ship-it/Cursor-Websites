/**
 * All /club/{slug} pages: same chrome as the homepage.
 * - Main navy header (logo left, Sign In / Sign Up + menu right)
 * - Remove Back to Search
 * - No outer page card / body inset so inner cards can use full MP width
 * Does not change js/blank-landing-header.js.
 */
(function () {
  'use strict';
  if (window.__SSA_CLUB_PAGE_STD__) return;
  window.__SSA_CLUB_PAGE_STD__ = true;

  var CSS_ID = 'club-page-std-css';
  var JS_VER = 'clubstd2';

  function isClubUrl() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    return /^\/club\/[^/]+$/.test(path);
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      'html,body{margin:0!important;padding:0;}' +
      'body.admin-dashboard-v10{background:#f0f4f8;}' +
      '.club-page{width:100%!important;max-width:none!important;margin:0!important;padding:0 0 1.5rem;box-sizing:border-box;border:none!important;background:transparent!important;box-shadow:none!important;}' +
      '.club-page a.back-to-home,.club-page .back-to-home{display:none!important;}' +
      '.club-page .header.club-page-header,.club-page .club-page-header,.club-page .header.club-story-header{' +
      'border:none!important;box-shadow:none!important;background:transparent!important;' +
      'padding:0!important;margin:0!important;border-radius:0!important;max-width:none!important;}' +
      '.club-page .club-story-inner{width:100%;box-sizing:border-box;}' +
      '.club-page .club-live-media{padding:0;border:0;background:transparent;box-shadow:none;}' +
      '@media (max-width:767px){' +
      '.club-page{padding:0 0 1rem;}' +
      '.club-page .club-story-inner{max-width:100%!important;padding:0!important;margin:0!important;}' +
      '.club-page .club-story-panel{width:100%;box-sizing:border-box;}' +
      '}';
    document.head.appendChild(s);
  }

  function isBackToSearch(el) {
    if (!el) return false;
    if (el.classList && (el.classList.contains('back-to-home') || el.classList.contains('back-to-search'))) {
      return true;
    }
    var t = String(el.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    return t.indexOf('back to search') !== -1;
  }

  function removeBackToSearch() {
    var nodes = document.querySelectorAll('a.back-to-home, .back-to-home, a.back-to-search, .back-to-search');
    var i;
    for (i = 0; i < nodes.length; i++) {
      if (nodes[i] && nodes[i].parentNode) nodes[i].parentNode.removeChild(nodes[i]);
    }
    var links = document.querySelectorAll('a');
    for (i = 0; i < links.length; i++) {
      if (isBackToSearch(links[i]) && links[i].parentNode) {
        links[i].parentNode.removeChild(links[i]);
      }
    }
  }

  function ensureClubPageClass() {
    var page = document.querySelector('.club-page');
    if (page) return page;
    if (!document.body) return null;
    document.body.classList.add('club-page');
    return document.body;
  }

  function headerHtml() {
    return (
      '<div class="admin-v10-second-header" aria-label="Site header">' +
      '<div class="admin-v10-second-header__inner">' +
      '<div class="admin-v10-second-header__top-row">' +
      '<div class="admin-v10-second-header__brand-block">' +
      '<a href="/" class="admin-v10-second-header__brand-link js-go-home" id="headerLogoLink" title="Home – SailingSA" aria-label="Home – SailingSA">' +
      '<span class="admin-v10-second-header__brand-slice admin-v10-second-header__brand-slice--word" aria-hidden="true"></span>' +
      '<span class="admin-v10-second-header__brand-slice admin-v10-second-header__brand-slice--flags" aria-hidden="true"></span>' +
      '</a></div>' +
      '<div class="admin-v10-second-header__right">' +
      '<div class="header-auth admin-v10-second-header__auth" id="headerAuth">' +
      '<div id="loginBox" style="display: none;"></div>' +
      '<div class="admin-v10-header-auth-sr-only" aria-hidden="true">' +
      '<div id="loggedInStatus" style="display: none;">' +
      '<img id="userAvatarImg" alt="Avatar" style="width:28px;height:28px;border-radius:50%;object-fit:cover;display:none;">' +
      '<div class="user-info"><span class="user-name" id="userNameDisplay"></span>' +
      '<span class="user-sas-id" id="userSasIdDisplay"></span></div></div></div></div>' +
      '<div class="admin-v10-second-header__user" id="adminV10SecondHeaderUser" hidden>' +
      '<div class="admin-v10-second-header__user-text">' +
      '<span class="admin-v10-second-header__name" id="adminV10SecondHeaderName"></span>' +
      '<span class="admin-v10-second-header__sas" id="adminV10SecondHeaderSas"></span></div>' +
      '<img class="admin-v10-second-header__avatar" id="adminV10SecondHeaderAvatar" alt="" width="72" height="72" decoding="async">' +
      '<button type="button" class="btn-logout admin-v10-second-header__logout" id="adminV10SecondHeaderLogoutBtn">Logout</button>' +
      '</div>' +
      '<button type="button" class="menu-btn" id="menuBtn" aria-label="Open menu"><span class="menu-icon"></span></button>' +
      '</div></div></div>' +
      '<nav id="navMenuOverlay" class="nav-menu-overlay" aria-hidden="true" style="display:none;">' +
      '<a href="/">Sailor</a><a href="/" data-mode="regatta">Regatta</a><a href="/about">About</a>' +
      '</nav></div>'
    );
  }

  function loadScript(src) {
    return new Promise(function (resolve) {
      var base = src.split('?')[0];
      if (document.querySelector('script[src*="' + base + '"]')) {
        resolve();
        return;
      }
      var s = document.createElement('script');
      s.src = src;
      s.async = false;
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        resolve();
      };
      document.head.appendChild(s);
    });
  }

  function ensureHeader() {
    if (document.body) document.body.classList.add('admin-dashboard-v10');
    if (document.querySelector('.admin-v10-second-header')) {
      return Promise.resolve();
    }
    if (document.body) document.body.insertAdjacentHTML('afterbegin', headerHtml());
    return loadScript('/js/api.js')
      .then(function () {
        return loadScript('/js/session.js');
      })
      .then(function () {
        return loadScript('/js/blank-landing-header.js?v=' + JS_VER);
      });
  }

  function boot() {
    if (!isClubUrl()) return;
    injectCss();
    ensureClubPageClass();
    removeBackToSearch();
    ensureHeader();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
