// Authentication Routes

const express = require('express');
const router = express.Router();
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const crypto = require('crypto');
const fs = require('fs');

// Database connection
const dbDir = path.join(__dirname, '../db');
if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
}
const dbPath = path.join(dbDir, 'sailing.db');
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Error opening database:', err);
    } else {
        console.log('Connected to SQLite database');
        // Initialize schema if needed
        initializeSchema();
    }
});

function initializeSchema() {
    const schemaPath = path.join(__dirname, '../db/schema.sql');
    if (fs.existsSync(schemaPath)) {
        const schema = fs.readFileSync(schemaPath, 'utf8');
        db.exec(schema, (err) => {
            if (err) {
                console.error('Error initializing schema:', err);
            } else {
                console.log('Database schema initialized');
            }
        });
    }
}

// Configure Google OAuth Strategy
// All values MUST come from environment variables (no hardcoded fallbacks)
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const GOOGLE_CALLBACK_URL = process.env.GOOGLE_CALLBACK_URL;

// Check if Google OAuth is properly configured (not just placeholders)
const hasValidGoogleConfig = GOOGLE_CLIENT_ID && 
                              GOOGLE_CLIENT_SECRET && 
                              GOOGLE_CALLBACK_URL &&
                              !GOOGLE_CLIENT_ID.includes('your-google-client-id') &&
                              !GOOGLE_CLIENT_SECRET.includes('your-google-client-secret') &&
                              GOOGLE_CLIENT_ID.includes('.apps.googleusercontent.com');

if (hasValidGoogleConfig) {
    passport.use(new GoogleStrategy({
        clientID: GOOGLE_CLIENT_ID,
        clientSecret: GOOGLE_CLIENT_SECRET,
        callbackURL: GOOGLE_CALLBACK_URL
    }, async (accessToken, refreshToken, profile, done) => {
        try {
            // Find or create user
            db.get(
                `SELECT u.*, up.sas_id 
                 FROM users u 
                 LEFT JOIN user_profiles up ON u.id = up.user_id AND up.is_active = 1
                 WHERE u.google_id = ? OR u.email = ?`,
                [profile.id, profile.emails[0].value],
                async (err, user) => {
                    if (err) {
                        return done(err, null);
                    }
                    
                    if (user) {
                        // Update last login
                        db.run(`UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?`, [user.id]);
                        return done(null, user);
                    }
                    
                    // User doesn't exist - return profile for registration
                    return done(null, {
                        needsRegistration: true,
                        google_id: profile.id,
                        email: profile.emails[0].value,
                        name: profile.displayName,
                        picture: profile.photos[0]?.value || null,
                        first_name: profile.name?.givenName || '',
                        last_name: profile.name?.familyName || ''
                    });
                }
            );
        } catch (error) {
            return done(error, null);
        }
    }));
    
    // Serialize user for session
    passport.serializeUser((user, done) => {
        done(null, user.id || user.google_id);
    });
    
    passport.deserializeUser((id, done) => {
        db.get('SELECT * FROM users WHERE id = ? OR google_id = ?', [id, id], (err, user) => {
            done(err, user);
        });
    });
    
    console.log('Google OAuth configured');
    console.log(`Callback URL: ${GOOGLE_CALLBACK_URL}`);
} else {
    console.warn('⚠️  Google OAuth not configured - set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_CALLBACK_URL in environment variables');
    console.warn('   Local: Use .env.local file');
    console.warn('   Live: Set server environment variables');
    if (GOOGLE_CLIENT_ID && GOOGLE_CLIENT_ID.includes('your-google-client-id')) {
        console.warn('   ⚠️  Detected placeholder values in GOOGLE_CLIENT_ID - replace with actual credentials from Google Cloud Console');
    }
}

/**
 * GET /auth/google
 * Initiate Google OAuth flow
 */
router.get('/google', (req, res, next) => {
    const hasValidGoogleConfig = GOOGLE_CLIENT_ID && 
                                  GOOGLE_CLIENT_SECRET && 
                                  GOOGLE_CALLBACK_URL &&
                                  !GOOGLE_CLIENT_ID.includes('your-google-client-id') &&
                                  !GOOGLE_CLIENT_SECRET.includes('your-google-client-secret') &&
                                  GOOGLE_CLIENT_ID.includes('.apps.googleusercontent.com');
    
    if (!hasValidGoogleConfig) {
        return res.status(500).json({ 
            success: false, 
            error: 'Google OAuth not configured. Please set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_CALLBACK_URL in environment variables.' 
        });
    }
    
    // Real Google OAuth flow - works the same locally and in production
    passport.authenticate('google', {
        scope: ['profile', 'email']
    })(req, res, next);
});

/**
 * GET /auth/google/callback
 * Handle Google OAuth callback
 */
