// Session Management

/** True when URL is any SPA class page under /class/… (avoid re-running landing/sailor updatePageContent). */
function sailingsaIsClassSpaPath() {
    try {
        var p = (window.location.pathname || '').replace(/\/+$/, '') || '/';
        return p.indexOf('/class/') === 0;
    } catch (e) {
        return false;
    }
}

/**
 * Hub pages where js/blank-landing-header.js exclusively owns #loginBox and #adminV10SecondHeader*.
 * session.js must not paint header auth, run ensureButtonText on #loginBox, or set admin header avatars here.
 * Opt-in: body data-sailingsa-hub-header-isolated="1" and/or pathname …/blank69…
 */
function sailingsaHubHeaderOwnedByBlankLandingJs() {
    try {
        if (typeof window !== 'undefined' && window.location && String(window.location.pathname || '').indexOf('blank69') !== -1) {
            return true;
        }
    } catch (e1) { /* ignore */ }
    try {
        if (typeof document !== 'undefined' && document.body && document.body.getAttribute('data-sailingsa-hub-header-isolated') === '1') {
            return true;
        }
    } catch (e2) { /* ignore */ }
    return false;
}
window.sailingsaHubHeaderOwnedByBlankLandingJs = sailingsaHubHeaderOwnedByBlankLandingJs;

/** Skip updatePageContent on class routes — header-triggered updates must not replace class view with sailor home. */
function safeUpdatePageContentSync() {
    if (typeof updatePageContent !== 'function') return;
    if (sailingsaIsClassSpaPath()) return;
    updatePageContent();
}

async function safeUpdatePageContentAsync() {
    if (typeof updatePageContent !== 'function') return;
    if (sailingsaIsClassSpaPath()) return;
    return await updatePageContent();
}

/** Slug from display name for personal-avatars filenames: `{sasId}-{slug}.png` */
function sailingPersonalAvatarNameSlug(fullName) {
    return String(fullName || '')
        .toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'member';
}

/**
 * Ordered avatar URLs: personal folder first, then uploaded avatar files, with default-youth only as fallback.
 * @param {string} apiBase - e.g. window.API_BASE without trailing slash
 */
function sailingBuildSailorAvatarCandidates(apiBase, sasId, fullName, opts) {
    opts = opts || {};
    const id = sasId != null ? String(sasId).trim() : '';
    if (!/^\d+$/.test(id)) return [];
    const pre = apiBase && String(apiBase).trim() ? String(apiBase).replace(/\/$/, '') + '/' : '';
    const slug = sailingPersonalAvatarNameSlug(fullName);
    const urls = [];
    urls.push(pre + 'assets/personal-avatars/' + encodeURIComponent(id) + '-' + slug + '.png');
    urls.push(pre + 'assets/personal-avatars/' + encodeURIComponent(id) + '-' + slug + '.jpg');
    /* SAS-only filenames in personal-avatars/ (if full name slug does not match session string) */
    urls.push(pre + 'assets/personal-avatars/' + encodeURIComponent(id) + '.png');
    urls.push(pre + 'assets/personal-avatars/' + encodeURIComponent(id) + '.jpg');
    let ageNum = null;
    if (opts.ageYears !== undefined && opts.ageYears !== null && opts.ageYears !== '' && !isNaN(opts.ageYears)) {
        ageNum = parseInt(opts.ageYears, 10);
    }
    urls.push(pre + 'assets/avatars/' + encodeURIComponent(id) + '.png');
    urls.push(pre + 'assets/avatars/' + encodeURIComponent(id) + '.jpg');
    if (opts.includeMediaCache !== false) {
        urls.push(pre + 'media/avatars/' + encodeURIComponent(id) + '.jpg');
    }
    if (ageNum >= 9 && ageNum <= 18) {
        urls.push(pre + 'assets/avatars/default-youth.png');
    }
    urls.push(pre + 'assets/avatars/default-youth.png');
    const seen = {};
    const out = [];
    for (let u = 0; u < urls.length; u++) {
        if (!seen[urls[u]]) {
            seen[urls[u]] = true;
            out.push(urls[u]);
        }
    }
    return out;
}

/**
 * Apply candidate chain to an <img> (sailor profile or header).
 * opts: { apiBase, ageYears, includeMediaCache, headerMode }
 */
function applySailingAvatarToImg(imgEl, sasId, fullName, opts) {
    if (!imgEl) return;
    opts = opts || {};
    const apiBase = (opts.apiBase != null ? opts.apiBase : (window.API_BASE || '')).replace(/\/$/, '');
    const urls = sailingBuildSailorAvatarCandidates(apiBase, sasId, fullName, opts);
    if (!urls.length) {
        imgEl.removeAttribute('src');
        if (opts.headerMode) imgEl.style.display = 'none';
        return;
    }
    let idx = 0;
    imgEl.onerror = function sailingAvatarOnErr() {
        idx += 1;
        if (idx >= urls.length) {
            imgEl.onerror = null;
            if (opts.headerMode) {
                imgEl.removeAttribute('src');
                imgEl.style.display = 'none';
            } else {
                imgEl.style.display = 'none';
                const fb = imgEl.parentElement && imgEl.parentElement.querySelector('.avatar-fallback');
                if (fb) fb.style.display = 'flex';
            }
            return;
        }
        imgEl.src = urls[idx];
    };
    imgEl.onload = function sailingAvatarOnLoad() {
        if (opts.headerMode) {
            imgEl.style.display = 'block';
        } else {
            imgEl.style.display = '';
            const fb = imgEl.parentElement && imgEl.parentElement.querySelector('.avatar-fallback');
            if (fb) fb.style.display = 'none';
        }
    };
    idx = 0;
    imgEl.src = urls[0];
}

function applySailingLoginAvatarsFromSession(sasId, displayName) {
    const apiBase = (window.API_BASE || '').replace(/\/$/, '');
    const ids =
        typeof sailingsaHubHeaderOwnedByBlankLandingJs === 'function' && sailingsaHubHeaderOwnedByBlankLandingJs()
            ? ['userAvatarImg']
            : ['userAvatarImg', 'adminV10SecondHeaderAvatar'];
    ids.forEach(function (tid) {
        const el = document.getElementById(tid);
        if (el) {
            applySailingAvatarToImg(el, sasId, displayName, {
                apiBase,
                headerMode: true,
                includeMediaCache: false
            });
        }
    });
}

function clearSailingLoginAvatars() {
    const ids =
        typeof sailingsaHubHeaderOwnedByBlankLandingJs === 'function' && sailingsaHubHeaderOwnedByBlankLandingJs()
            ? ['userAvatarImg']
            : ['userAvatarImg', 'adminV10SecondHeaderAvatar'];
    ids.forEach(function (tid) {
        const el = document.getElementById(tid);
        if (!el) return;
        el.removeAttribute('src');
        el.style.display = 'none';
        el.onerror = null;
    });
}

window.sailingPersonalAvatarNameSlug = sailingPersonalAvatarNameSlug;
window.sailingBuildSailorAvatarCandidates = sailingBuildSailorAvatarCandidates;
window.applySailingAvatarToImg = applySailingAvatarToImg;
window.applySailingLoginAvatarsFromSession = applySailingLoginAvatarsFromSession;
window.clearSailingLoginAvatars = clearSailingLoginAvatars;

/**
 * Check session and show popup if needed
 * After login, redirects to landing page (not profile)
 */
async function checkSessionAndShowPopup() {
    try {
        const session = await checkSession();
        
        if (session.valid) {
            // Already logged in - redirect to landing page
            redirectToLandingPage();
        } else {
            // No valid session - show popup
            showPopup();
        }
    } catch (error) {
        console.error('Session check failed:', error);
        // Show popup on error
        showPopup();
    }
}

/**
 * Show popup modal
 */
function showPopup() {
    const popup = document.getElementById('popup-container') || document.getElementById('popupOverlay');
    if (popup) {
        popup.style.display = 'flex';
        // Reset to state 1
        showState('login-choice');
    }
}

/**
 * Hide popup modal
 */
function hidePopup() {
    const popup = document.getElementById('popup-container') || document.getElementById('popupOverlay');
    if (popup) {
        popup.style.display = 'none';
    }
}

/**
 * Show specific popup state
 */
function showState(stateName) {
    // Hide all states
    const states = document.querySelectorAll('.popup-state');
    states.forEach(state => {
        state.style.display = 'none';
        state.classList.add('hidden');
    });
    
    // Show target state
    const targetState = document.getElementById(`state-${stateName}`);
    if (targetState) {
        targetState.style.display = 'block';
        targetState.classList.remove('hidden');
    }
}

/**
 * Store session data
 */
function storeSession(sessionData) {
    // Store in localStorage as backup
    localStorage.setItem('sailing_session', JSON.stringify(sessionData));
}

/**
 * Get stored session
 */
function getStoredSession() {
    const stored = localStorage.getItem('sailing_session');
    return stored ? JSON.parse(stored) : null;
}

/**
 * Clear session
 */
