#!/bin/bash
# SailingSA Deployment Script
# ONLY run this when code is tested and ready

set -e

echo "=========================================="
echo "SailingSA Deployment Script"
echo "=========================================="
echo ""
echo "WARNING: This will push to the live server!"
echo "Make sure all tests pass before continuing."
echo ""
read -p "Are you sure you want to deploy? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 1
fi

# Build frontend
echo "Building frontend..."
cd ../frontend
zip -r ../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX"

echo ""
echo "Frontend built: sailingsa-frontend.zip"
echo ""
echo "Next steps:"
echo "1. Upload sailingsa-frontend.zip to server"
echo "2. Extract to web root"
echo "3. Restart backend service"
echo ""
echo "Deployment package ready!"
