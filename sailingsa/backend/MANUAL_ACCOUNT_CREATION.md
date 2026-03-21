# Manual Google Account Creation - NO AUTOMATION

## ⚠️ CRITICAL: Create Account 100% Manually

Google detected automation and disabled the account. You MUST create the next account completely manually.

## Steps (Do Everything Yourself):

1. **Open browser manually**: Go to https://accounts.google.com/signup
2. **Fill form manually**:
   - First name: SailingSA
   - Last name: Admin  
   - Username: Try `sailingsaadmin@gmail.com` or similar
   - Password: Type manually (strong password)
3. **Complete CAPTCHA manually** - click/tap yourself
4. **Verify email manually** - check inbox yourself
5. **Complete all steps manually** - no scripts, no automation

## After Account Created:

1. **Login to Google Cloud Console** with new account
2. **Run setup**:
   ```bash
   cd sailingsa/backend
   npm run setup-google
   ```

## Why Manual?

- Google's security detects automation
- Automated accounts get disabled immediately
- Manual creation = account stays active
- Takes 2 minutes manually vs hours of appeals

## Alternative: Use Existing Account

If you have another Google account you control:
- Use that for now
- Can create dedicated account later
- OAuth will work the same
