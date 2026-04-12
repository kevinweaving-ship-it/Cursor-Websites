/**
 * blank.html — same header behaviour as /admin/dashboard-v10 (menu overlay, session.js auth, v10 user row).
 * Load after /js/api.js and /js/session.js; DOM must include #menuBtn, #navMenuOverlay, #adminV10SecondHeaderUser, etc.
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
      var p = (window.location && window.location.pathname) ? window.location.pathname : '';
      var useAdminSessionProxy = p === '/admin' || (p.indexOf('/admin/') === 0);
      var sessionUrl = window.API_BASE + (useAdminSessionProxy ? '/admin/api/session' : '/auth/session') + pathQs;
      var r = await fetch(sessionUrl, { credentials: 'include', cache: 'no-store' });
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
    if (typeof updateHeaderAuthStatus === 'function') {
      try {
        await updateHeaderAuthStatus();
      } catch (e) { /* ignore */ }
    }
    await syncAdminV10SecondHeader();
  }

  window.refreshBlankLandingHeader = refreshBlankLandingHeader;

  function callRefresh() {
    var fn = window.refreshBlankLandingHeader;
    return typeof fn === 'function' ? fn() : Promise.resolve();
  }

  function boot() {
    wireLogoHomeFlag();
    wireBlankHeaderNav();
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
