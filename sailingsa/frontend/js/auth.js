// Authentication Handlers

/**
 * Handle authentication after verification
 */
async function handleAuthComplete(provider, providerData) {
    if (!currentProfile) {
        console.error('No profile selected');
        return;
    }
    
    try {
        // Register or login with provider
        const result = await registerWithProvider(provider, providerData, {
            ...currentProfile,
            relationship: registrationRelationship || 'self'
        });
        
        if (result.success) {
            // Store session
            storeSession(result.session);
            
            // Redirect to landing page (not profile)
            redirectToLandingPage();
        } else {
            alert('Registration failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Auth complete failed:', error);
        alert('Authentication failed. Please try again.');
    }
}

/**
 * Check if user is 13+ (for Facebook)
 */
function isUser13Plus(dateOfBirth) {
    if (!dateOfBirth) return false;
    
    const dob = new Date(dateOfBirth);
    const today = new Date();
    const age = today.getFullYear() - dob.getFullYear();
    const monthDiff = today.getMonth() - dob.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
        return age - 1 >= 13;
    }
    
    return age >= 13;
}

/**
 * Enable/disable Facebook button based on age
 */
function updateFacebookButtonVisibility(profile) {
    const fbBtn = document.getElementById('btnFacebook');
    const fbVerifyBtn = document.getElementById('btnVerifyFacebook');
    
    if (!profile || !profile.dateOfBirth) {
        // Hide if no DOB available
        if (fbBtn) fbBtn.style.display = 'none';
        if (fbVerifyBtn) fbVerifyBtn.style.display = 'none';
        return;
    }
    
    const is13Plus = isUser13Plus(profile.dateOfBirth);
    
    if (fbBtn) {
        fbBtn.style.display = is13Plus ? 'block' : 'none';
        if (!is13Plus) {
            fbBtn.disabled = true;
            fbBtn.title = 'Facebook requires age 13+';
        }
    }
    
    if (fbVerifyBtn) {
        fbVerifyBtn.style.display = is13Plus ? 'block' : 'none';
        if (!is13Plus) {
            fbVerifyBtn.disabled = true;
            fbVerifyBtn.title = 'Facebook requires age 13+';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        handleAuthComplete,
        isUser13Plus,
        updateFacebookButtonVisibility
    };
}
