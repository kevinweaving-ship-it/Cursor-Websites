# Environment Variables Setup

## Core Rule
**Same codebase works locally and live - all config from environment variables**

## Local Development (.env.local)

Create `sailingsa/backend/.env.local`:

```env
PORT=3001
FRONTEND_URL=http://localhost:8080

GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CALLBACK_URL=http://localhost:3001/auth/google/callback

SESSION_SECRET=generate-random-string-here
```

## Live Server (Environment Variables)

Set these on your server (NOT in .env.local):

```env
PORT=3001
FRONTEND_URL=https://sailingsa.co.za

GOOGLE_CLIENT_ID=same-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=same-client-secret
GOOGLE_CALLBACK_URL=https://sailingsa.co.za/auth/google/callback

SESSION_SECRET=different-strong-random-string-for-production
```

## Important Notes

1. **Same Google Client ID** - Use the SAME Client ID for local and live
2. **Different Redirect URIs** - Add BOTH in Google Cloud Console:
   - `http://localhost:3001/auth/google/callback` (local)
   - `https://sailingsa.co.za/auth/google/callback` (live)
3. **No .env.local on live** - Server environment variables only
4. **No hardcoded values** - All config comes from environment

## Verification

After setting environment variables:

1. Restart backend
2. Check console logs - should show "Google OAuth configured" with callback URL
3. Test `/auth/google` endpoint - should redirect to Google consent screen
