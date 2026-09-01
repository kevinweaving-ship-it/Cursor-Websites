// API Configuration and Helper Functions
//
// Dev URLs (localhost, private LAN, *.local): same-origin GET/HEAD /api/* are rewritten to
// https://sailingsa.co.za — responses come from the live API and therefore live DB tables.
// sailingsa.co.za itself is never rewritten. Override base with window.SAILINGSA_LIVE_ORIGIN if needed.
//
// Real prod login from dev: session cookies are SameSite=Lax and are not sent cross-origin from
// LAN/localhost to sailingsa.co.za. Optional: set localStorage sailingsa_live_session_token to the
// value of the prod `session` cookie (after logging in on https://sailingsa.co.za) — then /auth/session
// and mutating /api/* use ?session= on live (see sailingDevLiveSessionToken).
//
// Same origin as the page; index.html / login.html set window.API_BASE = window.location.origin
let API_BASE = (typeof window !== 'undefined' && window.location) ? (window.location.origin || '') : '';

/**
 * True when hostname is a private/LAN IPv4, link-local IPv4, or *.local (mDNS).
 * Does not match public IPs — production hostnames never return true here.
 */
function sailingDevIsPrivateLanHostname(hostname) {
    var h = String(hostname || '').toLowerCase();
    if (!h) return false;
    if (h.endsWith('.local')) return true;
    var m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(h);
    if (!m) return false;
    var a = parseInt(m[1], 10);
    var b = parseInt(m[2], 10);
    var c = parseInt(m[3], 10);
    var d = parseInt(m[4], 10);
    if (a > 255 || b > 255 || c > 255 || d > 255) return false;
    if (a === 10) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
    if (a === 169 && b === 254) return true;
    if (a === 127) return true;
    return false;
}

/**
 * Local live-data mode (hub / blank dev on LAN or localhost):
 * - GET/HEAD same-origin /api/* → https://sailingsa.co.za (live API / live DB snapshot — use SAILINGSA_LIVE_ORIGIN to override).
 * - GET/HEAD /auth/session → mock Super Admin unless sailingsa_live_session_token (or window.SAILINGSA_LIVE_SESSION_TOKEN) is set → then live /auth/session?session=… (real name/SAS id; SA saves go to live if role allows).
 * - POST/PATCH/PUT/DELETE same-origin /api/* → blocked with a mock 200 unless that token is set → then forwarded to live with ?session=…
 *
 * Workflow so deploy matches what you saw in dev:
 * - Rely on live GETs for regatta/summary/events shape; hub card URLs must stay canonical (see breaking-news-card.js).
 * - To persist hub edits against a real backend while keeping live reads: run local api.py and set
 *   window.SAILINGSA_DEV_PASS_MUTATING_TO_LOCAL_API = true in the console, then reload (before api.js runs: inline script in blank69).
 *   Point that API at the DB you intend to ship (e.g. tunnel/staging) — do not mix “live reads + random local DB” and expect parity.
 * - Fully local stack (no live rewrite): window.SAILINGSA_LIVE_DEV_OFF = true before api.js loads.
 *
 * Active when: SAILINGSA_ENV === 'DEV', or hostname is loopback, or private LAN IP / *.local,
 * or sessionStorage sailingsa_blank69_local_live_api === '1'. Production (sailingsa.co.za) never matches.
 */
function sailingDevModeActive() {
    try {
        if (typeof window === 'undefined') return false;
        if (window.SAILINGSA_LIVE_DEV_OFF === true) return false;
        if (String(window.SAILINGSA_ENV || '').toUpperCase() === 'DEV') return true;
        var h = (window.location && String(window.location.hostname || '').toLowerCase()) || '';
        if (h === '127.0.0.1' || h === 'localhost' || h === '[::1]') return true;
        if (sailingDevIsPrivateLanHostname(h)) return true;
        try {
            if (window.sessionStorage && window.sessionStorage.getItem('sailingsa_blank69_local_live_api') === '1') {
                return true;
            }
        } catch (e2) {
            /* private mode */
        }
        return false;
    } catch (e) {
        return false;
    }
}

