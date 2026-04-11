#!/bin/bash
# SailingSA Beta V1 — Push frontend to cloud (sailingsa.co.za)
# Uses same server as timadvisor. Requires SSH access.
# Run from project root: ./sailingsa/deploy/push-to-cloud.sh

set -e

SERVER_IP="${SAILINGSA_SERVER:-102.218.215.253}"
SERVER_USER="${SAILINGSA_USER:-root}"
# Path where sailingsa.co.za is served (nginx root). Override: export SAILINGSA_WEB_ROOT=/var/www/sailingsa.co.za
WEB_ROOT="${SAILINGSA_WEB_ROOT:-/var/www/sailingsa}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ZIP_PATH="$PROJECT_ROOT/sailingsa-frontend.zip"

echo "=========================================="
echo "SailingSA Beta V1 — Push to Cloud"
echo "=========================================="
echo "Server: $SERVER_USER@$SERVER_IP"
echo "Web root: $WEB_ROOT"
echo ""

# Step 1: Build frontend zip
echo "Step 1: Building frontend zip..."
cd "$PROJECT_ROOT/sailingsa/frontend"
rm -f "$ZIP_PATH"
zip -r "$ZIP_PATH" . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md" -x "data/hub_hero.json"
echo "  Built: $ZIP_PATH"
echo ""

# Step 2: Test connection
echo "Step 2: Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER_USER@$SERVER_IP" "echo '  OK' && hostname"
echo ""

# Step 3: Backup on server
echo "Step 3: Backing up current web root..."
ssh "$SERVER_USER@$SERVER_IP" "if [ -d $WEB_ROOT ]; then B=\$(date +%Y%m%d); sudo cp -a $WEB_ROOT ${WEB_ROOT}.backup.\$B && echo '  Backup: ${WEB_ROOT}.backup.'\$B; else echo '  No existing dir (first deploy)'; sudo mkdir -p $WEB_ROOT; fi"
echo ""

# Step 4: Upload zip
echo "Step 4: Uploading sailingsa-frontend.zip..."
scp -o StrictHostKeyChecking=no "$ZIP_PATH" "$SERVER_USER@$SERVER_IP:/tmp/sailingsa-frontend.zip"
echo "  Uploaded"
echo ""

# Step 5: Extract on server
echo "Step 5: Extracting to web root..."
ssh "$SERVER_USER@$SERVER_IP" "cd $WEB_ROOT && unzip -o /tmp/sailingsa-frontend.zip && rm /tmp/sailingsa-frontend.zip && ls -la index.html robots.txt sitemap.xml 2>/dev/null || ls -la index.html"
echo "  Extracted"
echo ""

# Step 6: Fix ownership (if www-data exists)
echo "Step 6: Setting ownership..."
ssh "$SERVER_USER@$SERVER_IP" "chown -R www-data:www-data $WEB_ROOT 2>/dev/null || true"
echo ""

echo "=========================================="
echo "Frontend deploy complete."
echo "=========================================="
echo ""
echo "REQUIRED: Apply nginx robots/sitemap fix (Step 10b) if not done:"
echo "  Add location = /robots.txt and location = /sitemap.xml blocks before location /"
echo "  See: docs/SAILINGSA_BETA_PUBLISHING.md"
echo ""
echo "Then on server:"
echo "  nginx -t && sudo systemctl reload nginx"
echo ""
echo "Run Step C smoke + SEO checks: https://sailingsa.co.za/"
echo ""
