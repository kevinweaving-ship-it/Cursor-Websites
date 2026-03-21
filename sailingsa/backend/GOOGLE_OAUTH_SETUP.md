# Google OAuth Setup Guide

## ✅ What's Been Done

1. **Backend OAuth Flow Implemented**
   - Added Passport.js with Google OAuth strategy
   - Created `/auth/google` endpoint to initiate OAuth
   - Created `/auth/google/callback` endpoint to handle callback
   - Frontend now redirects to backend (no client-side OAuth)

2. **Dependencies Added**
   - `passport`
   - `passport-google-oauth20`
   - `express-session`

3. **Configuration Files**
   - `.env.local.example` created with required variables

## 🔧 Setup Steps

### Step 1: Install Dependencies

```bash
cd sailingsa/backend
npm install passport passport-google-oauth20 express-session
```

### Step 2: Google Cloud Console Setup

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
   - Name: **SailingSA Local Dev**
   - **Authorized redirect URIs:**
     ```
     http://localhost:3001/auth/google/callback
     ```
   - ⚠️ **CRITICAL:** Must match EXACTLY (no trailing slash, correct port)

6. **Copy Credentials:**
   - Copy the **Client ID** (looks like: `1234567890-abc...xyz.apps.googleusercontent.com`)
   - Copy the **Client Secret**

### Step 3: Configure Backend

1. **Create `.env.local` file:**
   ```bash
   cd sailingsa/backend
   cp .env.local.example .env.local
   ```

2. **Edit `.env.local` and add:**
   ```env
   PORT=3001
   
   GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-actual-client-secret
   GOOGLE_CALLBACK_URL=http://localhost:3001/auth/google/callback
   
   SESSION_SECRET=generate-a-random-string-here
   FRONTEND_URL=http://localhost:8080
   ```

3. **Generate SESSION_SECRET:**
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   ```
   Copy the output to `SESSION_SECRET` in `.env.local`

### Step 4: Restart Backend

```bash
cd sailingsa/backend
npm start
# or for development:
npm run dev
```

### Step 5: Test

1. Open `http://localhost:8080/timadvisor/login.html`
2. Click "Sign in with Google"
3. You should see:
   - Redirect to Google consent screen
   - After consent, redirect back to login page
   - Success message or registration flow

## 🔍 Troubleshooting

### Error: "invalid_client" or "OAuth client was not found"
- ✅ Check Client ID is correct in `.env.local`
- ✅ Check redirect URI matches EXACTLY: `http://localhost:3001/auth/google/callback`
- ✅ Ensure OAuth consent screen is configured
- ✅ Restart backend after changing `.env.local`

### Error: "redirect_uri_mismatch"
- ✅ Check redirect URI in Google Cloud Console matches exactly
- ✅ No trailing slash
- ✅ Correct port (3001)
- ✅ Correct protocol (http for localhost)

### Backend won't start
- ✅ Run `npm install` first
- ✅ Check `.env.local` exists and has all required variables
- ✅ Check port 3001 is not already in use

## 📝 Notes

- **Frontend no longer needs Google Client ID** - backend handles everything
- **No Google SDK needed in frontend** - removed from login.html
- **Backend redirects to frontend** after OAuth completes
- **Session stored in cookie** and localStorage for frontend access

## 🚀 Production Setup

When deploying to production:

1. Create new OAuth Client ID in Google Cloud Console
2. Add production redirect URI:
   ```
   https://sailingsa.co.za/auth/google/callback
   ```
3. Update `.env.local` (or production env vars):
   ```env
   GOOGLE_CALLBACK_URL=https://sailingsa.co.za/auth/google/callback
   FRONTEND_URL=https://sailingsa.co.za
   SESSION_SECRET=<strong-random-secret>
   ```
4. Set `secure: true` in cookie settings (requires HTTPS)
