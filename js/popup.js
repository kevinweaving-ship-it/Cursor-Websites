// Popup State Management

let currentProfile = null;
let registrationRelationship = null;

/**
 * Initialize popup event listeners
 */
function initPopup() {
    // Close button
    const closeBtn = document.getElementById('popupClose');
    if (closeBtn) {
        closeBtn.addEventListener('click', hidePopup);
    }
    
    // Overlay click to close
    const overlay = document.getElementById('popupOverlay');
    if (overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                hidePopup();
            }
        });
    }
    
    // State 1: Login Choice buttons
    document.getElementById('btnGoogle')?.addEventListener('click', () => handleGoogleLogin());
    document.getElementById('btnFacebook')?.addEventListener('click', () => handleFacebookLogin());
    document.getElementById('btnEmail')?.addEventListener('click', () => handleEmailLogin());
    document.getElementById('btnUsernamePassword')?.addEventListener('click', () => showState('username-password'));
    document.getElementById('btnRegister')?.addEventListener('click', () => showState('find-profile'));
    
    // State 1b: Username/Password form
    const usernamePasswordForm = document.getElementById('usernamePasswordForm');
    if (usernamePasswordForm) {
        usernamePasswordForm.addEventListener('submit', handleUsernamePasswordLogin);
    }
    
    // State 2: Search profile form
    const searchForm = document.getElementById('searchProfileForm');
    if (searchForm) {
        searchForm.addEventListener('submit', handleProfileSearch);
    }
    
    // State 3: Profile confirmation buttons
    document.getElementById('btnThisIsMe')?.addEventListener('click', () => handleThisIsMe());
    document.getElementById('btnFamilyMember')?.addEventListener('click', () => showState('relationship'));
    document.getElementById('btnNotMe')?.addEventListener('click', () => showState('find-profile'));
    
    // State 4: Relationship form
    const relationshipForm = document.getElementById('relationshipForm');
    if (relationshipForm) {
        relationshipForm.addEventListener('submit', handleRelationshipSubmit);
    }
    
    // State 5: Verification buttons
    document.getElementById('btnVerifyEmail')?.addEventListener('click', () => handleEmailVerification());
    document.getElementById('btnVerifyGoogle')?.addEventListener('click', () => handleGoogleVerification());
    document.getElementById('btnVerifyFacebook')?.addEventListener('click', () => handleFacebookVerification());
}

/**
 * Handle profile search
 */
async function handleProfileSearch(e) {
    e.preventDefault();
    const query = document.getElementById('searchInput').value;
    
    if (!query) return;
    
    showState('loading');
    
    try {
        const results = await searchProfiles(query);
        
        if (results.length === 0) {
            document.getElementById('searchResults').innerHTML = '<p>No profiles found. Please try again.</p>';
            showState('find-profile');
        } else if (results.length === 1) {
            // Auto-select if only one result
            currentProfile = results[0];
            showProfileConfirmation(currentProfile);
        } else {
            // Show selection list
            displayProfileResults(results);
        }
    } catch (error) {
        console.error('Profile search failed:', error);
        document.getElementById('searchResults').innerHTML = '<p>Error searching profiles. Please try again.</p>';
        showState('find-profile');
    }
}

/**
 * Display profile search results
 */
function displayProfileResults(results) {
    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.innerHTML = '<h3>Select your profile:</h3>';
    
    results.forEach(profile => {
        const div = document.createElement('div');
        div.className = 'profile-result';
        div.innerHTML = `
            <p><strong>${profile.firstName} ${profile.surname}</strong></p>
            <p>SAS ID: ${profile.sas_id}</p>
            <p>Class: ${profile.class || 'N/A'}</p>
            <button class="btn-primary" onclick="selectProfile(${profile.sas_id})">Select</button>
        `;
        resultsDiv.appendChild(div);
    });
    
    showState('find-profile');
}

