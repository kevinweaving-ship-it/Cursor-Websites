/**
 * /admin/dashboard only — uses /admin/api/session and /admin/api/logout only.
 * Does not load session.js or blank-landing-header.js (no main-site auth UI).
 */
(function () {
  var path = (window.location && window.location.pathname) ? window.location.pathname : '';
  if (path.indexOf('/admin/dashboard') !== 0) return;

  var base = (window.API_BASE || (window.location && window.location.origin) || '').replace(/\/$/, '');

  function wireLogoHomeFlag() {
    document.addEventListener(
      'click',
      function (e) {
        var a = e.target && e.target.closest && e.target.closest('a.js-go-home');
        if (!a) return;
        try {
          sessionStorage.setItem('sailingsa_home_from_logo', '1');
        } catch (err) {}
      },
      true
    );
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

  var logoutWired = false;
  function wireLogoutOnce() {
    if (logoutWired) return;
    var b = document.getElementById('adminV10SecondHeaderLogoutBtn');
    if (!b) return;
    logoutWired = true;
    b.addEventListener('click', async function (e) {
      e.preventDefault();
      try {
        await fetch(base + '/admin/api/logout', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        });
      } catch (err) {}
      window.location.href = '/';
    });
  }

  async function syncAdminHeader() {
    var wrap = document.getElementById('adminV10SecondHeaderUser');
    var nm = document.getElementById('adminV10SecondHeaderName');
    var sasEl = document.getElementById('adminV10SecondHeaderSas');
    var av = document.getElementById('adminV10SecondHeaderAvatar');
    if (!wrap || !nm || !sasEl || !av) return;
    wireLogoutOnce();
    try {
      var pathQs = '?path=' + encodeURIComponent(path || '/');
      var r = await fetch(base + '/admin/api/session' + pathQs, {
        credentials: 'include',
        cache: 'no-store',
      });
      var s = await r.json().catch(function () {
        return null;
      });
      if (!s || !s.valid || !s.user) {
        wrap.setAttribute('hidden', '');
        av.removeAttribute('src');
        av.style.display = 'none';
        nm.textContent = '';
        sasEl.textContent = '';
        document.body.classList.add('admin-dash-auth-out');
        document.body.classList.remove('admin-dash-auth-in');
        return;
      }
      var u = s.user || {};
      var full = (u.full_name || [u.first_name, u.last_name].filter(Boolean).join(' ') || 'Member').trim();
      nm.textContent = full;
      sasEl.textContent = s.sas_id != null ? 'SAS ID: ' + String(s.sas_id) : 'SAS ID: —';
      if (s.sas_id != null) {
        av.src = base + '/assets/avatars/' + String(s.sas_id) + '.png';
        av.style.display = 'block';
        av.onerror = function () {
          av.style.display = 'none';
        };
      } else {
        av.removeAttribute('src');
        av.style.display = 'none';
      }
      wrap.removeAttribute('hidden');
      document.body.classList.remove('admin-dash-auth-out');
      document.body.classList.add('admin-dash-auth-in');
    } catch (e) {
      wrap.setAttribute('hidden', '');
      document.body.classList.add('admin-dash-auth-out');
      document.body.classList.remove('admin-dash-auth-in');
    }
  }

  function htmlEncode(s) {
    return String(s == null ? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  var logPollId = null;
  function stopLogPoll() {
    if (logPollId) {
      clearInterval(logPollId);
      logPollId = null;
    }
  }

  function card() {
    return document.querySelector('[data-run-scrape-key]');
  }

  function showPanel(title) {
    var p = document.getElementById('adminDashboardRegistryPanel');
    var t = document.getElementById('adminDashboardRegistryPanelTitle');
    if (t) t.textContent = title || '';
    if (p) p.hidden = false;
  }

  function panelBody() {
    return document.getElementById('adminDashboardRegistryPanelBody');
  }

  function panelStatus() {
    return document.getElementById('adminDashboardRegistryStatus');
  }

  function clearBody() {
    var st = panelStatus();
    if (st) {
      st.textContent = '';
      st.hidden = true;
    }
    var b = panelBody();
    if (b) b.innerHTML = '';
  }

  function hidePanel() {
    var p = document.getElementById('adminDashboardRegistryPanel');
    if (p) p.hidden = true;
    stopLogPoll();
    clearBody();
  }

  async function refreshLog() {
    var el = card();
    var file = (el && el.getAttribute('data-panel-log-file')) || 'sas-id-registry-scrape.log';
    var r = await fetch(
      base + '/admin/api/panel/log-text?file=' + encodeURIComponent(file) + '&t=' + Date.now(),
      { credentials: 'include', cache: 'no-store' }
    );
    var j = await r.json().catch(function () {
      return {};
    });
    var m = panelBody();
    if (!m) return;
    var text = j && j.ok && j.text ? j.text : (j.detail || j.error || '(no log text)');
    if (typeof text !== 'string') text = String(text);
    m.innerHTML = '<pre class="admin-dashboard-registry-log">' + htmlEncode(text) + '</pre>';
    var pre = m.querySelector('pre');
    if (pre) pre.scrollTop = pre.scrollHeight;
  }

  async function onRecords(e) {
    e.preventDefault();
    stopLogPoll();
    showPanel('Last 5 SAS IDs');
    clearBody();
    var m = panelBody();
    if (m) m.innerHTML = '<p>Loading…</p>';
    try {
      var r = await fetch(base + '/admin/api/panel/sas-registry-recent?limit=5', {
        credentials: 'include',
        cache: 'no-store',
      });
      var j = await r.json();
      if (!m) return;
      if (j && j.ok && j.rows) {
        var rows = j.rows;
        var html =
          '<div class="table-container"><table class="table admin-dashboard-registry-table"><thead><tr>' +
          '<th>First name</th><th>Last name</th><th>SAS ID</th><th>Year born</th></tr></thead><tbody>';
        for (var i = 0; i < rows.length; i++) {
          var row = rows[i] || {};
          html +=
            '<tr><td>' +
            htmlEncode(row.first_name) +
            '</td><td>' +
            htmlEncode(row.last_name) +
            '</td><td>' +
            htmlEncode(row.sas_id) +
            '</td><td>' +
            (row.year_born != null ? htmlEncode(row.year_born) : '—') +
            '</td></tr>';
        }
        if (!rows.length) html += '<tr><td colspan="4">No rows.</td></tr>';
        html += '</tbody></table></div>';
        m.innerHTML = html;
      } else {
        m.innerHTML = '<p>' + htmlEncode(j.error || 'Failed.') + '</p>';
      }
    } catch (err) {
      var mb = panelBody();
      if (mb) mb.innerHTML = '<p>' + htmlEncode(err.message || '') + '</p>';
    }
  }

  async function onManual(e) {
    e.preventDefault();
    stopLogPoll();
    showPanel('Manual run');
    clearBody();
    var statusEl = panelStatus();
    if (statusEl) {
      statusEl.hidden = false;
      statusEl.textContent = '…';
    }
    var key = (card() && card().getAttribute('data-run-scrape-key')) || 'sas_registry';
    try {
      var r = await fetch(base + '/admin/api/run-scrape', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scrape: key }),
      });
      if (r.status === 403) {
        if (statusEl) statusEl.textContent = 'Live host only.';
        return;
      }
      var j = await r.json().catch(function () {
        return {};
      });
      if (!r.ok) {
        var msg = j.detail != null ? j.detail : j.error;
        if (typeof msg !== 'string') msg = msg ? JSON.stringify(msg) : 'Failed';
        if (statusEl) statusEl.textContent = msg;
        return;
      }
      await refreshLog();
      logPollId = window.setInterval(function () {
        refreshLog().catch(function () {});
      }, 2000);
    } catch (err) {
      if (statusEl) statusEl.textContent = err.message || String(err);
    }
  }

  function wireUi() {
    var rec = document.querySelector('[data-admin-dash-records]');
    var man = document.querySelector('[data-admin-dash-manual]');
    if (rec) rec.addEventListener('click', onRecords);
    if (man) man.addEventListener('click', onManual);
    var c = document.getElementById('adminDashboardRegistryPanelClose');
    if (c) c.addEventListener('click', hidePanel);
  }

  function boot() {
    wireLogoHomeFlag();
    wireBlankHeaderNav();
    syncAdminHeader().catch(function () {});
    window.setInterval(function () {
      syncAdminHeader().catch(function () {});
    }, 12000);
    wireUi();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
