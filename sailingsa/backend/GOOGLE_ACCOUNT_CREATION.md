# Google Account Creation for sailingsa.co.za

## Automated Setup

I've opened the Google signup page and attempted to auto-fill the form.

## What You Need to Do:

1. **Complete the form** (may be partially filled):
   - First name: **SailingSA**
   - Last name: **Admin**
   - Username: **admin@sailingsa.co.za** (or try hello@sailingsa.co.za if taken)
   - Password: **Create a strong password** (save it securely!)

2. **Complete CAPTCHA** (required - can't automate this)

3. **Verify email**:
   - Google will send verification to admin@sailingsa.co.za
   - You need access to that email inbox
   - Click verification link

4. **Complete setup**:
   - Add phone number (if required)
   - Accept terms
   - Account created!

## After Account Creation:

Run this to set up OAuth:
```bash
cd sailingsa/backend
npm run setup-google
```

## Important Notes:

- **Email access required**: You must have access to admin@sailingsa.co.za email
- **Password**: Save it securely - you'll need it for Google Cloud Console
- **Same account**: Use this account for both local and production OAuth

## If Email Not Available:

If you don't have email set up for sailingsa.co.za yet:
1. Set up email first (via your hosting provider)
2. Then create Google account
3. Or use a different email you control (but less ideal)
