// Session Management

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
    
    // Clear cookies
    document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
    document.cookie = 'session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
    
    console.log('[DEBUG] clearSession: All session data cleared');
}

/**
 * Redirect to landing page after successful login/registration
 */
function redirectToLandingPage() {
    // Redirect to landing page (index.html) - same page, just refresh
    window.location.href = window.location.origin + window.location.pathname;
}

/**
 * Update header auth status (login box or user name + logout)
 */
async function updateHeaderAuthStatus() {
    console.log('[DEBUG] updateHeaderAuthStatus: Called');
    try {
        const session = await checkSession();
        console.log('[DEBUG] updateHeaderAuthStatus: Session data:', session);
        
        if (session.valid) {
            // Show logged in status
            const loggedInDiv = document.getElementById('loggedInStatus');
            const loginBoxDiv = document.getElementById('loginBox');
            const userNameDisplay = document.getElementById('userNameDisplay');
            
            console.log('[DEBUG] updateHeaderAuthStatus: Elements found:', {
                loggedInDiv: !!loggedInDiv,
                loginBoxDiv: !!loginBoxDiv,
                userNameDisplay: !!userNameDisplay
            });
            
            if (loggedInDiv && loginBoxDiv && userNameDisplay) {
                // Get user info from session
                const user = session.user || {};
                const fullName = user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim();
                const displayName = fullName || 'User';
                const sasId = session.sas_id || '';
                
                console.log('[DEBUG] updateHeaderAuthStatus: User data:', {
                    fullName,
                    displayName,
                    sasId,
                    user
                });
                
                // Display name only (white) - Welcome removed
                userNameDisplay.innerHTML = `<span class="user-name-value">${displayName}</span>`;
                
                // Display SAS ID if available
                const sasIdDisplay = document.getElementById('userSasIdDisplay');
                if (sasIdDisplay) {
                    if (sasId) {
                        sasIdDisplay.innerHTML = `SAS ID: <span class="sas-id-value">${sasId}</span>`;
                    } else {
                        sasIdDisplay.textContent = '';
                    }
                }
                
                loggedInDiv.style.display = 'flex';
                loginBoxDiv.style.display = 'none';
                console.log('[DEBUG] updateHeaderAuthStatus: Logged in status displayed');
            }
            
            // Update auth button to "Logout" (same button, different text/function)
            // Remove any existing buttons with old IDs first
            const oldLogoutBtn = document.getElementById('logoutBtn');
            const oldLoginBtn = document.getElementById('loginBtn');
            if (oldLogoutBtn) {
                oldLogoutBtn.remove();
            }
            if (oldLoginBtn) {
                oldLoginBtn.remove();
            }
            
            let authBtn = document.getElementById('authBtn');
            if (!authBtn) {
                // Create button if it doesn't exist
                authBtn = document.createElement('button');
                authBtn.id = 'authBtn';
            }
            
            // Update button properties for logged in state
            authBtn.textContent = 'Logout';
            authBtn.className = 'btn-logout';
            
            // Move button to loggedInStatus if not already there
            const loggedInDivForBtn = document.getElementById('loggedInStatus');
            if (loggedInDivForBtn) {
                // Remove button from any other parent first
                if (authBtn.parentNode && authBtn.parentNode !== loggedInDivForBtn) {
                    authBtn.parentNode.removeChild(authBtn);
                }
                // Add to loggedInStatus if not already there
                if (!loggedInDivForBtn.contains(authBtn)) {
                    loggedInDivForBtn.appendChild(authBtn);
                }
            }
            
            // Remove any existing listeners and add logout listener
            const newAuthBtn = authBtn.cloneNode(true);
            if (authBtn.parentNode) {
                authBtn.parentNode.replaceChild(newAuthBtn, authBtn);
            }
            newAuthBtn.addEventListener('click', async function(e) {
                e.preventDefault();
                console.log('[DEBUG] Auth button clicked (Logout)');
                if (typeof handleLogout === 'function') {
                    await handleLogout();
                }
            });
            
            // "Your Sailing Results" button removed - no longer needed
            
            // Trigger page content update if function exists
            if (typeof updatePageContent === 'function') {
                updatePageContent();
            }
        } else {
            console.log('[DEBUG] updateHeaderAuthStatus: No valid session, showing login box');
            // Show login box or "Your Sailing Results" button
            const loggedInDiv = document.getElementById('loggedInStatus');
            const loginBoxDiv = document.getElementById('loginBox');
            const userNameDisplay = document.getElementById('userNameDisplay');
            const userSasIdDisplay = document.getElementById('userSasIdDisplay');
            
            // Hide logged in status and clear user info
            if (loggedInDiv) {
                loggedInDiv.style.display = 'none';
            }
            
            // Clear Name and SAS ID when logged out
            if (userNameDisplay) {
                userNameDisplay.textContent = '';
                userNameDisplay.innerHTML = '';
            }
            
            if (userSasIdDisplay) {
                userSasIdDisplay.textContent = '';
                userSasIdDisplay.innerHTML = '';
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
            
            let authBtn = document.getElementById('authBtn');
            if (!authBtn) {
                // Create button if it doesn't exist
                authBtn = document.createElement('button');
                authBtn.id = 'authBtn';
            }
            
            // Update button properties for logged out state
            // Use both textContent AND innerHTML to ensure it sticks
            authBtn.textContent = 'Sign In / Sign Up';
            authBtn.innerHTML = 'Sign In / Sign Up';
            authBtn.className = 'btn-primary';
            // Set as attribute too
            authBtn.setAttribute('data-button-text', 'Sign In / Sign Up');
            console.log('[DEBUG] updateHeaderAuthStatus: Set button text to:', authBtn.textContent);
            console.log('[DEBUG] updateHeaderAuthStatus: Button element:', authBtn);
            
            // Move button to loginBox if not already there
            if (loginBoxDiv) {
                // Remove button from any other parent first
                if (authBtn.parentNode && authBtn.parentNode !== loginBoxDiv) {
                    authBtn.parentNode.removeChild(authBtn);
                }
                // Add to loginBox if not already there
                if (!loginBoxDiv.contains(authBtn)) {
                    loginBoxDiv.appendChild(authBtn);
                }
            }
            
            // Remove any existing listeners and add sign in listener
            const newAuthBtn = authBtn.cloneNode(true);
            // Ensure text is set after clone - use multiple methods
            newAuthBtn.textContent = 'Sign In / Sign Up';
            newAuthBtn.innerHTML = 'Sign In / Sign Up';
            newAuthBtn.setAttribute('data-button-text', 'Sign In / Sign Up');
            if (authBtn.parentNode) {
                authBtn.parentNode.replaceChild(newAuthBtn, authBtn);
            }
            // Double-check text after replacement - use setTimeout to ensure DOM is updated
            setTimeout(function() {
                const finalBtn = document.getElementById('authBtn');
                if (finalBtn) {
                    if (finalBtn.textContent !== 'Sign In / Sign Up') {
                        finalBtn.textContent = 'Sign In / Sign Up';
                        finalBtn.innerHTML = 'Sign In / Sign Up';
                        console.log('[DEBUG] updateHeaderAuthStatus: Fixed button text after replacement:', finalBtn.textContent);
                    } else {
                        console.log('[DEBUG] updateHeaderAuthStatus: Final button text correct:', finalBtn.textContent);
                    }
                }
            }, 50);
            newAuthBtn.addEventListener('click', async function(e) {
                e.preventDefault();
                console.log('[DEBUG] Auth button clicked (Sign In)');
                
                // Check if there's a valid session on this device
                try {
                    const session = await checkSession();
                    console.log('[DEBUG] Sign In: Session check result:', session);
                    
                    if (session && session.valid) {
                        // Auto sign in - valid session found on this device
                        console.log('[DEBUG] Sign In: Valid session found, auto-signing in');
                        // Update header and page content
                        await updateHeaderAuthStatus();
                        if (typeof updatePageContent === 'function') {
                            await updatePageContent();
                        }
                        // Refresh to show signed-in view
                        window.location.reload();
                    } else {
                        // Check for stored credentials (WhatsApp/SAS ID + Password)
                        const rememberCredentials = localStorage.getItem('remember_credentials');
                        if (rememberCredentials === 'true') {
                            const savedUsername = localStorage.getItem('saved_username');
                            const savedPassword = localStorage.getItem('saved_password');
                            
                            if (savedUsername && savedPassword) {
                                console.log('[DEBUG] Sign In: Stored credentials found, attempting auto-login');
                                try {
                                    // Try auto-login with stored credentials
                                    const loginResult = await loginWithUsernamePassword(savedUsername, savedPassword);
                                    if (loginResult && loginResult.success) {
                                        console.log('[DEBUG] Sign In: Auto-login successful');
                                        // Store session
                                        document.cookie = `session=${loginResult.session || loginResult.session_token}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;
                                        localStorage.setItem('session', loginResult.session || loginResult.session_token);
                                        // Update header and reload
                                        await updateHeaderAuthStatus();
                                        if (typeof updatePageContent === 'function') {
                                            await updatePageContent();
                                        }
                                        window.location.reload();
                                        return;
                                    }
                                } catch (loginError) {
                                    console.error('[DEBUG] Sign In: Auto-login failed:', loginError);
                                }
                            }
                        }
                        
                        // No valid session or auto-login failed - redirect to login page
                        try { sessionStorage.setItem('auth_returnTo', window.location.href); } catch (err) {}
                        const loginUrl = `http://192.168.0.130:8081/sailingsa/frontend/login.html`;
                        console.log('[DEBUG] Sign In: No valid session, redirecting to:', loginUrl);
                        window.location.href = loginUrl;
                    }
                } catch (error) {
                    console.error('[DEBUG] Sign In: Error checking session:', error);
                    // On error, redirect to login page
                    try { sessionStorage.setItem('auth_returnTo', window.location.href); } catch (err) {}
                    const loginUrl = `http://192.168.0.130:8081/sailingsa/frontend/login.html`;
                    window.location.href = loginUrl;
                }
            });
            
            // "Your Sailing Results" button removed - no longer needed
            
            // Trigger page content update if function exists
            if (typeof updatePageContent === 'function') {
                updatePageContent();
            }
        }
    } catch (error) {
        console.error('[DEBUG] updateHeaderAuthStatus: Error:', error);
        console.error('[DEBUG] updateHeaderAuthStatus: Stack trace:', error.stack);
        // Show login box on error
        const loggedInDiv = document.getElementById('loggedInStatus');
        const loginBoxDiv = document.getElementById('loginBox');
        const userNameDisplay = document.getElementById('userNameDisplay');
        const userSasIdDisplay = document.getElementById('userSasIdDisplay');
        
        // Hide logged in status and clear user info
        if (loggedInDiv) {
            loggedInDiv.style.display = 'none';
        }
        
        // Clear Name and SAS ID when logged out (error state)
        if (userNameDisplay) {
            userNameDisplay.textContent = '';
            userNameDisplay.innerHTML = '';
        }
        
        if (userSasIdDisplay) {
            userSasIdDisplay.textContent = '';
            userSasIdDisplay.innerHTML = '';
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
        
        let authBtn = document.getElementById('authBtn');
        if (!authBtn) {
            // Create button if it doesn't exist
            authBtn = document.createElement('button');
            authBtn.id = 'authBtn';
        }
        
        // Update button properties for logged out state
        // Use both textContent AND innerHTML to ensure it sticks
        authBtn.textContent = 'Sign In / Sign Up';
        authBtn.innerHTML = 'Sign In / Sign Up';
        authBtn.className = 'btn-primary';
        // Set as attribute too
        authBtn.setAttribute('data-button-text', 'Sign In / Sign Up');
        console.log('[DEBUG] updateHeaderAuthStatus (error): Set button text to:', authBtn.textContent);
        console.log('[DEBUG] updateHeaderAuthStatus (error): Button element:', authBtn);
        
        // Move button to loginBox if not already there
        if (loginBoxDiv) {
            // Remove button from any other parent first
            if (authBtn.parentNode && authBtn.parentNode !== loginBoxDiv) {
                authBtn.parentNode.removeChild(authBtn);
            }
            // Add to loginBox if not already there
            if (!loginBoxDiv.contains(authBtn)) {
                loginBoxDiv.appendChild(authBtn);
            }
        }
        
        // Remove any existing listeners and add sign in listener
        const newAuthBtn = authBtn.cloneNode(true);
        // Ensure text is set after clone - use multiple methods
        newAuthBtn.textContent = 'Sign In / Sign Up';
        newAuthBtn.innerHTML = 'Sign In / Sign Up';
        newAuthBtn.setAttribute('data-button-text', 'Sign In / Sign Up');
        if (authBtn.parentNode) {
            authBtn.parentNode.replaceChild(newAuthBtn, authBtn);
        }
        // Double-check text after replacement - use setTimeout to ensure DOM is updated
        setTimeout(function() {
            const finalBtn = document.getElementById('authBtn');
            if (finalBtn) {
                if (finalBtn.textContent !== 'Sign In / Sign Up') {
                    finalBtn.textContent = 'Sign In / Sign Up';
                    finalBtn.innerHTML = 'Sign In / Sign Up';
                    console.log('[DEBUG] updateHeaderAuthStatus (error): Fixed button text after replacement:', finalBtn.textContent);
                } else {
                    console.log('[DEBUG] updateHeaderAuthStatus (error): Final button text correct:', finalBtn.textContent);
                }
            }
        }, 50);
        newAuthBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('[DEBUG] Auth button clicked (Sign In - error state)');
            
            // Check if there's a valid session on this device
            try {
                const session = await checkSession();
                console.log('[DEBUG] Sign In (error state): Session check result:', session);
                
                if (session && session.valid) {
                    // Auto sign in - valid session found on this device
                    console.log('[DEBUG] Sign In (error state): Valid session found, auto-signing in');
                    // Update header and page content
                    await updateHeaderAuthStatus();
                    if (typeof updatePageContent === 'function') {
                        await updatePageContent();
                    }
                    // Refresh to show signed-in view
                    window.location.reload();
                } else {
                    // Check for stored credentials (WhatsApp/SAS ID + Password)
                    const rememberCredentials = localStorage.getItem('remember_credentials');
                    if (rememberCredentials === 'true') {
                        const savedUsername = localStorage.getItem('saved_username');
                        const savedPassword = localStorage.getItem('saved_password');
                        
                        if (savedUsername && savedPassword && typeof loginWithUsernamePassword === 'function') {
                            console.log('[DEBUG] Sign In (error state): Stored credentials found, attempting auto-login');
                            try {
                                // Try auto-login with stored credentials
                                const loginResult = await loginWithUsernamePassword(savedUsername, savedPassword);
                                if (loginResult && loginResult.success) {
                                    console.log('[DEBUG] Sign In (error state): Auto-login successful');
                                    // Store session
                                    document.cookie = `session=${loginResult.session || loginResult.session_token}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;
                                    localStorage.setItem('session', loginResult.session || loginResult.session_token);
                                    // Update header and reload
                                    await updateHeaderAuthStatus();
                                    if (typeof updatePageContent === 'function') {
                                        await updatePageContent();
                                    }
                                    window.location.reload();
                                    return;
                                }
                            } catch (loginError) {
                                console.error('[DEBUG] Sign In (error state): Auto-login failed:', loginError);
                            }
                        }
                    }
                    
                    // No valid session or auto-login failed - redirect to login page
                    try { sessionStorage.setItem('auth_returnTo', window.location.href); } catch (err) {}
                    const loginUrl = `http://192.168.0.130:8081/sailingsa/frontend/login.html`;
                    console.log('[DEBUG] Sign In (error state): No valid session, redirecting to:', loginUrl);
                    window.location.href = loginUrl;
                }
            } catch (error) {
                console.error('[DEBUG] Sign In (error state): Error checking session:', error);
                // On error, redirect to login page
                try { sessionStorage.setItem('auth_returnTo', window.location.href); } catch (err) {}
                const loginUrl = `http://192.168.0.130:8081/sailingsa/frontend/login.html`;
                window.location.href = loginUrl;
            }
        });
        
        // "Your Sailing Results" button removed - no longer needed
    }
}

/**
 * Show auto-login confirmation popup
 */
function showAutoLoginPopup() {
    return new Promise((resolve) => {
        // Create popup overlay
        const overlay = document.createElement('div');
        overlay.id = 'autoLoginPopupOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        // Create popup container
        const popup = document.createElement('div');
        popup.style.cssText = `
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            min-width: 200px;
            max-width: 300px;
            text-align: center;
        `;
        
        // Title
        const title = document.createElement('div');
        title.textContent = 'Auto Sign In';
        title.style.cssText = `
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #1a365d;
        `;
        
        // Buttons container
        const buttonsDiv = document.createElement('div');
        buttonsDiv.style.cssText = `
            display: flex;
            gap: 0.75rem;
            justify-content: center;
        `;
        
        // Yes button
        const yesBtn = document.createElement('button');
        yesBtn.textContent = 'Yes';
        yesBtn.style.cssText = `
            padding: 0.5rem 1.5rem;
            background: #1a365d;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        `;
        yesBtn.onmouseover = () => yesBtn.style.background = '#2c5282';
        yesBtn.onmouseout = () => yesBtn.style.background = '#1a365d';
        yesBtn.onclick = () => {
            document.body.removeChild(overlay);
            resolve(true);
        };
        
        // No button
        const noBtn = document.createElement('button');
        noBtn.textContent = 'No';
        noBtn.style.cssText = `
            padding: 0.5rem 1.5rem;
            background: #e2e8f0;
            color: #1a365d;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        `;
        noBtn.onmouseover = () => noBtn.style.background = '#cbd5e0';
        noBtn.onmouseout = () => noBtn.style.background = '#e2e8f0';
        noBtn.onclick = () => {
            document.body.removeChild(overlay);
            resolve(false);
        };
        
        // Close on overlay click (outside popup)
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                resolve(false);
            }
        };
        
        // Assemble popup
        buttonsDiv.appendChild(yesBtn);
        buttonsDiv.appendChild(noBtn);
        popup.appendChild(title);
        popup.appendChild(buttonsDiv);
        overlay.appendChild(popup);
        
        // Add to page
        document.body.appendChild(overlay);
    });
}

// Make function globally available
window.showAutoLoginPopup = showAutoLoginPopup;

/**
 * Handle logout
 */
async function handleLogout() {
    console.log('[DEBUG] handleLogout: Called');
    
    // Show styled popup asking about auto-login
    const enableAutoLogin = await showAutoLoginPopup();
    
    try {
        // Clear user info display immediately
        const userNameDisplay = document.getElementById('userNameDisplay');
        const userSasIdDisplay = document.getElementById('userSasIdDisplay');
        const loggedInDiv = document.getElementById('loggedInStatus');
        
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
        }
        
        // Call logout endpoint to end session on server
        try {
            const response = await fetch(`${API_BASE}/auth/logout`, {
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
            localStorage.removeItem('saved_username');
            localStorage.removeItem('saved_password');
            localStorage.removeItem('remember_credentials');
            
            // Redirect to public page (index.html), not login.html
            const indexUrl = `${window.location.protocol}//${window.location.host}/sailingsa/frontend/index.html`;
            console.log('[DEBUG] handleLogout: Redirecting to public page (no auto-login):', indexUrl);
            window.location.href = indexUrl;
        } else {
            // User chose to enable auto-login - keep credentials stored
            console.log('[DEBUG] handleLogout: User chose to enable auto-login, keeping credentials');
            
            // Redirect to public index page
            const indexUrl = `${window.location.protocol}//${window.location.host}/sailingsa/frontend/index.html`;
            console.log('[DEBUG] handleLogout: Redirecting to public page:', indexUrl);
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
        }
        
        // Redirect to public page (index.html) on error, not login.html
        const indexUrl = `${window.location.protocol}//${window.location.host}/sailingsa/frontend/index.html`;
        console.log('[DEBUG] handleLogout: Redirecting to public page (error):', indexUrl);
        window.location.href = indexUrl;
    }
}

// Ensure button text persists - monitor and fix if changed
(function ensureButtonText() {
    function fixButtonText() {
        const authBtn = document.getElementById('authBtn');
        if (authBtn) {
            const loginBox = document.getElementById('loginBox');
            const loggedInStatus = document.getElementById('loggedInStatus');
            
            // Check if user should be logged out (loginBox visible, loggedInStatus hidden)
            const shouldBeLoggedOut = loginBox && loginBox.style.display !== 'none' && 
                                     (!loggedInStatus || loggedInStatus.style.display === 'none');
            
            if (shouldBeLoggedOut) {
                // User is logged out, should show "Sign In / Sign Up"
                const currentText = authBtn.textContent.trim();
                if (currentText === 'Sign In' || currentText !== 'Sign In / Sign Up') {
                    authBtn.textContent = 'Sign In / Sign Up';
                    authBtn.innerHTML = 'Sign In / Sign Up';
                    authBtn.setAttribute('data-button-text', 'Sign In / Sign Up');
                    console.log('[DEBUG] ensureButtonText: Fixed button text from "' + currentText + '" to "Sign In / Sign Up"');
                }
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

// Make functions globally available
window.showState = showState;
window.showPopup = showPopup;
window.hidePopup = hidePopup;
window.handleLogout = handleLogout;
window.showAutoLoginPopup = showAutoLoginPopup;

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
