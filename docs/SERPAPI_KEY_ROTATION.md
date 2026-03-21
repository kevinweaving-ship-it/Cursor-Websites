# SerpAPI Key Rotation Instructions

## ⚠️ IMPORTANT SECURITY NOTE

**The previous API key was exposed and should be considered compromised.**

## Steps to Rotate and Secure the Key

### Step 1: Regenerate API Key (Do this FIRST)

1. Go to SerpAPI Dashboard: https://serpapi.com/dashboard
2. Navigate to API Keys section
3. **Regenerate / Rotate** the exposed API key immediately
4. **DO NOT paste the new key in chat or any public location**

### Step 2: Add New Key to Project (Local Only)

#### Step 2A — Update .env file

1. Open your project folder
2. Find (or create) `.env` file in project root: `/Users/kevinweaving/Desktop/MyProjects_Local/Project 6/.env`
3. Update the line with your NEW key:
   ```
   SERPAPI_API_KEY=your_new_key_here
   ```
4. Save the file

#### Step 2B — Restart Backend

1. Stop the backend server (if running)
2. Start it again (so it loads the new env var)
3. The new key will be loaded automatically

## Current Status

- ✅ Old key has been stored in `.env` (but should be replaced)
- ⚠️ Old key should be considered compromised
- ⏳ Waiting for new key to be added after rotation

## Security Best Practices

- Never commit `.env` file to git (already in `.gitignore`)
- Never paste API keys in chat, logs, or public locations
- Rotate keys immediately if exposed
- Use environment variables, never hardcode keys
