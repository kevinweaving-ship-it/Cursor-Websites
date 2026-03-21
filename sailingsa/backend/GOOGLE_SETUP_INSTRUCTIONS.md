# Google OAuth Setup - Same for Local and Production

## How It Works

**Both local and production use REAL Google OAuth** - no dev mode, no simulation. They work exactly the same way.

The only difference is the redirect URL:
- **Local**: `http://localhost:3001/auth/google/callback`
- **Production**: `https://sailingsa.co.za/auth/google/callback`

## Setup Steps

### 1. Get Google OAuth Credentials

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
   - Name: **SailingSA** (or whatever you want)
   - **Authorized redirect URIs:** Add BOTH:
     ```
     http://localhost:3001/auth/google/callback
     https://sailingsa.co.za/auth/google/callback
     ```
   - ⚠️ **CRITICAL:** Must match EXACTLY (no trailing slash)

6. **Copy Credentials:**
   - Copy the **Client ID** (looks like: `1234567890-abc...xyz.apps.googleusercontent.com`)
   - Copy the **Client Secret**

### 2. Local Setup (.env.local)

Edit `sailingsa/backend/.env.local`:

```env
PORT=3001
FRONTEND_URL=http://localhost:8080

GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-secret
GOOGLE_CALLBACK_URL=http://localhost:3001/auth/google/callback

SESSION_SECRET=local-dev-secret
```

### 3. Production Setup (Server Environment Variables)

Set these on your live server (NOT in .env.local):

```env
PORT=3001
FRONTEND_URL=https://sailingsa.co.za

GOOGLE_CLIENT_ID=same-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=same-secret
GOOGLE_CALLBACK_URL=https://sailingsa.co.za/auth/google/callback

SESSION_SECRET=production-secret-different-from-local
NODE_ENV=production
```

### 4. Restart Backend

**Local:**
```bash
cd sailingsa/backend
# Kill existing process, then:
node server.js
```

**Production:**
```bash
# Restart your server process (PM2, systemd, etc.)
pm2 restart sailingsa-backend
# or
sudo systemctl restart sailingsa-backend
```

## Testing

1. **Local:** Open `http://localhost:8080/timadvisor/login.html`
2. Click "Sign in with Google"
3. Should redirect to Google consent screen
4. After consent, redirects back to your app

**Production:** Same flow, just different URLs.

## Important Notes

- **Use the SAME Client ID** for both local and production (just add both redirect URIs)
- **Different redirect URLs** - one for localhost, one for production domain
- **Same code, same flow** - no differences between local and production
- **Real Google OAuth** - no simulation, no dev mode

## Troubleshooting

**Error: "invalid_client"**
- Check Client ID is correct (no typos)
- Check redirect URI matches EXACTLY in Google Cloud Console
- Make sure you added BOTH redirect URIs (localhost and production)

**Error: "redirect_uri_mismatch"**
- Redirect URI in code must match EXACTLY what's in Google Cloud Console
- No trailing slashes
- Correct protocol (http for localhost, https for production)
