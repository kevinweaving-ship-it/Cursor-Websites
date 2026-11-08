#!/usr/bin/env python3
"""Prepare regatta pagination fixes against exact SailingSA live snapshots.

Offline/staging only. Never publishes files, changes databases or restarts services.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
from pathlib import Path

EXPECTED = {
    "api.py": "415f6c38ce85dbdb21e20f8975fcb2da7697c8bd0418fbffbfde0079ffd5408f",
    "index.html": "7c3462c668dbcec76c41a4601234e37439c46cd068f4a4fe9a5c964cf3a4709d",
    "js/api.js": "449edcdb32f800a0317963f3e8dbcb79e810cd45e820ccf34bcb3109e7ded1b6",
}

def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise ValueError(f"{label}: expected one anchor; found {n}")
    return text.replace(old, new, 1)

def patch_api(text: str) -> str:
    begin = text.index('def api_regattas_with_counts(')
    end = text.index('\n@app.', begin)
    section = text[begin:end]
    section = once(section, '    request: Request = None,\n', '    request: Request = None,\n    offset: int = Query(0, ge=0, le=500),\n', 'offset parameter')
    section = once(section, '    _lim = max(1, min(500, int(limit)))', '    _lim = max(1, min(500, int(limit)))\n    _offset = max(0, min(500, int(offset)))\n    _page_end = min(500, _offset + _lim)', 'offset normalization')
    section = once(section, 'return _cached[:_lim]', 'return _cached[_offset:_page_end]', 'memory page')
    section = once(section, '(_cached_lim >= _lim or _cached_n >= _lim or (_lim >= 100 and _cached_n >= 50))', '(_cached_lim >= _page_end or _cached_n >= _page_end)', 'memory validity')
    section = once(section, 'if len(disk_data) >= _lim or _lim >= 100:', 'if len(disk_data) >= _page_end:', 'disk validity')
    section = once(section, 'return disk_data[:_lim]', 'return disk_data[_offset:_page_end]', 'disk page')
    section = once(section, '''        _sql_lim = _lim
        if _no_filters and _lim < 100:
            _sql_lim = min(500, max(_lim * 4, 120))
''', '''        # Fetch enough rows to form a complete parent batch after children nest.
        # Hard cap prevents unbounded queries. Disk/memory caches serve hot pages.
        _sql_lim = min(500, max(120, _page_end * 4))
''', 'SQL page overfetch')
    section = once(section, 'if _no_filters and _lim >= 100:', 'if _no_filters and _sql_lim >= 500:', 'only cache complete set')
    section = once(section, '_REGATTA_WITH_COUNTS_CACHE["limit"] = _lim', '_REGATTA_WITH_COUNTS_CACHE["limit"] = _sql_lim', 'cache span')
    section = once(section, '''        if _no_filters and len(out) > _lim:
            out = out[:_lim]
        return out''', '''        return out[_offset:_page_end]''', 'final page slice')
    text = text[:begin] + section + text[end:]
    ast.parse(text)
    return text

def patch_api_js(text: str) -> str:
    begin = text.index('async function getRegattas(params)')
    end = text.index('\n}', begin) + 2
    sec = text[begin:end]
    sec = once(sec, '''        const qs = sp.toString();''', '''        if (params.offset != null && params.offset !== '') {
            const offset = Math.max(0, Math.min(500, parseInt(params.offset, 10) || 0));
            sp.set('offset', String(offset));
        }
        const qs = sp.toString();''', 'client offset pass-through')
    return text[:begin] + sec + text[end:]

def patch_landing(text: str) -> str:
    # Render page-2 into a detached container and append the card nodes only:
    # loaded cards, click listeners and scroll position are preserved.
    begin = text.index('function renderRegattasTable(regattas, searchQuery)')
    end = text.index('function _saHomeLiveBoardApply(', begin)
    sec = text[begin:end]
    sec = once(sec,
        'function renderRegattasTable(regattas, searchQuery) {',
        'function renderRegattasTable(regattas, searchQuery, outputTarget, preserveServerOrder) {',
        'targeted render signature')
    sec = once(sec,
        "var publicRegattasList = document.getElementById('public-regattas-list');",
        "var publicRegattasList = outputTarget || document.getElementById('public-regattas-list');",
        'isolated target')
    sec = once(sec,
        '            regattas = _sortRegattasNewestFirst(regattas);',
        '            if (!preserveServerOrder) regattas = _sortRegattasNewestFirst(regattas);',
        'preserve backend sorting')
    sec = once(sec,
        '''            _saApplyRegattaSearchRestoreScroll();
            try { _saHomeLiveBoardPollStart(); } catch (_) {}''',
        '''            if (!outputTarget) {
                _saApplyRegattaSearchRestoreScroll();
                try { _saHomeLiveBoardPollStart(); } catch (_) {}
            }''', 'suppress detached side effects')
    text = text[:begin] + sec + text[end:]

    start = text.index('        var _regattaSearchAllCache = null;')
    end = text.index('        /**\n         * Load regattas for public view', start)
    pagination = '''        // Backend applies full-dataset search and ordering BEFORE offset/limit.
        // Never fetch the entire catalogue on activation; exactly 30 per request.
        var _regattaSearchAllCache = null;
        var _saRegattaPagerState = null;
        var _saRegattaPagerGeneration = 0;
        function _clearPublicRegattasList() {
            var target = document.getElementById('public-regattas-list');
            if (target) target.innerHTML = '';
        }
        function _stopRegattaPager() {
            ++_saRegattaPagerGeneration;
            if (_saRegattaPagerState && _saRegattaPagerState.observer) {
                _saRegattaPagerState.observer.disconnect();
            }
            _saRegattaPagerState = null;
        }
        async function applyRegattaFilter() {
            if ((window.searchMode || 'sailor') !== 'regatta') {
                _stopRegattaPager();
                _clearPublicRegattasList();
                return;
            }
            var si = document.getElementById('sailor-search-input');
            var ri = document.getElementById('temp-landing-regatta-input');
            var useRi = !!(ri && (document.activeElement === ri || ri.offsetParent !== null));
            var raw = useRi ? (ri.value || '').trim() : (si ? (si.value || '').trim() : '');
            var query = raw.toLowerCase() === 'all' ? '' : raw;
            var target = document.getElementById('public-regattas-list');
            if (!target) return;
            if (_saRegattaPagerState && _saRegattaPagerState.query === query && target.querySelector('.sa-home-regatta-list')) return;
            _stopRegattaPager();
            if (query && query.length < 2) {
                target.textContent = 'Type at least 2 characters to search regattas.';
                return;
            }
            target.textContent = 'Loading regattas…';
            var state = { query: query, generation: _saRegattaPagerGeneration,
                offset: 0, shown: 0, busy: false, done: false, observer: null,
                seen: new Set(), sentinel: null };
            _saRegattaPagerState = state;

            function updateHeading() {
                var h = target.querySelector('.regatta-search-results-label');
                if (!h) return;
                var label = state.query ? 'Regatta Search for "' + state.query + '"' : 'All Regattas — newest first';
                h.textContent = label + ' — showing ' + state.shown + (state.done ? '' : '+');
            }
            async function nextPage() {
                if (_saRegattaPagerState !== state || state.busy || state.done) return;
                state.busy = true;
                try {
                    var params = { limit: 30, offset: state.offset };
                    if (state.query) params.q = state.query;
                    var rows = typeof getRegattas === 'function' ? await getRegattas(params) : [];
                    if (_saRegattaPagerState !== state ||
                        (window.searchMode || 'sailor') !== 'regatta') return;
                    if (!Array.isArray(rows)) throw new Error('Invalid regatta response');
                    state.offset += rows.length;
                    var unique = rows.filter(function(r) {
                        var id = String(r.regatta_id != null ? r.regatta_id : r.id || '').trim();
                        if (!id || state.seen.has(id)) return false;
                        state.seen.add(id);
                        return true;
                    });
                    if (!state.shown) {
                        renderRegattasTable(unique, state.query, null, true);
                    } else if (unique.length) {
                        var detached = document.createElement('div');
                        renderRegattasTable(unique, state.query, detached, true);
                        var existing = target.querySelector('.sa-home-regatta-list');
                        var incoming = detached.querySelector('.sa-home-regatta-list');
                        if (existing && incoming) {
                            if (existing.lastElementChild && incoming.firstElementChild) {
                                var sep = document.createElement('hr');
                                sep.className = 'sa-home-regatta-sep';
                                existing.appendChild(sep);
                            }
                            while (incoming.firstChild) existing.appendChild(incoming.firstChild);
                        }
                    }
                    state.shown += unique.length;
                    if (rows.length < 30 || state.offset >= 500) state.done = true;
                    if (state.shown === 0) target.textContent = 'No regattas match.';
                    updateHeading();
                    if (state.done && state.observer) {
                        state.observer.disconnect();
                        if (state.sentinel) state.sentinel.remove();
                    }
                } catch (error) {
                    if (_saRegattaPagerState === state) {
                        console.error('Regatta paging:', error);
                        state.done = true;
                        if (!state.shown) target.textContent = 'Unable to load regattas. Try again.';
                    }
                } finally { state.busy = false; }
            }
            await nextPage();
            if (_saRegattaPagerState !== state || state.done) return;
            var sentinel = document.createElement('div');
            sentinel.className = 'sa-regatta-page-sentinel';
            sentinel.style.cssText = 'min-height:1px;width:100%;';
            target.appendChild(sentinel);
            state.sentinel = sentinel;
            if ('IntersectionObserver' in window) {
                state.observer = new IntersectionObserver(function(entries) {
                    if (entries.some(function(e) { return e.isIntersecting; })) nextPage();
                }, { root: null, rootMargin: '500px 0px', threshold: 0.01 });
                state.observer.observe(sentinel);
            } else {
                var btn = document.createElement('button');
                btn.type = 'button';
                btn.textContent = 'Load next 30 regattas';
                btn.onclick = nextPage;
                sentinel.appendChild(btn);
            }
        }
'''
    text = text[:start] + pagination + text[end:]
    return text

def prepare(kind: str, source: Path, output: Path, expected: str | None = None) -> str:
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError('Input and output may not be the same')
    data = source.read_bytes()
    observed = hashlib.sha256(data).hexdigest()
    wanted = expected or EXPECTED[kind]
    if observed != wanted:
        raise ValueError(f'{kind}: live hash differs: {observed}, expected {wanted}')
    source_text = data.decode('utf-8')
    changed = {'api.py': patch_api, 'index.html': patch_landing,
               'js/api.js': patch_api_js}[kind](source_text)
    if changed == source_text:
        raise ValueError('No change produced')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(changed.encode('utf-8'))
    return hashlib.sha256(output.read_bytes()).hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=list(EXPECTED))
    ap.add_argument('--source', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--expected-sha256')
    args = ap.parse_args()
    print(prepare(args.kind, args.source, args.output, args.expected_sha256))

if __name__ == '__main__':
    main()