/**
 * Live API origin for DEV GET rewrites only. Set window.SAILINGSA_LIVE_ORIGIN to override (no trailing slash).
 * Default host string exists only inside this helper and is used solely when sailingDevModeActive().
 */
function sailingDevResolveLiveOrigin() {
    if (!sailingDevModeActive()) return '';
    try {
        var c = (window.SAILINGSA_LIVE_ORIGIN && String(window.SAILINGSA_LIVE_ORIGIN).trim()) || '';
        c = c.replace(/\/$/, '');
        if (c) return c;
    } catch (e1) { /* ignore */ }
    var h = 'sailingsa.co.za';
    return 'https://' + h;
}

/**
 * Optional production session id for dev (LAN/localhost). Prod cookies are not sent cross-origin;
 * paste the `session` cookie value from sailingsa.co.za after login: DevTools → Application → Cookies.
 * Or set window.SAILINGSA_LIVE_SESSION_TOKEN before load.
 */
function sailingDevLiveSessionToken() {
    try {
        if (typeof window === 'undefined') return '';
        var w = window.SAILINGSA_LIVE_SESSION_TOKEN;
        if (w != null && String(w).trim()) return String(w).trim();
        if (window.localStorage) {
            var s = window.localStorage.getItem('sailingsa_live_session_token');
            if (s != null && String(s).trim()) return String(s).trim();
        }
    } catch (e) {
        /* private mode / blocked storage */
    }
    return '';
}

function sailingDevMockSuperAdminSession() {
    return {
        valid: true,
        is_super_admin: true,
        role: 'super_admin',
        sas_id: '0',
        user: {
            full_name: 'DEV Super Admin',
            first_name: 'DEV',
            last_name: 'Super Admin',
            role: 'super_admin'
        }
    };
}

window.sailingDevModeActive = sailingDevModeActive;
window.sailingDevResolveLiveOrigin = sailingDevResolveLiveOrigin;
window.sailingDevIsPrivateLanHostname = sailingDevIsPrivateLanHostname;
window.sailingDevLiveSessionToken = sailingDevLiveSessionToken;

/**
 * DEV: intercept fetch — GET /api/* from page origin → live; mutating /api/* → mock unless
 * window.SAILINGSA_DEV_PASS_MUTATING_TO_LOCAL_API === true (then same-origin /api/* uses real fetch),
 * or sailingsa_live_session_token for live prod session via ?session=.
 * Install once. Production: SAILINGSA_ENV unset → native fetch only.
 */