function clearSession() {
    // Clear localStorage
    localStorage.removeItem('sailing_session');
    localStorage.removeItem('session');
    try {
        window.__sailingSessionCache = null;
        window.__sailingSessionPromise = null;
    } catch (eCache) {}
    
    // Clear cookies
    document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
    document.cookie = 'session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
    
    console.log('[DEBUG] clearSession: All session data cleared');
}

/**
 * Redirect to landing page after successful login/registration
 */
function redirectToLandingPage() {
    // Redirect to current path on same origin (canonical home is / not /index.html)
    window.location.href = window.location.origin + window.location.pathname;
}

/** Toggle document.body.super-admin (e.g. for CSS hooks). No global click blocking here. */
function sailingSyncSuperAdminBodyClass(sessionLike) {
    try {
        const sess = sessionLike || {};
        const isSa = typeof sailingSessionIsSuperAdmin === 'function' && sailingSessionIsSuperAdmin(sess);
        document.body.classList.toggle('super-admin', !!isSa);
    } catch (_) {
        try {
            document.body.classList.remove('super-admin');
        } catch (e2) {}
    }
}

/**
 * Update header auth status (login box or user name + logout)
 */
function sailingRememberAuthReturnToCurrentPage() {
    try {
        sessionStorage.setItem('auth_returnTo', window.location.href);
    } catch (err) {}
}

function sailingLoginUrl() {
    return (window.location.origin || '') + '/login.html';
}

function sailingAutoLoginDisabledOnce() {
    try {
        return sessionStorage.getItem('disable_auto_login_once') === 'true';
    } catch (err) {
        return false;
    }
}

function sailingSetAutoLoginDisabledOnce() {
    try {
        sessionStorage.setItem('disable_auto_login_once', 'true');
    } catch (err) {}
}

function sailingClearAutoLoginDisabledOnce() {
    try {
        sessionStorage.removeItem('disable_auto_login_once');
    } catch (err) {}
}

function sailingSignupUrl() {
    var signupBase = (window.location.origin || '') + '/signup.html';
    var returnTo = '';
    try {
        returnTo = window.location.href || '';
    } catch (err) {}
    return signupBase + '?signup=1&returnTo=' + encodeURIComponent(returnTo);
}

