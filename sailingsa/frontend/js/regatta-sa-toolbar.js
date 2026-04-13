/**
 * Regatta standalone Super Admin bar: Public / SA toggle, News type → POST breaking-news-meta.
 * Loaded deferred so it cannot break WC fleet inline scripts. Single source for hub badge: GET results-summary sync.
 */
(function () {
  'use strict';

  function init() {
    var wrap = document.getElementById('regattaSaModeWrap');
    if (!wrap) return;

    var rid = (wrap.getAttribute('data-regatta-id') || '').trim();
    var lsKey = (wrap.getAttribute('data-ls-key') || '').trim();
    var i = document.getElementById('regattaSaEditToggle');
    var p = i && i.closest('.regatta-page');
    var hubSel = document.getElementById('regattaHubNewsType');
    if (!p || !i) return;

    function apply() {
      var o = i.checked;
      try {
        p.classList.toggle('regatta-page--super-admin-edit', o);
      } catch (e1) {}
      if (typeof window.__wcInitFleetAutocomplete === 'function') {
        try {
          window.__wcInitFleetAutocomplete();
        } catch (e2) {}
      }
      if (typeof window.__wcBindAllFleetSaves === 'function') {
        try {
          window.__wcBindAllFleetSaves();
        } catch (e3) {}
      }
      try {
        if (lsKey) localStorage.setItem(lsKey, o ? '1' : '0');
      } catch (e4) {}
    }

    function load() {
      try {
        var v = lsKey ? localStorage.getItem(lsKey) : null;
        if (v === '0') i.checked = false;
        else i.checked = true;
      } catch (e) {
        i.checked = true;
      }
      apply();
    }

    var hubPrev = hubSel ? String(hubSel.value || '') : '';

    load();
    setTimeout(function () {
      try {
        apply();
      } catch (eAp) {}
    }, 0);

    i.addEventListener('change', apply);
    window.addEventListener('pageshow', function (e) {
      if (e.persisted) load();
    });

    if (!hubSel || !rid) return;

    hubSel.addEventListener('change', function () {
      var v = (hubSel.value || '').trim();
      fetch('/api/super-admin/regatta/' + encodeURIComponent(rid) + '/breaking-news-meta', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blank_hub_news_badge_label: v || null })
      })
        .then(function (r) {
          return r.text().then(function (t) {
            var j = null;
            try {
              j = t ? JSON.parse(t) : null;
            } catch (e) {}
            return { ok: r.ok, j: j, raw: t };
          });
        })
        .then(function (o) {
          if (!o.ok) {
            hubSel.value = hubPrev;
            var d = o.j && o.j.detail;
            alert(typeof d === 'string' ? d : JSON.stringify(d || o.raw || 'Save failed'));
            return;
          }
          if (o.j && Object.prototype.hasOwnProperty.call(o.j, 'blank_hub_news_badge_label')) {
            var sv = o.j.blank_hub_news_badge_label;
            sv = sv == null ? '' : String(sv);
            var opts = hubSel.options;
            var oi,
              hit = -1;
            for (oi = 0; oi < opts.length; oi++) {
              if ((opts[oi].value || '') === sv) {
                hit = oi;
                break;
              }
            }
            if (hit >= 0) hubSel.selectedIndex = hit;
          }
          hubPrev = String(hubSel.value || '');
          try {
            localStorage.setItem('sailsa_hub_news_dirty', String(Date.now()));
          } catch (e) {}
        })
        .catch(function () {
          hubSel.value = hubPrev;
          alert('Network error.');
        });
    });

    fetch('/api/regatta/' + encodeURIComponent(rid) + '/results-summary', {
      credentials: 'include',
      cache: 'no-store'
    })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (s) {
        if (!s || !hubSel) return;
        var lab = String(s.blank_hub_news_badge_label || '').trim();
        var opts = hubSel.options;
        var oi,
          h = -1;
        for (oi = 0; oi < opts.length; oi++) {
          if ((opts[oi].value || '') === lab) {
            h = oi;
            break;
          }
        }
        if (h >= 0) {
          hubSel.selectedIndex = h;
          hubPrev = String(hubSel.value || '');
        }
      })
      .catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