(function sailingDevInstallFetchInterceptor() {
    if (typeof window === 'undefined' || typeof window.fetch !== 'function' || typeof Response === 'undefined') return;
    if (window.__sailingSaDevFetchInstalled) return;
    var nativeFetch = window.fetch.bind(window);
    window.__sailingSaDevFetchInstalled = true;

    function parseInput(input, init) {
        var method = 'GET';
        var urlStr = '';
        try {
            if (typeof Request !== 'undefined' && input instanceof Request) {
                urlStr = String(input.url || '');
                method = String((init && init.method) || input.method || 'GET').toUpperCase();
            } else {
                urlStr = String(input != null ? input : '');
                method = String((init && init.method) || 'GET').toUpperCase();
            }
        } catch (e1) {
            urlStr = '';
            method = 'GET';
        }
        return { method: method, urlStr: urlStr };
    }

    window.fetch = function (input, init) {
        if (!sailingDevModeActive()) {
            return nativeFetch(input, init);
        }

        var parsed = parseInput(input, init);
        var method = parsed.method;
        var url = parsed.urlStr;

        if (method === 'POST' || method === 'PUT' || method === 'PATCH' || method === 'DELETE') {
            var pageOriginM = '';
            try {
                pageOriginM = window.location.origin;
            } catch (ePO) {
                pageOriginM = '';
            }
            try {
                var devTokMut = sailingDevLiveSessionToken();
                if (devTokMut && pageOriginM) {
                    var baseHrefMut = '';
                    try {
                        baseHrefMut = window.location.href;
                    } catch (eBHM) {
                        baseHrefMut = '';
                    }
                    var uMut = new URL(url, baseHrefMut || undefined);
                    var pathMut = uMut.pathname || '';
                    var liveBM = sailingDevResolveLiveOrigin();
                    if (uMut.origin === pageOriginM && pathMut.indexOf('/api/') === 0 && liveBM) {
                        var tgtMut = new URL(liveBM.replace(/\/$/, '') + uMut.pathname + uMut.search);
                        tgtMut.searchParams.set('session', devTokMut);
                        var finalMutUrl = tgtMut.toString();
                        console.log('[SAILINGSA DEV] ' + method + ' \u2192 live with ?session= (real prod session):', pathMut);
                        var crossMut = Object.assign({}, init, { credentials: 'omit', mode: 'cors' });
                        if (typeof Request !== 'undefined' && input instanceof Request) {
                            var nrm = new Request(finalMutUrl, {
                                method: method,
                                headers: input.headers,
                                body: method === 'GET' || method === 'HEAD' ? null : input.body,
                                cache: input.cache,
                                redirect: input.redirect,
                                referrer: input.referrer,
                                integrity: input.integrity,
                                credentials: 'omit',
                                mode: 'cors',
                                signal: (init && init.signal) || input.signal
                            });
                            return nativeFetch(nrm);
                        }
                        return nativeFetch(finalMutUrl, crossMut);
                    }
                }
            } catch (eMutLive) {
                /* fall through */
            }
            try {
                if (window.SAILINGSA_DEV_PASS_MUTATING_TO_LOCAL_API === true && pageOriginM) {
                    var baseHrefM = '';
                    try {
                        baseHrefM = window.location.href;
                    } catch (eBH) {
                        baseHrefM = '';
                    }
                    var uM = new URL(url, baseHrefM || undefined);
                    var pathM = uM.pathname || '';
                    if (uM.origin === pageOriginM && pathM.indexOf('/api/') === 0) {
                        return nativeFetch(input, init);
                    }
                }
            } catch (ePass) {
                /* fall through to mock */
            }
            try {
                var prev = '';
                if (init && init.body != null) {
                    var b = init.body;
                    prev = typeof b === 'string' ? (b.length > 400 ? b.slice(0, 400) + '\u2026' : b) : '[' + Object.prototype.toString.call(b) + ']';
                }
                var liveHint = '';
                try {
                    liveHint = sailingDevResolveLiveOrigin() || 'https://sailingsa.co.za';
                } catch (eLB) {
                    liveHint = 'https://sailingsa.co.za';
                }
                console.warn(
                    '[SAILINGSA DEV] BLOCKED ' +
                        method +
                        ' (mock OK, not sent). GET /api uses live data from ' +
                        liveHint +
                        '. To send saves: local api.py + SAILINGSA_DEV_PASS_MUTATING_TO_LOCAL_API=true; ' +
                        'or live writes: localStorage sailingsa_live_session_token = prod `session` cookie after login on sailingsa.co.za; ' +
                        'or SAILINGSA_LIVE_DEV_OFF=true for an all-local stack.',
                    url,
                    prev || ''
                );
            } catch (eL) {
                console.warn('[SAILINGSA DEV] BLOCKED ' + method + ' (mock OK, not sent):', url);
            }
            var body = JSON.stringify({
                ok: true,
                dev_mock: true,
                method: method,
                message: 'DEV: mutating request not sent'
            });
            return Promise.resolve(
                new Response(body, {
                    status: 200,
                    statusText: 'OK',
                    headers: { 'Content-Type': 'application/json' }
                })
            );
        }

        if (method === 'GET' || method === 'HEAD') {
            var liveBase = sailingDevResolveLiveOrigin();
            if (!liveBase) return nativeFetch(input, init);

            var liveOrigin = '';
            try {
                liveOrigin = new URL(liveBase).origin;
            } catch (eO) {
                return nativeFetch(input, init);
            }

            var baseHref = '';
            try {
                baseHref = window.location.href;
            } catch (eH) {
                baseHref = '';
            }

            var u = null;
            try {
                u = new URL(url, baseHref || undefined);
            } catch (eU) {
                u = null;
            }
            if (!u) return nativeFetch(input, init);
            if (u.origin === liveOrigin) return nativeFetch(input, init);

            var pageOrigin = '';
            try {
                pageOrigin = window.location.origin;
            } catch (eP) {}

            if (u.origin !== pageOrigin) return nativeFetch(input, init);

            var path = u.pathname || '';
            var rewriteApi = path.indexOf('/api/') === 0;
            var rewriteSession = path === '/auth/session';
            if (!rewriteApi && !rewriteSession) return nativeFetch(input, init);

            function devMockSessionResponse() {
                var body = JSON.stringify(sailingDevMockSuperAdminSession());
                return new Response(body, {
                    status: 200,
                    statusText: 'OK',
                    headers: { 'Content-Type': 'application/json' }
                });
            }

            /* Without sailingsa_live_session_token: mock Super Admin. With token: real live /auth/session?session=… */
            if (rewriteSession && (method === 'GET' || method === 'HEAD')) {
                var devTokS = sailingDevLiveSessionToken();
                if (devTokS && liveBase) {
                    var sessUrl = new URL(liveBase.replace(/\/$/, '') + u.pathname + u.search);
                    sessUrl.searchParams.set('session', devTokS);
                    console.log('[SAILINGSA DEV] /auth/session \u2192 live with ?session= (real prod identity)');
                    var crossSess = Object.assign({}, init, { credentials: 'omit', mode: 'cors' });
                    if (typeof Request !== 'undefined' && input instanceof Request) {
                        var nrs = new Request(sessUrl.toString(), {
                            method: method,
                            headers: input.headers,
                            cache: input.cache,
                            redirect: input.redirect,
                            referrer: input.referrer,
                            integrity: input.integrity,
                            credentials: 'omit',
                            mode: 'cors',
                            signal: (init && init.signal) || input.signal
                        });
                        return nativeFetch(nrs);
                    }
                    return nativeFetch(sessUrl.toString(), crossSess);
                }
                console.log(
                    '[SAILINGSA DEV] /auth/session → mock Super Admin (set localStorage sailingsa_live_session_token for real prod session)'
                );
                if (method === 'HEAD') {
                    return Promise.resolve(
                        new Response(null, {
                            status: 200,
                            statusText: 'OK',
                            headers: { 'Content-Type': 'application/json' }
                        })
                    );
                }
                return Promise.resolve(devMockSessionResponse());
            }

            if (!rewriteApi) return nativeFetch(input, init);

            var liveUrl = liveBase.replace(/\/$/, '') + u.pathname + u.search + u.hash;
            console.log('[SAILINGSA DEV] GET \u2192 live (not localhost):', liveUrl, '(api)');

            var crossInit = Object.assign({}, init, { credentials: 'omit', mode: 'cors' });

            if (typeof Request !== 'undefined' && input instanceof Request) {
                var nr = new Request(liveUrl, {
                    method: method,
                    headers: input.headers,
                    cache: input.cache,
                    redirect: input.redirect,
                    referrer: input.referrer,
                    integrity: input.integrity,
                    credentials: 'omit',
                    mode: 'cors',
                    signal: (init && init.signal) || input.signal
                });
                return nativeFetch(nr);
            }
            return nativeFetch(liveUrl, crossInit);
        }

        return nativeFetch(input, init);
    };
})();