async function sailingHandleHeaderSignIn(e) {
    if (e) e.preventDefault();
    console.log('[DEBUG] Header Sign In clicked');
    try {
        const session = await checkSession();
        console.log('[DEBUG] Header Sign In: Session check result:', session);

        if (session && session.valid) {
            await updateHeaderAuthStatus();
            await safeUpdatePageContentAsync();
            window.location.reload();
            return;
        }

        // If user said Yes on Logout, Login silently auto-signs in (no second popup).
        const rememberCredentials = localStorage.getItem('remember_credentials');
        if (rememberCredentials === 'true') {
            const savedOAuthMethod = (localStorage.getItem('saved_login_method') || '').toLowerCase();
            if (savedOAuthMethod === 'google' || savedOAuthMethod === 'facebook') {
                console.log('[DEBUG] Header Sign In: silent OAuth auto-login via', savedOAuthMethod);
                sailingClearAutoLoginDisabledOnce();
                sailingRememberAuthReturnToCurrentPage();
                const oauthUrl = new URL((window.location.origin || '') + '/auth/' + savedOAuthMethod);
                oauthUrl.searchParams.set('flow', 'login');
                try {
                    const rt = sessionStorage.getItem('auth_returnTo') || '';
                    if (rt) oauthUrl.searchParams.set('returnTo', rt);
                } catch (_rt) {}
                window.location.href = oauthUrl.toString();
                return;
            }

            const savedUsername = localStorage.getItem('saved_username');
            const savedPassword = localStorage.getItem('saved_password');
            if (savedUsername && savedPassword && typeof loginWithUsernamePassword === 'function') {
                console.log('[DEBUG] Header Sign In: silent password auto-login');
                try {
                    const loginResult = await loginWithUsernamePassword(savedUsername, savedPassword);
                    if (loginResult && loginResult.success) {
                        document.cookie = `session=${loginResult.session || loginResult.session_token}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;
                        localStorage.setItem('session', loginResult.session || loginResult.session_token);
                        localStorage.setItem('remember_credentials', 'true');
                        localStorage.setItem('saved_login_method', 'password');
                        sailingClearAutoLoginDisabledOnce();
                        await updateHeaderAuthStatus();
                        await safeUpdatePageContentAsync();
                        window.location.reload();
                        return;
                    }
                    localStorage.removeItem('saved_password');
                } catch (loginError) {
                    console.error('[DEBUG] Header Sign In: Auto-login failed:', loginError);
                }
            }
        }

        sailingRememberAuthReturnToCurrentPage();
        const loginUrl = sailingLoginUrl();
        console.log('[DEBUG] Header Sign In: Redirecting to:', loginUrl);
        window.location.href = loginUrl;
    } catch (error) {
        console.error('[DEBUG] Header Sign In: Error checking session:', error);
        sailingRememberAuthReturnToCurrentPage();
        window.location.href = sailingLoginUrl();
    }
}

function sailingHandleHeaderSignUp(e) {
    if (e) e.preventDefault();
    sailingRememberAuthReturnToCurrentPage();
    const signupUrl = sailingSignupUrl();
    console.log('[DEBUG] Header Sign Up: Redirecting to:', signupUrl);
    window.location.href = signupUrl;
}

function sailingRenderLoggedOutAuthButtons(loginBoxDiv) {
    if (!loginBoxDiv) return;

    const existingAuthBtn = document.getElementById('authBtn');
    if (existingAuthBtn && existingAuthBtn.parentNode) {
        existingAuthBtn.parentNode.removeChild(existingAuthBtn);
    }

    loginBoxDiv.innerHTML = '';
    loginBoxDiv.style.setProperty('position', 'absolute', 'important');
    loginBoxDiv.style.setProperty('right', '0px', 'important');
    loginBoxDiv.style.setProperty('top', '50%', 'important');
    loginBoxDiv.style.setProperty('transform', 'translateY(-50%)', 'important');
    loginBoxDiv.style.setProperty('display', 'flex', 'important');
    loginBoxDiv.style.setProperty('justify-content', 'flex-end', 'important');
    loginBoxDiv.style.setProperty('align-items', 'center', 'important');
    loginBoxDiv.style.setProperty('width', 'auto', 'important');
    loginBoxDiv.style.setProperty('box-sizing', 'border-box', 'important');
    loginBoxDiv.style.setProperty('padding', '0', 'important');
    loginBoxDiv.style.setProperty('margin', '0', 'important');
    loginBoxDiv.style.setProperty('overflow', 'visible', 'important');
    loginBoxDiv.style.setProperty('background', 'transparent', 'important');

    const wrap = document.createElement('div');
    wrap.className = 'auth-split-buttons';
    wrap.style.setProperty('display', 'inline-flex', 'important');
    wrap.style.setProperty('align-items', 'center', 'important');
    wrap.style.setProperty('justify-content', 'flex-end', 'important');
    wrap.style.setProperty('gap', '6px', 'important');
    wrap.style.setProperty('flex-wrap', 'nowrap', 'important');
    wrap.style.setProperty('width', 'auto', 'important');
    wrap.style.setProperty('height', '32px', 'important');
    wrap.style.setProperty('min-height', '32px', 'important');
    wrap.style.setProperty('max-height', '32px', 'important');
    wrap.style.setProperty('margin', '0', 'important');
    wrap.style.setProperty('padding', '0', 'important');
    wrap.style.setProperty('padding-right', '6px', 'important');
    wrap.style.setProperty('flex-shrink', '0', 'important');
    wrap.style.setProperty('flex-grow', '0', 'important');
    wrap.style.setProperty('box-sizing', 'border-box', 'important');
    wrap.style.setProperty('overflow', 'hidden', 'important');

    const SI_ICON = '/icons/assets/phosphor/bold/user-circle-gear-bold.svg';
    const SI_TEXT = 'Login';
    const SI_BG = '#ffffff';
    const SI_FG = '#001f3f';
    const SI_BORDER = '#f1f5f9';
    const SI_TINT = 'filter:invert(8%) sepia(92%) saturate(2500%) hue-rotate(185deg) brightness(92%) contrast(105%)';

    const SU_ICON = '/icons/assets/iconoir/regular/edit.svg';
    const SU_TEXT = 'Sign Up';
    const SU_BG = '#eab308';
    const SU_FG = '#000000';
    const SU_BORDER = '#eab308';

    function boxBase(el) {
        el.style.setProperty('box-sizing', 'border-box', 'important');
        el.style.setProperty('border-style', 'solid', 'important');
        el.style.setProperty('border-width', '3px', 'important');
        el.style.setProperty('border-radius', '10px', 'important');
        el.style.setProperty('outline', 'none', 'important');
        el.style.setProperty('line-height', '32px', 'important');
        el.style.setProperty('height', '32px', 'important');
        el.style.setProperty('min-height', '32px', 'important');
        el.style.setProperty('max-height', '32px', 'important');
        el.style.setProperty('padding', '0 10px', 'important');
        el.style.setProperty('vertical-align', 'middle', 'important');
        el.style.setProperty('font-family', 'inherit', 'important');
        el.style.setProperty('white-space', 'nowrap', 'important');
        el.style.setProperty('overflow', 'hidden', 'important');
        el.style.setProperty('opacity', '1', 'important');
        el.style.setProperty('background-image', 'none', 'important');
        el.style.setProperty('box-shadow', '0 1px 2px rgba(15,23,42,.18)', 'important');
        el.style.setProperty('text-decoration', 'none', 'important');
        el.style.setProperty('flex-shrink', '0', 'important');
        el.style.setProperty('flex-grow', '0', 'important');
        try {
            el.style.setProperty('appearance', 'none', 'important');
            el.style.setProperty('-moz-appearance', 'none', 'important');
            el.style.setProperty('-webkit-appearance', 'none', 'important');
        } catch (_a) { /* ignore */ }
        el.style.setProperty('-webkit-tap-highlight-color', 'transparent', 'important');
    }

    function forceIdenticalBoxHeight(el) {
        // Post-boxBase lock — same values for both buttons 100% identical.
        // Guarantees zero pixel mismatch on Safari mobile where bold-font line-height 1 adds rounding delta.
        el.style.setProperty('height', '32px', 'important');
        el.style.setProperty('min-height', '32px', 'important');
        el.style.setProperty('max-height', '32px', 'important');
        el.style.setProperty('line-height', '32px', 'important');
    }

    const signInBtn = document.createElement('button');
    signInBtn.type = 'button';
    signInBtn.id = 'authSignInBtn';
    boxBase(signInBtn);
    forceIdenticalBoxHeight(signInBtn);
    signInBtn.style.setProperty('display', 'inline-flex', 'important');
    signInBtn.style.setProperty('align-items', 'center', 'important');
    signInBtn.style.setProperty('justify-content', 'center', 'important');
    signInBtn.style.setProperty('gap', '5px', 'important');
    signInBtn.style.setProperty('min-width', '88px', 'important');
    signInBtn.style.setProperty('background', SI_BG, 'important');
    signInBtn.style.setProperty('background-color', SI_BG, 'important');
    signInBtn.style.setProperty('border-color', SI_BORDER, 'important');
    signInBtn.style.setProperty('color', SI_FG, 'important');
    signInBtn.style.setProperty('font-size', '13px', 'important');
    signInBtn.style.setProperty('font-weight', '700', 'important');
    signInBtn.style.setProperty('cursor', 'pointer', 'important');
    forceIdenticalBoxHeight(signInBtn); // RE-LOCK after all per-button styles (in case any above override height)
    signInBtn.innerHTML =
        '<img src="' + SI_ICON + '" alt="' + SI_TEXT + '" width="16" height="16" style="display:block;flex-shrink:0;width:16px;height:16px;max-width:16px;max-height:16px;object-fit:contain;object-position:center;' + SI_TINT + ';background:none;border:0;padding:0;margin:0">' +
        '<span style="display:inline-block;vertical-align:middle;line-height:32px!important;color:' + SI_FG + '!important;font-weight:700!important;font-size:13px!important;background:none;padding:0;margin:0">' + SI_TEXT + '</span>';
    signInBtn.addEventListener('click', function(e){
      e.preventDefault();
      if (window.__GOLD_HEADER_CALL && typeof window.__GOLD_HEADER_CALL.fireSignIn === 'function') {
        window.__GOLD_HEADER_CALL.fireSignIn();
        return;
      }
      try { return sailingHandleHeaderSignIn.apply(this, arguments); } catch(_){}
    });

    const signUpBtn = document.createElement('button');
    signUpBtn.type = 'button';
    signUpBtn.id = 'authSignUpBtn';
    boxBase(signUpBtn);
    forceIdenticalBoxHeight(signUpBtn);
    signUpBtn.style.setProperty('display', 'inline-flex', 'important');
    signUpBtn.style.setProperty('align-items', 'center', 'important');
    signUpBtn.style.setProperty('justify-content', 'center', 'important');
    signUpBtn.style.setProperty('gap', '5px', 'important');
    signUpBtn.style.setProperty('min-width', '94px', 'important');
    signUpBtn.style.setProperty('background', SU_BG, 'important');
    signUpBtn.style.setProperty('background-color', SU_BG, 'important');
    signUpBtn.style.setProperty('border-color', SU_BORDER, 'important');
    signUpBtn.style.setProperty('color', SU_FG, 'important');
    signUpBtn.style.setProperty('font-size', '13px', 'important');
    signUpBtn.style.setProperty('font-weight', '700', 'important');
    signUpBtn.style.setProperty('cursor', 'pointer', 'important');
    forceIdenticalBoxHeight(signUpBtn); // RE-LOCK after per-button styles
    signUpBtn.innerHTML =
        '<img src="' + SU_ICON + '" alt="' + SU_TEXT + '" width="16" height="16" style="display:block;flex-shrink:0;width:16px;height:16px;max-width:16px;max-height:16px;object-fit:contain;object-position:center;filter:brightness(0) saturate(100%);background:none;border:0;padding:0;margin:0">' +
        '<span style="display:inline-block;vertical-align:middle;line-height:32px!important;color:' + SU_FG + '!important;font-weight:700!important;font-size:13px!important;background:none;padding:0;margin:0">' + SU_TEXT + '</span>';
    signUpBtn.addEventListener('click', function(e){
      e.preventDefault();
      if (window.__GOLD_HEADER_CALL && typeof window.__GOLD_HEADER_CALL.fireSignUp === 'function') {
        window.__GOLD_HEADER_CALL.fireSignUp();
        return;
      }
      try { return sailingHandleHeaderSignUp.apply(this, arguments); } catch(_){}
    });

    // DOM ORDER: signUpBtn FIRST (left) then signInBtn SECOND (right)
    wrap.appendChild(signUpBtn);
    wrap.appendChild(signInBtn);
    loginBoxDiv.appendChild(wrap);

    // --------------------------------------------------------------
    // PC / LAPTOP: MATCH LOGOUT'S RIGHT ALIGNMENT 1:1 (≥1024px ONLY)
    // MOBILE / TABLET (<1024px): ZERO CHANGES.  Mobile uses absolute
    //   right:0 inside site-header, already perfect — untouched.
    //
    // ROOT CAUSE OF "buttons too far left" on PC:
    //   Lines 435-448 above forced #loginBox to position:absolute.
    //   That pulled it COMPLETELY OUT OF the normal flex flow of its
    //   direct parent .header-auth.  But #loggedInStatus (Logout slot)
    //   sits INSIDE that flex flow:
    //     .header-auth (lines 3156-3164 header.html) =
    //       flex:0 0 auto; display:flex; align-items:center;
    //       justify-content:flex-end; margin-left:auto
    //     Inside that: #loggedInStatus.style.display = 'flex'
    //                + #loggedInStatus CSS = justify-content:flex-end
    //   → #loggedInStatus sits at exact RIGHT edge of the container
    //     (max-width 1200 0 auto, the same as root / uses).  Absolute
    //     #loginBox never could, because absolute ignores parent flex
    //     and picks the nearest positioned ancestor (which varies by
    //     CSS cascade on PC media queries).
    //
    // FIX (on PC ≥1024px ONLY):
    //   Put #loginBox BACK INTO the exact same flex flow Logout uses.
    //   Unset position:absolute → static (in flow), set the same
    //   display:flex + justify-content:flex-end + width:100% that
    //   #loggedInStatus has.  Same flex flow = same right edge. Done.
    //   No fixed positioning.  No scroll listeners.  No guesswork.
    // --------------------------------------------------------------
    try {
        if (typeof window !== 'undefined'
            && typeof window.matchMedia === 'function'
            && (
                window.matchMedia('(min-width: 1024px)').matches
                || window.matchMedia('(orientation: landscape) and (max-width: 1023px)').matches
            )) {

            // --- RESTORE #loginBox to the SAME flex flow Logout uses ---
            // PC + Mobile Landscape: static flex-end (matches MP right flush + vertical center).
            loginBoxDiv.style.setProperty('position',      'static',    'important');
            loginBoxDiv.style.setProperty('display',       'flex',      'important');
            loginBoxDiv.style.setProperty('align-items',   'center',    'important');
            loginBoxDiv.style.setProperty('justify-content','flex-end', 'important');
            loginBoxDiv.style.setProperty('flex-direction','row',       'important');
            loginBoxDiv.style.setProperty('width',         '100%',      'important');
            loginBoxDiv.style.setProperty('max-width',     'none',      'important');
            loginBoxDiv.style.setProperty('height',        'auto',      'important');
            loginBoxDiv.style.setProperty('top',           'auto',      'important');
            loginBoxDiv.style.setProperty('right',         'auto',      'important');
            loginBoxDiv.style.setProperty('bottom',        'auto',      'important');
            loginBoxDiv.style.setProperty('left',          'auto',      'important');
            loginBoxDiv.style.setProperty('transform',     'none',      'important');
            loginBoxDiv.style.setProperty('margin',        '0',         'important');
            loginBoxDiv.style.setProperty('padding',       '0',         'important');
            loginBoxDiv.style.setProperty('box-sizing',    'border-box','important');
            loginBoxDiv.style.setProperty('z-index',       'auto',      'important');
            loginBoxDiv.style.setProperty('gap',           '0',         'important');
            loginBoxDiv.style.setProperty('flex-wrap',     'nowrap',    'important');

            // --- Inner wrap matches too (no extra right pad) ---
            wrap.style.setProperty('display',       'inline-flex', 'important');
            wrap.style.setProperty('justify-content','flex-end',   'important');
            wrap.style.setProperty('align-items',   'center',      'important');
            wrap.style.setProperty('flex-direction','row',         'important');
            wrap.style.setProperty('width',         'auto',        'important');
            wrap.style.setProperty('height',        'auto',        'important');
            wrap.style.setProperty('padding',       '0',           'important');
            wrap.style.setProperty('margin',        '0',           'important');
            wrap.style.setProperty('box-sizing',    'border-box',  'important');
            wrap.style.setProperty('gap',           '6px',         'important');
            wrap.style.setProperty('flex-wrap',     'nowrap',      'important');
            wrap.style.setProperty('padding-right', '0px',         'important');
            wrap.style.setProperty('flex-grow',     '0',           'important');
            wrap.style.setProperty('flex-shrink',   '0',           'important');
        }
    } catch (_ee) { /* swallow — never break render */ }
    // --------------------------------------------------------------
}

async function updateHeaderAuthStatus() {
    console.log('[DEBUG] updateHeaderAuthStatus: Called');
    if (typeof sailingsaHubHeaderOwnedByBlankLandingJs === 'function' && sailingsaHubHeaderOwnedByBlankLandingJs()) {
        return;
    }
    try {
        const session = await checkSession();
        sailingSyncSuperAdminBodyClass(session);
        console.log('[DEBUG] updateHeaderAuthStatus: Session data:', session);

        /**
         * blank69 (and any blank hub using admin-v10 header): visible auth is ONLY
         * `#adminV10SecondHeaderUser` from blank-landing-header.js — same `/auth/session` as `/`.
         * When logged in, bail out before any Sign In / `#authBtn` logic so we never stack Sign In + Logout.
         */
        try {
            const v10Wrap = document.getElementById('adminV10SecondHeaderUser');
            const isBlankHub =
                document.body &&
                document.body.classList &&
                document.body.classList.contains('blank-landing-page') &&
                document.body.classList.contains('admin-dashboard-v10');
            if (session && session.valid && v10Wrap && isBlankHub) {
                const lbHub = document.getElementById('loginBox');
                if (lbHub) {
                    lbHub.style.display = 'none';
                    lbHub.innerHTML = '';
                }
                return;
            }
        } catch (eHubEarly) {
            /* continue with normal branches */
        }

        if (session.valid) {
            /**
             * blank69 / hub: safeUpdatePageContentSync → updatePageContent can throw (no full SPA).
             * That must NOT hit the outer catch, which paints "Sign In" while syncAdminV10SecondHeader still shows Logout.
             */
            try {
                const user = session.user || {};
                const fullName = user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim();
                const displayName = fullName || 'User';
                const sasId = session.sas_id || '';

                const loggedInDiv = document.getElementById('loggedInStatus');
                const loginBoxDiv = document.getElementById('loginBox');

                // /header/ and header.html OWN the new three-slot layout:
                //   slot 1 left:  logo
                //   slot 2 mid:   .header-user-center  (#headerUserCenter)
                //   slot 3 right: .header-auth > #loggedInStatus with ONLY Logout btn
                // If #headerUserCenter exists → this layout path ONLY, no legacy spans.
                const centerCol = document.getElementById('headerUserCenter');
                const IS_HEADER_OWNED_LAYOUT = !!(centerCol && loggedInDiv);

                console.log('[DEBUG] updateHeaderAuthStatus: Elements found:', {
                    loggedInDiv: !!loggedInDiv,
                    loginBoxDiv: !!loginBoxDiv,
                    centerCol: !!centerCol,
                    IS_HEADER_OWNED_LAYOUT: IS_HEADER_OWNED_LAYOUT
                });

                // Always hide public Sign In slot when session is valid.
                if (loginBoxDiv) {
                    loginBoxDiv.style.display = 'none';
                }

                // ================================================================
                // /header/ SPECIFIC RENDER (center name + SAS, Logout UNMOVED right)
                // ================================================================
                if (IS_HEADER_OWNED_LAYOUT) {
                    console.log('[DEBUG] updateHeaderAuthStatus: User data:', {
                        fullName,
                        displayName,
                        sasId,
                        user
                    });

                    // Pure CSS Grid layout centers this column (no JS transform hacks).
                    centerCol.innerHTML = '';
                    centerCol.style.setProperty('display','flex','important');
                    centerCol.style.setProperty('visibility','visible','important');

                    // --- ROW 1: Sailor's name centered ---
                    var nameRow = document.createElement('div');
                    nameRow.className = 'user-center-row-name';
                    nameRow.textContent = displayName;
                    try { centerCol.appendChild(nameRow); } catch(_){}

                    // --- ROW 2: SAS ID centered under name ---
                    if (sasId) {
                        var sasRow = document.createElement('div');
                        sasRow.className = 'user-center-row-sas';
                        sasRow.innerHTML =
                            'SAS ID: <span class="sas-id-value">' + sasId + '</span>';
                        try { centerCol.appendChild(sasRow); } catch(_){}
                    }

                    // #loggedInStatus: ONLY child is the Logout button (right side, UNMOVED).
                    loggedInDiv.innerHTML = '';
                    loggedInDiv.style.display = 'flex';
                    console.log('[DEBUG] updateHeaderAuthStatus: /header/ render — name centered, SAS under name, Logout right (unchanged)');
                } else {
                    // ================================================================
                    // LEGACY PATH for all OTHER pages (/, /results, etc — NEVER touch them).
                    // Old compact single-line user info + Logout button in #loggedInStatus.
                    // Code below is preserved exactly as it was before the /header/ split.
                    // ================================================================
                    const userNameDisplay = document.getElementById('userNameDisplay');
                    if (loggedInDiv && userNameDisplay) {
                        console.log('[DEBUG] updateHeaderAuthStatus (legacy): User data:', {
                            fullName, displayName, sasId, user
                        });
                        const sasIdDisplay = document.getElementById('userSasIdDisplay');
                        const showSas = !!(sasIdDisplay && sasId);
                        const nameHtml =
                            '<span class="user-name" style="display:inline!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:320px;line-height:18px!important;font-size:15px!important;font-weight:700!important;color:#ffffff!important;margin:0!important;padding:0!important">' +
                            displayName +
                            '</span>';
                        const sasSepHtml = showSas
                            ? '<span style="display:inline!important;white-space:nowrap;margin:0 6px 0 4px!important;padding:0!important;line-height:18px!important;color:rgba(255,255,255,0.45)!important;font-size:14px!important;font-weight:400!important">·</span>'
                            : '';
                        const sasHtml = showSas
                            ? '<span class="user-sas-id" style="display:inline!important;white-space:nowrap;line-height:18px!important;font-size:12px!important;font-weight:500!important;color:rgba(255,255,255,0.88)!important;margin:0!important;padding:0!important">SAS ID: <span class="sas-id-value" style="display:inline!important;color:rgba(255,255,255,0.92)!important;font-weight:600!important">' + sasId + '</span></span>'
                            : '';
                        userNameDisplay.style.setProperty('display', 'inline-block', 'important');
                        userNameDisplay.style.setProperty('white-space', 'nowrap', 'important');
                        userNameDisplay.style.setProperty('overflow', 'hidden', 'important');
                        userNameDisplay.style.setProperty('text-overflow', 'ellipsis', 'important');
                        userNameDisplay.style.setProperty('max-width', '460px', 'important');
                        userNameDisplay.style.setProperty('text-align', 'right', 'important');
                        userNameDisplay.style.setProperty('line-height', '18px', 'important');
                        userNameDisplay.style.setProperty('margin', '0', 'important');
                        userNameDisplay.style.setProperty('padding', '0', 'important');
                        userNameDisplay.innerHTML = nameHtml + sasSepHtml + sasHtml;
                        if (sasIdDisplay) {
                            sasIdDisplay.textContent = '';
                            sasIdDisplay.innerHTML = '';
                            sasIdDisplay.style.setProperty('display', 'none', 'important');
                            sasIdDisplay.style.setProperty('height', '0px', 'important');
                            sasIdDisplay.style.setProperty('width', '0px', 'important');
                            sasIdDisplay.style.setProperty('margin', '0', 'important');
                            sasIdDisplay.style.setProperty('padding', '0', 'important');
                            sasIdDisplay.style.setProperty('overflow', 'hidden', 'important');
                        }
                        loggedInDiv.style.display = 'flex';
                        console.log('[DEBUG] updateHeaderAuthStatus: legacy user info (compact single-line row layout)');
                    }
                }

                applySailingLoginAvatarsFromSession(sasId, displayName);

                // ============================================================
                // Logout button: EXACT SAME BOX SIZE/STYLE as Login button
                // (same proportions, same border, same height, same text size,
                //  same white bg / navy text).  ONLY DIFFERENCES:
                //   icon  = /icons/assets/phosphor/regular/user-circle-minus.svg
                //   text  = "Logout" (instead of "Login")
                // Reference for these styles: session.js lines 468-539 Login button
                // (boxBase + forceIdenticalBoxHeight + SI_* constants)
                // ============================================================
                var LO_ICON   = '/icons/assets/phosphor/regular/user-circle-minus.svg';
                var LO_TEXT   = 'Logout';
                var LO_BG     = '#ffffff';
                var LO_FG     = '#001f3f';
                var LO_BORDER = '#f1f5f9';
                var LO_TINT   = 'filter:invert(8%) sepia(92%) saturate(2500%) hue-rotate(185deg) brightness(92%) contrast(105%)';

                function logoutBoxBase(el) {
                    el.style.setProperty('box-sizing', 'border-box', 'important');
                    el.style.setProperty('border-style', 'solid', 'important');
                    el.style.setProperty('border-width', '3px', 'important');
                    el.style.setProperty('border-radius', '10px', 'important');
                    el.style.setProperty('outline', 'none', 'important');
                    el.style.setProperty('line-height', '32px', 'important');
                    el.style.setProperty('height', '32px', 'important');
                    el.style.setProperty('min-height', '32px', 'important');
                    el.style.setProperty('max-height', '32px', 'important');
                    el.style.setProperty('padding', '0 10px', 'important');
                    el.style.setProperty('vertical-align', 'middle', 'important');
                    el.style.setProperty('font-family', 'inherit', 'important');
                    el.style.setProperty('white-space', 'nowrap', 'important');
                    el.style.setProperty('overflow', 'hidden', 'important');
                    el.style.setProperty('opacity', '1', 'important');
                    el.style.setProperty('background-image', 'none', 'important');
                    el.style.setProperty('box-shadow', '0 1px 2px rgba(15,23,42,.18)', 'important');
                    el.style.setProperty('text-decoration', 'none', 'important');
                    el.style.setProperty('flex-shrink', '0', 'important');
                    el.style.setProperty('flex-grow', '0', 'important');
                    try {
                        el.style.setProperty('appearance', 'none', 'important');
                        el.style.setProperty('-moz-appearance', 'none', 'important');
                        el.style.setProperty('-webkit-appearance', 'none', 'important');
                    } catch (_lo_a) { /* ignore */ }
                    el.style.setProperty('-webkit-tap-highlight-color', 'transparent', 'important');
                }
                function logoutForceIdenticalBoxHeight(el) {
                    el.style.setProperty('height', '32px', 'important');
                    el.style.setProperty('min-height', '32px', 'important');
                    el.style.setProperty('max-height', '32px', 'important');
                    el.style.setProperty('line-height', '32px', 'important');
                }

                // Remove any old/existing button instances with wrong style
                // (old id "authBtn" with class btn-logout / old purple giant button screenshot)
                var oldLogoutIds = ['logoutBtn','loginBtn','authBtn','oldLogoutBtn'];
                for (var _lo_k=0; _lo_k<oldLogoutIds.length; _lo_k++) {
                    var oldEl = document.getElementById(oldLogoutIds[_lo_k]);
                    if (oldEl && oldEl.parentNode) { try { oldEl.parentNode.removeChild(oldEl); } catch(_){} }
                }

                var loggedInDivForBtn = document.getElementById('loggedInStatus');
                var logoutBtn = document.createElement('button');
                logoutBtn.type = 'button';
                logoutBtn.id = 'authBtn';
                // NO class="btn-logout" — that rendered the old giant purple/white outline box user hated
                logoutBtn.className = '';
                logoutBoxBase(logoutBtn);
                logoutForceIdenticalBoxHeight(logoutBtn);
                logoutBtn.style.setProperty('display', 'inline-flex', 'important');
                logoutBtn.style.setProperty('align-items', 'center', 'important');
                logoutBtn.style.setProperty('justify-content', 'center', 'important');
                logoutBtn.style.setProperty('gap', '5px', 'important');
                logoutBtn.style.setProperty('min-width', '96px', 'important'); // +8px vs Login (Logout longer text)
                logoutBtn.style.setProperty('background', LO_BG, 'important');
                logoutBtn.style.setProperty('background-color', LO_BG, 'important');
                logoutBtn.style.setProperty('border-color', LO_BORDER, 'important');
                logoutBtn.style.setProperty('color', LO_FG, 'important');
                logoutBtn.style.setProperty('font-size', '13px', 'important');
                logoutBtn.style.setProperty('font-weight', '700', 'important');
                logoutBtn.style.setProperty('cursor', 'pointer', 'important');
                logoutForceIdenticalBoxHeight(logoutBtn);
                logoutBtn.innerHTML =
                    '<img src="' + LO_ICON + '" alt="' + LO_TEXT + '" width="16" height="16" style="display:block;flex-shrink:0;width:16px;height:16px;max-width:16px;max-height:16px;object-fit:contain;object-position:center;' + LO_TINT + ';background:none;border:0;padding:0;margin:0">' +
                    '<span style="display:inline-block;vertical-align:middle;line-height:32px!important;color:' + LO_FG + '!important;font-weight:700!important;font-size:13px!important;background:none;padding:0;margin:0">' + LO_TEXT + '</span>';

                // Insert into #loggedInStatus (same flex-flow slot as before so right align stays perfect)
                if (loggedInDivForBtn) {
                    // Clean any previous button nodes from the div; #loggedInStatus ONLY holds Logout now.
                    var kids = loggedInDivForBtn.children ? Array.prototype.slice.call(loggedInDivForBtn.children) : [];
                    for (var _lo_j=0; _lo_j<kids.length; _lo_j++) {
                        var k = kids[_lo_j];
                        if (!k) continue;
                        if (k.id === 'authBtn' || (k.tagName && /button/i.test(k.tagName))) {
                            try { k.parentNode.removeChild(k); } catch(_){}
                        }
                    }
                    try { loggedInDivForBtn.appendChild(logoutBtn); } catch(_){}
                }

                // Logout click handler: identical to previous logic, same handleLogout call + reload fallback
                logoutBtn.addEventListener('click', async function(e) {
                    e.preventDefault();
                    try {
                        console.log('[DEBUG] Auth button clicked (Logout - new style match Login)');
                    } catch(_) {}
                    if (window.__GOLD_HEADER_CALL && typeof window.__GOLD_HEADER_CALL.fireLogout === 'function') {
                        try { window.__GOLD_HEADER_CALL.fireLogout(); return; } catch(_ghcLo){}
                    }
                    if (typeof handleLogout === 'function') {
                        try { await handleLogout(); } catch (_hl) {
                            try { window.location.reload(); } catch(_){}
                        }
                    } else {
                        try { window.location.reload(); } catch(_){}
                    }
                });

                // —————————————————————————————————————————————————————————————————
                // LEGACY CACHED-SCRIPT OVERWRITE GUARD (header only, ≥150ms).
                // Problem: cached old session.live.js / old session.js (before 20260808)
                //   sets authBtn.textContent='Logout' + className='btn-logout' / 'btn-primary'
                //   AFTER our fresh updateHeaderAuthStatus runs → kills icon, reverts to
                //   plain text-only (no user-circle-minus icon) and/or purple class.
                // Fix: MutationObserver on #loggedInStatus + 150ms interval guard both
                //   re-clone-and-rewrite authBtn back to the gold icon+text layout IF
                //   the inner no longer contains the logout img/svg icon AND the
                //   textContent still equals Logout (i.e. definitely this button).
                // Scope: only runs while session is valid; dies on next navigate;
                //   never touches buttons below header.
                // —————————————————————————————————————————————————————————————————
                try {
                    (function guardGoldLogoutButton() {
                        var targetSlot = document.getElementById('loggedInStatus');
                        if (!targetSlot) return;
                        var GOLD_ICON = LO_ICON;
                        var GOLD_TEXT = LO_TEXT;
                        var guardClicks = 0;
                        function cloneListener(newBtn) {
                            if (!newBtn || guardClicks > 0) return;
                            guardClicks++;
                            newBtn.addEventListener('click', async function(ev) {
                                ev.preventDefault();
                                try { console.log('[DEBUG] Guard: authBtn click (gold)'); } catch(_g){}
                                if (window.__GOLD_HEADER_CALL && typeof window.__GOLD_HEADER_CALL.fireLogout === 'function') {
                                    try { window.__GOLD_HEADER_CALL.fireLogout(); return; } catch(_g0){}
                                }
                                if (typeof handleLogout === 'function') {
                                    try { await handleLogout(); } catch(_g1){ try { window.location.reload(); } catch(_g2){} }
                                } else { try { window.location.reload(); } catch(_g3){} }
                            });
                        }
                        function isBrokenLegacyRewrite(b) {
                            if (!b) return false;
                            var hasImg = (b.querySelectorAll && (b.querySelectorAll('img,svg').length > 0));
                            if (hasImg) return false;
                            var txt = (b.textContent || '').replace(/\s+/g, ' ').trim();
                            return (txt === GOLD_TEXT || txt === 'Login' || txt === 'Sign In');
                        }
                        function rewriteToGoldIfBroken() {
                            var btn = document.getElementById('authBtn');
                            if (!btn) return;
                            if (!isBrokenLegacyRewrite(btn)) return;
                            var slot = document.getElementById('loggedInStatus');
                            if (!slot) return;
                            if (btn.parentNode) { try { btn.parentNode.removeChild(btn); } catch(_g){} }
                            var nb = document.createElement('button');
                            nb.type = 'button';
                            nb.id = 'authBtn';
                            nb.className = '';
                            logoutBoxBase(nb);
                            logoutForceIdenticalBoxHeight(nb);
                            nb.style.setProperty('display','inline-flex','important');
                            nb.style.setProperty('align-items','center','important');
                            nb.style.setProperty('justify-content','center','important');
                            nb.style.setProperty('gap','5px','important');
                            nb.style.setProperty('min-width','96px','important');
                            nb.style.setProperty('background', LO_BG, 'important');
                            nb.style.setProperty('background-color', LO_BG, 'important');
                            nb.style.setProperty('border-color', LO_BORDER, 'important');
                            nb.style.setProperty('color', LO_FG, 'important');
                            nb.style.setProperty('font-size','13px','important');
                            nb.style.setProperty('font-weight','700','important');
                            nb.style.setProperty('cursor','pointer','important');
                            logoutForceIdenticalBoxHeight(nb);
                            nb.innerHTML =
                                '<img src="'+GOLD_ICON+'" alt="'+GOLD_TEXT+'" width="16" height="16" style="display:block;flex-shrink:0;width:16px;height:16px;max-width:16px;max-height:16px;object-fit:contain;object-position:center;'+LO_TINT+';background:none;border:0;padding:0;margin:0">'+
                                '<span style="display:inline-block;vertical-align:middle;line-height:32px!important;color:'+LO_FG+'!important;font-weight:700!important;font-size:13px!important;background:none;padding:0;margin:0">'+GOLD_TEXT+'</span>';
                            guardClicks = 0;
                            cloneListener(nb);
                            try { slot.appendChild(nb); } catch(_g){}
                        }
                        cloneListener(logoutBtn);
                        rewriteToGoldIfBroken();
                        if (typeof window.MutationObserver === 'function') {
                            var mo = new MutationObserver(function(){ rewriteToGoldIfBroken(); });
                            try { mo.observe(targetSlot, { childList: true, subtree: true, attributes: true, characterData: true }); } catch(_g){}
                        }
                        var guardCount = 0;
                        var guardTimer = setInterval(function() {
                            guardCount++;
                            rewriteToGoldIfBroken();
                            if (guardCount > 14) { clearInterval(guardTimer); }
                        }, 25);
                    })();
                } catch (_ginit) { /* ignore guard init errors */ }

                // Trigger page content update if function exists
                safeUpdatePageContentSync();
            } catch (loggedInUiErr) {
                console.error('[DEBUG] updateHeaderAuthStatus: logged-in UI error (session still valid):', loggedInUiErr);
                const loginBoxErr = document.getElementById('loginBox');
                if (loginBoxErr) {
                    loginBoxErr.style.display = 'none';
                }
            }
        } else {
            sailingSyncSuperAdminBodyClass({ valid: false });
            console.log('[DEBUG] updateHeaderAuthStatus: No valid session, showing login box');
            clearSailingLoginAvatars();
            // Show login box or "Your Sailing Results" button
            const loggedInDiv = document.getElementById('loggedInStatus');
            const loginBoxDiv = document.getElementById('loginBox');
            const userNameDisplay = document.getElementById('userNameDisplay');
            const userSasIdDisplay = document.getElementById('userSasIdDisplay');
            const centerCol = document.getElementById('headerUserCenter');

            // Hide logged in status and clear user info
            if (loggedInDiv) {
                loggedInDiv.style.display = 'none';
                loggedInDiv.innerHTML = '';
            }

            // Legacy span clear — ONLY runs when IDs exist (other pages, not /header/)
            if (userNameDisplay) {
                userNameDisplay.textContent = '';
                userNameDisplay.innerHTML = '';
            }

            if (userSasIdDisplay) {
                userSasIdDisplay.textContent = '';
                userSasIdDisplay.innerHTML = '';
            }

            // /header/-owned layout: wipe center column + nudge transform reset
            if (centerCol) {
                centerCol.innerHTML = '';
                try { centerCol.style.removeProperty('transform'); } catch(_){}
                try { centerCol.style.removeProperty('translate'); } catch(_){}
                centerCol.style.setProperty('visibility','hidden','important');
            }

            // Show login box with Sign In button
            if (loginBoxDiv) {
                loginBoxDiv.style.display = 'block';
            }
            
            // Update auth button to "Sign In" (same button, different text/function)
            // Remove any existing buttons with old IDs first
            const oldLogoutBtn = document.getElementById('logoutBtn');
            const oldLoginBtn = document.getElementById('loginBtn');
            if (oldLogoutBtn) {
                oldLogoutBtn.remove();
            }
            if (oldLoginBtn) {
                oldLoginBtn.remove();
            }
            
            sailingRenderLoggedOutAuthButtons(loginBoxDiv);
            
            // "Your Sailing Results" button removed - no longer needed
            
            // Trigger page content update if function exists
            safeUpdatePageContentSync();
        }
    } catch (error) {
        try {
            const sRecover = await checkSession();
            if (sRecover && sRecover.valid) {
                sailingSyncSuperAdminBodyClass(sRecover);
                const lbRec = document.getElementById('loginBox');
                if (lbRec) {
                    lbRec.style.display = 'none';
                }
                return;
            }
        } catch (eRec) {
            /* fall through to logged-out error UI */
        }
        sailingSyncSuperAdminBodyClass({ valid: false });
        console.error('[DEBUG] updateHeaderAuthStatus: Error:', error);
        console.error('[DEBUG] updateHeaderAuthStatus: Stack trace:', error.stack);
        // Show login box on error
        const loggedInDiv = document.getElementById('loggedInStatus');
        const loginBoxDiv = document.getElementById('loginBox');
        const userNameDisplay = document.getElementById('userNameDisplay');
        const userSasIdDisplay = document.getElementById('userSasIdDisplay');
        const centerColErr = document.getElementById('headerUserCenter');

        // Hide logged in status and clear user info
        if (loggedInDiv) {
            loggedInDiv.style.display = 'none';
            loggedInDiv.innerHTML = '';
        }

        // Clear Name and SAS ID when logged out (error state, legacy spans only)
        if (userNameDisplay) {
            userNameDisplay.textContent = '';
            userNameDisplay.innerHTML = '';
        }

        if (userSasIdDisplay) {
            userSasIdDisplay.textContent = '';
            userSasIdDisplay.innerHTML = '';
        }

        // /header/-owned layout: wipe center column + nudge transform reset
        if (centerColErr) {
            centerColErr.innerHTML = '';
            try { centerColErr.style.removeProperty('transform'); } catch(_){}
            try { centerColErr.style.removeProperty('translate'); } catch(_){}
            centerColErr.style.setProperty('visibility','hidden','important');
        }

        // Show login box with Sign In button
        if (loginBoxDiv) {
            loginBoxDiv.style.display = 'block';
        }
        
        // Update auth button to "Sign In" on error (same button, different text/function)
        // Remove any existing buttons with old IDs first
        const oldLogoutBtn = document.getElementById('logoutBtn');
        const oldLoginBtn = document.getElementById('loginBtn');
        if (oldLogoutBtn) {
            oldLogoutBtn.remove();
        }
        if (oldLoginBtn) {
            oldLoginBtn.remove();
        }
        
        sailingRenderLoggedOutAuthButtons(loginBoxDiv);
        
        // "Your Sailing Results" button removed - no longer needed
    }
}

/**
 * Show auto-login confirmation popup
 */
function showAutoLoginPopup() {
    return new Promise((resolve) => {
        let __done = false;
        let __createdAt = 0;
        const host = document.body || document.documentElement;
        if (!host) { resolve(false); return; }

        // Remove any leftover popups immediately
        try {
            var old = host.querySelectorAll('#_srgAutoLoginOverlay, #autoLoginPopupOverlay, [data-srg-popup="1"]');
            for (var i = 0; i < old.length; i++) {
                try { if (old[i].parentNode) old[i].parentNode.removeChild(old[i]); } catch (_) {}
            }
        } catch (_) {}

        const overlay = document.createElement('div');
        overlay.id = 'autoLoginPopupOverlay';
        overlay.setAttribute('data-srg-popup', '1');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);display:flex;align-items:center;justify-content:center;';
        try { overlay.style.setProperty('z-index', '9999999', 'important'); } catch (_) { overlay.style.zIndex = '9999999'; }

        function finish(v) {
            if (__done) return;
            __done = true;
            try { if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay); } catch (_) {}
            try {
                var left = document.querySelectorAll('#autoLoginPopupOverlay, #_srgAutoLoginOverlay, [data-srg-popup="1"]');
                for (var j = 0; j < left.length; j++) {
                    try { if (left[j].parentNode) left[j].parentNode.removeChild(left[j]); } catch (_) {}
                }
            } catch (_) {}
            resolve(!!v);
        }

        const popup = document.createElement('div');
        popup.style.cssText = 'background:white;border-radius:10px;padding:22px 22px 18px;box-shadow:0 10px 30px rgba(0,0,0,0.28);min-width:230px;max-width:300px;text-align:center;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;';

        const title = document.createElement('div');
        title.textContent = 'Auto Login';
        title.style.cssText = 'font-size:17px;font-weight:700;margin-bottom:8px;color:#1a365d;';

        const question = document.createElement('div');
        question.textContent = 'Sign in automatically next time?';
        question.style.cssText = 'font-size:14px;color:#2d3748;margin-bottom:16px;line-height:1.45;';

        const row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:12px;justify-content:center;';

        function mkBtn(txt, bg, fg) {
            const b = document.createElement('button');
            b.type = 'button';
            b.textContent = txt;
            b.style.cssText = 'padding:9px 22px;background:' + bg + ';color:' + fg + ';border:none;border-radius:7px;font-size:14px;font-weight:600;cursor:pointer;min-width:88px;';
            return b;
        }
        const yesBtn = mkBtn('Yes', '#1a365d', '#ffffff');
        const noBtn = mkBtn('No', '#e2e8f0', '#1a365d');

        function onYes(ev) {
            try { if (ev) { ev.preventDefault(); ev.stopPropagation(); } } catch (_) {}
            finish(true);
        }
        function onNo(ev) {
            try { if (ev) { ev.preventDefault(); ev.stopPropagation(); } } catch (_) {}
            finish(false);
        }
        yesBtn.addEventListener('click', onYes, true);
        noBtn.addEventListener('click', onNo, true);

        overlay.addEventListener('click', function (e) {
            if (!e || e.target !== overlay) return;
            finish(false);
        }, true);

        try {
            document.addEventListener('keydown', function onKey(ev) {
                if (!ev || ev.key !== 'Escape') return;
                try { document.removeEventListener('keydown', onKey, true); } catch (_) {}
                finish(false);
            }, true);
        } catch (_) { }

        row.appendChild(yesBtn);
        row.appendChild(noBtn);
        popup.appendChild(title);
        popup.appendChild(question);
        popup.appendChild(row);
        overlay.appendChild(popup);

        // Append now (no delayed re-open after No)
        try {
            __createdAt = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
            if (!__done) host.appendChild(overlay);
        } catch (_) {
            finish(false);
        }
    });
}

// Make function globally available
window.showAutoLoginPopup = showAutoLoginPopup;

/**
 * Handle logout
 */
async function handleLogout() {
    console.log('[DEBUG] handleLogout: Called');
    let enableAutoLogin = false;
    try {
        enableAutoLogin = await showAutoLoginPopup();
    } catch (popupErr) {
        console.error('[DEBUG] handleLogout: showAutoLoginPopup failed, defaulting to no-auto-login:', popupErr);
        enableAutoLogin = false;
    }

    try {
        // Clear user info display immediately
        const userNameDisplay = document.getElementById('userNameDisplay');
        const userSasIdDisplay = document.getElementById('userSasIdDisplay');
        const loggedInDiv = document.getElementById('loggedInStatus');
        const centerCol = document.getElementById('headerUserCenter');

        if (userNameDisplay) {
            userNameDisplay.textContent = '';
            userNameDisplay.innerHTML = '';
        }

        if (userSasIdDisplay) {
            userSasIdDisplay.textContent = '';
            userSasIdDisplay.innerHTML = '';
        }

        if (loggedInDiv) {
            loggedInDiv.style.display = 'none';
            loggedInDiv.innerHTML = '';
        }

        // /header/-owned layout: wipe center column + transform reset
        if (centerCol) {
            centerCol.innerHTML = '';
            try { centerCol.style.removeProperty('transform'); } catch(_){}
            try { centerCol.style.removeProperty('translate'); } catch(_){}
            centerCol.style.setProperty('visibility','hidden','important');
        }
        
        // Call logout endpoint to end session on server
        try {
            const apiBase = (window.API_BASE || window.location.origin || '').replace(/\/$/, '');
            var logoutPath = '/auth/logout';
            try {
                if (window.location && window.location.pathname && window.location.pathname.indexOf('/admin/') === 0) {
                    logoutPath = '/admin/api/logout';
                }
            } catch (ePath) { /* ignore */ }
            const response = await fetch(`${apiBase}${logoutPath}`, {
                method: 'POST',
                credentials: 'include'
            });
            console.log('[DEBUG] handleLogout: Logout response:', response.status);
        } catch (fetchError) {
            console.error('[DEBUG] handleLogout: Logout endpoint error:', fetchError);
        }
        
        // Clear local session (cookies, localStorage)
        clearSession();
        
        // Clear all session-related data
        document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
        document.cookie = 'session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
        localStorage.removeItem('session');
        localStorage.removeItem('sailing_session');
        
        // Handle auto-login preference
        if (!enableAutoLogin) {
            // User chose NOT to enable auto-login - clear stored credentials
            console.log('[DEBUG] handleLogout: User chose not to enable auto-login, clearing credentials');
            sailingSetAutoLoginDisabledOnce();
            localStorage.removeItem('saved_username');
            localStorage.removeItem('saved_password');
            localStorage.removeItem('remember_credentials');
            localStorage.removeItem('saved_login_method');
            
            // Canonical home: / (not /index.html)
            const indexUrl = `${window.location.protocol}//${window.location.host}/`;
            console.log('[DEBUG] handleLogout: Redirecting to public page (no auto-login):', indexUrl);
            window.location.href = indexUrl;
        } else {
            // Yes = remember for NEXT Login click only. Stay logged out now.
            console.log('[DEBUG] handleLogout: Remember for next time — stay logged out');
            try { localStorage.setItem('remember_credentials', 'true'); } catch (_r) {}
            // CRITICAL: do not auto-login on the page we land on after logout
            sailingSetAutoLoginDisabledOnce();
            const indexUrl = `${window.location.protocol}//${window.location.host}/`;
            console.log('[DEBUG] handleLogout: Redirecting logged-out to:', indexUrl);
            window.location.href = indexUrl;
        }
    } catch (error) {
        console.error('[DEBUG] handleLogout: Error:', error);
        // Even on error, clear everything and redirect
        clearSession();
        
        // Clear all session-related data
        document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
        document.cookie = 'session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
        localStorage.removeItem('session');
        localStorage.removeItem('sailing_session');
        
        // Clear stored credentials on error
        localStorage.removeItem('saved_username');
        localStorage.removeItem('saved_password');
        localStorage.removeItem('remember_credentials');
        
        // Clear user info display on error too
        const userNameDisplay = document.getElementById('userNameDisplay');
        const userSasIdDisplay = document.getElementById('userSasIdDisplay');
        const loggedInDiv = document.getElementById('loggedInStatus');
        const centerColErr = document.getElementById('headerUserCenter');

        if (userNameDisplay) {
            userNameDisplay.textContent = '';
            userNameDisplay.innerHTML = '';
        }

        if (userSasIdDisplay) {
            userSasIdDisplay.textContent = '';
            userSasIdDisplay.innerHTML = '';
        }

        if (loggedInDiv) {
            loggedInDiv.style.display = 'none';
            loggedInDiv.innerHTML = '';
        }

        // /header/-owned layout: wipe center column + transform reset
        if (centerColErr) {
            centerColErr.innerHTML = '';
            try { centerColErr.style.removeProperty('transform'); } catch(_){}
            try { centerColErr.style.removeProperty('translate'); } catch(_){}
            centerColErr.style.setProperty('visibility','hidden','important');
        }

        const indexUrl = `${window.location.protocol}//${window.location.host}/`;
        console.log('[DEBUG] handleLogout: Redirecting to public page (error):', indexUrl);
        window.location.href = indexUrl;
    }
}

// After logout we stay logged out. Do NOT auto-login on page load.
// Auto Login Yes/No only on Logout. Login click silently uses remember if Yes was chosen.
(function ensureSurgicalAutoLoginGuard() {
    try {
        var p = String((window.location && window.location.pathname) || '/').replace(/\/+$/, '') || '/';
        var isLoginOrSignupPage =
            p.indexOf('/login') === 0 || p.indexOf('/signup') === 0 || p.endsWith('/login.html') || p.endsWith('/signup.html');
        if (isLoginOrSignupPage) {
            sailingSetAutoLoginDisabledOnce();
        }
        // Intentionally no on-load auto-login popup (was repeating + logging users back in after Logout).
    } catch(_eMain) {}
})();

// Ensure button text persists - monitor and fix if changed
(function ensureButtonText() {
    if (typeof sailingsaHubHeaderOwnedByBlankLandingJs === 'function' && sailingsaHubHeaderOwnedByBlankLandingJs()) {
        return;
    }
    function fixButtonText() {
        const splitSignInBtn = document.getElementById('authSignInBtn');
        const splitSignUpBtn = document.getElementById('authSignUpBtn');
        if (splitSignInBtn || splitSignUpBtn) {
            return;
        }
        const authBtn = document.getElementById('authBtn');
        if (authBtn) {
            const loginBox = document.getElementById('loginBox');
            const loggedInStatus = document.getElementById('loggedInStatus');
            
            // Check if user should be logged out (loginBox visible, loggedInStatus hidden)
            const shouldBeLoggedOut = loginBox && loginBox.style.display !== 'none' && 
                                     (!loggedInStatus || loggedInStatus.style.display === 'none');
            
            if (shouldBeLoggedOut) {
                return;
            }
        }
    }
    
    // Check immediately and repeatedly
    function startChecking() {
        fixButtonText();
        setTimeout(fixButtonText, 100);
        setTimeout(fixButtonText, 300);
        setTimeout(fixButtonText, 500);
        setTimeout(fixButtonText, 1000);
        setTimeout(fixButtonText, 2000);
        // Keep checking every 2 seconds for first 10 seconds
        let checks = 0;
        const interval = setInterval(function() {
            fixButtonText();
            checks++;
            if (checks >= 5) {
                clearInterval(interval);
            }
        }, 2000);
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startChecking);
    } else {
        startChecking();
    }
    
    // Monitor for changes with MutationObserver
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' || mutation.type === 'characterData' || mutation.type === 'attributes') {
                setTimeout(fixButtonText, 10);
            }
        });
    });
    
    // Start observing when DOM is ready
    function startObserving() {
        const authBtn = document.getElementById('authBtn');
        const loginBox = document.getElementById('loginBox');
        if (authBtn) {
            observer.observe(authBtn, {
                childList: true,
                characterData: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class']
            });
        }
        if (loginBox) {
            observer.observe(loginBox, {
                attributes: true,
                attributeFilter: ['style']
            });
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startObserving);
    } else {
        setTimeout(startObserving, 500);
    }
})();

