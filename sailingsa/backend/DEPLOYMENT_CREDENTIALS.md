# Setting Google OAuth Credentials for Live/Cloud Server

## Important: Dev Mode vs Production

- **Local Development**: Dev mode simulates Google OAuth when credentials aren't set (for testing)
- **Live/Production**: **MUST** have real Google OAuth credentials - dev mode is disabled

## For Live/Cloud Server

### Step 1: Get Google OAuth Credentials

1. Go to https://console.cloud.google.com/
2. Select your project (or create one)
3. **Enable APIs:**
   - APIs & Services → Library
   - Enable "Google Identity Services"
   - Enable "Google OAuth2 API"

4. **Configure OAuth Consent Screen:**
   - APIs & Services → OAuth consent screen
   - User type: **External**
   - App name: **SailingSA Results**
   - Support email: Your email
   - Developer contact email: Your email
   - Scopes: `openid`, `email`, `profile`

5. **Create OAuth Client ID:**
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web application**
   - Name: **SailingSA Production**
   - **Authorized redirect URIs:**
     ```
     https://sailingsa.co.za/auth/google/callback
     ```
   - ⚠️ **CRITICAL:** Must match EXACTLY (no trailing slash, correct domain)

6. **Copy Credentials:**
   - Copy the **Client ID** (looks like: `1234567890-abc...xyz.apps.googleusercontent.com`)
   - Copy the **Client Secret**

### Step 2: Set Environment Variables on Live Server

**DO NOT** use `.env.local` on the live server. Set environment variables directly on the server:

#### Option A: Using PM2 (if you use PM2)
```bash
pm2 set GOOGLE_CLIENT_ID "your-actual-client-id.apps.googleusercontent.com"
pm2 set GOOGLE_CLIENT_SECRET "your-actual-secret"
pm2 set GOOGLE_CALLBACK_URL "https://sailingsa.co.za/auth/google/callback"
pm2 set FRONTEND_URL "https://sailingsa.co.za"
pm2 restart sailingsa-backend
```

#### Option B: Using systemd service file
Edit `/etc/systemd/system/sailingsa-backend.service`:
```ini
[Service]
Environment="GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com"
Environment="GOOGLE_CLIENT_SECRET=your-actual-secret"
Environment="GOOGLE_CALLBACK_URL=https://sailingsa.co.za/auth/google/callback"
Environment="FRONTEND_URL=https://sailingsa.co.za"
Environment="NODE_ENV=production"
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart sailingsa-backend
```

#### Option C: Using .env file (if your deployment supports it)
Create `.env` file (NOT `.env.local`) on the server:
```env
NODE_ENV=production
PORT=3001
FRONTEND_URL=https://sailingsa.co.za

GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-secret
GOOGLE_CALLBACK_URL=https://sailingsa.co.za/auth/google/callback

SESSION_SECRET=strong-random-secret-for-production
```

### Step 3: Verify

After setting credentials and restarting:

1. Check backend logs - should show "Google OAuth configured" (not dev mode warning)
2. Test: `curl https://sailingsa.co.za/auth/google`
   - Should redirect to Google consent screen (not error)
3. Complete OAuth flow - should work end-to-end

## Security Notes

- **Never commit credentials to git**
- **Use different Client IDs for local vs production** (or same ID with both redirect URIs)
- **Session secret must be different** for production
- **Set `NODE_ENV=production`** on live server (disables dev mode)

## Same Client ID for Both?

You can use the **same Google Client ID** for local and production by adding **both** redirect URIs in Google Cloud Console:
- `http://localhost:3001/auth/google/callback` (local)
- `https://sailingsa.co.za/auth/google/callback` (production)

This is the recommended approach - one Client ID, multiple redirect URIs.
