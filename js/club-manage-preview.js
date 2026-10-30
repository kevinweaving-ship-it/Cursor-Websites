/**
 * Club-manage preview: approved layout on /club-manage-preview only.
 * Reuses buildMasterPageLayout, .card, .table, .stats-link. IDs stay in JS.
 */
(function () {
    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    var SHORT_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    var state = {
        me: null,
        events: [],
        regattas: [],
        raceClasses: [],
        selectedEventId: null,
        selectedRegattaId: null,
        preview: null,
        previewFile: null,
        entryRows: [],
        statusLine: '',
        message: ''
    };

    function esc(s) {
        if (s == null || s === undefined) return '';
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function sessQ(url) {
        var s = new URLSearchParams(window.location.search).get('session');
        if (!s) return url;
        return url + (url.indexOf('?') >= 0 ? '&' : '?') + 'session=' + encodeURIComponent(s);
    }

    async function j(url, opt) {
        var headers = { 'Content-Type': 'application/json' };
        var r = await fetch(sessQ(url), Object.assign({
            credentials: 'same-origin',
            headers: headers
        }, opt || {}));
        var b = null;
        try { b = await r.json(); } catch (e) { b = {}; }
        if (r.status === 401) {
            window.location.replace('/login.html?returnTo=/club-manage-preview');
            throw new Error('Login required');
        }
        if (!r.ok) throw new Error((b && b.detail) || r.statusText || 'Request failed');
        return b;
    }

    function buildMasterPageLayout(container, opts) {
        if (!container || !opts) return;
        var back = (opts.backLink !== false) ? '<a href="/" class="js-go-home" style="margin-bottom:12px;padding:6px 12px;font-size:13px;font-weight:600;color:#fff;background:#001f3f;border:none;border-radius:6px;cursor:pointer;display:inline-block;text-decoration:none;">Back to results</a>' : '';
        var titleCard = '';
        if (opts.titleCard && opts.titleCard.title) {
            var tc = opts.titleCard;
            var main = '<div class="class-hero-main"><h1>' + esc(tc.title) + '</h1>'
                + (tc.description ? '<p class="class-bio">' + esc(tc.description) + '</p>' : '')
                + (tc.associationHtml ? '<div class="class-assoc">' + tc.associationHtml + '</div>' : '')
                + '</div>';
            titleCard = '<div class="card">' + main + '</div>';
        }
        var statsCard = '';
        if (opts.statsCard && opts.statsCard.links && opts.statsCard.links.length) {
            var linkParts = opts.statsCard.links.map(function (l) {
                return '<a class="stats-link" href="' + esc(l.href) + '">' + esc(l.label) + '</a>';
            });
            statsCard = '<div class="card stats-card"><div class="class-stats">' + linkParts.join('') + '</div></div>';
        }
        var dataCards = (opts.dataCards || []).map(function (d) {
            return '<div id="' + esc(d.id) + '" class="card"><h2 class="section-title">' + esc(d.title)
                + '</h2><div class="table-container">' + (d.tableHtml || '') + '</div></div>';
        }).join('');
        container.innerHTML = '<div class="master-page-layout container">' + back + titleCard + statsCard + dataCards + '</div>';
    }

    function formatShortDate(iso) {
        if (!iso) return '—';
        var p = String(iso).slice(0, 10).split('-');
        if (p.length !== 3) return esc(iso);
        var m = parseInt(p[1], 10) - 1;
        var d = parseInt(p[2], 10);
        if (m < 0 || m > 11 || !d) return esc(iso);
        return d + ' ' + SHORT_MONTHS[m] + ' ' + p[0];
    }

    function formatStatusLine(status, asAt) {
        var word = (status || '').trim() || 'Provisional';
        if (!asAt) return 'Results are ' + word + ' (snapshot time not recorded)';
        var dt = null;
        if (typeof asAt === 'string') {
            var s = asAt.trim().replace('T', ' ').replace('Z', '');
            var m = s.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
            if (m) {
                dt = { y: m[1], mo: parseInt(m[2], 10), d: parseInt(m[3], 10), h: m[4], mi: m[5] };
            } else {
                var d2 = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
                if (d2) dt = { y: d2[1], mo: parseInt(d2[2], 10), d: parseInt(d2[3], 10), h: '00', mi: '00' };
            }
        }
        if (!dt || dt.mo < 1 || dt.mo > 12) return 'Results are ' + word + ' (snapshot time not recorded)';
        return 'Results are ' + word + ' as at ' + dt.d + ' ' + MONTHS[dt.mo - 1] + ' ' + dt.y + ' at ' + dt.h + ':' + dt.mi;
    }

    function selectedEvent() {
        var id = state.selectedEventId;
        if (id == null) return null;
        for (var i = 0; i < state.events.length; i++) {
            if (String(state.events[i].event_id) === String(id)) return state.events[i];
        }
        return null;
    }

    function regattaFor(ev) {
        if (!ev || !ev.regatta_id) return null;
        for (var i = 0; i < state.regattas.length; i++) {
            if (state.regattas[i].regatta_id === ev.regatta_id) return state.regattas[i];
        }
        return null;
    }

    function fleetNames(ev) {
        var r = regattaFor(ev);
        if (!r || !r.blocks) return [];
        return r.blocks.map(function (b) { return b.class_name; }).filter(Boolean);
    }

    function classOptionsHtml(selectedId) {
        var html = '<option value="">Class</option>';
        (state.raceClasses || []).forEach(function (c) {
            var sel = (selectedId != null && String(c.class_id) === String(selectedId)) ? ' selected' : '';
            html += '<option value="' + esc(c.class_id) + '"' + sel + '>' + esc(c.class_name) + '</option>';
        });
        return html;
    }

    function scoresEmpty(scores) {
        if (scores == null || scores === '' || scores === '{}' || scores === '[]' || scores === 'null') return true;
        if (typeof scores === 'object') {
            if (Array.isArray(scores)) return scores.length === 0;
            return Object.keys(scores).length === 0;
        }
        return false;
    }

    function ensureRoot() {
        var main = document.querySelector('main.main-content') || document.body;
        var kids = main.children;
        for (var i = 0; i < kids.length; i++) {
            if (kids[i].id !== 'club-manage-root') kids[i].hidden = true;
        }
        var root = document.getElementById('club-manage-root');
        if (!root) {
            root = document.createElement('div');
            root.id = 'club-manage-root';
            main.appendChild(root);
        }
        root.hidden = false;
        return root;
    }

    function selectEvent(eventId, regattaId) {
        state.selectedEventId = eventId || null;
        state.selectedRegattaId = regattaId || null;
        state.preview = null;
        state.previewFile = null;
        state.message = '';
        loadEntryRows().then(render).catch(function () { render(); });
    }

    function permissionText(me) {
        var club = (me && (me.club_abbrev || '')) || 'this club';
        var role = (me && me.role) || '';
        if (role === 'super_admin') {
            return 'Super admin can help any hosted event. Club officers only see their own club. Host is taken from your login.';
        }
        return 'You can create and publish events hosted by ' + club
            + '. That is the club on your login. You cannot host for another club. '
            + 'Sailors do not use this page. When entries are open they enter from the public event.';
    }

    function eventsTableHtml() {
        var rows = '';
        (state.events || []).forEach(function (e) {
            var r = regattaFor(e);
            var status = (r && r.result_status) || '—';
            var fleets = fleetNames(e).join(', ') || '—';
            var selected = String(e.event_id) === String(state.selectedEventId);
            var name = e.event_name || 'Event';
            var href = e.regatta_id ? '/regatta/' + encodeURIComponent(e.regatta_id) : '#club-manage-events';
            var nameHtml = e.regatta_id
                ? '<a href="' + esc(href) + '">' + esc(name) + '</a>'
                : esc(name);
            if (selected) nameHtml = '<strong>' + nameHtml + '</strong>';
            rows += '<tr data-event-id="' + esc(e.event_id) + '" data-regatta-id="' + esc(e.regatta_id || '') + '">'
                + '<td class="cell-nowrap">' + esc(formatShortDate(e.start_date)) + '</td>'
                + '<td class="cell-left">' + nameHtml + ' <a href="#club-manage-fleets" class="js-select-event">Select</a></td>'
                + '<td class="hide-mobile">' + esc(e.venue_text || '—') + '</td>'
                + '<td>' + (e.entry_open ? 'Open' : 'Closed') + '</td>'
                + '<td class="hide-mobile">' + esc(status) + '</td>'
                + '<td>' + esc(fleets) + '</td>'
                + '</tr>';
        });
        if (!rows) {
            rows = '<tr><td colspan="6">No hosted events yet. Create one below.</td></tr>';
        }
        rows += '<tr>'
            + '<td><input type="date" id="cm-create-start" required></td>'
            + '<td><input type="text" id="cm-create-title" placeholder="Event name" required></td>'
            + '<td class="hide-mobile"><input type="text" id="cm-create-venue" placeholder="Venue"></td>'
            + '<td><input type="date" id="cm-create-end"></td>'
            + '<td class="hide-mobile"><select id="cm-create-class">' + classOptionsHtml() + '</select></td>'
            + '<td><button type="button" class="btn" id="cm-create-btn">Create event</button></td>'
            + '</tr>';
        return '<table class="table" id="cm-events-table"><thead><tr>'
            + '<th>Date</th><th>Event</th><th class="hide-mobile">Venue</th>'
            + '<th>Entries</th><th class="hide-mobile">Results</th><th>Fleets</th>'
            + '</tr></thead><tbody>' + rows + '</tbody></table>'
            + (state.message ? '<p>' + esc(state.message) + '</p>' : '');
    }

    function fleetsTableHtml() {
        var ev = selectedEvent();
        if (!ev) {
            return '<table class="table"><tbody><tr><td>Select an event above.</td></tr></tbody></table>';
        }
        var r = regattaFor(ev);
        var blocks = (r && r.blocks) || [];
        var rows = '';
        blocks.forEach(function (b) {
            rows += '<tr><td>' + esc(b.class_name || '—') + '</td><td>'
                + esc(b.races_sailed != null ? b.races_sailed : 0) + '</td></tr>';
        });
        if (!rows) rows = '<tr><td colspan="2">No fleets yet.</td></tr>';
        rows += '<tr><td><select id="cm-fleet-class">' + classOptionsHtml() + '</select></td>'
            + '<td><button type="button" class="btn" id="cm-fleet-add">Add fleet</button></td></tr>';
        rows += '<tr><td><select id="cm-entry-open">'
            + '<option value="false"' + (ev.entry_open ? '' : ' selected') + '>Closed</option>'
            + '<option value="true"' + (ev.entry_open ? ' selected' : '') + '>Open</option>'
            + '</select></td>'
            + '<td><button type="button" class="btn" id="cm-entry-open-btn">Set entries</button></td></tr>';
        return '<table class="table"><thead><tr><th>Class</th><th>Races sailed</th></tr></thead><tbody>'
            + rows + '</tbody></table>';
    }

    function entriesTableHtml() {
        var ev = selectedEvent();
        if (!ev) {
            return '<table class="table"><tbody><tr><td>Select an event above.</td></tr></tbody></table>';
        }
        var rows = '';
        (state.entryRows || []).forEach(function (row) {
            var source = row.entry_source || (scoresEmpty(row.race_scores) ? 'Entry' : 'Scored');
            var remove = scoresEmpty(row.race_scores) && row.result_id
                ? ' <a href="#club-manage-entries" class="js-remove-entry" data-result-id="' + esc(row.result_id) + '">Remove</a>'
                : '';
            rows += '<tr><td>' + esc(row.helm_name || '—') + '</td><td>' + esc(row.sail_number || '—')
                + '</td><td>' + esc(row.class_name || '—') + '</td><td>' + esc(source) + remove + '</td></tr>';
        });
        if (!rows) rows = '<tr><td colspan="4">No entries yet.</td></tr>';
        rows += '<tr>'
            + '<td><input type="text" id="cm-entry-helm" placeholder="Helm name"></td>'
            + '<td><input type="text" id="cm-entry-sail" placeholder="Sail no"></td>'
            + '<td><select id="cm-entry-class">' + classOptionsHtml() + '</select></td>'
            + '<td><input type="text" id="cm-entry-sas" placeholder="SAS ID"> '
            + '<button type="button" class="btn" id="cm-entry-add">Add</button></td>'
            + '</tr>';
        return '<table class="table"><thead><tr><th>Helm</th><th>Sail no</th><th>Class</th><th>Source</th></tr></thead><tbody>'
            + rows + '</tbody></table>';
    }

    function uploadTableHtml() {
        var ev = selectedEvent();
        if (!ev) {
            return '<table class="table"><tbody><tr><td>Select an event above.</td></tr></tbody></table>';
        }
        var html = '<table class="table"><tbody><tr>'
            + '<td><input type="file" id="cm-upload-file" accept=".html,.htm,.csv,text/html,text/csv"></td>'
            + '<td><button type="button" class="btn" id="cm-preview-btn">Preview</button></td>'
            + '<td><button type="button" class="btn" id="cm-commit-btn"'
            + (state.preview && state.preview.preview_token ? '' : ' disabled')
            + '>Commit scores</button></td>'
            + '</tr></tbody></table>';
        var prev = state.preview;
        if (prev && (prev.rows || []).length) {
            var body = '';
            (prev.rows || []).forEach(function (row) {
                var warn = '';
                if (!row.class_id) warn = 'Unknown class';
                body += '<tr><td>' + esc(row.class_label || '—') + '</td><td>' + esc(row.sail_number || '—')
                    + '</td><td>' + esc(row.helm_name || '—') + '</td><td>' + esc(row.rank != null ? row.rank : '—')
                    + '</td><td>' + esc(warn) + '</td></tr>';
            });
            html += '<table class="table"><thead><tr><th>Class</th><th>Sail no</th><th>Helm</th><th>Place</th><th>Warnings</th></tr></thead><tbody>'
                + body + '</tbody></table>';
            if ((prev.warnings || []).length) {
                html += '<p>' + esc((prev.warnings || []).slice(0, 8).join(' · ')) + '</p>';
            }
            if ((prev.unknown_classes || []).length) {
                html += '<p>Unknown classes: ' + esc(prev.unknown_classes.join(', ')) + '</p>';
            }
        } else {
            html += '<table class="table"><tbody><tr><td>Choose a Sailwave HTML or CSV file, then Preview. Commit stays off until preview succeeds.</td></tr></tbody></table>';
        }
        return html;
    }

    function publishTableHtml() {
        var ev = selectedEvent();
        if (!ev) {
            return '<table class="table"><tbody><tr><td>Select an event above.</td></tr></tbody></table>';
        }
        var r = regattaFor(ev);
        var current = (r && r.result_status) || 'Provisional';
        var line = state.statusLine || ('Results are ' + current + ' (snapshot time not recorded)');
        var publicLink = ev.regatta_id
            ? '<a href="/regatta/' + encodeURIComponent(ev.regatta_id) + '">View public results</a>'
            : '—';
        return '<table class="table"><tbody>'
            + '<tr><td colspan="2">' + esc(line) + '</td></tr>'
            + '<tr><td><select id="cm-publish-status">'
            + '<option' + (current === 'Provisional' ? ' selected' : '') + '>Provisional</option>'
            + '<option' + (current === 'Final' ? ' selected' : '') + '>Final</option>'
            + '</select></td>'
            + '<td><button type="button" class="btn" id="cm-publish-btn">Publish</button></td></tr>'
            + '<tr><td colspan="2">' + publicLink + '</td></tr>'
            + '</tbody></table>';
    }

    function selectedLabel() {
        var ev = selectedEvent();
        return ev ? (ev.event_name || 'Event') : '';
    }

    function render() {
        var root = ensureRoot();
        var me = state.me || {};
        var club = me.club_abbrev || 'Club';
        var evName = selectedLabel();
        var canWrite = me.is_club_admin || me.role === 'club_admin' || me.role === 'club_manager' || me.role === 'super_admin';
        if (!canWrite) {
            buildMasterPageLayout(root, {
                titleCard: {
                    title: 'Club events',
                    description: 'A club admin or club manager login is required.'
                },
                dataCards: [{
                    id: 'club-manage-denied',
                    title: 'Access',
                    tableHtml: '<table class="table"><tbody><tr><td>Sailors do not use this page. '
                        + (club && club !== 'Club' ? '<a href="/club/' + encodeURIComponent(String(club).toLowerCase()) + '">Open the public club page</a>.' : 'Open your public club page.')
                        + ' <a href="/login.html?returnTo=/club-manage-preview">Log in</a></td></tr></tbody></table>'
                }]
            });
            return;
        }
        buildMasterPageLayout(root, {
            titleCard: {
                title: club + ' — manage events',
                description: permissionText(me)
            },
            statsCard: {
                links: [
                    { href: '#club-manage-events', label: 'Events' },
                    { href: '#club-manage-fleets', label: 'Fleets' },
                    { href: '#club-manage-entries', label: 'Entries' },
                    { href: '#club-manage-upload', label: 'Upload' },
                    { href: '#club-manage-publish', label: 'Publish' }
                ]
            },
            dataCards: [
                { id: 'club-manage-events', title: 'Events', tableHtml: eventsTableHtml() },
                { id: 'club-manage-fleets', title: evName ? ('Fleets — ' + evName) : 'Fleets', tableHtml: fleetsTableHtml() },
                { id: 'club-manage-entries', title: evName ? ('Entries — ' + evName) : 'Entries', tableHtml: entriesTableHtml() },
                { id: 'club-manage-upload', title: evName ? ('Upload — ' + evName) : 'Upload', tableHtml: uploadTableHtml() },
                { id: 'club-manage-publish', title: evName ? ('Publish — ' + evName) : 'Publish', tableHtml: publishTableHtml() }
            ]
        });
        bind();
    }

    function bind() {
        document.querySelectorAll('#cm-events-table tbody tr[data-event-id]').forEach(function (tr) {
            tr.addEventListener('click', function (ev) {
                if (ev.target && ev.target.closest && ev.target.closest('a') && !ev.target.classList.contains('js-select-event')) return;
                selectEvent(tr.getAttribute('data-event-id'), tr.getAttribute('data-regatta-id'));
            });
        });
        document.querySelectorAll('.js-select-event').forEach(function (a) {
            a.addEventListener('click', function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                var tr = a.closest('tr');
                if (tr) selectEvent(tr.getAttribute('data-event-id'), tr.getAttribute('data-regatta-id'));
            });
        });
        var createBtn = document.getElementById('cm-create-btn');
        if (createBtn) createBtn.addEventListener('click', onCreate);
        var fleetAdd = document.getElementById('cm-fleet-add');
        if (fleetAdd) fleetAdd.addEventListener('click', onAddFleet);
        var openBtn = document.getElementById('cm-entry-open-btn');
        if (openBtn) openBtn.addEventListener('click', onSetOpen);
        var entryAdd = document.getElementById('cm-entry-add');
        if (entryAdd) entryAdd.addEventListener('click', onAddEntry);
        document.querySelectorAll('.js-remove-entry').forEach(function (a) {
            a.addEventListener('click', function (ev) {
                ev.preventDefault();
                onRemoveEntry(a.getAttribute('data-result-id'));
            });
        });
        var previewBtn = document.getElementById('cm-preview-btn');
        if (previewBtn) previewBtn.addEventListener('click', onPreview);
        var commitBtn = document.getElementById('cm-commit-btn');
        if (commitBtn) commitBtn.addEventListener('click', onCommit);
        var pubBtn = document.getElementById('cm-publish-btn');
        if (pubBtn) pubBtn.addEventListener('click', onPublish);
    }

    function setMsg(text) {
        state.message = text || '';
        render();
    }

    async function onCreate() {
        var title = (document.getElementById('cm-create-title') || {}).value || '';
        var start = (document.getElementById('cm-create-start') || {}).value || '';
        var end = (document.getElementById('cm-create-end') || {}).value || start;
        var venue = (document.getElementById('cm-create-venue') || {}).value || '';
        var classId = (document.getElementById('cm-create-class') || {}).value || '';
        if (!title.trim() || !start) {
            setMsg('Event name and start date are required.');
            return;
        }
        var body = { title: title.trim(), start_date: start, end_date: end || start, venue_text: venue };
        if (classId) body.class_ids = [parseInt(classId, 10)];
        try {
            var created = await j('/api/club/events', { method: 'POST', body: JSON.stringify(body) });
            await reload();
            selectEvent(created.event_id, created.regatta_id);
            setMsg('Event created.');
        } catch (err) {
            setMsg(err.message || 'Create failed');
        }
    }

    async function onAddFleet() {
        var ev = selectedEvent();
        if (!ev || !ev.regatta_id) { setMsg('Select an event first.'); return; }
        var classId = (document.getElementById('cm-fleet-class') || {}).value || '';
        if (!classId) { setMsg('Choose a class.'); return; }
        try {
            await j('/api/club/regattas/' + encodeURIComponent(ev.regatta_id) + '/classes', {
                method: 'POST',
                body: JSON.stringify({ class_id: parseInt(classId, 10) })
            });
            await reload();
            selectEvent(ev.event_id, ev.regatta_id);
            setMsg('Fleet added.');
        } catch (err) {
            setMsg(err.message || 'Fleet failed');
        }
    }

    async function onSetOpen() {
        var ev = selectedEvent();
        if (!ev) { setMsg('Select an event first.'); return; }
        var open = (document.getElementById('cm-entry-open') || {}).value === 'true';
        try {
            await j('/api/club/events/' + encodeURIComponent(ev.event_id), {
                method: 'PATCH',
                body: JSON.stringify({ entry_open: open })
            });
            await reload();
            selectEvent(ev.event_id, ev.regatta_id);
            setMsg(open ? 'Entries opened.' : 'Entries closed.');
        } catch (err) {
            setMsg(err.message || 'Update failed');
        }
    }

    async function onAddEntry() {
        var ev = selectedEvent();
        if (!ev || !ev.regatta_id) { setMsg('Select an event first.'); return; }
        var sail = (document.getElementById('cm-entry-sail') || {}).value || '';
        var helm = (document.getElementById('cm-entry-helm') || {}).value || '';
        var sas = (document.getElementById('cm-entry-sas') || {}).value || '';
        var classId = (document.getElementById('cm-entry-class') || {}).value || '';
        if (!sail.trim()) { setMsg('Sail number is required.'); return; }
        var body = { sail_number: sail.trim() };
        if (helm.trim()) body.helm_name = helm.trim();
        if (sas.trim()) body.sas_id = sas.trim();
        if (classId) body.class_id = parseInt(classId, 10);
        try {
            await j('/api/club/regattas/' + encodeURIComponent(ev.regatta_id) + '/entries', {
                method: 'POST',
                body: JSON.stringify(body)
            });
            await loadEntryRows();
            setMsg('Entry added.');
        } catch (err) {
            setMsg(err.message || 'Entry failed');
        }
    }

    async function onRemoveEntry(resultId) {
        var ev = selectedEvent();
        if (!ev || !ev.regatta_id || !resultId) return;
        try {
            await j('/api/club/regattas/' + encodeURIComponent(ev.regatta_id) + '/entries/' + encodeURIComponent(resultId), {
                method: 'DELETE'
            });
            await loadEntryRows();
            setMsg('Entry removed.');
        } catch (err) {
            setMsg(err.message || 'Remove failed');
        }
    }

    async function onPreview() {
        var ev = selectedEvent();
        if (!ev || !ev.regatta_id) { setMsg('Select an event first.'); return; }
        var input = document.getElementById('cm-upload-file');
        var file = input && input.files && input.files[0];
        if (!file) { setMsg('Choose a Sailwave HTML or CSV file.'); return; }
        var body = new FormData();
        body.append('file', file);
        try {
            var r = await fetch(sessQ('/api/club/regattas/' + encodeURIComponent(ev.regatta_id) + '/ingest/preview'), {
                method: 'POST',
                credentials: 'same-origin',
                body: body
            });
            var pb = await r.json();
            if (!r.ok) throw new Error((pb && pb.detail) || 'Preview failed');
            state.preview = pb;
            state.previewFile = file;
            setMsg('Previewed ' + (pb.count || (pb.rows || []).length || 0) + ' rows. Review the table, then Commit scores.');
        } catch (err) {
            state.preview = null;
            state.previewFile = null;
            setMsg(err.message || 'Preview failed');
        }
    }

    async function onCommit() {
        var ev = selectedEvent();
        if (!ev || !ev.regatta_id) return;
        if (!state.preview || !state.preview.preview_token || !state.previewFile) {
            setMsg('Preview first, then commit.');
            return;
        }
        var body = new FormData();
        body.append('file', state.previewFile);
        body.append('preview_token', state.preview.preview_token);
        try {
            var r = await fetch(sessQ('/api/club/regattas/' + encodeURIComponent(ev.regatta_id) + '/ingest/commit'), {
                method: 'POST',
                credentials: 'same-origin',
                body: body
            });
            var cb = await r.json();
            if (!r.ok) throw new Error((cb && cb.detail) || 'Commit failed');
            state.preview = null;
            state.previewFile = null;
            await reload();
            selectEvent(ev.event_id, ev.regatta_id);
            setMsg('Committed ' + (cb.rows_updated || 0) + ' updated, ' + (cb.rows_added || 0) + ' added.');
        } catch (err) {
            setMsg(err.message || 'Commit failed');
        }
    }

    async function onPublish() {
        var ev = selectedEvent();
        if (!ev || !ev.regatta_id) { setMsg('Select an event first.'); return; }
        var status = (document.getElementById('cm-publish-status') || {}).value || 'Provisional';
        try {
            await j('/api/club/regattas/' + encodeURIComponent(ev.regatta_id) + '/result-status', {
                method: 'PATCH',
                body: JSON.stringify({ result_status: status })
            });
            await reload();
            selectEvent(ev.event_id, ev.regatta_id);
            setMsg('Published as ' + status + '.');
        } catch (err) {
            setMsg(err.message || 'Publish failed');
        }
    }

    async function loadEntryRows() {
        var ev = selectedEvent();
        state.entryRows = [];
        state.statusLine = '';
        if (!ev || !ev.regatta_id) return;
        try {
            var rows = await j('/api/regatta/' + encodeURIComponent(ev.regatta_id));
            if (!Array.isArray(rows)) rows = [];
            state.entryRows = rows.filter(function (row) { return row && row.result_id; });
            var first = rows[0] || {};
            var r = regattaFor(ev) || {};
            state.statusLine = formatStatusLine(r.result_status || first.result_status, first.as_at_time);
        } catch (e) {
            state.entryRows = [];
        }
    }

    async function reload() {
        var data = await j('/api/club/me/events');
        state.events = data.events || [];
        state.regattas = data.regattas || [];
        state.raceClasses = data.race_classes || [];
        if (data.club_abbrev && state.me) state.me.club_abbrev = data.club_abbrev;
    }

    async function boot() {
        var root = ensureRoot();
        try {
            var me;
            try {
                me = await j('/api/club/me');
            } catch (err) {
                if (/403|Club admin|required/i.test(String(err.message || ''))) {
                    state.me = { role: 'sailor', is_club_admin: false };
                    render();
                    return;
                }
                throw err;
            }
            state.me = me;
            await reload();
            if (!state.selectedEventId && state.events.length) {
                state.selectedEventId = state.events[0].event_id;
                state.selectedRegattaId = state.events[0].regatta_id;
            }
            await loadEntryRows();
            render();
        } catch (err) {
            buildMasterPageLayout(root, {
                titleCard: { title: 'Club events', description: err.message || 'Failed to load' },
                dataCards: [{
                    id: 'club-manage-error',
                    title: 'Status',
                    tableHtml: '<table class="table"><tbody><tr><td><a href="/login.html?returnTo=/club-manage-preview">Log in</a></td></tr></tbody></table>'
                }]
            });
        }
    }

    function start() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', boot);
        } else {
            boot();
        }
    }

    start();
})();
