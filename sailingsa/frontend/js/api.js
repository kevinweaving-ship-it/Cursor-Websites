// API Configuration and Helper Functions
// Same origin as the page; index.html / login.html set window.API_BASE = window.location.origin
let API_BASE = (typeof window !== 'undefined' && window.location) ? (window.location.origin || '') : '';

/**
 * Make API request with error handling
 */
async function apiRequest(endpoint, options = {}) {
    let apiBase = window.API_BASE || API_BASE;
    if (!apiBase) apiBase = (typeof window !== 'undefined' && window.location) ? window.location.origin : '';
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
    try {
        const result = await apiRequest('/auth/session', { 
            method: 'GET',
            credentials: 'include' // Important: include cookies
        });
        return result;
    } catch (error) {
        console.error('[DEBUG] checkSession: Error:', error);
        return { valid: false, error: error.message };
    }
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
        const qs = sp.toString();
        if (qs) url += '?' + qs;
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
window.getRegattaClassEntries = getRegattaClassEntries;

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