// Report real browser page for Online Users + Public current page (path+query).
(function sailingReportCurrentPagePath() {
    var lastSent = '';
    function report() {
        try {
            var path = String(window.location.pathname || '/') + String(window.location.search || '');
            if (path === lastSent) return;
            lastSent = path;
            fetch('/auth/session?path=' + encodeURIComponent(path), {
                credentials: 'include',
                cache: 'no-store'
            }).catch(function () {});
        } catch (e) {}
    }
    function reportForce() {
        lastSent = '';
        report();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', reportForce);
    } else {
        reportForce();
    }
    try { window.addEventListener('popstate', reportForce); } catch (e2) {}
    try { window.addEventListener('pageshow', reportForce); } catch (e3) {}
    try {
        var _ps = history.pushState;
        var _rs = history.replaceState;
        if (typeof _ps === 'function') {
            history.pushState = function () {
                var r = _ps.apply(this, arguments);
                reportForce();
                return r;
            };
        }
        if (typeof _rs === 'function') {
            history.replaceState = function () {
                var r = _rs.apply(this, arguments);
                reportForce();
                return r;
            };
        }
    } catch (e4) {}
    // No 15s heartbeat — that inflated "session duration" with zero new pages.
    // Presence/duration must come from real path changes only.
    // On leave/hide: close current page dwell (time-on-page).
    try {
        function sendLeave() {
            try {
                // MUST be GET — /auth/session leave is GET-only. sendBeacon() POSTs and never closes dwell.
                var path = String(window.location.pathname || '/') + String(window.location.search || '');
                var url = '/auth/session?path=' + encodeURIComponent(path) + '&leave=1';
                try {
                    var eg = (window.__ssaEngageTokens || []);
                    if (eg && eg.length) url += '&engage=' + encodeURIComponent(eg.join(','));
                } catch (eE) {}
                if (typeof fetch === 'function') {
                    fetch(url, { method: 'GET', credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
                }
                try {
                    var img = new Image();
                    img.src = url + '&_=' + Date.now();
                } catch (eImg) {}
            } catch (eL) {}
        }
        window.addEventListener('pagehide', sendLeave);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'hidden') sendLeave();
        });
        // While tab visible: soft heartbeat so landing-only dwell can stop at real leave
        // (same-URL touch bumps last_activity; does not add trail rows).
        try {
            /* LANDING_DWELL_HEARTBEAT */
            setInterval(function () {
                try {
                    if (document.visibilityState !== 'visible') return;
                    var path = String(window.location.pathname || '/') + String(window.location.search || '');
                    var hb = '/auth/session?path=' + encodeURIComponent(path);
                    try {
                        var eg2 = (window.__ssaEngageTokens || []);
                        if (eg2 && eg2.length) hb += '&engage=' + encodeURIComponent(eg2.join(','));
                    } catch (eE2) {}
                    fetch(hb, {
                        method: 'GET',
                        credentials: 'include',
                        cache: 'no-store',
                        keepalive: true
                    }).catch(function () {});
                } catch (eH) {}
            }, 45000);
        } catch (eH2) {}
    } catch (e6) {}
})();

