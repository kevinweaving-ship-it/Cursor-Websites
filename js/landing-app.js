
        // Function to close popup and return to landing page
        function closePopupAndReturnToPage() {
            const popup = document.getElementById('popupOverlay');
            if (popup) {
                popup.style.display = 'none';
                // Hide all popup states
                const states = document.querySelectorAll('.popup-state');
                states.forEach(state => {
                    state.style.display = 'none';
                    state.classList.add('hidden');
                });
            }
        }
        window.closePopupAndReturnToPage = closePopupAndReturnToPage;

        function setMainColumnMode(mode) {
            var isClass = mode === 'class';
            var isSailor = mode === 'sailor';
            var isHome = !isClass && !isSailor;
            function show(el, on) { if (el) el.style.display = on ? '' : 'none'; }
            show(document.getElementById('site-stats-embed'), false); // gauges temporarily removed
            if (isSailor) {
                return;
            }
            show(document.querySelector('.search-header-container'), isHome);
            show(document.getElementById('public-regattas-section'), isHome);
            show(document.querySelector('.search-row-container'), !isClass);
            var hr = document.querySelector('.search-to-profile-separator');
            if (hr) hr.style.display = isClass ? 'none' : '';
            show(document.getElementById('landing-news-embed'), isHome);
            var browse = document.querySelector('section.browse-sailingsa');
            if (browse) show(browse, isHome);
            show(document.getElementById('public-view'), !isClass);
            show(document.getElementById('sailor-view'), !isClass);
            var cv = document.getElementById('class-view');
            if (cv) cv.style.display = isClass ? 'block' : 'none';
            var sailorResults = document.getElementById('sailor-search-results');
            if (sailorResults && isClass) {
                sailorResults.style.display = 'none';
                sailorResults.innerHTML = '';
            }
        }
        window.setMainColumnMode = setMainColumnMode;

        /** Normalized path; true for any /class/… route (SPA class page). */
        function sailingsaIsClassRoutePath(p) {
            try {
                var path = (p != null && p !== '') ? String(p) : String((window.location && window.location.pathname) || '/');
                path = path.replace(/\/+$/, '') || '/';
                return path.indexOf('/class/') === 0;
            } catch (e) { return false; }
        }
        window.sailingsaIsClassRoutePath = sailingsaIsClassRoutePath;

        function finishClassPageLoad() {
            setMainColumnMode('class');
            setTimeout(function() {
                try {
                    var p = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                    if (sailingsaIsClassRoutePath(p)) setMainColumnMode('class');
                } catch (e) {}
            }, 0);
            setTimeout(function() {
                try {
                    var p = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                    if (sailingsaIsClassRoutePath(p)) setMainColumnMode('class');
                } catch (e) {}
            }, 200);
        }

        function stripDomForSailorProfile() {
            try {
                var heroBanner = document.getElementById('temp-landing-hero-image');
                if (heroBanner && heroBanner.parentNode) heroBanner.parentNode.removeChild(heroBanner);
                var claimBanner = document.getElementById('temp-landing-claim-profile-banner');
                if (claimBanner && claimBanner.parentNode) claimBanner.parentNode.removeChild(claimBanner);
                var homeSearchSection = document.getElementById('sailor-search-section');
                var homeSearchWrapper = homeSearchSection ? homeSearchSection.closest('div.search-header-container.sailor-search-pills, div.search-header-container') : null;
                if (!homeSearchWrapper) {
                    homeSearchWrapper = document.querySelector('div.search-header-container.sailor-search-pills, div.search-header-container');
                }
                if (homeSearchWrapper && homeSearchWrapper.parentNode) {
                    var hasProfileProtectedNodes = !!(
                        homeSearchWrapper.querySelector('#public-view') ||
                        homeSearchWrapper.querySelector('#sailor-view') ||
                        homeSearchWrapper.querySelector('#sailor-search-results') ||
                        homeSearchWrapper.querySelector('#class-view')
                    );
                    if (!hasProfileProtectedNodes) {
                        homeSearchWrapper.parentNode.removeChild(homeSearchWrapper);
                    }
                }
                var publicRegattas = document.getElementById('public-regattas-section');
                if (publicRegattas && publicRegattas.parentNode) publicRegattas.parentNode.removeChild(publicRegattas);
            } catch (_) {}
        }

        window.loadClassPageRoute = async function(classSlug) {
            if (!classSlug) return;
            if (window.__sailingClassSsrPainted) return;
            var ssrEl = document.getElementById('sailing-class-ssr-data');
            if (ssrEl) {
                try {
                    var ssrData = JSON.parse(ssrEl.textContent);
                    if (ssrData && typeof ssrData === 'object') {
                        if (typeof window.renderClassPage === 'function') window.renderClassPage(ssrData);
                        if (typeof setClassPageSEO === 'function') setClassPageSEO(window.location.pathname || '', ssrData);
                        finishClassPageLoad();
                        return;
                    }
                } catch (err) {
                    console.error('[class] SSR parse failed', err);
                }
            }
            var API = (window.API_BASE || '').replace(/\/$/, '');
            var classRes = await fetch(API + '/api/class/' + encodeURIComponent(classSlug) + '?t=' + Date.now(), { cache: 'no-store' }).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; });
            if (!classRes || typeof classRes !== 'object') {
                var cv0 = document.getElementById('class-view');
                if (cv0) cv0.innerHTML = '<div class="container"><p class="card">Failed to load class. Try again or <a href="/classes">browse classes</a>.</p></div>';
                setMainColumnMode('class');
                return;
            }
            if (!(classRes.class_name && String(classRes.class_name).trim()) && !(classRes.class_slug && String(classRes.class_slug).trim())) {
                var cvEmpty = document.getElementById('class-view');
                if (cvEmpty) cvEmpty.innerHTML = '<div class="container"><p class="card">No data available</p></div>';
                setMainColumnMode('class');
                return;
            }
            try {
                if (typeof window.renderClassPage === 'function') window.renderClassPage(classRes);
                if (typeof setClassPageSEO === 'function') setClassPageSEO(window.location.pathname || '', classRes);
            } catch (err) {
                console.error('[class] render failed', err);
                var cvErr = document.getElementById('class-view');
                if (cvErr) cvErr.innerHTML = '<div class="container"><p class="card">Could not display this class.</p></div>';
            } finally {
                finishClassPageLoad();
            }
        };

        function escapeClassHtml(s) {
            if (s == null || s === undefined) return '';
            return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
        function classSlugFromName(name) {
            return (name || '').toString().toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
        }
        /** Catalogue class → blue /class/{slug} link; unmatched sheet label → light red. */
        function formatClassCellHtml(r, rowClass) {
            var label = (rowClass || '').trim();
            if (!label) return '';
            var matched = !!(r.class_slug || r.class_path || r.result_class_id != null || r.class_id != null);
            if (matched) {
                var slug = (r.class_slug || classSlugFromName(label) || '').toString();
                var href = (r.class_path || (slug ? ('/class/' + slug) : '/classes'));
                return '<a href="' + escapeClassHtml(href) + '" class="class-link-valid" title="View class page">' + escapeClassHtml(label) + '</a>';
            }
            return '<span class="result-class-unmatched" title="Class on result sheet — not yet in catalogue">' + escapeClassHtml(label) + '</span>';
        }
        function sortTable(table, colIndex) {
            if (!table || !table.tBodies || !table.tBodies[0]) return;
            var tbody = table.tBodies[0];
            var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
            if (rows.length === 0) return;
            var currentCol = parseInt(table.dataset.sortCol, 10);
            var currentDir = table.dataset.sortDir || 'asc';
            var dir = (currentCol === colIndex && currentDir === 'asc') ? 'desc' : 'asc';
            table.dataset.sortCol = colIndex;
            table.dataset.sortDir = dir;
            rows.sort(function(a, b) {
                var ac = a.cells[colIndex];
                var bc = b.cells[colIndex];
                if (!ac || !bc) return 0;
                var at = (ac.textContent || ac.innerText || '').trim();
                var bt = (bc.textContent || bc.innerText || '').trim();
                var an = parseFloat(at.replace(/[^\d.-]/g, ''));
                var bn = parseFloat(bt.replace(/[^\d.-]/g, ''));
                if (!isNaN(an) && !isNaN(bn)) return dir === 'asc' ? an - bn : bn - an;
                var c = at.localeCompare(bt, undefined, { numeric: true });
                return dir === 'asc' ? c : -c;
            });
            rows.forEach(function(r) { tbody.appendChild(r); });
            var dirChar = dir === 'asc' ? '\u25B2' : '\u25BC';
            table.querySelectorAll('thead th').forEach(function(th, i) {
                var span = th.querySelector('.sort-indicator');
                if (span) span.textContent = i === colIndex ? ' ' + dirChar : ' \u21C5';
            });
        }
        function attachSortableTables(container) {
            if (!container) return;
            container.querySelectorAll('table thead th').forEach(function(th, index) {
                th.style.cursor = 'pointer';
                th.setAttribute('title', 'Sort');
                if (!th._sortAttached) {
                    th._sortAttached = true;
                    th.addEventListener('click', function() { sortTable(th.closest('table'), index); });
                }
            });
        }
        function buildMasterPageLayout(container, opts) {
            if (!container || !opts) return;
            var esc = function(s) { if (s == null || s === undefined) return ''; var t = String(s); return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };
            var back = (opts.backLink !== false) ? '<a href="/" class="js-go-home" style="margin-bottom:12px;padding:6px 12px;font-size:13px;font-weight:600;color:#fff;background:#001f3f;border:none;border-radius:6px;cursor:pointer;display:inline-block;text-decoration:none;">Back to results</a>' : '';
            var titleCard = '';
            if (opts.titleCard && opts.titleCard.title) {
                var tc = opts.titleCard;
                var icon = (tc.iconSrc && tc.iconSrc.trim()) ? '<div class="class-hero-left"><img src="' + esc(tc.iconSrc) + '" alt="" class="class-icon" onerror="this.style.display=\'none\'"></div>' : '';
                var main = '<div class="class-hero-main"><h1>' + esc(tc.title) + '</h1>' + (tc.description ? '<p class="class-bio">' + esc(tc.description) + '</p>' : '') + (tc.associationHtml ? '<div class="class-assoc">Association: ' + tc.associationHtml + '</div>' : '') + '</div>';
                var titleCardClass = icon ? 'card class-hero' : 'card';
                titleCard = '<div class="' + titleCardClass + '">' + icon + main + '</div>';
            }
            var statsCard = '';
            if (opts.statsCard && opts.statsCard.links && opts.statsCard.links.length) {
                var linkParts = opts.statsCard.links.map(function(l) { return '<a class="stats-link" href="' + esc(l.href) + '">' + esc(l.label) + '</a>'; });
                statsCard = '<div class="card stats-card"><div class="class-stats">' + linkParts.join('') + '</div></div>';
            }
            var dataCards = (opts.dataCards || []).map(function(d) {
                return '<div id="' + esc(d.id) + '" class="card"><h2 class="section-title">' + esc(d.title) + '</h2><div class="table-container">' + (d.tableHtml || '') + '</div></div>';
            }).join('');
            container.innerHTML = '<div class="master-page-layout container">' + back + titleCard + statsCard + dataCards + '</div>';
        }
        function classLink(_ignored, displayName) {
            var name = (displayName || '').toString().trim();
            var esc = escapeClassHtml(name) || '—';
            var slug = classSlugFromName(name);
            if (name && slug)
                return '<a href="/class/' + encodeURIComponent(slug) + '" target="_top">' + esc + '</a>';
            return esc;
        }
        window.renderClassPage = function(data) {
            var cv = document.getElementById('class-view');
            if (!cv) return;
            if (!data || typeof data !== 'object') {
                cv.innerHTML = '<div class="container"><p class="card">No data available</p></div>';
                return;
            }
            var esc = escapeClassHtml;
            var className = data.class_name || 'Class';
            var classSlug = classSlugFromName(className) || '';
            var classLogo = (data.logo_path || '').trim();
            if (classLogo && classLogo.charAt(0) !== '/') classLogo = '/' + classLogo;
            var regattas = (data.regattas || []).slice();
            var clubs = (data.clubs_sailing_class || []).slice();
            var sailors = (data.sailors || []).slice();
            // Newest regattas first
            regattas.sort(function(a, b) {
                return String(b.event_date || b.end_date || b.start_date || '').localeCompare(
                    String(a.event_date || a.end_date || a.start_date || '')
                );
            });
            clubs.sort(function(a, b) {
                return String(a.club_code || a.club_name || '').localeCompare(
                    String(b.club_code || b.club_name || ''), undefined, { sensitivity: 'base' }
                );
            });
            sailors.sort(function(a, b) {
                return String(a.sailor_name || '').localeCompare(
                    String(b.sailor_name || ''), undefined, { sensitivity: 'base' }
                );
            });

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

            function eventLogoSlug(path) {
                if (!path) return '';
                var base = String(path).split('/').pop() || '';
                base = base.replace(/\.[a-z0-9]+$/i, '');
                base = base.replace(/[-_]?(class[-_]?logo|event[-_]?logo|logo)$/i, '');
                return base.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
            }
            function chip(href, img, label, title) {
                var logo = img
                    ? '<span class="club-story-chip-logo"><img src="' + esc(img) + '" alt="' + esc(label) + '" loading="lazy" decoding="async" onerror="this.style.display=\'none\'"></span>'
                    : '<span class="club-story-chip-logo" aria-hidden="true"></span>';
                var inner = logo + '<span class="club-story-chip-label">' + esc(label) + '</span>';
                if (href) {
                    return '<a class="club-story-chip" href="' + esc(href) + '" title="' + esc(title || label) + '">' + inner + '</a>';
                }
                return '<span class="club-story-chip" title="' + esc(title || label) + '">' + inner + '</span>';
            }

            // Event logo chips → catalogue series, count for THIS class, most→least.
            // Zero-count logos do not belong here.
            var EVENT_LOGO_CATALOGUE = {
                'interclub.png': 'interclub',
                'dinghy-provincials-championship.png': 'dinghy-provincials-championship',
                'cape-classic-series.png': 'zvyc-cape-classic',
                'western-cape-dinghy-champs.png': 'western-cape-dinghy-champs',
                'wc-dinghy-champs-2026.jpg': 'western-cape-dinghy-champs',
                'tour-de-vlei.jpg': 'tour-de-vlei',
                'sa-sailing-youth-nationals.png': 'sa-sailing-youth-nationals',
                'youth-nationals-logo.png': 'sa-sailing-youth-nationals',
                'kyc-interclub.png': 'kyc-interclub',
                'knysna-yacht-club-interclub.png': 'kyc-interclub'
            };
            var eventByPath = {};
            regattas.forEach(function(r) {
                var p = (r.event_logo_url || '').trim();
                if (!p) return;
                if (!eventByPath[p]) eventByPath[p] = { path: p, n: 0 };
                eventByPath[p].n += 1;
            });
            var eventChips = Object.keys(eventByPath).map(function(p) {
                var row = eventByPath[p];
                if (!row.n) return null;
                var fn = String(p).split('/').pop().split('?')[0].toLowerCase();
                var catSlug = EVENT_LOGO_CATALOGUE[fn] || '';
                var lab = classNameFromLogoFilename(p) || 'Event';
                lab = String(lab).replace(/\b\w/g, function(c) { return c.toUpperCase(); });
                var href = catSlug ? ('/events-logos/' + encodeURIComponent(catSlug)) : '/events-logos';
                var countLab = row.n + ' event' + (row.n === 1 ? '' : 's');
                var logo = '<span class="club-story-chip-logo"><img src="' + esc(p) + '" alt="' + esc(lab) + '" loading="lazy" decoding="async" onerror="this.style.display=\'none\'"></span>';
                var inner = logo +
                    '<span class="club-story-chip-count">' + esc(countLab) + '</span>' +
                    '<span class="club-story-chip-label">' + esc(lab) + '</span>';
                return { n: row.n, lab: lab, html: '<a class="club-story-chip" href="' + esc(href) + '" title="' + esc(lab + ' — ' + countLab) + '">' + inner + '</a>' };
            }).filter(Boolean);
            eventChips.sort(function(a, b) {
                if (b.n !== a.n) return b.n - a.n;
                return String(a.lab || '').localeCompare(String(b.lab || ''));
            });
            eventChips = eventChips.map(function(x) { return x.html; });

            // Club logo chips
            var clubChips = clubs.map(function(c) {
                var code = (c.club_code || '').trim().toUpperCase();
                var slug = (c.club_slug || code.toLowerCase() || '').trim();
                var img = (c.club_logo_url || (code ? '/api/club-logo/' + code : '')).trim();
                return chip(slug ? '/club/' + encodeURIComponent(slug) : '', img, code || c.club_name || 'Club', code);
            });

            var meta = [];
            var sailorsN = sailors.length || (data.active_sailors != null ? Number(data.active_sailors) : 0);
            var regN = data.total_regattas != null ? Number(data.total_regattas) : regattas.length;
            var raceN = data.total_races != null ? Number(data.total_races) : 0;
            if (sailorsN) meta.push(sailorsN + ' sailor' + (sailorsN === 1 ? '' : 's'));
            if (regN) meta.push(regN + ' regatta' + (regN === 1 ? '' : 's'));
            if (raceN) meta.push(raceN.toLocaleString() + ' race' + (raceN === 1 ? '' : 's'));
            if (clubs.length) meta.push(clubs.length + ' club' + (clubs.length === 1 ? '' : 's'));

            var logoHtml = classLogo
                ? '<div class="club-page-logo-wrap"><img src="' + esc(classLogo) + '" alt="' + esc(className) + '" class="club-page-logo-img" loading="lazy" onerror="this.parentNode.style.display=\'none\'"></div>'
                : '';

            var strips = '';
            if (eventChips.length) {
                strips += '<div class="club-story-logo-row"><div class="club-story-logo-row-label">Events featuring ' + esc(className) + '</div><div class="club-story-logo-chips">' + eventChips.join('') + '</div></div>';
            }
            if (clubChips.length) {
                strips += '<div class="club-story-logo-row"><div class="club-story-logo-row-label">Clubs sailing ' + esc(className) + '</div><div class="club-story-logo-chips">' + clubChips.join('') + '</div></div>';
            }

            function rowLogo(src) {
                if (!src) return '';
                return '<img src="' + esc(src) + '" alt="" class="row-logo" loading="lazy" onerror="this.style.display=\'none\'">';
            }
            function rowAv(src) {
                var u = src || '/assets/avatars/default-youth.png';
                return '<img src="' + esc(u) + '" alt="" class="row-av" width="28" height="28" loading="lazy" decoding="async" onerror="this.onerror=null;this.src=\'/assets/avatars/default-youth.png\'">';
            }

            var regattaRows = regattas.map(function(r, i) {
                var slug = (r.regatta_slug || (r.regatta_id != null ? String(r.regatta_id) : '')) || '';
                var url = slug ? '/regatta/' + encodeURIComponent(slug) : '#';
                var eventName = esc(r.regatta_name || r.event_name || '');
                var eventDate = esc(r.event_date || r.end_date || r.start_date || '—');
                var hostCode = (r.club_code || '').trim().toUpperCase();
                var hostSlug = (r.club_slug || hostCode.toLowerCase() || '').trim();
                var hostLogo = (r.club_logo_url || (hostCode ? '/api/club-logo/' + hostCode : '')).trim();
                var hostCell = hostCode
                    ? (rowLogo(hostLogo) + (hostSlug ? '<a href="/club/' + encodeURIComponent(hostSlug) + '">' + esc(hostCode) + '</a>' : esc(hostCode)))
                    : '—';
                var evLogo = (r.event_logo_url || classLogo || '').trim();
                var eventEntries = (r.event_entries != null && r.event_entries !== '') ? r.event_entries
                    : ((r.fleet_size != null && r.fleet_size !== '') ? r.fleet_size : '—');
                var classEntries = (r.class_entries != null && r.class_entries !== '') ? r.class_entries
                    : ((r.fleet_size != null && r.fleet_size !== '') ? r.fleet_size : '—');
                var races = (r.races != null && r.races !== '') ? r.races : '—';
                var search = esc(((r.regatta_name || '') + ' ' + hostCode + ' ' + eventDate).toLowerCase());
                return '<tr data-search="' + search + '"><td>' + (i + 1) + '</td><td class="cell-left">' + rowLogo(evLogo) + '<a href="' + url + '">' + eventName + '</a></td><td class="cell-nowrap">' + eventDate + '</td><td class="cell-left hide-mobile">' + hostCell + '</td><td>' + eventEntries + '</td><td>' + classEntries + '</td><td class="hide-mobile">' + races + '</td></tr>';
            }).join('');

            var clubRows = clubs.map(function(c, i) {
                var code = (c.club_code || '').trim().toUpperCase();
                var slug = (c.club_slug || code.toLowerCase() || '').trim();
                var img = (c.club_logo_url || (code ? '/api/club-logo/' + code : '')).trim();
                var label = (code && c.club_name) ? (esc(code) + ' — ' + esc(c.club_name)) : esc(code || c.club_name || '');
                var clubCell = rowLogo(img) + (slug ? '<a href="/club/' + encodeURIComponent(slug) + '">' + label + '</a>' : label);
                var lastUrl = c.last_regatta_slug ? '/regatta/' + encodeURIComponent(c.last_regatta_slug) : '';
                var lastCell = (c.last_regatta_name || '').trim()
                    ? (lastUrl ? '<a href="' + lastUrl + '">' + esc(c.last_regatta_name) + '</a>' : esc(c.last_regatta_name))
                    : '—';
                var search = esc(((code || '') + ' ' + (c.club_name || '') + ' ' + (c.last_regatta_name || '')).toLowerCase());
                return '<tr data-search="' + search + '"><td>' + (i + 1) + '</td><td class="cell-left">' + clubCell + '</td><td>' + (c.sailors != null ? c.sailors : '—') + '</td><td>' + (c.races != null ? c.races : '—') + '</td><td>' + lastCell + '</td><td class="cell-nowrap">' + esc(c.last_regatta_date || '—') + '</td></tr>';
            }).join('');

            function ordinal(n) {
                var num = parseInt(n, 10);
                if (!num || isNaN(num)) return '';
                var dd = num % 100;
                if (dd >= 10 && dd <= 20) return num + 'th';
                var d = num % 10;
                return num + ({ 1: 'st', 2: 'nd', 3: 'rd' }[d] || 'th');
            }
            var sailorRows = sailors.map(function(s, i) {
                var slug = s.sailor_slug || '';
                var url = slug ? '/sailor/' + encodeURIComponent(slug) : '#';
                var clubCode = (s.club_code || '').trim().toUpperCase();
                var clubImg = (s.club_logo_url || (clubCode ? '/api/club-logo/' + clubCode : '')).trim();
                var clubCell = clubCode ? (rowLogo(clubImg) + '<a href="/club/' + encodeURIComponent(clubCode) + '">' + esc(clubCode) + '</a>') : '—';
                var rank = '';
                if (s.last_result_rank != null && s.last_fleet_size != null) {
                    rank = ordinal(s.last_result_rank) + '/' + s.last_fleet_size;
                } else if (s.last_result_rank != null) {
                    rank = ordinal(s.last_result_rank);
                } else {
                    rank = '—';
                }
                var lastUrl = s.last_regatta_slug ? '/regatta/' + encodeURIComponent(s.last_regatta_slug) : '';
                var lastCell = (s.last_regatta_name || '').trim()
                    ? (lastUrl ? '<a href="' + lastUrl + '">' + esc(s.last_regatta_name) + '</a>' : esc(s.last_regatta_name))
                    : '—';
                var search = esc(((s.sailor_name || '') + ' ' + clubCode + ' ' + (s.last_regatta_name || '')).toLowerCase());
                return '<tr data-search="' + search + '"><td>' + (i + 1) + '</td><td class="cell-left">' + rowAv(s.avatar_url) + '<a href="' + url + '">' + esc(s.sailor_name || s.sas_id || '') + '</a></td><td class="cell-left hide-mobile">' + clubCell + '</td><td>' + (s.races_in_class != null ? s.races_in_class : '—') + '</td><td>' + (s.regattas_in_class != null ? s.regattas_in_class : '—') + '</td><td class="cell-nowrap">' + esc(rank) + '</td><td>' + lastCell + '</td></tr>';
            }).join('');

            function section(id, title, filterId, tableHtml) {
                return '<div class="section-heading-row" id="' + id + '">' +
                    '<h2 class="section-title">' + esc(title) + '</h2>' +
                    '<input type="search" class="club-table-filter" data-table="' + filterId + '" placeholder="Search…" autocomplete="off">' +
                    '</div><div class="table-container club-table-scroll">' + tableHtml + '</div>';
            }

            var regattaTable = '<table class="table" id="class-regattas-table"><thead><tr><th>#</th><th>Event</th><th>Date</th><th class="hide-mobile">Host</th><th>Entries</th><th>' + esc(className || 'Class') + '</th><th class="hide-mobile">Races</th></tr></thead><tbody>' +
                (regattaRows || '<tr><td colspan="7">No regattas</td></tr>') + '</tbody></table>';
            var clubsTable = '<table class="table" id="class-clubs-table"><thead><tr><th>#</th><th>Club</th><th>Sailors</th><th>Races</th><th>Last regatta</th><th>Date</th></tr></thead><tbody>' +
                (clubRows || '<tr><td colspan="6">No clubs</td></tr>') + '</tbody></table>';
            var sailorsTable = '<table class="table" id="class-sailors-table"><thead><tr><th>#</th><th>Sailor</th><th class="hide-mobile">Club</th><th>Races</th><th>Regattas</th><th>Last result</th><th>Last regatta</th></tr></thead><tbody>' +
                (sailorRows || '<tr><td colspan="7">No sailors</td></tr>') + '</tbody></table>';

            var html = '' +
                '<div class="container club-page class-gold-page">' +
                '<div class="card elg-detail-page" style="border:none;box-shadow:none;padding:0;">' +
                '<div class="header club-page-header club-story-header">' +
                '<div class="club-story-inner">' +
                '<div class="club-story-title-row"><h1>' + esc(className) + '</h1>' + logoHtml + '</div>' +
                (meta.length ? '<p class="club-story-meta">' + esc(meta.join(' · ')) + '</p>' : '') +
                strips +
                '</div></div>' +
                section('regattas', 'Regattas (' + regattas.length + ')', 'class-regattas-table', regattaTable) +
                (clubs.length ? section('clubs', 'Clubs sailing ' + className + ' (' + clubs.length + ')', 'class-clubs-table', clubsTable) : '') +
                section('sailors', 'Sailors (' + sailors.length + ')', 'class-sailors-table', sailorsTable) +
                '</div></div>';

            cv.innerHTML = html;
            // Table filters
            cv.querySelectorAll('.club-table-filter').forEach(function(inp) {
                inp.addEventListener('input', function() {
                    var id = inp.getAttribute('data-table');
                    var table = document.getElementById(id);
                    if (!table) return;
                    var q = (inp.value || '').toLowerCase().trim();
                    table.querySelectorAll('tbody tr').forEach(function(tr) {
                        var hay = tr.getAttribute('data-search') || tr.textContent.toLowerCase();
                        tr.style.display = (!q || hay.indexOf(q) !== -1) ? '' : 'none';
                    });
                });
            });
            if (typeof attachSortableTables === 'function') attachSortableTables(cv);
        };

        // Initialize popup handlers
        document.addEventListener('DOMContentLoaded', async function() {
            _dbg('[DEBUG] index.html: DOMContentLoaded fired');
            _dbg('[DEBUG] index.html: Current cookies:', document.cookie);
            _dbg('[DEBUG] index.html: localStorage session:', localStorage.getItem('session'));
            window.__sailingsaGetSharedSession = window.__sailingsaGetSharedSession || async function() {
                try {
                    if (window.__sailingsaBootSession && typeof window.__sailingsaBootSession === 'object') {
                        return window.__sailingsaBootSession;
                    }
                    if (!window.__sailingsaBootSessionPromise) {
                        window.__sailingsaBootSessionPromise = (typeof checkSession === 'function'
                            ? checkSession()
                            : Promise.resolve({ valid: false }))
                            .then(function(session) {
                                window.__sailingsaBootSession = session || { valid: false };
                                return window.__sailingsaBootSession;
                            })
                            .catch(function() {
                                window.__sailingsaBootSession = { valid: false };
                                return window.__sailingsaBootSession;
                            });
                    }
                    return window.__sailingsaBootSessionPromise;
                } catch (_) {
                    return { valid: false };
                }
            };
            // #region debug-point A:dom-ready
            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('A', 'DOMContentLoaded fired', {
                path: (window.location && window.location.pathname) || '',
                search: (window.location && window.location.search) || ''
            }, 'dom-ready');
            // #endregion
            
            (function () {
                var dedupeIds = ['temp-landing-hero-image', 'temp-landing-claim-profile-banner'];
                for (var di = 0; di < dedupeIds.length; di++) {
                    var id = dedupeIds[di];
                    var nodes = document.querySelectorAll('[id="' + id + '"]');
                    for (var ni = 1; ni < nodes.length; ni++) {
                        try { nodes[ni].parentNode && nodes[ni].parentNode.removeChild(nodes[ni]); } catch (_) {}
                    }
                }
            })();

            // Initialize popup
            if (typeof initPopup === 'function') {
                initPopup();
            }
            
            // Add Back button handlers
            const backButtons = [
                'btnBackToPage',
                'btnBackToPageFromLogin',
                'btnBackToPageFromRestricted',
                'btnBackToPageFromSearch',
                'btnBackToPageFromConfirm',
                'btnBackToPageFromRelationship',
                'btnBackToPageFromVerification'
            ];
            
            backButtons.forEach(btnId => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        closePopupAndReturnToPage();
                    });
                }
            });
            
            // Ensure close button closes popup
            const popupClose = document.getElementById('popupClose');
            if (popupClose) {
                // Remove old listeners by cloning
                const newCloseBtn = popupClose.cloneNode(true);
                if (popupClose.parentNode) {
                    popupClose.parentNode.replaceChild(newCloseBtn, popupClose);
                }
                newCloseBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    closePopupAndReturnToPage();
                });
            }
            
            // Sailor profile URLs: strip hero/search/news/browse from DOM (DELETE not hide), then load profile. PROFILE BOX NO TOUCH — ONLY strip non-profile nodes.
            _dbg('[DEBUG] index.html: Checking sailor profile boot...');
            try {
                var pnormSailorBoot = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                var sailorSlugBoot = sailingsaIsSailorProfilePath(pnormSailorBoot)
                    ? pnormSailorBoot.slice('/sailor/'.length).split('/')[0]
                    : '';
                if (sailorSlugBoot && typeof window.loadSailorProfileRoute === 'function') {
                    stripDomForSailorProfile();
                    window.__sailingsaDeferPageContent = true;
                    setTimeout(function() {
                        Promise.resolve(window.loadSailorProfileRoute(sailorSlugBoot))
                            .then(function() { return updateHeaderAuthStatus(); })
                            .catch(function(eSailor) {
                                console.error('[sailor] loadSailorProfileRoute failed', eSailor);
                                return updateHeaderAuthStatus();
                            });
                    }, 0);
                    return;
                }
            } catch (error) {
                console.error('[DEBUG] index.html: Sailor profile boot error:', error);
            }

            // Class URLs: load after other DOMContentLoaded boot (setTimeout 0) so session/landing hooks run first; skip home updatePageContent.
            _dbg('[DEBUG] index.html: Checking session and updating header...');
            try {
                var pnormBoot = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                var classSlugBoot = (pnormBoot.indexOf('/class/') === 0) ? pnormBoot.slice('/class/'.length).split('/')[0] : '';
                if (classSlugBoot && typeof window.loadClassPageRoute === 'function') {
                    setMainColumnMode('class');
                    setTimeout(function() {
                        Promise.resolve(window.loadClassPageRoute(classSlugBoot))
                            .then(function() { return updateHeaderAuthStatus(); })
                            .catch(function(eClass) {
                                console.error('[class] loadClassPageRoute failed', eClass);
                                return updateHeaderAuthStatus();
                            });
                    }, 0);
                    return;
                }
                window.__sailingsaDeferPageContent = sailingsaIsSailorProfilePath(pnormBoot);
                // #region debug-point A:dom-boot-branch
                if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('A', 'DOMContentLoaded boot branch', {
                    path: pnormBoot,
                    classSlugBoot: classSlugBoot,
                    deferPageContent: !!window.__sailingsaDeferPageContent
                }, 'dom-boot');
                // #endregion
                var sharedBootSessionPromise = (typeof window.__sailingsaGetSharedSession === 'function')
                    ? window.__sailingsaGetSharedSession()
                    : Promise.resolve({ valid: false });
                await updateHeaderAuthStatus();
            } catch (error) {
                console.error('[DEBUG] index.html: Error updating header:', error);
                var pnormE = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                try { await updateHeaderAuthStatus(); } catch (e2) {}
            }
            try {
                if (typeof window.addEventListener === 'function') {
                    window.addEventListener('pageshow', function(pse) {
                        try {
                            if (pse && pse.persisted) {
                                if (typeof updateHeaderAuthStatus === 'function') {
                                    setTimeout(function(){ try { updateHeaderAuthStatus(); } catch(_x){} }, 0);
                                    setTimeout(function(){ try { updateHeaderAuthStatus(); } catch(_x){} }, 60);
                                }
                            }
                        } catch (_ps) {}
                    }, false);
                }
            } catch (_psk) {}

            // Sailor Search (above Welcome) — works for both public and logged-in
            const sailorSearchForm = document.getElementById('sailor-search-form');
            const sailorSearchInput = document.getElementById('sailor-search-input');
            const sailorSearchResults = document.getElementById('sailor-search-results');
            if (sailorSearchForm && sailorSearchInput && sailorSearchResults) {
                var searchMode = 'sailor'; // Toggle: 'sailor' (default) or 'regatta' — already on sailor search by default
                window.searchMode = searchMode;
                var sailorSearchDebounce = null;
                var sailorSearchAbort = null;
                var sailorSearchLastQuery = '';
                var regattaFromTopDebounce = null;
                var showSailorStatsInResultsFn;
                // #region debug-point search-global-cross-clear
                (function() {
                    if (window.__saGlobalCrossClearBound) return;
                    window.__saGlobalCrossClearBound = true;
                    window.__saSearchTrace = window.__saSearchTrace || [];
                    function __saTrace(tag, extra) {
                        try {
                            var regattaEl = document.getElementById('temp-landing-regatta-input');
                            window.__saSearchTrace.push({
                                t: Date.now(),
                                tag: String(tag || ''),
                                mode: window.searchMode || null,
                                activeId: (document.activeElement && document.activeElement.id) ? document.activeElement.id : '',
                                sailor: sailorSearchInput ? (sailorSearchInput.value || '') : '',
                                regatta: regattaEl ? (regattaEl.value || '') : '',
                                extra: extra || null
                            });
                            if (window.__saSearchTrace.length > 300) window.__saSearchTrace.splice(0, window.__saSearchTrace.length - 300);
                        } catch (_) {}
                    }
                    function hideProfile() {
                        try {
                            var _hp = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_hp) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        } catch (_) {}
                        try {
                            if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(true);
                        } catch (_) {}
                        sailorSearchResults.style.display = 'none';
                        sailorSearchResults.innerHTML = '';
                    }
                    function _installValueGuard(el, blockedMode, tag) {
                        try {
                            if (!el || el.__saValueGuardInstalled) return;
                            var desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement && window.HTMLInputElement.prototype ? window.HTMLInputElement.prototype : Object.getPrototypeOf(el), 'value');
                            if (!desc || typeof desc.get !== 'function' || typeof desc.set !== 'function') return;
                            Object.defineProperty(el, 'value', {
                                configurable: true,
                                enumerable: true,
                                get: function() { return desc.get.call(this); },
                                set: function(v) {
                                    var mode = (window.searchMode || 'sailor');
                                    if (mode === blockedMode) {
                                        __saTrace('guard-block', { tag: tag || '', mode: mode, attempted: String(v || '').slice(0, 50) });
                                        return desc.set.call(this, '');
                                    }
                                    return desc.set.call(this, v);
                                }
                            });
                            el.__saValueGuardInstalled = true;
                        } catch (_) {}
                    }
                    function _installGuardsIfReady() {
                        try {
                            var regattaEl = document.getElementById('temp-landing-regatta-input');
                            _installValueGuard(sailorSearchInput, 'regatta', 'sailor');
                            if (regattaEl) _installValueGuard(regattaEl, 'sailor', 'regatta');
                        } catch (_) {}
                    }
                    _installGuardsIfReady();
                    setTimeout(_installGuardsIfReady, 0);
                    setTimeout(_installGuardsIfReady, 250);
                    var container = document.getElementById('sailor-search-section') || sailorSearchForm;
                    var clearing = false;
                    function clearOtherInputs(activeEl) {
                        if (clearing) return;
                        clearing = true;
                        try {
                            var inputs = Array.prototype.slice.call(container.querySelectorAll('input[type=\"text\"], input[type=\"search\"]'));
                            inputs.forEach(function(i) {
                                if (i !== activeEl && i.value) {
                                    __saTrace('clear-other', { from: activeEl && activeEl.id ? activeEl.id : '', to: i.id || '' });
                                    i.value = '';
                                }
                            });
                        } catch (_) {}
                        clearing = false;
                    }
                    container.addEventListener('focusin', function(ev) {
                        try {
                            var _fp = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_fp) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        } catch (_) {}
                        var t = ev && ev.target;
                        if (!t || t.tagName !== 'INPUT') return;
                        __saTrace('focusin', { id: t.id || '', cls: t.className || '' });
                        hideProfile();
                        clearOtherInputs(t);
                    }, true);
                    container.addEventListener('input', function(ev) {
                        try {
                            var _ip = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_ip) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        } catch (_) {}
                        var t = ev && ev.target;
                        if (!t || t.tagName !== 'INPUT') return;
                        __saTrace('input', { id: t.id || '' });
                        clearOtherInputs(t);
                        try { setTimeout(function() { clearOtherInputs(t); }, 0); } catch (_) {}
                    }, true);
                    __saTrace('bound');
                })();
                // #endregion
                function showSailorProfilePlaceholder() {
                    try {
                        var _clsPathPh = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                        if (/^\/class\/\d+-/i.test(_clsPathPh)) return;
                        // Never clear a public /sailor/… profile (empty-search race was wiping the bio)
                        if (/^\/sailor\//i.test(_clsPathPh) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        if (sailorSearchResults.querySelector('#chosen-sailor-before-profile')) return;
                    } catch (_) {}
                    // #region debug-point C:placeholder
                    if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'showSailorProfilePlaceholder called', {
                        path: (window.location && window.location.pathname) || '',
                        hasChosenProfile: !!(sailorSearchResults && sailorSearchResults.querySelector && sailorSearchResults.querySelector('#chosen-sailor-before-profile'))
                    }, 'placeholder');
                    // #endregion
                    // Hide profile section when no sailor is logged in or selected
                    sailorSearchResults.style.display = 'none';
                    sailorSearchResults.innerHTML = '';
                }
                    function setSearchInteractionActive(active) {
                        window.__sailingsaSearchInteractionActive = !!active;
                    }
                    function isSearchInteractionActive() {
                        return window.__sailingsaSearchInteractionActive === true;
                    }
                    /** True while sailor search box has text — never paint logged-in profile over the list. */
                    function shouldSuppressLoggedInProfile() {
                        if (isSearchInteractionActive()) return true;
                        try {
                            if (sailorSearchInput && String(sailorSearchInput.value || '').trim() !== '') return true;
                        } catch (_) {}
                        return false;
                    }
                    function toProperCase(s) {
                        if (!s || typeof s !== 'string') return s;
                        return s.trim().replace(/\w+/g, function(w) { return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase(); });
                    }
                    showSailorStatsInResultsFn = async function(sid, name, club, classesSailed, options) {
                        var _perfStart = Date.now();
                        var _perfTraceId = "sailor-profile-" + _perfStart + "-" + Math.random().toString(36).slice(2, 8);
                        // #region debug-point B:show-sailor-start
                        if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('B', 'showSailorStatsInResults start', { sid: String(sid || ''), isLoggedInUser: !!(options && options.isLoggedInUser), path: (window.location && window.location.pathname) || '' }, _perfTraceId);
                        // #endregion
                        try {
                            var _clsPath = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (typeof sailingsaIsClassRoutePath === 'function' && sailingsaIsClassRoutePath(_clsPath)) return;
                        } catch (_) {}
                        options = options || {};
                        var isLoggedInUser = options.isLoggedInUser === true;
                        var _loggedInPaintGen = window.__sailorSearchGen || 0;
                        try {
                            var _sp = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_sp) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {
                                // Never wipe a valid public /sailor/ slug profile
                            } else if (isLoggedInUser && shouldSuppressLoggedInProfile()) {
                                // Search owns the results pane — do NOT clear the list.
                                return;
                            }
                        } catch (_) {
                            if (isLoggedInUser && shouldSuppressLoggedInProfile()) return;
                        }
                        function _abortLoggedInIfSearching() {
                            if (!isLoggedInUser) return false;
                            if ((window.__sailorSearchGen || 0) !== _loggedInPaintGen) return true;
                            return shouldSuppressLoggedInProfile();
                        }
                        // SSL sidecar (not live WoS) — cache once for all profile renders, including logged-in users.
                        try {
                            if (!window.__sslSailorProfilesPromise) {
                                var sslJsonUrl = (typeof API !== 'undefined' && API ? API : '') + '/data/ssl_sailor_profiles.json';
                                window.__sslSailorProfilesPromise = fetch(sslJsonUrl, { cache: 'no-store' })
                                    .then(function(r) { return r.ok ? r.json() : null; })
                                    .then(function(j) {
                                        window.__sslSailorProfiles = (j && j.sailors) ? j.sailors : {};
                                        return window.__sslSailorProfiles;
                                    })
                                    .catch(function() { window.__sslSailorProfiles = {}; return {}; });
                            }
                            await window.__sslSailorProfilesPromise;
                        } catch (_) { window.__sslSailorProfiles = window.__sslSailorProfiles || {}; }
                        // Rule: /sailor/{slug} always wins. Never inject logged-in home profile over it.
                        var urlLockedSlug = (typeof window.sailingsaUrlLockedSlug === 'string' && window.sailingsaUrlLockedSlug)
                            ? window.sailingsaUrlLockedSlug
                            : (typeof sailingsaSailorSlugFromPath === 'function' ? sailingsaSailorSlugFromPath() : '');
                        if (urlLockedSlug) {
                            window.sailingsaUrlLockedSlug = urlLockedSlug;
                            if (isLoggedInUser) return;
                        }
                        // Check if ANY user is logged in (not just if viewing own profile)
                        var isAnyUserLoggedIn = false;
                        try {
                            var _nestedSessionStart = Date.now();
                            var session = (options && options.session)
                                ? options.session
                                : (typeof window.__sailingsaGetSharedSession === 'function'
                                    ? await window.__sailingsaGetSharedSession()
                                    : (typeof checkSession === 'function' ? await checkSession() : { valid: false }));
                            isAnyUserLoggedIn = session.valid === true;
                            // #region debug-point B:nested-session
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('B', 'showSailorStatsInResults nested checkSession done', { ms: Date.now() - _nestedSessionStart, valid: !!session.valid, sasId: session.sas_id || (session.user && session.user.sas_id) || '', reusedSession: !!(options && options.session) }, _perfTraceId);
                            // #endregion
                        } catch (_) {}
                        // Use isAnyUserLoggedIn for regatta clickability (any logged-in user can click)
                        var canClickRegattas = isAnyUserLoggedIn;
                        var API = window.API_BASE || '';
                        var sidStr = String(sid || '').trim();
                        var membersRaw = [];
                        var members = [];
                        // Bare slug (e.g. lesley-rostek) → NAME: key for member/* API
                        if (sidStr && /^[a-z0-9]+(?:-[a-z0-9]+)+$/i.test(sidStr) && !/^\d+$/.test(sidStr) && !sidStr.toUpperCase().startsWith('TMP:') && !sidStr.toUpperCase().startsWith('NAME:')) {
                            sidStr = 'NAME:' + sidStr;
                            sid = sidStr;
                        }
                        // Numeric/TMP: search enriches profile metadata only — never replace identity key.
                        var memberLookupSid = sidStr;
                        var loggedInSessionUser = (isLoggedInUser && options && options.session && options.session.user) ? options.session.user : null;
                        var loggedInSessionSasId = (isLoggedInUser && options && options.session)
                            ? String(options.session.sas_id || (options.session.user && options.session.user.sas_id) || '').trim()
                            : '';
                        if (sidStr.match(/^\d+$/) || sidStr.toUpperCase().startsWith('TMP:')) {
                            var memberRes = await fetch(API + '/api/search?sas_id=' + encodeURIComponent(sidStr)).catch(function() { return null; });
                            try { membersRaw = (memberRes && memberRes.ok) ? await memberRes.json() : []; } catch (_) {}
                            members = Array.isArray(membersRaw) ? membersRaw : (membersRaw && typeof membersRaw === 'object' && (membersRaw.sas_id != null || membersRaw.surname != null || membersRaw.first_names != null) ? [membersRaw] : []);
                            if ((!Array.isArray(members) || !members.length) && loggedInSessionUser && loggedInSessionSasId === sidStr) members = [loggedInSessionUser];
                            sid = memberLookupSid;
                        } else if (sidStr.toUpperCase().startsWith('NAME:')) {
                            sid = sidStr;
                        }
                        if (_abortLoggedInIfSearching()) return;
                        sailorSearchResults.style.display = 'block';
                        // Keep SSR-injected .sailor-bio text before we replace the profile DOM
                        var ssrSailorBioText = '';
                        try {
                            var ssrBioEl = sailorSearchResults.querySelector('.sailor-bio p') || document.querySelector('.sailor-bio p');
                            if (ssrBioEl && ssrBioEl.textContent) ssrSailorBioText = String(ssrBioEl.textContent).trim();
                        } catch (_) {}
                        try {
                            var _parallelFetchStart = Date.now();
                            var _parallelResponses = await Promise.all([
                                fetch(API + '/api/member/' + encodeURIComponent(sid) + '/results').catch(function() { return null; }),
                                fetch(API + '/api/clubs').catch(function() { return null; })
                            ]);
                            var resultsRes = _parallelResponses[0];
                            var clubsRes = _parallelResponses[1];
                            // #region debug-point C:results-fetch
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'member results fetch done', { ms: Date.now() - _parallelFetchStart, ok: !!(resultsRes && resultsRes.ok), status: resultsRes ? resultsRes.status : 0, sid: String(sid || '') }, _perfTraceId);
                            // #endregion
                            // #region debug-point C:roles-fetch
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'member roles fetch skipped', { ms: 0, skipped: true, reason: 'unused-on-profile-first-paint', sid: String(sid || '') }, _perfTraceId);
                            // #endregion
                            // #region debug-point D:clubs-fetch
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('D', 'clubs fetch done', { ms: Date.now() - _parallelFetchStart, ok: !!(clubsRes && clubsRes.ok), status: clubsRes ? clubsRes.status : 0 }, _perfTraceId);
                            // #endregion
                            var resultsData = { results: [] };
                            try { resultsData = (resultsRes && resultsRes.ok) ? await resultsRes.json() : { results: [] }; } catch (_) {}
                            var results = (resultsData && Array.isArray(resultsData.results)) ? resultsData.results : (Array.isArray(resultsData) ? resultsData : []);
                            var m = (members.length && members[0]) ? members[0] : {};
                            var clubsList = [];
                            try { clubsList = (clubsRes && clubsRes.ok) ? await clubsRes.json() : []; } catch (_) {}
                            // #region debug-point C:profile-data-ready
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'profile data payloads ready', { totalMs: Date.now() - _perfStart, resultsCount: Array.isArray(results) ? results.length : 0, clubsCount: Array.isArray(clubsList) ? clubsList.length : 0, hadMembers: members.length }, _perfTraceId);
                            // #endregion
                            var clubsByCode = {};
                            var codeToSlug = {};
                            if (Array.isArray(clubsList)) clubsList.forEach(function(c) { var code = (c.code || '').toString().trim().toUpperCase(); if (code) { clubsByCode[code] = (c.province || '').toString().trim(); if (c.slug) codeToSlug[code] = c.slug; } });
                            var sailingDuration = '0 years & 0 months';
                            if (results.length) {
                                var dateStrings = results.map(function(r) { return r.start_date || r.end_date; }).filter(function(d) { return d && d !== 'N/A'; });
                                if (dateStrings.length) {
                                    var oldestStr = dateStrings.reduce(function(min, d) { return (min && min <= d) ? min : d; }, null);
                                    var oldest = new Date(oldestStr);
                                    if (!isNaN(oldest.getTime())) {
                                        var now = new Date();
                                        var years = now.getFullYear() - oldest.getFullYear();
                                        var months = now.getMonth() - oldest.getMonth();
                                        if (months < 0) { years -= 1; months += 12; }
                                        sailingDuration = years + ' years & ' + months + ' months';
                                    }
                                }
                            }
                            var regattaEventKeys = {};
                            var raceCount = 0;
                            var regattaRaceSeen = {};
                            results.forEach(function(r) {
                                if (isMemberResultSeriesRow(r) || !shouldIncludeMemberResultRow(r, results)) return;
                                if (!isMemberYouthSubFleetBlock(r.block_id)) {
                                    var eventKey = memberResultCareerEventKey(r);
                                    if (eventKey) regattaEventKeys[eventKey] = true;
                                }
                                if (shouldCountMemberResultRaces(r, regattaRaceSeen)) {
                                    if (typeof r.races_sailed === 'number') raceCount += r.races_sailed;
                                    else if (r.race_scores) {
                                        Object.keys(r.race_scores).forEach(function(k) {
                                            if (/^R\d+$/i.test(k)) {
                                                var score = r.race_scores[k];
                                                if (typeof score === 'number' || (typeof score === 'string' && !/^(DNC|DNS|DNF|DSQ|RET|OCS|BFD|UFD|SCP|RDG|DPI)$/i.test(score))) raceCount++;
                                            }
                                        });
                                    }
                                }
                            });
                            var regattaCount = Object.keys(regattaEventKeys).length;
                            var normalizeClassName = function(n) {
                                if (!n) return '';
                                var norm = n.trim();
                                if (/^OPTIMIST\s*(A|B|C)?$/i.test(norm)) {
                                    var match = norm.match(/^OPTIMIST\s*(A|B|C)?$/i);
                                    norm = 'Optimist ' + (match && match[1] ? match[1].toUpperCase() : 'A');
                                } else if (/^optimist\s*(a|b|c)?$/i.test(norm)) {
                                    var match = norm.match(/^optimist\s*(a|b|c)?$/i);
                                    norm = 'Optimist ' + (match && match[1] ? match[1].toUpperCase() : 'A');
                                }
                                return norm.replace(/\s+fleet\s*$/i, '').trim();
                            };
                            var classStats = {};
                            var classRegattaIds = {};
                            var classRegattaRaceSeen = {};
                            var classLastDates = {};
                            results.forEach(function(r) {
                                if (isMemberResultSeriesRow(r) || !shouldIncludeMemberResultRow(r, results)) return;
                                var rawClassName = (r.class_canonical || r.class_original || '').trim();
                                var className = normalizeClassName(rawClassName);
                                if (!className) return;
                                if (!classStats[className]) {
                                    classStats[className] = { rg: 0, r: 0, medals: { gold: 0, silver: 0, bronze: 0 } };
                                    classRegattaIds[className] = {};
                                    classRegattaRaceSeen[className] = {};
                                    classLastDates[className] = null;
                                }
                                if (r.regatta_id && !isMemberYouthSubFleetBlock(r.block_id) && !classRegattaIds[className][r.regatta_id]) {
                                    classStats[className].rg++;
                                    classRegattaIds[className][r.regatta_id] = true;
                                }
                                var regattaDate = r.end_date || r.start_date;
                                if (regattaDate) {
                                    var d = new Date(regattaDate);
                                    if (!isNaN(d.getTime()) && (!classLastDates[className] || d > classLastDates[className])) classLastDates[className] = d;
                                }
                                var classRaceKey = memberResultCareerEventKey(r) || '';
                                if (!isMemberYouthSubFleetBlock(r.block_id) && classRaceKey && !classRegattaRaceSeen[className][classRaceKey]) {
                                    classRegattaRaceSeen[className][classRaceKey] = true;
                                    if (r.race_scores && typeof r.race_scores === 'object') {
                                        Object.keys(r.race_scores).forEach(function(k) {
                                            if (/^R\d+$/i.test(k) && r.race_scores[k] !== null && r.race_scores[k] !== undefined && r.race_scores[k] !== '') classStats[className].r++;
                                        });
                                    } else if (typeof r.races_sailed === 'number' && r.races_sailed > 0) classStats[className].r += r.races_sailed;
                                }
                                var rankNum = null;
                                if (typeof r.rank === 'number') rankNum = r.rank;
                                else if (r.rank && typeof r.rank === 'string') { var match = String(r.rank).match(/^\s*([0-9]+)/); if (match) rankNum = Number(match[1]); }
                                if (rankNum === 1) classStats[className].medals.gold++;
                                else if (rankNum === 2) classStats[className].medals.silver++;
                                else if (rankNum === 3) classStats[className].medals.bronze++;
                            });
                            var exactMemberRow = null;
                            if (Array.isArray(members) && members.length) {
                                exactMemberRow = members.find(function(row) {
                                    return String((row && row.sas_id) || '').trim() === String(sid || '').trim();
                                }) || null;
                                if (!exactMemberRow && name) {
                                    var targetName = String(name || '').trim().toLowerCase();
                                    exactMemberRow = members.find(function(row) {
                                        var fullName = [row && (row.first_name || row.first_names), row && (row.last_name || row.surname)].filter(Boolean).join(' ').trim().toLowerCase();
                                        return fullName && fullName === targetName;
                                    }) || null;
                                }
                            }
                            var memberSource = exactMemberRow || m || {};
                            var memberClubVal = memberSource.club_abbrev || memberSource.club_code || memberSource.club || memberSource.primary_club || memberSource.club_1 || memberSource.club_name || memberSource.country || '';
                            var sasMemberClubVal = memberClubVal || m.club_abbrev || m.club_code || m.club || m.primary_club || m.club_1 || m.club_name || '';
                            var clubVal = sasMemberClubVal || (club && club !== '—' ? club : '');
                            if (clubVal && clubVal !== '—') {
                                try {
                                    var clubTrim = String(clubVal).trim();
                                    if (clubTrim && clubTrim.length > 5 && Array.isArray(clubsList)) {
                                        var clubMatch = clubsList.find(function(c) {
                                            var code = String((c && (c.code || c.club_code)) || '').trim().toUpperCase();
                                            var full = String((c && (c.club_name || c.name || c.full_name)) || '').trim().toLowerCase();
                                            return (code && code === clubTrim.toUpperCase()) || (full && full === clubTrim.toLowerCase());
                                        }) || null;
                                        if (clubMatch && (clubMatch.code || clubMatch.club_code)) clubVal = clubMatch.code || clubMatch.club_code;
                                    }
                                } catch (_eClubNameResolve) {}
                            }
                            var ageVal = '';
                            var ageFromYearOnly = false;
                            var ageReferenceYear = (typeof window.AGE_REFERENCE_YEAR === 'number' && window.AGE_REFERENCE_YEAR > 1900) ? window.AGE_REFERENCE_YEAR : new Date().getFullYear();
                            // Prefer year_of_birth/born with reference year so season age (e.g. 15/16) is consistent; only use m.age when no birth year
                            if (m.born !== undefined && m.born !== null && m.born !== '' && !isNaN(m.born)) {
                                ageVal = ageReferenceYear - parseInt(m.born, 10);
                                ageFromYearOnly = true;
                            } else if (m.year_of_birth !== undefined && m.year_of_birth !== null && m.year_of_birth !== '' && !isNaN(m.year_of_birth)) {
                                ageVal = ageReferenceYear - parseInt(m.year_of_birth, 10);
                                ageFromYearOnly = true;
                            } else if (m.age !== undefined && m.age !== null && m.age !== '' && !isNaN(m.age)) {
                                ageVal = parseInt(m.age, 10);
                            }
                            var nameFromMember = [memberSource.first_name || memberSource.first_names, memberSource.last_name || memberSource.surname].filter(Boolean).join(' ').trim() || memberSource.full_name || '';
                            var nameD = toProperCase((name && name.trim()) ? name.trim() : nameFromMember);
                            // Split name into first and last name for two-line display
                            var nameParts = nameD.trim().split(/\s+/);
                            var firstName = nameParts.length > 0 ? nameParts[0] : nameD;
                            var lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : '';
                            var clubD = (clubVal && clubVal !== '—') ? String(clubVal).trim().toUpperCase() : '—';
                            // International / no-SAS sailors (e.g. Rob Skinner): WoS country overrides bogus result-club (HYC)
                            var sidStrCheck = String(sid || '');
                            var noRealSasId = /^NAME:/i.test(sidStrCheck) || /^TMP:/i.test(sidStrCheck);
                            var sslIntl = null;
                            try {
                                var _sslMapEarly = (typeof window !== 'undefined' && window.__sslSailorProfiles) ? window.__sslSailorProfiles : null;
                                sslIntl = _sslMapEarly && sid != null ? (_sslMapEarly[String(sid)] || null) : null;
                            } catch (_eSslEarly) { sslIntl = null; }
                            // Known international name-identities (no SAS ID) until/alongside SSL sidecar
                            var nameIntlOverrides = {
                                'NAME:ROB-SKINNER': { club: 'UK', country: 'GBR' }
                            };
                            var nameOverride = nameIntlOverrides[sidStrCheck.toUpperCase()] || null;
                            var sslCountryCode = (sslIntl && sslIntl.ssl_country_code) ? String(sslIntl.ssl_country_code).toUpperCase() : (nameOverride ? nameOverride.country : '');
                            var sslDisplayClub = (sslIntl && sslIntl.ssl_display_club) ? String(sslIntl.ssl_display_club).toUpperCase() : (nameOverride ? nameOverride.club : '');
                            var isIntlSailor = !!(sslCountryCode && !/^(RSA|ZA)$/i.test(sslCountryCode)) || !!nameOverride;
                            if ((isIntlSailor || nameOverride) && sslDisplayClub) {
                                clubD = sslDisplayClub;
                            }
                            var ageDisplay = (ageVal && !isNaN(ageVal) && ageVal > 0) ? (' Age ' + ageVal + '/' + (ageVal + 1) + ' Yrs') : '';
                            var classEntries = Object.keys(classStats).sort(function(a, b) {
                                var dateA = classLastDates[a] || new Date(0);
                                var dateB = classLastDates[b] || new Date(0);
                                return dateB - dateA;
                            });
                            var registeredClassHint = String(classesSailed || memberSource.class_name || memberSource.primary_class || '').trim();
                            if (registeredClassHint && registeredClassHint !== '—') {
                                var regClassNorm = normalizeClassName(registeredClassHint);
                                if (regClassNorm && !classStats[regClassNorm]) {
                                    classStats[regClassNorm] = { rg: 0, r: 0, medals: { gold: 0, silver: 0, bronze: 0 } };
                                    classEntries = Object.keys(classStats).sort(function(a, b) {
                                        var dateA = classLastDates[a] || new Date(0);
                                        var dateB = classLastDates[b] || new Date(0);
                                        return dateB - dateA;
                                    });
                                }
                            }
                            // Header total = sum of per-class regatta badges (matches class sections)
                            regattaCount = classEntries.reduce(function(sum, cn) {
                                return sum + ((classStats[cn] && classStats[cn].rg) || 0);
                            }, 0);
                            var backBtn = isLoggedInUser ? '' : '<a href="/" class="js-go-home" id="sailor-stats-back-btn" title="Return to https://sailingsa.co.za/" style="margin-bottom:8px;padding:6px 12px;font-size:13px;font-weight:600;color:#fff;background:#001f3f;border:none;border-radius:6px;cursor:pointer;display:inline-block;text-decoration:none;">Back to results</a>';
                            var career = '<div class="sailor-stats-section"><h3 style="font-size:16px;margin:8px 0 6px 0;">Career Summary</h3>' +
                                '<div class="sailor-stats-row"><span class="sailor-stats-label">Sailing:</span><span class="sailor-stats-value">' + sailingDuration + '</span></div>' +
                                '<div class="sailor-stats-row"><span class="sailor-stats-label">Total Regattas:</span><span class="sailor-stats-value">' + regattaCount + '</span></div>' +
                                '<div class="sailor-stats-row"><span class="sailor-stats-label">Total Races:</span><span class="sailor-stats-value">' + raceCount + '</span></div></div>';
                            var classHtml = '';
                            if (classEntries.length) {
                                classHtml = '<div class="sailor-stats-section"><h3 style="font-size:16px;margin:8px 0 6px 0;">Breakdown by Class</h3>';
                                classEntries.forEach(function(className) {
                                    var st = classStats[className];
                                    var medals = st.medals || { gold: 0, silver: 0, bronze: 0 };
                                    var totalM = medals.gold + medals.silver + medals.bronze;
                                    var medalsText = totalM > 0 ? ('\uD83C\uDFC7' + medals.gold + ' \uD83C\uDFC8' + medals.silver + ' \uD83C\uDFC9' + medals.bronze) : '';
                                    classHtml += '<div class="sailor-stats-class-line"><span class="sailor-stats-label" style="font-weight:700;">' + className + ':</span><span class="sailor-stats-value">' + (st.rg || 0) + ' regattas, ' + (st.r || 0) + ' races</span>';
                                    if (medalsText) classHtml += ' <span class="medal-box" style="background:#fff3e0;border:1px solid #ffb74d;border-radius:3px;padding:2px 4px;font-weight:600;color:#e65100;font-size:11px;">' + medalsText + '</span>';
                                    classHtml += '</div>';
                                });
                                classHtml += '</div>';
                            }
                            var regattaHistoryRows = [];
                            results.forEach(function(r) {
                                if (isMemberResultSeriesRow(r) || !r.regatta_id || !shouldIncludeMemberResultRow(r, results)) return;
                                var rawClass = (r.class_canonical || r.class_original || '').trim();
                                var classDisplay = normalizeClassName(rawClass) || rawClass || '—';
                                var dateStr = r.end_date || r.start_date || '';
                                var races = 0;
                                if (typeof r.races_sailed === 'number') races = r.races_sailed;
                                else if (r.race_scores && typeof r.race_scores === 'object') {
                                    Object.keys(r.race_scores).forEach(function(k) {
                                        if (/^R\d+$/i.test(k)) races++;
                                    });
                                }
                                var rankNum = null;
                                if (typeof r.rank === 'number') rankNum = r.rank;
                                else if (r.rank && typeof r.rank === 'string') { var match = String(r.rank).match(/^\s*([0-9]+)/); if (match) rankNum = Number(match[1]); }
                                var entries = r.entries != null ? r.entries : 0;
                                var sailNumber = r.sail_number || r.sail_no || '';
                                var clubCode = (r.club || r.club_abbrev || r.club_raw || '').toString().trim().toUpperCase();
                                regattaHistoryRows.push({
                                    regatta_id: r.regatta_id,
                                    block_id: r.block_id || '',
                                    event_name: memberResultDisplayEventName(r),
                                    highlight_event_name: memberResultHighlightEventName(r),
                                    result_href: memberResultRegattaHref(r),
                                    dateStr: dateStr,
                                    className: classDisplay,
                                    races: races,
                                    rank: rankNum,
                                    entries: entries,
                                    sail_number: sailNumber,
                                    club: clubCode,
                                    isSubFleetChild: isMemberYouthSubFleetBlock(r.block_id || '')
                                });
                            });
                            regattaHistoryRows.sort(function(a, b) { return (b.dateStr || '').localeCompare(a.dateStr || ''); });
                            // #region debug-point E:profile-render-ready
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('E', 'profile render ready', { totalMs: Date.now() - _perfStart, regattaRows: regattaHistoryRows.length, classEntries: classEntries.length }, _perfTraceId);
                            // #endregion
                            var escapeHtml = function(s) { if (s == null || s === '') return ''; return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };
                            var formatRegattaDate = function(str) {
                                if (!str) return 'N/A';
                                var d = new Date(str);
                                if (isNaN(d.getTime())) return 'N/A';
                                var day = String(d.getDate()).padStart(2, '0');
                                var mon = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()];
                                var year = d.getFullYear();
                                return day + ' ' + mon + ' ' + year;
                            };
                            
                            // Prepare header data (header will be built after media fetch to get avatar)
                            var classesDisplay = classEntries.length > 0 ? classEntries.join(' / ') : '—';
                                var provinceVal = (memberSource.province || memberSource.province_name || m.province || m.province_name || '').trim();
                            if (!provinceVal && clubD && clubD !== '—' && clubsByCode[clubD]) provinceVal = clubsByCode[clubD];
                            var provinceDisplay = provinceVal ? toProperCase(provinceVal) : '—';
                            // Map full province names to codes so we load proper province icons (WC.png, KZN.png, etc.)
                            var provinceNameToCode = { 'Western Cape': 'WC', 'Eastern Cape': 'EC', 'Northern Cape': 'NC', 'Free State': 'FS', 'KwaZulu-Natal': 'KZN', 'KwaZulu Natal': 'KZN', 'Gauteng': 'GP', 'Mpumalanga': 'MP', 'Limpopo': 'LP', 'North West': 'NW', 'Western cape': 'WC', 'Eastern cape': 'EC', 'Northern cape': 'NC', 'Free state': 'FS', 'Gauteng': 'GP', 'Mpumalanga': 'MP', 'Limpopo': 'LP', 'North west': 'NW' };
                            var provinceCode = (provinceVal && provinceVal.length <= 4) ? String(provinceVal).toUpperCase() : (provinceNameToCode[provinceVal] || (provinceVal ? provinceVal.replace(/\s+/g, ' ').trim() : ''));
                            if (provinceCode && provinceCode.length > 4) provinceCode = provinceNameToCode[provinceVal] || '';
                            // International: no province badge (flag lives only in club box)
                            if (isIntlSailor) {
                                provinceDisplay = '—';
                                provinceCode = '';
                            }
                            var lastActiveDate = '—';
                            if (regattaHistoryRows.length > 0 && regattaHistoryRows[0].dateStr) {
                                var lastDate = new Date(regattaHistoryRows[0].dateStr);
                                if (!isNaN(lastDate.getTime())) {
                                    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                                    lastActiveDate = months[lastDate.getMonth()] + ' ' + lastDate.getFullYear();
                                }
                            }
                            
                            // Generate initials for avatar fallback
                            var initials = '—';
                            if (nameD && nameD.trim()) {
                                var nameParts = nameD.trim().split(/\s+/);
                                if (nameParts.length >= 2) {
                                    initials = (nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)).toUpperCase();
                                } else if (nameParts.length === 1 && nameParts[0].length >= 2) {
                                    initials = nameParts[0].substring(0, 2).toUpperCase();
                                } else if (nameParts[0].length === 1) {
                                    initials = nameParts[0].toUpperCase();
                                }
                            }
                            
                            // Header will be built after media fetch (to get avatar)
                            var header = '';
                            var regattaHistorySectionHtml = '';
                            
                            // For logged-in sailors: show profile boxes and class-based sections
                            if (isLoggedInUser) {
                                // Calculate sailing duration
                                var sailingDuration = '0 years & 0 months';
                                if (regattaHistoryRows.length > 0) {
                                    var dates = regattaHistoryRows.map(function(r) { return r.dateStr; }).filter(function(d) { return d && d !== 'N/A'; });
                                    if (dates.length > 0) {
                                        var oldest = new Date(Math.min.apply(null, dates.map(function(d) { return new Date(d).getTime(); })));
                                        var now = new Date();
                                        var years = now.getFullYear() - oldest.getFullYear();
                                        var months = now.getMonth() - oldest.getMonth();
                                        if (months < 0) { years -= 1; months += 12; }
                                        sailingDuration = years > 0 ? (years + ' year' + (years !== 1 ? 's' : '') + ' & ' + months + ' month' + (months !== 1 ? 's' : '')) : (months + ' month' + (months !== 1 ? 's' : ''));
                                    }
                                }
                                
                                // Build profile boxes HTML
                                var profileBoxesHtml = [];
                                var fullNameEsc = escapeHtml(nameD);
                                var sailorIdEsc = escapeHtml(String(sid));
                                var ageDisplayEsc = (ageVal && !isNaN(ageVal) && ageVal > 0) ? (ageVal + '/' + (ageVal + 1) + ' yrs') : '-';
                                var clubEsc = escapeHtml(clubD);
                                
                                // Box 1: Personal Profile > Name
                                profileBoxesHtml.push('<span style="background: #e1bee7 !important; border: 1px solid #ce93d8 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 13px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap; flex-shrink: 0;">Personal Profile &gt; ' + fullNameEsc + '</span>');
                                
                                // Box 2: ID
                                profileBoxesHtml.push('<div style="background: #e1bee7 !important; border: 1px solid #ce93d8 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">ID:</span> <span style="font-weight: 700;">' + sailorIdEsc + '</span></div>');
                                
                                // Box 3: Age
                                profileBoxesHtml.push('<div style="background: #ffe0b2 !important; border: 1px solid #ffb74d !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #8B4513 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">Age:</span> <span style="font-weight: 700;">' + ageDisplayEsc + '</span></div>');
                                
                                // Box 4: Club
                                profileBoxesHtml.push('<div style="background: #e3f2fd !important; border: 1px solid #90caf9 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">Club:</span> <span style="font-weight: 700;">' + clubEsc + '</span></div>');
                                
                                // Box 5: Sailing Duration
                                profileBoxesHtml.push('<div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">Sailing:</span> <span style="font-weight: 700;">' + escapeHtml(sailingDuration) + '</span></div>');
                                
                                // Box 6: Regattas
                                profileBoxesHtml.push('<div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">Regatta\'s =</span> <span style="font-weight: 700;">' + regattaCount + '</span></div>');
                                
                                // Box 7: Races
                                profileBoxesHtml.push('<div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">Races =</span> <span style="font-weight: 700;">' + raceCount + '</span></div>');
                                
                                // Boxes 8-12: Classes (Main, 2nd, 3rd, 4th, 5th)
                                var classColors = [
                                    {bg: '#64b5f6', border: '#42a5f5'},
                                    {bg: '#90caf9', border: '#64b5f6'},
                                    {bg: '#b3e5fc', border: '#81d4fa'},
                                    {bg: '#e1f5fe', border: '#b3e5fc'},
                                    {bg: '#f3e5f5', border: '#ce93d8'}
                                ];
                                var classLabels = ['Main Class', '2nd Class', '3rd Class', '4th Class', '5th Class'];
                                for (var i = 0; i < Math.min(classEntries.length, 5); i++) {
                                    var classNameEsc = escapeHtml(classEntries[i]);
                                    profileBoxesHtml.push('<div style="background: ' + classColors[i].bg + ' !important; border: 1px solid ' + classColors[i].border + ' !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;"><span style="font-weight: 700;">' + classLabels[i] + ':</span> <span style="font-weight: 700;">' + classNameEsc + '</span></div>');
                                }
                                
                                // Box: Sailor Stats button
                                var fullNameEscaped = fullNameEsc.replace(/'/g, "\\'");
                                profileBoxesHtml.push('<div style="background: #d32f2f !important; border: 1px solid #b71c1c !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #ffffff !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap; cursor: pointer;" onclick="if(typeof showSailorStats === \'function\') { showSailorStats(\'' + sailorIdEsc + '\', \'' + fullNameEscaped + '\', event); }">Sailor Stats</div>');
                                
                                // Group regattas by class
                                var regattasByClass = {};
                                regattaHistoryRows.forEach(function(row) {
                                    var className = row.className || '—';
                                    if (!regattasByClass[className]) {
                                        regattasByClass[className] = [];
                                    }
                                    regattasByClass[className].push(row);
                                });
                                
                                // Sort classes by last date (most recent first)
                                var sortedClassNames = Object.keys(regattasByClass).sort(function(a, b) {
                                    var dateA = regattasByClass[a].length > 0 ? new Date(regattasByClass[a][0].dateStr || 0) : new Date(0);
                                    var dateB = regattasByClass[b].length > 0 ? new Date(regattasByClass[b][0].dateStr || 0) : new Date(0);
                                    return dateB - dateA;
                                });
                                
                                // Get rankings data for class-specific stats
                                var rankings = m.rankings || [];
                                var rankingsByClass = {};
                                rankings.forEach(function(rank) {
                                    if (rank.class_code) {
                                        var classKey = normalizeClassName(rank.class_code.trim());
                                        if (classKey) {
                                            rankingsByClass[classKey] = rank;
                                        }
                                    }
                                });
                                
                                // Calculate per-class sailing duration
                                var classSailingDurations = {};
                                sortedClassNames.forEach(function(className) {
                                    var classRegattas = regattasByClass[className];
                                    if (classRegattas.length > 0) {
                                        var dates = classRegattas.map(function(r) { return r.dateStr; }).filter(function(d) { return d && d !== 'N/A'; });
                                        if (dates.length > 0) {
                                            var oldest = new Date(Math.min.apply(null, dates.map(function(d) { return new Date(d).getTime(); })));
                                            var newest = new Date(Math.max.apply(null, dates.map(function(d) { return new Date(d).getTime(); })));
                                            var now = new Date();
                                            var startDate = oldest < newest ? oldest : newest;
                                            var years = now.getFullYear() - startDate.getFullYear();
                                            var months = now.getMonth() - startDate.getMonth();
                                            if (months < 0) { years -= 1; months += 12; }
                                            classSailingDurations[className] = years > 0 ? (years + ' year' + (years !== 1 ? 's' : '') + ' & ' + months + ' month' + (months !== 1 ? 's' : '')) : (months + ' month' + (months !== 1 ? 's' : ''));
                                        }
                                    }
                                });
                                
                                // Build class-based sections HTML
                                var classSectionsHtml = '';
                                sortedClassNames.forEach(function(className) {
                                    var classRegattas = assignMemberRegattaDisplayNumbers(
                                        regattasByClass[className].slice().sort(memberClassRegattaSort)
                                    );
                                    
                                    // Get class statistics
                                    var classStat = classStats[className] || { rg: 0, r: 0, medals: { gold: 0, silver: 0, bronze: 0 } };
                                    var classRegattaCount = classStat.rg || 0;
                                    var classRaceCount = classStat.r || 0;
                                    var medals = classStat.medals || { gold: 0, silver: 0, bronze: 0 };
                                    var classSailingDuration = classSailingDurations[className] || '0 years & 0 months';
                                    
                                    // Get ranking info for this class
                                    var classRanking = rankingsByClass[className];
                                    var rankingText = '';
                                    if (classRanking) {
                                        var rankNum = classRanking.rank || classRanking.position;
                                        var score = classRanking.score || classRanking.total_score || classRanking.points;
                                        var totalSailors = classRanking.total_sailors || classRanking.total_entries || classRanking.total;
                                        if (rankNum != null) {
                                            var rankSuffix = rankNum === 1 ? 'st' : rankNum === 2 ? 'nd' : rankNum === 3 ? 'rd' : 'th';
                                            rankingText = 'Ranked ' + rankNum + rankSuffix;
                                            if (score != null) {
                                                rankingText += ' (Score: ' + score + ')';
                                            }
                                            if (totalSailors != null) {
                                                rankingText += ' out of ' + totalSailors + ' sailors';
                                            }
                                        }
                                    }
                                    
                                    // Determine class label (Main Class, 2nd Class, 3rd Class, etc.)
                                    var classIndex = sortedClassNames.indexOf(className);
                                    var classLabels = ['Main Class', '2nd Class', '3rd Class', '4th Class', '5th Class'];
                                    var classLabel = classIndex < classLabels.length ? classLabels[classIndex] : (classIndex + 1) + 'th Class';
                                    
                                    // Build badges HTML
                                    var badgesHtml = [];
                                    
                                    // Badge 1: Class label > Regatta's =X/ Races =Y (show for ALL classes)
                                    badgesHtml.push('<div style="background: #64b5f6 !important; border: 1px solid #42a5f5 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">' + escapeHtml(classLabel) + ' &gt; Regatta\'s =' + classRegattaCount + '/ Races =' + classRaceCount + '</div>');
                                    
                                    // Badge 2: Sailing duration
                                    badgesHtml.push('<div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">Sailing: ' + escapeHtml(classSailingDuration) + '</div>');
                                    
                                    // Badge 3: Ranking (if available)
                                    if (rankingText) {
                                        badgesHtml.push('<div style="background: #e0e0e0 !important; border: 1px solid #bdbdbd !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">' + escapeHtml(rankingText) + '</div>');
                                    }
                                    
                                    // Badge 4: Medal counts (correct podium icons: 🥇 🥈 🥉)
                                    if (medals.gold > 0 || medals.silver > 0 || medals.bronze > 0) {
                                        var medalText = '';
                                        if (medals.gold > 0) medalText += '\uD83E\uDD47' + medals.gold;
                                        if (medals.silver > 0) {
                                            if (medalText) medalText += ' | ';
                                            medalText += '\uD83E\uDD48' + medals.silver;
                                        }
                                        if (medals.bronze > 0) {
                                            if (medalText) medalText += ' | ';
                                            medalText += '\uD83E\uDD49' + medals.bronze;
                                        }
                                        badgesHtml.push('<div style="background: #ffe0b2 !important; border: 1px solid #ffb74d !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #e65100 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">' + medalText + '</div>');
                                    }
                                    
                                    var classTableRows = classRegattas.map(function(row) {
                                        return renderMemberRegattaTableRow(row, className, escapeHtml, formatRegattaDate, canClickRegattas);
                                    }).join('');
                                    
                                    var classNameEsc = escapeHtml(className);
                                    var badgesRowHtml = badgesHtml.length > 0 ? '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; align-items: center;">' + badgesHtml.join('') + '</div>' : '';
                                    classSectionsHtml += '<div class="class-results-section" style="margin-bottom: 0.5rem;"><h4 style="font-size: 16px; margin: 6px 0 4px 0; color: #1e3a8a; font-weight: 700;">' + classNameEsc + ' Results</h4>' + badgesRowHtml + '<div style="overflow-x: auto;"><table class="snapshot-table"><thead><tr><th>No.</th><th>Regatta</th><th>Date</th><th>Sail No</th><th>Club</th><th>Rank</th></tr></thead><tbody>' + classTableRows + '</tbody></table></div></div>';
                                });
                                
                                regattaHistorySectionHtml = '<div class="sailor-career-regatta-history" style="margin-top: 1rem;"><div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 1rem; align-items: center;">' + profileBoxesHtml.join('') + '</div>' + classSectionsHtml + '</div>';
                            } else {
                                // For public users: single table format
                                if (regattaHistoryRows.length === 0) {
                                    regattaHistorySectionHtml = '<div class="sailor-career-regatta-history"><h2>Sailing Career – Regatta History</h2><p class="sailor-career-subtitle">No regatta history available.</p></div>';
                                } else {
                                    var publicRows = assignMemberRegattaDisplayNumbers(regattaHistoryRows.slice().sort(memberClassRegattaSort));
                                    var tableRows = publicRows.map(function(row) {
                                        return renderMemberRegattaTableRow(row, row.className || '—', escapeHtml, formatRegattaDate, canClickRegattas);
                                    }).join('');
                                    var subtitleText = canClickRegattas ? 'Click a regatta to view full results and public coverage.' : 'Click a regatta to sign in and view detailed results.';
                                    regattaHistorySectionHtml = '<div class="sailor-career-regatta-history"><h2>Sailing Career – Regatta History</h2><p class="sailor-career-subtitle">' + subtitleText + '</p><div style="overflow-x: auto;"><table class="snapshot-table"><thead><tr><th>No.</th><th>Regatta</th><th>Date</th><th>Sail No</th><th>Club</th><th>Rank</th></tr></thead><tbody>' + tableRows + '</tbody></table></div></div>';
                                }
                            }
                            var mentionsSectionHtml = '';
                            var summaryCardHtml = '';
                            var aiOverviewHtml = '';
                            var sailorBioHtml = '';
                            var highlightsHtml = '';
                            try {
                                var mentionItems = [];
                                var mentionsData = { items: [] };
                                // Keep the approved sailor template fed by the same public data whether the viewer is logged in or not.
                                if (!sid || String(sid).trim() === '' || isNaN(Number(sid))) {
                                    console.error("[media] Invalid sa_id for public-mentions:", sid);
                                    console.error("[media] sa_id must be numeric; stopping.");
                                } else {
                                    var mentionsRes = await fetch(API + '/api/member/' + encodeURIComponent(sid) + '/public-mentions').catch(function(err) { 
                                        console.error("Fetch error:", err);
                                        return null; 
                                    });
                                    if (!mentionsRes) {
                                        console.error("No response from API");
                                    } else if (!mentionsRes.ok) {
                                        console.error("API response not OK:", mentionsRes.status, mentionsRes.statusText);
                                    } else {
                                        try {
                                            var body = await mentionsRes.text();
                                            if (body && body.trim()) {
                                                try {
                                                    mentionsData = JSON.parse(body);
                                                } catch (_) {
                                                    var ct = mentionsRes.headers.get("content-type") || "";
                                                    if (ct.indexOf("application/json") !== -1) mentionsData = { items: [] };
                                                }
                                            }
                                        } catch (parseErr) {
                                            console.error("Error fetching media feed:", parseErr);
                                        }
                                        mentionItems = Array.isArray(mentionsData.items) ? mentionsData.items : [];
                                    }
                                    var mediaScore = mentionsData && mentionsData.media_score;
                                    if (mediaScore != null && Number(mediaScore) >= 4 && mentionItems.length === 0) {
                                        console.error("[media] Sailor has media_score >= 4 but sailor_public_mentions = 0. Run jobs/refresh_sailor_media_recent.py to ingest content.");
                                    }
                                }
                                
                                // Extract AI Overview Summary if available; fall back to resolve/SSR sailor bio
                                var aiOverviewSummary = mentionsData && mentionsData.ai_overview_summary;
                                var resolveBioText = '';
                                try {
                                    var resolveSid = String(sid || '').replace(/^NAME:/i, '').trim();
                                    if (/^\d+$/.test(resolveSid)) {
                                        var resolveRes = await fetch(API + '/api/sailor/resolve?sas_id=' + encodeURIComponent(resolveSid)).catch(function() { return null; });
                                        if (resolveRes && resolveRes.ok) {
                                            var resolveData = await resolveRes.json();
                                            if (resolveData && resolveData.bio) resolveBioText = String(resolveData.bio).trim();
                                        }
                                    }
                                } catch (_) {}
                                // Prefer full sailor_bio (resolve) over short media ai_overview — Tim was "light" because ai_overview won
                                var sailorBioText = resolveBioText
                                    || ssrSailorBioText
                                    || (aiOverviewSummary && String(aiOverviewSummary).trim())
                                    || '';
                                // Visible Note about sailor (between header and tabs) — must not flash then disappear
                                sailorBioHtml = '';
                                if (sailorBioText) {
                                    sailorBioHtml = '<div class="sailor-bio"><p>' + escapeHtml(sailorBioText) + '</p></div>';
                                }
                                // Skip short media ai_overview in profile tab when full sailor bio is already shown above tabs
                                if (!sailorBioHtml && aiOverviewSummary && aiOverviewSummary.trim()) {
                                    var formattedSummary = escapeHtml(aiOverviewSummary.trim())
                                        .replace(/\n/g, '<br>')
                                        .replace(/•/g, '•');
                                    
                                    aiOverviewHtml = '<section class="sailor-ai-overview">' +
                                        '<h2 class="ai-overview-title">Career Summary</h2>' +
                                        '<div class="ai-overview-text">' + formattedSummary + '</div>' +
                                        '</section>';
                                } else {
                                }
                                
                                // Sailor avatar: ONLY local assets/avatars, cached media/avatars, or default – never media tab thumbnails
                                var avatarPath = '';
                                var hasAvatar = false;
                                var apiBase = (window.API_BASE || '').replace(/\/$/, '');
                                var sidSafe = escapeHtml(String(sid));
                                var avatarOverrides = {
                                    '21172': {
                                        path: 'assets/personal-avatars/21172-timothy-weaving.png?v=20260805a',
                                        objectPosition: '36% 22%',
                                        scale: '1.42'
                                    },
                                    '27159': {
                                        path: 'assets/personal-avatars/27159-birgitta-weaving.png?v=20260805a',
                                        objectPosition: '41% 18%',
                                        scale: '1.34'
                                    }
                                };
                                var avatarOverride = null;
                                var avatarOverrideKeys = [
                                    String(sid || '').trim(),
                                    String((memberSource && memberSource.sas_id) || '').trim(),
                                    String((m && m.sas_id) || '').trim(),
                                    String((memberSource && ([memberSource.first_name || memberSource.first_names, memberSource.last_name || memberSource.surname].filter(Boolean).join(' '))) || '').trim().toLowerCase(),
                                    String(nameD || '').trim().toLowerCase(),
                                    String((nameFromMember || '')).trim().toLowerCase()
                                ].filter(Boolean);
                                for (var avatarKeyIdx = 0; avatarKeyIdx < avatarOverrideKeys.length; avatarKeyIdx++) {
                                    var avatarKey = avatarOverrideKeys[avatarKeyIdx];
                                    if (avatarOverrides[avatarKey]) {
                                        avatarOverride = avatarOverrides[avatarKey];
                                        break;
                                    }
                                    if (avatarKey === 'timothy weaving' || avatarKey === 'name:timothy-weaving' || avatarKey === 'timothy-weaving') {
                                        avatarOverride = avatarOverrides['21172'];
                                        break;
                                    }
                                    if (avatarKey === 'birgitta weaving' || avatarKey === 'name:birgitta-weaving' || avatarKey === 'birgitta-weaving') {
                                        avatarOverride = avatarOverrides['27159'];
                                        break;
                                    }
                                }
                                var localAvatarPng = 'assets/avatars/' + sidSafe + '.png';
                                var localAvatarJpg = 'assets/avatars/' + sidSafe + '.jpg';
                                var cachedAvatarPath = 'media/avatars/' + sidSafe + '.jpg';
                                var fullAvatarPath = (apiBase ? apiBase + '/' : '') + cachedAvatarPath;
                                var avatarObjectPosition = (avatarOverride && avatarOverride.objectPosition) ? String(avatarOverride.objectPosition) : 'center center';
                                var avatarScale = (avatarOverride && avatarOverride.scale) ? String(avatarOverride.scale) : '1';
                                var avatarStyleAttr = (avatarObjectPosition !== 'center center' || avatarScale !== '1')
                                    ? ' style="object-position:' + escapeHtml(avatarObjectPosition) + ';transform:scale(' + escapeHtml(avatarScale) + ');transform-origin:' + escapeHtml(avatarObjectPosition) + ';"'
                                    : '';
                                if (avatarOverride && avatarOverride.path) {
                                    avatarPath = String(avatarOverride.path);
                                    hasAvatar = true;
                                }
                                if (!hasAvatar) {
                                    var ageNum = (ageVal !== '' && ageVal !== undefined && ageVal !== null && !isNaN(ageVal)) ? parseInt(ageVal, 10) : null;
                                    if (ageNum >= 9 && ageNum <= 18) {
                                        avatarPath = 'assets/avatars/default-youth.png';
                                    } else {
                                        avatarPath = localAvatarPng;
                                    }
                                    hasAvatar = true;
                                }
                                if (!hasAvatar) {
                                    avatarPath = localAvatarJpg;
                                    hasAvatar = true;
                                }
                                if (!hasAvatar) {
                                    avatarPath = fullAvatarPath;
                                    hasAvatar = true;
                                }
                                // Final hard override: specific profile photos must win for both public and logged-in views.
                                var forcedAvatarOverride = null;
                                if (String(sid || '').trim() === '21172' || String((memberSource && memberSource.sas_id) || '').trim() === '21172' || String(nameD || '').trim().toLowerCase() === 'timothy weaving' || String(nameFromMember || '').trim().toLowerCase() === 'timothy weaving') {
                                    forcedAvatarOverride = avatarOverrides['21172'];
                                } else if (String(sid || '').trim() === '27159' || String((memberSource && memberSource.sas_id) || '').trim() === '27159' || String(nameD || '').trim().toLowerCase() === 'birgitta weaving' || String(nameFromMember || '').trim().toLowerCase() === 'birgitta weaving') {
                                    forcedAvatarOverride = avatarOverrides['27159'];
                                }
                                if (forcedAvatarOverride && forcedAvatarOverride.path) {
                                    avatarPath = String(forcedAvatarOverride.path);
                                    avatarObjectPosition = forcedAvatarOverride.objectPosition ? String(forcedAvatarOverride.objectPosition) : 'center center';
                                    avatarScale = forcedAvatarOverride.scale ? String(forcedAvatarOverride.scale) : '1';
                                    avatarStyleAttr = (avatarObjectPosition !== 'center center' || avatarScale !== '1')
                                        ? ' style="object-position:' + escapeHtml(avatarObjectPosition) + ';transform:scale(' + escapeHtml(avatarScale) + ');transform-origin:' + escapeHtml(avatarObjectPosition) + ';"'
                                        : '';
                                }
                                // img src: 9-18 yrs = default-youth.png; else custom {sid}.png/jpg or initials
                                
                                // Build header: Province = SA codes only; Club = club logo OR (intl) one country flag + UK
                                var provinceCodeDisplay = (provinceCode && provinceCode !== '—') ? String(provinceCode).toUpperCase() : '';
                                var provinceWebMap = { 'WC': 'https://wcsailingchamps.co.za/' };
                                var provinceWeb = (!isIntlSailor && provinceCodeDisplay) ? (provinceWebMap[provinceCodeDisplay] || '') : '';
                                var countryFlagCode = (isIntlSailor && sslCountryCode)
                                    ? (/^GB$/i.test(sslCountryCode) ? 'GBR' : sslCountryCode)
                                    : '';
                                var intlFlagUrl = countryFlagCode
                                    ? ((apiBase ? apiBase + '/' : '/') + 'artwork/International Flags/' + encodeURIComponent(countryFlagCode) + '.png')
                                    : '';
                                // Intl: same dark-blue province box, blank (no flag / no code). Flag only in club box.
                                var provinceInner = isIntlSailor
                                    ? '<div class="sailor-province-icon-box" title=""></div>'
                                    : ('<div class="sailor-province-icon-box' + (provinceCodeDisplay ? '' : ' province-empty') + '" title="' + escapeHtml(provinceDisplay) + '">' +
                                        (provinceCodeDisplay ? escapeHtml(provinceCodeDisplay) : '—') +
                                        '</div>');
                                var provinceIconBox = (!isIntlSailor && provinceWeb) ? '<a class="sailor-province-icon-link" href="' + escapeHtml(provinceWeb) + '" target="_blank" rel="noopener noreferrer" title="Visit ' + escapeHtml(provinceDisplay || provinceCodeDisplay) + ' sailing">' + provinceInner + '</a>' : provinceInner;
                                var finalClubCode = (!isIntlSailor && clubD && clubD !== '—') ? String(clubD).trim().toUpperCase() : '';
                                var clubLogoUrl = (apiBase && finalClubCode) ? (apiBase + '/api/club-logo/' + encodeURIComponent(finalClubCode)) : '';
                                var clubWebsiteMap = { 'HYC': 'https://www.hyc.co.za/', 'ZVYC': 'https://zvyc.co.za/', 'TSC': 'https://www.theewater.co.za/' };
                                var clubWeb = finalClubCode ? (clubWebsiteMap[finalClubCode] || '') : '';
                                var clubSlug = (finalClubCode && codeToSlug) ? (codeToSlug[finalClubCode] || '') : '';
                                var finalClubHref = clubSlug ? ('/club/' + encodeURIComponent(clubSlug)) : (clubWeb || '');
                                var finalClubTitle = finalClubCode || 'Club';
                                var clubFlagInner;
                                if (isIntlSailor && intlFlagUrl) {
                                    // Same club-box size as SA logos; small country flag only (no UK text beside it)
                                    clubFlagInner = '<img src="' + escapeHtml(intlFlagUrl) + '" alt="' + escapeHtml(clubD || countryFlagCode) + '" loading="lazy">';
                                } else if (finalClubCode) {
                                    if (clubLogoUrl) {
                                        clubFlagInner = '<img src="' + escapeHtml(clubLogoUrl) + '" alt="' + escapeHtml(finalClubCode) + '" loading="lazy" onerror="this.style.display=\'none\'; var n=this.nextElementSibling; if(n) n.style.display=\'inline\';">' +
                                            '<span class="club-code-fallback" style="display:none">' + escapeHtml(finalClubCode) + '</span>';
                                    } else {
                                        clubFlagInner = '<span style="font-size:0.7rem;font-weight:700;color:#001f3f;">' + escapeHtml(finalClubCode) + '</span>';
                                    }
                                } else {
                                    clubFlagInner = '<span style="font-size:0.5rem;color:#64748b">—</span>';
                                }
                                var clubLink = finalClubHref;
                                var clubFlagBox = '<div class="sailor-club-flag-box">' + (clubLink ? '<a href="' + escapeHtml(clubLink) + (clubWeb && !clubSlug ? '" target="_blank" rel="noopener noreferrer" title="Visit club website"' : '" title="View club page"') + '>' + clubFlagInner + '</a>' : clubFlagInner) + '</div>';
                                // Sailing For: first result date → today as "X yrs Y mths"
                                var sailingForHtml = '';
                                if (regattaHistoryRows && regattaHistoryRows.length > 0) {
                                    var sailingForDates = regattaHistoryRows.map(function(r) { return r.dateStr; }).filter(function(d) {
                                        if (!d || d === 'N/A') return false;
                                        var t = new Date(d).getTime();
                                        return !isNaN(t);
                                    });
                                    if (sailingForDates.length > 0) {
                                        var oldestMs = Math.min.apply(null, sailingForDates.map(function(d) { return new Date(d).getTime(); }));
                                        var oldest = new Date(oldestMs);
                                        var nowSf = new Date();
                                        var yrs = nowSf.getFullYear() - oldest.getFullYear();
                                        var mths = nowSf.getMonth() - oldest.getMonth();
                                        if (nowSf.getDate() < oldest.getDate()) mths -= 1;
                                        if (mths < 0) { yrs -= 1; mths += 12; }
                                        if (yrs < 0) { yrs = 0; mths = 0; }
                                        var sailingForLabel = yrs + ' yrs ' + mths + ' mths';
                                        var sailingForIconUrl = (apiBase ? apiBase + '/' : '/') + 'artwork/Sailing-For.png?v=4';
                                        var sslBlockInline = '';
                                        try {
                                            var _sslPre = (window.__sslSailorProfiles && sid != null) ? window.__sslSailorProfiles[String(sid)] : null;
                                            if (_sslPre && _sslPre.ssl_profile_slug) {
                                                var _sslHref = _sslPre.ssl_profile_url || ('https://worldofsailors.com/sailor/' + encodeURIComponent(_sslPre.ssl_profile_slug));
                                                var _sslLogoUrl = (apiBase ? apiBase + '/' : '/') + 'artwork/SSL-logo.png?v=5';
                                                var _sslLogo = '<a class="sailor-ssl-logo-link" href="' + escapeHtml(_sslHref) + '" target="_blank" rel="noopener noreferrer" title="Star Sailors League / WorldOfSailors profile">' +
                                                    '<img class="sailor-ssl-logo" src="' + escapeHtml(_sslLogoUrl) + '" alt="SSL" loading="lazy" height="28">' +
                                                    '</a>';

                                                var _rankPart = '';
                                                if (_sslPre.ssl_rank != null && _sslPre.ssl_rank !== '') {
                                                    _rankPart = '<div class="sailor-ssl-stat"><span class="sailor-ssl-stat-label">Rank</span>' +
                                                        '<span class="sailor-ssl-rank-value">' + escapeHtml(String(_sslPre.ssl_rank)) + '</span></div>';
                                                }
                                                var _pointsPart = '';
                                                if (_sslPre.ssl_points != null && _sslPre.ssl_points !== '') {
                                                    // Integer digits only — never "14.0" → "140"
                                                    var _ptsNum = Math.round(Number(_sslPre.ssl_points));
                                                    if (!isFinite(_ptsNum) || _ptsNum < 0) _ptsNum = 0;
                                                    var _ptsStr = String(_ptsNum);
                                                    var _digitHtml = _ptsStr.split('').map(function(d) {
                                                        return '<span class="sailor-ssl-points-digit">' + escapeHtml(d) + '</span>';
                                                    }).join('');
                                                    _pointsPart = '<div class="sailor-ssl-stat"><span class="sailor-ssl-stat-label">SSL Points</span>' +
                                                        '<div class="sailor-ssl-points-boxes" aria-label="SSL Points ' + escapeHtml(_ptsStr) + '">' + _digitHtml + '</div></div>';
                                                }
                                                var _stats = (_rankPart || _pointsPart) ? ('<div class="sailor-ssl-stats">' + _rankPart + _pointsPart + '</div>') : '';
                                                sslBlockInline = '<div class="sailor-ssl-block">' + _sslLogo + _stats + '</div>';
                                            }
                                        } catch (_eSsl) {}
                                        sailingForHtml = '<div class="sailor-sailing-for" title="Sailing for ' + escapeHtml(sailingForLabel) + ' since first recorded result">' +
                                            '<img class="sailor-sailing-for-icon" src="' + escapeHtml(sailingForIconUrl) + '" alt="Sailing For" loading="lazy" width="48" height="48">' +
                                            '<span class="sailor-sailing-for-duration">' + escapeHtml(sailingForLabel) + '</span>' +
                                            sslBlockInline +
                                            '</div>';
                                    }
                                }
                                if (!window.__trackFunnelEvent) {
                                    window.__trackFunnelEvent = function(stepKey, stableEntityId, okFlag, errCode, metaValue) {
                                        try {
                                            var body = {
                                                funnel_name: 'claim_profile',
                                                step_key: String(stepKey || ''),
                                                stable_entity_id: stableEntityId != null ? String(stableEntityId) : '',
                                                url_path: (window.location && window.location.pathname) ? String(window.location.pathname) : '',
                                                ok: okFlag !== false,
                                                error_code: errCode != null ? String(errCode) : '',
                                                meta: (metaValue && typeof metaValue === 'object') ? metaValue : {}
                                            };
                                            fetch(API + '/api/funnel-event', {
                                                method: 'POST',
                                                credentials: 'include',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify(body)
                                            }).catch(function() {});
                                        } catch (e) {}
                                    };
                                }
                                var claimIsClaimed = false;
                                try {
                                    var claimStatusRes = await fetch(API + '/api/sailor/claim-status?sas_id=' + encodeURIComponent(String(sid))).catch(function() { return null; });
                                    if (claimStatusRes && claimStatusRes.ok) {
                                        var claimStatusData = await claimStatusRes.json();
                                        claimIsClaimed = !!(claimStatusData && claimStatusData.claimed);
                                    }
                                } catch (_eClaim) {}
                                var claimTickHtml = claimIsClaimed ? '<span class="sailor-claimed-tick" aria-label="Claimed">✓</span>' : '';
                                var claimCtaHtml = '';
                                if (!claimIsClaimed && sid != null && String(sid).trim()) {
                                    var claimReturnTo = (window.location && window.location.pathname) ? String(window.location.pathname) : '/';
                                    var claimHref = '/signup.html?sas_id=' + encodeURIComponent(String(sid)) + '&returnTo=' + encodeURIComponent(claimReturnTo);
                                    if (window.__trackFunnelEvent) window.__trackFunnelEvent('claim_cta_impression', String(sid), true, '', { returnTo: claimReturnTo });
                                    claimCtaHtml = '<a class="sailor-claim-cta" id="sailorClaimCta" data-sas-id="' + escapeHtml(String(sid)) + '" href="' + escapeHtml(claimHref) + '" onclick="try{window.__trackFunnelEvent&&window.__trackFunnelEvent(\'claim_cta_click\',this.getAttribute(\'data-sas-id\')||\'\',true,\'\',{returnTo:(window.location&&window.location.pathname)?String(window.location.pathname):\'/\'});}catch(e){}">Is this you? Claim this profile</a>';
                                }
                                header = '<section class="sailor-profile-header">' +
                                    '<header class="sailor-identity has-avatar">' +
                                    '<div class="sailor-avatar">' +
                                    '<img src="' + escapeHtml(avatarPath) + '" alt="' + escapeHtml(nameD || 'Sailor') + '" loading="lazy"' + avatarStyleAttr + ' onerror="this.style.display=\'none\'; var fallback = this.parentElement.querySelector(\'.avatar-fallback\'); if (fallback) fallback.style.display=\'flex\';">' +
                                    '<span class="avatar-fallback" style="display:none;">' + escapeHtml(initials) + '</span>' +
                                    '</div>' +
                                    '<div class="sailor-identity-text">' +
                                    '<h1 class="sailor-name">' +
                                    '<div class="sailor-name-first">' + escapeHtml(firstName || nameD || 'Sailor') + '</div>' +
                                    (lastName ? '<div class="sailor-name-last">' + escapeHtml(lastName) + '</div>' : '') +
                                    claimTickHtml +
                                    '</h1>' +
                                    claimCtaHtml +
                                    '</div>' +
                                    provinceIconBox +
                                    clubFlagBox +
                                    sailingForHtml +
                                    '</header>' +
                                    '</section>';
                                
                                // Extract Google Profile summary for "What it says about you" card (Step 8)
                                var googleProfileItem = mentionItems.find(function(item) {
                                    return item.is_pinned === true || (item.headline && item.headline.indexOf('What Google says about') === 0);
                                });
                                if (googleProfileItem && googleProfileItem.snippet && googleProfileItem.snippet.trim()) {
                                    var summaryText = googleProfileItem.snippet.trim();
                                    // Limit to max 2 lines (approx 120 chars for mobile)
                                    if (summaryText.length > 120) {
                                        var truncated = summaryText.substring(0, 120);
                                        var lastSpace = truncated.lastIndexOf(' ');
                                        if (lastSpace > 80) {
                                            summaryText = truncated.substring(0, lastSpace) + '...';
                                        } else {
                                            summaryText = truncated + '...';
                                        }
                                    }
                                    summaryCardHtml = '<section class="sailor-summary-card">' +
                                        '<header class="summary-header">' +
                                        '<h2 class="summary-title">What it says about ' + escapeHtml(nameD || 'this sailor') + '</h2>' +
                                        '</header>' +
                                        '<div class="summary-body">' +
                                        '<p class="summary-text">' + escapeHtml(summaryText) + '</p>' +
                                        '</div>' +
                                        '<footer class="summary-footer">' +
                                        '<a href="#" class="summary-link" onclick="event.preventDefault(); var mediaTab = document.querySelector(\'.sailor-profile-tab[data-tab=\\\'media\\\']\'); if (mediaTab) { mediaTab.click(); setTimeout(function() { document.getElementById(\'sailor-tab-panel-media\').scrollIntoView({ behavior: \'smooth\', block: \'start\' }); }, 100); } return false;">View sources</a>' +
                                        '</footer>' +
                                        '</section>';
                                }
                                
                                // Fetch highlights from API (includes AI Overview descriptions)
                                var highlightsData = [];
                                try {
                                    var highlightsRes = await fetch(API + '/api/member/' + encodeURIComponent(sid) + '/highlights').catch(function() { return null; });
                                    if (highlightsRes && highlightsRes.ok) {
                                        var highlightsApiData = await highlightsRes.json();
                                        if (highlightsApiData.highlights && Array.isArray(highlightsApiData.highlights)) {
                                            highlightsData = highlightsApiData.highlights
                                                .filter(function(h) {
                                                    // Only include podium finishes (rank 1-3)
                                                    var rank = h.rank || 0;
                                                    return rank > 0 && rank <= 3;
                                                })
                                                .map(function(h) {
                                                    return {
                                                        text: h.text || h,
                                                        rank: h.rank || 0,
                                                        description: h.description || null,
                                                        dateStr: h.dateStr || null,
                                                        regatta_id: h.regatta_id || null,
                                                        className: h.className || h.class || '',
                                                        regattaName: h.regattaName || h.event_name || null
                                                    };
                                                });
                                        }
                                    }
                                } catch (err) {
                                    console.warn("Could not fetch highlights from API:", err);
                                }
                                
                                // Always extract ALL podium finishes (rank 1-3) from regattaHistoryRows
                                var fallbackHighlights = [];
                                if (regattaHistoryRows && regattaHistoryRows.length > 0) {
                                    var podiumEvents = regattaHistoryRows.filter(function(r) {
                                        return r.rank && r.rank > 0 && r.rank <= 3;
                                    });
                                    for (var i = 0; i < podiumEvents.length; i++) {
                                        var r = podiumEvents[i];
                                        var rank = r.rank;
                                        var eventName = r.highlight_event_name || r.event_name || 'Regatta';
                                        var className = r.className || '';
                                        var dateStr = r.dateStr || '';
                                        var year = dateStr ? dateStr.substring(0, 4) : '';
                                        var positionText = (['1st', '2nd', '3rd'][rank - 1] + ' place');
                                        var highlightText = positionText + ' – ' + eventName;
                                        if (className && className !== '—') {
                                            highlightText += ' (' + className;
                                            if (year) highlightText += ', ' + year;
                                            highlightText += ')';
                                        } else if (year) {
                                            highlightText += ' (' + year + ')';
                                        }
                                        fallbackHighlights.push({ text: highlightText, rank: rank, description: null, dateStr: dateStr, regatta_id: r.regatta_id, block_id: r.block_id, result_href: r.result_href, className: className, regattaName: eventName });
                                    }
                                }
                                
                                // Merge API highlights with fallback highlights
                                // Prioritize fallback highlights (from regattaHistoryRows) as source of truth
                                // Use a map to track unique highlights by text + date (to avoid false duplicates)
                                var highlightsMap = {};
                                
                                // Add fallback highlights first (complete source of truth from regattaHistoryRows)
                                // These contain ALL podiums from regattaHistoryRows
                                fallbackHighlights.forEach(function(h) {
                                    // Use text + dateStr as key to avoid false duplicates (same event, different dates)
                                    var key = (h.text || '') + '|' + (h.dateStr || '');
                                    if (h.text) {
                                        highlightsMap[key] = h;
                                    }
                                });
                                
                                // Add API highlights only if they don't already exist (to preserve descriptions if available)
                                highlightsData.forEach(function(h) {
                                    var key = (h.text || '') + '|' + (h.dateStr || '');
                                    if (h.text && !highlightsMap[key]) {
                                        // Only add if not already in fallback highlights
                                        highlightsMap[key] = h;
                                    } else if (h.text && highlightsMap[key] && h.description && !highlightsMap[key].description) {
                                        // If duplicate exists but API has description and fallback doesn't, add description
                                        highlightsMap[key].description = h.description;
                                    }
                                });
                                
                                // Convert map back to array - this ensures ALL podiums from regattaHistoryRows are included
                                highlightsData = Object.values(highlightsMap);
                                
                                // Sort all highlights by date descending (most recent first)
                                // Extract date from text if dateStr not available
                                highlightsData.sort(function(a, b) {
                                    var dateA = a.dateStr || '';
                                    var dateB = b.dateStr || '';
                                    // If no dateStr, try to extract year from text
                                    if (!dateA && a.text) {
                                        var yearMatch = a.text.match(/(\d{4})/);
                                        if (yearMatch) dateA = yearMatch[1] + '-12-31'; // Use year-end as fallback
                                    }
                                    if (!dateB && b.text) {
                                        var yearMatch = b.text.match(/(\d{4})/);
                                        if (yearMatch) dateB = yearMatch[1] + '-12-31'; // Use year-end as fallback
                                    }
                                    return dateB.localeCompare(dateA);
                                });
                                
                                // Step 14: Render highlights with emoji prefixes (1st=gold, 2nd=silver, 3rd=bronze)
                                if (highlightsData && highlightsData.length > 0) {
                                    var highlightsListHtml = highlightsData.map(function(h) {
                                        var emoji = '';
                                        var rank = h.rank || 0;
                                        if (rank === 1) {
                                            emoji = '🥇 ';
                                        } else if (rank === 2) {
                                            emoji = '🥈 ';
                                        } else if (rank === 3) {
                                            emoji = '🥉 ';
                                        } else if (rank >= 4 && rank <= 10) {
                                            emoji = '🥉 ';
                                        }
                                        
                                        // Format: Medal + Text + Description (if available)
                                        var highlightHtml = emoji + escapeHtml(h.text);
                                        if (h.description && h.description.trim()) {
                                            highlightHtml += ': "' + escapeHtml(h.description.trim()) + '"';
                                        }
                                        
                                        var regattaHref = typeof highlightRegattaHref === 'function' ? highlightRegattaHref(h) : '';
                                        if (regattaHref) {
                                            return '<li><a href="' + escapeHtml(regattaHref) + '" class="highlight-regatta-link" title="View regatta results">' + highlightHtml + '</a></li>';
                                        }
                                        return '<li>' + highlightHtml + '</li>';
                                    }).join('');
                                    
                                    highlightsHtml = '<section class="sailor-highlights">' +
                                        '<h2 class="highlights-title">Highlights</h2>' +
                                        '<ul class="highlights-list">' +
                                        highlightsListHtml +
                                        '</ul>' +
                                        '</section>';
                                } else if (regattaHistoryRows && regattaHistoryRows.length > 0) {
                                    // No podiums: show best 5 most recent results (no medals), in date order
                                    var bestResults = regattaHistoryRows
                                        .filter(function(r) { return r.rank && r.rank > 3 && r.rank <= 100; })
                                        .slice()
                                        .sort(function(a, b) { return (b.dateStr || '').localeCompare(a.dateStr || ''); })
                                        .slice(0, 5);
                                    if (bestResults.length > 0) {
                                        var formatRank = function(n) {
                                            if (!n || isNaN(n)) return '';
                                            var num = parseInt(n, 10);
                                            var dd = num % 100;
                                            if (dd >= 10 && dd <= 20) return num + 'th';
                                            var d = num % 10;
                                            return num + ({ 1: 'st', 2: 'nd', 3: 'rd' }[d] || 'th');
                                        };
                                        var bestListHtml = bestResults.map(function(r) {
                                            var rank = r.rank;
                                            var eventName = r.event_name || 'Regatta';
                                            var className = r.className || '';
                                            var dateStr = r.dateStr || '';
                                            var year = dateStr ? dateStr.substring(0, 4) : '';
                                            var positionText = formatRank(rank) + ' place';
                                            var text = positionText + ' – ' + eventName;
                                            if (className && className !== '—') {
                                                text += ' (' + className + (year ? ', ' + year : '') + ')';
                                            } else if (year) text += ' (' + year + ')';
                                            var regattaHref = typeof highlightRegattaHref === 'function' ? highlightRegattaHref(r) : '';
                                            if (regattaHref) {
                                                return '<li><a href="' + escapeHtml(regattaHref) + '" class="highlight-regatta-link" title="View regatta results">' + escapeHtml(text) + '</a></li>';
                                            }
                                            return '<li>' + escapeHtml(text) + '</li>';
                                        }).join('');
                                        highlightsHtml = '<section class="sailor-highlights">' +
                                            '<h2 class="highlights-title">Best results</h2>' +
                                            '<ul class="highlights-list">' +
                                            bestListHtml +
                                            '</ul>' +
                                            '</section>';
                                    }
                                }
                                
                                // Calculate compact stats (Step 13) — unique regattas/races only (not sub-fleet rows)
                                var totalRegattas = regattaCount;
                                var totalRaces = raceCount;
                                var sailingSinceYear = null;
                                // Find earliest year
                                if (regattaHistoryRows.length > 0) {
                                    var dates = regattaHistoryRows.map(function(r) { return r.dateStr; }).filter(function(d) { return d && /^\d{4}/.test(d); });
                                    if (dates.length > 0) {
                                        dates.sort();
                                        var earliestDate = dates[0];
                                        if (earliestDate) sailingSinceYear = earliestDate.substring(0, 4);
                                    }
                                }
                                
                                var compactStatsHtml = '';
                                if (totalRegattas > 0 || totalRaces > 0 || sailingSinceYear) {
                                    var statsParts = [];
                                    if (totalRegattas > 0) statsParts.push('<span>' + totalRegattas + ' regatta' + (totalRegattas !== 1 ? 's' : '') + '</span>');
                                    if (totalRaces > 0) statsParts.push('<span>' + totalRaces + ' race' + (totalRaces !== 1 ? 's' : '') + '</span>');
                                    if (sailingSinceYear) statsParts.push('<span>Sailing since ' + escapeHtml(sailingSinceYear) + '</span>');
                                    if (statsParts.length > 0) {
                                        compactStatsHtml = '<div class="sailor-compact-stats">' + statsParts.join('<span>•</span>') + '</div>';
                                    }
                                }
                                
                                // Step 14: Medal tally must match highlights (dedupe same SAS event + rank, keep U19/U17 separate)
                                var goldCount = 0, silverCount = 0, bronzeCount = 0;
                                if (highlightsData && highlightsData.length > 0) {
                                    var medalSeen = {};
                                    highlightsData.forEach(function(h) {
                                        var rank = h.rank || 0;
                                        if (rank < 1 || rank > 3) return;
                                        var eventPart = (h.block_id && isMemberYouthSubFleetBlock(h.block_id))
                                            ? (String(h.regatta_id || '') + ':' + memberResultBlockTail(h.block_id))
                                            : memberResultCareerEventKey({ regatta_id: h.regatta_id });
                                        var medalKey = eventPart + ':' + rank + ':' + (h.className || '');
                                        if (medalSeen[medalKey]) return;
                                        medalSeen[medalKey] = true;
                                        if (rank === 1) goldCount++;
                                        else if (rank === 2) silverCount++;
                                        else if (rank === 3) bronzeCount++;
                                    });
                                }
                                var medalSummaryHtml = '';
                                if (goldCount > 0 || silverCount > 0 || bronzeCount > 0) {
                                    medalSummaryHtml = '<div class="sailor-medal-summary">' +
                                        '<span>🥇 ' + goldCount + '</span>' +
                                        '<span>🥈 ' + silverCount + '</span>' +
                                        '<span>🥉 ' + bronzeCount + '</span>' +
                                        '<span class="medal-scope">Podium finishes</span>' +
                                        '</div>';
                                }
                                
                                if (mentionItems.length > 0) {
                                    var sailorNameForMedia = (nameD || 'Sailor').trim();
                                    // Name variants for bolding in snippet (e.g. Tim/Timothy, Josh/Joshua)
                                    var firstLongToShort = { timothy: 'tim', joshua: 'josh', thomas: 'tom', christopher: 'chris', benjamin: 'ben', matthew: 'matt', michael: 'mike', daniel: 'dan', samuel: 'sam', jonathan: 'jon', nicholas: 'nick', andrew: 'andy', joseph: 'joe', nathan: 'nate' };
                                    var nameVariantsForBold = [sailorNameForMedia];
                                    if (sailorNameForMedia) {
                                        var parts = sailorNameForMedia.split(/\s+/);
                                        if (parts.length >= 2) {
                                            var first = parts[0].toLowerCase();
                                            var rest = parts.slice(1).join(' ');
                                            if (firstLongToShort[first]) {
                                                nameVariantsForBold.push(firstLongToShort[first].charAt(0).toUpperCase() + firstLongToShort[first].slice(1) + ' ' + rest);
                                            }
                                            var shortToLong = {};
                                            for (var k in firstLongToShort) { shortToLong[firstLongToShort[k]] = k; }
                                            if (shortToLong[first]) {
                                                var longFirst = shortToLong[first].charAt(0).toUpperCase() + shortToLong[first].slice(1);
                                                nameVariantsForBold.push(longFirst + ' ' + rest);
                                            }
                                        }
                                    }
                                    var isRedundantHeadline = function(h) {
                                        if (!h) return true;
                                        var lower = h.toLowerCase();
                                        var nameLower = sailorNameForMedia.toLowerCase();
                                        if (lower === nameLower) return true;
                                        if (lower === nameLower + ' (sailor)') return true;
                                        if (lower === nameLower + ' (sailor)' || lower.indexOf(nameLower + ' |') === 0) return true;
                                        if (h.length <= nameLower.length + 15 && lower.indexOf(nameLower) === 0) return true;
                                        return false;
                                    };
                                    // Sort: pinned items first, then by date DESC
                                    var sortedItems = mentionItems.slice().sort(function(a, b) {
                                        if (a.is_pinned && !b.is_pinned) return -1;
                                        if (!a.is_pinned && b.is_pinned) return 1;
                                        var dateA = (a.date_iso || '').trim();
                                        var dateB = (b.date_iso || '').trim();
                                        if (dateA && dateB) return dateB.localeCompare(dateA);
                                        if (dateA) return -1;
                                        if (dateB) return 1;
                                        return 0;
                                    });
                                    var mentionCards = sortedItems.map(function(item) {
                                        var rawUrl = (item.url || '').trim();
                                        var url = rawUrl && rawUrl.indexOf('http') === 0 ? rawUrl.replace(/"/g, '&quot;') : '#';
                                        var rawHeadline = (item.headline || '').trim() || 'Untitled';
                                        var displayHeadline = isRedundantHeadline(rawHeadline) ? ((item.source || '').trim() || 'Article') : rawHeadline;
                                        var headlineEsc = escapeHtml(displayHeadline);
                                        var snippetEsc = escapeHtml((item.snippet || '').trim());
                                        if (snippetEsc && nameVariantsForBold.length) {
                                            nameVariantsForBold.sort(function(a, b) { return (b.length - a.length); });
                                            for (var vi = 0; vi < nameVariantsForBold.length; vi++) {
                                                var v = nameVariantsForBold[vi];
                                                if (!v) continue;
                                                var re = new RegExp('(' + v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
                                                snippetEsc = snippetEsc.replace(re, '<strong>$1</strong>');
                                            }
                                        }
                                        var sourceEsc = escapeHtml((item.source || '').trim() || '');
                                        var timeAgo = (item.time_ago || item.time_ago_text || '').trim();
                                        var dateTimeDisplay = (item.date_time_display || '').trim();
                                        var dateIso = (item.date_iso || '').trim();
                                        var type = (item.type || 'article').toLowerCase();
                                        var icon = type === 'video' ? '\u25B6\uFE0F' : (type === 'photo' ? '\uD83D\uDCF7' : '\uD83D\uDCC4');
                                        var thumbOriginal = (item.thumb_url && String(item.thumb_url).trim()) || '';
                                        var apiBase = (window.API_BASE || window.location.origin || '').replace(/\/$/, '');
                                        var thumb = (thumbOriginal && thumbOriginal.indexOf('http') === 0) ? thumbOriginal : '';
                                        if (thumb) { thumb = apiBase + '/api/thumbnail?url=' + encodeURIComponent(thumb); }
                                        var placeholderThumb = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90" viewBox="0 0 160 90"><rect fill="#e5e7eb" width="160" height="90"/><text x="80" y="52" fill="#9ca3af" font-family="sans-serif" font-size="14" text-anchor="middle">Media</text></svg>');
                                        var thumbSrc = thumb || placeholderThumb;
                                        var metaParts = [];
                                        if (dateTimeDisplay) metaParts.push(escapeHtml(dateTimeDisplay));
                                        else if (dateIso) metaParts.push(escapeHtml(dateIso));
                                        if (timeAgo) metaParts.push(escapeHtml(timeAgo));
                                        metaParts.push(sourceEsc);
                                        if (type !== 'article') metaParts.push(escapeHtml(type.charAt(0).toUpperCase() + type.slice(1)));
                                        var metaText = metaParts.join(' \u2022 ');
                                        var linkLabel = (item.is_pinned ? 'Google Profile \u2013 ' : '') + (displayHeadline || 'Link');
                                        var cardClass = (item.is_pinned ? ' media-google' : '');
                                        var snippetForAttr = ((item.snippet || '').trim()).replace(/"/g, '&quot;').substring(0, 500);
                                        var thumbForAttr = (thumbOriginal || '').replace(/"/g, '&quot;').substring(0, 1000);
                                        var editBtnHtml = isLoggedInUser ? '<button type="button" class="media-edit-btn" data-id="' + escapeHtml(String(item.id || '')) + '" data-url="' + escapeHtml(rawUrl) + '" data-source-added="' + escapeHtml(String(item.source_added || 'system')) + '" data-headline="' + escapeHtml(displayHeadline) + '" data-snippet="' + escapeHtml(snippetForAttr) + '" data-thumb-url="' + escapeHtml(thumbForAttr) + '" data-date-iso="' + escapeHtml(dateIso) + '">Edit</button>' : '';
                                        var thumbHtml = '<div class="media-thumb-wrap"><div class="media-thumb"><img src="' + escapeHtml(thumbSrc) + '" alt="" loading="lazy" onerror="this.onerror=null;this.src=\'' + placeholderThumb + '\';" /><span class="media-icon" style="display:none">' + icon + '</span></div>' + editBtnHtml + '</div>';
                                        var snippetHtml = snippetEsc ? '<p class="media-snippet">' + snippetEsc + '</p>' : '';
                                        var metaHtml = metaText ? '<div class="media-meta">' + metaText + '</div>' : '';
                                        var urlAuditHtml = rawUrl ? '<div class="media-url-audit">' + escapeHtml(rawUrl) + '</div>' : '';
                                        return '<div class="media-card-wrap' + cardClass + '">' + thumbHtml + '<a class="media-card-link" href="' + url + '" target="_blank" rel="noopener noreferrer" aria-label="' + escapeHtml(linkLabel) + '"><div class="media-body"><div class="media-title">' + headlineEsc + '</div>' + snippetHtml + metaHtml + urlAuditHtml + '</div></a></div>';
                                    }).join('');
                                    var addMediaBtn = isLoggedInUser ? '<button type="button" class="add-media-btn" id="add-media-btn" data-sa-id="' + escapeHtml(String(sid)) + '" data-name="' + escapeHtml(String(name || '')) + '" data-club="' + escapeHtml(String(club || '')) + '" style="margin-top:8px;padding:8px 14px;background:#001f3f;color:#fff;border:none;border-radius:6px;font-size:0.9rem;cursor:pointer;">Add Media</button>' : '';
                                    mentionsSectionHtml = '<div class="sailor-public-mentions"><h2 class="sailor-media-page-header">Sailor &quot;' + escapeHtml(sailorNameForMedia) + '&quot; in the Media</h2><h3 class="sailor-media-section-title">Media</h3><p class="sailor-mentions-subtitle">Publicly available articles, posts and videos.</p>' + (addMediaBtn ? '<div class="sailor-media-header-actions">' + addMediaBtn + '</div>' : '') + '<div class="media-list">' + mentionCards + '</div></div>';
                                } else {
                                    var addMediaBtnEmpty = isLoggedInUser ? '<button type="button" class="add-media-btn" id="add-media-btn" data-sa-id="' + escapeHtml(String(sid)) + '" data-name="' + escapeHtml(String(name || '')) + '" data-club="' + escapeHtml(String(club || '')) + '" style="margin-top:8px;padding:8px 14px;background:#001f3f;color:#fff;border:none;border-radius:6px;font-size:0.9rem;cursor:pointer;">Add Media</button>' : '';
                                    mentionsSectionHtml = '<div class="sailor-public-mentions"><h2 class="sailor-media-page-header">Sailor &quot;' + escapeHtml(sailorNameForMedia) + '&quot; in the Media</h2><h3 class="sailor-media-section-title">Media</h3><p class="sailor-mentions-subtitle">No public mentions yet.</p>' + (addMediaBtnEmpty ? '<div class="sailor-media-header-actions">' + addMediaBtnEmpty + '</div>' : '') + '</div>';
                                }
                            } catch (err) {
                                console.error("❌ Error in public mentions fetch:", err);
                                console.error("Stack:", err.stack);
                            }
                            var activitySectionHtml = '';
                            if (!isLoggedInUser) {
                                try {
                                    var activityRes = await fetch(API + '/api/member/' + encodeURIComponent(sid) + '/activity').catch(function() { return null; });
                                    var activityData = (activityRes && activityRes.ok) ? await activityRes.json() : { years: [] };
                                    var activityYears = Array.isArray(activityData.years) ? activityData.years : [];
                                    if (activityYears.length > 0) {
                                        var yearBlocks = activityYears.map(function(yrObj) {
                                            var yearNum = yrObj.year;
                                            var items = Array.isArray(yrObj.items) ? yrObj.items : [];
                                            var cards = items.map(function(item) {
                                                var url = (item.url || '').replace(/"/g, '&quot;');
                                                var titleEsc = escapeHtml((item.title || '').trim() || 'Untitled');
                                                var snippetEsc = escapeHtml((item.snippet || '').trim());
                                                var sourceEsc = escapeHtml((item.source || '').trim() || '');
                                                var timeAgo = (item.time_ago || '').trim();
                                                var metaText = sourceEsc + (timeAgo ? ' \u2022 ' + escapeHtml(timeAgo) : '');
                                                var type = (item.type || 'article').toLowerCase();
                                                var icon = type === 'video' ? '\u25B6\uFE0F' : (type === 'photo' ? '\uD83D\uDCF7' : '\uD83D\uDCC4');
                                                var thumb = (item.thumb_url && String(item.thumb_url).trim() && item.thumb_url.indexOf('http') === 0) ? item.thumb_url.trim() : '';
                                                if (thumb) { var _api = (window.API_BASE || window.location.origin || '').replace(/\/$/, ''); thumb = _api + '/api/thumbnail?url=' + encodeURIComponent(thumb); }
                                                var mediaBlock = thumb ? '<div class="feed-item-media"><img class="feed-item-image" src="' + escapeHtml(thumb) + '" alt="" loading="lazy" onerror="this.style.display=\'none\'" /></div>' : '';
                                                var headlineBlock = thumb ? '<h3 class="feed-item-headline">' + titleEsc + '</h3>' : '<div class="feed-item-headline-row"><span class="feed-item-icon" aria-hidden="true">' + icon + '</span><h3 class="feed-item-headline">' + titleEsc + '</h3></div>';
                                                var snippetBlock = snippetEsc ? '<p class="feed-item-snippet">' + snippetEsc + '</p>' : '';
                                                var metaBlock = metaText ? '<div class="feed-item-meta">' + metaText + '</div>' : '';
                                                return '<a class="feed-item" href="' + url + '" target="_blank" rel="noopener noreferrer">' + mediaBlock + '<div class="feed-item-body">' + headlineBlock + snippetBlock + metaBlock + '</div></a>';
                                            }).join('');
                                            return '<div class="feed-year-header">' + escapeHtml(String(yearNum)) + '</div><div class="feed-list">' + cards + '</div>';
                                        }).join('');
                                        activitySectionHtml = '<div class="sailor-activity-timeline"><h2>Sailor Activity</h2><p class="sailor-activity-subtitle">Self-published or community posts about this sailor.</p><div class="activity-timeline">' + yearBlocks + '</div></div>';
                                    }
                                } catch (_) {}
                            }
                            (async function renderApprovedSailorProfileCard() {
                                function formatApprovedDate(dateStr) {
                                    if (!dateStr) return 'Date unknown';
                                    var d = new Date(dateStr);
                                    if (isNaN(d.getTime())) return escapeHtml(String(dateStr));
                                    var monthsShort = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                                    return String(d.getDate()).padStart(2, '0') + ' ' + monthsShort[d.getMonth()] + ' ' + d.getFullYear();
                                }
                                function formatApprovedDurationShort(rows) {
                                    if (!rows || !rows.length) return '—';
                                    var times = rows.map(function(r) {
                                        var t = new Date(r.dateStr || '').getTime();
                                        return isNaN(t) ? null : t;
                                    }).filter(function(v) { return v != null; });
                                    if (!times.length) return '0 yrs 0 mths';
                                    var oldest = new Date(Math.min.apply(null, times));
                                    var now = new Date();
                                    var years = now.getFullYear() - oldest.getFullYear();
                                    var months = now.getMonth() - oldest.getMonth();
                                    if (now.getDate() < oldest.getDate()) months -= 1;
                                    if (months < 0) { years -= 1; months += 12; }
                                    if (years < 0) { years = 0; months = 0; }
                                    return years + ' yrs ' + months + ' mths';
                                }
                                function normalizeApprovedClassKey(name) {
                                    return normalizeClassName(String(name || '')).toLowerCase().replace(/\s+fleet\s*$/i, '').trim();
                                }
                                function buildApprovedChevron(dir) {
                                    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + (dir === 'up' ? 'M6 14l6-6 6 6' : 'M6 10l6 6 6-6') + '" stroke-linecap="round" stroke-linejoin="round"></path></svg>';
                                }
                                function buildApprovedCalendarIcon() {
                                    return '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="6" width="16" height="14" rx="2"></rect><path d="M8 4v4M16 4v4M4 10h16"></path></svg>';
                                }
                                function buildApprovedStarIcon(stroke) {
                                    return '<svg viewBox="0 0 24 24" aria-hidden="true" style="color:' + stroke + ';"><path d="M12 3.6l2.5 5.1 5.7.8-4.1 4 1 5.7L12 16.7 6.9 19.2l1-5.7-4.1-4 5.7-.8L12 3.6z" stroke="currentColor" stroke-linejoin="round"></path></svg>';
                                }
                                function buildApprovedSailIcon(color) {
                                    return '<svg viewBox="0 0 24 24" aria-hidden="true" style="color:' + color + ';"><path d="M12 4v14"></path><path d="M12 5l6 11H12z"></path><path d="M12 7L7 16h5"></path><path d="M5 19h14"></path></svg>';
                                }
                                function buildApprovedAllClassesIcon() {
                                    return '<svg viewBox="0 0 24 24" aria-hidden="true" style="color:#18a99f;"><path d="M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path><path d="M6 17l3-10 3 10H6z" fill="currentColor"></path><path d="M12 17l2.6-8.8 2.6 8.8H12z" fill="currentColor" opacity="0.75"></path><path d="M9 17l1.5-5.2 1.5 5.2H9z" fill="currentColor" opacity="0.55"></path></svg>';
                                }
                                function formatApprovedOrdinal(rank) {
                                    var n = parseInt(rank, 10);
                                    if (!n || isNaN(n)) return '—';
                                    var rem = n % 100;
                                    if (rem >= 11 && rem <= 13) return n + 'th';
                                    var last = n % 10;
                                    if (last === 1) return n + 'st';
                                    if (last === 2) return n + 'nd';
                                    if (last === 3) return n + 'rd';
                                    return n + 'th';
                                }
                                function extractApprovedPointsDigits(value) {
                                    if (value == null || value === '' || isNaN(Number(value))) return [];
                                    return String(Math.round(Number(value))).split('');
                                }
                                function getApprovedClassLogoCandidates(className) {
                                    var key = normalizeApprovedClassKey(className);
                                    var list = [];
                                    var push = function(p) {
                                        if (!p) return;
                                        var t = String(p).trim();
                                        if (!t) return;
                                        if (list.indexOf(t) !== -1) return;
                                        list.push(t);
                                    };
                                    var fileMap = {
                                        'ilca 4': 'ILCA-4.7-Class-Logo.png',
                                        'ilca 4.7': 'ILCA-4.7-Class-Logo.png',
                                        'ilca 6': 'ILCA-6-Class-Logo.png',
                                        'ilca 7': 'ILCA-7-Class-Logo.png',
                                        'ilca': 'ILCA-Class-Logo.png',
                                        'optimist': 'Optimist-Class-Logo.png',
                                        'optimist a': 'Optimist-A-Class-Logo.png',
                                        'optimist b': 'Optimist-B-Class-Logo.png',
                                        'optimist c': 'Optimist-C-Class-Logo.png',
                                        'df95': 'DF95-Class-Logo.png',
                                        'df 95': 'DF95-Class-Logo.png',
                                        'dragonflite': 'DF95-Class-Logo.png',
                                        'dragonflite 95': 'DF95-Class-Logo.png',
                                        'dragon flight': 'DF95-Class-Logo.png',
                                        'dragon flight 95': 'DF95-Class-Logo.png',
                                        '420': '420-Class-Logo.png',
                                        '505': '505-Class-Logo.png',
                                        'open': 'Open-Class-Logo.png',
                                        'open a': 'Open-Class-Logo.png',
                                        'mirror': 'Mirror-Class-Logo.png',
                                        'dabchick': 'Dabchick-Class-Logo.png',
                                        'sonnet': 'Sonnet-Class-Logo.png',
                                        'gp14': 'GP14-Class-Logo.png',
                                        'soling': 'Soling-Class-Logo.png',
                                        'tsl': 'TSL-Class-Logo.png',
                                        'flying dutchman': 'Flying-Dutchman-Class-Logo.png',
                                        'flying fifteen': 'Flying-Fifteen-Class-Logo.png',
                                        'windsurfer lt': 'Windsurfer-LT-Class-Logo.png',
                                        'multihull': 'Multihull-Fleet-Class-Logo.png',
                                        'multihull fleet': 'Multihull-Fleet-Class-Logo.png',
                                        'topper 5.3': 'Topper-5.3-Class-Logo.png',
                                        'halcat': 'Halcat-Class-Logo.png',
                                        'j22': 'J22-Class-Logo.png',
                                        'hobie 14': 'Hobie-14-Class-Logo.png',
                                        'hobie tiger': 'Hobie-Tiger-Class-Logo.png',
                                        'hunter': 'Hunter-19-Class-Logo.png',
                                        'hunter 19': 'Hunter-19-Class-Logo.png',
                                        'hunter19': 'Hunter-19-Class-Logo.png',
                                        'hunter 19 fleet': 'Hunter-19-Class-Logo.png',
                                        'jpk': 'JPK-1010-Class-Logo.png',
                                        'jpk 1010': 'JPK-1010-Class-Logo.png',
                                        'jpk1010': 'JPK-1010-Class-Logo.png',
                                        'jpk 10.10': 'JPK-1010-Class-Logo.png',
                                        'jpk10.10': 'JPK-1010-Class-Logo.png',
                                        'pacer': 'Pacer-27-Class-Logo.png',
                                        'pacer 27': 'Pacer-27-Class-Logo.png',
                                        'pacer27': 'Pacer-27-Class-Logo.png'
                                    };
                                    var file = fileMap[key] || '';
                                    if (file) push('/artwork/Class Logo/' + file);
                                    try {
                                        var labelNorm = normalizeClassName(String(className || '')).replace(/\s+fleet\s*$/i, '').trim();
                                        var base = labelNorm;
                                        var opt = base.match(/^Optimist\s+([ABC])$/i);
                                        if (opt) base = 'Optimist';
                                        base = base.replace(/\s+/g, '-').replace(/[\/]/g, '-').trim();
                                        if (base) push('/artwork/Class Logo/' + base + '-Class-Logo.png');
                                    } catch (_) {}
                                    if (apiBase) {
                                        list.slice().forEach(function(p) {
                                            if (p && p.charAt(0) === '/') push(apiBase + p);
                                        });
                                    }
                                    return list;
                                }
                                function buildApprovedClassLogoImgHtml(label, candidates) {
                                    var list = Array.isArray(candidates) ? candidates : [];
                                    if (!list.length) return '';
                                    var candAttr = escapeHtml(list.join('|'));
                                    return '<img src="' + escapeHtml(list[0]) + '" alt="' + escapeHtml(label || '') + '" loading="lazy" data-sa-candidates="' + candAttr + '" data-sa-idx="0" onerror="try{var c=(this.dataset.saCandidates||\'\').split(\'|\');var i=parseInt(this.dataset.saIdx||\'0\',10)+1; if(c && i<c.length && c[i]){this.dataset.saIdx=String(i);this.src=c[i];}else{this.style.display=\\\'none\\\';}}catch(e){this.style.display=\\\'none\\\';}">';
                                }
                                function buildApprovedClassIconHtml(item) {
                                    if (!item) return buildApprovedAllClassesIcon();
                                    if (item.key === 'all') return buildApprovedAllClassesIcon();
                                    var candidates = item.logoCandidates || (item.logoSrc ? [item.logoSrc] : []);
                                    var imgHtml = buildApprovedClassLogoImgHtml(item.label || '', candidates);
                                    if (imgHtml) return imgHtml;
                                    return buildApprovedSailIcon('#18a99f');
                                }
                                function buildApprovedMedal(rank) {
                                    var num = parseInt(rank, 10);
                                    if (!num || isNaN(num)) return '<span class="sa-approved-sailor-result-medal other"></span>';
                                    if (num === 1) return '<span class="sa-approved-sailor-result-medal rank-1">🥇</span>';
                                    if (num === 2) return '<span class="sa-approved-sailor-result-medal rank-2">🥈</span>';
                                    if (num === 3) return '<span class="sa-approved-sailor-result-medal rank-3">🥉</span>';
                                    return '<span class="sa-approved-sailor-result-medal other">' + escapeHtml(String(num)) + '</span>';
                                }
                                function buildApprovedClubMiniIcon() {
                                    if (isIntlSailor && intlFlagUrl) return '<span class="sa-approved-sailor-club-icon"><img src="' + escapeHtml(intlFlagUrl) + '" alt="' + escapeHtml(clubD || 'Club') + '" loading="lazy"></span>';
                                    if (clubLogoUrl) return '<span class="sa-approved-sailor-club-icon"><img src="' + escapeHtml(clubLogoUrl) + '" alt="' + escapeHtml(finalClubTitle) + '" loading="lazy" onerror="this.style.display=\'none\'; var n=this.nextElementSibling; if(n) n.style.display=\'inline-flex\';"><span class="club-code-fallback" style="display:none">' + escapeHtml(finalClubCode || '') + '</span></span>';
                                    if (finalClubCode) return '<span class="sa-approved-sailor-club-icon"><span class="club-code-fallback" style="display:inline-flex">' + escapeHtml(finalClubCode) + '</span></span>';
                                    return '<span class="sa-approved-sailor-club-icon"><span class="club-code-fallback" style="display:inline-flex">—</span></span>';
                                }
                                function getApprovedRowHref(item) {
                                    if (!item) return '';
                                    return typeof highlightRegattaHref === 'function' ? (highlightRegattaHref(item) || '') : '';
                                }
                                var approvedRankingsByKey = {};
                                (rankings || []).forEach(function(r) {
                                    var rawKey = String((r.class_code || r.class_name || r.class || '')).trim();
                                    if (!rawKey) return;
                                    var norm = normalizeApprovedClassKey(rawKey);
                                    if (norm) approvedRankingsByKey[norm] = r;
                                });
                                function getApprovedSaRankData(selectedKey) {
                                    var row = null;
                                    if (selectedKey && selectedKey !== 'all') row = approvedRankingsByKey[normalizeApprovedClassKey(selectedKey)] || null;
                                    if (!row) return { rankText: 'NONE', pointsDigits: [] };
                                    var rankVal = row.rank != null ? row.rank : (row.position != null ? row.position : (row.main_rank != null ? row.main_rank : row.rank_position));
                                    var pointsVal = row.ranking_score != null ? row.ranking_score : (row.score != null ? row.score : (row.points != null ? row.points : row.wc_score));
                                    return {
                                        rankText: String(rankVal != null && rankVal !== '' ? rankVal : 'NONE'),
                                        pointsDigits: extractApprovedPointsDigits(pointsVal)
                                    };
                                }
                                function getApprovedSslRankData() {
                                    var sslInfo = (typeof sslIntl !== 'undefined' && sslIntl) ? sslIntl : null;
                                    if (!sslInfo) return { rankText: '—', pointsDigits: [] };
                                    return {
                                        rankText: String(sslInfo.ssl_rank != null && sslInfo.ssl_rank !== '' ? sslInfo.ssl_rank : '—'),
                                        pointsDigits: extractApprovedPointsDigits(sslInfo.ssl_points)
                                    };
                                }
                                function getApprovedSslProfileHref() {
                                    var sslInfo = (typeof sslIntl !== 'undefined' && sslIntl) ? sslIntl : null;
                                    if (!sslInfo) return '';
                                    if (sslInfo.ssl_profile_url) return String(sslInfo.ssl_profile_url).trim();
                                    if (sslInfo.ssl_profile_slug) return 'https://worldofsailors.com/sailor/' + encodeURIComponent(String(sslInfo.ssl_profile_slug).trim());
                                    return '';
                                }
                                function getApprovedClubHref() {
                                    if (finalClubHref) return String(finalClubHref).trim();
                                    return '';
                                }
                                function getApprovedProvinceHref() {
                                    return provinceWeb ? String(provinceWeb).trim() : '';
                                }
                                function getApprovedRankingsHref(card) {
                                    if (!card || !card.key || card.key === 'all') return '/rankings';
                                    var cls = normalizeClassName(String(card.key || '')).replace(/\s+/g, '-').toLowerCase();
                                    return cls ? ('/rankings/?class=' + encodeURIComponent(cls)) : '/rankings';
                                }
                                function getApprovedClassHref(card) {
                                    if (!card) return '';
                                    if (card.key === 'all') return '/rankings';
                                    var slug = normalizeClassName(String(card.key || '')).replace(/\s+/g, '-').toLowerCase();
                                    return slug ? ('/class/' + encodeURIComponent(slug)) : '';
                                }
                                function findApprovedPublishedRankRow(list, sasId, sailorSlug) {
                                    var sid = String(sasId || '').trim();
                                    var slug = String(sailorSlug || '').trim().toLowerCase();
                                    if (!Array.isArray(list) || (!sid && !slug)) return null;
                                    return list.find(function(row) {
                                        var rowSid = String((row && (row.sasId || row.sas_id || row.sa_id || row.sailor_id)) || '').trim();
                                        var rowSlug = String((row && row.slug) || '').trim().toLowerCase();
                                        if (sid && rowSid && (rowSid === sid || String(Number(rowSid)) === String(Number(sid)))) return true;
                                        if (slug && rowSlug && rowSlug === slug) return true;
                                        return false;
                                    }) || null;
                                }
                                var approvedAuditPopupCache = {};
                                var approvedAuditPopupPending = {};
                                var approvedAuditPopupEl = null;
                                var approvedAuditPopupOpen = null;
                                var approvedAuditPopupCloseTimer = null;
                                function ensureApprovedAuditPopup() {
                                    if (approvedAuditPopupEl) return approvedAuditPopupEl;
                                    approvedAuditPopupEl = document.createElement('section');
                                    approvedAuditPopupEl.id = 'rkAuditCalcPopup';
                                    approvedAuditPopupEl.className = 'rk-audit-popup';
                                    approvedAuditPopupEl.hidden = true;
                                    approvedAuditPopupEl.setAttribute('role', 'dialog');
                                    approvedAuditPopupEl.setAttribute('aria-modal', 'false');
                                    approvedAuditPopupEl.setAttribute('aria-live', 'polite');
                                    approvedAuditPopupEl.innerHTML = '<div class="rk-audit-popup-inner"><div class="rk-audit-popup-loading">Loading…</div></div>';
                                    document.body.appendChild(approvedAuditPopupEl);
                                    approvedAuditPopupEl.addEventListener('mouseenter', function() {
                                        if (approvedAuditPopupCloseTimer) {
                                            clearTimeout(approvedAuditPopupCloseTimer);
                                            approvedAuditPopupCloseTimer = null;
                                        }
                                    });
                                    approvedAuditPopupEl.addEventListener('mouseleave', scheduleApprovedAuditPopupClose);
                                    approvedAuditPopupEl.addEventListener('click', function(e) {
                                        var closeBtn = e.target.closest ? e.target.closest('[data-rk-popup-close]') : null;
                                        if (!closeBtn) return;
                                        e.preventDefault();
                                        closeApprovedAuditPopup();
                                    });
                                    document.addEventListener('click', function(e) {
                                        if (!approvedAuditPopupOpen || !approvedAuditPopupEl || approvedAuditPopupEl.hidden) return;
                                        if (approvedAuditPopupEl.contains(e.target)) return;
                                        if (approvedAuditPopupOpen.trigger && approvedAuditPopupOpen.trigger.contains(e.target)) return;
                                        closeApprovedAuditPopup();
                                    });
                                    document.addEventListener('keydown', function(e) {
                                        if (e.key === 'Escape' && approvedAuditPopupOpen) closeApprovedAuditPopup();
                                    });
                                    return approvedAuditPopupEl;
                                }
                                function scheduleApprovedAuditPopupClose() {
                                    if (approvedAuditPopupCloseTimer) clearTimeout(approvedAuditPopupCloseTimer);
                                    approvedAuditPopupCloseTimer = setTimeout(closeApprovedAuditPopup, 240);
                                }
                                function closeApprovedAuditPopup() {
                                    if (approvedAuditPopupCloseTimer) {
                                        clearTimeout(approvedAuditPopupCloseTimer);
                                        approvedAuditPopupCloseTimer = null;
                                    }
                                    if (approvedAuditPopupOpen && approvedAuditPopupOpen.trigger) {
                                        approvedAuditPopupOpen.trigger.setAttribute('aria-expanded', 'false');
                                    }
                                    approvedAuditPopupOpen = null;
                                    if (approvedAuditPopupEl) {
                                        approvedAuditPopupEl.hidden = true;
                                        approvedAuditPopupEl.classList.remove('is-mobile');
                                    }
                                }
                                function positionApprovedAuditPopup(trigger) {
                                    var popup = ensureApprovedAuditPopup();
                                    if (!popup || !trigger) return;
                                    if (window.matchMedia && window.matchMedia('(max-width: 480px)').matches) {
                                        popup.classList.add('is-mobile');
                                        popup.style.left = '0';
                                        popup.style.right = '0';
                                        popup.style.top = 'auto';
                                        popup.style.bottom = '0';
                                        popup.style.width = '100%';
                                        popup.style.maxWidth = '100%';
                                        return;
                                    }
                                    popup.classList.remove('is-mobile');
                                    popup.style.width = 'min(460px, calc(100vw - 24px))';
                                    popup.style.maxWidth = '460px';
                                    var rect = trigger.getBoundingClientRect();
                                    var popupRect = popup.getBoundingClientRect();
                                    var gap = 10;
                                    var x = rect.right + gap;
                                    var y = rect.top;
                                    if (x + popupRect.width > window.innerWidth - 10) x = rect.left - popupRect.width - gap;
                                    if (x < 10) {
                                        x = Math.max(10, rect.left);
                                        y = rect.bottom + gap;
                                    }
                                    if (y + popupRect.height > window.innerHeight - 10) y = Math.max(10, window.innerHeight - popupRect.height - 10);
                                    popup.style.left = Math.round(x) + 'px';
                                    popup.style.top = Math.round(y) + 'px';
                                    popup.style.bottom = 'auto';
                                    popup.style.right = 'auto';
                                }
                                function renderApprovedAuditContributionRow(row) {
                                    var ageWeeks = Number(row && row.age_weeks || 0);
                                    var ageBand = ageWeeks <= 52 ? '100%' : (ageWeeks <= 104 ? '50%' : 'Expired');
                                    return '' +
                                        '<div class="rk-audit-row-item">' +
                                            '<div class="rk-audit-row-title">' + escapeHtml((row && row.event_name) || 'Unknown event') + '</div>' +
                                            '<div class="rk-audit-row-meta">' + escapeHtml((row && row.event_date) || '—') + ' · Age ' + escapeHtml((row && row.age_weeks) == null ? '—' : String(row.age_weeks) + 'w') + ' · ' + escapeHtml(ageBand) + '</div>' +
                                            '<div class="rk-audit-row-grid">' +
                                                '<span>Class</span><strong>' + escapeHtml((row && row.class_name) || '—') + '</strong>' +
                                                '<span>Fleet</span><strong>' + escapeHtml((row && (row.ranking_fleet_label || row.scored_fleet)) || '—') + ' (N=' + escapeHtml((row && row.fleet_size) == null ? '—' : row.fleet_size) + ')</strong>' +
                                                '<span>Place</span><strong>' + escapeHtml((row && row.place) == null ? '—' : row.place) + '</strong>' +
                                                '<span>Category</span><strong>' + escapeHtml((row && row.category_name) || ((row && row.category) ? ('Cat ' + row.category) : '—')) + '</strong>' +
                                                '<span>Points</span><strong>' + escapeHtml(Number((row && row.final_points) || 0).toFixed(2)) + '</strong>' +
                                            '</div>' +
                                            '<div class="rk-audit-row-reason">' + escapeHtml((row && row.reason) || '—') + '</div>' +
                                        '</div>';
                                }
                                function renderApprovedAuditPopup(payload) {
                                    var popup = ensureApprovedAuditPopup();
                                    var summary = payload && payload.summary ? payload.summary : {};
                                    var counted = payload && Array.isArray(payload.counted) ? payload.counted : [];
                                    var excluded = payload && Array.isArray(payload.excluded) ? payload.excluded : [];
                                    var audit = payload && payload.audit ? payload.audit : {};
                                    var technical = payload && payload.technical ? payload.technical : {};
                                    var diff = Number(summary.diff || 0);
                                    var mismatch = Math.abs(diff) >= 0.01;
                                    popup.hidden = false;
                                    popup.innerHTML = '' +
                                        '<div class="rk-audit-popup-inner">' +
                                            '<div class="rk-audit-popup-head">' +
                                                '<div class="rk-audit-popup-title-wrap">' +
                                                    '<h3 class="rk-audit-popup-title">' + escapeHtml(summary.sailor_name || 'Sailor') + '</h3>' +
                                                    '<p class="rk-audit-popup-sub">Rank ' + escapeHtml(summary.rank == null ? '—' : summary.rank) + ' · ' + escapeHtml(Number(summary.total_points || 0).toFixed(2)) + ' pts</p>' +
                                                    '<p class="rk-audit-popup-sub">' + escapeHtml(summary.board_label || 'Skipper') + ' · Audit ' + escapeHtml(audit.ranking_version || '—') + '</p>' +
                                                '</div>' +
                                                '<button type="button" class="rk-audit-close" data-rk-popup-close="1" aria-label="Close score details">Close</button>' +
                                            '</div>' +
                                            '<div class="rk-audit-pillbar">' +
                                                '<span>Audit ID: ' + escapeHtml(audit.audit_id == null ? '—' : audit.audit_id) + '</span>' +
                                                '<span>Formula: ' + escapeHtml(audit.formula_version || '—') + '</span>' +
                                                '<span>Generated: ' + escapeHtml(audit.calculated_at || '—') + '</span>' +
                                            '</div>' +
                                            '<section class="rk-audit-section">' +
                                                '<h4>Counted results (' + counted.length + ')</h4>' +
                                                (counted.map(renderApprovedAuditContributionRow).join('') || '<div class="rk-audit-muted">No counted contributions found.</div>') +
                                                '<div class="rk-audit-totals">' +
                                                    '<div>Counted total: <strong>' + escapeHtml(Number(summary.counted_total || 0).toFixed(2)) + '</strong></div>' +
                                                    '<div>Published total: <strong>' + escapeHtml(Number(summary.total_points || 0).toFixed(2)) + '</strong></div>' +
                                                    '<div>Difference: <strong>' + escapeHtml(diff.toFixed(2)) + '</strong></div>' +
                                                '</div>' +
                                                (mismatch ? '<div class="rk-audit-mismatch">AUDIT MISMATCH: counted total does not match published total.</div>' : '') +
                                            '</section>' +
                                            '<details class="rk-audit-section"><summary>Not counted (' + excluded.length + ')</summary>' +
                                                (excluded.map(renderApprovedAuditContributionRow).join('') || '<div class="rk-audit-muted">No excluded results recorded.</div>') +
                                            '</details>' +
                                            '<details class="rk-audit-section"><summary>Why this rank changed</summary>' +
                                                '<div class="rk-audit-change">' +
                                                    '<div>Previous rank: ' + escapeHtml(summary.previous_rank == null ? '—' : summary.previous_rank) + '</div>' +
                                                    '<div>Previous points: ' + escapeHtml(summary.previous_points == null ? '—' : Number(summary.previous_points).toFixed(2)) + '</div>' +
                                                    '<div>Current rank: ' + escapeHtml(summary.rank == null ? '—' : summary.rank) + '</div>' +
                                                    '<div>Current points: ' + escapeHtml(Number(summary.total_points || 0).toFixed(2)) + '</div>' +
                                                    '<div>' + escapeHtml(summary.change_reason || 'No explicit change record available in snapshot.') + '</div>' +
                                                '</div>' +
                                            '</details>' +
                                            '<details class="rk-audit-section"><summary>Technical audit data</summary>' +
                                                '<div class="rk-audit-tech">' +
                                                    '<div>audit_id: ' + escapeHtml(technical.audit_id) + '</div>' +
                                                    '<div>audit_version: ' + escapeHtml(technical.ranking_version) + '</div>' +
                                                    '<div>sailor_slug: ' + escapeHtml(technical.sailor_slug) + '</div>' +
                                                    '<div>sas_id: ' + escapeHtml(technical.sas_id) + '</div>' +
                                                    '<div>role: ' + escapeHtml(technical.board) + '</div>' +
                                                    '<div>result_ids: ' + escapeHtml(((technical.result_ids || []).join(', '))) + '</div>' +
                                                    '<div>regatta_ids: ' + escapeHtml(((technical.regatta_ids || []).join(', '))) + '</div>' +
                                                    '<div>contrib_ids: ' + escapeHtml(((technical.contrib_ids || []).join(', '))) + '</div>' +
                                                '</div>' +
                                            '</details>' +
                                        '</div>';
                                }
                                function fetchApprovedAuditPopupDetails(opts) {
                                    var key = [opts.auditVersion || '', opts.sailorSlug || '', opts.sasId || '', 'skipper'].join('|');
                                    if (approvedAuditPopupCache[key]) return Promise.resolve(approvedAuditPopupCache[key]);
                                    if (approvedAuditPopupPending[key]) return approvedAuditPopupPending[key];
                                    var params = new URLSearchParams();
                                    params.set('board', 'skipper');
                                    if (opts.sailorSlug) params.set('sailor_slug', opts.sailorSlug);
                                    if (opts.sasId) params.set('sas_id', opts.sasId);
                                    if (opts.auditVersion) params.set('audit_version', opts.auditVersion);
                                    approvedAuditPopupPending[key] = fetch('/api/rankings/audit-popup?' + params.toString(), {
                                        credentials: 'same-origin',
                                        cache: 'no-store'
                                    }).then(function(res) {
                                        if (!res.ok) throw new Error('HTTP ' + res.status);
                                        return res.json();
                                    }).then(function(payload) {
                                        approvedAuditPopupCache[key] = payload;
                                        delete approvedAuditPopupPending[key];
                                        return payload;
                                    }).catch(function(err) {
                                        delete approvedAuditPopupPending[key];
                                        throw err;
                                    });
                                    return approvedAuditPopupPending[key];
                                }
                                function bindApprovedSaRankAuditPopup(trigger, opts) {
                                    if (!trigger || trigger.dataset.saAuditBound === '1') return;
                                    trigger.dataset.saAuditBound = '1';
                                    ensureApprovedAuditPopup();
                                    function openPopup() {
                                        if (approvedAuditPopupCloseTimer) {
                                            clearTimeout(approvedAuditPopupCloseTimer);
                                            approvedAuditPopupCloseTimer = null;
                                        }
                                        if (approvedAuditPopupOpen && approvedAuditPopupOpen.trigger !== trigger) approvedAuditPopupOpen.trigger.setAttribute('aria-expanded', 'false');
                                        approvedAuditPopupOpen = { trigger: trigger };
                                        trigger.setAttribute('aria-expanded', 'true');
                                        approvedAuditPopupEl.hidden = false;
                                        approvedAuditPopupEl.innerHTML = '<div class="rk-audit-popup-inner"><div class="rk-audit-popup-loading">Loading score details…</div></div>';
                                        positionApprovedAuditPopup(trigger);
                                        fetchApprovedAuditPopupDetails(opts).then(function(payload) {
                                            if (!approvedAuditPopupOpen || approvedAuditPopupOpen.trigger !== trigger) return;
                                            renderApprovedAuditPopup(payload);
                                            positionApprovedAuditPopup(trigger);
                                        }).catch(function(err) {
                                            if (!approvedAuditPopupOpen || approvedAuditPopupOpen.trigger !== trigger) return;
                                            approvedAuditPopupEl.hidden = false;
                                            approvedAuditPopupEl.innerHTML = '<div class="rk-audit-popup-inner"><div class="rk-audit-popup-error">Score details unavailable (' + escapeHtml(err && err.message ? err.message : 'error') + ').</div></div>';
                                            positionApprovedAuditPopup(trigger);
                                        });
                                    }
                                    trigger.addEventListener('mouseenter', openPopup);
                                    trigger.addEventListener('focus', openPopup);
                                    trigger.addEventListener('mouseleave', scheduleApprovedAuditPopupClose);
                                }
                                function buildApprovedResultItem(item, kind) {
                                    var title = '';
                                    if (kind === 'highlights') {
                                        title = item.regattaName || ((item.text || '').replace(/^\s*\d+(?:st|nd|rd|th)\s+place\s+[–-]\s+/i, '').trim()) || 'Result';
                                    } else {
                                        title = item.event_name || item.regattaName || 'Result';
                                    }
                                    var classLabel = item.className || 'All Classes';
                                    var classIconHtml = '';
                                    if (!item || !item.className) {
                                        classIconHtml = buildApprovedAllClassesIcon();
                                    } else {
                                        var classCandidates = getApprovedClassLogoCandidates(item.className);
                                        classIconHtml = buildApprovedClassLogoImgHtml(item.className, classCandidates) || buildApprovedSailIcon('#18a99f');
                                    }
                                    var metaParts = [formatApprovedDate(item.dateStr || '')];
                                    if (item.club) metaParts.push(escapeHtml(item.club));
                                    var metaHtml = '' +
                                        '<span>' + metaParts.join(' <span aria-hidden="true">•</span> ') + '</span>' +
                                        '<span class="sa-approved-sailor-chip sa-approved-sailor-chip-with-logo">' +
                                            '<span class="sa-approved-sailor-chip-logo">' + classIconHtml + '</span>' +
                                            '<span class="sa-approved-sailor-chip-text">' + escapeHtml(classLabel) + '</span>' +
                                        '</span>';
                                    var entriesVal = item.entries != null && item.entries !== '' ? parseInt(item.entries, 10) : null;
                                    var fleetText = entriesVal && !isNaN(entriesVal) ? ('Fleet: ' + entriesVal) : '';
                                    return '' +
                                        '<div class="sa-approved-sailor-result-row" data-profile-row-kind="' + escapeHtml(kind) + '" data-profile-row-id="' + escapeHtml(String(item.__rowId || '')) + '">' +
                                            buildApprovedMedal(item.rank) +
                                            '<div class="sa-approved-sailor-result-main">' +
                                                '<div class="sa-approved-sailor-result-title">' + escapeHtml(title) + '</div>' +
                                                '<div class="sa-approved-sailor-result-meta">' + metaHtml + '</div>' +
                                            '</div>' +
                                            '<div class="sa-approved-sailor-result-rank">' +
                                                '<span class="place">' + escapeHtml(formatApprovedOrdinal(item.rank)) + ' Overall</span>' +
                                                '<span class="fleet">' + escapeHtml(fleetText || 'Fleet: —') + '</span>' +
                                            '</div>' +
                                            '<span class="sa-approved-sailor-result-arrow">' + buildApprovedChevron('down').replace('M6 10l6 6 6-6', 'M9 6l6 6-6 6') + '</span>' +
                                        '</div>';
                                }
                                function openApprovedResult(item) {
                                    if (!item) return;
                                    if (!canClickRegattas) {
                                        if (typeof showLoginRequiredPopup === 'function') showLoginRequiredPopup();
                                        return;
                                    }
                                    if ((item.result_href || item.block_id || item.isSubFleetChild) && getApprovedRowHref(item)) {
                                        window.location.href = getApprovedRowHref(item);
                                        return;
                                    }
                                    if (typeof showRegattaResultChoice === 'function' && item.regatta_id) {
                                        showRegattaResultChoice(item.regatta_id, item.className || '', item.event_name || item.regattaName || '');
                                        return;
                                    }
                                    var href = getApprovedRowHref(item);
                                    if (href) window.location.href = href;
                                }
                                var approvedClassCards = [];
                                classEntries.forEach(function(className) {
                                    var logoCandidates = getApprovedClassLogoCandidates(className);
                                    approvedClassCards.push({
                                        key: className,
                                        label: className,
                                        logoCandidates: logoCandidates,
                                        logoSrc: (logoCandidates && logoCandidates.length) ? logoCandidates[0] : '',
                                        stats: classStats[className] || { rg: 0, r: 0 }
                                    });
                                });
                                if (regattaCount > 0 || raceCount > 0 || !approvedClassCards.length) {
                                    approvedClassCards.push({ key: 'all', label: 'All Classes', logoCandidates: [], logoSrc: '', stats: { rg: regattaCount || 0, r: raceCount || 0 } });
                                }
                                var approvedDefaultKey = (approvedClassCards.length ? approvedClassCards[0].key : 'all');
                                try {
                                    var best = null;
                                    approvedClassCards.forEach(function(c) {
                                        if (!c || c.key === 'all') return;
                                        var n = (c.stats && c.stats.rg != null) ? Number(c.stats.rg) : 0;
                                        if (!isFinite(n)) n = 0;
                                        if (!best || n > best.n) best = { n: n, key: c.key };
                                    });
                                    if (best && best.key) approvedDefaultKey = best.key;
                                } catch (_eBest) {}
                                var approvedState = {
                                    mode: 'expanded',
                                    tab: 'highlights',
                                    selectedKey: approvedDefaultKey,
                                    visibleRows: 8
                                };
                                var approvedSaBoardState = {
                                    loaded: false,
                                    rankText: 'NONE',
                                    pointsDigits: [],
                                    totalPoints: null,
                                    sailorSlug: '',
                                    auditVersion: null,
                                    popupEnabled: false
                                };
                                async function loadApprovedSaBoardRank() {
                                    if (approvedSaBoardState.loaded) return approvedSaBoardState;
                                    approvedSaBoardState.loaded = true;
                                    var sasIdRaw = String(((memberSource && memberSource.sas_id) || sid || '')).trim();
                                    var sailorSlug = (typeof window.sailingsaUrlLockedSlug === 'string' && window.sailingsaUrlLockedSlug) ? String(window.sailingsaUrlLockedSlug).trim() : '';
                                    if (!sailorSlug && /^\d+$/.test(sasIdRaw) && API) {
                                        try {
                                            var resolveRankRes = await fetch(API + '/api/sailor/resolve?sas_id=' + encodeURIComponent(sasIdRaw), { cache: 'no-store' }).catch(function() { return null; });
                                            var resolveRankData = (resolveRankRes && resolveRankRes.ok) ? await resolveRankRes.json() : null;
                                            if (resolveRankData && resolveRankData.slug) sailorSlug = String(resolveRankData.slug).trim();
                                        } catch (_) {}
                                    }
                                    approvedSaBoardState.sailorSlug = sailorSlug;
                                    try {
                                        var publishedRes = await fetch('/rankings/data/published.json', { credentials: 'same-origin', cache: 'no-store' }).catch(function() { return null; });
                                        var publishedPayload = (publishedRes && publishedRes.ok) ? await publishedRes.json() : null;
                                        var publishedRow = findApprovedPublishedRankRow(publishedPayload && publishedPayload.sailors, sasIdRaw, sailorSlug);
                                        if (publishedPayload && publishedPayload.auditVersion) approvedSaBoardState.auditVersion = String(publishedPayload.auditVersion);
                                        if (publishedRow) {
                                            approvedSaBoardState.rankText = String(publishedRow.rank != null && publishedRow.rank !== '' ? publishedRow.rank : 'NONE');
                                            approvedSaBoardState.totalPoints = (publishedRow.points != null && publishedRow.points !== '') ? Number(publishedRow.points) : null;
                                            approvedSaBoardState.pointsDigits = extractApprovedPointsDigits(approvedSaBoardState.totalPoints);
                                        }
                                    } catch (_) {}
                                    try {
                                        var capRes = await fetch('/api/rankings/audit-popup-capability', { credentials: 'same-origin', cache: 'no-store' }).catch(function() { return null; });
                                        var capData = (capRes && capRes.ok) ? await capRes.json() : null;
                                        approvedSaBoardState.popupEnabled = !!(capData && capData.enabled);
                                        if (capData && capData.audit && capData.audit.ranking_version) approvedSaBoardState.auditVersion = String(capData.audit.ranking_version);
                                    } catch (_) {
                                        approvedSaBoardState.popupEnabled = false;
                                    }
                                    if (approvedSaBoardState.rankText === 'NONE' && approvedSaBoardState.popupEnabled && sasIdRaw) {
                                        try {
                                            var params = new URLSearchParams();
                                            params.set('board', 'skipper');
                                            params.set('sas_id', sasIdRaw);
                                            if (approvedSaBoardState.sailorSlug) params.set('sailor_slug', approvedSaBoardState.sailorSlug);
                                            if (approvedSaBoardState.auditVersion) params.set('audit_version', approvedSaBoardState.auditVersion);
                                            var auditRes = await fetch('/api/rankings/audit-popup?' + params.toString(), { credentials: 'same-origin', cache: 'no-store' }).catch(function() { return null; });
                                            var auditPayload = (auditRes && auditRes.ok) ? await auditRes.json() : null;
                                            if (auditPayload && auditPayload.summary) {
                                                approvedSaBoardState.rankText = String(auditPayload.summary.rank != null && auditPayload.summary.rank !== '' ? auditPayload.summary.rank : 'NONE');
                                                approvedSaBoardState.totalPoints = (auditPayload.summary.total_points != null && auditPayload.summary.total_points !== '') ? Number(auditPayload.summary.total_points) : null;
                                                approvedSaBoardState.pointsDigits = extractApprovedPointsDigits(approvedSaBoardState.totalPoints);
                                                if (!approvedSaBoardState.sailorSlug && auditPayload.technical && auditPayload.technical.sailor_slug) approvedSaBoardState.sailorSlug = String(auditPayload.technical.sailor_slug).trim();
                                            }
                                        } catch (_) {}
                                    }
                                    return approvedSaBoardState;
                                }
                                var approvedRowsById = {};
                                function getApprovedSelectedCard() {
                                    return approvedClassCards.find(function(card) { return card.key === approvedState.selectedKey; }) || approvedClassCards[0];
                                }
                                function getApprovedFilteredHighlights() {
                                    var selectedNorm = approvedState.selectedKey === 'all' ? '' : normalizeApprovedClassKey(approvedState.selectedKey);
                                    return (highlightsData || []).filter(function(item, idx) {
                                        if (!item) return false;
                                        if (!selectedNorm) return true;
                                        return normalizeApprovedClassKey(item.className || '') === selectedNorm;
                                    }).map(function(item, idx) {
                                        var row = Object.assign({}, item);
                                        row.__rowId = 'h-' + idx + '-' + String(item.regatta_id || item.text || idx);
                                        approvedRowsById[row.__rowId] = row;
                                        return row;
                                    });
                                }
                                function getApprovedFilteredResults() {
                                    var selectedNorm = approvedState.selectedKey === 'all' ? '' : normalizeApprovedClassKey(approvedState.selectedKey);
                                    return (regattaHistoryRows || []).filter(function(item) {
                                        if (!item) return false;
                                        if (!selectedNorm) return true;
                                        return normalizeApprovedClassKey(item.className || '') === selectedNorm;
                                    }).map(function(item, idx) {
                                        var row = Object.assign({}, item);
                                        row.__rowId = 'r-' + idx + '-' + String(item.regatta_id || item.event_name || idx);
                                        approvedRowsById[row.__rowId] = row;
                                        return row;
                                    });
                                }
                                function renderApprovedProfile() {
                                    approvedRowsById = {};
                                    if (approvedState.mode !== 'full') approvedState.mode = 'expanded';
                                    var selectedCard = getApprovedSelectedCard();
                                    var saRankData = getApprovedSaRankData(approvedState.selectedKey);
                                    if (approvedSaBoardState.loaded) {
                                        saRankData = {
                                            rankText: approvedSaBoardState.rankText,
                                            pointsDigits: approvedSaBoardState.pointsDigits || [],
                                            totalPoints: approvedSaBoardState.totalPoints,
                                            popupEnabled: approvedSaBoardState.popupEnabled,
                                            sailorSlug: approvedSaBoardState.sailorSlug,
                                            auditVersion: approvedSaBoardState.auditVersion
                                        };
                                    }
                                    var sslRankData = getApprovedSslRankData();
                                    var sslProfileHref = getApprovedSslProfileHref();
                                    var clubHref = getApprovedClubHref();
                                    var provinceHref = getApprovedProvinceHref();
                                    var saRankHref = getApprovedRankingsHref(selectedCard);
                                    var saRankLogoUrl = (apiBase ? apiBase : '') + '/artwork/SSA-Ranking-Logo.png?v=20260805b';
                                    var sslLogoUrl = (apiBase ? apiBase : '') + '/artwork/SSL-logo.png?v=5';
                                    var sasLogoUrl = (apiBase ? apiBase : '') + '/artwork/SAS-Logo.png?v=20260805a';
                                    var sailingForLogoUrl = (apiBase ? apiBase : '') + '/artwork/Sailing-For.png?v=4';
                                    var sailingForShort = formatApprovedDurationShort(regattaHistoryRows || []);
                                    var provinceShort = provinceCodeDisplay || '—';
                                    var provinceWords = String(provinceDisplay || provinceShort || '—').trim().split(/\s+/).filter(Boolean);
                                    var provinceTextHtml = provinceWords.length > 1
                                        ? '<span class="sa-approved-sailor-meta-text-line">' + escapeHtml(provinceWords[0]) + '</span><span class="sa-approved-sailor-meta-text-line">' + escapeHtml(provinceWords.slice(1).join(' ')) + '</span>'
                                        : '<span class="sa-approved-sailor-meta-text-line">' + escapeHtml(provinceDisplay || provinceShort || '—') + '</span>';
                                    var sailingMatch = String(sailingForShort || '').match(/(\d+)\s*yrs?\s*(\d+)\s*mths?/i);
                                    var sailingTop = sailingMatch ? (String(sailingMatch[1]) + 'yrs') : String(sailingForShort || '—');
                                    var sailingBottom = sailingMatch ? (String(sailingMatch[2]) + 'mths') : '';
                                    var sailingTextHtml = '<span class="sa-approved-sailor-meta-text-line">' + escapeHtml(sailingTop || '—') + '</span>' + (sailingBottom ? '<span class="sa-approved-sailor-meta-text-line">' + escapeHtml(sailingBottom) + '</span>' : '');
                                    var resultsSource = approvedState.tab === 'highlights' ? getApprovedFilteredHighlights() : getApprovedFilteredResults();
                                    var visibleResults = resultsSource.slice(0, approvedState.visibleRows);
                                    var classCardsHtml = approvedClassCards.map(function(card) {
                                        var eventCount = (card && card.stats && card.stats.rg != null) ? card.stats.rg : 0;
                                        var classHref = getApprovedClassHref(card);
                                        return '' +
                                            '<button type="button" class="sa-approved-sailor-class-card' + (card.key === approvedState.selectedKey ? ' active' : '') + '" data-profile-class="' + escapeHtml(card.key) + '"' + (classHref ? ' data-profile-class-href="' + escapeHtml(classHref) + '"' : '') + '>' +
                                                '<span class="sa-approved-sailor-class-logo">' + buildApprovedClassIconHtml(card) + '</span>' +
                                                '<span class="sa-approved-sailor-class-name">' + escapeHtml(card.label) + ' <span class="sa-approved-sailor-class-count">(' + escapeHtml(String(eventCount)) + ')</span></span>' +
                                            '</button>';
                                    }).join('');
                                    var saRankTriggerAttrs = ' data-profile-sa-rank="1"';
                                    if (saRankData && saRankData.popupEnabled && sasIdText !== '—') {
                                        saRankTriggerAttrs += ' data-rk-audit-trigger="1" aria-expanded="false" aria-controls="rkAuditCalcPopup"';
                                    }
                                    var saRankOpen = saRankHref ? '<a class="sa-approved-sailor-rank-card sa-approved-sailor-rank-card-sa sa-approved-sailor-rank-card-link" href="' + escapeHtml(saRankHref) + '" title="Open SA rankings"' + saRankTriggerAttrs + '>' : '<div class="sa-approved-sailor-rank-card sa-approved-sailor-rank-card-sa"' + saRankTriggerAttrs + '>';
                                    var saRankClose = saRankHref ? '</a>' : '</div>';
                                    var sslRankOpen = sslProfileHref ? '<a class="sa-approved-sailor-rank-card sa-approved-sailor-rank-card-ssl sa-approved-sailor-rank-card-link" href="' + escapeHtml(sslProfileHref) + '" target="_blank" rel="noopener noreferrer" title="Open SSL profile">' : '<div class="sa-approved-sailor-rank-card sa-approved-sailor-rank-card-ssl">';
                                    var sslRankClose = sslProfileHref ? '</a>' : '</div>';
                                    var sasIdRaw = String(((memberSource && memberSource.sas_id) || sid || '')).trim();
                                    var sasIdText = (/^\d+$/.test(sasIdRaw)) ? sasIdRaw : '—';
                                    var saScoreText = (saRankData && saRankData.totalPoints != null && saRankData.totalPoints !== '' && !isNaN(Number(saRankData.totalPoints)))
                                        ? String(Math.round(Number(saRankData.totalPoints)))
                                        : ((saRankData.pointsDigits && saRankData.pointsDigits.length) ? saRankData.pointsDigits.join('') : '');
                                    var sslScoreText = (sslRankData.pointsDigits && sslRankData.pointsDigits.length) ? sslRankData.pointsDigits.join('') : '';
                                    var sslRankRawText = String((sslRankData && sslRankData.rankText != null) ? sslRankData.rankText : 'NONE');
                                    var sslRankIsNone = sslRankRawText === 'NONE' || sslRankRawText === '—' || sslRankRawText === '';
                                    var sslRankBigText = sslRankIsNone ? 'NONE' : sslRankRawText;
                                    var saRankRawText = String((saRankData && saRankData.rankText != null) ? saRankData.rankText : 'NONE');
                                    var saRankIsNone = saRankRawText === 'NONE' || saRankRawText === '—' || saRankRawText === '';
                                    var saRankBigText = saRankIsNone ? 'NONE' : saRankRawText;
                                    var saPointsDigitsHtml = (!saRankIsNone && saScoreText)
                                        ? ('<div class="sa-approved-ssa-points-digits">' + String(saScoreText).split('').map(function(d) { return '<span class="sa-approved-ssa-points-digit">' + escapeHtml(d) + '</span>'; }).join('') + '</div>')
                                        : '';
                                    var sslPointsDigitsHtml = (!sslRankIsNone && sslScoreText)
                                        ? ('<div class="sa-approved-ssl-points-digits">' + String(sslScoreText).split('').map(function(d) { return '<span class="sa-approved-ssl-points-digit">' + escapeHtml(d) + '</span>'; }).join('') + '</div>')
                                        : '';
                                    // PUBLIC_SAS_ID_PAUSE: omit entire visible SAS ID rank card
                                    var hidePublicSasIds = (typeof window.sailingsaHidePublicSasIds === 'function' ? window.sailingsaHidePublicSasIds() : (window.__SSA_HIDE_PUBLIC_SAS_IDS !== false));
                                    var sasIdRankCardHtml = hidePublicSasIds ? '' : (
                                                '<div class="sa-approved-sailor-rank-card sa-approved-sailor-rank-card-sas">' +
                                                    '<span class="sa-approved-sailor-rank-icon sas"><img src="' + escapeHtml(sasLogoUrl) + '" alt="SAS" loading="lazy"></span>' +
                                                    '<div class="sa-approved-sailor-rank-copy single">' +
                                                        '<div class="sa-approved-sailor-rank-main">' +
                                                            '<span class="label">SAS ID</span>' +
                                                            '<span class="value sas">' + escapeHtml(sasIdText) + '</span>' +
                                                        '</div>' +
                                                    '</div>' +
                                                '</div>'
                                    );
                                    var approvedNoArchiveResults = (regattaCount === 0 && raceCount === 0 && (!regattaHistoryRows || !regattaHistoryRows.length));
                                    var hideApprovedRankPanels = approvedNoArchiveResults && saRankIsNone && sslRankIsNone;
                                    var rankSectionHtml = hideApprovedRankPanels
                                        ? ('<div class="sa-approved-sailor-rank-row sa-approved-sailor-rank-row--empty">' +
                                            '<div class="sa-approved-sailor-results-empty">No regatta results in the SailingSA archive yet.</div>' +
                                          '</div>')
                                        : ('' +
                                        '<div class="sa-approved-sailor-rank-row">' +
                                            '<div class="sa-approved-sailor-rank-core">' +
                                                saRankOpen +
                                                    '<div class="sa-approved-ssa-frame">' +
                                                        '<div class="sa-approved-ssa-grid">' +
                                                            '<div class="sa-approved-ssa-topblock">' +
                                                                '<div class="sa-approved-ssa-logo"><img src="' + escapeHtml(saRankLogoUrl) + '" alt="SSA" loading="lazy"></div>' +
                                                                '<div class="sa-approved-ssa-title">SSA</div>' +
                                                            '</div>' +
                                                            '<div class="sa-approved-ssa-rail">' +
                                                                '<div class="sa-approved-ssa-col-label sa-approved-ssa-label-rank">RANK</div>' +
                                                                '<div class="sa-approved-ssa-col-label sa-approved-ssa-label-points">POINTS</div>' +
                                                                '<div class="sa-approved-ssa-value-rank"><div class="sa-approved-ssa-rank-number' + (saRankIsNone ? ' is-none' : '') + '">' + escapeHtml(saRankBigText) + '</div></div>' +
                                                                '<div class="sa-approved-ssa-divider" aria-hidden="true"></div>' +
                                                                '<div class="sa-approved-ssa-value-points">' + saPointsDigitsHtml + '</div>' +
                                                            '</div>' +
                                                        '</div>' +
                                                    '</div>' +
                                                saRankClose +
                                                sasIdRankCardHtml +
                                                sslRankOpen +
                                                    '<div class="sa-approved-ssl-frame">' +
                                                        '<div class="sa-approved-ssl-grid">' +
                                                            '<div class="sa-approved-ssl-topblock">' +
                                                                '<div class="sa-approved-ssl-logo"><img src="' + escapeHtml(sslLogoUrl) + '" alt="SSL" loading="lazy"></div>' +
                                                                '<div class="sa-approved-ssl-title">SSL</div>' +
                                                            '</div>' +
                                                            '<div class="sa-approved-ssl-rail">' +
                                                                '<div class="sa-approved-ssl-col-label sa-approved-ssl-label-rank">SSL RANK</div>' +
                                                                '<div class="sa-approved-ssl-col-label sa-approved-ssl-label-points">SSL POINTS</div>' +
                                                                '<div class="sa-approved-ssl-value-rank"><div class="sa-approved-ssl-rank-number' + (sslRankIsNone ? ' is-none' : '') + '">' + escapeHtml(sslRankBigText) + '</div></div>' +
                                                                '<div class="sa-approved-ssl-divider" aria-hidden="true"></div>' +
                                                                '<div class="sa-approved-ssl-value-points">' + sslPointsDigitsHtml + '</div>' +
                                                            '</div>' +
                                                        '</div>' +
                                                    '</div>' +
                                                sslRankClose +
                                            '</div>' +
                                            '<button type="button" class="sa-approved-sailor-mode-toggle" data-profile-mode-toggle="1" aria-label="' + (approvedState.mode === 'full' ? 'Hide highlights' : 'Show highlights') + '">' + buildApprovedChevron(approvedState.mode === 'full' ? 'up' : 'down') + '</button>' +
                                        '</div>');
                                    rankSectionHtml += '<div class="sa-approved-sailor-class-cards">' + classCardsHtml + '</div>';
                                    var fullSectionHtml = '';
                                    if (approvedState.mode === 'full') {
                                        var rowsHtml = visibleResults.length
                                            ? visibleResults.map(function(item) { return buildApprovedResultItem(item, approvedState.tab); }).join('')
                                            : '<div class="sa-approved-sailor-results-empty">No results in this view yet.</div>';
                                        var viewMoreHtml = resultsSource.length > approvedState.visibleRows
                                            ? '<div class="sa-approved-sailor-view-more-wrap"><button type="button" class="sa-approved-sailor-view-more" data-profile-view-more="1">View more ' + buildApprovedChevron('down') + '</button></div>'
                                            : '';
                                        var footerTopParts = [];
                                        if (totalRegattas > 0) footerTopParts.push('<span>' + escapeHtml(String(totalRegattas)) + ' regattas</span>');
                                        if (totalRaces > 0) footerTopParts.push('<span>' + escapeHtml(String(totalRaces)) + ' races</span>');
                                        if (sailingSinceYear) footerTopParts.push('<span>Sailing since ' + escapeHtml(String(sailingSinceYear)) + '</span>');
                                        var footerBottom = (goldCount > 0 || silverCount > 0 || bronzeCount > 0)
                                            ? '<div class="sa-approved-sailor-footer-bottom">' +
                                                '<span class="sa-approved-sailor-footer-medal">🥇 ' + escapeHtml(String(goldCount)) + '</span>' +
                                                '<span class="sa-approved-sailor-footer-medal">🥈 ' + escapeHtml(String(silverCount)) + '</span>' +
                                                '<span class="sa-approved-sailor-footer-medal">🥉 ' + escapeHtml(String(bronzeCount)) + '</span>' +
                                              '</div>'
                                            : '';
                                        var footerHtml = (footerTopParts.length || footerBottom)
                                            ? '<div class="sa-approved-sailor-footer">' + (footerTopParts.length ? '<div class="sa-approved-sailor-footer-top">' + footerTopParts.join('<span aria-hidden="true">•</span>') + '</div>' : '') + footerBottom + '</div>'
                                            : '';
                                        fullSectionHtml = '' +
                                            '<div class="sa-approved-sailor-full">' +
                                                '<div class="sa-approved-sailor-result-tabs" role="tablist">' +
                                                    '<button type="button" class="sa-approved-sailor-result-tab' + (approvedState.tab === 'highlights' ? ' active' : '') + '" data-profile-tab="highlights">Highlights</button>' +
                                                    '<button type="button" class="sa-approved-sailor-result-tab' + (approvedState.tab === 'results' ? ' active' : '') + '" data-profile-tab="results">All Results</button>' +
                                                '</div>' +
                                                '<div class="sa-approved-sailor-results">' + rowsHtml + '</div>' +
                                                viewMoreHtml +
                                                footerHtml +
                                            '</div>';
                                    }
                                    var expandedHtml = '<div class="sa-approved-sailor-expanded">' + rankSectionHtml + fullSectionHtml + '</div>';
                                    if (_abortLoggedInIfSearching()) return;
                                    sailorSearchResults.innerHTML = '' +
                                        '<div id="chosen-sailor-before-profile" class="profile-card sailor-stats-before-profile sa-approved-sailor-card" style="cursor:default;max-width:100%;">' +
                                            '<div class="sa-approved-sailor-header">' +
                                                '<div class="sa-approved-sailor-avatar">' +
                                                    '<img src="' + escapeHtml(avatarPath) + '" alt="' + escapeHtml(nameD || 'Sailor') + '" loading="lazy"' + avatarStyleAttr + ' onerror="this.style.display=\'none\'; var fallback = this.nextElementSibling; if(fallback) fallback.style.display=\'flex\';">' +
                                                    '<span class="avatar-fallback" style="display:none;">' + escapeHtml(initials) + '</span>' +
                                                '</div>' +
                                                '<div class="sa-approved-sailor-main">' +
                                                    '<h2 class="sa-approved-sailor-name"><span class="sa-approved-sailor-name-first">' + escapeHtml(firstName || nameD || 'Sailor') + '</span>' + (lastName ? '<span class="sa-approved-sailor-name-last">' + escapeHtml(lastName) + '</span>' : '') + '</h2>' +
                                                    '<div class="sa-approved-sailor-club">' + (clubHref ? '<a class="sa-approved-sailor-club-link" href="' + escapeHtml(clubHref) + '"' + (clubWeb && !clubSlug ? ' target="_blank" rel="noopener noreferrer"' : '') + ' title="' + escapeHtml(finalClubTitle) + '">' : '') + buildApprovedClubMiniIcon() + '<span class="sa-approved-sailor-club-code">' + escapeHtml(finalClubCode || '—') + '</span>' + (clubHref ? '</a>' : '') + '</div>' +
                                                '</div>' +
                                                '<div class="sa-approved-sailor-meta-block province">' +
                                                    (provinceHref ? '<a class="sa-approved-sailor-meta-link" href="' + escapeHtml(provinceHref) + '" target="_blank" rel="noopener noreferrer" title="' + escapeHtml(provinceDisplay || provinceShort || 'Province') + '">' : '') +
                                                    '<span class="sa-approved-sailor-province-box">' + escapeHtml(provinceShort) + '</span>' +
                                                    '<span class="sa-approved-sailor-meta-text">' + provinceTextHtml + '</span>' +
                                                    (provinceHref ? '</a>' : '') +
                                                '</div>' +
                                                '<div class="sa-approved-sailor-meta-block">' +
                                                    '<button type="button" class="sa-approved-sailor-meta-link" data-profile-sailing-for-toggle="1" title="Show highlights">' +
                                                        '<img class="sa-approved-sailor-sailing-for-icon" src="' + escapeHtml(sailingForLogoUrl) + '" alt="Sailing for" loading="lazy">' +
                                                        '<span class="sa-approved-sailor-meta-text">' + sailingTextHtml + '</span>' +
                                                    '</button>' +
                                                '</div>' +
                                            '</div>' +
                                            expandedHtml +
                                        '</div>';
                                    sailorSearchResults.style.display = 'block';
                                    var root = sailorSearchResults.querySelector('.sa-approved-sailor-card');
                                    if (!root) return;
                                    root.querySelectorAll('[data-profile-class]').forEach(function(btn) {
                                        btn.addEventListener('click', function(ev) {
                                            var href = btn.getAttribute('data-profile-class-href') || '';
                                            var logoTarget = ev && ev.target && ev.target.closest ? ev.target.closest('.sa-approved-sailor-class-logo') : null;
                                            if (logoTarget && href) {
                                                window.location.href = href;
                                                return;
                                            }
                                            approvedState.selectedKey = btn.getAttribute('data-profile-class') || 'all';
                                            approvedState.visibleRows = 8;
                                            renderApprovedProfile();
                                        });
                                    });
                                    root.querySelectorAll('[data-profile-class-href]').forEach(function(btn) {
                                        btn.addEventListener('auxclick', function(ev) {
                                            if (ev.button !== 1) return;
                                            var href = btn.getAttribute('data-profile-class-href') || '';
                                            if (href) window.open(href, '_blank', 'noopener');
                                        });
                                    });
                                    var modeToggle = root.querySelector('[data-profile-mode-toggle="1"]');
                                    if (modeToggle) {
                                        modeToggle.addEventListener('click', function() {
                                            approvedState.mode = approvedState.mode === 'full' ? 'expanded' : 'full';
                                            approvedState.visibleRows = 8;
                                            renderApprovedProfile();
                                        });
                                    }
                                    var sailingForToggle = root.querySelector('[data-profile-sailing-for-toggle="1"]');
                                    if (sailingForToggle) {
                                        sailingForToggle.addEventListener('click', function() {
                                            approvedState.mode = 'full';
                                            approvedState.tab = 'highlights';
                                            approvedState.visibleRows = 8;
                                            renderApprovedProfile();
                                        });
                                    }
                                    root.querySelectorAll('[data-profile-tab]').forEach(function(btn) {
                                        btn.addEventListener('click', function() {
                                            approvedState.tab = btn.getAttribute('data-profile-tab') === 'results' ? 'results' : 'highlights';
                                            approvedState.visibleRows = 8;
                                            renderApprovedProfile();
                                        });
                                    });
                                    var viewMoreBtn = root.querySelector('[data-profile-view-more="1"]');
                                    if (viewMoreBtn) {
                                        viewMoreBtn.addEventListener('click', function() {
                                            approvedState.visibleRows += 8;
                                            renderApprovedProfile();
                                        });
                                    }
                                    var saRankTrigger = root.querySelector('[data-profile-sa-rank="1"]');
                                    if (saRankTrigger && saRankData && saRankData.popupEnabled && sasIdText !== '—') {
                                        bindApprovedSaRankAuditPopup(saRankTrigger, {
                                            sasId: sasIdText,
                                            sailorSlug: saRankData.sailorSlug || '',
                                            auditVersion: saRankData.auditVersion || ''
                                        });
                                    }
                                    root.querySelectorAll('[data-profile-row-id]').forEach(function(rowEl) {
                                        rowEl.addEventListener('click', function() {
                                            var rowId = rowEl.getAttribute('data-profile-row-id') || '';
                                            openApprovedResult(approvedRowsById[rowId] || null);
                                        });
                                    });
                                }
                                await loadApprovedSaBoardRank();
                                renderApprovedProfile();
                            })();
                            return;
                            var tabBar = '<div class="sailor-profile-tabs" role="tablist">' +
                                '<button type="button" class="sailor-profile-tab active" role="tab" data-tab="profile" aria-selected="true">Sailor Profile</button>' +
                                '<button type="button" class="sailor-profile-tab" role="tab" data-tab="regattas" aria-selected="false">Regattas Sailed</button>' +
                                (isLoggedInUser ? '' : '<button type="button" class="sailor-profile-tab" role="tab" data-tab="media" aria-selected="false">Media</button>') +
                                (isLoggedInUser ? '' : '<button type="button" class="sailor-profile-tab" role="tab" data-tab="activity" aria-selected="false">Activity</button>') +
                                '</div>';
                            // Step 13: Profile tab only shows meta details, summary, AI overview, highlights, compact stats (no career/class breakdown, header moved above tabs)
                            // Step 14: Add medal summary after compact stats
                            // Header is now shared across all tabs - placed before tabBar
                            // Profile meta details (Age, Class, Province, Club, SAS ID, Last active) appear only in Profile tab, above Career Summary
                            var profileMetaSection = '';
                            try {
                                profileMetaSection = '<div class="sailor-meta" style="padding: 14px 16px; border-bottom: 1px solid #e5e7eb; background: #ffffff;">' +
                                    '<div class="meta-row">' +
                                    '<span class="meta-label">Age</span>' +
                                    '<span class="meta-value">' + escapeHtml((ageVal && !isNaN(ageVal) && ageVal > 0) ? (ageFromYearOnly ? (ageVal + '/' + (ageVal + 1) + ' Yrs') : (String(ageVal) + ' Yrs')) : '—') + '</span>' +
                                    '</div>' +
                                    '<div class="meta-row">' +
                                    '<span class="meta-label">Class</span>' +
                                    '<span class="meta-value">' + escapeHtml(classesDisplay) + '</span>' +
                                    '</div>' +
                                    '<div class="meta-row meta-row-combined">' +
                                    '<span class="meta-label">Province</span>' +
                                    '<span class="meta-value">' + escapeHtml(provinceDisplay) + '<span class="meta-club-separator"> </span><span class="meta-label meta-club-label">CLUB</span> <span class="meta-value meta-club-value">' + escapeHtml(clubD !== '—' ? clubD : '—') + '</span></span>' +
                                    '</div>' +
                                    ((typeof window.sailingsaHidePublicSasIds === 'function' ? window.sailingsaHidePublicSasIds() : (window.__SSA_HIDE_PUBLIC_SAS_IDS !== false)) ? '' : (
                                    '<div class="meta-row secondary">' +
                                    '<span class="meta-label">SAS ID</span>' +
                                    '<span class="meta-value">' + (noRealSasId ? 'No SAS ID' : (isLoggedInUser ? escapeHtml(sid || '—') : '—')) + '</span>' +
                                    '</div>'
                                    )) +
                                    '<div class="meta-row secondary">' +
                                    '<span class="meta-label">Last active</span>' +
                                    '<span class="meta-value">' + escapeHtml(lastActiveDate) + '</span>' +
                                    '</div>' +
                                    '</div>';
                            } catch (e) {
                                console.error('[DEBUG] Error building profile meta section:', e);
                            }
                            var panelProfile = '<div id="sailor-tab-panel-profile" class="sailor-profile-panel active" role="tabpanel">' + profileMetaSection + (summaryCardHtml ? summaryCardHtml : '') + (aiOverviewHtml ? aiOverviewHtml : '') + (highlightsHtml ? highlightsHtml : '') + (compactStatsHtml ? compactStatsHtml : '') + (medalSummaryHtml ? medalSummaryHtml : '') + '</div>';
                            var panelRegattas = '<div id="sailor-tab-panel-regattas" class="sailor-profile-panel" role="tabpanel">' + (regattaHistorySectionHtml || '<div class="sailor-career-regatta-history"><p class="sailor-career-subtitle">No regatta history.</p></div>') + '</div>';
                            // Media tab empty state (same for all sailors)
                            var mediaEmptyHtml = '';
                            if (!mentionsSectionHtml) {
                                var addMediaBtnEmptyPanel = isLoggedInUser ? '<button type="button" class="add-media-btn" id="add-media-btn" data-sa-id="' + escapeHtml(String(sid)) + '" data-name="' + escapeHtml(String(nameD || '')) + '" data-club="' + escapeHtml(String(clubD || '')) + '" style="margin-top:8px;padding:8px 14px;background:#001f3f;color:#fff;border:none;border-radius:6px;font-size:0.9rem;cursor:pointer;">Add Media</button>' : '';
                                mediaEmptyHtml = '<div class="sailor-public-mentions"><h2 class="sailor-media-page-header">Sailor &quot;' + escapeHtml((nameD || 'Sailor').trim()) + '&quot; in the Media</h2><h3 class="sailor-media-section-title">Media</h3><p class="sailor-mentions-subtitle">No public mentions yet.</p>' + (addMediaBtnEmptyPanel ? '<div class="sailor-media-header-actions">' + addMediaBtnEmptyPanel + '</div>' : '') + '</div>';
                            }
                            var panelMedia = isLoggedInUser ? '' : ('<div id="sailor-tab-panel-media" class="sailor-profile-panel" role="tabpanel">' + (mentionsSectionHtml || mediaEmptyHtml) + '</div>');
                            var panelActivity = isLoggedInUser ? '' : ('<div id="sailor-tab-panel-activity" class="sailor-profile-panel" role="tabpanel">' + (activitySectionHtml || '<div class="sailor-activity-timeline"><p class="sailor-activity-subtitle">No sailor activity yet.</p></div>') + '</div>');
                            // Header + bio above tabs (bio must stay visible — matches SSR placement)
                            if (_abortLoggedInIfSearching()) return;
                            sailorSearchResults.innerHTML = '<div id="chosen-sailor-before-profile" class="profile-card sailor-stats-before-profile" style="cursor:default;max-width:100%;margin-top:1rem;">' + backBtn + header + (sailorBioHtml || '') + tabBar + panelProfile + panelRegattas + panelMedia + panelActivity + '</div>';
                            sailorSearchResults.style.display = 'block';
                            if (!isLoggedInUser) {
                                // Back to results is now <a href="/"> so it always goes to homepage
                            }
                            function updateSailorTabFlashState() {
                                sailorSearchResults.querySelectorAll('.sailor-profile-tab').forEach(function(b) {
                                    b.classList.remove('btn-flash-active');
                                    if (b.classList.contains('active')) requestAnimationFrame(function() { b.classList.add('btn-flash-active'); });
                                });
                            }
                            sailorSearchResults.querySelectorAll('.sailor-profile-tab').forEach(function(btn) {
                                btn.addEventListener('click', function() {
                                    var tab = btn.getAttribute('data-tab');
                                    sailorSearchResults.querySelectorAll('.sailor-profile-tab').forEach(function(b) { b.classList.remove('active'); b.classList.remove('btn-flash-active'); b.setAttribute('aria-selected', 'false'); });
                                    sailorSearchResults.querySelectorAll('.sailor-profile-panel').forEach(function(p) { p.classList.remove('active'); });
                                    btn.classList.add('active'); btn.setAttribute('aria-selected', 'true');
                                    updateSailorTabFlashState();
                                    var panel = document.getElementById('sailor-tab-panel-' + tab);
                                    if (panel) panel.classList.add('active');
                                });
                            });
                            updateSailorTabFlashState();
                            var addMediaBtnEl = sailorSearchResults.querySelector('#add-media-btn');
                            if (addMediaBtnEl) {
                                addMediaBtnEl.addEventListener('click', function() {
                                    var saId = addMediaBtnEl.getAttribute('data-sa-id');
                                    if (!saId) return;
                                    window._mediaFormSaId = saId;
                                    document.getElementById('media-form-mode').value = 'add';
                                    document.getElementById('media-form-title').textContent = 'Add Media';
                                    document.getElementById('media-form-url').value = '';
                                    document.getElementById('media-form-url').readOnly = false;
                                    document.getElementById('media-form-headline').value = '';
                                    document.getElementById('media-form-snippet').value = '';
                                    document.getElementById('media-form-thumb').value = '';
                                    document.getElementById('media-form-date').value = '';
                                    document.getElementById('media-form-delete').style.display = 'none';
                                    document.getElementById('media-form-delete-reason').style.display = 'none';
                                    document.getElementById('media-form-overlay').style.display = 'block';
                                    document.getElementById('media-form-overlay').setAttribute('aria-hidden', 'false');
                                });
                            }
                            (function() {
                                var overlay = document.getElementById('media-form-overlay');
                                if (!overlay) return;
                                var saIdForMedia = function() { return window._mediaFormSaId || ''; };
                                document.getElementById('media-form-cancel').addEventListener('click', function() {
                                    overlay.style.display = 'none';
                                    overlay.setAttribute('aria-hidden', 'true');
                                });
                                overlay.addEventListener('click', function(e) {
                                    if (e.target === overlay) { overlay.style.display = 'none'; overlay.setAttribute('aria-hidden', 'true'); }
                                });
                                document.getElementById('media-form').addEventListener('submit', function(e) {
                                    e.preventDefault();
                                    var saId = saIdForMedia();
                                    if (!saId) return;
                                    var mode = document.getElementById('media-form-mode').value;
                                    var url = document.getElementById('media-form-url').value.trim();
                                    if (!url || url.indexOf('http') !== 0) { alert('Please enter a valid URL.'); return; }
                                    var headline = document.getElementById('media-form-headline').value.trim();
                                    var snippet = document.getElementById('media-form-snippet').value.trim();
                                    var thumb = document.getElementById('media-form-thumb').value.trim();
                                    var dateVal = document.getElementById('media-form-date').value.trim();
                                    var API = window.API_BASE || '';
                                    if (mode === 'add') {
                                        document.getElementById('media-form-save').disabled = true;
                                        fetch(API + '/api/member/' + encodeURIComponent(saId) + '/add-media', {
                                            method: 'POST',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({ url: url, headline: headline || undefined, snippet: snippet || undefined, thumb_url: thumb || undefined, published_at: dateVal || undefined }),
                                            credentials: 'include'
                                        }).then(function(r) { return r.json().then(function(d) { return { ok: r.ok, data: d }; }); }).then(function(result) {
                                            document.getElementById('media-form-save').disabled = false;
                                            if (result.ok && result.data.success) {
                                                overlay.style.display = 'none';
                                                overlay.setAttribute('aria-hidden', 'true');
                                                if (typeof window.showSailorStatsInResults === 'function') {
                                                    var btn = document.querySelector('#add-media-btn');
                                                    var nameD = (btn && btn.getAttribute('data-name')) ? btn.getAttribute('data-name').trim() : 'Sailor';
                                                    var clubD = (btn && btn.getAttribute('data-club')) ? btn.getAttribute('data-club').trim() : '—';
                                                    window.showSailorStatsInResults(saId, nameD, clubD, [], { isLoggedInUser: true });
                                                }
                                            } else {
                                                alert(result.data.detail || result.data.message || 'Could not add.');
                                            }
                                        }).catch(function() {
                                            document.getElementById('media-form-save').disabled = false;
                                            alert('Request failed.');
                                        });
                                    } else {
                                        document.getElementById('media-form-save').disabled = true;
                                        var payload = { url: url, headline: headline || undefined, snippet: snippet || undefined, published_at: dateVal || undefined };
                                        if (thumb && String(thumb).trim()) payload.thumb_url = String(thumb).trim();
                                        var mediaIdEl = document.getElementById('media-form-id');
                                        var rawId = mediaIdEl ? (mediaIdEl.value || '').trim() : '';
                                        if (rawId) { var n = parseInt(rawId, 10); if (!isNaN(n) && n > 0) payload.id = n; }
                                        fetch(API + '/api/member/' + encodeURIComponent(saId) + '/media', {
                                            method: 'PATCH',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify(payload),
                                            credentials: 'include'
                                        }).then(function(r) {
                                            return r.text().then(function(t) {
                                                var d = null;
                                                try { d = t ? JSON.parse(t) : {}; } catch (_) { d = { detail: r.status + ': ' + (t ? t.substring(0, 80) : 'Non-JSON response') }; }
                                                return { ok: r.ok, data: d, status: r.status };
                                            });
                                        }).then(function(result) {
                                            document.getElementById('media-form-save').disabled = false;
                                            if (result.ok && result.data.success) {
                                                overlay.style.display = 'none';
                                                overlay.setAttribute('aria-hidden', 'true');
                                                if (typeof window.showSailorStatsInResults === 'function') {
                                                    var btn = document.querySelector('#add-media-btn');
                                                    var nameD = (btn && btn.getAttribute('data-name')) ? btn.getAttribute('data-name').trim() : 'Sailor';
                                                    var clubD = (btn && btn.getAttribute('data-club')) ? btn.getAttribute('data-club').trim() : '—';
                                                    window.showSailorStatsInResults(saId, nameD, clubD, [], { isLoggedInUser: true });
                                                }
                                            } else {
                                                var errMsg = result.data.detail || result.data.message || ('Could not update (' + (result.status || '') + ').');
                                                console.error('Edit media error:', result.status, result.data);
                                                alert(errMsg);
                                            }
                                        }).catch(function(err) {
                                            document.getElementById('media-form-save').disabled = false;
                                            console.error('Edit media PATCH failed:', err);
                                            var msg = 'Request failed. ';
                                            if (err && err.message) msg += err.message + '. ';
                                            msg += 'Check Network tab (F12) and that the API is running at ' + (API || 'same origin') + '.';
                                            alert(msg);
                                        });
                                    }
                                });
                                document.getElementById('media-form-delete').addEventListener('click', function() {
                                    var sourceAdded = (this.getAttribute('data-source-added') || 'system').toLowerCase();
                                    var url = document.getElementById('media-form-url').value.trim();
                                    if (sourceAdded !== 'sailor') {
                                        document.getElementById('media-form-delete-reason').style.display = 'block';
                                        return;
                                    }
                                    if (!confirm('Delete this media item? This cannot be undone.')) return;
                                    if (!confirm('Really delete? This cannot be undone.')) return;
                                    var saId = saIdForMedia();
                                    if (!saId) return;
                                    var API = window.API_BASE || '';
                                    fetch(API + '/api/member/' + encodeURIComponent(saId) + '/media', {
                                        method: 'DELETE',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ url: url, confirm: true }),
                                        credentials: 'include'
                                    }).then(function(r) { return r.json().then(function(d) { return { ok: r.ok, data: d }; }); }).then(function(result) {
                                        if (result.ok && result.data.success) {
                                            overlay.style.display = 'none';
                                            overlay.setAttribute('aria-hidden', 'true');
                                            document.getElementById('media-form-delete-reason').style.display = 'none';
                                            if (typeof window.showSailorStatsInResults === 'function') {
                                                var btn = document.querySelector('#add-media-btn');
                                                var nameD = (btn && btn.getAttribute('data-name')) ? btn.getAttribute('data-name').trim() : 'Sailor';
                                                var clubD = (btn && btn.getAttribute('data-club')) ? btn.getAttribute('data-club').trim() : '—';
                                                window.showSailorStatsInResults(saId, nameD, clubD, [], { isLoggedInUser: true });
                                            }
                                        } else {
                                            alert(result.data.detail || result.data.message || 'Could not delete.');
                                        }
                                    }).catch(function() { alert('Request failed.'); });
                                });
                                document.getElementById('media-form-submit-delete-request').addEventListener('click', function() {
                                    var reason = (document.getElementById('media-form-delete-reason-text').value || '').trim();
                                    if (!reason) { alert('Please give a reason for the delete request.'); return; }
                                    var url = document.getElementById('media-form-url').value.trim();
                                    var saId = saIdForMedia();
                                    if (!saId) return;
                                    var API = window.API_BASE || '';
                                    var submitBtn = this;
                                    submitBtn.disabled = true;
                                    fetch(API + '/api/member/' + encodeURIComponent(saId) + '/media', {
                                        method: 'DELETE',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ url: url, reason: reason }),
                                        credentials: 'include'
                                    }).then(function(r) { return r.json().then(function(d) { return { ok: r.ok, data: d }; }); }).then(function(result) {
                                        submitBtn.disabled = false;
                                        if (result.ok && result.data.request_submitted) {
                                            alert('Delete request submitted. An admin will review.');
                                            overlay.style.display = 'none';
                                            overlay.setAttribute('aria-hidden', 'true');
                                            document.getElementById('media-form-delete-reason').style.display = 'none';
                                            document.getElementById('media-form-delete-reason-text').value = '';
                                        } else {
                                            alert(result.data.detail || result.data.message || 'Request failed.');
                                        }
                                    }).catch(function() { submitBtn.disabled = false; alert('Request failed.'); });
                                });
                                document.body.addEventListener('click', function(e) {
                                    if (!e.target || !e.target.classList || !e.target.classList.contains('media-edit-btn')) return;
                                    e.preventDefault();
                                    e.stopPropagation();
                                    var btn = e.target;
                                    var saId = document.querySelector('#add-media-btn');
                                    saId = saId ? saId.getAttribute('data-sa-id') : '';
                                    if (!saId) return;
                                    window._mediaFormSaId = saId;
                                    document.getElementById('media-form-mode').value = 'edit';
                                    document.getElementById('media-form-title').textContent = 'Edit Media';
                                    document.getElementById('media-form-url').value = btn.getAttribute('data-url') || '';
                                    document.getElementById('media-form-url').readOnly = true;
                                    document.getElementById('media-form-headline').value = btn.getAttribute('data-headline') || '';
                                    document.getElementById('media-form-snippet').value = (btn.getAttribute('data-snippet') || '').replace(/&quot;/g, '"');
                                    document.getElementById('media-form-thumb').value = (btn.getAttribute('data-thumb-url') || '').replace(/&quot;/g, '"');
                                    document.getElementById('media-form-date').value = btn.getAttribute('data-date-iso') || '';
                                    document.getElementById('media-form-delete').style.display = 'inline-block';
                                    document.getElementById('media-form-delete').setAttribute('data-source-added', btn.getAttribute('data-source-added') || 'system');
                                    document.getElementById('media-form-delete-reason').style.display = 'none';
                                    document.getElementById('media-form-delete-reason-text').value = '';
                                    overlay.style.display = 'block';
                                    overlay.setAttribute('aria-hidden', 'false');
                                });
                            })();
                        } catch (err) {
                            sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;color:#c00;">Failed to load sailor details. Try again.</div>';
                            sailorSearchResults.style.display = 'block';
                        }
                    };
                function runSailorSearch() {
                    try {
                        var _clsPathRs = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                        if (typeof sailingsaIsClassRoutePath === 'function' && sailingsaIsClassRoutePath(_clsPathRs)) return;
                    } catch (_) {}
                    // Auto-close regatta results modal when showing sailor content (mirrors sailor results hiding when doing regatta search)
                    if (typeof window.closeRegattaResultSheetModal === 'function') window.closeRegattaResultSheetModal();
                    const q = (sailorSearchInput.value || '').trim();
                    if (q.length >= 2) sailorSearchLastQuery = q;
                    if (q.length === 0) {
                        // Never run empty-search session profile fallback on a PUBLIC /sailor/<slug> URL.
                        try {
                            var _sq = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_sq) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        } catch (_) {}
                        if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(false);
                        if (sailorSearchAbort) sailorSearchAbort.abort();
                        sailorSearchAbort = new AbortController();
                        (async function() {
                            try {
                                var _sailorPathEmpty = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                                if (typeof sailingsaIsSailorProfilePath === 'function' && sailingsaIsSailorProfilePath(_sailorPathEmpty)) return;
                                var session = typeof window.__sailingsaGetSharedSession === 'function'
                                    ? await window.__sailingsaGetSharedSession()
                                    : (typeof checkSession === 'function' ? await checkSession() : { valid: false });
                                var sasId = session.valid && (session.sas_id || (session.user && session.user.sas_id)) ? (session.sas_id || session.user.sas_id) : null;
                                if (sasId && typeof window.showSailorStatsInResults === 'function') {
                                    var user = session.user || {};
                                    var displayName = [user.first_name || user.first_names, user.last_name || user.surname].filter(Boolean).join(' ') || '';
                                    var club = user.primary_club || user.club || '';
                                    // Ensure profile is shown - don't hide it
                                    sailorSearchResults.style.display = 'block';
                                    await window.showSailorStatsInResults(sasId, displayName, club, [], { isLoggedInUser: true, session: session });
                                    return;
                                }
                            } catch (_) {}
                            // Only show placeholder if not logged in
                            showSailorProfilePlaceholder();
                        })();
                        return;
                    }
                    if (q.length < 2) {
                        try {
                            var _sq5 = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_sq5) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        } catch (_) {}
                        if (sailorSearchAbort) sailorSearchAbort.abort();
                        sailorSearchAbort = new AbortController();
                        sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">Type at least 2 characters to search.</div>';
                        sailorSearchResults.style.display = 'block';
                        return;
                    }
                    if (sailorSearchAbort) sailorSearchAbort.abort();
                    sailorSearchAbort = new AbortController();
                    try {
                        var _ss = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                        if (/^\/sailor\//i.test(_ss) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                    } catch (_) {}
                    const API = window.API_BASE || '';
                    if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(true);
                    window.__sailorSearchGen = (window.__sailorSearchGen || 0) + 1;
                    var _searchGen = window.__sailorSearchGen;
                    sailorSearchResults.style.display = 'block';
                    sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">Searching…</div>';
                    // Full fuzzy list via q= (includes nicknames). Do NOT early-stop on first_names/surname —
                    // that missed Rick→Richard Nankin for "Rick n".
                    const parts = q.split(/\s+/).filter(Boolean);
                    var limitParam = '&hub=1&limit=500';

                    function fetchSearch(u) {
                        return fetch(u, { signal: sailorSearchAbort.signal })
                            .then(function(res) { return res.ok ? res.json() : Promise.resolve([]); })
                            .then(function(data) { return Array.isArray(data) ? data : []; });
                    }
                    function sortSailorList(list) {
                        var qn = String(q || '').toLowerCase().replace(/\s+/g, ' ').trim();
                        var tokens = qn.split(' ').filter(Boolean);
                        function score(row) {
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
                        return (list || []).slice().sort(function(a, b) {
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
                    function renderSailorList(list) {
                        if (_searchGen !== (window.__sailorSearchGen || 0)) return Promise.resolve();
                        try {
                            var _rsl = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_rsl) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
                        } catch (_) {}
                        if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(true);
                        list = sortSailorList(list);
                        sailorSearchResults.innerHTML = '';
                        sailorSearchResults.style.display = 'block';
                        if (list.length === 0) {
                            sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">No sailors found.</div>';
                            return Promise.resolve();
                        }
                        var guestLocked = true;
                        try {
                            var _lis = document.getElementById('loggedInStatus');
                            guestLocked = !(_lis && _lis.style.display !== 'none');
                        } catch (_) { guestLocked = true; }
                        sailorSearchResults.classList.toggle('guest-locked', !!guestLocked);
                        function scopedDev1Doc(root) {
                            return {
                                getElementById: function(id) {
                                    try { return root.querySelector('[id="' + String(id).replace(/"/g, "") + '"]'); }
                                    catch (e) { return null; }
                                },
                                querySelector: function(sel) { return root.querySelector(sel); },
                                querySelectorAll: function(sel) { return root.querySelectorAll(sel); },
                                createElement: function(t) { return window.document.createElement(t); },
                                createTextNode: function(t) { return window.document.createTextNode(t); },
                                addEventListener: function(t, fn, opt) { return window.document.addEventListener(t, fn, opt); },
                                removeEventListener: function(t, fn, opt) { return window.document.removeEventListener(t, fn, opt); },
                                get body() { return window.document.body; },
                                get documentElement() { return window.document.documentElement; },
                                get head() { return window.document.head; }
                            };
                        }
                        function runDev1Scripts(root, codes) {
                            var scoped = scopedDev1Doc(root);
                            codes.forEach(function(code) {
                                if (!code || !String(code).trim()) return;
                                try { (new Function("document", "window", code))(scoped, window); }
                                catch (e) { try { console.warn("dev1 card script", e); } catch (_) {} }
                            });
                        }
                        function sailorFromSlot(slot) {
                            var sid = String((slot && slot.dataset && slot.dataset.sasId) || "").trim();
                            var firstEl = slot ? slot.querySelector(".sa-approved-sailor-name-first") : null;
                            var lastEl = slot ? slot.querySelector(".sa-approved-sailor-name-last") : null;
                            var name = [firstEl && firstEl.textContent, lastEl && lastEl.textContent].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
                            if (!name) {
                                var img = slot ? slot.querySelector(".sa-approved-sailor-avatar img[alt]") : null;
                                name = img && img.getAttribute("alt") ? String(img.getAttribute("alt")).trim() : "";
                            }
                            return { sid: sid, name: name };
                        }
                        function claimSignupHref(sid, name) {
                            var u = "/signup.html?signup=1";
                            if (sid) u += "&sas_id=" + encodeURIComponent(sid);
                            if (name) u += "&name=" + encodeURIComponent(name);
                            try {
                                var ret = window.location.href || "/";
                                u += "&returnTo=" + encodeURIComponent(ret);
                            } catch (_) {}
                            return u;
                        }
                        function rememberClaimSailor(sid, name) {
                            window.__ssaClaimSailor = { sid: sid || "", name: name || "" };
                        }
                        function wireClaimBanners(slot) {
                            var info = sailorFromSlot(slot);
                            var href = claimSignupHref(info.sid, info.name);
                            slot.querySelectorAll("a.sa-claim-banner").forEach(function(a) {
                                a.setAttribute("href", href);
                                a.addEventListener("click", function() {
                                    rememberClaimSailor(info.sid, info.name);
                                });
                            });
                        }
                        function mountDev1Card(slot, html) {
                            var box = document.createElement("div");
                            box.innerHTML = html;
                            var lock = box.querySelector("#dev1-viewport-locks");
                            if (lock) {
                                if (!document.getElementById("dev1-viewport-locks")) {
                                    document.head.appendChild(lock);
                                } else if (lock.parentNode) {
                                    lock.parentNode.removeChild(lock);
                                }
                            }
                            var codes = [];
                            box.querySelectorAll("script").forEach(function(sc) {
                                if (!sc.src) codes.push(sc.textContent || "");
                                if (sc.parentNode) sc.parentNode.removeChild(sc);
                            });
                            slot.innerHTML = "";
                            while (box.firstChild) slot.appendChild(box.firstChild);
                            runDev1Scripts(slot, codes);
                            wireClaimBanners(slot);
                            if (guestLocked) {
                                slot.addEventListener("click", function(ev) {
                                    var btn = ev.target && ev.target.closest ? ev.target.closest(".sa-avatar-expand-btn") : null;
                                    if (!btn || !slot.contains(btn)) return;
                                    ev.preventDefault();
                                    ev.stopPropagation();
                                    if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
                                    var panel = slot.querySelector(".dev1-rank-expand-panel");
                                    if (panel) panel.style.display = "none";
                                    btn.setAttribute("aria-expanded", "false");
                                    var svg = btn.querySelector("svg");
                                    if (svg) svg.style.transform = "rotate(0deg)";
                                    var info = sailorFromSlot(slot);
                                    rememberClaimSailor(info.sid, info.name);
                                    if (typeof window.showLoginRequiredPopup === "function") window.showLoginRequiredPopup();
                                }, true);
                            }
                        }
                        var gen = window.__sailorSearchGen || 0;
                        var slots = [];
                        list.forEach(function(row) {
                            var sid = row.sa_sailing_id != null ? String(row.sa_sailing_id) : String(row.sas_id || row.sa_id || '');
                            var wrap = document.createElement('div');
                            wrap.className = 'ssa-dev1-inject';
                            wrap.setAttribute('role', 'listitem');
                            wrap.dataset.sasId = sid;
                            wrap.innerHTML = '<div class="profile-card" style="cursor:default;">Loading…</div>';
                            sailorSearchResults.appendChild(wrap);
                            slots.push({ wrap: wrap, sid: sid, row: row });
                        });

                        function mountSimpleSailorCard(item) {
                            var row = item.row || {};
                            var sid = String(item.sid || '').trim();
                            var name = [row.first_names || row.first_name, row.surname || row.last_name].filter(Boolean).join(' ') || row.full_name || 'Sailor';
                            var club = row.club || row.primary_club || row.club_1 || '—';
                            var classesSailed = row.class_name || row.primary_class || '—';
                            function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
                            var card = document.createElement('div');
                            card.className = 'profile-card';
                            card.setAttribute('role', 'listitem');
                            card.dataset.sasId = sid;
                            card.innerHTML = '<div class="profile-card-header">Profile</div><div class="profile-card-body">' +
                                '<span class="profile-card-label">Name</span><span class="profile-card-value">' + esc(name) + '</span>' +
                                '<span class="profile-card-label">Club</span><span class="profile-card-value">' + esc(club) + '</span>' +
                                '<span class="profile-card-label">Classes Sailed</span><span class="profile-card-value">' + esc(classesSailed) + '</span></div>';
                            card.style.cursor = 'pointer';
                            card.addEventListener('click', function(ev) {
                                ev.preventDefault();
                                if (!sid) return;
                                if (typeof window.showSailorStatsInResults === 'function') {
                                    window.showSailorStatsInResults(sid, name, club, classesSailed);
                                }
                            });
                            item.wrap.innerHTML = '';
                            item.wrap.appendChild(card);
                        }
                        function _ssaUseDev1SailorCards() {
                            return true;
                        }
                        function fetchOne(item) {
                            if (!item || item.wrap.getAttribute('data-card-loaded') === '1') return Promise.resolve();
                            item.wrap.setAttribute('data-card-loaded', '1');
                            if (!item.sid) {
                                item.wrap.innerHTML = '<div class="profile-card" style="cursor:default;">No SAS ID.</div>';
                                return Promise.resolve();
                            }
                            window.__ssaDev1CardCache = window.__ssaDev1CardCache || {};
                            var cached = window.__ssaDev1CardCache[item.sid];
                            if (cached) {
                                mountDev1Card(item.wrap, cached);
                                return Promise.resolve();
                            }
                            if (!_ssaUseDev1SailorCards()) {
                                mountSimpleSailorCard(item);
                                return Promise.resolve();
                            }
                            return fetch('/dev-1?embed=1&sas_id=' + encodeURIComponent(item.sid), { credentials: 'same-origin' })
                                .then(function(r) {
                                    if (!r.ok) throw new Error('dev1 ' + r.status);
                                    return r.text();
                                })
                                .then(function(html) {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    var t = (html || '').trim();
                                    if (!t || t.charAt(0) === '{' ) throw new Error('dev1 bad body');
                                    window.__ssaDev1CardCache[item.sid] = html;
                                    mountDev1Card(item.wrap, html);
                                })
                                .catch(function() {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    mountSimpleSailorCard(item);
                                });
                        }
                        function loadRange(start, end, conc) {
                            var i = start;
                            var stop = Math.min(end, slots.length);
                            function worker() {
                                if (gen !== (window.__sailorSearchGen || 0)) return Promise.resolve();
                                if (i >= stop) return Promise.resolve();
                                var item = slots[i++];
                                return fetchOne(item).then(worker);
                            }
                            var pool = [];
                            var n = Math.min(conc, Math.max(0, stop - start));
                            for (var k = 0; k < n; k++) pool.push(worker());
                            return Promise.all(pool);
                        }
                        if (window.__ssaSailorCardIO) {
                            try { window.__ssaSailorCardIO.disconnect(); } catch (_) {}
                            window.__ssaSailorCardIO = null;
                        }
                        var topN = Math.min(3, slots.length);
                        var topLoad = loadRange(0, topN, 3);
                        if (slots.length > topN && typeof IntersectionObserver === 'function') {
                            var io = new IntersectionObserver(function(entries) {
                                if (gen !== (window.__sailorSearchGen || 0)) return;
                                entries.forEach(function(en) {
                                    if (!en.isIntersecting) return;
                                    io.unobserve(en.target);
                                    var item = null;
                                    for (var s = topN; s < slots.length; s++) {
                                        if (slots[s].wrap === en.target) { item = slots[s]; break; }
                                    }
                                    if (item) fetchOne(item);
                                });
                            }, { root: null, rootMargin: '600px 0px', threshold: 0.01 });
                            window.__ssaSailorCardIO = io;
                            for (var s = topN; s < slots.length; s++) io.observe(slots[s].wrap);
                        } else if (slots.length > topN) {
                            loadRange(topN, slots.length, 2);
                        }
                        return topLoad;
                    }

                    var url = API + '/api/search?q=' + encodeURIComponent(q) + limitParam;
                    fetchSearch(url)
                        .then(function(list) { return renderSailorList(list); })
                        .catch(function(err) {
                            if (err && err.name === 'AbortError') return;
                            if (_searchGen !== (window.__sailorSearchGen || 0)) return;
                            sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;color:#c00;">Search failed. Try again.</div>';
                            sailorSearchResults.style.display = 'block';
                        });
                }
                sailorSearchInput.addEventListener('input', function() {
                    const q = (sailorSearchInput.value || '').trim();
                    var regattaInput = document.getElementById('temp-landing-regatta-input');
                    var hasRegattaField = !!(regattaInput && regattaInput.offsetParent !== null);
                    if (hasRegattaField && searchMode !== 'sailor') setSearchModeSoft('sailor');
                    if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(q !== '');
                    if (q !== '') {
                        window.__sailorSearchGen = (window.__sailorSearchGen || 0) + 1;
                        if (q.length >= 2 && regattaInput && (regattaInput.value || '').trim()) {
                            regattaInput.value = '';
                        }
                        // Hard-hide logged-in profile immediately so the full search list owns the space.
                        try {
                            var _hp = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (!(/^\/sailor\//i.test(_hp) || /[?&]sas[_-]?id=/i.test(window.location.search || ''))) {
                                sailorSearchResults.style.display = 'block';
                                if (q.length >= 2) sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">Searching…</div>';
                                else sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">Type at least 2 characters to search.</div>';
                            }
                        } catch (_) {}
                    }
                    if (searchMode === 'sailor') {
                        clearTimeout(sailorSearchDebounce);
                        // If search field empty, show logged-in profile immediately (or placeholder if not logged in)
                        if (q === '') {
                            runSailorSearch();
                        } else {
                            sailorSearchDebounce = setTimeout(runSailorSearch, 280);
                        }
                    } else {
                        // Regatta mode: never show sailor profile. Empty = show regatta list/hint; typed = filter regattas.
                        clearTimeout(regattaFromTopDebounce);
                        try {
                            var _r1 = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_r1) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {} else {
                                sailorSearchResults.style.display = 'none';
                                sailorSearchResults.innerHTML = '';
                            }
                        } catch (_) {
                            sailorSearchResults.style.display = 'none';
                            sailorSearchResults.innerHTML = '';
                        }
                        regattaFromTopDebounce = setTimeout(function() {
                            if (typeof applyRegattaFilter === 'function') applyRegattaFilter();
                        }, q === '' ? 0 : 280);
                    }
                });
                sailorSearchInput.addEventListener('focus', function() {
                    const q = (sailorSearchInput.value || '').trim();
                    var regattaInput = document.getElementById('temp-landing-regatta-input');
                    var hasRegattaField = !!(regattaInput && regattaInput.offsetParent !== null);
                    if (hasRegattaField && searchMode !== 'sailor') setSearchModeSoft('sailor');
                    setSearchInteractionActive(q !== '');
                    if (searchMode === 'sailor' && q.length >= 2) {
                        /* keep existing results; do not refetch on mere focus */
                    } else if (searchMode === 'regatta' && (regattaInput && (regattaInput.value || '').trim().length >= 2)) {
                        if (typeof applyRegattaFilter === 'function') applyRegattaFilter();
                    }
                });
                sailorSearchForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    if (searchMode === 'sailor') {
                        clearTimeout(sailorSearchDebounce);
                        runSailorSearch();
                    } else {
                        clearTimeout(regattaFromTopDebounce);
                        if (typeof applyRegattaFilter === 'function') applyRegattaFilter();
                    }
                });
                function _bindRegattaInputCrossClear() {
                    var regattaInput = document.getElementById('temp-landing-regatta-input');
                    if (!regattaInput || regattaInput.__saCrossClearBound) return !!regattaInput;
                    regattaInput.__saCrossClearBound = true;
                    function clearSailorInput() {
                        if (!sailorSearchInput) return;
                        if ((regattaInput.value || '').trim().length < 2) return;
                        sailorSearchInput.value = '';
                    }
                    function ensureRegattaMode() {
                        if (searchMode === 'regatta') return;
                        if (typeof setSearchModeSoft === 'function') setSearchModeSoft('regatta');
                        else {
                            searchMode = 'regatta';
                            window.searchMode = 'regatta';
                        }
                    }
                    function scheduleRegattaFilter() {
                        clearTimeout(regattaFromTopDebounce);
                        regattaFromTopDebounce = setTimeout(function() {
                            if (typeof applyRegattaFilter === 'function') applyRegattaFilter();
                        }, (regattaInput.value || '').trim() === '' ? 0 : 280);
                    }
                    regattaInput.addEventListener('input', function(ev) {
                        setSearchInteractionActive(true);
                        ensureRegattaMode();
                        clearSailorInput();
                        scheduleRegattaFilter();
                    });
                    regattaInput.addEventListener('focus', function(ev) {
                        setSearchInteractionActive(true);
                        ensureRegattaMode();
                    });
                    return true;
                }
                _bindRegattaInputCrossClear();
                (function() {
                    var tries = 0;
                    var iv = setInterval(function() {
                        tries += 1;
                        if (_bindRegattaInputCrossClear() || tries > 50) clearInterval(iv);
                    }, 100);
                })();
                // Toggle Sailor / Regatta — Sailor is selected by default
                var sailorBtn = document.querySelector('.search-mode-btn[data-mode="sailor"]');
                var regattaBtn = document.querySelector('.search-mode-btn[data-mode="regatta"]');
                
                function updateSearchModeFlashState() {
                    [sailorBtn, regattaBtn].forEach(function(b) { if (b) b.classList.remove('btn-flash-active'); });
                    var active = (searchMode === 'sailor' ? sailorBtn : regattaBtn);
                    if (active) requestAnimationFrame(function() { active.classList.add('btn-flash-active'); });
                }
                function setSearchModeSoft(mode) {
                    if (!mode || mode === searchMode) return;
                    searchMode = mode;
                    window.searchMode = mode;
                    var regattaInputSoft = document.getElementById('temp-landing-regatta-input');
                    if (mode === 'sailor') {
                        var publicRegattasList = document.getElementById('public-regattas-list');
                        if (publicRegattasList) publicRegattasList.innerHTML = '';
                        sailorSearchResults.style.display = 'block';
                        try { if (regattaInputSoft) regattaInputSoft.value = ''; } catch (_) {}
                        try { if (sailorSearchInput) sailorSearchInput.focus(); } catch (_) {}
                    } else if (mode === 'regatta') {
                        try {
                            var _sm1 = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_sm1) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {} else {
                                sailorSearchResults.style.display = 'none';
                                sailorSearchResults.innerHTML = '';
                            }
                        } catch (_) {
                            sailorSearchResults.style.display = 'none';
                            sailorSearchResults.innerHTML = '';
                        }
                        try { if (sailorSearchInput) sailorSearchInput.value = ''; } catch (_) {}
                        try { if (regattaInputSoft) regattaInputSoft.focus(); } catch (_) {}
                    }
                    if (sailorBtn) {
                        if (mode === 'sailor') { sailorBtn.classList.add('active'); sailorBtn.setAttribute('aria-pressed', 'true'); }
                        else { sailorBtn.classList.remove('active'); sailorBtn.setAttribute('aria-pressed', 'false'); }
                    }
                    if (regattaBtn) {
                        if (mode === 'regatta') { regattaBtn.classList.add('active'); regattaBtn.setAttribute('aria-pressed', 'true'); }
                        else { regattaBtn.classList.remove('active'); regattaBtn.setAttribute('aria-pressed', 'false'); }
                    }
                    updateSearchModeFlashState();
                }
                function setSearchMode(mode, skipDelayedSearch) {
                    searchMode = mode;
                    window.searchMode = mode;
                    window.setSearchMode = setSearchMode;
                    setSearchInteractionActive(false);
                    // Clear the inactive field when toggling
                    var regattaInput = document.getElementById('temp-landing-regatta-input');
                    // Abort any ongoing search
                    if (sailorSearchAbort) sailorSearchAbort.abort();
                    sailorSearchAbort = new AbortController();
                    // Clear search results to revert to logged-in profile
                    sailorSearchLastQuery = '';
                    // Auto-close regatta results modal when switching to Sailor (same way sailor results hide when switching to Regatta)
                    if (mode === 'sailor' && typeof window.closeRegattaResultSheetModal === 'function') window.closeRegattaResultSheetModal();
                    if (mode === 'sailor') {
                        try { if (regattaInput) regattaInput.value = ''; } catch (_) {}
                        try { if (sailorSearchInput) sailorSearchInput.focus(); } catch (_) {}
                        // Clear regatta results list and show sailor profile area (return to Sailor profile)
                        var publicRegattasList = document.getElementById('public-regattas-list');
                        if (publicRegattasList) publicRegattasList.innerHTML = '';
                        sailorSearchResults.style.display = 'block';
                    }
                    if (sailorBtn) {
                        if (mode === 'sailor') { sailorBtn.classList.add('active'); sailorBtn.setAttribute('aria-pressed', 'true'); }
                        else { sailorBtn.classList.remove('active'); sailorBtn.setAttribute('aria-pressed', 'false'); }
                    }
                    if (regattaBtn) {
                        if (mode === 'regatta') { regattaBtn.classList.add('active'); regattaBtn.setAttribute('aria-pressed', 'true'); }
                        else { regattaBtn.classList.remove('active'); regattaBtn.setAttribute('aria-pressed', 'false'); }
                    }
                    updateSearchModeFlashState();
                    if (mode === 'sailor') {
                        try { if (sailorSearchInput) sailorSearchInput.value = ''; } catch (_) {}
                        if (!skipDelayedSearch) {
                            try { runSailorSearch(); } catch (_) {}
                        }
                    } else if (mode === 'regatta') {
                        try { if (sailorSearchInput) sailorSearchInput.value = ''; } catch (_) {}
                        try { if (regattaInput) regattaInput.focus(); } catch (_) {}
                        // Hide sailor results when switching to Regatta mode
                        try {
                            var _sm2 = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_sm2) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {} else {
                                sailorSearchResults.style.display = 'none';
                                sailorSearchResults.innerHTML = '';
                            }
                        } catch (_) {
                            sailorSearchResults.style.display = 'none';
                            sailorSearchResults.innerHTML = '';
                        }
                        // Full dated list newest-first (empty query loads all)
                        _regattaSearchAllCache = null;
                        if (typeof applyRegattaFilter === 'function') applyRegattaFilter();
                    }
                }
                // Toggle Sailor / Regatta: click switches mode without navigating
                updateSearchModeFlashState();
                if (sailorBtn) sailorBtn.addEventListener('click', function(e) { e.preventDefault(); setSearchMode('sailor'); });
                if (regattaBtn) regattaBtn.addEventListener('click', function(e) { e.preventDefault(); setSearchMode('regatta'); });
                var regattaFormTop = document.getElementById('temp-landing-regatta-form');
                if (regattaFormTop) regattaFormTop.addEventListener('submit', function(e) { e.preventDefault(); try { if (typeof applyRegattaFilter === 'function') applyRegattaFilter(); } catch (_) {} });
                try { _saTryRestoreRegattaSearchState(); } catch (_) {}

                document.addEventListener('click', function(ev) {
                    if (sailorSearchResults.querySelector('#chosen-sailor-before-profile')) return;
                    // Never show sailor profile when user clicked regatta results (so regatta row opens regatta, not sailor popup)
                    var inRegattaResults = ev.target && ev.target.closest && (ev.target.closest('#public-regattas-section') || ev.target.closest('#public-regattas-list'));
                    if (inRegattaResults) return;
                    if (!sailorSearchForm.contains(ev.target) && !sailorSearchResults.contains(ev.target)) {
                        // Only handle click-outside for Sailor mode
                        if (searchMode === 'sailor') {
                            // If logged in, show their profile; otherwise show placeholder
                            (async function() {
                                try {
                                    setSearchInteractionActive(false);
                                    var _clsPathClk = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                                    if (typeof sailingsaIsClassRoutePath === 'function' && sailingsaIsClassRoutePath(_clsPathClk)) return;
                                    if (typeof sailingsaIsSailorProfilePath === 'function' && sailingsaIsSailorProfilePath(_clsPathClk)) return;
                                    var session = typeof window.__sailingsaGetSharedSession === 'function'
                                        ? await window.__sailingsaGetSharedSession()
                                        : (typeof checkSession === 'function' ? await checkSession() : { valid: false });
                                    var sasId = session.valid && (session.sas_id || (session.user && session.user.sas_id)) ? (session.sas_id || session.user.sas_id) : null;
                                    if (sasId && typeof window.showSailorStatsInResults === 'function') {
                                        var user = session.user || {};
                                        var displayName = [user.first_name || user.first_names, user.last_name || user.surname].filter(Boolean).join(' ') || '';
                                        var club = user.primary_club || user.club || '';
                                        window.showSailorStatsInResults(sasId, displayName, club, [], { isLoggedInUser: true, session: session });
                                        return;
                                    }
                                } catch (_) {}
                                showSailorProfilePlaceholder();
                            })();
                        }
                    }
                });
                window.showSailorStatsInResults = showSailorStatsInResultsFn;
                function scrollToSailorProfile() {
                    if (sailorSearchResults && sailorSearchResults.offsetParent !== null) {
                        sailorSearchResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
                window.showSailorProfileFromResult = function(sid, name, club, classesSailed) {
                    if (!sid && !(name = (name || '').trim())) return;
                    if (typeof window.closeRegattaResultSheetModal === 'function') window.closeRegattaResultSheetModal();
                    if (typeof setSearchMode === 'function') setSearchMode('sailor', true);
                    sailorSearchResults.style.display = 'block';
                    var sidStrProfile = String(sid || '').trim();
                    var isNameIdentity = sidStrProfile.toUpperCase().startsWith('NAME:');
                    var isBareSlug = sidStrProfile && /^[a-z0-9]+(?:-[a-z0-9]+)+$/i.test(sidStrProfile) && !/^\d+$/.test(sidStrProfile) && !sidStrProfile.toUpperCase().startsWith('TMP:') && !isNameIdentity;
                    if (sid && (isNameIdentity || isBareSlug)) {
                        var APIname = window.API_BASE || '';
                        var slugForUrl = isNameIdentity ? sidStrProfile.slice(5) : sidStrProfile;
                        var memberSid = isNameIdentity ? sidStrProfile : ('NAME:' + sidStrProfile);
                        window.sailingsaUrlLockedSlug = slugForUrl;
                        if (slugForUrl && window.history && window.history.pushState) {
                            window.history.pushState({}, '', '/sailor/' + slugForUrl);
                        }
                        if (APIname && slugForUrl) {
                            fetch(APIname + '/api/sailor/resolve?slug=' + encodeURIComponent(slugForUrl)).then(function(r) { return r.ok ? r.json() : null; }).then(function(res) {
                                if (res && typeof setSailorPageSEO === 'function') setSailorPageSEO(res.name, res.sas_id, res.slug, res.canonical_url);
                            }).catch(function() {});
                        }
                        if (typeof window.showSailorStatsInResults === 'function') {
                            var pName = window.showSailorStatsInResults(memberSid, name || '', club || '—', classesSailed || '—', { allowUrlOverride: true });
                            if (pName && typeof pName.then === 'function') pName.then(scrollToSailorProfile); else setTimeout(scrollToSailorProfile, 300);
                        }
                        return;
                    }
                    if (sid && (String(sid).match(/^\d+$/) || String(sid).toUpperCase().startsWith('TMP'))) {
                        var API = window.API_BASE || '';
                        if (String(sid).match(/^\d+$/) && API) {
                            fetch(API + '/api/sailor/resolve?sas_id=' + encodeURIComponent(sid)).then(function(r) { return r.ok ? r.json() : null; }).then(function(res) {
                                if (res && res.slug && window.history && window.history.pushState) {
                                    window.sailingsaUrlLockedSlug = res.slug;
                                    window.history.pushState({}, '', '/sailor/' + res.slug);
                                    if (typeof setSailorPageSEO === 'function') setSailorPageSEO(res.name, res.sas_id, res.slug, res.canonical_url);
                                }
                            }).catch(function() {});
                        } else {
                            var basePath = window.location.pathname || ((window.BASE_PATH || '/') + 'index.html');
                            if (basePath === '/' || !basePath) basePath = (window.BASE_PATH || '/') + 'index.html';
                            if (window.history && window.history.pushState) window.history.pushState({}, '', basePath.split('?')[0] + '?sas_id=' + encodeURIComponent(sid));
                        }
                        if (typeof window.showSailorStatsInResults === 'function') {
                            var p = window.showSailorStatsInResults(sid, name || '', club || '—', classesSailed || '—', { allowUrlOverride: true });
                            if (p && typeof p.then === 'function') p.then(scrollToSailorProfile); else setTimeout(scrollToSailorProfile, 300);
                        }
                        return;
                    }
                    if (name) {
                        var APIresolve = window.API_BASE || '';
                        var slugFromName = String(name).trim().toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                        var resolvePromise = (slugFromName && APIresolve)
                            ? fetch(APIresolve + '/api/sailor/resolve?slug=' + encodeURIComponent(slugFromName)).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; })
                            : Promise.resolve(null);
                        resolvePromise.then(function(resolved) {
                            var memberSid = (resolved && resolved.sas_id) ? String(resolved.sas_id) : '';
                            if (memberSid && resolved.slug && window.history && window.history.pushState) {
                                window.sailingsaUrlLockedSlug = resolved.slug;
                                window.history.pushState({}, '', '/sailor/' + resolved.slug);
                                if (typeof setSailorPageSEO === 'function') setSailorPageSEO(resolved.name, resolved.sas_id, resolved.slug, resolved.canonical_url);
                            } else if (slugFromName && window.history && window.history.pushState) {
                                window.sailingsaUrlLockedSlug = slugFromName;
                                window.history.pushState({}, '', '/sailor/' + slugFromName);
                            }
                            if (typeof window.showSailorStatsInResults === 'function') {
                                var p = window.showSailorStatsInResults(memberSid || ('NAME:' + slugFromName) || name, name || '', club || '—', classesSailed || '—', { allowUrlOverride: true });
                                if (p && typeof p.then === 'function') p.then(scrollToSailorProfile); else setTimeout(scrollToSailorProfile, 300);
                            }
                        }).catch(function() {
                            if (typeof window.showSailorStatsInResults === 'function') {
                                var p = window.showSailorStatsInResults(name, name || '', club || '—', classesSailed || '—');
                                if (p && typeof p.then === 'function') p.then(scrollToSailorProfile); else setTimeout(scrollToSailorProfile, 300);
                            }
                        });
                    }
                };
                // Initially hide profile section - will be shown only if logged in or sailor selected
                try {
                    var _i1 = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                    if (/^\/sailor\//i.test(_i1) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {} else {
                        sailorSearchResults.style.display = 'none';
                        sailorSearchResults.innerHTML = '';
                    }
                } catch (_) {
                    sailorSearchResults.style.display = 'none';
                    sailorSearchResults.innerHTML = '';
                }
                (async function() {
                    var _startupTraceId = "startup-iife-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
                    // #region debug-point C:startup-iife-start
                    if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'startup IIFE start', {
                        path: (window.location && window.location.pathname) || '',
                        deferPageContent: !!window.__sailingsaDeferPageContent
                    }, _startupTraceId);
                    // #endregion
                    try {
                        var pathname = window.location.pathname || '';
                        var sailorSlugMatch = pathname.match(/^\/sailor\/([^/]+)/);
                        if (sailorSlugMatch) {
                            // #region debug-point C:startup-sailor-slug
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'startup IIFE sailor slug branch', {
                                slug: decodeURIComponent(sailorSlugMatch[1] || '')
                            }, _startupTraceId);
                            // #endregion
                            await loadSailorProfileFromPathSlug(decodeURIComponent(sailorSlugMatch[1]));
                            if (window.__sailingsaDeferPageContent) {
                                await updatePageContent();
                            }
                            return;
                        }
                        if (!window.__sailingsaDeferPageContent) {
                            // #region debug-point C:startup-skip
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'startup IIFE skipped because page content already handled', {
                                path: pathname
                            }, _startupTraceId);
                            // #endregion
                            return;
                        }
                        if (window.__sailingsaDeferPageContent) {
                            window.sailingsaUrlLockedSlug = '';
                            await updatePageContent();
                        }
                        var pathNorm = (pathname || '').replace(/\/+$/, '') || '/';
                        if (/^\/class\/\d+-/i.test(pathNorm)) {
                            return;
                        }
                        var session = typeof window.__sailingsaGetSharedSession === 'function'
                            ? await window.__sailingsaGetSharedSession()
                            : (typeof checkSession === 'function' ? await checkSession() : { valid: false });
                        // #region debug-point C:startup-session
                        if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'startup IIFE checkSession done', {
                            valid: !!session.valid,
                            sasId: session.sas_id || (session.user && session.user.sas_id) || '',
                            path: pathname
                        }, _startupTraceId);
                        // #endregion
                        var qs = new URLSearchParams(window.location.search);
                        var sasIdFromUrl = qs.get('sas_id') || qs.get('sas-id');
                        if (session.valid && (session.sas_id || (session.user && session.user.sas_id))) {
                            var sasId = session.sas_id || session.user.sas_id;
                            var user = session.user || {};
                            var displayName = [user.first_name || user.first_names, user.last_name || user.surname].filter(Boolean).join(' ') || '';
                            var club = user.primary_club || user.club || '';
                            // #region debug-point C:startup-show-profile
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'startup IIFE rendering logged-in profile', {
                                sasId: sasId,
                                displayName: displayName
                            }, _startupTraceId);
                            // #endregion
                            await window.showSailorStatsInResults(sasId, displayName, club, [], { isLoggedInUser: true, session: session });
                            if (sasIdFromUrl) {
                                var basePath = window.location.pathname || '/index.html';
                                if (basePath === '/' || !basePath) basePath = '/index.html';
                                if (window.history && window.history.replaceState) window.history.replaceState({}, document.title, basePath);
                            }
                            return;
                        }
                        if (sasIdFromUrl && typeof window.showSailorProfileFromResult === 'function') {
                            // #region debug-point C:startup-sas-url
                            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('C', 'startup IIFE sas_id URL branch', {
                                sasIdFromUrl: sasIdFromUrl
                            }, _startupTraceId);
                            // #endregion
                            window.showSailorProfileFromResult(sasIdFromUrl, '', '', '');
                        }
                    } catch (e) {
                        console.warn('[DEBUG] Load logged-in sailor profile in box:', e);
                        // On error, keep profile section hidden
                        try {
                            var _e1 = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                            if (/^\/sailor\//i.test(_e1) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {} else {
                                sailorSearchResults.style.display = 'none';
                                sailorSearchResults.innerHTML = '';
                            }
                        } catch (_) {
                            sailorSearchResults.style.display = 'none';
                            sailorSearchResults.innerHTML = '';
                        }
                    }
                })();
            }
        });

        // Landing page regatta search: navigation is handled ONLY by per-row listener in renderRegattasTable (stopImmediatePropagation). No delegated handler here to avoid conflict.

        // "Your Sailing Results" button removed - no longer needed

        // Auth button (Logout/Sign In) - handled dynamically in updateHeaderAuthStatus
        // The button ID is 'authBtn' and it switches between Logout and Sign In based on login status
        _dbg('[DEBUG] index.html: Auth button will be handled by updateHeaderAuthStatus');
        
        /**
         * Update page content based on login status
         */
        async function updatePageContent(options) {
            _dbg('[DEBUG] updatePageContent: Called');
            options = options || {};
            var pathname = (typeof window !== 'undefined' && window.location && window.location.pathname) ? String(window.location.pathname).replace(/\/+$/, '') || '/' : '';
            var _updatePerfStart = Date.now();
            var _updateTraceId = "update-page-" + _updatePerfStart + "-" + Math.random().toString(36).slice(2, 8);
            // #region debug-point A:update-start
            if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('A', 'updatePageContent start', { path: pathname }, _updateTraceId);
            // #endregion
            if (typeof sailingsaIsClassRoutePath === 'function' && sailingsaIsClassRoutePath(pathname)) {
                return;
            }
            var isExplicitSailorProfileUrl = sailingsaIsSailorProfilePath(pathname);
            if (typeof window.setMainColumnMode === 'function') {
                window.setMainColumnMode('landing');
            }
            try {
                var _sessionStart = Date.now();
                const session = options.session
                    ? options.session
                    : (typeof window.__sailingsaGetSharedSession === 'function'
                        ? await window.__sailingsaGetSharedSession()
                        : await checkSession());
                // #region debug-point A:session-done
                if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('A', 'updatePageContent checkSession done', { ms: Date.now() - _sessionStart, valid: !!session.valid, sasId: session.sas_id || (session.user && session.user.sas_id) || '' }, _updateTraceId);
                // #endregion
                // #region debug-point A:update-branch
                if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('A', 'updatePageContent branch decided', {
                    path: pathname,
                    isExplicitSailorProfileUrl: !!isExplicitSailorProfileUrl,
                    sessionValid: !!session.valid
                }, _updateTraceId);
                // #endregion
                const publicView = document.getElementById('public-view');
                const sailorView = document.getElementById('sailor-view');
                if (isExplicitSailorProfileUrl) {
                    if (session.valid) {
                        if (publicView) publicView.style.display = 'none';
                        if (sailorView) sailorView.style.display = 'none';
                    }
                    const sasIdLocked = session.sas_id || session.user?.sas_id;
                    if (sasIdLocked) {
                        const fullProfileLinkContainer = document.getElementById('full-profile-link-container');
                        const fullProfileLink = document.getElementById('full-profile-link');
                        if (fullProfileLinkContainer && fullProfileLink) {
                            fullProfileLinkContainer.style.display = 'block';
                            fullProfileLink.href = '/search.html?sas_id=' + encodeURIComponent(sasIdLocked);
                        }
                    }
                    await loadPublicRegattas();
                    return;
                }
                
                if (session.valid) {
                    // Same containers: show logged-in sailor's tabbed profile in sailor-search-results (replaced only when they search and click a result)
                    _dbg('[DEBUG] updatePageContent: Showing sailor view (unified container)');
                    if (publicView) {
                        publicView.style.display = 'none';
                    }
                    if (sailorView) {
                        sailorView.style.display = 'none';
                    }
                    
                    const sasId = session.sas_id || session.user?.sas_id;
                    if (!isExplicitSailorProfileUrl && sasId && typeof window.showSailorStatsInResults === 'function') {
                        const user = session.user || {};
                        const displayName = [user.first_name || user.first_names, user.last_name || user.surname].filter(Boolean).join(' ') || '';
                        const club = user.primary_club || user.club || '';
                        var _showStatsStart = Date.now();
                        await window.showSailorStatsInResults(sasId, displayName, club, [], { isLoggedInUser: true, session: session });
                        // #region debug-point B:update-show-sailor-done
                        if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('B', 'updatePageContent showSailorStatsInResults done', { ms: Date.now() - _showStatsStart, totalMs: Date.now() - _updatePerfStart, sasId: sasId }, _updateTraceId);
                        // #endregion
                    } else if (!isExplicitSailorProfileUrl && sailorView) {
                        sailorView.style.display = 'block';
                    }
                    
                    if (sasId && !isExplicitSailorProfileUrl) {
                        var _congratsStart = Date.now();
                        await loadCongratulations(sasId);
                        // #region debug-point D:congratulations-done
                        if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('D', 'updatePageContent loadCongratulations done', { ms: Date.now() - _congratsStart, totalMs: Date.now() - _updatePerfStart, sasId: sasId }, _updateTraceId);
                        // #endregion
                    }
                    if (sasId) {
                        // Show and set full profile link
                        const fullProfileLinkContainer = document.getElementById('full-profile-link-container');
                        const fullProfileLink = document.getElementById('full-profile-link');
                        const popupCheckbox = document.getElementById('popup-expansion-checkbox');
                        
                        if (fullProfileLinkContainer && fullProfileLink) {
                            fullProfileLinkContainer.style.display = 'block';
                            const searchUrl = `/search.html?sas_id=${encodeURIComponent(sasId)}`;
                            
                            // Set up click handler for popup vs new tab
                            fullProfileLink.addEventListener('click', function(e) {
                                e.preventDefault();
                                const usePopup = popupCheckbox && popupCheckbox.checked;
                                
                                if (usePopup) {
                                    // Open in popup modal
                                    openFullProfilePopup(sasId);
                                } else {
                                    // Open in new tab
                                    window.open(searchUrl, '_blank', 'noopener,noreferrer');
                                }
                            });
                            
                            // Set href for right-click/open in new tab
                            fullProfileLink.href = searchUrl;
                        }
                    } else {
                        // Hide full profile link if not logged in
                        const fullProfileLinkContainer = document.getElementById('full-profile-link-container');
                        if (fullProfileLinkContainer) {
                            fullProfileLinkContainer.style.display = 'none';
                        }
                    }
                    
                    // Load regattas for signed-in users (same as public, but with personal context)
                    await loadPublicRegattas();
                    // #region debug-point E:update-finished-logged-in
                    if (typeof window.__saProfilePerfLog === 'function') window.__saProfilePerfLog('E', 'updatePageContent finished logged-in path', { totalMs: Date.now() - _updatePerfStart, sasId: sasId || '' }, _updateTraceId);
                    // #endregion
                } else {
                    // Show public view
                    _dbg('[DEBUG] updatePageContent: Showing public view');
                    if (publicView) {
                        publicView.style.display = 'block';
                    }
                    if (sailorView) {
                        sailorView.style.display = 'none';
                    }
                    
                    // Hide full profile link for public view
                    const fullProfileLinkContainer = document.getElementById('full-profile-link-container');
                    if (fullProfileLinkContainer) {
                        fullProfileLinkContainer.style.display = 'none';
                    }
                    
                    // Load public regattas
                    await loadPublicRegattas();
                }
            } catch (error) {
                console.error('[DEBUG] updatePageContent: Error:', error);
                var pathErr = (typeof window !== 'undefined' && window.location && window.location.pathname) ? String(window.location.pathname).replace(/\/+$/, '') || '/' : '';
                if (typeof sailingsaIsClassRoutePath === 'function' && sailingsaIsClassRoutePath(pathErr)) {
                    return;
                }
                // Default to public view on error
                const publicView = document.getElementById('public-view');
                const sailorView = document.getElementById('sailor-view');
                if (publicView) {
                    publicView.style.display = 'block';
                }
                if (sailorView) {
                    sailorView.style.display = 'none';
                }
                // Try to load public regattas even on error
                await loadPublicRegattas();
            }
        }
        
        // Make updatePageContent globally available
        window.updatePageContent = updatePageContent;
        window.addEventListener('popstate', function() {
            var p = (window.location.pathname || '').replace(/\/+$/, '') || '/';
            var classSlugPop = (p.indexOf('/class/') === 0) ? p.slice('/class/'.length).split('/')[0] : '';
            if (classSlugPop && typeof window.loadClassPageRoute === 'function') {
                window.loadClassPageRoute(classSlugPop);
                return;
            }
            var sailorSlugPop = sailingsaSailorSlugFromPath(p);
            if (sailorSlugPop) {
                loadSailorProfileFromPathSlug(sailorSlugPop);
                return;
            }
            window.sailingsaUrlLockedSlug = '';
            if (typeof updatePageContent === 'function') updatePageContent();
        });
        
        /**
         * Load congratulations message for podium finishes
         */
        async function loadCongratulations(sasId) {
            // Congratulations message removed for later re-add; section kept hidden
            const congratsSection = document.getElementById('congratulations-section');
            if (congratsSection) congratsSection.style.display = 'none';
            return;

        }
        
        // Make function globally available
        window.loadCongratulations = loadCongratulations;
        
        /**
         * Load personal sailing profile data
         */
        async function loadPersonalProfile(sasId) {
            _dbg('[DEBUG] loadPersonalProfile: Loading profile for SAS ID:', sasId);
            const profileBoxes = document.getElementById('personal-profile-boxes');
            
            if (!profileBoxes) {
                console.warn('[DEBUG] loadPersonalProfile: personal-profile-boxes not found');
                return;
            }
            
            try {
                // Show loading state
                profileBoxes.innerHTML = '<div style="grid-column: 1 / -1; padding: 1rem; text-align: center; color: #666;">Loading profile...</div>';
                
                // Fetch member profile, results, and clubs in parallel (clubs for province fallback)
                const API = window.API_BASE || window.location.origin || '';
                const [memberResponse, resultsResponse, clubsResponse] = await Promise.all([
                    fetch(`${API}/api/search?sas_id=${encodeURIComponent(sasId)}`).catch(() => null),
                    fetch(`${API}/api/member/${encodeURIComponent(sasId)}/results`).catch(() => null),
                    fetch(`${API}/api/clubs`).catch(() => null)
                ]);
                
                const members = memberResponse?.ok ? await memberResponse.json() : [];
                const resultsData = resultsResponse?.ok ? await resultsResponse.json() : { results: [] };
                let clubsList = [];
                try { clubsList = clubsResponse?.ok ? await clubsResponse.json() : []; } catch (_) {}
                const clubsByCode = {};
                if (Array.isArray(clubsList)) clubsList.forEach(function(c) { const code = (c.code || '').toString().trim().toUpperCase(); if (code) clubsByCode[code] = (c.province || c.province_code || '').toString().trim(); });
                
                const member = Array.isArray(members) ? members[0] : members;
                const results = resultsData.results || [];
                
                if (!member) {
                    profileBoxes.innerHTML = '<div style="grid-column: 1 / -1; padding: 1rem; text-align: center; color: #666;">Profile not found.</div>';
                    return;
                }
                
                // Get basic info
                const fullName = member.full_name || `${member.first_name || ''} ${member.last_name || ''}`.trim() || 'Sailor';
                const sailorId = sasId;
                
                // Calculate age - use reference year when we have birth year so season age (e.g. 15/16) is consistent
                const ageRefYear = (typeof window.AGE_REFERENCE_YEAR === 'number' && window.AGE_REFERENCE_YEAR > 1900) ? window.AGE_REFERENCE_YEAR : 2025;
                let age = '';
                if (member.born !== undefined && member.born !== null && member.born !== '' && !isNaN(member.born)) {
                    age = ageRefYear - parseInt(member.born);
                } else if (member.year_of_birth !== undefined && member.year_of_birth !== null && member.year_of_birth !== '' && !isNaN(member.year_of_birth)) {
                    age = ageRefYear - parseInt(member.year_of_birth);
                } else if (member.age !== undefined && member.age !== null && member.age !== '' && !isNaN(member.age)) {
                    age = parseInt(member.age);
                }
                
                // Format age as "15/16 yrs" (current age / next age) - same as Sailor Stats
                let ageDisplay = '';
                if (age && !isNaN(age) && parseInt(age) > 0) {
                    const ageNum = parseInt(age);
                    ageDisplay = `${ageNum}/${ageNum + 1} yrs`;
                } else {
                    ageDisplay = '-';
                }
                const club = (member.club || member.primary_club || member.club_1 || 'N/A').toString().trim();
                const clubDisplay = club && club !== 'N/A' ? club.toUpperCase() : club;
                
                // Province: same resolution as searched sailor profiles (m.province, fallback to club province)
                let provinceVal = (member.province || member.province_name || '').toString().trim();
                if (!provinceVal && clubDisplay && clubDisplay !== 'N/A' && clubsByCode[clubDisplay]) provinceVal = clubsByCode[clubDisplay];
                const provinceNameToCode = { 'Western Cape': 'WC', 'Eastern Cape': 'EC', 'Northern Cape': 'NC', 'Free State': 'FS', 'KwaZulu-Natal': 'KZN', 'KwaZulu Natal': 'KZN', 'Gauteng': 'GP', 'Mpumalanga': 'MP', 'Limpopo': 'LP', 'North West': 'NW', 'Western cape': 'WC', 'Eastern cape': 'EC', 'Northern cape': 'NC', 'Free state': 'FS', 'North west': 'NW' };
                let provinceCode = (provinceVal && provinceVal.length <= 4) ? String(provinceVal).toUpperCase() : (provinceNameToCode[provinceVal] || (provinceVal ? provinceVal.replace(/\s+/g, ' ').trim() : ''));
                if (provinceCode && provinceCode.length > 4) provinceCode = provinceNameToCode[provinceVal] || '';
                const provinceDisplay = provinceVal ? (typeof toProperCase === 'function' ? toProperCase(provinceVal) : provinceVal) : '';
                
                // Calculate sailing statistics
                const regattaEventKeys = new Set();
                let totalRaces = 0;
                const regattaRaceSeen = {};
                const classesSailed = new Set();
                const classRegattaCounts = {};
                
                // Calculate sailing duration
                let sailingDuration = '0 years & 0 months';
                if (results.length > 0) {
                    const dates = results
                        .map(r => r.start_date || r.end_date)
                        .filter(d => d && d !== 'N/A');
                    if (dates.length > 0) {
                        const oldest = new Date(Math.min(...dates.map(d => new Date(d).getTime())));
                        const now = new Date();
                        let years = now.getFullYear() - oldest.getFullYear();
                        let months = now.getMonth() - oldest.getMonth();
                        if (months < 0) {
                            years -= 1;
                            months += 12;
                        }
                        sailingDuration = years > 0 ? `${years} year${years !== 1 ? 's' : ''} & ${months} month${months !== 1 ? 's' : ''}` : `${months} month${months !== 1 ? 's' : ''}`;
                    }
                }
                
                results.forEach(r => {
                    if (isMemberResultSeriesRow(r) || !shouldIncludeMemberResultRow(r, results)) return;

                    if (!isMemberYouthSubFleetBlock(r.block_id)) {
                        const eventKey = memberResultCareerEventKey(r);
                        if (eventKey) regattaEventKeys.add(eventKey);
                    }

                    if (shouldCountMemberResultRaces(r, regattaRaceSeen)) {
                        if (r.race_scores && typeof r.race_scores === 'object') {
                            Object.keys(r.race_scores).forEach(k => {
                                if (/^R\d+$/i.test(k)) {
                                    const score = r.race_scores[k];
                                    if (typeof score === 'number' || (typeof score === 'string' && !/^(DNC|DNS|DNF|DSQ|RET|OCS|BFD|UFD|SCP|RDG|DPI)$/i.test(score))) {
                                        totalRaces++;
                                    }
                                }
                            });
                        } else if (r.races_sailed && typeof r.races_sailed === 'number') {
                            totalRaces += r.races_sailed;
                        }
                    }

                    const className = (r.class_canonical || r.class_original || '').trim();
                    if (className) {
                        classesSailed.add(className);
                        if (!classRegattaCounts[className]) {
                            classRegattaCounts[className] = new Set();
                        }
                        if (r.regatta_id && !isMemberYouthSubFleetBlock(r.block_id)) {
                            classRegattaCounts[className].add(r.regatta_id);
                        }
                    }
                });

                const totalRegattas = regattaEventKeys.size;
                
                // Sort classes by regatta count (descending)
                const sortedClasses = Array.from(classesSailed).sort((a, b) => {
                    const countA = classRegattaCounts[a]?.size || 0;
                    const countB = classRegattaCounts[b]?.size || 0;
                    return countB - countA;
                });
                
                // Build profile boxes - matching search.html styling (small, single line, bold)
                const boxes = [];
                
                // Box 1: Personal Profile > Name
                boxes.push(`
                    <span style="background: #e1bee7 !important; border: 1px solid #ce93d8 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 13px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap; flex-shrink: 0;">
                        Personal Profile &gt; ${fullName}
                    </span>
                `);
                
                // Box 2: ID
                boxes.push(`
                    <div style="background: #e1bee7 !important; border: 1px solid #ce93d8 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                        <span style="font-weight: 700;">ID:</span> <span style="font-weight: 700;">${sailorId}</span>
                    </div>
                `);
                
                // Box 3: Age (format: 15/16)
                boxes.push(`
                    <div style="background: #ffe0b2 !important; border: 1px solid #ffb74d !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #8B4513 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                        <span style="font-weight: 700;">Age:</span> <span style="font-weight: 700;">${ageDisplay}</span>
                    </div>
                `);
                
                // Box 4: Club (link to /club/{slug} when available)
                const clubSlug = clubDisplay && clubDisplay !== 'N/A' ? (codeToSlug[clubDisplay] || '') : '';
                const clubLinkHtml = clubSlug ? `<a href="/club/${encodeURIComponent(clubSlug)}" style="color:inherit;text-decoration:underline">${club.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')}</a>` : club.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                boxes.push(`
                    <div style="background: #e3f2fd !important; border: 1px solid #90caf9 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                        <span style="font-weight: 700;">Club:</span> <span style="font-weight: 700;">${clubLinkHtml}</span>
                    </div>
                `);
                
                // Box: Province (same badge style as searched sailor; only show when we have a value)
                if (provinceVal && provinceDisplay) {
                    const provinceLabel = (provinceCode && provinceCode.length <= 4) ? provinceCode : provinceDisplay;
                    boxes.push(`
                        <div class="sailor-province-icon-box" style="background: #e3f2fd !important; border: 1px solid #90caf9 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;" title="${(provinceDisplay || '').replace(/"/g, '&quot;')}">
                            <span style="font-weight: 700;">Province:</span> <span style="font-weight: 700;">${(provinceLabel || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')}</span>
                        </div>
                    `);
                }
                
                // Box 5: Sailing Duration
                boxes.push(`
                    <div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                        <span style="font-weight: 700;">Sailing:</span> <span style="font-weight: 700;">${sailingDuration}</span>
                    </div>
                `);
                
                // Box 6: Regattas
                boxes.push(`
                    <div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                        <span style="font-weight: 700;">Regatta's =</span> <span style="font-weight: 700;">${totalRegattas}</span>
                    </div>
                `);
                
                // Box 7: Races
                boxes.push(`
                    <div style="background: #c8e6c9 !important; border: 1px solid #81c784 !important; border-radius: 6px; padding: 2px 8px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                        <span style="font-weight: 700;">Races =</span> <span style="font-weight: 700;">${totalRaces}</span>
                    </div>
                `);
                
                // Box 8-12: Classes (Main, 2nd, 3rd, 4th, 5th)
                const classColors = [
                    {bg: '#64b5f6', border: '#42a5f5'}, // Main Class
                    {bg: '#90caf9', border: '#64b5f6'}, // 2nd Class
                    {bg: '#b3e5fc', border: '#81d4fa'}, // 3rd Class
                    {bg: '#e1f5fe', border: '#b3e5fc'}, // 4th Class
                    {bg: '#f3e5f5', border: '#ce93d8'}  // 5th Class
                ];
                const classLabels = ['Main Class', '2nd Class', '3rd Class', '4th Class', '5th Class'];
                
                for (let i = 0; i < Math.min(sortedClasses.length, 5); i++) {
                    boxes.push(`
                        <div style="background: ${classColors[i].bg} !important; border: 1px solid ${classColors[i].border} !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">
                            <span style="font-weight: 700;">${classLabels[i]}:</span> <span style="font-weight: 700;">${sortedClasses[i]}</span>
                        </div>
                    `);
                }
                
                // Box: Sailor Stats (button) - opens modal
                boxes.push(`
                    <div style="background: #d32f2f !important; border: 1px solid #b71c1c !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #ffffff !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap; cursor: pointer;" onclick="showSailorStats('${sailorId}', '${fullName.replace(/'/g, "\\'")}', event)">
                        Sailor Stats
                    </div>
                `);
                
                profileBoxes.innerHTML = boxes.join('');
                
            } catch (error) {
                console.error('[DEBUG] loadPersonalProfile: Error:', error);
                profileBoxes.innerHTML = '<div style="grid-column: 1 / -1; padding: 1rem; text-align: center; color: #d32f2f;">Error loading profile. Please try again later.</div>';
            }
        }
        
        // Make function globally available
        window.loadPersonalProfile = loadPersonalProfile;
        
        /**
         * Load per-class results tables on main page
         */
        async function loadPerClassResults(sasId) {
            try {
                const API = window.API_BASE || window.location.origin || '';
                const container = document.getElementById('per-class-results-container');
                if (!container) return;
                
                // Fetch results
                const resultsResponse = await fetch(`${API}/api/member/${encodeURIComponent(sasId)}/results`);
                if (!resultsResponse.ok) return;
                
                const resultsData = await resultsResponse.json();
                const results = resultsData.results || [];
                
                if (results.length === 0) {
                    container.style.display = 'none';
                    return;
                }
                
                // Group results by class and calculate stats
                const resultsByClass = {};
                const classLastDates = {};
                const classRegattaIds = {};
                const classRaceCounts = {};
                
                results.forEach(r => {
                    // Exclude series regattas
                    const isSeries = r.is_series === true || 
                                   r.regatta_number === 'S' || 
                                   (r.event_name && r.event_name.includes('Series') && r.event_name.includes('> Overall'));
                    if (isSeries) return;
                    
                    const className = (r.class_canonical || r.class_original || '').trim();
                    if (!className) return;
                    
                    if (!resultsByClass[className]) {
                        resultsByClass[className] = [];
                        classRegattaIds[className] = new Set();
                        classRaceCounts[className] = 0;
                    }
                    resultsByClass[className].push(r);
                    
                    // Count unique regattas
                    if (r.regatta_id && !classRegattaIds[className].has(r.regatta_id)) {
                        classRegattaIds[className].add(r.regatta_id);
                    }
                    
                    // Count races
                    if (r.race_scores && typeof r.race_scores === 'object') {
                        Object.keys(r.race_scores).forEach(k => {
                            if (/^R\d+$/i.test(k) && r.race_scores[k] !== null && r.race_scores[k] !== undefined && r.race_scores[k] !== '') {
                                classRaceCounts[className]++;
                            }
                        });
                    } else if (typeof r.races_sailed === 'number' && r.races_sailed > 0) {
                        classRaceCounts[className] += r.races_sailed;
                    }
                    
                    // Track last date for sorting
                    const dateStr = r.end_date || r.start_date;
                    if (dateStr) {
                        const date = new Date(dateStr);
                        if (!isNaN(date.getTime())) {
                            if (!classLastDates[className] || date > classLastDates[className]) {
                                classLastDates[className] = date;
                            }
                        }
                    }
                });
                
                // Sort classes by last date (most recent first)
                const sortedClasses = Object.keys(resultsByClass).sort((a, b) => {
                    const dateA = classLastDates[a] || new Date(0);
                    const dateB = classLastDates[b] || new Date(0);
                    return dateB - dateA;
                });
                
                if (sortedClasses.length === 0) {
                    container.style.display = 'none';
                    return;
                }
                
                let html = '';
                
                // Class labels for badges
                const classLabels = ['Main Class', '2nd Class', '3rd Class', '4th Class', '5th Class'];
                
                sortedClasses.forEach((className, classIndex) => {
                    const classResults = (resultsByClass[className] || []).sort((a, b) => {
                        const dateA = new Date(a.end_date || a.start_date || 0);
                        const dateB = new Date(b.end_date || b.start_date || 0);
                        return dateB - dateA;
                    });
                    
                    // Calculate class stats
                    const classRegattaCount = classRegattaIds[className] ? classRegattaIds[className].size : 0;
                    const classRaceCount = classRaceCounts[className] || 0;
                    
                    // Determine class label
                    const classLabel = classIndex < classLabels.length ? classLabels[classIndex] : (classIndex + 1) + 'th Class';
                    
                    const classResultsId = `class-results-${className.replace(/\s+/g, '-').toLowerCase()}-${sasId}`;
                    const expandedViewId = `expanded-view-${className.replace(/\s+/g, '-').toLowerCase()}-${sasId}`;
                    
                    // Build badges HTML
                    const badgesHtml = `<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; align-items: center;">
                        <div style="background: #64b5f6 !important; border: 1px solid #42a5f5 !important; border-radius: 6px; padding: 2px 6px; width: auto; height: auto; font-size: 11px; font-weight: 700; color: #000080 !important; box-sizing: border-box; display: inline-flex; align-items: center; line-height: 1.1; margin: 0; white-space: nowrap;">${classLabel} &gt; Regatta's =${classRegattaCount}/ Races =${classRaceCount}</div>
                    </div>`;
                    
                    html += `
                        <div class="class-results-section" id="${classResultsId}" style="margin-bottom: 0.5rem;">
                            <h4 style="font-size: 16px; margin: 6px 0 4px 0; color: #1e3a8a; font-weight: 700;">${className} Results</h4>
                            ${badgesHtml}
                            <div style="overflow-x: auto;">
                                <table class="snapshot-table">
                                    <thead>
                                        <tr>
                                            <th>No.</th>
                                            <th>Regatta</th>
                                            <th>Date</th>
                                            <th>Sail No</th>
                                            <th>Club</th>
                                            <th>Rank</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;
                    
                    classResults.forEach((result, index) => {
                        const rankNum = result.rank ? parseInt(String(result.rank).match(/^\s*([0-9]+)/)?.[1] || '0') : null;
                        const rankClass = rankNum === 1 ? 'rank-1' : rankNum === 2 ? 'rank-2' : rankNum === 3 ? 'rank-3' : '';
                        
                        let formattedDate = 'N/A';
                        const dateStr = result.regatta_date || result.end_date || result.start_date;
                        if (dateStr) {
                            const date = new Date(dateStr);
                            if (!isNaN(date.getTime())) {
                                const day = String(date.getDate()).padStart(2, '0');
                                const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                                const month = months[date.getMonth()];
                                const year = date.getFullYear();
                                formattedDate = `${day} ${month} ${year}`;
                            }
                        }
                        
                        // Format rank (e.g., "1st/33")
                        let displayRank = result.rank || 'N/A';
                        const entries = result.entries || result.ranks_sailed || result.entries_raced;
                        if (entries && rankNum) {
                            const suffix = rankNum === 1 ? 'st' : rankNum === 2 ? 'nd' : rankNum === 3 ? 'rd' : 'th';
                            displayRank = `${rankNum}${suffix}/${entries}`;
                        }
                        
                        const regattaId = result.regatta_id || '';
                        const classNameEscaped = className.replace(/'/g, "\\'");
                        const regattaNameEscaped = (result.event_name || result.regatta_name || 'N/A').replace(/'/g, "\\'");
                        
                        html += `
                            <tr class="${rankClass}" style="cursor: pointer;" onclick="showRegattaResultChoice('${regattaId}', '${classNameEscaped}', '${regattaNameEscaped}')" title="Click to view results">
                                <td>${index + 1}</td>
                                <td style="text-align: left; font-weight: bold;">${result.event_name || result.regatta_name || 'N/A'}</td>
                                <td>${formattedDate}</td>
                                <td>${result.sail_number || ''}</td>
                                <td style="font-weight: bold;">${String(result.club || result.club_abbrev || result.club_raw || '').toUpperCase()}</td>
                                <td style="font-weight: bold;">${displayRank}</td>
                            </tr>
                        `;
                    });
                    
                    html += `
                                    </tbody>
                                </table>
                            </div>
                            <div class="expanded-view-toggle">
                                <input type="checkbox" id="${expandedViewId}" onchange="toggleExpandedView('${className.replace(/'/g, "\\'")}', '${sasId}', this.checked)">
                                <label for="${expandedViewId}" style="cursor: pointer;">Expanded View</label>
                            </div>
                        </div>
                    `;
                });
                
                container.innerHTML = html;
                container.style.display = 'block';
                
            } catch (error) {
                console.error('[DEBUG] loadPerClassResults: Error:', error);
                const container = document.getElementById('per-class-results-container');
                if (container) {
                    container.style.display = 'none';
                }
            }
        }
        
        // Make function globally available
        window.loadPerClassResults = loadPerClassResults;
        
        /**
         * Show login required popup for public users trying to access restricted content.
         * Popup has "Sign In / Sign Up" (redirect to login) and "Back to Page" (close, stay on page).
         */
        function showLoginRequiredPopup() {
            if (typeof BETA_LOGIN_DISABLED !== 'undefined' && BETA_LOGIN_DISABLED) {
                alert('Login coming soon (Beta). Public content remains available.');
                return;
            }
            var popup = document.getElementById('popupOverlay');
            var loginRequiredState = document.getElementById('state-login-required');
            if (!loginRequiredState) return;
            if (!popup) {
                popup = document.createElement('div');
                popup.id = 'popupOverlay';
                var wrap = document.createElement('div');
                wrap.className = 'popup-container';
                loginRequiredState.parentNode.insertBefore(popup, loginRequiredState);
                popup.appendChild(wrap);
                wrap.appendChild(loginRequiredState);
            }
            popup.style.display = 'flex';
            var states = popup.querySelectorAll('.popup-state');
            if (!states.length) states = document.querySelectorAll('.popup-state');
            states.forEach(function(state) {
                state.style.display = 'none';
                state.classList.add('hidden');
            });
            loginRequiredState.style.display = 'block';
            loginRequiredState.classList.remove('hidden');
            
            function closeLoginRequiredPopup() {
                if (popup) {
                    popup.style.display = 'none';
                    states.forEach(state => {
                        state.style.display = 'none';
                        state.classList.add('hidden');
                    });
                }
            }
            
            const signInBtn = document.getElementById('btnLoginRequiredSignIn');
            const signUpBtn = document.getElementById('btnLoginRequiredSignUp');
            const backBtn = document.getElementById('btnBackToPageFromRestricted');
            
            if (backBtn) {
                backBtn.onclick = function() {
                    closeLoginRequiredPopup();
                };
            }
            
            if (signInBtn) {
                signInBtn.onclick = function() {
                    closeLoginRequiredPopup();
                    var base = (window.location.origin || '') + (window.BASE_PATH || '');
                    if (!base || base === '/') base = window.location.origin || '';
                    window.location.href = base + '/login.html';
                };
            }
            if (signUpBtn) {
                signUpBtn.onclick = function() {
                    closeLoginRequiredPopup();
                    var base = (window.location.origin || '') + (window.BASE_PATH || '');
                    if (!base || base === '/') base = window.location.origin || '';
                    var claim = window.__ssaClaimSailor || {};
                    window.location.href = base + '/signup.html?signup=1'
                        + (claim.sid ? ('&sas_id=' + encodeURIComponent(claim.sid)) : '')
                        + (claim.name ? ('&name=' + encodeURIComponent(claim.name)) : '')
                        + '&returnTo=' + encodeURIComponent(window.location.href || (base + '/'));
                };
            }
        }
        
        // Make function globally available
        window.showLoginRequiredPopup = showLoginRequiredPopup;
        
        /**
         * Show pre-popup or go directly to results.
         * From sailor Regattas Sailed (has class): skip modal, go straight to Class/Fleet results popup.
         * From Regatta Search (no class): go straight to Full Regatta Results (no View results modal).
         */
        async function showRegattaResultChoice(regattaId, className, regattaName) {
            const hasClass = (className || '').trim().length > 0;
            if (hasClass && regattaId) {
                // Sailor profile: go straight to Class/Fleet results popup (skip View results modal)
                if (typeof navigateToClassResults === 'function') {
                    navigateToClassResults(regattaId, className, regattaName);
                }
                return;
            }
            // Regatta Search: go straight to Full Regatta Results (no popup)
            if (regattaId && typeof navigateToFullRegattaResults === 'function') {
                navigateToFullRegattaResults(regattaId, regattaName);
                return;
            }
            const modal = document.getElementById('regattaChoiceModal');
            const nameEl = document.getElementById('regattaChoiceRegattaName');
            const fullRegattaBtn = document.getElementById('regattaChoiceFullRegattaBtn');
            const classResultsBtn = document.getElementById('regattaChoiceClassResultsBtn');
            const classResultBtn = document.getElementById('regattaChoiceClassResultBtn');
            const podiumBtn = document.getElementById('regattaChoicePodiumBtn');
            const step1 = document.getElementById('regattaChoiceStep1');
            const step2 = document.getElementById('regattaChoiceStep2');
            const step3 = document.getElementById('regattaChoiceStep3');
            if (!modal || !nameEl) return;
            modal.dataset.regattaId = regattaId || '';
            modal.dataset.className = className || '';
            modal.dataset.regattaName = regattaName || '';
            nameEl.textContent = regattaName || 'Regatta';
            if (step1) step1.classList.add('active');
            if (step2) step2.classList.remove('active');
            if (step3) step3.classList.remove('active');
            if (fullRegattaBtn) fullRegattaBtn.style.display = '';
            if (podiumBtn) podiumBtn.style.display = 'none';
            if (classResultsBtn) classResultsBtn.style.display = 'none';
            if (classResultBtn) classResultBtn.style.display = '';
            modal.classList.add('show');
        }
        
        function closeRegattaChoiceModal() {
            const modal = document.getElementById('regattaChoiceModal');
            const step1 = document.getElementById('regattaChoiceStep1');
            const step2 = document.getElementById('regattaChoiceStep2');
            const step3 = document.getElementById('regattaChoiceStep3');
            if (modal) modal.classList.remove('show');
            if (step1) step1.classList.add('active');
            if (step2) step2.classList.remove('active');
            if (step3) step3.classList.remove('active');
        }
        
        function showRegattaChoiceStep(stepId) {
            ['regattaChoiceStep1', 'regattaChoiceStep2', 'regattaChoiceStep3'].forEach(function(id) {
                var el = document.getElementById(id);
                if (el) el.classList.toggle('active', id === stepId);
            });
        }
        
        // Close modal on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const choiceModal = document.getElementById('regattaChoiceModal');
                if (choiceModal && choiceModal.classList.contains('show')) {
                    closeRegattaChoiceModal();
                }
            }
        });
        
        /**
         * Generate URL-friendly slug from text
         */
        function generateSlug(text) {
            if (!text) return '';
            return text.toString()
                .toLowerCase()
                .trim()
                .replace(/[^\w\s-]/g, '')
                .replace(/[\s_-]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }

        function memberResultBlockTail(blockId) {
            if (!blockId || String(blockId).indexOf(':') < 0) return '';
            return String(blockId).split(':').slice(1).join(':');
        }

        function isMemberYouthSubFleetBlock(blockId) {
            var tail = memberResultBlockTail(blockId);
            return /^(u19-results|u17-results|420-fleet-under-19|420-fleet-under-17)$/i.test(tail);
        }

        function isMemberOverallSubFleetBlock(blockId) {
            var tail = memberResultBlockTail(blockId);
            return /^(overall-results|420)$/i.test(tail);
        }

        function memberResultFleetShellTail(blockId) {
            var tail = memberResultBlockTail(blockId);
            if (/^420-fleet-under-19$/i.test(tail)) return 'u19-results';
            if (/^420-fleet-under-17$/i.test(tail)) return 'u17-results';
            if (/^420$/i.test(tail)) return 'overall-results';
            return tail;
        }

        function memberResultDisplayEventName(r) {
            var base = (r && r.event_name ? String(r.event_name) : 'Regatta').trim();
            var stem = base.replace(/\s+Results\s*$/i, '').trim();
            var tail = memberResultBlockTail(r && r.block_id);
            var fleet = (r && r.fleet_label ? String(r.fleet_label) : '').trim();
            if (tail === 'u19-results' || tail === '420-fleet-under-19' || /under\s*19/i.test(fleet)) return stem + ' U19 Results';
            if (tail === 'u17-results' || tail === '420-fleet-under-17' || /under\s*17/i.test(fleet)) return stem + ' U17 Results';
            if (tail === 'overall-results' || tail === '420' || fleet === '420 Fleet') return stem + ' Overall Results';
            return base;
        }

        function memberResultHighlightEventName(r) {
            var tail = memberResultBlockTail(r && r.block_id);
            if (tail === 'u19-results' || tail === '420-fleet-under-19') return '420 U19 National Championship Results';
            if (tail === 'u17-results' || tail === '420-fleet-under-17') return '420 U17 National Championship Results';
            return memberResultDisplayEventName(r);
        }

        function memberResultRegattaHref(r) {
            var rid = (r && (r.regatta_id || r.slug)) ? String(r.regatta_id || r.slug).trim() : '';
            if (!rid) return '';
            // Always link to the parent public /regatta/{id} page.
            // Do NOT append fleet tails (-overall-results / -u19-results / …): those child
            // slugs only exist for some events and 404 for most → broken Highlights links.
            // Display labels still use memberResultDisplayEventName / HighlightEventName.
            return '/regatta/' + encodeURIComponent(rid);
        }

        function isMemberResultSeriesRow(r) {
            return !!(r && (r.is_series === true || r.regatta_number === 'S' ||
                (r.event_name && r.event_name.includes('Series') && r.event_name.includes('> Overall'))));
        }

        /** One SAS event key for global regatta/race totals (multi-class same day = once). */
        function memberResultCareerEventKey(r) {
            var rid = (r && r.regatta_id) ? String(r.regatta_id) : '';
            if (!rid) return '';
            if (rid === '381-2026-rcyc-gimco-inter-academy' || rid === '382-2026-rcyc-gimco-cape-31') {
                return '381-2026-rcyc-gimco-inter-academy';
            }
            return rid;
        }

        function shouldCountMemberResultRaces(r, seenByEventKey) {
            if (!r || !r.regatta_id) return false;
            if (isMemberYouthSubFleetBlock(r.block_id)) return false;
            var key = memberResultCareerEventKey(r);
            if (!key || seenByEventKey[key]) return false;
            seenByEventKey[key] = true;
            return true;
        }

        function shouldIncludeMemberResultRow(r, allResults) {
            var rid = (r && r.regatta_id) ? String(r.regatta_id) : '';
            if (!rid) return false;
            var has = function(id) {
                return (allResults || []).some(function(x) { return x.regatta_id === id; });
            };
            if (rid === '419-2025-2025-420-national-championship-results' && has('366-2025-420-national-championship-results')) return false;
            if (rid === '412-2025-2025-sa-sailing-youth-national-championship-fina' && has('377-2025-hyc-sa-youth-nationals')) return false;
            if (rid === '416-2025-2025-tsc-cape-classic' && has('371-2025-tsc-cape-classic')) return false;
            if (rid === '382-2026-rcyc-gimco-inter-academy-challenge' && has('381-2026-rcyc-gimco-inter-academy')) return false;
            if (rid === 'live-2026-wc-dinghy-champs-sbyc' && has('2026-04-06-western-cape-dinghy-championships')) return false;
            return true;
        }

        function memberClassRegattaSort(a, b) {
            var d = (b.dateStr || '').localeCompare(a.dateStr || '');
            if (d) return d;
            if ((a.regatta_id || '') !== (b.regatta_id || '')) return (a.regatta_id || '').localeCompare(b.regatta_id || '');
            function blockOrder(blockId) {
                var t = memberResultBlockTail(blockId);
                if (t === 'overall-results' || t === '420') return 0;
                if (t === 'u19-results' || t === '420-fleet-under-19') return 1;
                if (t === 'u17-results' || t === '420-fleet-under-17') return 2;
                return 3;
            }
            return blockOrder(a.block_id) - blockOrder(b.block_id);
        }

        function assignMemberRegattaDisplayNumbers(rows) {
            var parentNum = 0;
            var childIdx = 0;
            var groupRegattaId = null;
            return (rows || []).map(function(row) {
                var copy = Object.assign({}, row);
                var isChild = isMemberYouthSubFleetBlock(copy.block_id);
                if (!isChild) {
                    parentNum += 1;
                    childIdx = 0;
                    groupRegattaId = copy.regatta_id || null;
                    copy.displayNo = String(parentNum);
                    copy.isSubFleetChild = false;
                } else if (copy.regatta_id && copy.regatta_id === groupRegattaId) {
                    copy.displayNo = parentNum + String.fromCharCode(97 + childIdx);
                    childIdx += 1;
                    copy.isSubFleetChild = true;
                } else {
                    parentNum += 1;
                    childIdx = 0;
                    groupRegattaId = copy.regatta_id || null;
                    copy.displayNo = String(parentNum);
                    copy.isSubFleetChild = false;
                }
                return copy;
            });
        }

        function renderMemberRegattaTableRow(row, className, escapeHtml, formatRegattaDate, canClickRegattas) {
            var regattaSlug = typeof generateSlug === 'function' ? generateSlug(row.event_name || row.regatta_id) : '';
            var href = row.result_href || ('/regatta/results.html?regatta_id=' + encodeURIComponent(row.regatta_id) + (regattaSlug ? '&regatta_slug=' + encodeURIComponent(regattaSlug) : ''));
            var nameEsc = escapeHtml(row.event_name);
            var formattedDate = formatRegattaDate(row.dateStr);
            var sailNo = row.sail_number || '';
            var clubCode = row.club || '';
            var rankNum = row.rank;
            var displayRank = '—';
            if (rankNum != null && row.entries != null && row.entries > 0) {
                var suffix = rankNum === 1 ? 'st' : rankNum === 2 ? 'nd' : rankNum === 3 ? 'rd' : 'th';
                displayRank = rankNum + suffix + '/' + row.entries;
            } else if (rankNum != null) {
                var suffix2 = rankNum === 1 ? 'st' : rankNum === 2 ? 'nd' : rankNum === 3 ? 'rd' : 'th';
                displayRank = rankNum + suffix2;
            }
            var rankClass = '';
            if (rankNum === 1) rankClass = 'rank-1';
            else if (rankNum === 2) rankClass = 'rank-2';
            else if (rankNum === 3) rankClass = 'rank-3';
            var rowClass = rankClass + (row.isSubFleetChild ? ' regatta-subfleet-child' : '');
            var nameCellStyle = row.isSubFleetChild
                ? 'text-align: left; font-weight: 600; padding-left: 1.25rem; color: #334155;'
                : 'text-align: left; font-weight: bold;';
            var classNameEscaped = escapeHtml(className).replace(/'/g, "\\'");
            var regattaNameEscaped = nameEsc.replace(/'/g, "\\'");
            var onclickAttr;
            if (row.isSubFleetChild || row.result_href) {
                onclickAttr = canClickRegattas
                    ? 'onclick="window.location.href=\'' + href.replace(/'/g, "\\'") + '\'" title="View fleet results"'
                    : 'onclick="if(typeof showLoginRequiredPopup === \'function\') { showLoginRequiredPopup(); } else { event.preventDefault(); }" title="Sign in to view regatta details"';
            } else {
                onclickAttr = canClickRegattas
                    ? 'onclick="if(typeof showRegattaResultChoice === \'function\') { showRegattaResultChoice(\'' + escapeHtml(row.regatta_id) + '\', \'' + classNameEscaped + '\', \'' + regattaNameEscaped + '\'); } else { window.location.href=\'' + href.replace(/'/g, "\\'") + '\'; }" title="Click to view results"'
                    : 'onclick="if(typeof showLoginRequiredPopup === \'function\') { showLoginRequiredPopup(); } else { event.preventDefault(); }" title="Sign in to view regatta details"';
            }
            return '<tr class="' + rowClass.trim() + '" style="cursor: pointer;" ' + onclickAttr + '>' +
                '<td>' + escapeHtml(row.displayNo || '') + '</td>' +
                '<td style="' + nameCellStyle + '">' + nameEsc + '</td>' +
                '<td>' + formattedDate + '</td>' +
                '<td>' + escapeHtml(sailNo) + '</td>' +
                '<td style="font-weight: bold;">' + escapeHtml(clubCode) + '</td>' +
                '<td style="font-weight: bold;">' + escapeHtml(displayRank) + '</td>' +
                '</tr>';
        }

        function highlightRegattaHref(item) {
            if (item && item.result_href) return item.result_href;
            if (item && item.block_id) return memberResultRegattaHref(item);
            var slug = (item && (item.regatta_id || item.slug)) ? String(item.regatta_id || item.slug).trim() : '';
            return slug ? '/regatta/' + encodeURIComponent(slug) : '';
        }
        
        /**
         * Open Class Results page in POPUP MODAL (stays on Sailor Profile page)
         */
        function navigateToClassResults(regattaId, className, regattaName) {
            const rid = regattaId != null && regattaId !== '' ? String(regattaId).trim() : '';
            const cname = className != null && className !== '' ? String(className).trim() : '';
            if (!rid || !cname) {
                console.error('navigateToClassResults: missing regatta_id or class', { regattaId, className });
                if (typeof window.showError === 'function') window.showError('Cannot open class results: missing regatta or class.');
                return;
            }
            window._regattaResultBackContext = { regattaId: rid, regattaName: regattaName || rid || '', className: cname };
            const regattaSlug = generateSlug(regattaName || rid);
            const classSlug = generateSlug(cname);
            const url = '/regatta/class/class-results.html?regatta_id=' + encodeURIComponent(rid) + '&class=' + encodeURIComponent(cname) + '&regatta_slug=' + encodeURIComponent(regattaSlug) + '&class_slug=' + encodeURIComponent(classSlug) + '&v=20260323_final_fix';
            openResultPageInModal(url);
        }
        
        /**
         * Open Full Regatta Results page in POPUP MODAL (stays on Sailor Profile page).
         * Opens in expanded view by default.
         */
        function navigateToFullRegattaResults(regattaId, regattaName) {
            const regattaSlug = generateSlug(regattaName || regattaId);
            const url = `/regatta/results.html?regatta_id=${encodeURIComponent(regattaId)}&regatta_slug=${encodeURIComponent(regattaSlug)}&view=expanded`;
            openResultPageInModal(url);
        }
        
        /**
         * Open Class Podium page in POPUP MODAL (stays on Sailor Profile page)
         */
        function navigateToClassPodium(regattaId, className, regattaName) {
            const regattaSlug = generateSlug(regattaName || regattaId);
            const classSlug = generateSlug(className);
            const url = `/regatta/class/podium/podium.html?regatta_id=${encodeURIComponent(regattaId)}&class=${encodeURIComponent(className)}&regatta_slug=${encodeURIComponent(regattaSlug)}&class_slug=${encodeURIComponent(classSlug)}`;
            openResultPageInModal(url);
        }
        
        /**
         * Open result page in modal iframe (POPUP - does NOT navigate away)
         */
        function openResultPageInModal(pageUrl) {
            const engine = typeof window.resolveResultsEngine === 'function' ? window.resolveResultsEngine() : null;
            if (!engine) {
                console.error('Results engine missing');
                if (typeof window.showError === 'function') window.showError('Results engine not loaded');
                return;
            }
            // Build absolute URL from site root only (never use current path - fixes /sailor/regatta/... 404)
            let absoluteUrl = pageUrl;
            if (!pageUrl.startsWith('http://') && !pageUrl.startsWith('https://') && !pageUrl.startsWith('//')) {
                var path = pageUrl.startsWith('/') ? pageUrl : '/' + pageUrl;
                absoluteUrl = window.location.origin + path;
            }
            // Safeguard: if URL wrongly contains /sailor/regatta/ (old basePath bug), fix it
            if (absoluteUrl.indexOf('/sailor/regatta/') !== -1) {
                absoluteUrl = absoluteUrl.replace(/\/sailor\/regatta\//g, '/regatta/');
            }
            
            const modal = document.getElementById('regattaResultSheetModal');
            const iframe = document.getElementById('regattaResultSheetIframe');
            const modalContent = modal ? modal.querySelector('.regatta-result-sheet-modal-content') : null;
            
            if (!modal || !iframe) {
                console.error('Modal or iframe not found - opening in new tab');
                window.open(absoluteUrl, '_blank');
                return;
            }
            
            // Save context for Full/Podium nav. Use choice modal if populated; else parse URL; else keep existing.
            const choiceModal = document.getElementById('regattaChoiceModal');
            var rid = choiceModal ? (choiceModal.dataset.regattaId || '').trim() : '';
            var rname = choiceModal ? (choiceModal.dataset.regattaName || '').trim() : '';
            var cname = choiceModal ? (choiceModal.dataset.className || '').trim() : '';
            if (!rid && pageUrl) {
                var m = pageUrl.match(/regatta_id=([^&]+)/);
                if (m) rid = decodeURIComponent(m[1]);
                m = pageUrl.match(/[?&]class=([^&]+)/);
                if (m) cname = decodeURIComponent(m[1]);
            }
            if (rid || rname || cname) {
                var ctx = window._regattaResultBackContext || {};
                window._regattaResultBackContext = { regattaId: rid || ctx.regattaId || '', regattaName: rname || ctx.regattaName || rid || '', className: cname || ctx.className || '' };
            }
            // Close choice modal
            closeRegattaChoiceModal();
            
            // Show modal
            modal.style.display = 'block';
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
            
            // Show iframe
            iframe.style.display = 'block';
            iframe.style.visibility = 'visible';
            
            // Load page in iframe
            iframe.src = absoluteUrl;
            
            // Set view bar: expanded for full regatta results (view=expanded), else Lite
            var liteBtn = document.getElementById('btn-view-lite-modal');
            var expBtn = document.getElementById('btn-view-expanded-modal');
            var defaultExpanded = (pageUrl.indexOf('results.html') !== -1 && (pageUrl.indexOf('view=expanded') !== -1 || pageUrl.indexOf('view%3Dexpanded') !== -1));
            if (liteBtn && expBtn) {
                if (defaultExpanded) {
                    expBtn.classList.add('bar-view-active');
                    liteBtn.classList.remove('bar-view-active');
                } else {
                    liteBtn.classList.add('bar-view-active');
                    expBtn.classList.remove('bar-view-active');
                }
            }
            window._currentResultContentView = detectViewFromUrl(pageUrl);
            setTimeout(function() { updateResultSheetFlashState(); }, 100);
        }
        
        /**
         * Detect which result view a URL represents: 'class', 'full', or 'podium'
         */
        function detectViewFromUrl(url) {
            if (!url) return 'class';
            var s = String(url);
            if (s.indexOf('podium') !== -1 || s.indexOf('podium.html') !== -1) return 'podium';
            if (s.indexOf('class-results.html') !== -1) return 'class';
            if (s.indexOf('results.html') !== -1) return 'full';
            return 'class';
        }
        
        /**
         * Navigate to one of class, full, or podium view (toggle between the 3)
         */
        function navigateToResultView(view) {
            var ctx = window._regattaResultBackContext || {};
            var regattaId = ctx.regattaId || '';
            var className = ctx.className || '';
            var regattaName = ctx.regattaName || regattaId;
            if (!regattaId) return;
            var regattaSlug = typeof generateSlug === 'function' ? generateSlug(regattaName) : '';
            var classSlug = typeof generateSlug === 'function' ? generateSlug(className) : '';
            var url = '';
            if (view === 'full') {
                url = '/regatta/results.html?regatta_id=' + encodeURIComponent(regattaId) + (regattaSlug ? '&regatta_slug=' + encodeURIComponent(regattaSlug) : '') + '&view=expanded';
            } else if (view === 'podium' && className) {
                url = '/regatta/class/podium/podium.html?regatta_id=' + encodeURIComponent(regattaId) + '&class=' + encodeURIComponent(className) + (regattaSlug ? '&regatta_slug=' + encodeURIComponent(regattaSlug) : '') + (classSlug ? '&class_slug=' + encodeURIComponent(classSlug) : '');
            } else if (view === 'class' && className) {
                var cn = String(className).trim();
                if (!regattaId || !cn) return;
                url = '/regatta/class/class-results.html?regatta_id=' + encodeURIComponent(regattaId) + '&class=' + encodeURIComponent(cn) + (regattaSlug ? '&regatta_slug=' + encodeURIComponent(regattaSlug) : '') + (classSlug ? '&class_slug=' + encodeURIComponent(classSlug) : '') + '&v=20260323_final_fix';
            } else return;
            loadResultPageInIframe(url);
        }
        
        window._currentResultContentView = 'class';
        
        function updateResultSheetFlashState() {
            var classBtn = document.getElementById('btn-class-fleet-sheet-modal');
            var fullBtn = document.getElementById('btn-full-regatta-sheet-modal');
            var podiumBtn = document.getElementById('btn-podium-sheet-modal');
            var liteBtn = document.getElementById('btn-view-lite-modal');
            var expBtn = document.getElementById('btn-view-expanded-modal');
            [classBtn, fullBtn, podiumBtn, liteBtn, expBtn].forEach(function(b) { if (b) b.classList.remove('btn-flash-active'); });
            var c = window._currentResultContentView || 'class';
            var expanded = expBtn && expBtn.classList.contains('bar-view-active');
            var toFlash = [];
            if (liteBtn && !expanded) toFlash.push(liteBtn);
            if (expBtn && expanded) toFlash.push(expBtn);
            if (c === 'class' && classBtn) toFlash.push(classBtn);
            else if (c === 'full' && fullBtn) toFlash.push(fullBtn);
            else if (c === 'podium' && podiumBtn) toFlash.push(podiumBtn);
            requestAnimationFrame(function() {
                toFlash.forEach(function(b) { b.classList.add('btn-flash-active'); });
            });
        }
        
        /**
         * Load a result page into the existing result sheet iframe (switches view within modal)
         */
        function loadResultPageInIframe(pageUrl) {
            const engine = typeof window.resolveResultsEngine === 'function' ? window.resolveResultsEngine() : null;
            if (!engine) {
                console.error('Results engine missing');
                if (typeof window.showError === 'function') window.showError('Results engine not loaded');
                return;
            }
            const iframe = document.getElementById('regattaResultSheetIframe');
            if (!iframe) return;
            let absoluteUrl = pageUrl;
            if (!pageUrl.startsWith('http://') && !pageUrl.startsWith('https://') && !pageUrl.startsWith('//')) {
                var path = pageUrl.startsWith('/') ? pageUrl : '/' + pageUrl;
                absoluteUrl = window.location.origin + path;
            }
            if (absoluteUrl.indexOf('/sailor/regatta/') !== -1) absoluteUrl = absoluteUrl.replace(/\/sailor\/regatta\//g, '/regatta/');
            iframe.src = absoluteUrl;
            var liteBtn = document.getElementById('btn-view-lite-modal');
            var expBtn = document.getElementById('btn-view-expanded-modal');
            if (liteBtn) liteBtn.classList.add('bar-view-active');
            if (expBtn) expBtn.classList.remove('bar-view-active');
            window._currentResultContentView = detectViewFromUrl(pageUrl);
            setTimeout(function() { updateResultSheetFlashState(); }, 100);
        }
        
        
        function wireRegattaChoiceButtons() {
            const modal = document.getElementById('regattaChoiceModal');
            const classResultsBtn = document.getElementById('regattaChoiceClassResultsBtn');
            const classResultBtn = document.getElementById('regattaChoiceClassResultBtn');
            const fullRegattaBtn = document.getElementById('regattaChoiceFullRegattaBtn');
            const podiumBtn = document.getElementById('regattaChoicePodiumBtn');
            const classListEl = document.getElementById('regattaChoiceClassList');
            const step2RegattaName = document.getElementById('regattaChoiceStep2RegattaName');
            const step2Back = document.getElementById('regattaChoiceStep2Back');
            const step1Back = document.getElementById('regattaChoiceStep1Back');
            const step3ClassName = document.getElementById('regattaChoiceStep3ClassName');
            const fullClassResultBtn = document.getElementById('regattaChoiceFullClassResultBtn');
            const classPodiumBtn = document.getElementById('regattaChoiceClassPodiumBtn');
            const step3Back = document.getElementById('regattaChoiceStep3Back');
            if (!modal || !classResultsBtn || !fullRegattaBtn || !podiumBtn) {
                if (window.DEBUG_MODE) console.error('[DEBUG] wireRegattaChoiceButtons: Button elements not found');
                return;
            }
            
            // Remove any existing listeners by cloning buttons
            const newClassBtn = classResultsBtn.cloneNode(true);
            const newClassResultBtn = classResultBtn ? classResultBtn.cloneNode(true) : null;
            const newFullBtn = fullRegattaBtn.cloneNode(true);
            const newPodiumBtn = podiumBtn.cloneNode(true);
            classResultsBtn.parentNode.replaceChild(newClassBtn, classResultsBtn);
            if (classResultBtn && newClassResultBtn) classResultBtn.parentNode.replaceChild(newClassResultBtn, classResultBtn);
            fullRegattaBtn.parentNode.replaceChild(newFullBtn, fullRegattaBtn);
            podiumBtn.parentNode.replaceChild(newPodiumBtn, podiumBtn);
            
            // Step 1: Class Results (sailor - has class already)
            newClassBtn.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                const regattaId = modal.dataset.regattaId || '';
                const className = modal.dataset.className || '';
                const regattaName = modal.dataset.regattaName || '';
                
                // Check if this is a single-fleet regatta
                // If there's only one fleet/class, show full regatta results (same as "Full Regatta Results")
                try {
                    const entries = typeof getRegattaClassEntries === 'function' ? await getRegattaClassEntries(regattaId) : {};
                    const keys = Object.keys(entries || {});
                    
                    // If only one fleet/class exists, show full regatta results instead
                    if (keys.length === 1) {
                        closeRegattaChoiceModal();
                        navigateToFullRegattaResults(regattaId, regattaName);
                        return;
                    }
                } catch (err) {
                    console.error('Failed to check fleet count:', err);
                    // On error, proceed with class results navigation
                }
                
                closeRegattaChoiceModal();
                navigateToClassResults(regattaId, className, regattaName);
            });
            
            // Step 1: Class Result (search - show class list)
            if (newClassResultBtn) {
                newClassResultBtn.addEventListener('click', async function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const regattaId = modal.dataset.regattaId || '';
                    const regattaName = modal.dataset.regattaName || '';
                    if (!regattaId) return;
                    if (step2RegattaName) step2RegattaName.textContent = regattaName || 'Regatta';
                    if (classListEl) {
                        classListEl.innerHTML = '<div style="padding:12px;color:#666;">Loading classes…</div>';
                        showRegattaChoiceStep('regattaChoiceStep2');
                    }
                    try {
                        const entries = typeof getRegattaClassEntries === 'function' ? await getRegattaClassEntries(regattaId) : {};
                        const keys = Object.keys(entries || {});
                        if (keys.length === 1) {
                            var singleKey = keys[0];
                            var singleO = entries[singleKey];
                            var singleName = (singleO && singleO.name) ? singleO.name : singleKey;
                            modal.dataset.className = singleName;
                            if (step3ClassName) step3ClassName.textContent = singleName || 'Class';
                            showRegattaChoiceStep('regattaChoiceStep3');
                        } else {
                            const list = keys.map(function(key) {
                                const o = entries[key];
                                const name = (o && o.name) ? o.name : key;
                                const count = (o && o.entries != null) ? o.entries : '';
                                return '<button type="button" class="regatta-choice-class-item" data-class-name="' + (name || '').replace(/"/g, '&quot;') + '">' + (name || key).replace(/</g, '&lt;') + '<span class="entries">' + (count ? ' (' + count + ' entries)' : '') + '</span></button>';
                            }).join('');
                            if (classListEl) {
                                classListEl.innerHTML = list || '<div style="padding:12px;color:#666;">No classes found.</div>';
                                classListEl.querySelectorAll('.regatta-choice-class-item').forEach(function(btn) {
                                    btn.addEventListener('click', function(ev) {
                                        ev.preventDefault();
                                        ev.stopPropagation();
                                        var cn = btn.getAttribute('data-class-name') || btn.dataset.className || '';
                                        modal.dataset.className = cn;
                                        if (step3ClassName) step3ClassName.textContent = cn || 'Class';
                                        showRegattaChoiceStep('regattaChoiceStep3');
                                    });
                                });
                            }
                            showRegattaChoiceStep('regattaChoiceStep2');
                        }
                    } catch (err) {
                        console.error('Failed to load class entries:', err);
                        if (classListEl) classListEl.innerHTML = '<div style="padding:12px;color:#c00;">Unable to load classes. Try again.</div>';
                    }
                });
            }
            
            // Step 1: Full Regatta Results
            newFullBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const regattaId = modal.dataset.regattaId || '';
                const regattaName = modal.dataset.regattaName || '';
                closeRegattaChoiceModal();
                navigateToFullRegattaResults(regattaId, regattaName);
            });
            
            // Step 1: Class Podium (sailor)
            newPodiumBtn.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                const regattaId = modal.dataset.regattaId || '';
                const className = modal.dataset.className || '';
                const regattaName = modal.dataset.regattaName || '';
                
                // Check if this is a single-fleet regatta
                // If there's only one fleet/class, show full regatta results (same as "Full Regatta Results")
                try {
                    const entries = typeof getRegattaClassEntries === 'function' ? await getRegattaClassEntries(regattaId) : {};
                    const keys = Object.keys(entries || {});
                    
                    // If only one fleet/class exists, show full regatta results instead
                    if (keys.length === 1) {
                        closeRegattaChoiceModal();
                        navigateToFullRegattaResults(regattaId, regattaName);
                        return;
                    }
                } catch (err) {
                    console.error('Failed to check fleet count:', err);
                    // On error, proceed with class podium navigation
                }
                
                closeRegattaChoiceModal();
                navigateToClassPodium(regattaId, className, regattaName);
            });
            
            // Step 1: Go Back (close popup → back to page)
            if (step1Back) {
                const newStep1Back = step1Back.cloneNode(true);
                step1Back.parentNode.replaceChild(newStep1Back, step1Back);
                newStep1Back.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    closeRegattaChoiceModal();
                });
            }
            // Step 2: Go Back (→ step 1)
            if (step2Back) {
                const newStep2Back = step2Back.cloneNode(true);
                step2Back.parentNode.replaceChild(newStep2Back, step2Back);
                newStep2Back.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    showRegattaChoiceStep('regattaChoiceStep1');
                });
            }
            
            // Step 3: Full Class Result
            if (fullClassResultBtn) {
                const newFullClassBtn = fullClassResultBtn.cloneNode(true);
                fullClassResultBtn.parentNode.replaceChild(newFullClassBtn, fullClassResultBtn);
                newFullClassBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const regattaId = modal.dataset.regattaId || '';
                    const className = modal.dataset.className || '';
                    const regattaName = modal.dataset.regattaName || '';
                    closeRegattaChoiceModal();
                    navigateToClassResults(regattaId, className, regattaName);
                });
            }
            
            // Step 3: Class Podium Results
            if (classPodiumBtn) {
                const newClassPodiumBtn = classPodiumBtn.cloneNode(true);
                classPodiumBtn.parentNode.replaceChild(newClassPodiumBtn, classPodiumBtn);
                newClassPodiumBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const regattaId = modal.dataset.regattaId || '';
                    const className = modal.dataset.className || '';
                    const regattaName = modal.dataset.regattaName || '';
                    closeRegattaChoiceModal();
                    navigateToClassPodium(regattaId, className, regattaName);
                });
            }
            
            // Step 3: Go Back (→ step 2, class list)
            if (step3Back) {
                const newStep3Back = step3Back.cloneNode(true);
                step3Back.parentNode.replaceChild(newStep3Back, step3Back);
                newStep3Back.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    showRegattaChoiceStep('regattaChoiceStep2');
                });
            }
        }
        // Wire up regatta choice buttons - ensure it runs after DOM is ready
        function initRegattaChoiceButtons() {
            _dbg('[DEBUG] initRegattaChoiceButtons: Called');
            _dbg('[DEBUG] Document ready state:', document.readyState);
            
            // Try to wire immediately
            wireRegattaChoiceButtons();
            
            // Also try after a short delay in case elements aren't ready
            setTimeout(() => {
                _dbg('[DEBUG] initRegattaChoiceButtons: Retrying after delay');
                wireRegattaChoiceButtons();
            }, 100);
            
            // Also try on DOMContentLoaded if not already loaded
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    _dbg('[DEBUG] DOMContentLoaded fired - wiring buttons');
                    wireRegattaChoiceButtons();
                });
            }
        }
        
        // Initialize immediately if DOM is ready, otherwise wait
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initRegattaChoiceButtons);
        } else {
            initRegattaChoiceButtons();
        }
        
        /**
         * Open full regatta result sheet for a class (similar to regatta_viewer.html)
         * Uses the regatta's actual date instead of current date
         */
        async function openRegattaResultSheet(regattaId, className, regattaName) {
            const engine = typeof window.resolveResultsEngine === 'function' ? window.resolveResultsEngine() : null;
            if (!engine) {
                console.error('Results engine missing');
                if (typeof window.showError === 'function') window.showError('Results engine not loaded');
                return;
            }
            try {
                const API = window.API_BASE || window.location.origin || '';
                
                // Fetch regatta data
                const regattaDataResponse = await fetch(`${API}/api/regatta/${regattaId}?t=${Date.now()}`);
                if (!regattaDataResponse.ok) {
                    alert('Failed to load regatta data');
                    return;
                }
                
                const regattaData = await regattaDataResponse.json();
                
                if (!regattaData || regattaData.length === 0) {
                    alert('No regatta data found');
                    return;
                }
                
                const h0 = regattaData[0];
                
                // Fleet = broad category (Open, Windsurfer). Class = boat sailed (Sonnet, Bic).
                // Match block by: fleet_label, class_canonical, class_original, OR any result row's class.
const normalizeClass = (s) => (s || '').trim().replace(/_/g, ' ').replace(/\s+Fleet\s*$/i, '').toLowerCase();
                const compactClass = (s) => normalizeClass(s).replace(/[^a-z0-9]/g, '');
                const classEquiv = (a, b) => {
                    const na = normalizeClass(a), nb = normalizeClass(b);
                    if (na === nb) return true;
                    const ca = compactClass(a), cb = compactClass(b);
                    if (ca && cb && ca === cb) return true;
                    return na.indexOf(nb) === 0 || nb.indexOf(na) === 0 || (ca && cb && (ca.indexOf(cb) === 0 || cb.indexOf(ca) === 0));
                };
                const want = normalizeClass(className);
                const blockData = regattaData.find(r => {
                    if (!r.block_id) return false;
                    const blockClass = (r.class_canonical || r.class_original || r.fleet_label || '').trim();
                    const rowClass = (r.result_class_canonical || r.result_class_original || r.class_name || '').trim();
                    const normBlock = normalizeClass(blockClass);
                    const normRow = normalizeClass(rowClass);
                    return classEquiv(blockClass, className) || classEquiv(rowClass, className);
                });
                
                if (!blockData || !blockData.block_id) {
                    alert(`Fleet/class data not found for ${className}`);
                    return;
                }
                
                const blockId = blockData.block_id;
                let fleetResults = regattaData.filter(r => r.block_id === blockId && r.result_id);
                // For multi-class fleets (e.g. Open Fleet): filter to rows where class matches
                const blockNorm = normalizeClass(blockData.fleet_label || blockData.class_canonical || '');
                if (blockNorm !== want) {
                    fleetResults = fleetResults.filter(r => {
                        const rc = (r.result_class_canonical || r.result_class_original || r.class_name || '').trim();
                        return classEquiv(rc, className);
                    });
                }
                
                // "Results are X as at [date time]" = result data / time posted (use as_at_time when known)
                const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
                let dateTimeStr = 'Unknown';
                
                if (h0.as_at_time) {
                    const asAtDate = new Date(h0.as_at_time);
                    if (!isNaN(asAtDate.getTime())) {
                        const day = String(asAtDate.getDate()).padStart(2, '0');
                        const month = months[asAtDate.getMonth()];
                        const year = asAtDate.getFullYear();
                        const hours = String(asAtDate.getHours()).padStart(2, '0');
                        const minutes = String(asAtDate.getMinutes()).padStart(2, '0');
                        dateTimeStr = `${day} ${month} ${year} at ${hours}:${minutes}`;
                    }
                } else {
                    // Fallback: use regatta end_date or start_date if as_at_time not set
                    const regattaDateStr = h0.end_date || h0.start_date;
                    if (regattaDateStr) {
                        const d = new Date(regattaDateStr);
                        if (!isNaN(d.getTime())) {
                            const day = String(d.getDate()).padStart(2, '0');
                            const month = months[d.getMonth()];
                            const year = d.getFullYear();
                            dateTimeStr = `${day} ${month} ${year}`;
                        }
                    }
                }
                
                // Fleet = broader category (Windsurfer LT). Class = boat sailed (BIC, Windsurfer LT). When fleet_label is minority, use majority class for Fleet.
                const blockFleet = (blockData.fleet_label || '').trim();
                const blockClass = (blockData.class_canonical || blockData.class_original || '').trim();
                const fleetCount = fleetResults.filter(r => {
                    const rc = (r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim();
                    return normalizeClass(rc) === normalizeClass(blockFleet);
                }).length;
                const classCount = fleetResults.filter(r => {
                    const rc = (r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim();
                    return normalizeClass(rc) === normalizeClass(blockClass);
                }).length;
                let fleetName = (classCount > fleetCount && blockClass) ? blockClass : (blockFleet || blockClass || blockData.class_original || className);
                const counts = {};
                fleetResults.forEach(r => {
                    const rc = (r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim();
                    const key = normalizeClass(rc);
                    if (key) counts[key] = (counts[key] || 0) + 1;
                });
                const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
                if (best && best[1] > fleetCount) {
                    const firstMatch = fleetResults.find(r => normalizeClass((r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim()) === best[0]);
                    fleetName = (firstMatch && (firstMatch.result_class_canonical || firstMatch.result_class_original || firstMatch.class_name || firstMatch.class_canonical || firstMatch.class_original || '').trim()) || fleetName;
                }
                
                // Determine if series regatta
                const isSeries = h0.regatta_type === 'SERIES' || h0.regatta_number === 'S';
                const hostClubCode = h0.host_club_code || '';
                const hostClubName = h0.host_club_name || '';
                let hostClub = 'Unknown';
                
                if (isSeries) {
                    hostClub = hostClubName || hostClubCode || 'Unknown';
                } else {
                    if (hostClubCode && hostClubName) {
                        hostClub = `${hostClubCode} - ${hostClubName}`;
                    } else if (hostClubCode) {
                        hostClub = hostClubCode;
                    } else if (hostClubName) {
                        hostClub = hostClubName;
                    }
                }
                
                // SailingSA logo in dark navy box (replaces TimAdvisor)
                const apiBase = API;
                const sailingsaLogoUrl = (typeof window !== 'undefined' && window.location && window.location.origin ? window.location.origin : '') + '/assets/logos/sailingsa-with-flags-below-nobg.png';
                const sailingsaLogoHtml = '<div class="header-logo-wrap"><img src="' + sailingsaLogoUrl + '" alt="SailingSA" class="header-logo"></div>';
                
                // Club logo HTML (simplified version) - wrap in link when club has website
                let clubLogoHtml = '';
                if (hostClubCode) {
                    var hostClubWebMap = { 'HYC': 'https://www.hyc.co.za/', 'ZVYC': 'https://zvyc.co.za/', 'TSC': 'https://www.theewater.co.za/' };
                    var hostClubWeb = hostClubWebMap[String(hostClubCode).toUpperCase()] || '';
                    var imgTag = '<img id="clubLogoImg" alt="' + (hostClubCode || '') + '" class="header-club-logo" style="display:none;height:60px;width:auto;object-fit:contain">';
                    clubLogoHtml = (hostClubWeb ? '<a href="' + hostClubWeb + '" target="_blank" rel="noopener noreferrer" title="Visit club website">' + imgTag + '</a>' : imgTag) +
                        '<script>(function(){var img=document.getElementById("clubLogoImg");var ex=["jpg","png","jpeg"];var i=0;function next(){if(i<ex.length){img.src="' + apiBase + '/artwork/Club Logo/' + (hostClubCode || '') + '."+ex[i];img.onload=function(){img.style.display="block";};img.onerror=function(){i++;next();};}} next();})();<\/script>';
                }
                
                const regattaNameDisplay = h0.event_name || regattaName || 'Unknown Regatta';
                const statusText = (h0.result_status || 'Final').charAt(0).toUpperCase() + (h0.result_status || 'Final').slice(1);
                
                const racesSailed = blockData.races_sailed || 0;
                const discardCount = blockData.discard_count || 0;
                const toCount = Math.max(0, racesSailed - discardCount);
                const entriesCount = fleetResults.length;
                const scoringSystem = blockData.scoring_system || 'Appendix A';
                const classHint = String(blockData.class_canonical || blockData.class_original || fleetName || '').toLowerCase();
                const hasDf95Tokens = fleetResults.some(r => {
                    const scores = r.race_scores || {};
                    return Object.keys(scores).some(k => /^Q\d+$/i.test(k) || /^F\d+$/i.test(k));
                });
                const useDf95Columns = /df95/.test(classHint) || hasDf95Tokens;
                let sailedLine = `Sailed: ${racesSailed}, Discards: ${discardCount}, To count: ${toCount}, Entries: ${entriesCount}, Scoring system: ${scoringSystem}`;
                
                fleetResults.sort((a, b) => {
                    const rankA = parseInt(a.rank) || 9999;
                    const rankB = parseInt(b.rank) || 9999;
                    return rankA - rankB;
                });
                
                const hasCrew = fleetResults.some(r => r.crew_name && r.crew_name.trim() !== '');
                const hasBoatName = fleetResults.some(r => r.boat_name && r.boat_name.trim() !== '');
                const hasJibNo = fleetResults.some(r => r.jib_no && r.jib_no.trim() !== '');
                const hasBowNo = fleetResults.some(r => r.bow_no && r.bow_no.trim() !== '');
                const hasHullNo = fleetResults.some(r => r.hull_no && r.hull_no.trim() !== '');
                
                const raceColumns = [];
                if (isSeries && racesSailed === 3) {
                    raceColumns.push({ label: 'HYC', dataKey: 'R1' }, { label: 'ZVYC', dataKey: 'R2' }, { label: 'TSC', dataKey: 'R3' });
                } else if (useDf95Columns) {
                    let qMax = 0;
                    let fMax = 0;
                    fleetResults.forEach(r => {
                        const scores = r.race_scores || {};
                        Object.keys(scores).forEach(k => {
                            const qm = k.match(/^Q(\d+)$/i);
                            const fm = k.match(/^F(\d+)$/i);
                            if (qm) qMax = Math.max(qMax, parseInt(qm[1], 10));
                            if (fm) fMax = Math.max(fMax, parseInt(fm[1], 10));
                        });
                    });
                    for (let i = 1; i <= qMax; i++) {
                        const key = `Q${i}`;
                        const hasData = fleetResults.some(r => {
                            const scores = r.race_scores || {};
                            const v = scores[key];
                            return v != null && String(v).trim() !== '';
                        });
                        if (hasData) raceColumns.push({ label: key, dataKey: key });
                    }
                    for (let i = 1; i <= fMax; i++) {
                        const key = `F${i}`;
                        const hasData = fleetResults.some(r => {
                            const scores = r.race_scores || {};
                            const v = scores[key];
                            return v != null && String(v).trim() !== '';
                        });
                        if (hasData) raceColumns.push({ label: key, dataKey: key });
                    }
                    const qDiscards = discardCount > 0 ? Math.max(0, discardCount - 1) : 0;
                    const fDiscards = discardCount > 0 ? Math.min(1, discardCount) : 0;
                    sailedLine = `Results are after ${racesSailed} races with ${qDiscards} Qualifying Discards and ${fDiscards} Finals Discard. Scoring check: Total = sum(Q+F), Nett = Total - Disc.`;
                } else {
                    for (let i = 1; i <= racesSailed; i++) {
                        const raceKey = `R${i}`;
                        const hasData = fleetResults.some(r => {
                            const scores = r.race_scores || {};
                            const v = scores[raceKey];
                            return v != null && String(v).trim() !== '';
                        });
                        if (hasData) {
                            raceColumns.push({ label: raceKey, dataKey: raceKey });
                        }
                    }
                }
                
                let tableHeaders = '<th class="rank-col">Rank</th><th>Fleet</th><th>Class</th><th class="sail-col">Sail No</th>';
                if (hasBoatName) tableHeaders += '<th>Boat Name</th>';
                if (hasJibNo) tableHeaders += '<th>Jib No</th>';
                if (hasBowNo) tableHeaders += '<th>Bow No</th>';
                if (hasHullNo) tableHeaders += '<th>Hull No</th>';
                tableHeaders += '<th class="club-col">Club</th><th class="helm-col">Helm</th>';
                if (hasCrew) tableHeaders += '<th>Crew</th>';
                raceColumns.forEach(col => tableHeaders += `<th>${col.label}</th>`);
                tableHeaders += '<th>Total</th>';
                if (useDf95Columns) tableHeaders += '<th class="disc-col">Disc</th>';
                tableHeaders += '<th class="nett-col">Nett</th>';
                
                const formatRank = (rank) => {
                    if (!rank || isNaN(rank)) return rank;
                    const num = parseInt(rank, 10);
                    const v = num % 100;
                    if (v >= 10 && v <= 20) return num + 'th';
                    const d = num % 10;
                    if (d === 1) return num + 'st';
                    if (d === 2) return num + 'nd';
                    if (d === 3) return num + 'rd';
                    return num + 'th';
                };
                
                const escJs = (s) => (s == null ? '' : String(s)).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                const tableRows = fleetResults.map(r => {
                    const raceScores = r.race_scores || {};
                    const rankNum = parseInt(r.rank) || 0;
                    let medalClass = '';
                    if (rankNum === 1) medalClass = 'medal-gold';
                    else if (rankNum === 2) medalClass = 'medal-silver';
                    else if (rankNum === 3) medalClass = 'medal-bronze';
                    
                    const didNotRace = r.raced === false || r.raced === 0;
                    const strikeOutClass = didNotRace ? 'strike-out' : '';
                    const rowClasses = [medalClass, strikeOutClass].filter(c => c).join(' ');
                    const sid = (r.helm_sa_sailing_id != null ? String(r.helm_sa_sailing_id) : (r.helm_temp_id != null ? String(r.helm_temp_id) : ''));
                    const helmName = (r.helm_name || '').trim();
                    const hasClick = sid || helmName;
                    const rowClass = r.result_class_canonical || r.result_class_original || r.class_name || blockData.class_canonical || '';
                    const trAttrs = hasClick ? ` style="cursor:pointer" class="${rowClasses} sailor-row-clickable" data-sailor-id="${escJs(sid)}" data-helm-name="${escJs(helmName)}" data-club="${escJs(r.club_abbrev || r.club_raw || '')}" data-class="${escJs(rowClass)}" title="Click to view sailor profile"` : ` class="${rowClasses}"`;
                    
                    let row = `<tr${trAttrs}>
                        <td class="rank-col">${formatRank(r.rank)}</td>
                        <td>${fleetName || ''}</td>
                        <td>${formatClassCellHtml(r, rowClass)}</td>
                        <td class="sail-col">${r.sail_number || ''}</td>`;
                    if (hasBoatName) row += `<td>${r.boat_name || ''}</td>`;
                    if (hasJibNo) row += `<td>${r.jib_no || ''}</td>`;
                    if (hasBowNo) row += `<td>${r.bow_no || ''}</td>`;
                    if (hasHullNo) row += `<td>${r.hull_no || ''}</td>`;
                    const clubText = r.club_abbrev || r.club_raw || '';
                    const esc = (s) => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                    const clubCell = (r.club_slug && clubText) ? '<a href="/club/' + String(r.club_slug).replace(/"/g, '&quot;') + '" title="View club page">' + esc(clubText) + '</a>' : esc(clubText);
                    row += `<td class="club-col">${clubCell}</td>
                        <td class="helm-col">${r.helm_name || ''}</td>`;
                    if (hasCrew) row += `<td>${r.crew_name || ''}</td>`;
                    raceColumns.forEach(col => {
                        const displayKey = col.label;
                        const dataKey = isSeries && displayKey === 'HYC' ? 'R1' :
                                       isSeries && displayKey === 'ZVYC' ? 'R2' :
                                       isSeries && displayKey === 'TSC' ? 'R3' : col.dataKey;
                        const scoreRaw = raceScores[dataKey];
                        const score = (scoreRaw == null || scoreRaw === '') ? '' : String(scoreRaw);
                        const isDiscarded = score.startsWith('(') && score.endsWith(')');
                        const hasPenalty = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i.test(score);
                        let cellClass = '';
                        if (hasPenalty) {
                            cellClass = 'code';
                        } else if (isDiscarded) {
                            cellClass = 'disc';
                        } else if (score.trim() !== '') {
                            cellClass = 'score-counts';
                        }
                        row += `<td class="${cellClass}">${score}</td>`;
                    });
                    const totalVal = r.total_points_raw ?? '';
                    const nettVal = r.nett_points_raw ?? '';
                    const totalNum = Number(totalVal);
                    const nettNum = Number(nettVal);
                    const discVal = (Number.isFinite(totalNum) && Number.isFinite(nettNum)) ? (Math.round((totalNum - nettNum) * 10) / 10) : '';
                    row += `<td class="${didNotRace ? 'strike-out' : ''}">${totalVal}</td>`;
                    if (useDf95Columns) row += `<td class="disc-col ${didNotRace ? 'strike-out' : ''}">${discVal}</td>`;
                    row += `<td class="nett-col ${didNotRace ? 'strike-out' : ''}">${nettVal}</td>
                    </tr>`;
                    return row;
                }).join('');
                
                // Escape for HTML
                const escapedRegattaName = regattaNameDisplay.replace(/'/g, "\\'");
                const escapedFleetName = fleetName.replace(/'/g, "\\'");
                const escapedStatusText = statusText.replace(/'/g, "\\'");
                const escapedDateTimeStr = dateTimeStr.replace(/'/g, "\\'");
                const hubLabelRaw = (h0.blank_hub_news_badge_label != null && String(h0.blank_hub_news_badge_label).trim() !== '') ? String(h0.blank_hub_news_badge_label).trim() : '';
                const hubNewsLineHtml = hubLabelRaw
                    ? ('<div class="status-line hub-news-type" style="margin-top:10px;font-weight:600;color:#0f172a">SailingSA hub: ' +
                        hubLabelRaw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') + '</div>')
                    : '';
                
                const htmlContent = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Result Sheet - ' + fleetName + '</title>' +
                    '<style>body{background:#ffffff;color:#1a2750;font-family:system-ui,sans-serif;margin:0;padding:20px}' +
                    '.header{text-align:center;margin-bottom:30px;position:relative;display:flex;align-items:center;justify-content:center;border:2px solid #1a2750;border-radius:10px;padding:6px;background:#ffffff}' +
                    '.header-logo-wrap{position:absolute;left:12px;top:58%;transform:translateY(calc(-50% - 5px));display:inline-flex;align-items:center;justify-content:center;padding:1px}' +
                    '.header-logo-wrap .header-logo{position:static;height:40px;width:auto;display:block;object-fit:contain}' +
                    '.header-club-logo{position:absolute;right:6px;height:60px;width:auto;object-fit:contain}' +
                    '.regatta-name{font-size:24px;font-weight:bold;color:#1a2750;margin-bottom:8px}' +
                    '.host-club{font-size:18px;color:#1a2750;margin-bottom:8px}' +
                    '.status-line{font-size:14px;color:#1a2750;margin-top:20px}' +
                    '.class-header{font-size:20px;font-weight:bold;color:#1a2750;text-align:center;margin-top:40px;margin-bottom:20px;border:2px solid #1a2750;border-radius:10px;padding:15px;background:#ffffff}' +
                    '.sailed-line{font-size:12px;color:#1a2750;text-align:center;margin-top:10px;margin-bottom:0}' +
                    'table{border-collapse:collapse;width:100%;background:#ffffff;margin-top:20px}' +
                    'th,td{border:1px solid #1d294d;padding:8px;text-align:center}' +
                    'th{background:#e9eefb;color:#1a2750}' +
                    'td{color:#1a2750}' +
                    '.rank-col,.sail-col,.club-col,.helm-col,.nett-col{font-weight:bold}' +
                    '.score-counts{font-weight:bold}' +
                    '.medal-gold{background-color:#D4AF37}' +
                    '.medal-silver{background-color:#D7D7D7}' +
                    '.medal-bronze{background-color:#CE8946}' +
                    '.strike-out{text-decoration:line-through;opacity:0.6}' +
                    '.code{color:#d32f2f;font-weight:bold}' +
                    '.result-class-unmatched{color:#c62828;font-weight:500}' +
                    '.class-link-valid{color:#0000ee;text-decoration:underline;font-weight:600}' +
                    '.class-link-valid:visited{color:#0000ee}' +
                    '.disc{text-decoration:line-through;opacity:0.7}' +
                    'tr.sailor-row-clickable:hover{background-color:#e8ecf7}' +
                    '</style></head><body>' +
                    '<div class="header">' +
                    sailingsaLogoHtml +
                    clubLogoHtml +
                    '<div style="flex:1;text-align:center">' +
                    '<div class="regatta-name">' + escapedRegattaName + '</div>' +
                    '<div class="host-club">' + (h0.host_club_slug && hostClub !== 'Unknown' ? '<a href="/club/' + String(h0.host_club_slug).replace(/"/g, '&quot;') + '" title="View club page">' + hostClub.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') + '</a>' : hostClub) + '</div>' +
                    '<div class="status-line">Results are ' + escapedStatusText + ' as at ' + escapedDateTimeStr + '</div>' + hubNewsLineHtml +
                    '</div></div>' +
                    '<div class="class-header">' + escapedFleetName + '</div>' +
                    '<div class="sailed-line">' + sailedLine + '</div>' +
                    '<table><thead><tr>' + tableHeaders + '</tr></thead><tbody>' + tableRows + '</tbody></table>' +
                    '<script>document.addEventListener("click",function(e){var row=e.target&&e.target.closest?(e.target.closest("tr.sailor-row-clickable")||e.target.closest("tr[data-helm-name]")):null;if(!row)return;var sid=(row.getAttribute("data-sailor-id")||"").trim(),name=(row.getAttribute("data-helm-name")||"").trim(),club=(row.getAttribute("data-club")||"").trim(),cls=(row.getAttribute("data-class")||"").trim();if(!name&&!sid)return;(window.opener||window.parent).postMessage({type:"showSailorProfile",sid:sid,name:name,club:club,cls:cls},"*");if(window.opener)window.close()});<\/script>' +
                    '</body></html>';
                
                // On mobile (and some browsers), window.open returns null when popups are blocked.
                // Fall back to an in-page modal with an iframe so the result sheet still works.
                let popup = null;
                try {
                    popup = window.open('', 'resultSheet', 'width=1200,height=800,scrollbars=yes');
                } catch (e) {}
                if (popup && !popup.closed) {
                    popup.document.write(htmlContent);
                    popup.document.close();
                } else {
                    const modal = document.getElementById('regattaResultSheetModal');
                    const iframe = document.getElementById('regattaResultSheetIframe');
                    if (modal && iframe) {
                        const doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
                        if (doc) {
                            doc.open();
                            doc.write(htmlContent);
                            doc.close();
                            modal.style.display = 'block';
                        } else {
                            alert('Failed to load regatta result sheet: cannot write to modal.');
                        }
                    } else {
                        alert('Failed to load regatta result sheet: popup blocked and modal not available.');
                    }
                }
                
            } catch (error) {
                console.error('[DEBUG] openRegattaResultSheet: Error:', error);
                alert('Failed to load regatta result sheet: ' + error.message);
            }
        }
        
        // Make function globally available
        window.openRegattaResultSheet = openRegattaResultSheet;
        
        /**
         * Open full regatta result sheet (all classes/fleets) in popup or modal.
         */
        async function openFullRegattaResultSheet(regattaId, regattaName) {
            const engine = typeof window.resolveResultsEngine === 'function' ? window.resolveResultsEngine() : null;
            if (!engine) {
                console.error('Results engine missing');
                if (typeof window.showError === 'function') window.showError('Results engine not loaded');
                return;
            }
            try {
                const API = window.API_BASE || window.location.origin || '';
                const regattaDataResponse = await fetch(`${API}/api/regatta/${regattaId}?t=${Date.now()}`);
                if (!regattaDataResponse.ok) {
                    alert('Failed to load regatta data');
                    return;
                }
                const regattaData = await regattaDataResponse.json();
                if (!regattaData || regattaData.length === 0) {
                    alert('No regatta data found');
                    return;
                }
                const h0 = regattaData[0];
                const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
                let dateTimeStr = 'Unknown';
                if (h0.as_at_time) {
                    const asAtDate = new Date(h0.as_at_time);
                    if (!isNaN(asAtDate.getTime())) {
                        const day = String(asAtDate.getDate()).padStart(2, '0');
                        const month = months[asAtDate.getMonth()];
                        const year = asAtDate.getFullYear();
                        const hours = String(asAtDate.getHours()).padStart(2, '0');
                        const minutes = String(asAtDate.getMinutes()).padStart(2, '0');
                        dateTimeStr = `${day} ${month} ${year} at ${hours}:${minutes}`;
                    }
                } else {
                    const regattaDateStr = h0.end_date || h0.start_date;
                    if (regattaDateStr) {
                        const d = new Date(regattaDateStr);
                        if (!isNaN(d.getTime())) {
                            dateTimeStr = `${String(d.getDate()).padStart(2, '0')} ${months[d.getMonth()]} ${d.getFullYear()}`;
                        }
                    }
                }
                const isSeries = h0.regatta_type === 'SERIES' || h0.regatta_number === 'S';
                const hostClubCode = h0.host_club_code || '';
                const hostClubName = h0.host_club_name || '';
                let hostClub = 'Unknown';
                if (isSeries) {
                    hostClub = hostClubName || hostClubCode || 'Unknown';
                } else {
                    if (hostClubCode && hostClubName) hostClub = `${hostClubCode} - ${hostClubName}`;
                    else if (hostClubCode) hostClub = hostClubCode;
                    else if (hostClubName) hostClub = hostClubName;
                }
                const apiBase = API;
                const sailingsaLogoUrl2 = (typeof window !== 'undefined' && window.location && window.location.origin ? window.location.origin : '') + '/assets/logos/sailingsa-with-flags-below-nobg.png';
                const sailingsaLogoHtml2 = '<div class="header-logo-wrap"><img src="' + sailingsaLogoUrl2 + '" alt="SailingSA" class="header-logo"></div>';
                let clubLogoHtml = '';
                if (hostClubCode) {
                    var hostClubWebMap = { 'HYC': 'https://www.hyc.co.za/', 'ZVYC': 'https://zvyc.co.za/', 'TSC': 'https://www.theewater.co.za/' };
                    var hostClubWeb = hostClubWebMap[String(hostClubCode).toUpperCase()] || '';
                    var imgTag = '<img id="clubLogoImg" alt="' + (hostClubCode || '') + '" class="header-club-logo" style="display:none;height:60px;width:auto;object-fit:contain">';
                    clubLogoHtml = (hostClubWeb ? '<a href="' + hostClubWeb + '" target="_blank" rel="noopener noreferrer" title="Visit club website">' + imgTag + '</a>' : imgTag) +
                        '<script>(function(){var img=document.getElementById("clubLogoImg");var ex=["jpg","png","jpeg"];var i=0;function next(){if(i<ex.length){img.src="' + apiBase + '/artwork/Club Logo/' + (hostClubCode || '') + '."+ex[i];img.onload=function(){img.style.display="block";};img.onerror=function(){i++;next();};}} next();})();<\/script>';
                }
                const regattaNameDisplay = h0.event_name || regattaName || 'Unknown Regatta';
                const statusText = (h0.result_status || 'Final').charAt(0).toUpperCase() + (h0.result_status || 'Final').slice(1);
                const escapedRegattaName = regattaNameDisplay.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                const escapedStatusText = statusText.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                const escapedDateTimeStr = dateTimeStr.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                const escapedHostClub = hostClub.replace(/"/g, '&quot;');
                const hubLabelFull = (h0.blank_hub_news_badge_label != null && String(h0.blank_hub_news_badge_label).trim() !== '') ? String(h0.blank_hub_news_badge_label).trim() : '';
                const hubNewsLineHtmlFull = hubLabelFull
                    ? ('<div class="status-line hub-news-type" style="margin-top:10px;font-weight:600;color:#0f172a">SailingSA hub: ' +
                        hubLabelFull.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') + '</div>')
                    : '';
                
                function formatRank(rank) {
                    if (!rank || isNaN(rank)) return rank;
                    const num = parseInt(rank, 10);
                    const v = num % 100;
                    if (v >= 10 && v <= 20) return num + 'th';
                    const d = num % 10;
                    if (d === 1) return num + 'st';
                    if (d === 2) return num + 'nd';
                    if (d === 3) return num + 'rd';
                    return num + 'th';
                }
                
                // Group ALL rows by block_id (same as regatta_viewer.html - includes all data)
                const byBlock = {};
                regattaData.forEach(r => {
                    if (r.block_id) {
                        if (!byBlock[r.block_id]) byBlock[r.block_id] = [];
                        byBlock[r.block_id].push(r);
                    }
                });
                const blockIds = Object.keys(byBlock);
                if (blockIds.length === 0) {
                    alert('No fleet/class data found for this regatta.');
                    return;
                }
                
                // Fetch class entries (class name + entry count) for box below header
                let classEntries = {};
                try {
                    const entriesResponse = await fetch(`${API}/api/regatta/${encodeURIComponent(regattaId)}/class-entries?t=${Date.now()}`);
                    if (entriesResponse.ok) classEntries = await entriesResponse.json();
                } catch (e) { console.error('Class entries fetch:', e); }
                function formatClassName(key) {
                    const m = { 'dabchick':'Dabchick','ilca 4':'ILCA 4','ilca 4.7':'ILCA 4.7','ilca 6':'ILCA 6','mirror':'Mirror','open':'Open','optimist a':'Optimist A','optimist b':'Optimist B','rs tera':'RS Tera','topaz':'Topaz','topper 5.3':'Topper 5.3' };
                    return m[(key || '').toLowerCase()] || key;
                }
                const classesWithEntries = Object.entries(classEntries)
                    .filter(([k, d]) => { const e = typeof d === 'object' ? d.entries : d; return e && e > 0; })
                    .map(([k, d]) => typeof d === 'object' && d.name ? [k, d.name, d.entries] : [k, formatClassName(k), d])
                    .sort((a, b) => a[1].localeCompare(b[1]));
                const colsPerCol = Math.ceil(classesWithEntries.length / 3) || 1;
                const col1 = classesWithEntries.slice(0, colsPerCol);
                const col2 = classesWithEntries.slice(colsPerCol, colsPerCol * 2);
                const col3 = classesWithEntries.slice(colsPerCol * 2);
                const entriesTotal = h0.entries_total != null ? h0.entries_total : classesWithEntries.reduce((s, [, , c]) => s + (c || 0), 0);
                const helmsTotal = h0.helms_total || 0;
                const crewsTotal = h0.crews_total || 0;
                const sailorsTotal = h0.sailors_total != null ? h0.sailors_total : (helmsTotal + crewsTotal);
                const classEntriesBoxHtml = classesWithEntries.length > 0
                    ? '<div class="entries-box"><div class="entries-box-inner"><div class="entries-cols"><div>' + col1.map(([, name, count]) => '<div><strong>' + (name || '').replace(/</g, '&lt;') + '</strong> &gt; Entries = ' + count + '</div>').join('') + '</div><div>' + col2.map(([, name, count]) => '<div><strong>' + (name || '').replace(/</g, '&lt;') + '</strong> &gt; Entries = ' + count + '</div>').join('') + '</div><div>' + col3.map(([, name, count]) => '<div><strong>' + (name || '').replace(/</g, '&lt;') + '</strong> &gt; Entries = ' + count + '</div>').join('') + '</div></div><div class="entries-totals"><div><strong>Entries Total</strong> = ' + entriesTotal + '</div><div><strong>Sailors Total</strong> = ' + sailorsTotal + '</div></div></div></div>'
                    : '';
                
                let classSectionsHtml = '';
                blockIds.forEach(blockId => {
                    const items = byBlock[blockId];
                    const blockData = items[0];
                    // Filter to only rows with result_id (actual results) for this block, then sort by rank
                    const fleetResults = items.filter(r => r.result_id).sort((a, b) => (parseInt(a.rank) || 9999) - (parseInt(b.rank) || 9999));
                    // Skip blocks with no actual results
                    if (fleetResults.length === 0) return;
                    const normalizeClass = (s) => (s || '').trim().replace(/_/g, ' ').replace(/\s+Fleet\s*$/i, '').toLowerCase();
                    const blockFleet = (blockData.fleet_label || '').trim();
                    const blockClass = (blockData.class_canonical || blockData.class_original || '').trim();
                    const fleetCount = fleetResults.filter(r => {
                        const rc = (r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim();
                        return normalizeClass(rc) === normalizeClass(blockFleet);
                    }).length;
                    let fleetName = blockData.fleet_label || blockData.class_canonical || blockData.class_original || 'Fleet';
                    const counts = {};
                    fleetResults.forEach(r => {
                        const rc = (r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim();
                        const key = normalizeClass(rc);
                        if (key) counts[key] = (counts[key] || 0) + 1;
                    });
                    const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
                    if (best && best[1] > fleetCount) {
                        const firstMatch = fleetResults.find(r => normalizeClass((r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || '').trim()) === best[0]);
                        fleetName = (firstMatch && (firstMatch.result_class_canonical || firstMatch.result_class_original || firstMatch.class_name || firstMatch.class_canonical || firstMatch.class_original || '').trim()) || fleetName;
                    }
                    // Determine races_sailed from blockData or by checking all race_scores (like regatta_viewer)
                    let racesSailed = Math.max(0, Number(blockData.races_sailed || 0));
                    if (racesSailed === 0) {
                        // If races_sailed is 0, check all race_scores to find max race number
                        const allRaceKeys = [];
                        fleetResults.forEach(r => {
                            if (r.race_scores) {
                                Object.keys(r.race_scores).filter(k => k.startsWith('R')).forEach(k => {
                                    const num = parseInt(k.substring(1));
                                    if (!isNaN(num)) allRaceKeys.push(num);
                                });
                            }
                        });
                        if (allRaceKeys.length > 0) racesSailed = Math.max(...allRaceKeys);
                    }
                    const discardCount = blockData.discard_count || 0;
                    const toCount = Math.max(0, racesSailed - discardCount);
                    const entriesCount = fleetResults.length;
                    const scoringSystem = blockData.scoring_system || 'Appendix A';
                    const sailedLine = `Sailed: ${racesSailed}, Discards: ${discardCount}, To count: ${toCount}, Entries: ${entriesCount}, Scoring system: ${scoringSystem}`;
                    const hasCrew = fleetResults.some(r => r.crew_name && r.crew_name.trim() !== '');
                    const hasBoatName = fleetResults.some(r => r.boat_name && r.boat_name.trim() !== '');
                    const hasJibNo = fleetResults.some(r => r.jib_no && r.jib_no.trim() !== '');
                    const hasBowNo = fleetResults.some(r => r.bow_no && r.bow_no.trim() !== '');
                    const hasHullNo = fleetResults.some(r => r.hull_no && r.hull_no.trim() !== '');
                    // Build race columns: check ALL results to find all races with data
                    let raceColumns = [];
                    if (isSeries && racesSailed === 3) {
                        raceColumns = ['HYC', 'ZVYC', 'TSC'];
                    } else {
                        // Find all race keys (R1, R2, etc.) that have data in any result
                        const raceKeysSet = new Set();
                        fleetResults.forEach(r => {
                            if (r.race_scores) {
                                Object.keys(r.race_scores).filter(k => k.startsWith('R')).forEach(k => {
                                    const score = r.race_scores[k];
                                    if (score && score.toString().trim() !== '') raceKeysSet.add(k);
                                });
                            }
                        });
                        // Convert to sorted array (R1, R2, R3, ...)
                        const raceKeys = Array.from(raceKeysSet).map(k => {
                            const num = parseInt(k.substring(1));
                            return { key: k, num: isNaN(num) ? 0 : num };
                        }).sort((a, b) => a.num - b.num).map(x => x.key);
                        raceColumns = raceKeys;
                    }
                    let tableHeaders = '<th class="rank-col">Rank</th><th>Fleet</th><th>Class</th><th class="sail-col">Sail No</th>';
                    if (hasBoatName) tableHeaders += '<th>Boat Name</th>';
                    if (hasJibNo) tableHeaders += '<th>Jib No</th>';
                    if (hasBowNo) tableHeaders += '<th>Bow No</th>';
                    if (hasHullNo) tableHeaders += '<th>Hull No</th>';
                    tableHeaders += '<th class="club-col">Club</th><th class="helm-col">Helm</th>';
                    if (hasCrew) tableHeaders += '<th>Crew</th>';
                    raceColumns.forEach(r => { tableHeaders += '<th>' + r + '</th>'; });
                    tableHeaders += '<th>Total</th><th class="nett-col">Nett</th>';
                    const escJs = (s) => (s == null ? '' : String(s)).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const tableRows = fleetResults.map(r => {
                        const raceScores = r.race_scores || {};
                        const rankNum = parseInt(r.rank) || 0;
                        let medalClass = rankNum === 1 ? 'medal-gold' : rankNum === 2 ? 'medal-silver' : rankNum === 3 ? 'medal-bronze' : '';
                        const didNotRace = r.raced === false || r.raced === 0;
                        const strikeOutClass = didNotRace ? 'strike-out' : '';
                        const rowClasses = [medalClass, strikeOutClass].filter(c => c).join(' ');
                        const sid = (r.helm_sa_sailing_id != null ? String(r.helm_sa_sailing_id) : (r.helm_temp_id != null ? String(r.helm_temp_id) : ''));
                        const helmName = (r.helm_name || '').trim();
                        const hasClick = sid || helmName;
                        const rowClass = r.result_class_canonical || r.result_class_original || r.class_name || blockData.class_canonical || '';
                        const trAttrs = hasClick ? ' class="' + rowClasses + ' sailor-row-clickable" style="cursor:pointer" data-sailor-id="' + escJs(sid) + '" data-helm-name="' + escJs(helmName) + '" data-club="' + escJs(r.club_abbrev || r.club_raw || '') + '" data-class="' + escJs(rowClass) + '" title="Click to view sailor profile"' : ' class="' + rowClasses + '"';
                        let row = '<tr' + trAttrs + '><td class="rank-col">' + formatRank(r.rank) + '</td><td>' + (fleetName || '') + '</td><td>' + formatClassCellHtml(r, rowClass) + '</td><td class="sail-col">' + (r.sail_number || '') + '</td>';
                        if (hasBoatName) row += '<td>' + (r.boat_name || '') + '</td>';
                        if (hasJibNo) row += '<td>' + (r.jib_no || '') + '</td>';
                        if (hasBowNo) row += '<td>' + (r.bow_no || '') + '</td>';
                        if (hasHullNo) row += '<td>' + (r.hull_no || '') + '</td>';
                        const ct = r.club_abbrev || r.club_raw || '';
                        const e = (s) => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                        const cc = (r.club_slug && ct) ? '<a href="/club/' + String(r.club_slug).replace(/"/g, '&quot;') + '" title="View club page">' + e(ct) + '</a>' : e(ct);
                        row += '<td class="club-col">' + cc + '</td><td class="helm-col">' + (r.helm_name || '') + '</td>';
                        if (hasCrew) row += '<td>' + (r.crew_name || '') + '</td>';
                        raceColumns.forEach(displayKey => {
                            const dataKey = isSeries && displayKey === 'HYC' ? 'R1' : isSeries && displayKey === 'ZVYC' ? 'R2' : isSeries && displayKey === 'TSC' ? 'R3' : displayKey;
                            const scoreRaw = raceScores[dataKey];
                            const score = (scoreRaw == null || scoreRaw === '') ? '' : String(scoreRaw);
                            const isDiscarded = score.startsWith('(') && score.endsWith(')');
                            const hasPenalty = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i.test(score);
                            let cellClass = hasPenalty ? 'code' : isDiscarded ? 'disc' : (score.trim() !== '' ? 'score-counts' : '');
                            row += '<td class="' + cellClass + '">' + score + '</td>';
                        });
                        row += '<td class="' + (didNotRace ? 'strike-out' : '') + '">' + (r.total_points_raw ?? '') + '</td><td class="nett-col ' + (didNotRace ? 'strike-out' : '') + '">' + (r.nett_points_raw ?? '') + '</td></tr>';
                        return row;
                    }).join('');
                    const escapedFleetName = (fleetName || '').replace(/"/g, '&quot;');
                    classSectionsHtml += '<div class="class-header">' + escapedFleetName + ' Fleet</div><div class="sailed-line">' + sailedLine + '</div><table><thead><tr>' + tableHeaders + '</tr></thead><tbody>' + tableRows + '</tbody></table>';
                });
                
                const htmlContent = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Full Regatta - ' + escapedRegattaName + '</title>' +
                    '<style>body{background:#ffffff;color:#1a2750;font-family:system-ui,sans-serif;margin:0;padding:20px}' +
                    '.header{text-align:center;margin-bottom:30px;position:relative;display:flex;align-items:center;justify-content:center;border:2px solid #1a2750;border-radius:10px;padding:6px;background:#ffffff}' +
                    '.header-logo-wrap{position:absolute;left:12px;top:58%;transform:translateY(calc(-50% - 5px));display:inline-flex;align-items:center;justify-content:center;padding:1px}' +
                    '.header-logo-wrap .header-logo{position:static;height:40px;width:auto;display:block;object-fit:contain}.header-club-logo{position:absolute;right:6px;height:60px;width:auto;object-fit:contain}' +
                    '.regatta-name{font-size:24px;font-weight:bold;color:#1a2750;margin-bottom:8px}.host-club{font-size:18px;color:#1a2750;margin-bottom:8px}' +
                    '.status-line{font-size:14px;color:#1a2750;margin-top:20px}' +
                    '.entries-box{margin-bottom:24px;border:2px solid #1a2750;border-radius:10px;padding:14px 18px;background:#f8f9fa}' +
                    '.entries-box-inner{display:flex;gap:2rem;align-items:flex-start;flex-wrap:wrap}' +
                    '.entries-cols{display:flex;gap:2rem;flex:1;min-width:0}.entries-cols>div{font-size:14px;color:#1a2750;line-height:1.8}' +
                    '.entries-totals{text-align:right;font-size:14px;color:#1a2750;line-height:1.8;font-weight:600}' +
                    '.class-header{font-size:20px;font-weight:bold;color:#1a2750;text-align:center;margin-top:40px;margin-bottom:20px;border:2px solid #1a2750;border-radius:10px;padding:15px;background:#ffffff}' +
                    '.sailed-line{font-size:12px;color:#1a2750;text-align:center;margin-top:10px;margin-bottom:0}' +
                    'table{border-collapse:collapse;width:100%;background:#ffffff;margin-top:20px}th,td{border:1px solid #1d294d;padding:8px;text-align:center}' +
                    'th{background:#e9eefb;color:#1a2750}td{color:#1a2750}.rank-col,.sail-col,.club-col,.helm-col,.nett-col{font-weight:bold}.score-counts{font-weight:bold}' +
                    '.medal-gold{background-color:#D4AF37}.medal-silver{background-color:#D7D7D7}.medal-bronze{background-color:#CE8946}' +
                    '.strike-out{text-decoration:line-through;opacity:0.6}.code{color:#d32f2f;font-weight:bold}.result-class-unmatched{color:#c62828;font-weight:500}.class-link-valid{color:#0000ee;text-decoration:underline;font-weight:600}.disc{text-decoration:line-through;opacity:0.7}tr.sailor-row-clickable:hover{background-color:#e8ecf7}</style></head><body>' +
                    '<div class="header">' + sailingsaLogoHtml2 + clubLogoHtml +
                    '<div style="flex:1;text-align:center">' +
                    '<div class="regatta-name">' + escapedRegattaName + '</div><div class="host-club">' + (h0.host_club_slug ? '<a href="/club/' + String(h0.host_club_slug).replace(/"/g, '&quot;') + '" title="View club page">' + escapedHostClub + '</a>' : escapedHostClub) + '</div>' +
                    '<div class="status-line">Results are ' + escapedStatusText + ' as at ' + escapedDateTimeStr + '</div>' + hubNewsLineHtmlFull + '</div></div>' +
                    classEntriesBoxHtml +
                    classSectionsHtml +
                    '<script>document.addEventListener("click",function(e){var row=e.target&&e.target.closest?(e.target.closest("tr.sailor-row-clickable")||e.target.closest("tr[data-helm-name]")):null;if(!row)return;var sid=(row.getAttribute("data-sailor-id")||"").trim(),name=(row.getAttribute("data-helm-name")||"").trim(),club=(row.getAttribute("data-club")||"").trim(),cls=(row.getAttribute("data-class")||"").trim();if(!name&&!sid)return;(window.opener||window.parent).postMessage({type:"showSailorProfile",sid:sid,name:name,club:club,cls:cls},"*");if(window.opener)window.close()});<\/script>' +
                    '</body></html>';

                let popup = null;
                try {
                    popup = window.open('', 'fullRegattaSheet', 'width=1200,height=800,scrollbars=yes');
                } catch (e) {}
                if (popup && !popup.closed) {
                    popup.document.write(htmlContent);
                    popup.document.close();
                } else {
                    const modal = document.getElementById('regattaResultSheetModal');
                    const iframe = document.getElementById('regattaResultSheetIframe');
                    if (modal && iframe) {
                        const doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
                        if (doc) {
                            doc.open();
                            doc.write(htmlContent);
                            doc.close();
                            modal.style.display = 'block';
                        } else {
                            alert('Failed to load full regatta results: cannot write to modal.');
                        }
                    } else {
                        alert('Failed to load full regatta results: popup blocked and modal not available.');
                    }
                }
            } catch (error) {
                console.error('[DEBUG] openFullRegattaResultSheet: Error:', error);
                alert('Failed to load full regatta results: ' + error.message);
            }
        }
        
        window.openFullRegattaResultSheet = openFullRegattaResultSheet;
        
        /** Parse Regatta search: "Y Nationals 2025" -> { q: "Y Nationals", year: 2025 }. Only 19xx/20xx count as year so "2025" filters out 2024; "1365" stays as term (sail number). */
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
                    if ((window.searchMode || 'sailor') !== 'regatta') return;
                    var a = e.target && e.target.closest ? e.target.closest('#public-regattas-list a[href^="/regatta/"]') : null;
                    if (!a) return;
                    var href = a.getAttribute('href') || '';
                    var m = href.match(/^\/regatta\/([^?#]+)/);
                    _saSaveRegattaSearchState(m ? decodeURIComponent(m[1]) : '');
                } catch (_) {}
            }, true);
        }

            function _sortRegattasNewestFirst(list) {
                return (list || []).slice().sort(function(a, b) {
                    var liveA = !!a.is_live, liveB = !!b.is_live;
                    if (liveA !== liveB) return liveA ? -1 : 1;
                    var da = String(a.start_date || a.end_date || a.as_at_time || '').slice(0, 10);
                    var db = String(b.start_date || b.end_date || b.as_at_time || '').slice(0, 10);
                    if (da !== db) return db.localeCompare(da);
                    var na = parseInt(a.regatta_number, 10), nb = parseInt(b.regatta_number, 10);
                    if (!isNaN(na) && !isNaN(nb) && na !== nb) return nb - na;
                    return String(b.regatta_id || '').localeCompare(String(a.regatta_id || ''));
                });
            }
        function renderRegattasTable(regattas, searchQuery) {
            var publicRegattasList = document.getElementById('public-regattas-list');
            if (!publicRegattasList) return;
            if (!regattas || regattas.length === 0) {
                publicRegattasList.innerHTML = '<p>No regattas match.</p>';
                return;
            }
            regattas = _sortRegattasNewestFirst(regattas);
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
                    '.sa-home-regatta-card--live{background:#fff1e6;border-color:#f5ac86;}' +
                    '.sa-home-regatta-card--racing{background:#dcfce7;border-color:#86efac;}' +
                    '.sa-home-regatta-card--postponed{background:#fee2e2;border-color:#fca5a5;}' +
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
                    '.sa-home-regatta-single-class .sa-home-regatta-chip-text{font:800 11px/1 system-ui,-apple-system,sans-serif;color:#1e3a8a;white-space:nowrap;padding:0 2px;}' +
                    '.sa-home-regatta-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;padding:9px 14px;border-radius:6px;border:1px solid #a5d7de;background:#f9ffff;color:#0f6d7a;font-weight:900;font-size:12px;text-decoration:none;white-space:nowrap;min-width:126px;box-shadow:0 1px 0 rgba(15,109,122,.08);}' +
                    '.sa-home-regatta-btn--live{background:#ea580c;border-color:#c2410c;color:#fff;}' +
                    '.sa-home-regatta-btn--racing{background:#15803d;border-color:#166534;color:#fff;}' +
                    '.sa-home-regatta-btn--postponed{background:#b91c1c;border-color:#991b1b;color:#fff;}' +
                    '.sa-home-regatta-btn--live .sa-home-regatta-btn-ico,.sa-home-regatta-btn--racing .sa-home-regatta-btn-ico,.sa-home-regatta-btn--postponed .sa-home-regatta-btn-ico{color:#fff;}' +
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
            var liveN = parents.filter(function(r) { return !!r.is_live; }).length;
            var labelText = searchQuery
                ? 'Regatta Search for "<span style="color:#c00;font-weight:700;">' + esc(searchQuery) + '</span>" = Results (' + count + ')'
                : (liveN
                    ? 'All Regattas — live races first (' + count + ')'
                    : 'All Regattas — newest first (' + count + ')');

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
                var boardSt = String(r.live_board_status || '').toUpperCase();
                var isLiveWindow = !!r.is_live;
                if (isLiveWindow && boardSt === 'POSTPONED') card.classList.add('sa-home-regatta-card--postponed');
                else if (isLiveWindow && boardSt === 'RACING') card.classList.add('sa-home-regatta-card--racing');
                else if (isLiveWindow) card.classList.add('sa-home-regatta-card--live');
                if (isLiveWindow) {
                    card.setAttribute('data-live-board-tint-rid', rid);
                    card.setAttribute('data-live-board-page-status', boardSt || 'LIVE');
                }

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

                // Single class: class logo left of Full Results / status → parent URL (no fleet bar).
                // kids.length===1 (fleet child) OR sole raced class on flat parent (e.g. Lipton J22).
                var soleName = String(r.sole_class_name || '').trim();
                var soleLogo = String(r.sole_class_logo_url || '').trim();
                if (kids.length === 1 || (kids.length === 0 && (soleName || soleLogo))) {
                    var only = kids.length === 1 ? kids[0] : null;
                    var onlyChildLabel = only
                        ? renderChildLabel(only.search_label || only.fleet_label || only.event_name || only.name, parentLabel)
                        : soleName;
                    var onlyParts = getChipLabelParts(onlyChildLabel);
                    var onlyName = onlyParts.text || renderChipLabel(onlyChildLabel) || soleName || 'Class';
                    var onlyMaster = regattaChipMasterClassLogo(onlyName) || soleLogo || (only && only.logo_url) || '';
                    var onlyChildId = only ? ((only.regatta_id != null ? only.regatta_id : only.id) + '') : rid;
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
                    singleLogo.dataset.saLogoSrc = onlyMaster || '';
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
                            // Flat sole-class: show text name if logo missing.
                            singleLogo.style.display = 'none';
                            if (!singleClass.querySelector('.sa-home-regatta-chip-text')) {
                                var t = document.createElement('span');
                                t.className = 'sa-home-regatta-chip-text';
                                t.textContent = onlyName;
                                singleClass.appendChild(t);
                            }
                        } catch (_) {}
                    };
                    singleClass.appendChild(singleLogo);
                    if (onlyMaster) {
                        singleLogo.src = onlyMaster;
                        singleLogo.style.visibility = '';
                    } else {
                        var t0 = document.createElement('span');
                        t0.className = 'sa-home-regatta-chip-text';
                        t0.textContent = onlyName;
                        singleClass.appendChild(t0);
                    }
                    actions.appendChild(singleClass);
                }

                var fullBtn = document.createElement('a');
                fullBtn.className = 'sa-home-regatta-btn';
                fullBtn.href = parentResultsHref;
                var btnLabel = 'Full Results';
                if (isLiveWindow && boardSt === 'POSTPONED') {
                    fullBtn.className = 'sa-home-regatta-btn sa-home-regatta-btn--postponed';
                    btnLabel = 'Postponed';
                } else if (isLiveWindow && boardSt === 'RACING') {
                    fullBtn.className = 'sa-home-regatta-btn sa-home-regatta-btn--racing';
                    btnLabel = 'Racing';
                } else if (isLiveWindow) {
                    fullBtn.className = 'sa-home-regatta-btn sa-home-regatta-btn--live';
                    btnLabel = 'Live Event';
                }
                if (isLiveWindow) {
                    fullBtn.setAttribute('data-live-board-rid', rid);
                    fullBtn.setAttribute('data-live-board-status', boardSt || 'LIVE');
                }
                var btnIco = document.createElement('span');
                btnIco.className = 'sa-home-regatta-btn-ico';
                btnIco.appendChild(svgIcon('trophy'));
                fullBtn.appendChild(btnIco);
                fullBtn.appendChild(document.createTextNode(btnLabel));
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
            try { _saHomeLiveBoardPollStart(); } catch (_) {}
        }
        function _saHomeLiveBoardApply(rid, status) {
            var st = String(status || 'LIVE').toUpperCase();
            if (st !== 'LIVE' && st !== 'RACING' && st !== 'POSTPONED') st = 'LIVE';
            var cards = document.querySelectorAll('.sa-home-regatta-card[data-live-board-tint-rid="' + rid + '"]');
            cards.forEach(function(card) {
                card.classList.remove('sa-home-regatta-card--live', 'sa-home-regatta-card--racing', 'sa-home-regatta-card--postponed');
                if (st === 'POSTPONED') card.classList.add('sa-home-regatta-card--postponed');
                else if (st === 'RACING') card.classList.add('sa-home-regatta-card--racing');
                else card.classList.add('sa-home-regatta-card--live');
                card.setAttribute('data-live-board-page-status', st);
            });
            var btns = document.querySelectorAll('.sa-home-regatta-btn[data-live-board-rid="' + rid + '"]');
            btns.forEach(function(btn) {
                btn.classList.remove('sa-home-regatta-btn--live', 'sa-home-regatta-btn--racing', 'sa-home-regatta-btn--postponed');
                var label = 'Live Event';
                if (st === 'POSTPONED') { btn.classList.add('sa-home-regatta-btn--postponed'); label = 'Postponed'; }
                else if (st === 'RACING') { btn.classList.add('sa-home-regatta-btn--racing'); label = 'Racing'; }
                else { btn.classList.add('sa-home-regatta-btn--live'); }
                btn.setAttribute('data-live-board-status', st);
                var ico = btn.querySelector('.sa-home-regatta-btn-ico');
                while (btn.firstChild) btn.removeChild(btn.firstChild);
                if (ico) btn.appendChild(ico);
                btn.appendChild(document.createTextNode(label));
            });
        }
        var _saHomeLiveBoardTimer = null;
        function _saHomeLiveBoardPollStart() {
            if (_saHomeLiveBoardTimer) {
                try { clearInterval(_saHomeLiveBoardTimer); } catch (_) {}
                _saHomeLiveBoardTimer = null;
            }
            var nodes = document.querySelectorAll('.sa-home-regatta-card[data-live-board-tint-rid]');
            if (!nodes || !nodes.length) return;
            var rids = [];
            nodes.forEach(function(n) {
                var rid = n.getAttribute('data-live-board-tint-rid') || '';
                if (rid && rids.indexOf(rid) < 0) rids.push(rid);
            });
            if (!rids.length) return;
            function tick() {
                rids.forEach(function(rid) {
                    fetch('/api/regatta/' + encodeURIComponent(rid) + '/live-board-status', { cache: 'no-store' })
                        .then(function(r) { return r.ok ? r.json() : null; })
                        .then(function(j) {
                            if (!j) return;
                            var st = String(j.status || j.live_board_status || '').toUpperCase();
                            if (st) _saHomeLiveBoardApply(rid, st);
                        })
                        .catch(function() {});
                });
            }
            tick();
            _saHomeLiveBoardTimer = setInterval(tick, 8000);
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
            if ((window.searchMode || 'sailor') !== 'regatta') {
                _clearPublicRegattasList();
                return;
            }
            var sailorSearchInput = document.getElementById('sailor-search-input');
            var regattaInput = document.getElementById('temp-landing-regatta-input');
            var useRegattaInput = !!(regattaInput && (document.activeElement === regattaInput || regattaInput.offsetParent !== null));
            var q = useRegattaInput
                ? (regattaInput.value || '').trim()
                : (sailorSearchInput ? sailorSearchInput.value.trim() : '');
            var publicRegattasList = document.getElementById('public-regattas-list');
            if (!publicRegattasList) return;

            // Empty query → first ~30 instant, then background fill to full parent list (fuzzy cache)
            if (!q || q.toLowerCase() === 'all') {
                publicRegattasList.innerHTML = '<p>Loading…</p>';
                try {
                    if (!_regattaSearchAllCache) {
                        var first = typeof getRegattas === 'function'
                            ? await getRegattas({ limit: 30 })
                            : [];
                        if (!Array.isArray(first)) first = [];
                        if ((window.searchMode || 'sailor') !== 'regatta') {
                            _clearPublicRegattasList();
                            return;
                        }
                        renderRegattasTable(first, q.toLowerCase() === 'all' ? 'all' : '');
                        // Background: load rest (~390) and replace list + populate fuzzy cache
                        (async function () {
                            try {
                                var all = typeof getRegattas === 'function'
                                    ? await getRegattas({ limit: 400 })
                                    : [];
                                if (!Array.isArray(all)) all = [];
                                _regattaSearchAllCache = all;
                                if ((window.searchMode || 'sailor') !== 'regatta') return;
                                var si = document.getElementById('sailor-search-input');
                                var ri = document.getElementById('temp-landing-regatta-input');
                                var useRi = !!(ri && (document.activeElement === ri || ri.offsetParent !== null));
                                var qNow = useRi
                                    ? (ri.value || '').trim()
                                    : (si ? si.value.trim() : '');
                                if (!qNow || qNow.toLowerCase() === 'all') {
                                    renderRegattasTable(all, qNow.toLowerCase() === 'all' ? 'all' : '');
                                }
                            } catch (bgErr) {
                                console.error('[DEBUG] regatta background fill:', bgErr);
                            }
                        })();
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
                var params = { q: (q || '').trim(), limit: 400 };
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
        /**
         * Load regattas for public view — only when Regatta pill is active.
         */
        async function loadPublicRegattas() {
            if ((window.searchMode || 'sailor') !== 'regatta') {
                _clearPublicRegattasList();
                return;
            }
            await applyRegattaFilter();
        }
        
        /**
         * Show Sailor Stats Modal
         */
        async function showSailorStats(sasId, fullName, event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            const modal = document.getElementById('sailorStatsModal');
            const modalContent = document.getElementById('sailorStatsContent');
            
            if (!modal || !modalContent) {
                console.error('[DEBUG] showSailorStats: Modal elements not found');
                return;
            }
            
            // Show loading state
            modalContent.innerHTML = '<div style="padding: 20px; text-align: center;">Loading sailor statistics...</div>';
            modal.style.display = 'block';
            
            try {
                const API = window.API_BASE || window.location.origin || '';
                
                // Fetch member data, results, and roles in parallel
                const [memberResponse, resultsResponse, rolesResponse] = await Promise.all([
                    fetch(`${API}/api/search?sas_id=${encodeURIComponent(sasId)}`).catch(() => null),
                    fetch(`${API}/api/member/${encodeURIComponent(sasId)}/results`).catch(() => null),
                    fetch(`${API}/api/member/${encodeURIComponent(sasId)}/roles`).catch(() => null)
                ]);
                
                const members = memberResponse?.ok ? await memberResponse.json() : [];
                const resultsData = resultsResponse?.ok ? await resultsResponse.json() : { results: [] };
                const roles = rolesResponse?.ok ? await rolesResponse.json() : [];
                
                const m = (Array.isArray(members) ? members[0] : null) || {};
                const results = resultsData.results || [];
                
                // Calculate sailing duration
                let sailingDuration = '0 years & 0 months';
                if (results.length) {
                    const dateStrings = results
                        .map(r => r.start_date || r.end_date)
                        .filter(d => d && d !== 'N/A');
                    if (dateStrings.length) {
                        const oldestStr = dateStrings.reduce((min, d) => (min && min <= d ? min : d), null);
                        const oldest = new Date(oldestStr);
                        if (!isNaN(oldest.getTime())) {
                            const now = new Date();
                            let years = now.getFullYear() - oldest.getFullYear();
                            let months = now.getMonth() - oldest.getMonth();
                            if (months < 0) {
                                years -= 1;
                                months += 12;
                            }
                            sailingDuration = `${years} years & ${months} months`;
                        }
                    }
                }
                
                // Calculate regatta count and race count
                const regattaEventKeys = new Set();
                let raceCount = 0;
                const regattaRaceSeen = {};
                results.forEach(r => {
                    if (isMemberResultSeriesRow(r) || !shouldIncludeMemberResultRow(r, results)) return;
                    if (!isMemberYouthSubFleetBlock(r.block_id)) {
                        const eventKey = memberResultCareerEventKey(r);
                        if (eventKey) regattaEventKeys.add(eventKey);
                    }
                    if (shouldCountMemberResultRaces(r, regattaRaceSeen)) {
                        if (r.races_sailed && typeof r.races_sailed === 'number') {
                            raceCount += r.races_sailed;
                        } else if (r.race_scores) {
                            Object.keys(r.race_scores).forEach(k => {
                                if (/^R\d+$/i.test(k)) {
                                    const score = r.race_scores[k];
                                    if (typeof score === 'number' || (typeof score === 'string' && !/^(DNC|DNS|DNF|DSQ|RET|OCS|BFD|UFD|SCP|RDG|DPI)$/i.test(score))) {
                                        raceCount++;
                                    }
                                }
                            });
                        }
                    }
                });
                const regattaCount = regattaEventKeys.size;
                
                // Calculate class stats and medals
                const classStats = {};
                const classMedals = {};
                const classRegattaIds = {};
                const classRegattaRaceSeen = {};
                const classLastDates = {};
                
                // Normalize class name function
                const normalizeClassName = (name) => {
                    if (!name) return '';
                    let normalized = name.trim();
                    if (/^OPTIMIST\s*(A|B|C)?$/i.test(normalized)) {
                        const match = normalized.match(/^OPTIMIST\s*(A|B|C)?$/i);
                        const fleet = match && match[1] ? match[1].toUpperCase() : 'A';
                        normalized = `Optimist ${fleet}`;
                    } else if (/^optimist\s*(a|b|c)?$/i.test(normalized)) {
                        const match = normalized.match(/^optimist\s*(a|b|c)?$/i);
                        const fleet = match && match[1] ? match[1].toUpperCase() : 'A';
                        normalized = `Optimist ${fleet}`;
                    }
                    normalized = normalized.replace(/\s+fleet\s*$/i, '').trim();
                    return normalized;
                };
                
                results.forEach(r => {
                    if (isMemberResultSeriesRow(r) || !shouldIncludeMemberResultRow(r, results)) return;
                    
                    const rawClassName = (r.class_canonical || r.class_original || '').trim();
                    const className = normalizeClassName(rawClassName);
                    if (!className) return;
                    
                    if (!classStats[className]) {
                        classStats[className] = { rg: 0, r: 0, medals: { gold: 0, silver: 0, bronze: 0 } };
                        classMedals[className] = { gold: 0, silver: 0, bronze: 0 };
                        classRegattaIds[className] = new Set();
                        classRegattaRaceSeen[className] = {};
                        classLastDates[className] = null;
                    }
                    
                    if (r.regatta_id && !isMemberYouthSubFleetBlock(r.block_id) && !classRegattaIds[className].has(r.regatta_id)) {
                        classStats[className].rg++;
                        classRegattaIds[className].add(r.regatta_id);
                    }
                    
                    const regattaDate = r.end_date || r.start_date;
                    if (regattaDate) {
                        const date = new Date(regattaDate);
                        if (!isNaN(date.getTime())) {
                            if (!classLastDates[className] || date > classLastDates[className]) {
                                classLastDates[className] = date;
                            }
                        }
                    }
                    
                    const classRaceKey = memberResultCareerEventKey(r) || '';
                    if (!isMemberYouthSubFleetBlock(r.block_id) && classRaceKey && !classRegattaRaceSeen[className][classRaceKey]) {
                        classRegattaRaceSeen[className][classRaceKey] = true;
                        if (r.race_scores && typeof r.race_scores === 'object') {
                            Object.keys(r.race_scores).forEach(k => {
                                if (/^R\d+$/i.test(k)) {
                                    const score = r.race_scores[k];
                                    if (score !== null && score !== undefined && score !== '') {
                                        classStats[className].r++;
                                    }
                                }
                            });
                        } else if (r.races_sailed && typeof r.races_sailed === 'number' && r.races_sailed > 0) {
                            classStats[className].r += r.races_sailed;
                        }
                    }
                    
                    let rankNum = null;
                    if (r.rank && typeof r.rank === 'number') {
                        rankNum = r.rank;
                    } else if (r.rank && typeof r.rank === 'string') {
                        const match = String(r.rank).match(/^\s*([0-9]+)/);
                        if (match) rankNum = Number(match[1]);
                    }
                    if (rankNum === 1) {
                        classStats[className].medals.gold++;
                        classMedals[className].gold++;
                    } else if (rankNum === 2) {
                        classStats[className].medals.silver++;
                        classMedals[className].silver++;
                    } else if (rankNum === 3) {
                        classStats[className].medals.bronze++;
                        classMedals[className].bronze++;
                    }
                });
                
                // Get rankings from member data
                let rankings = m.rankings || [];
                
                // Get club and age - prefer birth year with reference year for consistent season age
                const ageRefYear = (typeof window.AGE_REFERENCE_YEAR === 'number' && window.AGE_REFERENCE_YEAR > 1900) ? window.AGE_REFERENCE_YEAR : 2025;
                let club = m.club || m.primary_club || m.club_1 || '';
                let age = '';
                if (m.born !== undefined && m.born !== null && m.born !== '' && !isNaN(m.born)) {
                    age = ageRefYear - parseInt(m.born);
                } else if (m.year_of_birth !== undefined && m.year_of_birth !== null && m.year_of_birth !== '' && !isNaN(m.year_of_birth)) {
                    age = ageRefYear - parseInt(m.year_of_birth);
                } else if (m.age !== undefined && m.age !== null && m.age !== '' && !isNaN(m.age)) {
                    age = parseInt(m.age);
                }
                
                // Build summary object
                const summary = {
                    total_rg: regattaCount,
                    total_r: raceCount,
                    class_stats: classStats
                };
                
                // Build ranking map
                const rankingMap = {};
                rankings.forEach(r => {
                    if (r.class_code) {
                        const key = r.class_code.trim();
                        rankingMap[key] = r;
                        rankingMap[key.toLowerCase()] = r;
                        if (key.toLowerCase().includes('fleet')) {
                            const withoutFleet = key.toLowerCase().replace(/\s*fleet\s*$/i, '').trim();
                            rankingMap[withoutFleet] = r;
                        } else {
                            rankingMap[key.toLowerCase() + ' fleet'] = r;
                        }
                    }
                });
                
                // Build header
                let headerName = fullName;
                if (club) {
                    headerName += ` (${club})`;
                }
                let ageDisplay = '';
                if (age && !isNaN(age) && parseInt(age) > 0) {
                    const ageNum = parseInt(age);
                    ageDisplay = ` Age ${ageNum}/${ageNum + 1} Yrs`;
                }
                
                // Build stats content — Lite view (same structure as search.html, expandable by popup)
                let html = `
                    <h2 style="margin-top: 0; color: #1e3a8a; font-size: 22px; font-weight: 700; line-height: 1.3; word-wrap: break-word;">
                        Sailor Stats: ${headerName}${ageDisplay}
                    </h2>
                    <p style="margin: 4px 0 12px 0; font-size: 12px; color: #666;">Lite view — expand any class with <strong>Expanded View</strong> for full table.</p>
                    <div class="sailor-stats-section">
                        <h3 style="font-size: 18px; margin: 15px 0 10px 0;">Career Summary</h3>
                        <div class="sailor-stats-row">
                            <span class="sailor-stats-label">Sailing:</span>
                            <span class="sailor-stats-value">${sailingDuration}</span>
                        </div>
                        <div class="sailor-stats-row">
                            <span class="sailor-stats-label">Total Regattas:</span>
                            <span class="sailor-stats-value">${summary.total_rg || 0}</span>
                        </div>
                        <div class="sailor-stats-row">
                            <span class="sailor-stats-label">Total Races:</span>
                            <span class="sailor-stats-value">${summary.total_r || 0}</span>
                        </div>
                    </div>
                `;
                
                // Add class breakdown
                if (summary.class_stats && Object.keys(summary.class_stats).length > 0) {
                    html += `
                        <div class="sailor-stats-section">
                            <h3 style="font-size: 18px; margin: 15px 0 10px 0;">Breakdown by Class</h3>
                    `;
                    
                    const classEntries = Object.entries(summary.class_stats).sort((a, b) => {
                        const dateA = classLastDates[a[0]] || new Date(0);
                        const dateB = classLastDates[b[0]] || new Date(0);
                        return dateB - dateA;
                    });
                    
                    classEntries.forEach(([className, stats]) => {
                        const medals = stats.medals || { gold: 0, silver: 0, bronze: 0 };
                        const totalMedals = medals.gold + medals.silver + medals.bronze;
                        let medalsText = '';
                        if (totalMedals > 0) {
                            medalsText = `🥇${medals.gold} 🥈${medals.silver} 🥉${medals.bronze}`;
                        }
                        
                        const standingId = `standing-${className.replace(/\s+/g, '-').toLowerCase()}-${sasId}`;
                        const regattaCount = stats.rg || 0;
                        const raceCount = stats.r || 0;
                        
                        html += `
                            <div class="sailor-stats-class-line">
                                <span class="sailor-stats-label" style="font-weight: 700;">${className}:</span>
                                <span class="sailor-stats-value">${regattaCount} regattas, ${raceCount} races</span>
                                <span class="separator-dot" style="color: #666;">·</span>
                                <span id="${standingId}" class="standing-box" style="background: #e3f2fd; border: 1px solid #90caf9; border-radius: 3px; padding: 2px 4px; font-weight: 600; color: #1976d2; font-size: 11px;">Standing: …</span>
                                ${medalsText ? `<span class="separator-dot" style="color: #666;">·</span><span class="medal-box" style="background: #fff3e0; border: 1px solid #ffb74d; border-radius: 3px; padding: 2px 4px; font-weight: 600; color: #e65100; font-size: 11px;">${medalsText}</span>` : ''}
                            </div>
                        `;
                        
                        // Fetch rank - use /api/standings/db for all classes
                        const apiClassName = className.replace(/\s+fleet\s*$/i, '').trim();
                        const sasIdStr = String(sasId).trim();
                        const formatRank = (rank) => {
                            if (rank == null || rank === '') return 'N/A';
                            const num = parseInt(rank, 10);
                            if (isNaN(num)) return 'N/A';
                            const v = num % 100;
                            if (v >= 10 && v <= 20) return num + 'th';
                            const d = num % 10;
                            if (d === 1) return num + 'st';
                            if (d === 2) return num + 'nd';
                            if (d === 3) return num + 'rd';
                            return num + 'th';
                        };
                        function applyStanding(rankPosition, totalSailors, notRanked, rankingScore, hasParticipation) {
                            const el = document.getElementById(standingId);
                            if (!el) return;
                            var scorePart = (rankingScore != null && rankingScore !== '' && !isNaN(Number(rankingScore))) ? ' (' + Math.round(Number(rankingScore)) + ')' : '';
                            if (rankPosition && totalSailors) {
                                el.textContent = 'Ranked ' + formatRank(rankPosition) + scorePart + ' out of ' + totalSailors + ' sailors';
                            } else if (totalSailors > 0) {
                                el.textContent = notRanked ? ('Not ranked out of ' + totalSailors + ' sailors') : ('Standing: …');
                            } else if (hasParticipation) {
                                el.textContent = 'Standing: Ranked';
                            } else {
                                el.textContent = 'No ranking';
                            }
                        }
                        function findSailorInRankings(list) {
                            if (!list || !list.length) return null;
                            return list.find(function(r) {
                                var sid = r.sailor_id != null ? String(r.sailor_id).trim() : r.sa_id != null ? String(r.sa_id).trim() : r.sas_id != null ? String(r.sas_id).trim() : r.sa_sailing_id != null ? String(r.sa_sailing_id).trim() : '';
                                if (!sid) return false;
                                if (sid === sasIdStr) return true;
                                return String(Number(sid)) === String(Number(sasIdStr));
                            }) || null;
                        }
                        fetch(`${API}/api/standings/db?class_name=${encodeURIComponent(apiClassName)}`)
                                .then(function(r) {
                                    if (!r.ok) throw new Error('HTTP ' + r.status);
                                    return r.json();
                                })
                                .then(function(standingsData) {
                                    const rankings = standingsData.rankings || [];
                                    const totalSailors = standingsData.total_sailors != null ? standingsData.total_sailors : rankings.length;
                                    const sailorRow = findSailorInRankings(rankings);
                                    const rankPosition = sailorRow && (sailorRow.main_rank != null || sailorRow.rank_position != null) ? parseInt(sailorRow.main_rank || sailorRow.rank_position, 10) : null;
                                    var scoreFromRow = sailorRow && (sailorRow.ranking_score != null || sailorRow.ranking_score === 0) ? sailorRow.ranking_score : (sailorRow && sailorRow.score != null ? sailorRow.score : (sailorRow && sailorRow.wc_score != null ? sailorRow.wc_score : null));
                                    var hasParticipation = regattaCount > 0;
                                    function applyFromData(data) {
                                        const list = data.rankings || [];
                                        let total = data.total_sailors != null ? data.total_sailors : list.length;
                                        const row = findSailorInRankings(list);
                                        let rp = row && (row.main_rank != null || row.rank_position != null) ? parseInt(row.main_rank || row.rank_position, 10) : null;
                                        let sc = row && (row.ranking_score != null || row.ranking_score === 0) ? row.ranking_score : (row && row.score != null ? row.score : (row && row.wc_score != null ? row.wc_score : null));
                                        if (!rp && hasParticipation) {
                                            var mem = rankingMap[className.toLowerCase()] || rankingMap[apiClassName.toLowerCase()];
                                            if (mem && (mem.rank_position != null || mem.main_rank != null) && (mem.fleet_size != null || mem.total_sailors != null)) {
                                                rp = parseInt(mem.rank_position != null ? mem.rank_position : mem.main_rank, 10);
                                                total = mem.fleet_size != null ? mem.fleet_size : mem.total_sailors;
                                                if (sc == null && (mem.ranking_score != null || mem.score != null || mem.wc_score != null)) sc = mem.ranking_score != null ? mem.ranking_score : (mem.score != null ? mem.score : mem.wc_score);
                                            }
                                        }
                                        applyStanding(rp, total, true, sc, hasParticipation);
                                    }
                                    if (rankPosition && totalSailors) {
                                        applyStanding(rankPosition, totalSailors, true, scoreFromRow, hasParticipation);
                                        return;
                                    }
                                    if (rankings.length === 0 && apiClassName !== className) {
                                        return fetch(`${API}/api/standings/db?class_name=${encodeURIComponent(className)}`).then(function(r) { return r.ok ? r.json() : { rankings: [], total_sailors: 0 }; }).then(function(data2) {
                                            const list2 = data2.rankings || [];
                                            const row2 = list2.length ? findSailorInRankings(list2) : null;
                                            const rp2 = row2 && (row2.main_rank != null || row2.rank_position != null) ? parseInt(row2.main_rank || row2.rank_position, 10) : null;
                                            const total2 = data2.total_sailors != null ? data2.total_sailors : list2.length;
                                            if (rp2 && total2) {
                                                var sc2 = row2 && (row2.ranking_score != null || row2.ranking_score === 0) ? row2.ranking_score : (row2 && (row2.score != null || row2.wc_score != null) ? (row2.score != null ? row2.score : row2.wc_score) : null);
                                                applyStanding(rp2, total2, true, sc2, hasParticipation);
                                                return;
                                            }
                                            applyStanding(null, total2 || 0, true, null, hasParticipation);
                                        });
                                    }
                                    applyStanding(null, totalSailors || 0, true, null, hasParticipation);
                                })
                                .catch(function(err) {
                                    console.error('[DEBUG] Error loading standings for ' + className + ' (' + apiClassName + '):', err);
                                    const el = document.getElementById(standingId);
                                    if (!el) return;
                                    const ranking = rankingMap[className.toLowerCase()] || rankingMap[apiClassName.toLowerCase()];
                                    const rp = ranking && (ranking.main_rank != null || ranking.rank_position != null) ? parseInt(ranking.main_rank || ranking.rank_position, 10) : null;
                                    const fs = ranking && ranking.fleet_size != null ? ranking.fleet_size : null;
                                    const score = ranking && (ranking.ranking_score != null || ranking.ranking_score === 0) ? ranking.ranking_score : (ranking && ranking.score != null ? ranking.score : null);
                                    if (rp && fs) {
                                        var scorePart = (score != null && score !== '' && !isNaN(Number(score))) ? ' (' + Math.round(Number(score)) + ')' : '';
                                        el.textContent = 'Ranked ' + formatRank(rp) + scorePart + ' out of ' + fs + ' sailors';
                                    } else if (regattaCount > 0) {
                                        el.textContent = 'Standing: Ranked';
                                    } else {
                                        el.textContent = 'Not ranked';
                                    }
                                });
                    });
                    
                    html += `</div>`;
                }
                
                modalContent.innerHTML = html;
                modal.style.display = 'block';
                
            } catch (error) {
                console.error('[DEBUG] showSailorStats: Error:', error);
                modalContent.innerHTML = `
                    <div style="padding: 20px; color: #d32f2f;">
                        <h2>Error Loading Statistics</h2>
                        <p>Failed to load sailor statistics. Please try again.</p>
                        <p style="font-size: 12px; color: #666;">${error.message}</p>
                    </div>
                `;
                modal.style.display = 'block';
            }
        }
        
        function closeSailorStatsModal() {
            const modal = document.getElementById('sailorStatsModal');
            if (modal) {
                modal.style.display = 'none';
            }
        }
        
        /**
         * Open full profile (search.html) in a popup window (used when "Popup expansion for full table view" is checked)
         */
        function openFullProfilePopup(sasId) {
            const url = `/search.html?sas_id=${encodeURIComponent(sasId)}`;
            const w = 1000;
            const h = 700;
            const left = Math.round((screen.width - w) / 2);
            const top = Math.round((screen.height - h) / 2);
            window.open(url, 'FullProfile', `width=${w},height=${h},left=${left},top=${top},scrollbars=yes,resizable=yes`);
        }
        
        // Close modal when clicking/tapping outside (works for both mouse and touch)
        window.addEventListener('click', function(event) {
            const modal = document.getElementById('sailorStatsModal');
            if (event.target === modal) {
                closeSailorStatsModal();
            }
        });
        
        // Also handle touch events for mobile
        window.addEventListener('touchend', function(event) {
            const modal = document.getElementById('sailorStatsModal');
            if (event.target === modal) {
                closeSailorStatsModal();
            }
        });
        
        // Close on Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const modal = document.getElementById('sailorStatsModal');
                if (modal && modal.style.display === 'block') {
                    closeSailorStatsModal();
                }
            }
        });
        
        /**
         * Toggle Expanded View for a class
         */
        function toggleExpandedView(className, sasId, isChecked) {
            if (!isChecked) {
                closeExpandedViewModal();
                return;
            }
            
            const API = window.API_BASE || window.location.origin || '';
            const modal = document.getElementById('expandedViewModal');
            const modalContent = document.getElementById('expandedViewContent');
            
            if (!modal || !modalContent) {
                console.error('[DEBUG] Expanded view modal elements not found');
                return;
            }
            
            // Show loading
            modalContent.innerHTML = '<div style="padding: 20px; text-align: center;">Loading expanded view...</div>';
            modal.style.display = 'block';
            
            // Fetch results for this sailor
            fetch(`${API}/api/member/${encodeURIComponent(sasId)}/results`)
                .then(r => r.json())
                .then(resultsData => {
                    const results = resultsData.results || [];
                    const classResults = results.filter(r => {
                        const rClass = (r.class_canonical || r.class_original || '').trim();
                        return rClass === className;
                    }).sort((a, b) => {
                        const dateA = new Date(a.end_date || a.start_date || 0);
                        const dateB = new Date(b.end_date || b.start_date || 0);
                        return dateB - dateA;
                    });
                    
                    if (classResults.length === 0) {
                        modalContent.innerHTML = `
                            <h2 style="margin-top: 0; color: #1e3a8a;">${className} - Full Results</h2>
                            <p>No results found for this class.</p>
                        `;
                        return;
                    }
                    
                    // Find max races
                    let maxRaces = 0;
                    classResults.forEach(r => {
                        const raceScores = r.race_scores || {};
                        const raceKeys = Object.keys(raceScores).filter(k => k.startsWith('R') && /^\d+$/.test(k.substring(1)));
                        raceKeys.forEach(k => {
                            const num = parseInt(k.substring(1));
                            if (num > maxRaces) maxRaces = num;
                        });
                    });
                    
                    let html = `
                        <h2 style="margin-top: 0; color: #1e3a8a; font-size: 20px;">${className} - Full Results</h2>
                        <div style="overflow-x: auto;">
                            <table class="expanded-table">
                                <thead>
                                    <tr>
                                        <th>No.</th>
                                        <th>R No</th>
                                        <th>Regatta</th>
                                        <th>Date</th>
                                        <th>Sail No</th>
                                        <th>Bow No</th>
                                        <th>Boat Name</th>
                                        <th>Club</th>
                                        <th>Crew</th>
                                        <th>Rank</th>
                                        ${Array.from({length: maxRaces}, (_,i) => `<th>R${i+1}</th>`).join('')}
                                        <th>Total</th>
                                        <th>Nett</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    classResults.forEach((result, index) => {
                        const rankNum = result.rank ? parseInt(String(result.rank).match(/^\s*([0-9]+)/)?.[1] || '0') : null;
                        const rankClass = rankNum === 1 ? 'rank-1' : rankNum === 2 ? 'rank-2' : rankNum === 3 ? 'rank-3' : '';
                        
                        const isSeries = result.is_series === true || result.regatta_number === 'S';
                        const regattaNumber = isSeries ? 'S' : (result.regatta_number || '');
                        
                        let formattedDate = 'N/A';
                        const dateStr = result.regatta_date || result.end_date || result.start_date;
                        if (dateStr) {
                            const date = new Date(dateStr);
                            if (!isNaN(date.getTime())) {
                                const day = String(date.getDate()).padStart(2, '0');
                                const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                                const month = months[date.getMonth()];
                                const year = date.getFullYear();
                                formattedDate = `${day} ${month} ${year}`;
                            }
                        }
                        
                        // Format rank
                        let displayRank = result.rank || 'N/A';
                        const entries = result.entries || result.ranks_sailed || result.entries_raced;
                        if (entries && rankNum) {
                            const suffix = rankNum === 1 ? 'st' : rankNum === 2 ? 'nd' : rankNum === 3 ? 'rd' : 'th';
                            displayRank = `${rankNum}${suffix}/${entries}`;
                        }
                        
                        // Race scores
                        const raceScores = result.race_scores || {};
                        let raceCells = '';
                        for (let i = 1; i <= maxRaces; i++) {
                            const raceKey = `R${i}`;
                            const score = raceScores[raceKey] || '';
                            raceCells += `<td>${score}</td>`;
                        }
                        
                        html += `
                            <tr class="${rankClass}">
                                <td>${index + 1}</td>
                                <td style="font-weight: bold;">${regattaNumber}</td>
                                <td style="text-align: left; font-weight: bold;">${result.event_name || result.regatta_name || 'N/A'}</td>
                                <td>${formattedDate}</td>
                                <td>${result.sail_number || ''}</td>
                                <td>${result.bow_no || ''}</td>
                                <td style="text-align: left;">${result.boat_name || ''}</td>
                                <td style="font-weight: bold;">${String(result.club || result.club_abbrev || result.club_raw || '').toUpperCase()}</td>
                                <td style="text-align: left;">${result.crew_name || ''}</td>
                                <td style="font-weight: bold;">${displayRank}</td>
                                ${raceCells}
                                <td style="font-weight: bold;">${result.total_points_raw !== null && result.total_points_raw !== undefined ? Number(result.total_points_raw).toFixed(1) : ''}</td>
                                <td style="font-weight: bold;">${result.nett_points_raw !== null && result.nett_points_raw !== undefined ? Number(result.nett_points_raw).toFixed(1) : ''}</td>
                            </tr>
                        `;
                    });
                    
                    html += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    modalContent.innerHTML = html;
                })
                .catch(err => {
                    console.error('[DEBUG] Error loading expanded view:', err);
                    modalContent.innerHTML = `
                        <h2 style="margin-top: 0; color: #1e3a8a;">${className} - Full Results</h2>
                        <p style="color: #d32f2f;">Error loading results. Please try again.</p>
                    `;
                });
        }
        
        /**
         * Close Expanded View Modal
         */
        function closeExpandedViewModal() {
            const modal = document.getElementById('expandedViewModal');
            if (modal) {
                modal.style.display = 'none';
                // Uncheck all expanded view checkboxes
                document.querySelectorAll('input[type="checkbox"][id^="expanded-view-"]').forEach(cb => {
                    cb.checked = false;
                });
            }
        }
        
        /**
         * Close Regatta Result Sheet Modal (used when opened as fallback on mobile)
         */
        function closeRegattaResultSheetModal() {
            const modal = document.getElementById('regattaResultSheetModal');
            const modalContent = modal ? modal.querySelector('.regatta-result-sheet-modal-content') : null;
            if (modal) {
                modal.style.display = 'none';
                const iframe = document.getElementById('regattaResultSheetIframe');
                if (iframe) iframe.src = 'about:blank';
                // Reset to default size on close (will be restored from localStorage on next open if saved)
                if (modalContent && window.innerWidth > 768) {
                    modalContent.style.width = '900px';
                    modalContent.style.height = '80vh';
                    modalContent.style.maxWidth = 'none';
                    modalContent.style.maxHeight = 'none';
                }
            }
        }
        
        /** Close result sheet and return directly to Sailor Regattas Sailed tab (no popups) */
        function closeRegattaResultSheetAndGoBack() {
            closeRegattaResultSheetModal();
            window._regattaResultBackContext = null;
        }
        
        // Result sheet actions (Save, Share, Print, Open) - same line as Go Back, outside iframe
        (function() {
            var pendingCaptureIntent = null;
            function getResultIframe() {
                var modal = document.getElementById('regattaResultSheetModal');
                if (!modal) return null;
                var d = modal.style.display || window.getComputedStyle(modal).display;
                if (d === 'none') return null;
                var iframe = document.getElementById('regattaResultSheetIframe');
                if (!iframe || !iframe.src || iframe.src === 'about:blank') return null;
                return iframe;
            }
            function dataUrlToBlob(dataUrl) {
                if (!dataUrl) return null;
                var parts = dataUrl.split(',');
                var mime = (parts[0].match(/:(.*?);/) || [])[1] || 'image/png';
                var bstr = atob(parts[1]);
                var n = bstr.length;
                var u8 = new Uint8Array(n);
                for (var i = 0; i < n; i++) u8[i] = bstr.charCodeAt(i);
                return new Blob([u8], { type: mime });
            }
            function safeFilenameFromTitle(title) {
                var t = (title || 'result-sheet').replace(/[^a-zA-Z0-9\-_\s]/g, '').replace(/\s+/g, '-').slice(0, 50);
                return (t || 'result-sheet') + '.png';
            }
            window.addEventListener('message', function(e) {
                if (e.data && e.data.type === 'showSailorProfile') {
                    // showSailorProfile is sent only when user clicks a sailor row inside regatta results (iframe or popup). Never from main regatta search table.
                    if (typeof checkSession === 'function') {
                        checkSession().then(function(session) {
                            if (session && session.valid && typeof showSailorProfileFromResult === 'function') {
                                showSailorProfileFromResult(e.data.sid || '', e.data.name || '', e.data.club || '', e.data.cls || '');
                            } else {
                                if (typeof showLoginRequiredPopup === 'function') showLoginRequiredPopup();
                            }
                        }).catch(function() {
                            if (typeof showLoginRequiredPopup === 'function') showLoginRequiredPopup();
                        });
                    } else if (typeof showSailorProfileFromResult === 'function') {
                        showSailorProfileFromResult(e.data.sid || '', e.data.name || '', e.data.club || '', e.data.cls || '');
                    }
                    return;
                }
                if (!e.data || e.data.type !== 'captureResult' || !e.data.dataUrl) return;
                var intent = pendingCaptureIntent;
                pendingCaptureIntent = null;
                var blob = dataUrlToBlob(e.data.dataUrl);
                var iframe = getResultIframe();
                var title = (iframe && iframe.contentWindow && iframe.contentWindow.document && iframe.contentWindow.document.title) ? iframe.contentWindow.document.title : 'result-sheet';
                var filename = safeFilenameFromTitle(title);
                if (intent === 'save' && blob) {
                    var a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = filename;
                    a.click();
                    URL.revokeObjectURL(a.href);
                } else if (intent === 'share' && navigator.share) {
                    if (blob) {
                        var file = new File([blob], filename, { type: 'image/png' });
                        navigator.share({ title: title, files: [file] }).catch(function() {
                            if (iframe && iframe.src) navigator.share({ title: title, url: iframe.src }).catch(function() {});
                        });
                    } else if (iframe && iframe.src) {
                        navigator.share({ title: title, url: iframe.src }).catch(function() {});
                    }
                }
            });
            var barButtonLastTouch = { el: null, t: 0 };
            function bindBarButton(id, handler) {
                var el = document.getElementById(id);
                if (!el) return;
                el.addEventListener('touchend', function(e) {
                    e.preventDefault();
                    barButtonLastTouch.el = el;
                    barButtonLastTouch.t = Date.now();
                    handler();
                }, { passive: false });
                el.addEventListener('click', function(e) {
                    if (barButtonLastTouch.el === el && (Date.now() - barButtonLastTouch.t) < 500) {
                        e.preventDefault();
                        return;
                    }
                    handler();
                });
            }
            function setupResultSheetBarButtons() {
            bindBarButton('btn-class-fleet-sheet-modal', function() {
                if (typeof navigateToResultView === 'function') navigateToResultView('class');
            });
            bindBarButton('btn-full-regatta-sheet-modal', function() {
                if (typeof navigateToResultView === 'function') navigateToResultView('full');
            });
            bindBarButton('btn-podium-sheet-modal', function() {
                if (typeof navigateToResultView === 'function') navigateToResultView('podium');
            });
            bindBarButton('btn-save-sheet-modal', function() {
                var iframe = getResultIframe();
                if (!iframe || !iframe.contentWindow) return;
                var view = (document.getElementById('btn-view-expanded-modal') && document.getElementById('btn-view-expanded-modal').classList.contains('bar-view-active')) ? 'expanded' : 'lite';
                pendingCaptureIntent = 'save';
                iframe.contentWindow.postMessage({ type: 'captureSheet', view: view }, '*');
            });
            bindBarButton('btn-share-sheet-modal', function() {
                var iframe = getResultIframe();
                if (!iframe || !iframe.contentWindow) return;
                if (navigator.share) {
                    var view = (document.getElementById('btn-view-expanded-modal') && document.getElementById('btn-view-expanded-modal').classList.contains('bar-view-active')) ? 'expanded' : 'lite';
                    pendingCaptureIntent = 'share';
                    iframe.contentWindow.postMessage({ type: 'captureSheet', view: view }, '*');
                } else {
                    if (iframe.src) {
                        navigator.clipboard.writeText(iframe.src).then(function() { alert('Link copied to clipboard.'); }).catch(function() { prompt('Copy this link:', iframe.src); });
                    }
                }
            });
            bindBarButton('btn-print-sheet-modal', function() {
                var iframe = getResultIframe();
                if (iframe && iframe.contentWindow && iframe.contentWindow.print) iframe.contentWindow.print();
            });
            bindBarButton('btn-open-sheet-modal', function() {
                var iframe = getResultIframe();
                if (iframe && iframe.src) window.open(iframe.src, '_blank');
            });
            function setBarViewActive(view) {
                var liteBtn = document.getElementById('btn-view-lite-modal');
                var expBtn = document.getElementById('btn-view-expanded-modal');
                if (!liteBtn || !expBtn) return;
                if (view === 'lite') {
                    liteBtn.classList.add('bar-view-active');
                    expBtn.classList.remove('bar-view-active');
                } else {
                    expBtn.classList.add('bar-view-active');
                    liteBtn.classList.remove('bar-view-active');
                }
                if (typeof updateResultSheetFlashState === 'function') updateResultSheetFlashState();
            }
            bindBarButton('btn-view-lite-modal', function() {
                var iframe = getResultIframe();
                if (!iframe || !iframe.contentWindow) return;
                setBarViewActive('lite');
                iframe.contentWindow.postMessage({ type: 'setView', view: 'lite' }, '*');
            });
            bindBarButton('btn-view-expanded-modal', function() {
                var iframe = getResultIframe();
                if (!iframe || !iframe.contentWindow) return;
                setBarViewActive('expanded');
                iframe.contentWindow.postMessage({ type: 'setView', view: 'expanded' }, '*');
            });
            bindBarButton('btn-go-back-sheet-modal', function() {
                if (typeof closeRegattaResultSheetAndGoBack === 'function') closeRegattaResultSheetAndGoBack();
            });
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', setupResultSheetBarButtons);
            } else {
                setupResultSheetBarButtons();
            }
        })();
        
        // Close modals on Escape key (choice first, then result sheet, then expanded view)
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const choiceModal = document.getElementById('regattaChoiceModal');
                if (choiceModal && choiceModal.classList.contains('show')) {
                    closeRegattaChoiceModal();
                } else {
                    const regattaSheetModal = document.getElementById('regattaResultSheetModal');
                    if (regattaSheetModal && regattaSheetModal.style.display === 'block') {
                        closeRegattaResultSheetModal();
                    } else {
                        const expandedModal = document.getElementById('expandedViewModal');
                        if (expandedModal && expandedModal.style.display === 'block') {
                            closeExpandedViewModal();
                        }
                    }
                }
            }
        });
        
        // Close expanded view modal when clicking outside
        window.addEventListener('click', function(event) {
            const regattaSheetModal = document.getElementById('regattaResultSheetModal');
            if (regattaSheetModal && event.target === regattaSheetModal) {
                closeRegattaResultSheetAndGoBack();
            }
            const expandedModal = document.getElementById('expandedViewModal');
            if (event.target === expandedModal) {
                closeExpandedViewModal();
            }
        });
        
        // Make functions globally available
        window.showSailorStats = showSailorStats;
        window.closeSailorStatsModal = closeSailorStatsModal;
        window.toggleExpandedView = toggleExpandedView;
        window.closeExpandedViewModal = closeExpandedViewModal;
        window.closeRegattaResultSheetModal = closeRegattaResultSheetModal;
        window.closeRegattaResultSheetAndGoBack = closeRegattaResultSheetAndGoBack;
        window.showRegattaResultChoice = showRegattaResultChoice;
        window.closeRegattaChoiceModal = closeRegattaChoiceModal;
        window.navigateToClassResults = navigateToClassResults;
        window.navigateToFullRegattaResults = navigateToFullRegattaResults;
        window.navigateToClassPodium = navigateToClassPodium;
        window.openResultPageInModal = openResultPageInModal;
        window.openFullProfilePopup = openFullProfilePopup;
    