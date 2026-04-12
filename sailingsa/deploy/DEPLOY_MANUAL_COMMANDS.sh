#!/bin/bash
# Run from project root. You will be prompted for SSH password.
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "1. Frontend zip already built: sailingsa-frontend.zip"

echo "2. SCP zip to live server..."
scp -o StrictHostKeyChecking=no sailingsa-frontend.zip root@102.218.215.253:/tmp/sailingsa-frontend.zip

echo "3–5. SSH: extract and reload nginx..."
ssh -o StrictHostKeyChecking=no root@102.218.215.253 "cd /var/www/sailingsa && unzip -o /tmp/sailingsa-frontend.zip && systemctl reload nginx && echo Done."

echo "6. Exit (script ends)."
