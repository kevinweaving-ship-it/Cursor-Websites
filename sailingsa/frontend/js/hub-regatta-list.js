/* Hub regatta list — extracted from landing (renderRegattasTable + applyRegattaFilter). */
(function(global) {
  'use strict';
  if (global.__ssaHubRegattaListLoaded) return;
  global.__ssaHubRegattaListLoaded = true;
        function parseRegattaSearchQuery(input) {
            var trimmed = (input || '').trim();
            if (!trimmed) return { q: '', year: null };
            var year = null;
            var words = trimmed.split(/\s+/);
            var rest = [];
            for (var i = 0; i < words.length; i++) {
                if (/^\d{4}$/.test(words[i])) {
                    var y = parseInt(words[i], 10);
                    if (y >= 1900 && y <= 2099 && (words[i].indexOf('19') === 0 || words[i].indexOf('20') === 0)) {
                        year = y;
                        continue;
                    }
                }
                rest.push(words[i]);
            }
            var q = rest.join(' ').trim();
            return { q: q, year: year };
        }
        var SA_REGATTA_SEARCH_RESTORE_KEY = 'sa:regattaSearchRestore';
        function _saSaveRegattaSearchState(fromRid) {
            try {
                var inp = document.getElementById('temp-landing-regatta-input');
                sessionStorage.setItem(SA_REGATTA_SEARCH_RESTORE_KEY, JSON.stringify({
                    mode: 'regatta',
                    q: (inp && inp.value) ? String(inp.value).trim() : '',
                    scrollY: window.scrollY || 0,
                    fromRid: fromRid || '',
                    ts: Date.now()
                }));
            } catch (_) {}
        }
        function _saTryRestoreRegattaSearchState() {
            try {
                var raw = sessionStorage.getItem(SA_REGATTA_SEARCH_RESTORE_KEY);
                if (!raw) return;
                var st = JSON.parse(raw);
                if (!st || st.mode !== 'regatta') return;
                if (st.ts && Date.now() - st.ts > 1800000) {
                    sessionStorage.removeItem(SA_REGATTA_SEARCH_RESTORE_KEY);
                    return;
                }
                sessionStorage.removeItem(SA_REGATTA_SEARCH_RESTORE_KEY);
                window.__saRegattaSearchRestorePending = {
                    scrollY: st.scrollY || 0,
                    fromRid: st.fromRid || ''
                };
                var inp = document.getElementById('temp-landing-regatta-input');
                if (inp != null && st.q != null) inp.value = st.q;
                if (typeof setSearchMode === 'function') setSearchMode('regatta', true);
                else if (typeof window.setSearchMode === 'function') window.setSearchMode('regatta', true);
            } catch (_) {}
        }
        function _saApplyRegattaSearchRestoreScroll() {
            var st = window.__saRegattaSearchRestorePending;
            if (!st) return;
            window.__saRegattaSearchRestorePending = null;
            requestAnimationFrame(function() {
                requestAnimationFrame(function() {
                    if (st.scrollY) window.scrollTo(0, st.scrollY);
                });
            });
        }
        if (!window.__saRegattaSearchNavBound) {
            window.__saRegattaSearchNavBound = true;
            document.addEventListener('click', function(e) {
                try {
                    if ((global.searchMode || 'sailor') !== 'regatta' && global.__ssaDirectoryRegattas !== true) return;
                    var a = e.target && e.target.closest ? e.target.closest('#public-regattas-list a[href^="/regatta/"]') : null;
                    if (!a) return;
                    var href = a.getAttribute('href') || '';
                    var m = href.match(/^\/regatta\/([^?#]+)/);
                    _saSaveRegattaSearchState(m ? decodeURIComponent(m[1]) : '');
                } catch (_) {}
            }, true);
        }
        function renderRegattasTable(regattas, searchQuery) {
            var publicRegattasList = document.getElementById('public-regattas-list');
            if (!publicRegattasList) return;
            if (!regattas || regattas.length === 0) {
                publicRegattasList.innerHTML = '<p>No regattas match.</p>';
                return;
            }
            var esc = function(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };

            function hostLocationLabel(r) {
                if (r.host_location && String(r.host_location).trim()) return String(r.host_location).trim();
                var abbr = (r.host_club_abbrev || r.host_club_code || '').trim();
                var full = (r.host_club_fullname || r.host_club_name || '').trim();
                if (abbr && full && abbr.toLowerCase() !== full.toLowerCase()) return abbr + ' - ' + full;
                if (abbr) return abbr;
                if (full) return full;
                return 'N/A';
            }

            function ensureRegattaListCss() {
                if (document.getElementById('sa-home-regatta-list-style')) return;
                var css = '' +
                    '.sa-home-regatta-wrap{margin:0;}' +
                    '.sa-home-regatta-list{display:flex;flex-direction:column;gap:10px;}' +
                    '.sa-home-regatta-card{background:#fff;border:2px solid #8aa2c6;border-radius:6px;box-shadow:0 2px 3px rgba(15,23,42,.06);padding:10px 12px 10px;display:flex;flex-direction:column;gap:8px;overflow:hidden;box-sizing:border-box;}' +
                    '.sa-home-regatta-sep{display:none;}' +
                    '.sa-home-regatta-top{display:grid;grid-template-columns:104px minmax(0,1fr) minmax(200px,252px) auto;grid-template-areas:"logo main host actions";gap:14px;align-items:center;}' +
                    '.sa-home-regatta-event-logo-link{grid-area:logo;display:flex;align-items:center;justify-content:flex-start;text-decoration:none;line-height:0;min-width:0;justify-self:start;align-self:center;}' +
                    '.sa-home-regatta-event-logo{display:block;width:96px;height:68px;max-width:96px;max-height:68px;object-fit:contain;object-position:center;border:none;border-radius:0;background:transparent;flex:0 0 auto;padding:0;}' +
                    '.sa-home-regatta-top-main{grid-area:main;min-width:0;}' +
                    '.sa-home-regatta-title{font-size:15px;font-weight:900;color:#142c78;line-height:1.15;margin:0;letter-spacing:-.01em;}' +
                    '.sa-home-regatta-meta{display:flex;flex-wrap:wrap;gap:8px;color:#5b6780;font-size:11.5px;margin-top:6px;}' +
                    '.sa-home-regatta-meta-pill{display:inline-flex;align-items:center;gap:5px;padding:0;border:none;border-radius:0;background:transparent;font-weight:700;white-space:nowrap;position:relative;}' +
                    '.sa-home-regatta-meta-ico{display:inline-flex;align-items:center;justify-content:center;width:13px;height:13px;color:#60708b;}' +
                    '.sa-home-regatta-meta-pill + .sa-home-regatta-meta-pill{padding-left:10px;}' +
                    '.sa-home-regatta-meta-pill + .sa-home-regatta-meta-pill:before{content:"";position:absolute;left:0;top:2px;bottom:2px;width:1px;background:#cbd5e1;}' +
                    '.sa-home-regatta-host{grid-area:host;display:flex;align-items:center;gap:10px;min-width:0;color:inherit;text-decoration:none;}' +
                    'a.sa-home-regatta-host:hover .sa-home-regatta-host-code,a.sa-home-regatta-host:hover .sa-home-regatta-host-name{color:#0b3d91;text-decoration:underline;}' +
                    '.sa-home-regatta-host-logo{display:block;width:84px;height:44px;object-fit:contain;border:none;border-radius:0;background:transparent;flex:0 0 auto;padding:0;}' +
                    '.sa-home-regatta-host-text{display:flex;flex-direction:column;gap:2px;min-width:0;}' +
                    '.sa-home-regatta-host-code{font-weight:900;color:#21356b;font-size:14px;line-height:1.05;}' +
                    '.sa-home-regatta-host-name{color:#475569;font-size:11px;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px;}' +
                    '.sa-home-regatta-actions{grid-area:actions;display:flex;gap:8px;align-items:center;justify-content:flex-end;}' +
                    '.sa-home-regatta-single-class{display:inline-flex;align-items:center;justify-content:center;line-height:0;text-decoration:none;flex:0 0 auto;}' +
                    '.sa-home-regatta-single-class .sa-home-regatta-chip-logo{width:52px;height:28px;max-width:52px;visibility:visible;}' +
                    '.sa-home-regatta-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;padding:9px 14px;border-radius:6px;border:1px solid #a5d7de;background:#f9ffff;color:#0f6d7a;font-weight:900;font-size:12px;text-decoration:none;white-space:nowrap;min-width:126px;box-shadow:0 1px 0 rgba(15,109,122,.08);}' +
                    '.sa-home-regatta-btn-ico{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;color:#0f6d7a;}' +
                    '.sa-home-regatta-children{margin:0;border:1px solid #dbe3ef;border-radius:4px;background:#fff;padding:0;display:flex;flex-direction:column;gap:0;overflow:hidden;}' +
                    '.sa-home-regatta-children-head{display:flex;flex-direction:row;flex-wrap:wrap;align-items:center;gap:6px 10px;padding:8px 12px;background:#eff5ff;border-bottom:none;}' +
                    '.sa-home-regatta-children-note{color:#334155;font-size:11px;font-weight:700;white-space:nowrap;flex:0 0 auto;line-height:1.2;}' +
                    '.sa-home-regatta-children-chips{display:inline-flex;flex-wrap:wrap;align-items:center;gap:4px 6px;min-width:0;flex:1 1 auto;}' +
                    '.sa-home-regatta-children-chip{display:inline-flex;align-items:center;gap:3px;padding:2px 1px;border:none;border-radius:0;background:transparent;text-decoration:none;line-height:1;min-width:0;min-height:0;color:#334155;}' +
                    '.sa-home-regatta-chip-logo{display:block;width:48px;height:22px;max-width:48px;object-fit:contain;border:none;border-radius:0;background:transparent;flex:0 0 auto;padding:0;}' +
                    '.sa-home-regatta-chip-n{display:inline-flex;align-items:center;font-size:11px;font-weight:800;color:#334155;line-height:1;white-space:nowrap;flex:0 0 auto;}' +
                    '.sa-home-regatta-chip-text{display:inline-flex;align-items:center;font-size:11px;font-weight:800;color:#21356b;line-height:1.1;white-space:nowrap;flex:0 0 auto;}' +
                    '.sa-home-regatta-children-chip.has-logo .sa-home-regatta-chip-text{display:none;}' +
                    '.sa-home-regatta-children-chip.no-logo .sa-home-regatta-chip-logo{display:none;}' +
                    '.sa-home-regatta-chip-label{display:none;}' +
                    '.sa-home-regatta-chip-label.is-fallback{display:none;}' +
                    '@media (max-width: 480px){' +
                    '.sa-home-regatta-card{padding:10px 10px 10px;border-radius:6px;}' +
                    '.sa-home-regatta-top{grid-template-columns:82px minmax(0,1fr);grid-template-areas:"logo main" "logo host" "actions actions";gap:8px 10px;align-items:start;}' +
                    '.sa-home-regatta-event-logo-link{justify-self:start;align-self:start;}' +
                    '.sa-home-regatta-event-logo{width:78px;max-width:78px;height:58px;max-height:58px;object-fit:contain;object-position:center;padding:0;border-radius:0;}' +
                    '.sa-home-regatta-title{font-size:14px;}' +
                    '.sa-home-regatta-meta{gap:6px;margin-top:5px;}' +
                    '.sa-home-regatta-meta-pill{font-size:11px;}' +
                    '.sa-home-regatta-host{gap:8px;}' +
                    '.sa-home-regatta-host-logo{width:76px;height:36px;padding:0;border-radius:0;}' +
                    '.sa-home-regatta-host-name{max-width:220px;}' +
                    '.sa-home-regatta-actions{width:100%;justify-content:flex-end;gap:10px;}' +
                    '.sa-home-regatta-single-class .sa-home-regatta-chip-logo{width:46px;height:24px;max-width:46px;}' +
                    '.sa-home-regatta-btn{flex:1;min-width:0;padding:9px 10px;}' +
                    '.sa-home-regatta-children-head{padding:6px 10px;gap:4px 6px;}' +
                    '.sa-home-regatta-children-note{font-size:10px;}' +
                    '.sa-home-regatta-children-chips{gap:3px 5px;}' +
                    '.sa-home-regatta-chip-logo{width:42px;height:19px;max-width:42px;}' +
                    '.sa-home-regatta-chip-n{font-size:10px;}' +
                    '}';
                var st = document.createElement('style');
                st.id = 'sa-home-regatta-list-style';
                st.textContent = css;
                document.head.appendChild(st);
            }

            function dateShort(d) {
                var s = (d || '').toString().slice(0, 10);
                if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return s || 'N/A';
                var y = parseInt(s.slice(0, 4), 10);
                var m = parseInt(s.slice(5, 7), 10) - 1;
                var day = parseInt(s.slice(8, 10), 10);
                var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                if (m < 0 || m > 11 || !day || !y) return s;
                return day + ' ' + months[m] + ' ' + y;
            }

            function formatParentDate(r) {
                var sd = (r.start_date || '').toString().slice(0, 10);
                var ed = (r.end_date || '').toString().slice(0, 10);
                var asAt = (r.as_at_time || '').toString().slice(0, 10);
                if (!sd && !ed && asAt) return dateShort(asAt);
                if (!sd && !ed) return 'N/A';
                if (sd && ed && sd !== ed) return dateShort(sd) + ' → ' + dateShort(ed);
                return dateShort(ed || sd);
            }

            function safeImg(src, cls) {
                if (!src) return null;
                var img = document.createElement('img');
                img.className = cls;
                img.loading = 'lazy';
                img.decoding = 'async';
                img.alt = '';
                img.src = src;
                img.onerror = function() { try { img.style.display = 'none'; } catch (_) {} };
                return img;
            }

            function purgeStaleRegattaLogoCache() {
                try {
                    if (window.__saRegattaLogoV4Purged) return;
                    window.__saRegattaLogoV4Purged = true;
                    for (var i = localStorage.length - 1; i >= 0; i--) {
                        var k = localStorage.key(i);
                        if (k && (k.indexOf('sa:regattaLogo:event:v3:') === 0 || k.indexOf('sa:regattaLogo:child:v3:') === 0)) {
                            localStorage.removeItem(k);
                        }
                    }
                } catch (_) {}
            }
            purgeStaleRegattaLogoCache();

            function resolveEventLogoFromRegattaPage(regattaId, forceRefresh) {
                var rid = String(regattaId || '').trim();
                if (!rid) return Promise.resolve(null);
                window.__saRegattaEventLogoCache = window.__saRegattaEventLogoCache || {};
                if (!forceRefresh && window.__saRegattaEventLogoCache[rid]) return window.__saRegattaEventLogoCache[rid];
                try {
                    var k = 'sa:regattaLogo:event:v4:' + rid;
                    if (forceRefresh) localStorage.removeItem(k);
                    var cached = forceRefresh ? '' : localStorage.getItem(k);
                    if (cached && cached.trim()) {
                        window.__saRegattaEventLogoCache[rid] = Promise.resolve(cached.trim());
                        return window.__saRegattaEventLogoCache[rid];
                    }
                } catch (_) {}
                var p = fetch('/regatta/' + encodeURIComponent(rid), { credentials: 'same-origin', cache: 'no-store' })
                    .then(function(r) { return r.ok ? r.text() : ''; })
                    .then(function(html) {
                        if (!html) return null;
                        try {
                            var doc = new DOMParser().parseFromString(html, 'text/html');
                            var img = doc.querySelector('.regatta-header-logo-col img.regatta-header-left-logo-img, .regatta-header-logo-col img.regatta-header-logo-img');
                            var src = img ? (img.getAttribute('src') || '').trim() : '';
                            if (src) { try { localStorage.setItem('sa:regattaLogo:event:v4:' + rid, src); } catch (_) {} }
                            return src || null;
                        } catch (_) {
                            return null;
                        }
                    })
                    .catch(function() { return null; });
                window.__saRegattaEventLogoCache[rid] = p;
                return p;
            }

            function isRegattaSearchClassFleetChip(ch, parentRid) {
                var cid = String((ch && (ch.regatta_id != null ? ch.regatta_id : ch.id)) || '').trim();
                var pid = String(parentRid || '').trim();
                var tail = '';
                if (pid && cid.indexOf(pid + '-') === 0) tail = cid.slice(pid.length + 1).toLowerCase();
                var fl = String((ch && (ch.fleet_label || ch.search_label)) || '').trim().toLowerCase().replace(/\s+fleet$/i, '').trim();
                if (tail === 'overall' || tail === 'overall-results') return false;
                if (tail.replace(/-/g, ' ') === 'overall' || tail.replace(/-/g, ' ') === 'overall results') return false;
                if (fl === 'overall' || fl === 'overall results') return false;
                return true;
            }

            function normalizeArtworkPath(path) {
                try {
                    return decodeURIComponent(String(path || '').split('?')[0]).toLowerCase();
                } catch (_) {
                    return String(path || '').split('?')[0].toLowerCase();
                }
            }
            function isEventLogoArtworkPath(path) {
                return normalizeArtworkPath(path).indexOf('/artwork/event logo/') !== -1;
            }
            function classNameFromLogoFilename(path) {
                var base = String(path || '').split('/').pop() || '';
                base = base.replace(/\.[a-z0-9]+$/i, '');
                base = base.replace(/[-_]?(class[-_]?logo|event[-_]?logo|logo)$/i, '');
                return base.replace(/-/g, ' ').replace(/_/g, ' ').trim();
            }
            function classSlugFromLogoLabel(label) {
                return String(label || '').trim().toLowerCase()
                    .replace(/\s+/g, '-')
                    .replace(/[^a-z0-9.-]/g, '')
                    .replace(/^-+|-+$/g, '');
            }
            function eventLogoSeriesSlugFromContext(src, regattaId, regattaName) {
                var fn = String(src || '').split('/').pop().toLowerCase();
                var hay = (String(regattaId || '') + ' ' + String(regattaName || '') + ' ' + fn).toLowerCase();
                if (/j22-nationals/.test(fn) || (/j\s*-?\s*22|j22/.test(hay) && /national|champ|north-sails/.test(hay))) return 'j22-nationals';
                if (/cape-classic|zvyc.*classic|tsc.*classic|hyc.*classic/.test(hay)) return 'zvyc-cape-classic';
                if (/wc-dinghy|western-cape-dinghy/.test(hay)) return 'w-cape-championships-dinghy-classes';
                if (/ilca|laser/.test(hay) && /national|champ/.test(hay)) return 'ilca-nationals';
                return '';
            }
            function artworkCatalogueHref(src, className, regattaId, regattaName) {
                var s = String(src || '').trim();
                if (!s) return '';
                if (isEventLogoArtworkPath(s)) {
                    var series = eventLogoSeriesSlugFromContext(s, regattaId, regattaName);
                    return series ? ('/events-logos/' + encodeURIComponent(series)) : '/events-logos';
                }
                var cn = String(className || '').trim() || classNameFromLogoFilename(s);
                var cslug = classSlugFromLogoLabel(cn);
                return cslug ? ('/class/' + encodeURIComponent(cslug)) : '/classes';
            }

            function regattaLogoCatalogueHref(src, className, regattaId, regattaName) {
                return artworkCatalogueHref(src, className, regattaId, regattaName);
            }

            function updateEventLogoCatalogueLink(img, src, catalogueHref, regattaId, regattaName) {
                if (!img || !src) return;
                var link = img.closest ? img.closest('.sa-home-regatta-event-logo-link') : null;
                if (!link) return;
                var href = (catalogueHref || '').trim() || regattaLogoCatalogueHref(src, '', regattaId, regattaName);
                if (!href) {
                    link.removeAttribute('href');
                    return;
                }
                link.href = href;
                link.title = isEventLogoArtworkPath(src) ? 'Open named event in Events catalogue' : 'Open class in Classes catalogue';
            }

            function regattaChipMasterClassLogo(label) {
                var key = String(label || '').trim().toLowerCase().replace(/\s+fleet$/i, '').replace(/\s+class$/i, '').trim();
                var fileMap = {
                    'ilca 4': '/artwork/Class Logo/ILCA-4.7-Class-Logo.png',
                    'ilca 4.7': '/artwork/Class Logo/ILCA-4.7-Class-Logo.png',
                    'ilca 6': '/artwork/Class Logo/ILCA-6-Class-Logo.png',
                    'ilca 7': '/artwork/Class Logo/ILCA-7-Class-Logo.png',
                    'optimist a': '/artwork/Class Logo/Optimist-A-Class-Logo.png',
                    'optimist b': '/artwork/Class Logo/Optimist-B-Class-Logo.png',
                    'optimist c': '/artwork/Class Logo/Optimist-C-Class-Logo.png',
                    'optimist': '/artwork/Class Logo/Optimist-Class-Logo.png',
                    'dabchick': '/artwork/Class Logo/Dabchick-Class-Logo.png',
                    'mirror': '/artwork/Class Logo/Mirror-Class-Logo.png',
                    'open': '/artwork/Class Logo/Open-Class-Logo.png',
                    '420': '/artwork/Class Logo/420-Class-Logo.png',
                    'sonnet': '/artwork/Class Logo/Sonnet-Class-Logo.png',
                    '29er': '/artwork/Class Logo/29er-Class-Logo.png',
                    'hobie 14': '/artwork/Class Logo/Hobie-14-Class-Logo.png',
                    'hobie 16': '/artwork/Class Logo/Hobie-16-Class-Logo.png',
                    'rs tera pro': '/artwork/Class Logo/RS-Tera-Pro-Class-Logo.png',
                    'rs tera sport': '/artwork/Class Logo/RS-Tera-Sport-Class-Logo.png',
                    'df95': '/artwork/Class Logo/DF95-Class-Logo.png',
                    'j22': '/artwork/Class Logo/J22-Class-Logo.png',
                    'hunter 19': '/artwork/Class Logo/Hunter-19-Class-Logo.png'
                };
                return fileMap[key] || '';
            }

            function resolveChildClassLogoFromRegattaPage(regattaId, forceRefresh) {
                var rid = String(regattaId || '').trim();
                if (!rid) return Promise.resolve(null);
                window.__saRegattaChildLogoCache = window.__saRegattaChildLogoCache || {};
                if (!forceRefresh && window.__saRegattaChildLogoCache[rid]) return window.__saRegattaChildLogoCache[rid];
                try {
                    var k = 'sa:regattaLogo:child:v4:' + rid;
                    if (forceRefresh) localStorage.removeItem(k);
                    var cached = forceRefresh ? '' : localStorage.getItem(k);
                    if (cached && cached.trim()) {
                        window.__saRegattaChildLogoCache[rid] = Promise.resolve(cached.trim());
                        return window.__saRegattaChildLogoCache[rid];
                    }
                } catch (_) {}
                var p = fetch('/regatta/' + encodeURIComponent(rid), { credentials: 'same-origin', cache: 'force-cache' })
                    .then(function(r) { return r.ok ? r.text() : ''; })
                    .then(function(html) {
                        if (!html) return null;
                        try {
                            var doc = new DOMParser().parseFromString(html, 'text/html');
                            var img = doc.querySelector('.class-header-logo-col img.class-header-logo-img');
                            var src = img ? (img.getAttribute('src') || '').trim() : '';
                            if (src) { try { localStorage.setItem('sa:regattaLogo:child:v4:' + rid, src); } catch (_) {} }
                            return src || null;
                        } catch (_) {
                            return null;
                        }
                    })
                    .catch(function() { return null; });
                window.__saRegattaChildLogoCache[rid] = p;
                return p;
            }

            function _ensureRegattaLogoLoader() {
                window.__saRegattaLogoLoader = window.__saRegattaLogoLoader || { q: [], running: 0, max: 4 };
                return window.__saRegattaLogoLoader;
            }
            function _enqueueRegattaLogoTask(task) {
                var st = _ensureRegattaLogoLoader();
                st.q.push(task);
                _pumpRegattaLogoTasks();
            }
            function _pumpRegattaLogoTasks() {
                var st = _ensureRegattaLogoLoader();
                if (st.running >= st.max) return;
                var next = st.q.shift();
                if (!next) return;
                st.running += 1;
                var done = function() {
                    st.running -= 1;
                    try { _pumpRegattaLogoTasks(); } catch (_) {}
                    try { _pumpRegattaLogoTasks(); } catch (_) {}
                };
                var apply = function(src) {
                    try {
                        var chip = next.img && next.img.closest ? next.img.closest('.sa-home-regatta-children-chip') : null;
                        if (!src || !next.img || !next.img.isConnected) {
                            if (next.kind === 'child' && chip) setFleetChipLogoState(chip, false);
                            return;
                        }
                        next.img.src = src;
                        next.img.style.display = '';
                        next.img.style.visibility = '';
                        if (next.kind === 'event') {
                            var catHref = (next.img && next.img.dataset) ? (next.img.dataset.saLogoCatalogueHref || '') : '';
                            updateEventLogoCatalogueLink(next.img, src, catHref, next.rid, '');
                        }
                        if (next.kind === 'child' && chip) setFleetChipLogoState(chip, true);
                    } catch (_) {}
                };
                var p = null;
                if (next.kind === 'event') p = resolveEventLogoFromRegattaPage(next.rid, !!next.force);
                else if (next.kind === 'child') p = resolveChildClassLogoFromRegattaPage(next.rid, !!next.force);
                Promise.resolve(p).then(apply).catch(function() {}).finally(done);
            }

            // Nest separate child regatta rows under parent prefix; keep API fleet-shell children.
            function nestRegattaParents(list) {
                var items = (list || []).map(function(r) {
                    var copy = Object.assign({}, r);
                    copy._children = Array.isArray(r.children) ? r.children.slice() : [];
                    return copy;
                });
                var childIds = {};
                items.forEach(function(r) {
                    var rid = String(r.regatta_id || '');
                    var parent = null;
                    items.forEach(function(p) {
                        var pid = String(p.regatta_id || '');
                        if (pid && rid !== pid && rid.indexOf(pid + '-') === 0) {
                            if (!parent || pid.length > String(parent.regatta_id || '').length) parent = p;
                        }
                    });
                    if (parent) {
                        parent._children = parent._children || [];
                        parent._children.push(r);
                        childIds[rid] = true;
                    }
                });
                return items.filter(function(r) { return !childIds[String(r.regatta_id || '')]; });
            }

            var parents = nestRegattaParents(regattas);
            var count = parents.length;
            var labelText = searchQuery
                ? 'Regatta Search for "<span style="color:#c00;font-weight:700;">' + esc(searchQuery) + '</span>" = Results (' + count + ')'
                : 'All Regattas — newest first (' + count + ')';

            ensureRegattaListCss();
            var wrap = document.createElement('div');
            wrap.className = 'sa-home-regatta-wrap';
            var h2 = document.createElement('h2');
            h2.className = 'regatta-search-results-label';
            h2.style.cssText = 'margin:0 0 0.75rem 0;font-size:1.25rem;font-weight:700;color:#001f3f;';
            h2.innerHTML = labelText;
            var listEl = document.createElement('div');
            listEl.className = 'sa-home-regatta-list';

            function renderChildLabel(childLabel, parentLabel) {
                var label = String(childLabel || 'Class/Fleet');
                var p = String(parentLabel || '');
                if (p && label.toLowerCase().indexOf(p.toLowerCase() + ' ') === 0) {
                    label = label.slice(p.length).trim();
                }
                return label;
            }

            function renderChipLabel(childLabel) {
                var label = String(childLabel || '').trim();
                label = label.replace(/\s+fleet$/i, '').trim();
                label = label.replace(/\s+class$/i, '').trim();
                return label || 'Class/Fleet';
            }

            function fleetChipTextName(name) {
                // Fleet chip text fallback: never show trailing "Fleet" (ORC Fleet → ORC).
                var s = String(name || '').trim().replace(/\s+fleet$/i, '').trim();
                if (!s) return String(name || '').trim();
                // Light title-case for labels like "l26" / "orc" / "wseh 1 lap".
                return s.replace(/\b([a-z])/g, function(_, c) { return c.toUpperCase(); });
            }

            function setFleetChipLogoState(chip, hasLogo) {
                if (!chip) return;
                if (hasLogo) {
                    chip.classList.add('has-logo');
                    chip.classList.remove('no-logo');
                } else {
                    chip.classList.add('no-logo');
                    chip.classList.remove('has-logo');
                }
            }

            function getChipLabelParts(childLabel) {
                var label = renderChipLabel(childLabel);
                return { text: label, hideWhenLogo: false };
            }

            function svgIcon(name) {
                var ns = 'http://www.w3.org/2000/svg';
                var svg = document.createElementNS(ns, 'svg');
                svg.setAttribute('viewBox', '0 0 16 16');
                svg.setAttribute('aria-hidden', 'true');
                svg.setAttribute('focusable', 'false');
                svg.setAttribute('width', '14');
                svg.setAttribute('height', '14');
                svg.setAttribute('fill', 'none');
                svg.setAttribute('stroke', 'currentColor');
                svg.setAttribute('stroke-width', '1.6');
                svg.setAttribute('stroke-linecap', 'round');
                svg.setAttribute('stroke-linejoin', 'round');
                if (name === 'calendar') {
                    var r = document.createElementNS(ns, 'rect');
                    r.setAttribute('x', '2.25'); r.setAttribute('y', '3.5'); r.setAttribute('width', '11.5'); r.setAttribute('height', '9.5'); r.setAttribute('rx', '1.4');
                    var l1 = document.createElementNS(ns, 'line');
                    l1.setAttribute('x1', '2.25'); l1.setAttribute('y1', '6'); l1.setAttribute('x2', '13.75'); l1.setAttribute('y2', '6');
                    var l2 = document.createElementNS(ns, 'line');
                    l2.setAttribute('x1', '5'); l2.setAttribute('y1', '2.25'); l2.setAttribute('x2', '5'); l2.setAttribute('y2', '4.75');
                    var l3 = document.createElementNS(ns, 'line');
                    l3.setAttribute('x1', '11'); l3.setAttribute('y1', '2.25'); l3.setAttribute('x2', '11'); l3.setAttribute('y2', '4.75');
                    svg.appendChild(r); svg.appendChild(l1); svg.appendChild(l2); svg.appendChild(l3);
                } else if (name === 'users') {
                    var c1 = document.createElementNS(ns, 'circle');
                    c1.setAttribute('cx', '6'); c1.setAttribute('cy', '5.5'); c1.setAttribute('r', '2.1');
                    var c2 = document.createElementNS(ns, 'circle');
                    c2.setAttribute('cx', '10.5'); c2.setAttribute('cy', '6.2'); c2.setAttribute('r', '1.8');
                    var p1 = document.createElementNS(ns, 'path');
                    p1.setAttribute('d', 'M2.7 12.4c.45-1.9 2.05-3 4.2-3 2.15 0 3.75 1.1 4.2 3');
                    var p2 = document.createElementNS(ns, 'path');
                    p2.setAttribute('d', 'M9.4 11.8c.35-1.2 1.35-1.95 2.7-1.95 1.05 0 1.95.45 2.5 1.25');
                    svg.appendChild(c1); svg.appendChild(c2); svg.appendChild(p1); svg.appendChild(p2);
                } else if (name === 'trophy') {
                    var p = document.createElementNS(ns, 'path');
                    p.setAttribute('d', 'M5 2.5h6v1.8c0 2.3-1.4 4-3 4.6v2h2v1.6H6V10.9h2v-2c-1.6-.6-3-2.3-3-4.6V2.5Z');
                    var h1 = document.createElementNS(ns, 'path');
                    h1.setAttribute('d', 'M5 3.4H3.2c0 1.7.7 2.9 2.1 3.4');
                    var h2 = document.createElementNS(ns, 'path');
                    h2.setAttribute('d', 'M11 3.4h1.8c0 1.7-.7 2.9-2.1 3.4');
                    svg.appendChild(p); svg.appendChild(h1); svg.appendChild(h2);
                } else if (name === 'chevron-right') {
                    var cr = document.createElementNS(ns, 'path');
                    cr.setAttribute('d', 'M6 3.5 10 8l-4 4.5');
                    svg.appendChild(cr);
                }
                return svg;
            }

            parents.forEach(function(r, idx) {
                var rid = (r.regatta_id != null ? r.regatta_id : r.id) + '';
                var title = (r.search_label || r.event_name || r.name || 'Regatta') + '';
                var entries = r.entries_count != null ? r.entries_count : (r.total_entries != null ? r.total_entries : '—');
                var hostCode = (r.host_club_abbrev || r.host_club_code || '').trim().toUpperCase();
                var hostName = (r.host_club_fullname || r.host_club_name || '').trim();
                var kids = Array.isArray(r._children) ? r._children.slice().filter(function(ch) {
                    return isRegattaSearchClassFleetChip(ch, rid);
                }) : [];
                var displayEntries = entries;

                var card = document.createElement('div');
                card.className = 'sa-home-regatta-card';

                var parentRow = document.createElement('div');
                parentRow.className = 'sa-home-regatta-top';

                var eventLogoLink = document.createElement('a');
                eventLogoLink.className = 'sa-home-regatta-event-logo-link';
                eventLogoLink.setAttribute('aria-label', 'Open event or class catalogue');
                var eventLogoImg = document.createElement('img');
                eventLogoImg.className = 'sa-home-regatta-event-logo';
                eventLogoImg.loading = 'lazy';
                eventLogoImg.decoding = 'async';
                eventLogoImg.alt = '';
                eventLogoImg.style.display = 'none';
                eventLogoImg.dataset.saLogoRid = rid;
                eventLogoImg.dataset.saLogoSrc = (r.logo_url || '');
                eventLogoImg.dataset.saLogoCatalogueHref = (r.logo_catalogue_href || '');
                eventLogoImg.dataset.saLogoRetry = '0';
                if (r.logo_url) {
                    eventLogoImg.src = r.logo_url;
                    eventLogoImg.style.display = '';
                    updateEventLogoCatalogueLink(eventLogoImg, r.logo_url, r.logo_catalogue_href, rid, title);
                } else {
                    eventLogoLink.removeAttribute('href');
                }
                eventLogoImg.onerror = function() {
                    try {
                        var retryRid = eventLogoImg.dataset ? (eventLogoImg.dataset.saLogoRid || '') : '';
                        if (retryRid && eventLogoImg.dataset.saLogoRetry !== '1') {
                            eventLogoImg.dataset.saLogoRetry = '1';
                            eventLogoImg.removeAttribute('src');
                            eventLogoImg.style.display = 'none';
                            _enqueueRegattaLogoTask({ kind: 'event', rid: retryRid, img: eventLogoImg, force: true });
                            return;
                        }
                        eventLogoImg.style.display = 'none';
                        eventLogoLink.removeAttribute('href');
                    } catch (_) {}
                };
                eventLogoLink.appendChild(eventLogoImg);
                parentRow.appendChild(eventLogoLink);

                var main = document.createElement('div');
                main.className = 'sa-home-regatta-top-main';

                var h = document.createElement('div');
                h.className = 'sa-home-regatta-title';
                var aTitle = document.createElement('a');
                aTitle.href = '/regatta/' + encodeURIComponent(rid);
                aTitle.textContent = title;
                aTitle.style.color = 'inherit';
                aTitle.style.textDecoration = 'none';
                h.appendChild(aTitle);
                main.appendChild(h);

                var meta = document.createElement('div');
                meta.className = 'sa-home-regatta-meta';
                var dateItem = document.createElement('div');
                dateItem.className = 'sa-home-regatta-meta-pill';
                var dateIco = document.createElement('span');
                dateIco.className = 'sa-home-regatta-meta-ico';
                dateIco.appendChild(svgIcon('calendar'));
                dateItem.appendChild(dateIco);
                dateItem.appendChild(document.createTextNode(formatParentDate(r)));
                var entriesItem = document.createElement('div');
                entriesItem.className = 'sa-home-regatta-meta-pill';
                var entriesIco = document.createElement('span');
                entriesIco.className = 'sa-home-regatta-meta-ico';
                entriesIco.appendChild(svgIcon('users'));
                entriesItem.appendChild(entriesIco);
                entriesItem.appendChild(document.createTextNode((displayEntries != null && displayEntries !== '—') ? (Number(displayEntries).toLocaleString() + ' Entries') : '— Entries'));
                meta.appendChild(dateItem);
                meta.appendChild(entriesItem);
                main.appendChild(meta);

                var childrenWrap = document.createElement('div');
                childrenWrap.className = 'sa-home-regatta-children';

                parentRow.appendChild(main);
                var hostSlug = String(r.host_club_slug || hostCode || '').trim().toLowerCase();
                var hostHref = String(r.host_logo_href || '').trim() || (hostSlug ? ('/club/' + encodeURIComponent(hostSlug)) : '');
                var host = document.createElement(hostHref ? 'a' : 'div');
                host.className = 'sa-home-regatta-host';
                if (hostHref) {
                    host.href = hostHref;
                    host.title = 'Open club page';
                    host.setAttribute('aria-label', (hostCode || hostName || 'Club') + ' club page');
                }
                var hostLogo = safeImg((r.host_logo_url || (hostCode ? ('/api/club-logo/' + encodeURIComponent(hostCode)) : '')), 'sa-home-regatta-host-logo');
                if (hostLogo) host.appendChild(hostLogo);
                var hostText = document.createElement('div');
                hostText.className = 'sa-home-regatta-host-text';
                var hostCodeEl = document.createElement('div');
                hostCodeEl.className = 'sa-home-regatta-host-code';
                hostCodeEl.textContent = hostCode || '';
                var hostNameEl = document.createElement('div');
                hostNameEl.className = 'sa-home-regatta-host-name';
                hostNameEl.textContent = hostName || hostLocationLabel(r);
                hostText.appendChild(hostCodeEl);
                hostText.appendChild(hostNameEl);
                host.appendChild(hostText);

                var actions = document.createElement('div');
                actions.className = 'sa-home-regatta-actions';
                var parentResultsHref = '/regatta/' + encodeURIComponent(rid);
                var parentLabel = r.search_label || r.event_name || '';

                // Single class: class logo left of Full Results → same parent URL (no fleet bar).
                if (kids.length === 1) {
                    var only = kids[0];
                    var onlyChildLabel = renderChildLabel(only.search_label || only.fleet_label || only.event_name || only.name, parentLabel);
                    var onlyParts = getChipLabelParts(onlyChildLabel);
                    var onlyName = onlyParts.text || renderChipLabel(onlyChildLabel) || 'Class';
                    var onlyMaster = regattaChipMasterClassLogo(onlyName);
                    var onlyChildId = (only.regatta_id != null ? only.regatta_id : only.id) + '';
                    var singleClass = document.createElement('a');
                    singleClass.className = 'sa-home-regatta-single-class';
                    singleClass.href = parentResultsHref;
                    singleClass.title = onlyName;
                    singleClass.setAttribute('aria-label', onlyName + ' results');
                    var singleLogo = document.createElement('img');
                    singleLogo.className = 'sa-home-regatta-chip-logo';
                    singleLogo.loading = 'lazy';
                    singleLogo.decoding = 'async';
                    singleLogo.alt = onlyName;
                    singleLogo.style.visibility = 'hidden';
                    // Logo art from class master; link stays parent (not child slug).
                    singleLogo.dataset.saLogoRid = onlyChildId || rid;
                    singleLogo.dataset.saLogoSrc = onlyMaster || (only.logo_url || '');
                    singleLogo.dataset.saLogoRetry = '0';
                    singleLogo.onerror = function() {
                        try {
                            var retryRid = singleLogo.dataset ? (singleLogo.dataset.saLogoRid || '') : '';
                            if (retryRid && singleLogo.dataset.saLogoRetry !== '1') {
                                singleLogo.dataset.saLogoRetry = '1';
                                singleLogo.removeAttribute('src');
                                singleLogo.style.visibility = 'hidden';
                                _enqueueRegattaLogoTask({ kind: 'child', rid: retryRid, img: singleLogo, force: true });
                                return;
                            }
                            singleLogo.style.visibility = 'hidden';
                        } catch (_) {}
                    };
                    singleClass.appendChild(singleLogo);
                    actions.appendChild(singleClass);
                }

                var fullBtn = document.createElement('a');
                fullBtn.className = 'sa-home-regatta-btn';
                fullBtn.href = parentResultsHref;
                var btnIco = document.createElement('span');
                btnIco.className = 'sa-home-regatta-btn-ico';
                btnIco.appendChild(svgIcon('trophy'));
                fullBtn.appendChild(btnIco);
                fullBtn.appendChild(document.createTextNode('Full Results'));
                actions.appendChild(fullBtn);

                parentRow.appendChild(host);
                parentRow.appendChild(actions);
                card.appendChild(parentRow);

                // Multi-fleet only: bottom bar with per-fleet chips (each → child URL).
                if (kids.length > 1) {
                    var childrenHead = document.createElement('div');
                    childrenHead.className = 'sa-home-regatta-children-head';
                    var childrenNote = document.createElement('span');
                    childrenNote.className = 'sa-home-regatta-children-note';
                    childrenNote.textContent = 'Or view results by class/fleet:';
                    var childrenChips = document.createElement('div');
                    childrenChips.className = 'sa-home-regatta-children-chips';
                    childrenHead.appendChild(childrenNote);
                    childrenHead.appendChild(childrenChips);
                    childrenWrap.appendChild(childrenHead);

                    kids.forEach(function(ch) {
                        var childId = (ch.regatta_id != null ? ch.regatta_id : ch.id) + '';
                        if (!childId) return;
                        var childLabel = renderChildLabel(ch.search_label || ch.fleet_label || ch.event_name || ch.name, parentLabel);
                        var chipParts = getChipLabelParts(childLabel);
                        var chipName = chipParts.text || renderChipLabel(childLabel);
                        var textName = fleetChipTextName(chipName);
                        var masterChipLogo = regattaChipMasterClassLogo(chipName) || regattaChipMasterClassLogo(textName);
                        var logoSrc = masterChipLogo || (ch.logo_url || '');
                        var childEntries = ch.entries_count != null ? ch.entries_count : (ch.total_entries != null ? ch.total_entries : null);
                        var chip = document.createElement('a');
                        chip.className = 'sa-home-regatta-children-chip';
                        chip.href = '/regatta/' + encodeURIComponent(childId);
                        chip.title = textName + (childEntries != null ? (' (' + childEntries + ')') : '');
                        chip.setAttribute('aria-label', textName + (childEntries != null ? (' (' + childEntries + ' entries)') : ' results'));
                        var chipLogo = document.createElement('img');
                        chipLogo.className = 'sa-home-regatta-chip-logo';
                        chipLogo.loading = 'lazy';
                        chipLogo.decoding = 'async';
                        chipLogo.alt = textName;
                        chipLogo.style.visibility = 'hidden';
                        chipLogo.dataset.saLogoRid = childId;
                        chipLogo.dataset.saLogoSrc = logoSrc;
                        chipLogo.dataset.saLogoRetry = '0';
                        chipLogo.onerror = function() {
                            try {
                                var retryRid = chipLogo.dataset ? (chipLogo.dataset.saLogoRid || '') : '';
                                if (retryRid && chipLogo.dataset.saLogoRetry !== '1') {
                                    chipLogo.dataset.saLogoRetry = '1';
                                    chipLogo.removeAttribute('src');
                                    chipLogo.style.visibility = 'hidden';
                                    _enqueueRegattaLogoTask({ kind: 'child', rid: retryRid, img: chipLogo, force: true });
                                    return;
                                }
                                chipLogo.style.visibility = 'hidden';
                                setFleetChipLogoState(chip, false);
                            } catch (_) {}
                        };
                        chipLogo.onload = function() {
                            try {
                                chipLogo.style.visibility = '';
                                setFleetChipLogoState(chip, true);
                            } catch (_) {}
                        };
                        chip.appendChild(chipLogo);
                        // Logo 1st; text only when no class/fleet logo (name without "Fleet").
                        var chipText = document.createElement('span');
                        chipText.className = 'sa-home-regatta-chip-text';
                        chipText.textContent = textName;
                        chip.appendChild(chipText);
                        var chipN = document.createElement('span');
                        chipN.className = 'sa-home-regatta-chip-n';
                        chipN.textContent = childEntries != null && childEntries !== '' ? ('(' + Number(childEntries).toLocaleString() + ')') : '';
                        chip.appendChild(chipN);
                        setFleetChipLogoState(chip, !!logoSrc);
                        childrenChips.appendChild(chip);
                    });
                    card.appendChild(childrenWrap);
                }
                listEl.appendChild(card);

                if (idx !== parents.length - 1) {
                    var sep = document.createElement('hr');
                    sep.className = 'sa-home-regatta-sep';
                    listEl.appendChild(sep);
                }
            });

            (function() {
                function loadCardLogo(card) {
                    if (!card || card.__saLogoLoaded) return;
                    card.__saLogoLoaded = true;
                    var ev = card.querySelector('.sa-home-regatta-event-logo');
                    var rid = ev && ev.dataset ? ev.dataset.saLogoRid : '';
                    var src = ev && ev.dataset ? (ev.dataset.saLogoSrc || '') : '';
                    var catHref = ev && ev.dataset ? (ev.dataset.saLogoCatalogueHref || '') : '';
                    if (ev && src) {
                        ev.src = src;
                        ev.style.display = '';
                        updateEventLogoCatalogueLink(ev, src, catHref, rid, '');
                        loadChipLogos(card);
                        return;
                    }
                    if (ev && rid) _enqueueRegattaLogoTask({ kind: 'event', rid: rid, img: ev });
                    loadChipLogos(card);
                }
                function loadChipLogos(card) {
                    if (!card) return;
                    var imgs = Array.prototype.slice.call(card.querySelectorAll('.sa-home-regatta-chip-logo')) || [];
                    imgs.forEach(function(img) {
                        if (!img || img.__saLogoLoaded) return;
                        var rid = img.dataset ? img.dataset.saLogoRid : '';
                        if (!rid) return;
                        img.__saLogoLoaded = true;
                        var src = img.dataset ? (img.dataset.saLogoSrc || '') : '';
                        var chip = img.closest ? img.closest('.sa-home-regatta-children-chip') : null;
                        if (src) {
                            img.src = src;
                            img.style.visibility = '';
                            setFleetChipLogoState(chip, true);
                            return;
                        }
                        setFleetChipLogoState(chip, false);
                        _enqueueRegattaLogoTask({ kind: 'child', rid: rid, img: img });
                    });
                }
                var cards = Array.prototype.slice.call(listEl.querySelectorAll('.sa-home-regatta-card')) || [];
                cards.slice(0, 18).forEach(loadCardLogo);
                if (!('IntersectionObserver' in window)) {
                    cards.forEach(loadCardLogo);
                    return;
                }
                try {
                    var io = new IntersectionObserver(function(entries) {
                        entries.forEach(function(en) {
                            if (en.isIntersecting) {
                                loadCardLogo(en.target);
                                try { io.unobserve(en.target); } catch (_) {}
                            }
                        });
                    }, { root: null, rootMargin: '400px 0px', threshold: 0.01 });
                    cards.forEach(function(c, idx) {
                        if (idx < 18) return;
                        try { io.observe(c); } catch (_) {}
                    });
                } catch (_) {}
            })();

            wrap.appendChild(h2);
            wrap.appendChild(listEl);
            publicRegattasList.innerHTML = '';
            publicRegattasList.appendChild(wrap);
            _saApplyRegattaSearchRestoreScroll();
        }
        var _regattaSearchAllCache = null;
        function _filterRegattaCache(list, q) {
            if (!q) return list.slice();
            var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
            return list.filter(function(r) {
                var hay = [
                    r.search_label || '',
                    r.event_name || '',
                    r.regatta_id || '',
                    r.host_club_name || '',
                    r.host_club_code || '',
                    r.end_date || '',
                    r.start_date || ''
                ].join(' ').toLowerCase();
                return terms.every(function(t) { return hay.indexOf(t) !== -1; });
            });
        }
        function _clearPublicRegattasList() {
            var publicRegattasList = document.getElementById('public-regattas-list');
            if (publicRegattasList) publicRegattasList.innerHTML = '';
        }
        async function applyRegattaFilter() {
            // Only when Regatta pill is active — never on page load / Sailor mode
            var isDirectory = global.__ssaDirectoryRegattas === true;
            if (!isDirectory && (global.searchMode || 'sailor') !== 'regatta') {
                _clearPublicRegattasList();
                return;
            }
            var sailorSearchInput = document.getElementById('sailor-search-input');
            var regattaInput = document.getElementById('temp-landing-regatta-input');
            var directoryInput = document.getElementById('events-dashboard-search');
            var q = '';
            if (isDirectory && directoryInput) {
                q = (directoryInput.value || '').trim();
            } else {
                var useRegattaInput = !!(regattaInput && (document.activeElement === regattaInput || regattaInput.offsetParent !== null));
                q = useRegattaInput
                    ? (regattaInput.value || '').trim()
                    : (sailorSearchInput ? sailorSearchInput.value.trim() : '');
            }
            var publicRegattasList = document.getElementById('public-regattas-list');
            if (!publicRegattasList) return;

            // Empty query → show first page fast, then fill full cache in background
            if (!q || q.toLowerCase() === 'all') {
                publicRegattasList.innerHTML = '<p>Loading…</p>';
                try {
                    if (!_regattaSearchAllCache) {
                        var firstPage = typeof getRegattas === 'function'
                            ? await getRegattas({ limit: 60 })
                            : [];
                        if (!Array.isArray(firstPage)) firstPage = [];
                        if ((window.searchMode || 'sailor') !== 'regatta') {
                            _clearPublicRegattasList();
                            return;
                        }
                        renderRegattasTable(firstPage, q.toLowerCase() === 'all' ? 'all' : '');
                        // Background: full list for typeahead filter + complete scroll
                        if (typeof getRegattas === 'function') {
                            getRegattas({ limit: 500 }).then(function(all) {
                                if (!Array.isArray(all)) all = [];
                                _regattaSearchAllCache = all;
                                if ((window.searchMode || 'sailor') !== 'regatta') return;
                                var inp = document.getElementById('temp-landing-regatta-input')
                                    || document.getElementById('sailor-search-input');
                                var curQ = (inp && inp.value ? String(inp.value) : '').trim();
                                if (!curQ || curQ.toLowerCase() === 'all') {
                                    renderRegattasTable(all, curQ.toLowerCase() === 'all' ? 'all' : '');
                                }
                            }).catch(function() {});
                        }
                        return;
                    }
                    // Re-check mode after await (user may have switched to Sailor)
                    if ((window.searchMode || 'sailor') !== 'regatta') {
                        _clearPublicRegattasList();
                        return;
                    }
                    renderRegattasTable(_regattaSearchAllCache, q.toLowerCase() === 'all' ? 'all' : '');
                } catch (err) {
                    console.error('[DEBUG] applyRegattaFilter:', err);
                    publicRegattasList.innerHTML = '<p>Unable to load regattas. Try again.</p>';
                }
                return;
            }

            // As-you-type: filter cached full list (instant); fallback to API if cache empty
            if (_regattaSearchAllCache && _regattaSearchAllCache.length) {
                renderRegattasTable(_filterRegattaCache(_regattaSearchAllCache, q), q);
                return;
            }

            var minLen = 2;
            if (q.length < minLen) {
                publicRegattasList.innerHTML = '';
                return;
            }
            publicRegattasList.innerHTML = '<p>Loading…</p>';
            try {
                var params = { q: (q || '').trim(), limit: 500 };
                var regattas = typeof getRegattas === 'function' ? await getRegattas(params) : [];
                if ((window.searchMode || 'sailor') !== 'regatta') {
                    _clearPublicRegattasList();
                    return;
                }
                renderRegattasTable(Array.isArray(regattas) ? regattas : [], q);
            } catch (err) {
                console.error('[DEBUG] applyRegattaFilter:', err);
                publicRegattasList.innerHTML = '<p>Unable to load regattas. Try again.</p>';
            }
        }

  global.renderRegattasTable = renderRegattasTable;
  global.applyRegattaFilter = applyRegattaFilter;
  global.loadPublicRegattas = loadPublicRegattas;
  global._filterRegattaCache = _filterRegattaCache;
  global.parseRegattaSearchQuery = parseRegattaSearchQuery;
})(typeof window !== 'undefined' ? window : this);
