/* Compact claim/sign-in overlay. Header layout is not touched.
   Door 1 (Claim): stay on the sailor. Door 2 (header Sign Up): still /signup.html. */
(function () {
    'use strict';
    if (window.__ssaSignupOverlayWired) return;
    window.__ssaSignupOverlayWired = true;

    var OVERLAY_ID = 'ssa-auth-overlay';
    var FRAME_ID = 'ssa-auth-overlay-frame';
    var TEASER_ID = 'ssa-sailor-teaser';

    function hasSession() {
        try {
            if (localStorage.getItem('session')) return true;
        } catch (e1) {}
        try {
            if (document.cookie.split(';').some(function (c) {
                return c.trim().indexOf('session=') === 0 && c.trim().length > 8;
            })) return true;
        } catch (e2) {}
        try {
            if (window.currentSession || window.__ssaSession) return true;
        } catch (e3) {}
        return false;
    }

    function claimFromPage() {
        var claim = window.__ssaClaimSailor || {};
        var sid = claim.sid || '';
        var name = claim.name || '';
        var cta = document.getElementById('sailorClaimCta') || document.querySelector('.sailor-claim-cta, a.sa-claim-banner, [data-sas-id]');
        if (cta) {
            sid = sid || cta.getAttribute('data-sas-id') || '';
            if (!name) {
                var n1 = document.querySelector('.sailor-name-first, .sa-approved-sailor-name-first');
                var n2 = document.querySelector('.sailor-name-last, .sa-approved-sailor-name-last');
                name = [n1 && n1.textContent, n2 && n2.textContent].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
            }
        }
        return { sid: String(sid || '').trim(), name: String(name || '').trim() };
    }

    function authUrl(kind) {
        var claim = claimFromPage();
        var ret = window.location.href || '/';
        if (kind === 'signin') {
            return '/login.html?embed=1&v=20261128overlay&returnTo=' + encodeURIComponent(ret);
        }
        var u = '/signup.html?signup=1&embed=1';
        if (claim.sid) u += '&sas_id=' + encodeURIComponent(claim.sid);
        if (claim.name) u += '&name=' + encodeURIComponent(claim.name);
        u += '&returnTo=' + encodeURIComponent(ret);
        return u;
    }

    function ensureStyle() {
        if (document.getElementById('ssa-auth-overlay-style')) return;
        var s = document.createElement('style');
        s.id = 'ssa-auth-overlay-style';
        s.textContent =
            '#' + OVERLAY_ID + '{position:fixed;inset:0;z-index:10050;display:none;align-items:flex-end;justify-content:center;background:rgba(10,35,81,.45);padding:8px;box-sizing:border-box;}' +
            '#' + OVERLAY_ID + '.is-open{display:flex;}' +
            '#' + OVERLAY_ID + ' .ssa-auth-sheet{width:100%;max-width:420px;height:min(92dvh,760px);background:#fff;border-radius:12px 12px 0 0;overflow:hidden;box-shadow:0 18px 60px rgba(0,0,0,.45);display:flex;flex-direction:column;}' +
            '@media (min-width:768px){#' + OVERLAY_ID + '{align-items:center;}#' + OVERLAY_ID + ' .ssa-auth-sheet{border-radius:12px;height:min(88vh,720px);}}' +
            '#' + OVERLAY_ID + ' .ssa-auth-sheet-bar{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 10px;background:#001f3f;color:#fff;font-size:13px;line-height:1.2;}' +
            '#' + OVERLAY_ID + ' .ssa-auth-sheet-bar button{min-height:44px;min-width:44px;border:0;background:transparent;color:#fff;font-size:18px;cursor:pointer;}' +
            '#' + OVERLAY_ID + ' iframe{flex:1;width:100%;border:0;background:#fff;}' +
            '#' + TEASER_ID + '{margin:8px 0;padding:10px 12px;border:1px solid #fdba74;background:#fff7ed;border-radius:8px;font-size:14px;line-height:1.35;color:#9a3412;}' +
            '#' + TEASER_ID + ' button{margin-top:8px;min-height:44px;padding:8px 12px;border:0;border-radius:8px;background:#c62828;color:#fff;font-weight:600;font-size:14px;cursor:pointer;}' +
            'body.ssa-guest-teaser .sailor-stats-section,' +
            'body.ssa-guest-teaser .sailor-career-regatta-history,' +
            'body.ssa-guest-teaser .sailor-ai-overview,' +
            'body.ssa-guest-teaser .sailor-tab-panel-media,' +
            'body.ssa-guest-teaser [data-tab-panel="media"],' +
            'body.ssa-guest-teaser .sailor-rankings-block,' +
            'body.ssa-guest-teaser .class-results-section,' +
            'body.ssa-guest-teaser .sa-approved-sailor-mid,' +
            'body.ssa-guest-teaser .sa-ranks-mid-slot,' +
            'body.ssa-guest-teaser .sa-header-mid-slot,' +
            'body.ssa-guest-teaser #dev1-header-mid-slot,' +
            'body.ssa-guest-teaser #dev1-ranks-mid-slot,' +
            'body.ssa-guest-teaser .rank-hero,' +
            'body.ssa-guest-teaser [data-ns-stat-stack],' +
            'body.ssa-guest-teaser [data-ns-col-hdr],' +
            'body.ssa-guest-teaser .ne-card-stats{display:none !important;}';
        document.head.appendChild(s);
    }

    function ensureOverlay() {
        ensureStyle();
        var el = document.getElementById(OVERLAY_ID);
        if (el) return el;
        el = document.createElement('div');
        el.id = OVERLAY_ID;
        el.setAttribute('role', 'dialog');
        el.setAttribute('aria-modal', 'true');
        el.setAttribute('aria-label', 'Sign up');
        el.innerHTML =
            '<div class="ssa-auth-sheet">' +
            '<div class="ssa-auth-sheet-bar"><span data-ssa-auth-title>Claim your profile</span>' +
            '<button type="button" data-ssa-auth-close aria-label="Close">×</button></div>' +
            '<iframe id="' + FRAME_ID + '" title="Sign up"></iframe></div>';
        document.body.appendChild(el);
        el.addEventListener('click', function (e) {
            if (e.target === el) closeOverlay();
        });
        el.querySelector('[data-ssa-auth-close]').addEventListener('click', closeOverlay);
        var frame = el.querySelector('iframe');
        frame.addEventListener('load', function () {
            try {
                var path = frame.contentWindow.location.pathname || '';
                if (/signup\.html|login\.html/i.test(path)) return;
                if (/^\/sailor\//i.test(path) || path === '/') {
                    closeOverlay();
                    window.location.reload();
                }
            } catch (err) {}
        });
        return el;
    }

    function openAuthOverlay(kind) {
        var el = ensureOverlay();
        var title = el.querySelector('[data-ssa-auth-title]');
        if (title) title.textContent = kind === 'signin' ? 'Sign in' : 'Claim your profile';
        var frame = document.getElementById(FRAME_ID);
        frame.src = authUrl(kind);
        el.classList.add('is-open');
        el.style.display = 'flex';
        try {
            if (window.__trackFunnelEvent) {
                var claim = claimFromPage();
                window.__trackFunnelEvent(kind === 'signin' ? 'login_overlay_open' : 'claim_cta_click', claim.sid || '', true, '', {
                    returnTo: (window.location && window.location.pathname) ? String(window.location.pathname) : '/'
                });
            }
        } catch (e) {}
    }

    function closeOverlay() {
        var el = document.getElementById(OVERLAY_ID);
        if (!el) return;
        el.classList.remove('is-open');
        el.style.display = 'none';
        var frame = document.getElementById(FRAME_ID);
        if (frame) frame.src = 'about:blank';
    }

    window.openSsaAuthOverlay = openAuthOverlay;
    window.closeSsaAuthOverlay = closeOverlay;

    window.addEventListener('message', function (ev) {
        var data = ev && ev.data;
        if (!data || typeof data !== 'object') return;
        if (data.type === 'ssa-auth-close') closeOverlay();
        if (data.type === 'ssa-auth-done') {
            closeOverlay();
            try {
                if (data.url) window.location.href = data.url;
                else window.location.reload();
            } catch (e) {
                window.location.reload();
            }
        }
    });

    function isAuthTrigger(el) {
        if (!el || !el.closest) return null;
        if (el.closest('#btnLoginRequiredSignIn')) return 'signin';
        if (el.closest('#btnLoginRequiredSignUp')) return 'signup';
        if (el.closest('a.sailor-claim-cta, a.sa-claim-banner, #sailorClaimCta, button.sa-looked-claim, [data-ssa-list-claim]')) return 'signup';
        return null;
    }

    document.addEventListener('click', function (e) {
        var kind = isAuthTrigger(e.target);
        if (!kind) return;
        e.preventDefault();
        e.stopPropagation();
        if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
        var t = e.target.closest('a.sailor-claim-cta, a.sa-claim-banner, #sailorClaimCta, button.sa-looked-claim, [data-ssa-list-claim]');
        if (t) {
            var slot = t.closest('[data-sas-id], .ssa-dev1-inject, .sa-approved-sailor-card');
            var sid = t.getAttribute('data-sas-id') || (slot && slot.getAttribute('data-sas-id')) || '';
            var nameEl = slot && slot.querySelector('.sa-approved-sailor-name, .sailor-name');
            window.__ssaClaimSailor = {
                sid: sid || (window.__ssaClaimSailor && window.__ssaClaimSailor.sid) || '',
                name: (nameEl && nameEl.textContent.replace(/\s+/g, ' ').trim()) || (window.__ssaClaimSailor && window.__ssaClaimSailor.name) || ''
            };
        }
        openAuthOverlay(kind);
    }, true);

    function applyTeaser() {
        ensureStyle();
        if (hasSession()) {
            document.body.classList.remove('ssa-guest-teaser');
            var old = document.getElementById(TEASER_ID);
            if (old && old.parentNode) old.parentNode.removeChild(old);
            return;
        }
        try {
            var path = (window.location.pathname || '').replace(/\/+$/, '') || '/';
            if (!/^\/sailor\//i.test(path)) return;
        } catch (ePath) {
            return;
        }
        var host = document.querySelector('.sailor-profile-header, .sailor-identity, .sa-approved-sailor-card');
        if (!host) return;
        document.body.classList.add('ssa-guest-teaser');
        if (document.getElementById(TEASER_ID)) return;
        var box = document.createElement('div');
        box.id = TEASER_ID;
        box.innerHTML = '<strong>Sign up to see the rest</strong><div>Name, club and last event stay public. Career, ranks and media unlock when you claim this profile.</div><button type="button">Claim this profile</button>';
        box.querySelector('button').addEventListener('click', function () {
            openAuthOverlay('signup');
        });
        var header = document.querySelector('.sailor-profile-header') || host;
        if (header && header.parentNode) header.parentNode.insertBefore(box, header.nextSibling);
        else host.appendChild(box);
    }

    var teaserTimer = null;
    function scheduleTeaser() {
        clearTimeout(teaserTimer);
        teaserTimer = setTimeout(applyTeaser, 80);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scheduleTeaser);
    } else {
        scheduleTeaser();
    }
    var obs = new MutationObserver(scheduleTeaser);
    obs.observe(document.documentElement, { childList: true, subtree: true });
})();
