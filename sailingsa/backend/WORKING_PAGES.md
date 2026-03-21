# Pages We're Working On

## Local Development:

1. **Login Page**: http://localhost:8080/timadvisor/login.html
   - Google OAuth login
   - Registration flow
   - Main page we're testing

2. **TimAdvisor Home**: http://localhost:8080/timadvisor/index.html
   - Main site
   - "Your Sailing Results" button

3. **Backend API**: http://localhost:3001
   - Health check: http://localhost:3001/health
   - OAuth: http://localhost:3001/auth/google
   - Session: http://localhost:3001/auth/session

## Google Cloud Console:

4. **OAuth Credentials**: https://console.cloud.google.com/apis/credentials?project=all-tims-regatta-and-stats
   - Create OAuth Client ID
   - Configure redirect URIs
   - Get credentials for setup

## Quick Access:

```bash
# Open login page
open http://localhost:8080/timadvisor/login.html

# Check backend
curl http://localhost:3001/health

# Restart backend
cd sailingsa/backend && npm start
```
