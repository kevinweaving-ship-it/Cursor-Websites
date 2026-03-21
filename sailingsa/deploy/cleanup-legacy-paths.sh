#!/bin/bash
# STEP 5: Delete legacy structure on server
# Run: ssh root@102.218.215.253 "bash -s" < sailingsa/deploy/cleanup-legacy-paths.sh
# Or manually:
#   ssh root@102.218.215.253
#   rm -rf /var/www/sailingsa/sailingsa
#   rm -rf /var/www/sailingsa/frontend

set -e
echo "Removing legacy paths..."
rm -rf /var/www/sailingsa/sailingsa 2>/dev/null || true
rm -rf /var/www/sailingsa/frontend 2>/dev/null || true
echo "Done. Verify: curl -I https://sailingsa.co.za/sailingsa/frontend/login.html  (must return 404)"
