/* /sailors — landing-style fuzzy search, active sailors only, stats cards. */
(function (global) {
  'use strict';
  if (global.__ssaHubSailorDirectoryLoaded) return;
  global.__ssaHubSailorDirectoryLoaded = true;

  var RESULTS_ID = 'sailor-directory-results';
  var SEARCH_ID = 'events-dashboard-search';
  var SEARCH_LIMIT = 500;
  var DISPLAY_CAP = 30;
  var DEBOUNCE_MS = 220;

  var searchAbort = null;
  var searchDebounce = null;

  function getResultsEl() {
    return document.getElementById(RESULTS_ID);
  }

  function sortSailorList(list, q) {
    var qn = String(q || '').toLowerCase().replace(/\s+/g, ' ').trim();
    var tokens = qn.split(' ').filter(Boolean);
    function score(row) {
      if (row._search_rel != null && row._search_rel !== '') {
        var rel = parseInt(row._search_rel, 10);
        if (!isNaN(rel)) return rel;
      }
      var fn = String(row.first_names || row.first_name || '').toLowerCase();
      var ln = String(row.surname || row.last_name || '').toLowerCase();
      var full = (fn + ' ' + ln).replace(/\s+/g, ' ').trim();
      if (full === qn) return 0;
      if (qn && full.indexOf(qn) === 0) return 1;
      if (qn && full.indexOf(qn) !== -1) return 2;
      var firstTok = tokens[0] || '';
      var lastTok = tokens[tokens.length - 1] || '';
      if (tokens.length >= 2 && fn.indexOf(firstTok) === 0 && ln.indexOf(lastTok) === 0) return 3;
      if (lastTok && ln.indexOf(lastTok) === 0) return 4;
      if (firstTok && fn.indexOf(firstTok) === 0) return 5;
      return 9;
    }
    return (list || []).slice().sort(function (a, b) {
      var sa = score(a);
      var sb = score(b);
      if (sa !== sb) return sa - sb;
      var la = String(a.surname || a.last_name || '').toLowerCase();
      var lb = String(b.surname || b.last_name || '').toLowerCase();
      if (la !== lb) return la.localeCompare(lb);
      var fa = String(a.first_names || a.first_name || '').toLowerCase();
      var fb = String(b.first_names || b.first_name || '').toLowerCase();
      if (fa !== fb) return fa.localeCompare(fb);
      return String(a.sas_id || a.sa_sailing_id || '').localeCompare(String(b.sas_id || b.sa_sailing_id || ''));
    });
  }

  function scopedDev1Doc(root) {
    return {
      getElementById: function (id) {
        try {
          return root.querySelector('[id="' + String(id).replace(/"/g, '') + '"]');
        } catch (e) {
          return null;
        }
      },
      querySelector: function (sel) {
        return root.querySelector(sel);
      },
      querySelectorAll: function (sel) {
        return root.querySelectorAll(sel);
      },
      createElement: function (t) {
        return window.document.createElement(t);
      },
      createTextNode: function (t) {
        return window.document.createTextNode(t);
      },
      addEventListener: function (t, fn, opt) {
        return window.document.addEventListener(t, fn, opt);
      },
      removeEventListener: function (t, fn, opt) {
        return window.document.removeEventListener(t, fn, opt);
      },
      get body() {
        return window.document.body;
      },
      get documentElement() {
        return window.document.documentElement;
      },
      get head() {
        return window.document.head;
      },
    };
  }

  function runDev1Scripts(root, codes) {
    var scoped = scopedDev1Doc(root);
    codes.forEach(function (code) {
      if (!code || !String(code).trim()) return;
      try {
        new Function('document', 'window', code)(scoped, global);
      } catch (e) {
        try {
          console.warn('dev1 card script', e);
        } catch (_) {}
      }
    });
  }

  function hideClaimUi(slot) {
    if (!slot) return;
    slot.querySelectorAll('.sa-claim-banner, .sailor-claim-cta, #dev1-claim-banner, #dev1-claim-slot').forEach(function (el) {
      el.style.display = 'none';
      el.setAttribute('aria-hidden', 'true');
    });
  }

  function hasStatsCard(slot) {
    if (!slot) return false;
    var ne = slot.querySelector('#dev1-next-event-slot');
    if (ne && ne.textContent && ne.textContent.replace(/\s+/g, '').length > 20) return true;
    var mid = slot.querySelector('#dev1-header-mid-slot');
    return !!(mid && mid.children && mid.children.length);
  }

  function mountDev1Card(slot, html) {
    var box = document.createElement('div');
    box.innerHTML = html;
    var lock = box.querySelector('#dev1-viewport-locks');
    if (lock) {
      if (!document.getElementById('dev1-viewport-locks')) {
        document.head.appendChild(lock);
      } else if (lock.parentNode) {
        lock.parentNode.removeChild(lock);
      }
    }
    var codes = [];
    box.querySelectorAll('script').forEach(function (sc) {
      if (!sc.src) codes.push(sc.textContent || '');
      if (sc.parentNode) sc.parentNode.removeChild(sc);
    });
    slot.innerHTML = '';
    while (box.firstChild) slot.appendChild(box.firstChild);
    runDev1Scripts(slot, codes);
    hideClaimUi(slot);
    return hasStatsCard(slot);
  }

  function renderSailorList(list, q, gen) {
    var sailorSearchResults = getResultsEl();
    if (!sailorSearchResults) return Promise.resolve();
    list = sortSailorList(list, q);
    var total = list.length;
    if (total > DISPLAY_CAP) list = list.slice(0, DISPLAY_CAP);

    sailorSearchResults.innerHTML = '';
    sailorSearchResults.style.display = 'flex';
    if (!list.length) {
      sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">No sailors found.</div>';
      return Promise.resolve();
    }
    if (total > DISPLAY_CAP) {
      var note = document.createElement('p');
      note.className = 'sailor-directory-hint';
      note.style.cssText = 'color:#64748b;font-size:0.9rem;margin:0 0 0.5rem 0;';
      note.textContent = 'Showing top ' + DISPLAY_CAP + ' of ' + total + ' matches — type more to narrow.';
      sailorSearchResults.appendChild(note);
    }

    var slots = [];
    list.forEach(function (row) {
      var sid = row.sa_sailing_id != null ? String(row.sa_sailing_id) : String(row.sas_id || row.sa_id || '');
      var wrap = document.createElement('div');
      wrap.className = 'ssa-dev1-inject';
      wrap.setAttribute('role', 'listitem');
      wrap.dataset.sasId = sid;
      wrap.innerHTML = '<div class="profile-card" style="cursor:default;">Loading…</div>';
      sailorSearchResults.appendChild(wrap);
      slots.push({ wrap: wrap, sid: sid });
    });

    function fetchOne(item) {
      if (gen !== (global.__sailorDirectoryGen || 0)) return Promise.resolve();
      if (!item || item.wrap.getAttribute('data-card-loaded') === '1') return Promise.resolve();
      item.wrap.setAttribute('data-card-loaded', '1');
      if (!item.sid) {
        item.wrap.remove();
        return Promise.resolve();
      }
      global.__ssaDev1CardCache = global.__ssaDev1CardCache || {};
      var cached = global.__ssaDev1CardCache[item.sid];
      if (cached) {
        if (!mountDev1Card(item.wrap, cached)) item.wrap.remove();
        return Promise.resolve();
      }
      return fetch('/dev-1?embed=1&no_claim=1&sas_id=' + encodeURIComponent(item.sid), { credentials: 'same-origin' })
        .then(function (r) {
          return r.text();
        })
        .then(function (html) {
          if (gen !== (global.__sailorDirectoryGen || 0)) return;
          global.__ssaDev1CardCache[item.sid] = html;
          if (!mountDev1Card(item.wrap, html)) item.wrap.remove();
        })
        .catch(function () {
          if (gen !== (global.__sailorDirectoryGen || 0)) return;
          item.wrap.remove();
        });
    }

    function loadRange(start, end, conc) {
      var i = start;
      var stop = Math.min(end, slots.length);
      function worker() {
        if (gen !== (global.__sailorDirectoryGen || 0)) return Promise.resolve();
        if (i >= stop) return Promise.resolve();
        var item = slots[i++];
        return fetchOne(item).then(worker);
      }
      var pool = [];
      var n = Math.min(conc, Math.max(0, stop - start));
      for (var k = 0; k < n; k++) pool.push(worker());
      return Promise.all(pool).then(function () {
        if (gen !== (global.__sailorDirectoryGen || 0)) return;
        if (!sailorSearchResults.querySelector('.ssa-dev1-inject')) {
          sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">No sailors with results found.</div>';
        }
      });
    }

    if (global.__ssaSailorDirectoryIO) {
      try {
        global.__ssaSailorDirectoryIO.disconnect();
      } catch (_) {}
      global.__ssaSailorDirectoryIO = null;
    }
    var topN = Math.min(2, slots.length);
    var topLoad = loadRange(0, topN, 2);
    if (slots.length > topN && typeof IntersectionObserver === 'function') {
      var io = new IntersectionObserver(
        function (entries) {
          if (gen !== (global.__sailorDirectoryGen || 0)) return;
          entries.forEach(function (en) {
            if (!en.isIntersecting) return;
            io.unobserve(en.target);
            var item = null;
            for (var s = topN; s < slots.length; s++) {
              if (slots[s].wrap === en.target) {
                item = slots[s];
                break;
              }
            }
            if (item) fetchOne(item);
          });
        },
        { root: null, rootMargin: '400px 0px', threshold: 0.01 }
      );
      global.__ssaSailorDirectoryIO = io;
      for (var s = topN; s < slots.length; s++) io.observe(slots[s].wrap);
    } else if (slots.length > topN) {
      loadRange(topN, slots.length, 1);
    }
    return topLoad;
  }

  function clearResults() {
    var box = getResultsEl();
    if (searchAbort) {
      try {
        searchAbort.abort();
      } catch (_) {}
      searchAbort = null;
    }
    global.__sailorDirectoryGen = (global.__sailorDirectoryGen || 0) + 1;
    if (box) {
      box.innerHTML = '';
      box.style.display = 'none';
    }
  }

  function runSailorSearch() {
    var inp = document.getElementById(SEARCH_ID);
    var q = inp ? (inp.value || '').trim() : '';
    var box = getResultsEl();

    if (!q) {
      clearResults();
      return;
    }
    if (q.length < 2) {
      if (searchAbort) {
        try {
          searchAbort.abort();
        } catch (_) {}
        searchAbort = null;
      }
      if (box) {
        box.style.display = 'flex';
        box.innerHTML = '<div class="profile-card" style="cursor:default;">Type at least 2 characters to search.</div>';
      }
      return;
    }

    if (searchAbort) searchAbort.abort();
    searchAbort = new AbortController();
    global.__sailorDirectoryGen = (global.__sailorDirectoryGen || 0) + 1;
    var myGen = global.__sailorDirectoryGen;

    if (box) {
      box.style.display = 'flex';
      box.innerHTML = '<div class="profile-card" style="cursor:default;">Searching…</div>';
    }

    var api = global.API_BASE || '';
    var url =
      api +
      '/api/search?q=' +
      encodeURIComponent(q) +
      '&hub=1&active=1&limit=' +
      SEARCH_LIMIT;

    fetch(url, { credentials: 'same-origin', signal: searchAbort.signal })
      .then(function (r) {
        return r.ok ? r.json() : [];
      })
      .then(function (list) {
        if (myGen !== (global.__sailorDirectoryGen || 0)) return;
        return renderSailorList(Array.isArray(list) ? list : [], q, myGen);
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        if (myGen !== (global.__sailorDirectoryGen || 0)) return;
        if (box) box.innerHTML = '<div class="profile-card" style="cursor:default;color:#c00;">Search failed. Try again.</div>';
      });
  }

  function initSailorDirectory() {
    var inp = document.getElementById(SEARCH_ID);
    if (!inp) return;
    inp.setAttribute('placeholder', 'Search active sailors…');
    inp.setAttribute('aria-label', 'Search active sailors');
    inp.addEventListener('input', function () {
      clearTimeout(searchDebounce);
      var q = (inp.value || '').trim();
      if (q.length >= 2) {
        var box = getResultsEl();
        if (box) {
          box.style.display = 'flex';
          box.innerHTML = '<div class="profile-card" style="cursor:default;">Searching…</div>';
        }
      }
      searchDebounce = setTimeout(runSailorSearch, DEBOUNCE_MS);
    });
    clearResults();
  }

  global.__ssaSailorDirectoryRunSearch = runSailorSearch;
  global.__ssaSailorDirectoryInit = initSailorDirectory;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSailorDirectory);
  } else {
    initSailorDirectory();
  }
})(typeof window !== 'undefined' ? window : this);
