            (function() {
                function pad2(x) { return (x != null && String(x).length === 1) ? '0' + x : (x != null ? String(x) : '00'); }
                function formatSAST() {
                    var d = new Date();
                    var opts = { timeZone: 'Africa/Johannesburg', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
                    var parts = new Intl.DateTimeFormat('en-CA', opts).formatToParts(d);
                    var y = '', mo = '', day = '', h = '', mi = '', s = '';
                    parts.forEach(function(p) {
                        if (p.type === 'year') y = p.value;
                        if (p.type === 'month') mo = p.value;
                        if (p.type === 'day') day = p.value;
                        if (p.type === 'hour') h = p.value;
                        if (p.type === 'minute') mi = p.value;
                        if (p.type === 'second') s = p.value;
                    });
                    return y + '-' + pad2(mo) + '-' + pad2(day) + ' ' + pad2(h) + ':' + pad2(mi) + ':' + pad2(s) + ' SAST (UTC+2)';
                }
                var liveClock = document.getElementById('liveClock');
                if (liveClock) {
                    liveClock.textContent = formatSAST();
                    setInterval(function() { if (liveClock) liveClock.textContent = formatSAST(); }, 1000);
                }
                function formatDurationSeconds(sec) {
                    if (sec == null || isNaN(sec)) return '0d 0h 0m 0s';
                    sec = Math.max(0, Math.floor(sec));
                    var d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
                    return d + 'd ' + h + 'h ' + m + 'm ' + s + 's';
                }
                function formatDuration(sec) { return formatDurationSeconds(sec); }
                function tickDurations() {
                    var table = document.getElementById('online-users-table');
                    if (!table) return;
                    var now = Date.now() / 1000;
                    table.querySelectorAll('tbody tr').forEach(function(tr) {
                        if (tr.getAttribute('data-logout-row') === '1') return;
                        var cell = tr.querySelector('td.session-duration');
                        if (!cell) return;
                        var t = null;
                        var startUnix = tr.getAttribute('data-session-start-unix');
                        if (startUnix != null && startUnix !== '') t = parseInt(startUnix, 10);
                        if (t == null || isNaN(t)) {
                            var iso = tr.getAttribute('data-login-time');
                            if (iso) t = new Date(iso).getTime() / 1000;
                        }
                        if (t == null || isNaN(t)) { cell.textContent = '0d 0h 0m 0s'; return; }
                        var sec = Math.max(0, Math.floor(now - t));
                        cell.textContent = formatDuration(sec);
                    });
                }
                setInterval(tickDurations, 1000);
                tickDurations();
                function formatUptime(seconds) { return formatDurationSeconds(seconds); }
                function tickUptime() {
                    var el = document.getElementById('apiUptime');
                    if (!el) return;
                    var startTs = parseInt(el.dataset.startTs, 10);
                    var now = Math.floor(Date.now() / 1000);
                    var elapsed = (startTs != null && !isNaN(startTs)) ? Math.max(0, now - startTs) : 0;
                    el.innerText = formatDurationSeconds(elapsed);
                }
                function formatRestartTime(unixSec) {
                    if (unixSec == null || isNaN(unixSec)) return '—';
                    var d = new Date(unixSec * 1000);
                    return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
                }
                function updateRestartTime(overrideTs) {
                    var target = document.getElementById('apiRestartTime');
                    if (!target) return;
                    var startTs = overrideTs != null ? (typeof overrideTs === 'number' ? overrideTs : parseInt(overrideTs, 10)) : null;
                    if (startTs == null || isNaN(startTs)) {
                        var el = document.getElementById('apiUptime');
                        if (el) startTs = parseInt(el.dataset.startTs, 10);
                    }
                    target.textContent = formatRestartTime(startTs);
                }
                setInterval(tickUptime, 1000);
                tickUptime();
                updateRestartTime();
                function updateStatCardsFromData(data) {
                    var v1 = document.getElementById('admin-stat-1-value');
                    var v2 = document.getElementById('admin-stat-2-value');
                    var v3 = document.getElementById('admin-stat-3-value');
                    var v4 = document.getElementById('admin-stat-4-value');
                    if (v1) v1.textContent = (data.active_sailors != null && data.active_sailors !== '') ? Number(data.active_sailors) : '0';
                    if (v2) v2.textContent = (data.classes_sailed != null && data.classes_sailed !== '') ? Number(data.classes_sailed) : '0';
                    if (v3) v3.textContent = (data.regattas_sailed != null && data.regattas_sailed !== '') ? Number(data.regattas_sailed) : '0';
                    if (v4) v4.textContent = (data.races_raced != null && data.races_raced !== '') ? Number(data.races_raced) : '0';
                }
                var apiUptimeEl = document.getElementById('apiUptime');
                fetch('/admin/dashboard-data', { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(data) { updateStatCardsFromData(data); }).catch(function() {});
                setInterval(function() {
                    fetch('/admin/dashboard-data', { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(data) {
                        updateStatCardsFromData(data);
                        var table = document.getElementById('online-users-table');
                        if (!table) return;
                        var list = data.online_users || [];
                        var byId = {};
                        list.forEach(function(u) { var k = (u.session_id != null && u.session_id !== '') ? String(u.session_id) : String(u.sas_id || ''); byId[k] = u; });
                        var tbody = table.querySelector('tbody');
                        if (!tbody) return;
                        if (list.length > 0) {
                            tbody.querySelectorAll('tr td[colspan="8"]').forEach(function(td) { var tr = td.closest('tr'); if (tr) tr.parentNode.removeChild(tr); });
                        }
                        var trs = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
                        var seenIds = {};
                        trs.forEach(function(tr) {
                            if (tr.getAttribute('data-logout-row') === '1') return;
                            var sessionId = tr.getAttribute('data-session-id') || tr.getAttribute('data-sas-id');
                            if (!sessionId) return;
                            var u = byId[sessionId];
                            if (u) {
                                seenIds[sessionId] = true;
                                var cp = tr.querySelector('td.current-page');
                                var dev = tr.querySelector('td.device-cell');
                                var ip = tr.querySelector('td.ip-cell');
                                if (cp) cp.textContent = u.current_page != null ? u.current_page : '—';
                                if (dev) dev.textContent = u.device != null ? u.device : '—';
                                if (ip) ip.textContent = u.ip_address != null ? u.ip_address : '—';
                            } else {
                                var nameTd = tr.querySelector('td:first-child');
                                var activeTd = tr.querySelector('td.active-cell');
                                if (nameTd && activeTd) {
                                    tr.setAttribute('data-logout-row', '1');
                                    tr.removeAttribute('data-login-time');
                                    tr.removeAttribute('data-session-start-unix');
                                    tr.classList.add('logout-row');
                                    var nameText = (nameTd.textContent || '').trim();
                                    nameTd.textContent = nameText + ' — Logged out ✖';
                                    activeTd.innerHTML = '<span class="active-logout">✖</span>';
                                    tr.querySelectorAll('td.session-duration, td.current-page').forEach(function(c) { if (c) c.textContent = '—'; });
                                    setTimeout(function() {
                                        tr.classList.add('fade-out');
                                        setTimeout(function() {
                                            if (tr.parentNode) tr.parentNode.removeChild(tr);
                                            if (tbody && tbody.querySelectorAll('tr[data-session-id]:not([data-logout-row])').length === 0) {
                                                tbody.querySelectorAll('tr td[colspan="8"]').forEach(function(td) { var r = td.closest('tr'); if (r) r.parentNode.removeChild(r); });
                                                var empty = document.createElement('tr');
                                                empty.innerHTML = '<td colspan="8">No one currently signed in.</td>';
                                                tbody.appendChild(empty);
                                                var countEl = document.querySelector('.metric-tile[data-scroll-to="online-users"] .value');
                                                if (countEl) countEl.textContent = '0';
                                            }
                                        }, 2000);
                                    }, 0);
                                }
                            }
                        });
                        list.forEach(function(u) {
                            var sid = String(u.sas_id || '');
                            var sessionId = (u.session_id != null && u.session_id !== '') ? String(u.session_id) : sid;
                            if (seenIds[sessionId]) return;
                            var loginIso = u.login_time_iso || '';
                            var startUnix = u.session_start_unix;
                            var dataAttrs = ' data-sas-id="' + (sid.replace(/"/g, '&quot;')) + '" data-session-id="' + (sessionId.replace(/"/g, '&quot;')) + '"';
                            if (loginIso) dataAttrs += ' data-login-time="' + (loginIso.replace(/"/g, '&quot;')) + '"';
                            if (startUnix != null) dataAttrs += ' data-session-start-unix="' + startUnix + '"';
                            var name = (u.name != null ? String(u.name) : '—').replace(/</g, '&lt;').replace(/"/g, '&quot;');
                            var nameCell = '<td><span class="session-history-link" role="button" tabindex="0" data-sas-id="' + (sid.replace(/"/g, '&quot;')) + '" data-name="' + name + '">' + name + '</span></td>';
                            var loginDisplay = loginIso ? new Date(loginIso).toLocaleString() : '—';
                            var newTr = document.createElement('tr');
                            newTr.setAttribute('data-sas-id', sid);
                            newTr.setAttribute('data-session-id', sessionId);
                            if (loginIso) newTr.setAttribute('data-login-time', loginIso);
                            if (startUnix != null) newTr.setAttribute('data-session-start-unix', String(startUnix));
                            newTr.innerHTML = nameCell + '<td>' + (sid.replace(/</g, '&lt;')) + '</td><td class="ip-cell">' + (u.ip_address != null ? String(u.ip_address).replace(/</g, '&lt;') : '—') + '</td><td class="device-cell">' + (u.device != null ? String(u.device).replace(/</g, '&lt;') : '—') + '</td><td>' + loginDisplay + '</td><td class="session-duration">0d 0h 0m 0s</td><td class="current-page">' + (u.current_page != null ? String(u.current_page).replace(/</g, '&lt;') : '—') + '</td><td class="active-cell"><span class="active-yes">✓</span></td>';
                            tbody.insertBefore(newTr, tbody.firstChild);
                        });
                        if (tbody.querySelectorAll('tr').length === 0) {
                            var empty = document.createElement('tr');
                            empty.innerHTML = '<td colspan="8">No one currently signed in.</td>';
                            tbody.appendChild(empty);
                        }
                        var countEl = document.querySelector('.metric-tile[data-scroll-to="online-users"] .value');
                        if (countEl) countEl.textContent = list.length;
                        var offlineList = data.offline_sessions || [];
                        var offTbody = document.querySelector('#offline-users-table tbody');
                        if (offTbody) {
                            offTbody.innerHTML = '';
                            function formatDurSec(sec) { return formatDurationSeconds(sec); }
                            function fmtIso(iso) {
                                if (!iso) return '—';
                                var d = new Date(iso);
                                return isNaN(d.getTime()) ? iso.substring(0, 19) : d.toLocaleString();
                            }
                            if (offlineList.length === 0) {
                                var empty = document.createElement('tr');
                                empty.innerHTML = '<td colspan="7">No recently ended sessions.</td>';
                                offTbody.appendChild(empty);
                            } else {
                                offlineList.forEach(function(o) {
                                    var name = (o.name != null ? String(o.name) : '—').replace(/</g, '&lt;').replace(/"/g, '&quot;');
                                    var sid = (o.sas_id != null ? String(o.sas_id) : '—').replace(/</g, '&lt;');
                                    var ip = (o.ip_address != null ? String(o.ip_address) : '—').replace(/</g, '&lt;');
                                    var dev = (o.device != null ? String(o.device) : '—').replace(/</g, '&lt;');
                                    var nameCell = '<td><span class="session-history-link" role="button" tabindex="0" data-sas-id="' + sid.replace(/"/g, '&quot;') + '" data-name="' + name.replace(/"/g, '&quot;') + '">' + name + '</span></td>';
                                    var tr = document.createElement('tr');
                                    tr.innerHTML = nameCell + '<td>' + sid + '</td><td>' + ip + '</td><td>' + dev + '</td><td>' + fmtIso(o.login_time_iso) + '</td><td>' + formatDurSec(o.duration_seconds) + '</td><td>' + fmtIso(o.logout_time_iso) + '</td>';
                                    offTbody.appendChild(tr);
                                });
                            }
                        }
                    }).catch(function() {});
                }, 10000);
                var modal = document.getElementById('adminModal');
                var titleEl = document.getElementById('adminModalTitle');
                var bodyEl = document.getElementById('adminModalBody');
                var closeBtn = document.getElementById('adminModalClose');
                function closeModal() { modal.classList.remove('show'); }
                if (closeBtn) closeBtn.addEventListener('click', closeModal);
                if (modal) modal.addEventListener('click', function(e) { if (e.target === modal) closeModal(); });
                function openListModal(endpoint, title) {
                    modal.classList.add('show');
                    titleEl.textContent = title;
                    bodyEl.innerHTML = '<span class="loading">Loading…</span>';
                    fetch(endpoint).then(function(r) { return r.json(); }).then(function(data) {
                        if (!data.ok) { bodyEl.innerHTML = '<span class="err">' + (data.error || 'Error') + '</span>'; return; }
                        var rows = data.rows || [];
                        if (rows.length === 0) { bodyEl.innerHTML = '<p>No rows.</p>'; return; }
                        var keys = Object.keys(rows[0]);
                        var labels = data.column_labels || {};
                        var isRegistered = (endpoint || '').indexOf('registered-users') !== -1;
                        var h = '';
                        if (isRegistered) h += '<p><input type="text" id="adminModalSearch" placeholder="Search name, SAS ID, email, whatsapp" style="margin-bottom:12px;padding:8px 12px;width:100%;max-width:400px;box-sizing:border-box;"></p>';
                        h += '<table id="adminModalTable"><thead><tr>' + keys.map(function(k) { return '<th>' + (labels[k] || k.replace(/_/g, ' ')) + '</th>'; }).join('') + '</tr></thead><tbody>';
                        rows.forEach(function(row) {
                            h += '<tr>';
                            keys.forEach(function(k) {
                                if (k === 'active') {
                                    h += '<td>' + (row[k] ? '<span class="active-yes">✓</span>' : '<span class="active-no">–</span>') + '</td>';
                                } else if (k === 'class_name' && row.class_id != null && row.class_id !== '') {
                                    var slug = (row.class_name || '').toString().toLowerCase().trim().replace(/\\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                                    var esc = (row.class_name != null ? String(row.class_name) : '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                                    h += '<td><a href="/class/' + row.class_id + '-' + slug + '">' + esc + '</a></td>';
                                } else {
                                    h += '<td>' + (row[k] != null ? String(row[k]) : '') + '</td>';
                                }
                            });
                            h += '</tr>';
                        });
                        h += '</tbody></table>';
                        bodyEl.innerHTML = h;
                        if (isRegistered) {
                            var searchInput = document.getElementById('adminModalSearch');
                            var table = document.getElementById('adminModalTable');
                            if (searchInput && table) {
                                searchInput.addEventListener('input', function() {
                                    var q = (this.value || '').toLowerCase().trim();
                                    var tbody = table.querySelector('tbody');
                                    if (!tbody) return;
                                    var trs = tbody.querySelectorAll('tr');
                                    trs.forEach(function(tr) {
                                        var text = (tr.textContent || '').toLowerCase();
                                        tr.style.display = q === '' || text.indexOf(q) !== -1 ? '' : 'none';
                                    });
                                });
                            }
                        }
                    }).catch(function(err) { bodyEl.innerHTML = '<span class="err">' + (err.message || 'Error') + '</span>'; });
                }
                document.querySelectorAll('.metric-tile').forEach(function(tile) {
                    tile.addEventListener('click', function() {
                        var scrollTo = this.getAttribute('data-scroll-to');
                        var endpoint = this.getAttribute('data-endpoint');
                        var title = this.getAttribute('data-title') || '';
                        if (scrollTo) {
                            var el = document.getElementById(scrollTo);
                            if (el) el.scrollIntoView({ behavior: 'smooth' });
                        } else if (endpoint) openListModal(endpoint, title);
                    });
                });
                var activeSailorsPanel = document.getElementById('active-sailors-panel-wrap');
                var activeSailorsTable = document.getElementById('active-sailors-table');
                var activeSailorsSearch = document.getElementById('active-sailors-search');
                var activeSailorsData = null;
                var activeSailorsSortKey = 'races_count';
                var activeSailorsSortAsc = false;
                function renderActiveSailorsBody() {
                    var data = activeSailorsData;
                    if (!data || !activeSailorsTable) return;
                    var tbody = activeSailorsTable.querySelector('tbody');
                    if (!tbody) return;
                    var sortKey = activeSailorsSortKey;
                    var asc = activeSailorsSortAsc;
                    var sorted = data.slice().sort(function(a, b) {
                        var va = a[sortKey]; var vb = b[sortKey];
                        var numericKeys = ['rank', 'races_count', 'regattas_count', 'last_regatta_rank', 'fleet_size'];
                        if (numericKeys.indexOf(sortKey) !== -1) {
                            va = Number(va) || 0; vb = Number(vb) || 0;
                            return asc ? (va - vb) : (vb - va);
                        }
                        va = (va != null ? String(va) : ''); vb = (vb != null ? String(vb) : '');
                        var c = va.localeCompare(vb, undefined, { numeric: true });
                        return asc ? c : -c;
                    });
                    var searchQ = (activeSailorsSearch && activeSailorsSearch.value ? activeSailorsSearch.value : '').toLowerCase().trim();
                    tbody.innerHTML = '';
                    sorted.forEach(function(row) {
                        var tr = document.createElement('tr');
                        tr.setAttribute('data-rank', String(row.rank));
                        tr.setAttribute('data-sas-id', String(row.sas_id || ''));
                        var lastResultDisplay = (row.last_result_display != null ? String(row.last_result_display) : '');
                        tr.setAttribute('data-search', (String(row.rank) + ' ' + (row.full_name || '') + ' ' + (row.sas_id || '') + ' ' + (row.races_count || '') + ' ' + (row.regattas_count || '') + ' ' + (row.last_active_date || '') + ' ' + (row.last_regatta_name || '') + ' ' + (row.regatta_slug || '') + ' ' + (row.last_class_sailed || '') + ' ' + lastResultDisplay).toLowerCase());
                        var nameEsc = (row.full_name != null ? String(row.full_name).replace(/</g, '&lt;').replace(/"/g, '&quot;') : '');
                        var slug = (row.slug != null && row.slug !== '') ? String(row.slug) : '';
                        var nameCell = slug ? '<a href=\"/sailor/' + slug.replace(/"/g, '&quot;') + '\">' + nameEsc + '</a>' : nameEsc;
                        var regattaEsc = (row.last_regatta_name != null ? String(row.last_regatta_name).replace(/</g, '&lt;').replace(/\"/g, '&quot;') : '');
                        var regattaSlug = (row.regatta_slug != null && row.regatta_slug !== '') ? String(row.regatta_slug).replace(/\"/g, '&quot;') : '';
                        var regattaCell = regattaSlug ? '<a href=\"/regatta/' + regattaSlug + '\">' + regattaEsc + '</a>' : regattaEsc;
                        var classEsc = (row.last_class_sailed != null ? String(row.last_class_sailed).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;') : '');
                        var classSlug = (row.last_class_sailed || '').toString().toLowerCase().trim().replace(/\\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                        var classCell = (row.last_class_id != null && row.last_class_id !== '') ? '<a href="/class/' + String(row.last_class_id).replace(/</g, '&lt;') + '-' + classSlug + '">' + classEsc + '</a>' : classEsc;
                        var resultEsc = (lastResultDisplay ? lastResultDisplay.replace(/</g, '&lt;').replace(/\"/g, '&quot;') : '');
                        tr.innerHTML = '<td>' + (row.rank != null ? row.rank : '') + '</td><td>' + nameCell + '</td><td>' + (row.sas_id != null ? String(row.sas_id).replace(/</g, '&lt;') : '') + '</td><td>' + (row.races_count != null ? row.races_count : '') + '</td><td>' + (row.regattas_count != null ? row.regattas_count : '') + '</td><td>' + (row.last_active_date != null ? String(row.last_active_date).replace(/</g, '&lt;') : '') + '</td><td>' + regattaCell + '</td><td>' + classCell + '</td><td>' + resultEsc + '</td>';
                        if (searchQ && (tr.getAttribute('data-search') || '').indexOf(searchQ) === -1) tr.style.display = 'none';
                        tbody.appendChild(tr);
                    });
                }
                var card1 = document.getElementById('admin-stat-card-1');
                if (card1 && activeSailorsPanel) {
                    card1.addEventListener('click', function() {
                        var visible = activeSailorsPanel.style.display !== 'none';
                        activeSailorsPanel.style.display = visible ? 'none' : 'block';
                        if (!visible && activeSailorsData === null && activeSailorsTable) {
                            var tbody = activeSailorsTable.querySelector('tbody');
                            if (tbody) tbody.innerHTML = '<tr><td colspan="9">Loading…</td></tr>';
                            fetch('/admin/api/active-sailors', { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(data) {
                                activeSailorsData = (data.sailors || []);
                                if (!tbody) return;
                                renderActiveSailorsBody();
                                if (activeSailorsSearch) activeSailorsSearch.dispatchEvent(new Event('input'));
                            }).catch(function() {
                                var tb = activeSailorsTable && activeSailorsTable.querySelector('tbody');
                                if (tb) tb.innerHTML = '<tr><td colspan="9">Failed to load.</td></tr>';
                            });
                        }
                    });
                }
                if (activeSailorsTable) {
                    var asThead = activeSailorsTable.querySelector('thead');
                    if (asThead) asThead.addEventListener('click', function(e) {
                        if (e.target && (e.target.tagName === 'A' || (e.target.closest && e.target.closest('a')))) return;
                        var th = e.target && e.target.closest && e.target.closest('th[data-sort]');
                        if (!th || !activeSailorsData) return;
                        var key = th.getAttribute('data-sort');
                        if (key === activeSailorsSortKey) activeSailorsSortAsc = !activeSailorsSortAsc;
                        else { activeSailorsSortKey = key; activeSailorsSortAsc = true; }
                        renderActiveSailorsBody();
                    });
                }
                if (activeSailorsSearch && activeSailorsTable) {
                    activeSailorsSearch.addEventListener('input', function() {
                        var q = (this.value || '').toLowerCase().trim();
                        var tbody = activeSailorsTable.querySelector('tbody');
                        if (!tbody) return;
                        var trs = tbody.querySelectorAll('tr[data-search]');
                        trs.forEach(function(tr) {
                            var text = tr.getAttribute('data-search') || '';
                            tr.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
                        });
                    });
                }
                var classesPanel = document.getElementById('classes-panel-wrap');
                var classesTable = document.getElementById('classes-table');
                var classesSearch = document.getElementById('classes-search');
                var classesData = null;
                var classesSortKey = 'no';
                var classesSortAsc = false;
                function renderClassesBody() {
                    var data = classesData;
                    if (!data || !classesTable) return;
                    var tbody = classesTable.querySelector('tbody');
                    if (!tbody) return;
                    var sorted = data.slice();
                    if (classesSortKey === 'no') {
                        /* Backend order (sailor_count DESC); do not re-sort */
                    } else if (classesSortKey === 'class_name') {
                        sorted.sort(function(a, b) {
                            var va = (a.class_name != null ? String(a.class_name) : '');
                            var vb = (b.class_name != null ? String(b.class_name) : '');
                            return classesSortAsc ? va.localeCompare(vb, undefined, { numeric: true }) : vb.localeCompare(va, undefined, { numeric: true });
                        });
                    } else if (classesSortKey === 'sailor_count') {
                        sorted.sort(function(a, b) {
                            var va = (a.sailor_count === null || a.sailor_count === undefined || a.sailor_count === '') ? 0 : Number(a.sailor_count);
                            var vb = (b.sailor_count === null || b.sailor_count === undefined || b.sailor_count === '') ? 0 : Number(b.sailor_count);
                            return classesSortAsc ? (va - vb) : (vb - va);
                        });
                    }
                    var searchQ = (classesSearch && classesSearch.value ? classesSearch.value : '').toLowerCase().trim();
                    tbody.innerHTML = '';
                    sorted.forEach(function(row) {
                        var tr = document.createElement('tr');
                        var searchParts = [(row.class_name || ''), (row.class_id != null ? String(row.class_id) : ''), (row.sailor_count != null ? String(row.sailor_count) : '')];
                        tr.setAttribute('data-search', searchParts.join(' ').toLowerCase());
                        var slug = (row.class_name || '').toString().toLowerCase().trim().replace(/\\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                        var classEsc = (row.class_name != null ? String(row.class_name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '');
                        var classLink = (row.class_id != null && row.class_id !== '') ? '<a href="/class/' + String(row.class_id).replace(/</g, '&lt;') + '-' + slug + '">' + classEsc + '</a>' : classEsc;
                        tr.innerHTML = '<td>' + (row.no != null ? row.no : '') + '</td><td>' + classLink + '</td><td>' + (row.sailor_count != null ? row.sailor_count : '') + '</td>';
                        if (searchQ && (tr.getAttribute('data-search') || '').indexOf(searchQ) === -1) tr.style.display = 'none';
                        tbody.appendChild(tr);
                    });
                }
                var card2 = document.getElementById('admin-stat-card-2');
                if (card2 && classesPanel) {
                    card2.addEventListener('click', function() {
                        var visible = classesPanel.style.display !== 'none';
                        classesPanel.style.display = visible ? 'none' : 'block';
                        if (!visible && classesData === null && classesTable) {
                            var tbody = classesTable.querySelector('tbody');
                            if (tbody) tbody.innerHTML = '<tr><td colspan="3">Loading…</td></tr>';
                            fetch('/admin/list/classes', { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(data) {
                                console.log("[Classes] fetch success, ok:", data.ok);
                                classesData = (data.ok && data.rows) ? data.rows : [];
                                console.log("[Classes] API count:", data.count, "rows:", (data.rows ? data.rows.length : 0), "classesData.length:", classesData.length);
                                if (!tbody) return;
                                renderClassesBody();
                                console.log("[Classes] calling bindClassesHeaderClicks()");
                                bindClassesHeaderClicks();
                                if (classesSearch) classesSearch.dispatchEvent(new Event('input'));
                            }).catch(function() {
                                var tb = classesTable && classesTable.querySelector('tbody');
                                if (tb) tb.innerHTML = '<tr><td colspan="3">Failed to load.</td></tr>';
                            });
                        }
                    });
                }
                function bindClassesHeaderClicks() {
                    var els = document.querySelectorAll('#classes-table th[data-key]');
                    console.log("[Classes] Binding headers, th[data-key] count:", els.length, "table exists:", !!document.getElementById('classes-table'));
                    els.forEach(function(th) {
                        th.onclick = function(e) {
                            e.stopPropagation();
                            const key = this.dataset.key;
                            console.log("[Classes] header clicked, key:", key);
                            if (classesSortKey === key) {
                                classesSortAsc = !classesSortAsc;
                            } else {
                                classesSortKey = key;
                                classesSortAsc = (key !== 'no' && key !== 'date' && key !== 'entries');
                            }
                            renderClassesBody();
                        };
                    });
                }
                function reRankVisibleRows(selector) {
                    var table = document.querySelector(selector);
                    if (!table) return;
                    var tbody = table.querySelector('tbody');
                    if (!tbody) return;
                    var rows = tbody.querySelectorAll('tr[data-search]');
                    var rank = 1;
                    rows.forEach(function(tr) {
                        if (tr.style.display !== 'none') {
                            var firstCell = tr.querySelector('td');
                            if (firstCell) firstCell.textContent = rank++;
                        }
                    });
                }
                if (classesSearch && classesTable) {
                    classesSearch.addEventListener('input', function() {
                        var q = (this.value || '').toLowerCase().trim();
                        var tbody = classesTable.querySelector('tbody');
                        if (!tbody) return;
                        var trs = tbody.querySelectorAll('tr[data-search]');
                        trs.forEach(function(tr) {
                            var text = tr.getAttribute('data-search') || '';
                            tr.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
                        });
                    });
                }
                var regattasPanel = document.getElementById('regattas-panel-wrap');
                var regattasTable = document.getElementById('regattas-table');
                var regattasSearch = document.getElementById('regattas-search');
                var regattasData = null;
                var regattasSortKey = 'regatta_no';
                var regattasSortAsc = false;
                function renderRegattasBody() {
                    var data = regattasData;
                    if (!data || !regattasTable) return;
                    var tbody = regattasTable.querySelector('tbody');
                    if (!tbody) return;
                    var sorted = data.slice();
                    if (regattasSortKey === 'rank') {
                        if (!regattasSortAsc) sorted.reverse();
                    } else if (regattasSortKey === 'event_name') {
                        sorted.sort(function(a, b) {
                            var va = (a.event_name != null ? String(a.event_name) : '');
                            var vb = (b.event_name != null ? String(b.event_name) : '');
                            return regattasSortAsc ? va.localeCompare(vb, undefined, { numeric: true }) : vb.localeCompare(va, undefined, { numeric: true });
                        });
                    } else if (regattasSortKey === 'regatta_no') {
                        sorted.sort(function(a, b) {
                            var va = (a.regatta_no === null || a.regatta_no === undefined) ? 0 : Number(a.regatta_no);
                            var vb = (b.regatta_no === null || b.regatta_no === undefined) ? 0 : Number(b.regatta_no);
                            return regattasSortAsc ? (va - vb) : (vb - va);
                        });
                    } else if (regattasSortKey === 'date') {
                        sorted.sort(function(a, b) {
                            var ta = (a.date != null && a.date !== '') ? new Date(String(a.date)).getTime() : 0;
                            var tb = (b.date != null && b.date !== '') ? new Date(String(b.date)).getTime() : 0;
                            return regattasSortAsc ? (ta - tb) : (tb - ta);
                        });
                    } else if (regattasSortKey === 'entries') {
                        sorted.sort(function(a, b) {
                            var va = (a.entries === null || a.entries === undefined || a.entries === '') ? 0 : Number(a.entries);
                            var vb = (b.entries === null || b.entries === undefined || b.entries === '') ? 0 : Number(b.entries);
                            return regattasSortAsc ? (va - vb) : (vb - va);
                        });
                    } else if (regattasSortKey === 'location') {
                        sorted.sort(function(a, b) {
                            var va = (a.location != null ? String(a.location) : '');
                            var vb = (b.location != null ? String(b.location) : '');
                            return regattasSortAsc ? va.localeCompare(vb, undefined, { numeric: true }) : vb.localeCompare(va, undefined, { numeric: true });
                        });
                    } else if (regattasSortKey === 'has_results') {
                        sorted.sort(function(a, b) {
                            var va = (a.has_results === true || a.has_results === 'true') ? 1 : 0;
                            var vb = (b.has_results === true || b.has_results === 'true') ? 1 : 0;
                            return regattasSortAsc ? (va - vb) : (vb - va);
                        });
                    }
                    var searchQ = (regattasSearch && regattasSearch.value ? regattasSearch.value : '').toLowerCase().trim();
                    tbody.innerHTML = '';
                    var rankCounter = 0;
                    sorted.forEach(function(row, i) {
                        if (row.has_results === true || row.has_results === 'true') rankCounter++;
                        var rank = (row.has_results === true || row.has_results === 'true') ? rankCounter : '';
                        var tr = document.createElement('tr');
                        if (!(row.has_results === true || row.has_results === 'true')) tr.classList.add('no-results-row');
                        var searchParts = [(row.event_name || ''), (row.regatta_no != null ? String(row.regatta_no) : ''), (row.regatta_id != null ? String(row.regatta_id) : ''), (row.date != null ? String(row.date) : ''), (row.location != null ? String(row.location) : ''), (row.entries != null ? String(row.entries) : ''), (row.has_results ? 'yes' : 'no')];
                        tr.setAttribute('data-search', searchParts.join(' ').toLowerCase());
                        var regattaId = (row.regatta_id != null && row.regatta_id !== '') ? String(row.regatta_id).replace(/</g, '&lt;') : '';
                        var nameEsc = (row.event_name != null ? String(row.event_name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '');
                        var regattaCell = regattaId ? '<a href="/regatta/' + regattaId + '">' + nameEsc + '</a>' : nameEsc;
                        var regattaNoVal = (row.regatta_no != null && row.regatta_no !== '') ? row.regatta_no : '';
                        var dateEsc = (row.date != null ? String(row.date).replace(/</g, '&lt;') : '');
                        var clubCode = (row.club_abbrev || '').toString().toLowerCase().trim();
                        var locEsc = (row.location != null ? String(row.location).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '');
                        var clubCell = clubCode ? '<a href="/club/' + clubCode + '">' + locEsc + '</a>' : locEsc;
                        var entriesVal = (row.entries != null && row.entries !== '') ? row.entries : '';
                        var resultsVal = (row.has_results === true || row.has_results === 'true') ? 'Yes' : 'No';
                        tr.innerHTML = '<td>' + rank + '</td><td>' + regattaNoVal + '</td><td>' + regattaCell + '</td><td>' + dateEsc + '</td><td>' + clubCell + '</td><td>' + entriesVal + '</td><td>' + resultsVal + '</td>';
                        if (searchQ && (tr.getAttribute('data-search') || '').indexOf(searchQ) === -1) tr.style.display = 'none';
                        tbody.appendChild(tr);
                    });
                }
                var card3 = document.getElementById('admin-stat-card-3');
                if (card3 && regattasPanel) {
                    card3.addEventListener('click', function() {
                        var visible = regattasPanel.style.display !== 'none';
                        regattasPanel.style.display = visible ? 'none' : 'block';
                        if (!visible && regattasData === null && regattasTable) {
                            var tbody = regattasTable.querySelector('tbody');
                            if (tbody) tbody.innerHTML = '<tr><td colspan="7">Loading…</td></tr>';
                            fetch('/admin/list/regattas', { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(data) {
                                console.log("[Regattas] fetch success, ok:", data.ok);
                                regattasData = (data.ok && data.rows) ? data.rows : [];
                                console.log("[Regattas] rows:", (data.rows ? data.rows.length : 0), "regattasData.length:", regattasData.length);
                                if (!tbody) return;
                                renderRegattasBody();
                                console.log("[Regattas] calling bindRegattasHeaderClicks()");
                                bindRegattasHeaderClicks();
                                if (regattasSearch) regattasSearch.dispatchEvent(new Event('input'));
                            }).catch(function() {
                                var tb = regattasTable && regattasTable.querySelector('tbody');
                                if (tb) tb.innerHTML = '<tr><td colspan="7">Failed to load.</td></tr>';
                            });
                        }
                    });
                }
                function bindRegattasHeaderClicks() {
                    var els = document.querySelectorAll('#regattas-table th[data-key]');
                    console.log("[Regattas] Binding headers, th[data-key] count:", els.length, "table exists:", !!document.getElementById('regattas-table'));
                    els.forEach(function(th) {
                        th.onclick = function(e) {
                            e.stopPropagation();
                            const key = this.dataset.key;
                            console.log("[Regattas] header clicked, key:", key);
                            if (regattasSortKey === key) {
                                regattasSortAsc = !regattasSortAsc;
                            } else {
                                regattasSortKey = key;
                                regattasSortAsc = (key !== 'rank' && key !== 'date' && key !== 'entries' && key !== 'regatta_no' && key !== 'has_results');
                            }
                            renderRegattasBody();
                        };
                    });
                }
                if (regattasSearch && regattasTable) {
                    regattasSearch.addEventListener('input', function() {
                        var q = (this.value || '').toLowerCase().trim();
                        var tbody = regattasTable.querySelector('tbody');
                        if (!tbody) return;
                        var trs = tbody.querySelectorAll('tr[data-search]');
                        trs.forEach(function(tr) {
                            var text = tr.getAttribute('data-search') || '';
                            tr.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
                        });
                    });
                }
                var racesPanel = document.getElementById('races-panel-wrap');
                var racesTable = document.getElementById('races-table');
                var racesData = [];
                var racesSortKey = 'date';
                var racesSortAsc = false;
                var racesLoaded = false;
                function renderRacesBody() {
                    var data = racesData;
                    if (!data || !racesTable) return;
                    var tbody = racesTable.querySelector('tbody');
                    if (!tbody) return;
                    var sorted = data.slice();
                    if (racesSortKey === 'rank') {
                        if (!racesSortAsc) sorted.reverse();
                    } else if (racesSortKey === 'regatta_name') {
                        sorted.sort(function(a, b) {
                            var va = (a.regatta_name != null ? String(a.regatta_name) : '');
                            var vb = (b.regatta_name != null ? String(b.regatta_name) : '');
                            return racesSortAsc ? va.localeCompare(vb, undefined, { numeric: true }) : vb.localeCompare(va, undefined, { numeric: true });
                        });
                    } else if (racesSortKey === 'date') {
                        sorted.sort(function(a, b) {
                            var ta = (a.date != null && a.date !== '') ? new Date(String(a.date)).getTime() : 0;
                            var tb = (b.date != null && b.date !== '') ? new Date(String(b.date)).getTime() : 0;
                            return racesSortAsc ? (ta - tb) : (tb - ta);
                        });
                    } else if (racesSortKey === 'class_count') {
                        sorted.sort(function(a, b) {
                            var va = (a.class_count === null || a.class_count === undefined) ? 0 : Number(a.class_count);
                            var vb = (b.class_count === null || b.class_count === undefined) ? 0 : Number(b.class_count);
                            return racesSortAsc ? (va - vb) : (vb - va);
                        });
                    } else if (racesSortKey === 'race_count') {
                        sorted.sort(function(a, b) {
                            var va = (a.race_count === null || a.race_count === undefined) ? 0 : Number(a.race_count);
                            var vb = (b.race_count === null || b.race_count === undefined) ? 0 : Number(b.race_count);
                            return racesSortAsc ? (va - vb) : (vb - va);
                        });
                    }
                    tbody.innerHTML = '';
                    sorted.forEach(function(row, i) {
                        var rank = i + 1;
                        var tr = document.createElement('tr');
                        var regattaId = (row.regatta_id != null && row.regatta_id !== '') ? String(row.regatta_id).replace(/</g, '&lt;') : '';
                        var nameEsc = (row.regatta_name != null ? String(row.regatta_name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '');
                        var regattaCell = regattaId ? '<a href="/regatta/' + regattaId + '">' + nameEsc + '</a>' : nameEsc;
                        var dateEsc = (row.date != null ? String(row.date).replace(/</g, '&lt;') : '');
                        var classVal = (row.class_count != null && row.class_count !== '') ? row.class_count : '';
                        var raceVal = (row.race_count != null && row.race_count !== '') ? row.race_count : '';
                        tr.innerHTML = '<td>' + rank + '</td><td>' + regattaCell + '</td><td>' + dateEsc + '</td><td>' + classVal + '</td><td>' + raceVal + '</td>';
                        tbody.appendChild(tr);
                    });
                }
                function bindRacesHeaderClicks() {
                    document.querySelectorAll('#races-table th[data-key]').forEach(function(th) {
                        th.onclick = function(e) {
                            e.stopPropagation();
                            var key = th.getAttribute('data-key');
                            if (racesSortKey === key) {
                                racesSortAsc = !racesSortAsc;
                            } else {
                                racesSortKey = key;
                                racesSortAsc = (key !== 'rank' && key !== 'date' && key !== 'class_count' && key !== 'race_count');
                            }
                            renderRacesBody();
                        };
                    });
                }
                var card4 = document.getElementById('races-card');
                if (card4 && racesPanel) {
                    card4.addEventListener('click', function() {
                        var visible = racesPanel.style.display !== 'none';
                        racesPanel.style.display = visible ? 'none' : 'block';
                        if (!racesLoaded && racesTable) {
                            racesLoaded = true;
                            var tbody = racesTable.querySelector('tbody');
                            if (tbody) tbody.innerHTML = '<tr><td colspan="5">Loading…</td></tr>';
                            fetch('/admin/list/races', { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(data) {
                                racesData = (data.ok && data.rows) ? data.rows : [];
                                if (tbody) tbody.innerHTML = '';
                                renderRacesBody();
                                bindRacesHeaderClicks();
                            }).catch(function() {
                                var tb = racesTable && racesTable.querySelector('tbody');
                                if (tb) tb.innerHTML = '<tr><td colspan="5">Failed to load.</td></tr>';
                            });
                        }
                    });
                }
                var shModal = document.getElementById('sessionHistoryModal');
                var shTitle = document.getElementById('sessionHistoryModalTitle');
                var shBody = document.getElementById('sessionHistoryModalBody');
                var shClose = document.getElementById('sessionHistoryModalClose');
                function closeSessionHistoryModal() { if (shModal) shModal.classList.remove('show'); }
                if (shClose) shClose.addEventListener('click', closeSessionHistoryModal);
                if (shModal) shModal.addEventListener('click', function(e) { if (e.target === shModal) closeSessionHistoryModal(); });
                document.addEventListener('click', function(e) {
                    var link = e.target && e.target.closest && e.target.closest('.session-history-link');
                    if (!link) return;
                    e.preventDefault();
                    var sasId = link.getAttribute('data-sas-id');
                    var name = link.getAttribute('data-name') || 'User';
                    if (!sasId) return;
                    shTitle.textContent = name + ' – Session History';
                    shBody.innerHTML = '<span class="loading">Loading…</span>';
                    shModal.classList.add('show');
                    fetch('/admin/user-session-history/' + encodeURIComponent(sasId), { credentials: 'same-origin' })
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            if (!data.ok) { shBody.innerHTML = '<span class="err">' + (data.error || 'Error') + '</span>'; return; }
                            var h = '';
                            if (data.total_sessions_count != null) h += '<p><strong>Total sessions:</strong> ' + data.total_sessions_count + '</p>';
                            if (data.total_duration_seconds != null) h += '<p><strong>Total time (all sessions):</strong> ' + formatDuration(data.total_duration_seconds) + '</p>';
                            if (data.last_login_iso) h += '<p><strong>Last login:</strong> ' + data.last_login_iso + '</p>';
                            if (data.device) h += '<p><strong>Device:</strong> ' + (data.device || '—') + '</p>';
                            if (data.ip_address) h += '<p><strong>IP:</strong> ' + (data.ip_address || '—') + '</p>';
                            if (data.user_agent) h += '<p><strong>User agent:</strong> <code style="word-break:break-all;font-size:12px;">' + (data.user_agent || '').replace(/</g, '&lt;') + '</code></p>';
                            if (data.active_session) {
                                var s = data.active_session;
                                h += '<h3 style="margin-top:16px;">Current active session</h3>';
                                h += '<p>Login: ' + (s.login_time_iso || '—') + '</p>';
                                h += '<p>Duration: ' + (s.duration_seconds != null ? formatDuration(s.duration_seconds) : '—') + '</p>';
                                if (s.pages && s.pages.length) {
                                    h += '<p><strong>Pages visited:</strong></p><table><thead><tr><th>Page</th><th>Time</th></tr></thead><tbody>';
                                    s.pages.forEach(function(p) { h += '<tr><td>' + (p.path || '').replace(/</g, '&lt;') + '</td><td>' + (p.time_seconds != null ? formatDuration(p.time_seconds) : '—') + '</td></tr>'; });
                                    h += '</tbody></table>';
                                }
                            }
                            if (data.sessions && data.sessions.length) {
                                h += '<h3 style="margin-top:16px;">All sessions</h3><table><thead><tr><th>Login</th><th>Logout</th><th>Duration</th><th>Device</th><th>IP</th></tr></thead><tbody>';
                                data.sessions.forEach(function(s) {
                                    h += '<tr><td>' + (s.login_time_iso || '—') + '</td><td>' + (s.logout_time_iso || '—') + '</td><td>' + (s.duration_seconds != null ? formatDuration(s.duration_seconds) : '—') + '</td><td>' + (s.device || '—').replace(/</g, '&lt;') + '</td><td>' + (s.ip_address || '—').replace(/</g, '&lt;') + '</td></tr>';
                                    if (s.pages && s.pages.length) {
                                        h += '<tr><td colspan="5"><small>Pages: ' + s.pages.map(function(p) { return (p.path || '').replace(/</g, '&lt;'); }).join(' → ') + '</small></td></tr>';
                                    }
                                });
                                h += '</tbody></table>';
                            }
                            if (!h) h = '<p>No session data.</p>';
                            shBody.innerHTML = h;
                        })
                        .catch(function(err) { shBody.innerHTML = '<span class="err">' + (err.message || 'Error') + '</span>'; });
                });
                var restartModal = document.getElementById('adminRestartModal');
                var restartBtn = document.getElementById('adminRestartBtn');
                var restartConfirm = document.getElementById('adminRestartConfirm');
                var restartCancel = document.getElementById('adminRestartCancel');
                var restartStatusEl = document.getElementById('restartStatus');
                if (restartBtn) restartBtn.addEventListener('click', function() {
                    if (restartModal) restartModal.classList.add('show');
                });
                if (restartCancel) restartCancel.addEventListener('click', function() {
                    if (restartModal) { restartModal.classList.remove('show'); restartModal.style.display = 'none'; }
                    document.querySelectorAll('.modal-backdrop').forEach(function(e) { e.remove(); });
                });
                if (restartConfirm) restartConfirm.addEventListener('click', function() {
                    if (restartModal) { restartModal.classList.remove('show'); restartModal.style.display = 'none'; }
                    document.querySelectorAll('.modal-backdrop').forEach(function(e) { e.remove(); });
                    restartBtn.disabled = true;
                    restartBtn.textContent = 'Restarting...';
                    if (restartStatusEl) { restartStatusEl.textContent = 'Restarting service...'; restartStatusEl.style.display = 'inline'; }
                    var initialStart = apiUptimeEl ? parseInt(apiUptimeEl.dataset.startTs, 10) : null;
                    fetch('/admin/api/restart', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' }).catch(function() {});
                    var pollStart = Date.now();
                    var poll = setInterval(function() {
                        if (Date.now() - pollStart > 90000) {
                            clearInterval(poll);
                            if (restartStatusEl) { restartStatusEl.innerText = 'Timed out'; restartStatusEl.style.display = 'inline'; }
                            restartBtn.disabled = false;
                            restartBtn.innerText = 'Restart API';
                            setTimeout(function() { if (restartStatusEl) { restartStatusEl.style.display = 'none'; restartStatusEl.textContent = ''; } }, 3000);
                            return;
                        }
                        fetch('/admin/dashboard-data?t=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' }).then(function(r) {
                            if (!r.ok) return;
                            return r.json();
                        }).then(function(d) {
                            if (!d) return;
                            var serverTs = d.server_start_timestamp != null ? Number(d.server_start_timestamp) : NaN;
                            if (!isNaN(serverTs) && initialStart != null && serverTs !== initialStart) {
                                clearInterval(poll);
                                var newTs = serverTs;
                                if (apiUptimeEl) {
                                    apiUptimeEl.dataset.startTs = String(newTs);
                                    tickUptime();
                                    updateRestartTime(newTs);
                                }
                                if (restartStatusEl) { restartStatusEl.innerText = 'API restarted'; restartStatusEl.style.display = 'inline'; }
                                restartBtn.disabled = false;
                                restartBtn.innerText = 'Restart API';
                                setTimeout(function() { if (restartStatusEl) { restartStatusEl.style.display = 'none'; restartStatusEl.textContent = ''; } }, 3000);
                            }
                        }).catch(function() {});
                    }, 2000);
                });
            })();