/**
 * Make API request with error handling
 */
async function apiRequest(endpoint, options = {}) {
    let apiBase = window.API_BASE || API_BASE;
    if (!apiBase) apiBase = (typeof window !== 'undefined' && window.location) ? window.location.origin : '';
    // Relative API_BASE (e.g. '/admin' from another script) makes `/auth/session` → wrong host path and 404s.
    if (apiBase && !/^https?:\/\//i.test(String(apiBase))) {
        apiBase = (typeof window !== 'undefined' && window.location) ? window.location.origin : '';
    }
    if (apiBase && apiBase.includes('/')) apiBase = (apiBase.match(/^https?:\/\/[^\/]+/) || [apiBase])[0];
    const url = `${apiBase}${endpoint}`;
    
    
    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        credentials: 'include' // Important for cookies
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('[ERROR] API request failed:', {
            url: url,
            error: error.message,
            stack: error.stack
        });
        throw error;
    }
}

/**
 * Check if user has valid session
 */
async function checkSession() {
    if (sailingDevModeActive()) {
        return sailingDevMockSuperAdminSession();
    }
    try {
        let pathQs = '';
        try {
            if (typeof window !== 'undefined' && window.location && window.location.pathname) {
                pathQs = '?path=' + encodeURIComponent(window.location.pathname || '/');
            }
        } catch (e) { /* ignore */ }
        const sessionPath = '/auth/session' + pathQs;
        const now = Date.now();
        if (typeof window !== 'undefined') {
            if (window.__sailingSessionCache && window.__sailingSessionCache.path === sessionPath && (now - window.__sailingSessionCache.ts) < 10000) {
                return window.__sailingSessionCache.value;
            }
            if (window.__sailingSessionPromise && window.__sailingSessionPromise.path === sessionPath) {
                return window.__sailingSessionPromise.promise;
            }
        }
        const requestPromise = apiRequest(sessionPath, {
            method: 'GET',
            credentials: 'include' // Important: include cookies
        });
        if (typeof window !== 'undefined') {
            window.__sailingSessionPromise = { path: sessionPath, promise: requestPromise };
        }
        const result = await requestPromise;
        if (typeof window !== 'undefined') {
            window.__sailingSessionCache = { path: sessionPath, value: result, ts: Date.now() };
            window.__sailingSessionPromise = null;
        }
        return result;
    } catch (error) {
        if (typeof window !== 'undefined') {
            window.__sailingSessionPromise = null;
        }
        console.error('[DEBUG] checkSession: Error:', error);
        return { valid: false, error: error.message };
    }
}

