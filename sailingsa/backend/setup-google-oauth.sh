#!/bin/bash
# Automated Google OAuth Setup Script

echo "🔐 Google OAuth Setup - Automated"
echo "=================================="
echo ""

# Check if .env.local exists
ENV_FILE=".env.local"
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env.local from example..."
    cp .env.local.example .env.local
fi

echo "Step 1: Opening Google Cloud Console..."
echo "You need to:"
echo "  1. Create/Select a project"
echo "  2. Enable Google Identity Services API"
echo "  3. Configure OAuth Consent Screen"
echo "  4. Create OAuth Client ID (Web application)"
echo "  5. Add redirect URI: http://localhost:3001/auth/google/callback"
echo ""

# Open Google Cloud Console
open "https://console.cloud.google.com/apis/credentials?project=_"

echo ""
echo "Waiting for you to create credentials..."
echo "Press Enter when you have your Client ID and Secret..."
read

echo ""
echo "Enter your Google OAuth Client ID:"
read -r CLIENT_ID

echo "Enter your Google OAuth Client Secret:"
read -r CLIENT_SECRET

# Update .env.local
sed -i '' "s|GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$CLIENT_ID|" "$ENV_FILE"
sed -i '' "s|GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$CLIENT_SECRET|" "$ENV_FILE"
sed -i '' "s|GOOGLE_CALLBACK_URL=.*|GOOGLE_CALLBACK_URL=http://localhost:3001/auth/google/callback|" "$ENV_FILE"

echo ""
echo "✅ Credentials saved to .env.local"
echo ""
echo "Restarting backend..."
pkill -f "node server.js" 2>/dev/null
sleep 2

# Start backend
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
node server.js > /tmp/sailingsa-backend.log 2>&1 &
echo $! > /tmp/sailingsa-backend.pid

sleep 3
echo ""
echo "✅ Backend restarted"
echo ""
echo "Test: curl http://localhost:3001/auth/google"
echo ""