/* LITE_PAGE_ENGAGE — scroll / search / first click (bot vs real on long home dwell) */
(function () {
  try {
    window.__ssaEngageTokens = window.__ssaEngageTokens || [];
    function addTok(t) {
      try {
        if (!t) return;
        if (window.__ssaEngageTokens.indexOf(t) >= 0) return;
        window.__ssaEngageTokens.push(t);
        // push soon so Live can see it without waiting for leave
        var path = String(window.location.pathname || '/') + String(window.location.search || '');
        var url = '/auth/session?path=' + encodeURIComponent(path) + '&engage=' + encodeURIComponent(window.__ssaEngageTokens.join(','));
        if (typeof fetch === 'function') {
          fetch(url, { method: 'GET', credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
        }
      } catch (e) {}
    }
    function isSearchEl(el) {
      if (!el || !el.tagName) return false;
      var tag = String(el.tagName).toLowerCase();
      if (tag === 'input' || tag === 'textarea') {
        var ty = String(el.type || '').toLowerCase();
        var nm = String(el.name || el.id || '').toLowerCase();
        var ph = String(el.placeholder || '').toLowerCase();
        var role = String(el.getAttribute && el.getAttribute('role') || '').toLowerCase();
        if (ty === 'search') return true;
        if (role === 'searchbox') return true;
        if (nm.indexOf('search') >= 0 || nm === 'q' || nm.indexOf('query') >= 0) return true;
        if (ph.indexOf('search') >= 0) return true;
      }
      return false;
    }
    // scroll ~halfway
    var scrolled = false;
    function onScroll() {
      if (scrolled) return;
      try {
        var doc = document.documentElement || document.body;
        var max = Math.max(1, (doc.scrollHeight || 0) - (window.innerHeight || 0));
        var y = window.pageYOffset || doc.scrollTop || 0;
        if (y / max >= 0.35) {
          scrolled = true;
          addTok('scrolled');
          window.removeEventListener('scroll', onScroll, { passive: true });
        }
      } catch (e) {}
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    // search focus / type
    document.addEventListener('focusin', function (ev) {
      if (isSearchEl(ev.target)) addTok('searched');
    }, true);
    document.addEventListener('input', function (ev) {
      if (isSearchEl(ev.target)) addTok('searched');
    }, true);
    // first meaningful click/tap
    var clicked = false;
    document.addEventListener('click', function (ev) {
      if (clicked) return;
      try {
        var t = ev.target;
        if (!t) return;
        var el = t.closest ? t.closest('a,button,[role="button"],input[type="submit"]') : null;
        if (!el) return;
        clicked = true;
        addTok('clicked');
      } catch (e) {}
    }, true);
  } catch (e0) {}
})();


// Make functions globally available
window.showState = showState;
window.showPopup = showPopup;
window.hidePopup = hidePopup;
window.handleLogout = handleLogout;
window.showAutoLoginPopup = showAutoLoginPopup;
window.sailingsaIsClassSpaPath = sailingsaIsClassSpaPath;

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        checkSessionAndShowPopup,
        showPopup,
        hidePopup,
        showState,
        storeSession,
        getStoredSession,
        clearSession,
        redirectToLandingPage,
        updateHeaderAuthStatus,
        handleLogout
    };
}