/**
 * Normalize role for comparison (matches api.py _session_role_is_super_admin tolerance).
 */
function sailingNormalizeRoleString(role) {
    if (role == null || role === '') return '';
    return String(role)
        .trim()
        .toLowerCase()
        .replace(/[\s\-]+/g, '_')
        .replace(/_+/g, '_');
}

/**
 * True when session is super admin (top-level role or session.user.role).
 */
function sailingSessionIsSuperAdmin(session) {
    if (!session || session.valid !== true) return false;
    if (session.is_super_admin === true) return true;
    if (session.is_super_admin === false) return false;
    var r = session.role;
    if ((r == null || r === '') && session.user) r = session.user.role;
    var n = sailingNormalizeRoleString(r);
    return n === 'super_admin' || n === 'superadmin';
}

/**
 * Search for profiles
 */
async function searchProfiles(query) {
    try {
        const response = await apiRequest('/profiles/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        // Handle response - if it has results array, return it, otherwise return empty array
        if (response && response.results) {
            return response.results;
        } else if (Array.isArray(response)) {
            return response;
        } else {
            return [];
        }
    } catch (error) {
        console.error('[DEBUG] api.js searchProfiles error:', error);
        console.error('[DEBUG] api.js searchProfiles error details:', error.message, error.stack);
        throw error;
    }
}

/**
 * Claim/register profile
 */
async function claimProfile(profileData) {
    return apiRequest('/profiles/claim', {
        method: 'POST',
        body: JSON.stringify(profileData)
    });
}

/**
 * Login with provider
 */
async function loginWithProvider(provider, providerData) {
    return apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ provider, ...providerData })
    });
}

