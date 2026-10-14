/**
 * Club-page Event Management (Phase A). Injects Claim / Activate / Add only
 * for Super Admin (any club) or the officer of this page. Visitors unchanged.
 */
(function () {
    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    var SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var NO_REGATTA = { training: 1, external: 1, informal: 1, cruise: 1, ops: 1, duty: 1 };
    var KINDS = ['race', 'training', 'external', 'informal', 'cruise', 'ops'];

    var state = {
        me: null,
        club: '',
        events: [],
        regattas: [],
        raceClasses: [],
        seasonItems: [],
        previousEditions: [],
        step: 'details',
        mode: null,
        event: null,
        match: null,
        message: '',
        entryRows: [],
        preview: null,
        previewFile: null,
        statusLine: ''
    };

    function esc(s) {
        if (s == null) return '';
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function pageClub() {
        var root = document.querySelector('.club-page');
        var attr = root && root.getAttribute('data-club-abbrev');
        if (attr) return String(attr).trim().toLowerCase();
        var m = (location.pathname || '').match(/\/club\/([^/?#]+)/i);
        return m ? decodeURIComponent(m[1]).trim().toLowerCase() : '';
    }

    function sessQ(url) {
        var s = new URLSearchParams(location.search).get('session');
        if (!s) return url;
        return url + (url.indexOf('?') >= 0 ? '&' : '?') + 'session=' + encodeURIComponent(s);
    }

    async function j(url, opt) {
        var r = await fetch(sessQ(url), Object.assign({
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' }
        }, opt || {}));
        var b = null;
        try { b = await r.json(); } catch (e) { b = {}; }
        if (!r.ok) throw new Error((b && b.detail) || r.statusText || 'Request failed');
        return b;
    }

    function canManage(me) {
        if (!me) return false;
        if (me.is_super_admin || me.can_manage_all_clubs || me.role === 'super_admin') return true;
        if (!me.is_club_admin && me.role !== 'club_admin' && me.role !== 'club_manager') return false;
        var mine = String(me.club_abbrev || '').trim().toLowerCase();
        return !!(mine && mine === state.club);
    }

    function yearStrip(name) {
        return String(name || '').toLowerCase().replace(/\b(?:19|20)\d{2}\b/g, ' ')
            .replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
    }

    function parseCardDates(text) {
        var m = String(text || '').match(/(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})(?:\s*(?:→|->)\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4}))?/);
        if (!m) return { start: '', end: '' };
        function iso(d, mon, y) {
            var i = SHORT.findIndex(function (x) { return x.toLowerCase() === String(mon).toLowerCase(); });
            if (i < 0) return '';
            return y + '-' + String(i + 1).padStart(2, '0') + '-' + String(parseInt(d, 10)).padStart(2, '0');
        }
        var start = iso(m[1], m[2], m[3]);
        var end = m[4] ? iso(m[4], m[5], m[6]) : start;
        return { start: start, end: end };
    }

    function formatShort(iso) {
        if (!iso) return '—';
        var p = String(iso).slice(0, 10).split('-');
        if (p.length !== 3) return esc(iso);
        var m = parseInt(p[1], 10) - 1;
        var d = parseInt(p[2], 10);
        if (m < 0 || m > 11 || !d) return esc(iso);
        return d + ' ' + SHORT[m] + ' ' + p[0];
    }

    function formatStatusLine(status, asAt) {
        var word = (status || '').trim() || 'Provisional';
        if (!asAt) return 'Results are ' + word + ' (snapshot time not recorded)';
        var s = String(asAt).trim().replace('T', ' ').replace('Z', '');
        var m = s.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
        if (!m) {
            var d2 = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
            if (!d2) return 'Results are ' + word + ' (snapshot time not recorded)';
            return 'Results are ' + word + ' as at ' + parseInt(d2[3], 10) + ' ' + MONTHS[parseInt(d2[2], 10) - 1] + ' ' + d2[1] + ' at 00:00';
        }
        return 'Results are ' + word + ' as at ' + parseInt(m[3], 10) + ' ' + MONTHS[parseInt(m[2], 10) - 1] + ' ' + m[1] + ' at ' + m[4] + ':' + m[5];
    }

    function findHosted(name, start) {
        var key = yearStrip(name);
        var best = null;
        (state.events || []).forEach(function (e) {
            var sameName = yearStrip(e.event_name) === key || yearStrip(e.event_name).indexOf(key) >= 0 || key.indexOf(yearStrip(e.event_name)) >= 0;
            if (!sameName) return;
            var ds = String(e.start_date || '').slice(0, 10);
            if (start && ds && ds !== start) {
                if (!best) best = e;
                return;
            }
            best = e;
        });
        return best;
    }

    function previousClasses(name) {
        var key = yearStrip(name);
        var names = [];
        function add(list) {
            (list || []).forEach(function (n) {
                if (n && names.indexOf(n) < 0) names.push(n);
            });
        }
        (state.regattas || []).forEach(function (r) {
            if (yearStrip(r.event_name) === key) {
                add((r.blocks || []).map(function (b) { return b.class_name; }));
            }
        });
        (state.previousEditions || []).forEach(function (p) {
            if (yearStrip(p.event_name) === key) add(p.class_names);
        });
        return names;
    }

    function classOptions(selected) {
        var html = '<option value="">Class</option>';
        (state.raceClasses || []).forEach(function (c) {
            var sel = (selected != null && String(c.class_id) === String(selected)) ? ' selected' : '';
            html += '<option value="' + esc(c.class_id) + '"' + sel + '>' + esc(c.class_name) + '</option>';
        });
        return html;
    }

    function kindOptions(selected) {
        return KINDS.map(function (k) {
            return '<option value="' + k + '"' + (k === selected ? ' selected' : '') + '>' + k + '</option>';
        }).join('');
    }

    function isRaceKind(kind) {
        return !NO_REGATTA[String(kind || 'race')];
    }

    function btnClass() {
        return document.querySelector('.sa-home-regatta-actions') ? 'sa-home-regatta-btn' : 'event-details-btn';
    }

    function addChip(actions, label, onClick) {
        if (!actions || actions.querySelector('[data-club-wz]')) return;
        var b = document.createElement('button');
        b.type = 'button';
        b.className = btnClass();
        b.setAttribute('data-club-wz', '1');
        b.textContent = label;
        b.addEventListener('click', function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            onClick();
        });
        actions.appendChild(b);
    }

    function enhanceLiveCards() {
        document.querySelectorAll('.sa-home-regatta-card').forEach(function (card) {
            var past = card.classList.contains('ec-past-results') || !!(card.querySelector('a.sa-home-regatta-title[href^="/regatta/"]'));
            var titleEl = card.querySelector('.sa-home-regatta-title');
            var name = (titleEl && titleEl.textContent || '').trim();
            var pill = card.querySelector('.sa-home-regatta-meta-pill span');
            var dates = parseCardDates(pill && pill.textContent);
            var actions = card.querySelector('.sa-home-regatta-actions');
            if (!actions || !name) return;
            if (past) return;
            var hosted = findHosted(name, dates.start);
            if (hosted && hosted.regatta_id) {
                addChip(actions, 'Manage', function () { openExisting(hosted, 'manage'); });
            } else if (hosted) {
                addChip(actions, 'Activate Club Event', function () { activateEvent(hosted, name, dates); });
            } else {
                addChip(actions, 'Claim SAS Event', function () { startClaim(name, dates); });
            }
        });
    }

    function enhanceCarouselCards() {
        var raw = document.getElementById('events-data');
        if (!raw) return;
        var data;
        try { data = JSON.parse(raw.textContent || '{}'); } catch (e) { return; }
        var all = [].concat(data.upcoming || [], data.live || []);
        document.querySelectorAll('.event-card').forEach(function (card, idx) {
            var actions = card.querySelector('.event-card-actions');
            if (!actions) return;
            var ev = all[idx] || all.filter(function (e) {
                return (e.event_name || '') === (card.querySelector('h3') && card.querySelector('h3').textContent || '');
            })[0];
            if (!ev || !ev.event_id) return;
            var hosted = findHosted(ev.event_name, ev.start_date_iso);
            var row = hosted || { event_id: ev.event_id, event_name: ev.event_name, start_date: ev.start_date_iso, end_date: ev.end_date_iso, regatta_id: ev.regatta_id, category: ev.event_type, venue_text: ev.location };
            if (row.regatta_id) addChip(actions, 'Manage', function () { openExisting(row, 'manage'); });
            else addChip(actions, 'Activate', function () { activateEvent(row, row.event_name, { start: row.start_date, end: row.end_date }); });
        });
    }

    function addHeadingButton() {
        if (document.getElementById('club-wz-add')) return;
        var liveSec = document.querySelector('.club-upcoming-events-section');
        var dash = document.querySelector('.club-events-dashboard .events-section-heading-row');
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'club-wz-add';
        btn.className = btnClass();
        btn.setAttribute('data-club-wz', '1');
        btn.textContent = 'Add New Event';
        btn.addEventListener('click', function (ev) {
            ev.preventDefault();
            startAdd();
        });
        if (liveSec) {
            var filter = liveSec.querySelector('.club-home-card-filter');
            if (filter && filter.parentNode) filter.parentNode.insertBefore(btn, filter.nextSibling);
            else liveSec.querySelector('h2.section-title') && liveSec.querySelector('h2.section-title').appendChild(btn);
        } else if (dash) {
            dash.appendChild(btn);
        }
    }

    function wizardHost() {
        return document.querySelector('.club-upcoming-events-section')
            || document.querySelector('.club-events-dashboard')
            || document.querySelector('.club-content')
            || document.querySelector('.club-page');
    }

    function closeWizard() {
        var el = document.getElementById('club-event-wizard');
        if (el && el.parentNode) el.parentNode.removeChild(el);
        state.mode = null;
        state.event = null;
        state.match = null;
        state.message = '';
        state.preview = null;
        state.previewFile = null;
        if (history.replaceState) {
            var u = new URL(location.href);
            u.searchParams.delete('event');
            history.replaceState({}, '', u.pathname + (u.searchParams.toString() ? '?' + u.searchParams.toString() : '') + u.hash);
        }
    }

    function openWizard() {
        var host = wizardHost();
        if (!host) return;
        var card = document.getElementById('club-event-wizard');
        if (!card) {
            card = document.createElement('div');
            card.id = 'club-event-wizard';
            card.className = 'card stats-section';
            if (host.nextSibling) host.parentNode.insertBefore(card, host.nextSibling);
            else host.appendChild(card);
        }
        renderWizard();
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function ev() { return state.event || {}; }

    function raceStepsVisible() {
        return isRaceKind((ev().kind) || (state.mode === 'add' ? (document.getElementById('wz-kind') || {}).value : 'race')) && !!(ev().regatta_id);
    }

    function renderWizard() {
        var card = document.getElementById('club-event-wizard');
        if (!card) return;
        var e = ev();
        var title = state.mode === 'add' ? 'Add New Event' : (state.mode === 'claim' ? 'Claim SAS Event' : (e.regatta_id ? 'Manage event' : 'Activate Club Event'));
        var links = [{ href: '#club-wz-details', label: 'Details', step: 'details' }];
        if (raceStepsVisible()) {
            links = links.concat([
                { href: '#club-wz-fleets', label: 'Fleets', step: 'fleets' },
                { href: '#club-wz-reg', label: 'Registration', step: 'reg' },
                { href: '#club-wz-entries', label: 'Entries', step: 'entries' },
                { href: '#club-wz-upload', label: 'Upload', step: 'upload' },
                { href: '#club-wz-publish', label: 'Publish', step: 'publish' }
            ]);
        }
        var stats = '<div class="class-stats">' + links.map(function (l) {
            return '<a class="stats-link" href="' + l.href + '" data-wz-step="' + l.step + '">' + esc(l.label) + '</a>';
        }).join('') + '</div>';
        var body = tableForStep(state.step);
        card.innerHTML = '<h2 class="section-title">' + esc(title) + '</h2>'
            + stats
            + (state.message ? '<p>' + esc(state.message) + '</p>' : '')
            + '<div class="table-container">' + body + '</div>'
            + '<p><a href="#club-event-wizard" id="wz-close">Back to events</a></p>';
        bindWizard();
    }

    function tableForStep(step) {
        if (step === 'fleets') return fleetsTable();
        if (step === 'reg') return regTable();
        if (step === 'entries') return entriesTable();
        if (step === 'upload') return uploadTable();
        if (step === 'publish') return publishTable();
        return detailsTable();
    }

    function detailsTable() {
        var e = ev();
        var prev = previousClasses(e.event_name || (document.getElementById('wz-title') && document.getElementById('wz-title').value) || '');
        var last = prev.length ? ('Last year classes: ' + prev.join(', ')) : 'No previous edition classes found.';
        var matches = (state.match && state.match.matches) || [];
        var matchRows = '';
        matches.forEach(function (m) {
            var act = m.action === 'activate' ? 'Activate Club Event' : (m.action === 'manage' ? 'Manage' : 'Claim SAS Event');
            matchRows += '<tr><td>' + esc(m.event_name) + '</td><td>' + esc(formatShort(m.start_date)) + '</td><td>'
                + esc(m.host_display || '—') + '</td><td>' + esc(m.category || '—') + '</td><td><button type="button" class="btn js-wz-pick" data-event-id="'
                + esc(m.event_id) + '" data-action="' + esc(m.action) + '">' + act + '</button></td></tr>';
        });
        return '<table class="table"><tbody>'
            + '<tr><th>Name</th><td><input id="wz-title" value="' + esc(e.event_name || '') + '"></td></tr>'
            + '<tr><th>Start</th><td><input id="wz-start" type="date" value="' + esc((e.start_date || '').slice(0, 10)) + '"></td></tr>'
            + '<tr><th>End</th><td><input id="wz-end" type="date" value="' + esc((e.end_date || e.start_date || '').slice(0, 10)) + '"></td></tr>'
            + '<tr><th>Venue</th><td><input id="wz-venue" value="' + esc(e.venue_text || '') + '"></td></tr>'
            + '<tr><th>Type</th><td>' + esc(e.category || '—') + '</td></tr>'
            + '<tr><th>Kind</th><td><select id="wz-kind">' + kindOptions(e.kind || (state.mode === 'claim' ? 'external' : 'race')) + '</select></td></tr>'
            + '<tr><td colspan="2">' + esc(last) + '</td></tr>'
            + '</tbody></table>'
            + (matchRows ? '<table class="table"><thead><tr><th>SAS / club match</th><th>Date</th><th>Host</th><th>Category</th><th></th></tr></thead><tbody>'
                + matchRows + '</tbody></table>' : '')
            + '<p><button type="button" class="btn" id="wz-match">Check matches</button> '
            + '<button type="button" class="btn" id="wz-save">' + saveLabel() + '</button></p>';
    }

    function saveLabel() {
        if (state.mode === 'add') return 'Add event';
        if (state.mode === 'claim') return 'Claim SAS Event';
        if (ev().regatta_id) return 'Save details';
        return 'Activate Club Event';
    }

    function fleetsTable() {
        var e = ev();
        var r = (state.regattas || []).filter(function (x) { return x.regatta_id === e.regatta_id; })[0];
        var blocks = (r && r.blocks) || [];
        var rows = blocks.map(function (b) {
            return '<tr><td>' + esc(b.class_name || '—') + '</td><td>' + esc(b.races_sailed != null ? b.races_sailed : 0) + '</td></tr>';
        }).join('');
        var suggest = previousClasses(e.event_name);
        return '<table class="table"><thead><tr><th>Class</th><th>Races sailed</th></tr></thead><tbody>'
            + (rows || '<tr><td colspan="2">No fleets yet. Confirm a class — last year is a suggestion only.</td></tr>')
            + '<tr><td><select id="wz-fleet-class">' + classOptions() + '</select></td>'
            + '<td><button type="button" class="btn" id="wz-fleet-add">Add fleet</button></td></tr>'
            + '</tbody></table>'
            + (suggest.length ? '<p>Suggested from previous edition: ' + esc(suggest.join(', ')) + '</p>' : '');
    }

    function regTable() {
        var e = ev();
        return '<table class="table"><tbody><tr><td><select id="wz-entry-open">'
            + '<option value="false"' + (e.entry_open ? '' : ' selected') + '>Closed</option>'
            + '<option value="true"' + (e.entry_open ? ' selected' : '') + '>Open</option>'
            + '</select></td><td><button type="button" class="btn" id="wz-entry-open-btn">Set entries</button></td></tr></tbody></table>';
    }

    function entriesTable() {
        var rows = (state.entryRows || []).map(function (row) {
            return '<tr><td>' + esc(row.helm_name || '—') + '</td><td>' + esc(row.sail_number || '—')
                + '</td><td>' + esc(row.class_name || '—') + '</td></tr>';
        }).join('');
        return '<table class="table"><thead><tr><th>Helm</th><th>Sail no</th><th>Class</th></tr></thead><tbody>'
            + (rows || '<tr><td colspan="3">No entries yet.</td></tr>')
            + '<tr><td><input id="wz-entry-helm" placeholder="Helm name"></td>'
            + '<td><input id="wz-entry-sail" placeholder="Sail no"></td>'
            + '<td><select id="wz-entry-class">' + classOptions() + '</select> '
            + '<input id="wz-entry-sas" placeholder="SAS ID"> '
            + '<button type="button" class="btn" id="wz-entry-add">Add</button></td></tr>'
            + '</tbody></table>';
    }

    function uploadTable() {
        var html = '<table class="table"><tbody><tr>'
            + '<td><input type="file" id="wz-file" accept=".html,.htm,.csv,text/html,text/csv"></td>'
            + '<td><button type="button" class="btn" id="wz-preview">Preview</button></td>'
            + '<td><button type="button" class="btn" id="wz-commit"'
            + (state.preview && state.preview.preview_token ? '' : ' disabled')
            + '>Commit scores</button></td></tr></tbody></table>';
        var prev = state.preview;
        if (prev && (prev.rows || []).length) {
            html += '<table class="table"><thead><tr><th>Class</th><th>Sail no</th><th>Helm</th><th>Place</th></tr></thead><tbody>'
                + prev.rows.map(function (row) {
                    return '<tr><td>' + esc(row.class_label || '—') + '</td><td>' + esc(row.sail_number || '—')
                        + '</td><td>' + esc(row.helm_name || '—') + '</td><td>' + esc(row.rank != null ? row.rank : '—') + '</td></tr>';
                }).join('') + '</tbody></table>';
        }
        return html;
    }

    function publishTable() {
        var e = ev();
        var r = (state.regattas || []).filter(function (x) { return x.regatta_id === e.regatta_id; })[0] || {};
        var current = r.result_status || 'Provisional';
        var line = state.statusLine || ('Results are ' + current + ' (snapshot time not recorded)');
        var link = e.regatta_id ? '<a href="/regatta/' + encodeURIComponent(e.regatta_id) + '">View public results</a>' : '—';
        return '<table class="table"><tbody>'
            + '<tr><td colspan="2">' + esc(line) + '</td></tr>'
            + '<tr><td><select id="wz-status"><option' + (current === 'Provisional' ? ' selected' : '') + '>Provisional</option>'
            + '<option' + (current === 'Final' ? ' selected' : '') + '>Final</option></select></td>'
            + '<td><button type="button" class="btn" id="wz-publish">Publish</button></td></tr>'
            + '<tr><td colspan="2">' + link + '</td></tr></tbody></table>';
    }

    function bindWizard() {
        document.querySelectorAll('#club-event-wizard [data-wz-step]').forEach(function (a) {
            a.addEventListener('click', function (ev) {
                ev.preventDefault();
                state.step = a.getAttribute('data-wz-step') || 'details';
                renderWizard();
            });
        });
        var close = document.getElementById('wz-close');
        if (close) close.addEventListener('click', function (ev) { ev.preventDefault(); closeWizard(); });
        var matchBtn = document.getElementById('wz-match');
        if (matchBtn) matchBtn.addEventListener('click', runMatch);
        var save = document.getElementById('wz-save');
        if (save) save.addEventListener('click', onSave);
        document.querySelectorAll('.js-wz-pick').forEach(function (b) {
            b.addEventListener('click', function () {
                pickMatch(b.getAttribute('data-event-id'), b.getAttribute('data-action'));
            });
        });
        var fleet = document.getElementById('wz-fleet-add');
        if (fleet) fleet.addEventListener('click', onAddFleet);
        var openBtn = document.getElementById('wz-entry-open-btn');
        if (openBtn) openBtn.addEventListener('click', onSetOpen);
        var addEntry = document.getElementById('wz-entry-add');
        if (addEntry) addEntry.addEventListener('click', onAddEntry);
        var preview = document.getElementById('wz-preview');
        if (preview) preview.addEventListener('click', onPreview);
        var commit = document.getElementById('wz-commit');
        if (commit) commit.addEventListener('click', onCommit);
        var pub = document.getElementById('wz-publish');
        if (pub) pub.addEventListener('click', onPublish);
    }

    function formDetails() {
        return {
            title: ((document.getElementById('wz-title') || {}).value || '').trim(),
            start_date: ((document.getElementById('wz-start') || {}).value || '').trim(),
            end_date: ((document.getElementById('wz-end') || {}).value || '').trim(),
            venue_text: ((document.getElementById('wz-venue') || {}).value || '').trim(),
            kind: ((document.getElementById('wz-kind') || {}).value || 'race')
        };
    }

    async function runMatch() {
        var f = formDetails();
        if (!f.title) { state.message = 'Name is required to match.'; renderWizard(); return; }
        try {
            var q = '/api/club/events/match?club=' + encodeURIComponent(state.club)
                + '&name=' + encodeURIComponent(f.title);
            if (f.start_date) q += '&start=' + encodeURIComponent(f.start_date);
            if (f.end_date) q += '&end=' + encodeURIComponent(f.end_date);
            state.match = await j(q);
            state.message = (state.match.matches || []).length
                ? 'Matching SAS / club rows found. Claim or Activate instead of adding a second URL.'
                : 'No SAS match. You can add this as a club row.';
            renderWizard();
        } catch (err) {
            state.message = err.message || 'Match failed';
            renderWizard();
        }
    }

    async function pickMatch(eventId, action) {
        var row = ((state.match && state.match.matches) || []).filter(function (m) {
            return String(m.event_id) === String(eventId);
        })[0];
        if (!row) return;
        if (action === 'manage') {
            var hosted = findHosted(row.event_name, row.start_date) || row;
            await openExisting(hosted, 'manage');
            return;
        }
        if (action === 'activate') {
            await activateEvent(row, row.event_name, { start: row.start_date, end: row.end_date });
            return;
        }
        await claimEvent(row, 'external', false, false);
    }

    async function onSave() {
        var f = formDetails();
        if (!f.title || !f.start_date) {
            state.message = 'Name and start date are required.';
            renderWizard();
            return;
        }
        try {
            if (state.mode === 'add') {
                if (!state.match) await runMatch();
                var hits = (state.match && state.match.matches) || [];
                if (hits.length) {
                    state.message = 'A matching event already exists. Use Claim or Activate on the match table.';
                    renderWizard();
                    return;
                }
                if (isRaceKind(f.kind)) {
                    var created = await j('/api/club/events', {
                        method: 'POST',
                        body: JSON.stringify({
                            club: state.club,
                            title: f.title,
                            start_date: f.start_date,
                            end_date: f.end_date || f.start_date,
                            venue_text: f.venue_text,
                            kind: f.kind,
                            create_regatta: true
                        })
                    });
                    await reload();
                    state.event = findById(created.event_id) || Object.assign({}, f, created, { event_name: f.title });
                    state.mode = 'manage';
                    state.step = 'fleets';
                    state.message = created.created_regatta ? 'Race created.' : 'Event saved without a results URL.';
                } else {
                    await j('/api/club/season-items', {
                        method: 'POST',
                        body: JSON.stringify({
                            club: state.club,
                            title: f.title,
                            start_date: f.start_date,
                            end_date: f.end_date || f.start_date,
                            kind: f.kind,
                            create_regatta: false
                        })
                    });
                    await reload();
                    state.event = { event_name: f.title, start_date: f.start_date, end_date: f.end_date, kind: f.kind };
                    state.message = 'Calendar row saved. No regatta created.';
                }
                renderWizard();
                return;
            }
            if (state.mode === 'claim' && eId()) {
                await claimEvent(ev(), f.kind, false, false);
                return;
            }
            if (eId() && !ev().regatta_id && isRaceKind(f.kind)) {
                await activateEvent(ev(), f.title, { start: f.start_date, end: f.end_date });
                return;
            }
            if (eId()) {
                await j('/api/club/events/' + encodeURIComponent(eId()) + '?club=' + encodeURIComponent(state.club), {
                    method: 'PATCH',
                    body: JSON.stringify({ title: f.title, start_date: f.start_date, end_date: f.end_date || f.start_date, venue_text: f.venue_text })
                });
                await reload();
                state.event = findById(eId()) || ev();
                state.message = 'Details saved.';
                renderWizard();
            }
        } catch (err) {
            state.message = err.message || 'Save failed';
            renderWizard();
        }
    }

    function eId() { return ev().event_id; }

    function findById(id) {
        return (state.events || []).filter(function (e) { return String(e.event_id) === String(id); })[0] || null;
    }

    async function claimEvent(row, kind, createRegatta, assignHost) {
        var q = '/api/club/events/' + encodeURIComponent(row.event_id) + '/claim?club=' + encodeURIComponent(state.club)
            + '&create_regatta=' + (createRegatta ? 'true' : 'false')
            + '&assign_host=' + (assignHost ? 'true' : 'false')
            + '&kind=' + encodeURIComponent(kind || 'external');
        var out = await j(q, { method: 'POST' });
        await reload();
        state.event = findById(out.event_id) || Object.assign({}, row, out);
        state.event.kind = kind;
        state.mode = out.regatta_id ? 'manage' : 'claim';
        state.step = 'details';
        state.message = out.created_regatta
            ? 'Activated. Results URL created.'
            : (assignHost ? 'Host set. No new results URL.' : 'Claimed. Existing host and slug kept.');
        openWizard();
    }

    async function activateEvent(row, name, dates) {
        state.mode = 'activate';
        state.event = Object.assign({}, row, {
            event_name: name || row.event_name,
            start_date: (dates && dates.start) || row.start_date,
            end_date: (dates && dates.end) || row.end_date,
            kind: 'race'
        });
        state.step = 'details';
        if (row.event_id) {
            try {
                await claimEvent(row, 'race', true, true);
                state.step = ev().regatta_id ? 'fleets' : 'details';
                return;
            } catch (err) {
                state.message = err.message || 'Activate failed';
            }
        }
        openWizard();
    }

    async function openExisting(row, mode) {
        state.mode = mode || 'manage';
        state.event = findById(row.event_id) || row;
        state.step = state.event.regatta_id ? 'details' : 'details';
        await loadEntries();
        openWizard();
    }

    function startAdd() {
        state.mode = 'add';
        state.event = { kind: 'race', entry_open: false };
        state.match = null;
        state.step = 'details';
        state.message = 'Check matches before adding. Training / informal / cruise never create a results URL.';
        openWizard();
    }

    async function startClaim(name, dates) {
        state.mode = 'add';
        state.event = { event_name: name, start_date: dates.start, end_date: dates.end, kind: 'external' };
        state.step = 'details';
        state.message = '';
        openWizard();
        await runMatch();
    }

    async function onAddFleet() {
        var e = ev();
        if (!e.regatta_id) { state.message = 'Activate a race first.'; renderWizard(); return; }
        var classId = (document.getElementById('wz-fleet-class') || {}).value || '';
        if (!classId) { state.message = 'Choose a class.'; renderWizard(); return; }
        try {
            await j('/api/club/regattas/' + encodeURIComponent(e.regatta_id) + '/classes', {
                method: 'POST',
                body: JSON.stringify({ class_id: parseInt(classId, 10) })
            });
            await reload();
            state.event = findById(e.event_id) || e;
            state.message = 'Fleet added.';
            renderWizard();
        } catch (err) {
            state.message = err.message || 'Fleet failed';
            renderWizard();
        }
    }

    async function onSetOpen() {
        var e = ev();
        if (!e.event_id) return;
        var open = (document.getElementById('wz-entry-open') || {}).value === 'true';
        try {
            await j('/api/club/events/' + encodeURIComponent(e.event_id), {
                method: 'PATCH',
                body: JSON.stringify({ entry_open: open })
            });
            await reload();
            state.event = findById(e.event_id) || e;
            state.message = open ? 'Entries opened.' : 'Entries closed.';
            renderWizard();
        } catch (err) {
            state.message = err.message || 'Update failed';
            renderWizard();
        }
    }

    async function onAddEntry() {
        var e = ev();
        if (!e.regatta_id) return;
        var sail = ((document.getElementById('wz-entry-sail') || {}).value || '').trim();
        if (!sail) { state.message = 'Sail number is required.'; renderWizard(); return; }
        var body = { sail_number: sail };
        var helm = ((document.getElementById('wz-entry-helm') || {}).value || '').trim();
        var sas = ((document.getElementById('wz-entry-sas') || {}).value || '').trim();
        var classId = (document.getElementById('wz-entry-class') || {}).value || '';
        if (helm) body.helm_name = helm;
        if (sas) body.sas_id = sas;
        if (classId) body.class_id = parseInt(classId, 10);
        try {
            await j('/api/club/regattas/' + encodeURIComponent(e.regatta_id) + '/entries', {
                method: 'POST',
                body: JSON.stringify(body)
            });
            await loadEntries();
            state.message = 'Entry added.';
            renderWizard();
        } catch (err) {
            state.message = err.message || 'Entry failed';
            renderWizard();
        }
    }

    async function onPreview() {
        var e = ev();
        if (!e.regatta_id) return;
        var input = document.getElementById('wz-file');
        var file = input && input.files && input.files[0];
        if (!file) { state.message = 'Choose a Sailwave HTML or CSV file.'; renderWizard(); return; }
        var body = new FormData();
        body.append('file', file);
        try {
            var r = await fetch(sessQ('/api/club/regattas/' + encodeURIComponent(e.regatta_id) + '/ingest/preview'), {
                method: 'POST', credentials: 'same-origin', body: body
            });
            var pb = await r.json();
            if (!r.ok) throw new Error((pb && pb.detail) || 'Preview failed');
            state.preview = pb;
            state.previewFile = file;
            state.message = 'Previewed ' + (pb.count || (pb.rows || []).length || 0) + ' rows. Review, then Commit.';
            renderWizard();
        } catch (err) {
            state.preview = null;
            state.previewFile = null;
            state.message = err.message || 'Preview failed';
            renderWizard();
        }
    }

    async function onCommit() {
        var e = ev();
        if (!e.regatta_id || !state.preview || !state.preview.preview_token || !state.previewFile) {
            state.message = 'Preview first, then commit.';
            renderWizard();
            return;
        }
        var body = new FormData();
        body.append('file', state.previewFile);
        body.append('preview_token', state.preview.preview_token);
        try {
            var r = await fetch(sessQ('/api/club/regattas/' + encodeURIComponent(e.regatta_id) + '/ingest/commit'), {
                method: 'POST', credentials: 'same-origin', body: body
            });
            var cb = await r.json();
            if (!r.ok) throw new Error((cb && cb.detail) || 'Commit failed');
            state.preview = null;
            state.previewFile = null;
            await reload();
            state.event = findById(e.event_id) || e;
            state.message = 'Committed ' + (cb.rows_updated || 0) + ' updated, ' + (cb.rows_added || 0) + ' added.';
            renderWizard();
        } catch (err) {
            state.message = err.message || 'Commit failed';
            renderWizard();
        }
    }

    async function onPublish() {
        var e = ev();
        if (!e.regatta_id) return;
        var status = (document.getElementById('wz-status') || {}).value || 'Provisional';
        try {
            await j('/api/club/regattas/' + encodeURIComponent(e.regatta_id) + '/result-status', {
                method: 'PATCH',
                body: JSON.stringify({ result_status: status })
            });
            await reload();
            state.event = findById(e.event_id) || e;
            state.message = 'Published as ' + status + '.';
            renderWizard();
        } catch (err) {
            state.message = err.message || 'Publish failed';
            renderWizard();
        }
    }

    async function loadEntries() {
        var e = ev();
        state.entryRows = [];
        state.statusLine = '';
        if (!e || !e.regatta_id) return;
        try {
            var rows = await j('/api/regatta/' + encodeURIComponent(e.regatta_id));
            if (!Array.isArray(rows)) rows = [];
            state.entryRows = rows.filter(function (row) { return row && row.result_id; });
            var first = rows[0] || {};
            var r = (state.regattas || []).filter(function (x) { return x.regatta_id === e.regatta_id; })[0] || {};
            state.statusLine = formatStatusLine(r.result_status || first.result_status, first.as_at_time);
        } catch (err) {
            state.entryRows = [];
        }
    }

    async function reload() {
        var data = await j('/api/club/me/events?club=' + encodeURIComponent(state.club));
        state.events = data.events || [];
        state.regattas = data.regattas || [];
        state.raceClasses = data.race_classes || [];
        state.seasonItems = data.season_items || [];
        state.previousEditions = data.previous_editions || [];
    }

    async function boot() {
        state.club = pageClub();
        if (!state.club) return;
        var me;
        try {
            me = await j('/api/club/me');
        } catch (err) {
            return;
        }
        state.me = me;
        if (!canManage(me)) return;
        try {
            await reload();
        } catch (err) {
            return;
        }
        addHeadingButton();
        enhanceLiveCards();
        enhanceCarouselCards();
        var qEvent = new URLSearchParams(location.search).get('event');
        if (qEvent) {
            var row = findById(qEvent);
            if (row) openExisting(row, row.regatta_id ? 'manage' : 'activate');
        }
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
