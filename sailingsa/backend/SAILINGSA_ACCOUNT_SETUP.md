# Google Account Setup for SailingSA.co.za

## Recommended: Create New Google Account

Since `sailingsa.co.za` is the real production site, create a dedicated Google account:

### Option 1: Create New Google Account (Recommended)

1. **Create Google Account:**
   - Go to: https://accounts.google.com/signup
   - Email: `admin@sailingsa.co.za` or `hello@sailingsa.co.za`
   - (You'll need email access to verify)

2. **Or use existing sailingsa.co.za email:**
   - If you already have email set up for sailingsa.co.za
   - Use that email to create Google account

### Option 2: Use Existing Account

- Use any Google account that will manage sailingsa.co.za
- Make sure you have access to it long-term

## Setup Process

1. **Login to Google Cloud Console** with the SailingSA account
2. **Select/Create Project:** "All Tim's Regatta and Stats" (or create new)
3. **Run setup script:**
   ```bash
   cd sailingsa/backend
   npm run setup-google
   ```

4. **Follow prompts** - script will guide you through:
   - Configuring OAuth consent screen
   - Creating OAuth Client ID
   - Adding redirect URIs
   - Saving credentials

## Important Notes

- **Same Client ID** works for both local and production
- **Different redirect URIs:**
  - Local: `http://localhost:3001/auth/google/callback`
  - Production: `https://sailingsa.co.za/auth/google/callback`
- **Add BOTH** in Google Cloud Console
- **Support email** should be sailingsa.co.za email (for user support)

## After Setup

Credentials are saved to `.env.local` for local development.

For production, set same credentials as environment variables on your server.