/**
 * Login with identifier (email, SAS ID, or WhatsApp) and password.
 * Backend expects password + identifier as `email` or `username` (both accepted).
 */
async function loginWithUsernamePassword(identifier, password) {
    return apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
            email: identifier,
            password: password
        })
    });
}

/**
 * Register with provider
 */
async function registerWithProvider(provider, providerData, profile) {
    return apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ provider, ...providerData, profile })
    });
}

/**
 * Get regattas list. Optional params: { class_name, year, q } for filtering by class sailed, year, or regatta name.
 */
async function getRegattas(params) {
    let url = '/api/regattas/with-counts';
    if (params && typeof params === 'object') {
        const sp = new URLSearchParams();
        if (params.class_name != null && String(params.class_name).trim() !== '') {
            sp.set('class_name', String(params.class_name).trim());
        }
        if (params.year != null && params.year !== '') {
            sp.set('year', String(params.year));
        }
        if (params.q != null && String(params.q).trim() !== '') {
            sp.set('q', String(params.q).trim());
        }
        if (params.limit != null && params.limit !== '') {
            var lim = Math.min(400, Math.max(1, parseInt(params.limit, 10) || 150));
            sp.set('limit', String(lim));
        }
        const qs = sp.toString();
        if (qs) url += '?' + qs;
    } else {
        url += '?limit=400';
    }
    return apiRequest(url, { method: 'GET' });
}

/**
 * Get regatta details
 */
async function getRegatta(regattaId) {
    return apiRequest(`/api/regattas/${regattaId}`, { method: 'GET' });
}

/**
 * Get class entry counts for a regatta (classes sailed in that regatta).
 * Returns object keyed by lowercased class name: { "optimist a": { name: "Optimist A", entries: 15 }, ... }
 */
async function getRegattaClassEntries(regattaId) {
    return apiRequest(`/api/regatta/${encodeURIComponent(regattaId)}/class-entries`, { method: 'GET' });
}

/**
 * Get class results
 */
async function getClassResults(regattaId, classId) {
    return apiRequest(`/api/regattas/${regattaId}/classes/${classId}/results`, { method: 'GET' });
}

/**
 * Get podium results
 */
async function getPodium(regattaId, classId) {
    return apiRequest(`/api/regattas/${regattaId}/classes/${classId}/podium`, { method: 'GET' });
}

/**
 * Load regattas list (placeholder)
 */
async function loadRegattas() {
    try {
        const regattas = await getRegattas();
        const regattasList = document.getElementById('regattas-list');
        if (regattasList) {
            if (regattas.length === 0) {
                regattasList.innerHTML = '<p>No regattas available yet.</p>';
            } else {
                // Populate regattas list
                regattasList.innerHTML = regattas.map(r => `
                    <div class="regatta-card">
                        <h3>${r.name}</h3>
                        <p>${r.venue} - ${r.start_date}</p>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Failed to load regattas:', error);
    }
}

// Make functions globally available
window.loginWithUsernamePassword = loginWithUsernamePassword;
window.checkSession = checkSession;
window.sailingNormalizeRoleString = sailingNormalizeRoleString;
window.sailingSessionIsSuperAdmin = sailingSessionIsSuperAdmin;
window.getRegattaClassEntries = getRegattaClassEntries;
window.getRegattas = getRegattas;

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        apiRequest,
        checkSession,
        searchProfiles,
        claimProfile,
        loginWithProvider,
        loginWithUsernamePassword,
        registerWithProvider,
        getRegattas,
        getRegatta,
        getRegattaClassEntries,
        getClassResults,
        getPodium,
        loadRegattas
    };
}
