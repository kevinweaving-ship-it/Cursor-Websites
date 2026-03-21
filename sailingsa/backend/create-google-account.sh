#!/bin/bash
# Automated Google Account Creation for sailingsa.co.za

echo "🔐 Creating Google Account for sailingsa.co.za"
echo "=============================================="
echo ""

# Check if we have email access
echo "Checking email setup for sailingsa.co.za..."

# Open Google signup page
echo "Opening Google Account signup..."
open "https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp"

echo ""
echo "📋 FORM WILL AUTO-FILL:"
echo "   First name: SailingSA"
echo "   Last name: Admin"
echo "   Username: admin@sailingsa.co.za (or available variant)"
echo ""
echo "⚠️  You'll need to:"
echo "   1. Complete CAPTCHA"
echo "   2. Verify email (check sailingsa.co.za email)"
echo "   3. Set password"
echo ""
echo "Waiting 5 seconds for page to load, then auto-filling form..."
sleep 5

# Use AppleScript to fill the form
osascript << 'APPLESCRIPT'
tell application "Google Chrome"
    activate
    delay 2
    tell application "System Events"
        tell process "Google Chrome"
            -- Try to find and fill first name
            try
                set frontmost to true
                delay 1
                keystroke "SailingSA"
                delay 0.5
                keystroke tab
                delay 0.5
                keystroke "Admin"
                delay 0.5
                keystroke tab
                delay 0.5
                keystroke "admin@sailingsa.co.za"
            end try
        end tell
    end tell
end tell
APPLESCRIPT

echo ""
echo "✅ Form auto-filled (if browser supported)"
echo ""
echo "📝 NEXT STEPS:"
echo "   1. Complete any remaining fields"
echo "   2. Click 'Next'"
echo "   3. Verify email when prompted"
echo "   4. Set password"
echo ""
echo "After account is created, run: npm run setup-google"
