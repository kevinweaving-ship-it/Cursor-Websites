
document.documentElement.classList.add('temp-landing-layout-pending');
document.addEventListener('DOMContentLoaded', function () {
    async function initTempLanding() {
        var tempPath = '/';
        try {
            document.querySelectorAll('a.js-go-home').forEach(function (a) {
                a.setAttribute('href', tempPath);
            });
            document.querySelectorAll('.search-mode-btn').forEach(function (a) {
                a.setAttribute('href', tempPath);
            });
            var menuSailor = document.querySelector('#navMenuOverlay a[href="/"]');
            if (menuSailor) menuSailor.setAttribute('href', tempPath);
        } catch (_) {}

        var loginBox = document.getElementById('loginBox');
        var loggedInStatus = document.getElementById('loggedInStatus');
        var IS_GOLD_HEADER = !!document.getElementById('headerUserCenter');

        function tempLoginUrl() {
            return '/login.html?returnTo=' + encodeURIComponent(tempPath);
        }

        function tempSignupUrl() {
            return '/signup.html?signup=1&returnTo=' + encodeURIComponent(tempPath);
        }

        function getTempLandingSearchTarget() {
            return document.getElementById('temp-landing-links-row')
                || document.getElementById('temp-landing-sailor-row')
                || document.querySelector('.search-header-container.sailor-search-pills');
        }

        function getTempLandingHeaderOffset() {
            var siteHeader = document.querySelector('.site-header');
            var headerHeight = siteHeader ? Math.ceil(siteHeader.getBoundingClientRect().height || 0) : 0;
            return headerHeight + 12;
        }

        function getTempLandingSearchTargetTop() {
            var target = getTempLandingSearchTarget();
            if (!target) return 0;
            var rect = target.getBoundingClientRect();
            var absoluteTop = rect.top + (window.pageYOffset || document.documentElement.scrollTop || 0);
            return Math.max(absoluteTop - getTempLandingHeaderOffset(), 0);
        }

        function scrollTempLandingSearchIntoView() {
            try {
                var target = getTempLandingSearchTarget();
                if (!target) return;
                window.scrollTo({
                    top: getTempLandingSearchTargetTop(),
                    behavior: 'smooth'
                });
            } catch (_) {}
        }

        function keepTempLandingSearchVisible(preferSmooth) {
            try {
                var target = getTempLandingSearchTarget();
                if (!target) return;
                var desiredTop = getTempLandingSearchTargetTop();
                var currentTop = window.pageYOffset || document.documentElement.scrollTop || 0;
                var targetRect = target.getBoundingClientRect();
                var headerOffset = getTempLandingHeaderOffset();
                var targetIsVisibleAtTop =
                    targetRect.top >= (headerOffset - 8) &&
                    targetRect.top <= (headerOffset + 18);
                if (targetIsVisibleAtTop && Math.abs(currentTop - desiredTop) < 12) return;
                window.scrollTo({
                    top: desiredTop,
                    behavior: preferSmooth ? 'smooth' : 'auto'
                });
            } catch (_) {}
        }

        var tempLandingKeepVisibleTimer = null;
        function scheduleKeepTempLandingSearchVisible(preferSmooth) {
            try {
                if (tempLandingKeepVisibleTimer) {
                    window.clearTimeout(tempLandingKeepVisibleTimer);
                }
            } catch (_) {}
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    keepTempLandingSearchVisible(preferSmooth);
                });
            });
            tempLandingKeepVisibleTimer = window.setTimeout(function () {
                keepTempLandingSearchVisible(false);
            }, 160);
        }

        function setupTempLandingSearchLayout() {
            var header = document.querySelector('.search-header-container.sailor-search-pills');
            var sailorSection = document.getElementById('sailor-search-section');
            var sailorForm = document.getElementById('sailor-search-form');
            var sailorInput = document.getElementById('sailor-search-input');
            var buttonWrap = sailorSection ? sailorSection.querySelector('.search-mode-buttons') : null;
            var sailorBtn = sailorSection ? sailorSection.querySelector('.search-mode-btn[data-mode="sailor"]') : null;
            var regattaBtn = sailorSection ? sailorSection.querySelector('.search-mode-btn[data-mode="regatta"]') : null;
            if (!header || !sailorSection || !sailorForm || !sailorInput || !sailorBtn || !regattaBtn) return;
            sailorBtn.setAttribute('href', '#');
            regattaBtn.setAttribute('href', '#');

            var sailorDraft = sailorInput.value || '';
            var regattaDraft = '';
            var tempModeBootstrapGuard = false;
            header.classList.add('temp-landing-search-stack');

            var sailorRow = document.getElementById('temp-landing-sailor-row');
            var regattaRow = document.getElementById('temp-landing-regatta-row');
            var regattaInput = document.getElementById('temp-landing-regatta-input');
            var linksRow = document.getElementById('temp-landing-links-row');

            if (!sailorRow || !regattaRow || !regattaInput) {
                sailorRow = document.createElement('div');
                sailorRow.id = 'temp-landing-sailor-row';
                sailorRow.className = 'temp-landing-search-row is-active';

                regattaRow = document.createElement('div');
                regattaRow.id = 'temp-landing-regatta-row';
                regattaRow.className = 'temp-landing-search-row';

                var regattaForm = document.createElement('form');
                regattaForm.id = 'temp-landing-regatta-form';
                regattaForm.className = 'temp-landing-regatta-form';
                regattaForm.setAttribute('role', 'search');

                var regattaWrap = document.createElement('div');
                regattaWrap.className = 'temp-landing-regatta-input-wrap sailor-search-input-wrap';

                var regattaIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                regattaIcon.setAttribute('viewBox', '0 0 24 24');
                regattaIcon.setAttribute('class', 'search-icon');
                var regattaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                regattaPath.setAttribute('d', 'M21 21l-4.35-4.35m1.35-5.65a7 7 0 1 1-14 0 7 7 0 0 1 14 0z');
                regattaIcon.appendChild(regattaPath);

                regattaInput = document.createElement('input');
                regattaInput.type = 'text';
                regattaInput.id = 'temp-landing-regatta-input';
                regattaInput.className = 'temp-landing-regatta-input';
                regattaInput.placeholder = 'Regatta name or date';
                regattaInput.autocomplete = 'off';
                regattaInput.setAttribute('aria-label', 'Regatta name or date');

                regattaWrap.appendChild(regattaIcon);
                regattaWrap.appendChild(regattaInput);
                regattaForm.appendChild(regattaWrap);

                sailorBtn.parentNode && sailorBtn.parentNode.removeChild(sailorBtn);
                regattaBtn.parentNode && regattaBtn.parentNode.removeChild(regattaBtn);
                if (buttonWrap && buttonWrap.parentNode) {
                    buttonWrap.parentNode.removeChild(buttonWrap);
                }

                sailorRow.appendChild(sailorBtn);
                sailorRow.appendChild(sailorForm);
                regattaRow.appendChild(regattaBtn);
                regattaRow.appendChild(regattaForm);

                sailorSection.innerHTML = '';
                sailorSection.appendChild(linksRow || document.createElement('div'));
                sailorSection.appendChild(sailorRow);
                sailorSection.appendChild(regattaRow);
            }

            if (!linksRow || linksRow.id !== 'temp-landing-links-row') {
                linksRow = document.createElement('div');
                linksRow.id = 'temp-landing-links-row';
                linksRow.className = 'temp-landing-link-pills';
                [
                    { label: 'Club List', href: 'https://sailingsa.co.za/clubs' },
                    { label: 'Class List', href: 'https://sailingsa.co.za/classes' },
                    { label: 'Recurring Events List', href: 'https://sailingsa.co.za/events-logos' }
                ].forEach(function (item) {
                    var link = document.createElement('a');
                    link.className = 'temp-landing-link-pill';
                    link.href = item.href;
                    link.textContent = item.label;
                    linksRow.appendChild(link);
                });
            }
            if (linksRow.parentNode !== sailorSection) {
                sailorSection.insertBefore(linksRow, sailorSection.firstChild);
            }

            var sailorWrap = sailorForm.querySelector('.sailor-search-input-wrap');
            var regattaForm = regattaRow.querySelector('#temp-landing-regatta-form');
            var regattaWrap = regattaRow.querySelector('.temp-landing-regatta-input-wrap');

            function refreshTempLandingSearchState() {
                var mode = window.searchMode || 'sailor';
                sailorRow.classList.toggle('is-active', mode === 'sailor');
                regattaRow.classList.toggle('is-active', mode === 'regatta');
            }

            function restoreVisibleSailorInput() {
                if (!sailorInput) return;
                sailorInput.value = sailorDraft;
            }

            if (!window.__tempLandingApplyRegattaFilterWrapped && typeof window.applyRegattaFilter === 'function') {
                var originalApplyRegattaFilter = window.applyRegattaFilter;
                window.applyRegattaFilter = async function () {
                    var sharedBefore = sailorInput ? sailorInput.value : '';
                    if ((window.searchMode || 'sailor') === 'regatta' && sailorInput && regattaInput) {
                        sailorInput.value = regattaInput.value || regattaDraft || '';
                    }
                    try {
                        return await originalApplyRegattaFilter.apply(this, arguments);
                    } finally {
                        if (sailorInput) {
                            sailorInput.value = sailorDraft;
                        }
                        scheduleKeepTempLandingSearchVisible(false);
                    }
                };
                window.__tempLandingApplyRegattaFilterWrapped = true;
            }

            function activateSailorModeFromTemp() {
                if (typeof window.setSearchMode === 'function' && (window.searchMode || 'sailor') !== 'sailor') {
                    window.setSearchMode('sailor', true);
                } else if (typeof window.setSearchMode !== 'function' && sailorBtn && !tempModeBootstrapGuard) {
                    tempModeBootstrapGuard = true;
                    sailorBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    tempModeBootstrapGuard = false;
                }
                window.setTimeout(function () {
                    restoreVisibleSailorInput();
                    refreshTempLandingSearchState();
                    scheduleKeepTempLandingSearchVisible(false);
                }, 0);
            }

            function activateRegattaModeFromTemp() {
                if (typeof window.setSearchMode === 'function' && (window.searchMode || 'sailor') !== 'regatta') {
                    window.setSearchMode('regatta', true);
                } else if (typeof window.setSearchMode !== 'function' && regattaBtn && !tempModeBootstrapGuard) {
                    tempModeBootstrapGuard = true;
                    regattaBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    tempModeBootstrapGuard = false;
                }
                window.setTimeout(function () {
                    restoreVisibleSailorInput();
                    refreshTempLandingSearchState();
                    scheduleKeepTempLandingSearchVisible(false);
                }, 0);
            }

            function bindFieldModeActivation(field, activateFn, targetMode) {
                if (!field || field.dataset.tempLandingFieldModeBound) return;
                field.dataset.tempLandingFieldModeBound = '1';
                field.addEventListener('pointerdown', function () {
                    if ((window.searchMode || 'sailor') !== targetMode) {
                        activateFn();
                    }
                });
                field.addEventListener('click', function () {
                    if ((window.searchMode || 'sailor') !== targetMode) {
                        activateFn();
                    }
                });
            }

            if (!sailorInput.dataset.tempLandingBound) {
                sailorInput.dataset.tempLandingBound = '1';
                sailorInput.addEventListener('focus', function () {
                    activateSailorModeFromTemp();
                    scheduleKeepTempLandingSearchVisible(true);
                });
                sailorInput.addEventListener('input', function () {
                    sailorDraft = sailorInput.value;
                    if ((window.searchMode || 'sailor') !== 'sailor') {
                        activateSailorModeFromTemp();
                    } else {
                        refreshTempLandingSearchState();
                        scheduleKeepTempLandingSearchVisible(false);
                    }
                });
            }
            bindFieldModeActivation(sailorInput, activateSailorModeFromTemp, 'sailor');
            bindFieldModeActivation(sailorForm, activateSailorModeFromTemp, 'sailor');
            bindFieldModeActivation(sailorWrap, activateSailorModeFromTemp, 'sailor');
            bindFieldModeActivation(sailorRow, activateSailorModeFromTemp, 'sailor');

            if (!regattaInput.dataset.tempLandingBound) {
                regattaInput.dataset.tempLandingBound = '1';
                regattaInput.addEventListener('focus', function () {
                    activateRegattaModeFromTemp();
                    scheduleKeepTempLandingSearchVisible(true);
                });
                regattaInput.addEventListener('input', function () {
                    regattaDraft = regattaInput.value;
                    activateRegattaModeFromTemp();
                    scheduleKeepTempLandingSearchVisible(false);
                });
                regattaInput.form && regattaInput.form.addEventListener('submit', function (event) {
                    event.preventDefault();
                    regattaDraft = regattaInput.value;
                    activateRegattaModeFromTemp();
                    scheduleKeepTempLandingSearchVisible(true);
                });
            }
            bindFieldModeActivation(regattaInput, activateRegattaModeFromTemp, 'regatta');
            bindFieldModeActivation(regattaForm, activateRegattaModeFromTemp, 'regatta');
            bindFieldModeActivation(regattaWrap, activateRegattaModeFromTemp, 'regatta');
            bindFieldModeActivation(regattaRow, activateRegattaModeFromTemp, 'regatta');

            if (!sailorBtn.dataset.tempLandingBound) {
                sailorBtn.dataset.tempLandingBound = '1';
                sailorBtn.addEventListener('click', function (event) {
                    if (tempModeBootstrapGuard) return;
                    event.preventDefault();
                    event.stopPropagation();
                    window.setTimeout(function () {
                        activateSailorModeFromTemp();
                        scrollTempLandingSearchIntoView();
                    }, 0);
                }, true);
            }

            if (!regattaBtn.dataset.tempLandingBound) {
                regattaBtn.dataset.tempLandingBound = '1';
                regattaBtn.addEventListener('click', function (event) {
                    if (tempModeBootstrapGuard) return;
                    event.preventDefault();
                    event.stopPropagation();
                    window.setTimeout(function () {
                        activateRegattaModeFromTemp();
                        scrollTempLandingSearchIntoView();
                    }, 0);
                }, true);
            }

            restoreVisibleSailorInput();
            refreshTempLandingSearchState();
            document.documentElement.classList.remove('temp-landing-layout-pending');
        }

        function sanitizeTempProfileShell(isLoggedIn) {
            try {
                var _stps = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                if (/^\/sailor\//i.test(_stps) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) return;
            } catch (_) {}
            try {
                var root = document.getElementById('sailor-search-results') || document;
                root.querySelectorAll('.sailor-profile-tab[data-tab="media"], .sailor-profile-tab[data-tab="activity"]').forEach(function (el) {
                    el.remove();
                });
                root.querySelectorAll('#sailor-tab-panel-media, #sailor-tab-panel-activity').forEach(function (el) {
                    el.remove();
                });
                if (isLoggedIn) {
                    root.querySelectorAll('p').forEach(function (p) {
                        var text = (p.textContent || '').trim();
                        if (text === 'Select a sailor from search or sign in to see your profile here.') {
                            p.textContent = 'Loading your profile...';
                        }
                    });
                }
            } catch (_) {}
        }

        async function renderTempLandingLoggedInProfile(session) {
            try {
                try {
                    var _p = (window.location.pathname || '').replace(/\/+$/, '') || '/';
                    if (/^\/sailor\//i.test(_p) || /[?&]sas[_-]?id=/i.test(window.location.search || '')) {
                        window.__tempLandingProfileRenderInFlight = false;
                        return;
                    }
                } catch (_) {}
                if (window.__tempLandingProfileRenderInFlight) return;
                window.__tempLandingProfileRenderInFlight = true;
                var attempts = 0;
                while (attempts < 30) {
                    attempts += 1;
                    if (typeof window.showSailorStatsInResults === 'function') {
                        var user = session.user || {};
                        var sasId = session.sas_id || user.sas_id || '';
                        var displayName = [
                            user.first_name || user.first_names,
                            user.last_name || user.surname
                        ].filter(Boolean).join(' ') || user.full_name || '';
                        var club = user.primary_club || user.club || '';
                        if (sasId) {
                            await window.showSailorStatsInResults(sasId, displayName, club, [], {
                                isLoggedInUser: true,
                                session: session
                            });
                            sanitizeTempProfileShell(true);
                        }
                        return;
                    }
                    await new Promise(function(resolve) { window.setTimeout(resolve, 150); });
                }
            } catch (_) {
            } finally {
                window.__tempLandingProfileRenderInFlight = false;
            }
        }

        try {
            sanitizeTempProfileShell(false);
            var sanitizeTicks = 0;
            var sanitizeTimer = window.setInterval(function () {
                sanitizeTicks += 1;
                var isLoggedIn = !!(loggedInStatus && loggedInStatus.style.display !== 'none');
                sanitizeTempProfileShell(isLoggedIn);
                if (sanitizeTicks >= 40) {
                    window.clearInterval(sanitizeTimer);
                }
            }, 250);
            var root = document.getElementById('sailor-search-results');
            if (root && typeof MutationObserver !== 'undefined') {
                var observer = new MutationObserver(function () {
                    var isLoggedIn = !!(loggedInStatus && loggedInStatus.style.display !== 'none');
                    sanitizeTempProfileShell(isLoggedIn);
                });
                observer.observe(root, { childList: true, subtree: true });
            }
            var sailorBtn = document.querySelector('.search-mode-btn[data-mode="sailor"]');
            var regattaBtn = document.querySelector('.search-mode-btn[data-mode="regatta"]');
            if (sailorBtn) {
                sailorBtn.classList.add('active');
                sailorBtn.setAttribute('aria-pressed', 'true');
            }
            if (regattaBtn) {
                regattaBtn.classList.remove('active');
                regattaBtn.setAttribute('aria-pressed', 'false');
            }
            setupTempLandingSearchLayout();
            var signUpBanner = document.getElementById('temp-landing-claim-profile-banner');
            if (signUpBanner) {
                signUpBanner.setAttribute('role', 'link');
                signUpBanner.setAttribute('tabindex', '0');
                signUpBanner.setAttribute('aria-label', 'Open sign up');
                signUpBanner.addEventListener('click', function () {
                    window.location.href = tempSignupUrl();
                });
                signUpBanner.addEventListener('keydown', function (event) {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        window.location.href = tempSignupUrl();
                    }
                });
            }
        } catch (_) {}

        try {
            var session = (typeof checkSession === 'function')
                ? await checkSession()
                : await fetch('/auth/session?path=' + encodeURIComponent(tempPath), { credentials: 'include' }).then(function (r) { return r.json(); });
            if (session && session.valid) {
                sanitizeTempProfileShell(true);
                await renderTempLandingLoggedInProfile(session);
            }
        } catch (_) {
        }
    }
    initTempLanding();
});