/**
 * Select profile from search results
 */
function selectProfile(sasId) {
    // Find profile in results
    // This would need to be stored from search results
    // For now, re-search with SAS ID
    handleProfileSearch({ preventDefault: () => {} });
    document.getElementById('searchInput').value = sasId;
}

/**
 * Show profile confirmation (State 3)
 */
function showProfileConfirmation(profile) {
    currentProfile = profile;
    
    const detailsDiv = document.getElementById('profileDetails');
    detailsDiv.innerHTML = `
        <div class="profile-info">
            <h3>${profile.firstName} ${profile.surname}</h3>
            <p><strong>SAS ID:</strong> ${profile.sas_id}</p>
            <p><strong>Class:</strong> ${profile.class || 'N/A'}</p>
            ${profile.age ? `<p><strong>Age:</strong> ${profile.age}</p>` : ''}
        </div>
    `;
    
    showState('confirm-profile');
}

/**
 * Handle "This is me" button
 */
function handleThisIsMe() {
    registrationRelationship = 'self';
    showState('verification');
}

/**
 * Handle relationship form submit
 */
function handleRelationshipSubmit(e) {
    e.preventDefault();
    const relationship = document.getElementById('relationshipSelect').value;
    const consent = document.getElementById('consentCheckbox').checked;
    
    if (!consent) {
        alert('You must provide consent to manage this profile');
        return;
    }
    
    registrationRelationship = relationship;
    showState('verification');
}

/**
 * Handle Google login
 */
async function handleGoogleLogin() {
    // Implement Google OAuth
    console.log('Google login - to be implemented');
}

/**
 * Handle Facebook login
 */
async function handleFacebookLogin() {
    // Implement Facebook OAuth (13+ only)
    console.log('Facebook login - to be implemented');
}

/**
 * Handle Email login
 */
function handleEmailLogin() {
    showState('find-profile');
}

/**
 * Handle Username/Password login
 */
async function handleUsernamePasswordLogin(e) {
    e.preventDefault();
    const username = document.getElementById('usernameInput').value;
    const password = document.getElementById('passwordInput').value;
    
    if (!username || !password) {
        alert('Please enter both SAS ID and password');
        return;
    }
    
    showState('loading');
    
    try {
        const result = await loginWithUsernamePassword(username, password);
        
        if (result.success) {
            // Store session
            storeSession(result.session);
            
            // Redirect to landing page
            redirectToLandingPage();
        } else {
            alert('Login failed: ' + (result.error || 'Invalid credentials'));
            showState('username-password');
        }
    } catch (error) {
        console.error('Username/password login failed:', error);
        alert('Login failed. Please try again.');
        showState('username-password');
    }
}

/**
 * Handle Email verification
 */
function handleEmailVerification() {
    // Implement email verification flow
    console.log('Email verification - to be implemented');
}

/**
 * Handle Google verification
 */
function handleGoogleVerification() {
    // Implement Google OAuth for registration
    console.log('Google verification - to be implemented');
}

/**
 * Handle Facebook verification
 */
function handleFacebookVerification() {
    // Implement Facebook OAuth for registration (13+ only)
    console.log('Facebook verification - to be implemented');
}

// Initialize popup - make sure it's available globally
function showPopup() {
    const popup = document.getElementById('popupOverlay');
    if (popup) {
        popup.style.display = 'flex';
        showState('login-choice');
    }
}

function hidePopup() {
    const popup = document.getElementById('popupOverlay');
    if (popup) {
        popup.style.display = 'none';
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPopup);
} else {
    initPopup();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initPopup,
        handleProfileSearch,
        showProfileConfirmation,
        handleThisIsMe,
        handleUsernamePasswordLogin,
        currentProfile,
        registrationRelationship,
        showPopup,
        hidePopup
    };
}

// Make functions globally available
window.showPopup = showPopup;
window.hidePopup = hidePopup;
window.showState = showState;
