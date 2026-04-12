/**
 * Hub header (blank.html, blank69, admin dashboard template): single owner of #loginBox + #adminV10SecondHeader*
 * for pages where sailingsaHubHeaderOwnedByBlankLandingJs() is true (blank69 path or body data-sailingsa-hub-header-isolated="1").
 * session.js must not paint those nodes on those pages.
 * Load after /js/api.js and /js/session.js; DOM may omit #menuBtn / #navMenuOverlay when hamburger is not used.
 */
(function () {
  if (!window.API_BASE && window.location && window.location.origin) {
    window.API_BASE = String(window.location.origin).replace(/\/$/, '');
  }

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

  function pathnameHasBlank69() {
    try {
      return (window.location && String(window.location.pathname || '').indexOf('blank69') !== -1);
    } catch (e) {
      return false;
    }
  }

  /** Same contract as session.js sailingsaHubHeaderOwnedByBlankLandingJs (prefer window fn when session.js loaded). */
  function hubUsesIsolatedSessionJsHeader() {
    try {
      if (typeof window.sailingsaHubHeaderOwnedByBlankLandingJs === 'function' &&
          window.sailingsaHubHeaderOwnedByBlankLandingJs()) {
        return true;
      }
    } catch (e) { /* ignore */ }
    return pathnameHasBlank69();
  }

  /**
   * Isolated hub: session.js updateHeaderAuthStatus is NOT run — this file is the only Sign In control (no #authBtn clash).
   */
  function paintBlank69LoggedOutSignIn() {
    var lb = document.getElementById('loginBox');
    if (!lb) return;
    lb.style.display = 'block';
    lb.innerHTML =
      '<button type="button" class="btn-primary" id="blank69HubSignInOnly">Sign In / Sign Up</button>';
    var btn = document.getElementById('blank69HubSignInOnly');
    if (!btn) return;
    btn.addEventListener('click', function (ev) {
      ev.preventDefault();
      try {
        sessionStorage.setItem('auth_returnTo', window.location.href);
      } catch (e1) { /* ignore */ }
      window.location.href = (window.location.origin || '') + '/login.html';
    });
  }

  async function syncAdminV10SecondHeader() {
    var wrap = document.getElementById('adminV10SecondHeaderUser');
    var nm = document.getElementById('adminV10SecondHeaderName');
    var sasEl = document.getElementById('adminV10SecondHeaderSas');
    var av = document.getElementById('adminV10SecondHeaderAvatar');
    if (!wrap || !nm || !sasEl || !av) return;
    wireAdminV10SecondHeaderLogout();
    try {
      /**
       * Always fetch session with raw fetch — not session.js checkSession/apiRequest (throws on some status codes
       * before JSON is read). Gate on valid only; user may be sparse but API still returns valid + sas_id.
       */
      var pathQs = '';
      try {
        if (window.location && window.location.pathname) {
          pathQs = '?path=' + encodeURIComponent(window.location.pathname || '/');
        }
      } catch (e0) { /* ignore */ }
      var pathP = (window.location && window.location.pathname) ? window.location.pathname : '';
      var useAdminSessionProxy = pathP === '/admin' || (pathP.indexOf('/admin/') === 0);
      /** Hub pages must use origin — never a relative window.API_BASE clobbered by another deferred script. */
      var rawBase = (window.API_BASE || (window.location && window.location.origin) || '').replace(/\/$/, '');
      var apiBase = /^https?:\/\//i.test(String(rawBase)) ? rawBase : String((window.location && window.location.origin) || '').replace(/\/$/, '');
      var sessionUrl = apiBase + (useAdminSessionProxy ? '/admin/api/session' : '/auth/session') + pathQs;
      var r = await fetch(sessionUrl, { credentials: 'include', cache: 'no-store' });
      var s = null;
      try {
        s = await r.json();
      } catch (eJ) {
        s = { valid: false };
      }
      if (!s || s.valid !== true) {
        wrap.setAttribute('hidden', '');
        av.removeAttribute('src');
        av.style.display = 'none';
        nm.textContent = '';
        sasEl.textContent = '';
        if (hubUsesIsolatedSessionJsHeader()) {
          paintBlank69LoggedOutSignIn();
        }
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
      var loginBoxHide = document.getElementById('loginBox');
      if (loginBoxHide) {
        loginBoxHide.style.display = 'none';
        try {
          loginBoxHide.innerHTML = '';
        } catch (eClr) { /* ignore */ }
      }
    } catch (e) {
      wrap.setAttribute('hidden', '');
      // Do not paint Sign In here — transient fetch/DOM errors are not logged-out.
    }
  }

  /** SPA index reads this after full navigation to / so logged-in users get the same landing as guests (not auto-profile). */
  function wireLogoHomeFlag() {
    document.addEventListener('click', function (e) {
      var a = e.target && e.target.closest && e.target.closest('a.js-go-home');
      if (!a) return;
      try { sessionStorage.setItem('sailingsa_home_from_logo', '1'); } catch (err) {}
    }, true);
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

  async function refreshBlankLandingHeader() {
    var skipSessionJsHeader = hubUsesIsolatedSessionJsHeader();
    /** blank69: never call updateHeaderAuthStatus — it injects #authBtn into #loginBox and duplicates v10 Logout. */
    if (!skipSessionJsHeader && typeof updateHeaderAuthStatus === 'function') {
      try {
        await updateHeaderAuthStatus();
      } catch (e) { /* ignore */ }
    }
    await syncAdminV10SecondHeader();
    if (skipSessionJsHeader && typeof checkSession === 'function' && typeof sailingSyncSuperAdminBodyClass === 'function') {
      try {
        var sBody = await checkSession();
        sailingSyncSuperAdminBodyClass(sBody);
      } catch (eSa) { /* ignore */ }
    }
  }

  window.refreshBlankLandingHeader = refreshBlankLandingHeader;

  function callRefresh() {
    var fn = window.refreshBlankLandingHeader;
    return typeof fn === 'function' ? fn() : Promise.resolve();
  }

  function watchHubHeaderAvatarSrc(id) {
    var avatar = document.getElementById(id);
    if (!avatar) return;
    var observer = new MutationObserver(function () {
      if (avatar.src && avatar.src !== window.location.href) {
        avatar.style.display = 'block';
      }
    });
    observer.observe(avatar, { attributes: true, attributeFilter: ['src'] });
  }

  function boot() {
    wireLogoHomeFlag();
    wireBlankHeaderNav();
    watchHubHeaderAvatarSrc('userAvatarImg');
    watchHubHeaderAvatarSrc('adminV10SecondHeaderAvatar');
    callRefresh().catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  window.setInterval(function () {
    callRefresh().catch(function () {});
  }, 12000);
})();