router.get('/google/callback', 
    passport.authenticate('google', { session: false }),
    (req, res) => {
        const user = req.user;
        
        // Frontend URL for redirects - MUST be set in environment
        const frontendUrl = process.env.FRONTEND_URL;
        
        if (!frontendUrl) {
            console.error('FRONTEND_URL not set in environment variables');
            return res.status(500).json({ 
                success: false, 
                error: 'Server configuration error: FRONTEND_URL not set' 
            });
        }
        
        // Determine if user needs account completion (registration)
        // DO NOT create accounts here - just verify and return status
        if (user.needsRegistration) {
            // User doesn't exist - needs account completion
            // Return to frontend with Google profile data for registration flow
            return res.redirect(`${frontendUrl}/timadvisor/login.html?status=NEEDS_ACCOUNT_COMPLETION&google_data=${encodeURIComponent(JSON.stringify({
                provider: 'google',
                google_id: user.google_id,
                email: user.email,
                name: user.name,
                picture: user.picture,
                first_name: user.first_name,
                last_name: user.last_name
            }))}`);
        }
        
        // User exists - LOGIN_OK
        // Create session for existing user
        const sessionToken = crypto.randomBytes(32).toString('hex');
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + 30); // 30 days
        
        db.run(
            `INSERT INTO sessions (user_id, session_token, expires_at) 
             VALUES (?, ?, ?)`,
            [user.id, sessionToken, expiresAt.toISOString()],
            function(err) {
                if (err) {
                    console.error('Session creation error:', err);
                    return res.redirect(`${frontendUrl}/timadvisor/login.html?status=ERROR&error=session_failed`);
                }
                
                // Set session cookie
                // Secure flag: true in production (HTTPS), false in local dev
                const isSecure = process.env.NODE_ENV === 'production' || frontendUrl.startsWith('https://');
                res.cookie('sailing_session', sessionToken, {
                    httpOnly: true,
                    secure: isSecure,
                    maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
                    sameSite: 'lax'
                });
                
                // Redirect to frontend with success status
                res.redirect(`${frontendUrl}/timadvisor/login.html?status=LOGIN_OK&token=${sessionToken}`);
            }
        );
    }
);

/**
 * GET /auth/session
 * Check if user has valid session
 */
router.get('/session', (req, res) => {
    const sessionToken = req.cookies.sailing_session || req.query.token;
    
    if (!sessionToken) {
        return res.json({ valid: false });
    }
    
    db.get(
        `SELECT s.*, u.email, u.google_id, up.sas_id 
         FROM sessions s
         JOIN users u ON s.user_id = u.id
         LEFT JOIN user_profiles up ON u.id = up.user_id AND up.is_active = 1
         WHERE s.session_token = ? AND s.expires_at > datetime('now')`,
        [sessionToken],
        (err, session) => {
            if (err) {
                console.error('Session check error:', err);
                return res.json({ valid: false });
            }
            
            if (session) {
                res.json({
                    valid: true,
                    user: {
                        id: session.user_id,
                        email: session.email,
                        sas_id: session.sas_id
                    }
                });
            } else {
                res.json({ valid: false });
            }
        }
    );
});

/**
 * POST /auth/login
 * Login with provider (Google, Facebook, Email) or username/password
 */
router.post('/login', (req, res) => {
    const { provider, username, password, email, google_id, name, picture, credential, access_token } = req.body;
    
    if (provider === 'google') {
        // Google login flow
        if (!email && !google_id) {
            return res.json({ success: false, error: 'Missing Google authentication data' });
        }
        
        // Look up user by Google ID or email
        db.get(
            `SELECT u.*, up.sas_id 
             FROM users u 
             LEFT JOIN user_profiles up ON u.id = up.user_id AND up.is_active = 1
             WHERE u.google_id = ? OR u.email = ?`,
            [google_id || '', email || ''],
            (err, user) => {
                if (err) {
                    console.error('Database error:', err);
                    return res.json({ success: false, error: 'Database error' });
                }
                
                if (!user) {
                    // User doesn't exist - need to register
                    return res.json({ 
                        success: false, 
                        error: 'Account not found. Please register first.',
                        needsRegistration: true
                    });
                }
                
                // User exists - create session
                const sessionToken = crypto.randomBytes(32).toString('hex');
                const expiresAt = new Date();
                expiresAt.setDate(expiresAt.getDate() + 30); // 30 days
                
                db.run(
                    `INSERT INTO sessions (user_id, session_token, expires_at) 
                     VALUES (?, ?, ?)`,
                    [user.id, sessionToken, expiresAt.toISOString()],
                    function(err) {
                        if (err) {
                            console.error('Session creation error:', err);
                            return res.json({ success: false, error: 'Failed to create session' });
                        }
                        
                        // Update last login
                        db.run(`UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?`, [user.id]);
                        
                        res.json({
                            success: true,
                            session: {
                                token: sessionToken,
                                user_id: user.id,
                                sas_id: user.sas_id || null,
                                email: user.email,
                                name: name || user.email,
                                expires_at: expiresAt.toISOString()
                            }
                        });
                    }
                );
            }
        );
    } else if (provider === 'username' && username && password) {
        // Username/password login (SAS ID or WhatsApp)
        // TODO: Implement password validation
        res.json({ 
            success: true, 
            session: {
                token: 'mock_session_token',
                sas_id: username,
                name: 'User Name'
            }
        });
    } else {
        res.json({ success: false, error: 'Invalid login method' });
    }
});

/**
 * POST /auth/register
 * Register new user with provider
 */
router.post('/register', (req, res) => {
    const { provider, ...data } = req.body;
    
    // TODO: Implement registration logic
    // Validate provider data
    // Link to profile (SAS ID)
    // Create user account
    // Create session
    // Return session token
    
    res.json({ success: false, error: 'Not implemented' });
});

/**
 * POST /auth/logout
 * Logout user
 */
router.post('/logout', (req, res) => {
    // TODO: Implement logout
    // Invalidate session
    // Clear cookie
    
    res.json({ success: true });
});

module.exports = router;
