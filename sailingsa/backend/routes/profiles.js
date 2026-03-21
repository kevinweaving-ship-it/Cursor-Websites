// Profile Routes

const express = require('express');
const router = express.Router();

/**
 * POST /profiles/search
 * Search for profiles by SAS ID or Name & Surname
 */
router.post('/search', (req, res) => {
    const { query } = req.body;
    
    if (!query) {
        return res.status(400).json({ error: 'Query required' });
    }
    
    // TODO: Implement profile search
    // Search database for matching profiles
    // Return array of matching profiles
    // Exact name matches for privacy
    
    // Mock response for development
    res.json([]);
});

/**
 * POST /profiles/claim
 * Claim/link profile to user account
 */
router.post('/claim', (req, res) => {
    const { sas_id, relationship, ...profileData } = req.body;
    
    // TODO: Implement profile claiming
    // Validate profile exists
    // Link to user account
    // Store relationship if applicable
    // Return success
    
    res.json({ success: false, error: 'Not implemented' });
});

module.exports = router;
