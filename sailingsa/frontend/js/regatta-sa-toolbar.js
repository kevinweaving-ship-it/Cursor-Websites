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

    var mmSel = document.getElementById('regattaMmLiveFbFeed');
    var mmPrev = mmSel ? String(mmSel.value || 'OFF') : 'OFF';
    var mmSrc = document.getElementById('regattaMmFeedSource');
    var mmPage = document.getElementById('regattaMmFbPage');
    var mmUrls = document.getElementById('regattaMmClipUrls');

    function mmBody(onVal) {
      var body = { mm_live_fb_feed: onVal };
      if (mmSrc) body.feed_source = String(mmSrc.value || 'marine-megastore');
      if (mmPage) body.fb_page = String(mmPage.value || '').trim();
      if (mmUrls) {
        if (mmUrls.getAttribute('data-ready') === '1') body.clip_urls = String(mmUrls.value || '');
      }
      return body;
    }

    function saveMmFeed(v) {
      if (!rid || !mmSel) return;
      fetch('/api/super-admin/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mmBody(v))
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
            mmSel.value = mmPrev;
            var d = o.j && o.j.detail;
            alert(typeof d === 'string' ? d : JSON.stringify(d || o.raw || 'Save failed'));
            return;
          }
          if (o.j && Object.prototype.hasOwnProperty.call(o.j, 'mm_live_fb_feed')) {
            mmSel.value = o.j.mm_live_fb_feed ? 'ON' : 'OFF';
          }
          if (o.j && mmSrc && o.j.feed_source) mmSrc.value = o.j.feed_source;
          if (o.j && mmPage && Object.prototype.hasOwnProperty.call(o.j, 'fb_page')) mmPage.value = o.j.fb_page || '';
          if (o.j && mmUrls && Array.isArray(o.j.videos)) {
            mmUrls.value = o.j.videos.map(function (x) { return x && x.url ? x.url : ''; }).filter(Boolean).join('\n');
          }
          mmPrev = String(mmSel.value || 'OFF');
          try {
            window.location.reload();
          } catch (eRel) {}
        })
        .catch(function () {
          mmSel.value = mmPrev;
          alert('Network error.');
        });
    }

    if (mmSel && rid) {
      mmSel.addEventListener('change', function () {
        saveMmFeed(String(mmSel.value || 'OFF'));
      });
    }
    if (mmSrc && rid) {
      mmSrc.addEventListener('change', function () {
        if (mmSrc.value === 'marine-megastore' && mmPage && !String(mmPage.value || '').trim()) {
          mmPage.value = 'marin.megastoresa';
        }
        saveMmFeed(String(mmSel && mmSel.value || 'OFF'));
      });
    }
    function saveMmExtras() {
      saveMmFeed(String(mmSel && mmSel.value || 'OFF'));
    }
    if (mmPage && rid) mmPage.addEventListener('change', saveMmExtras);
    if (mmUrls && rid) {
      mmUrls.addEventListener('change', function () {
        mmUrls.setAttribute('data-ready', '1');
        saveMmExtras();
      });
    }

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
        if (!s) return;
        if (hubSel) {
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
        }
        if (mmSel) {
          mmSel.value = s.mm_live_fb_feed ? 'ON' : 'OFF';
          mmPrev = String(mmSel.value || 'OFF');
        }
        if (mmSrc && s.mm_feed_source) mmSrc.value = s.mm_feed_source;
        if (mmPage && s.mm_fb_page != null) mmPage.value = String(s.mm_fb_page || '');
        if (mmUrls && Array.isArray(s.mm_clip_urls)) {
          mmUrls.value = s.mm_clip_urls.join('\n');
          mmUrls.setAttribute('data-ready', '1');
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
