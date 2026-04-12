#!/usr/bin/env bash
# Run once: all canonical, sitemap, robots, admin, redirect checks (READ-ONLY, no deploy).
# Usage: bash sailingsa/deploy/verify-canonical-and-seo-live.sh

set -e
echo "=============================================="
echo "STEP 1 — Canonical & 301"
echo "=============================================="
echo "1. Non-www → www"
curl -sI https://sailingsa.co.za
echo ""
echo "2. www → canonical"
curl -sI https://www.sailingsa.co.za
echo ""
echo "3. Sailor non-www"
curl -sI https://sailingsa.co.za/sailor/ethan-kruger-15515
echo ""
echo "4. Sailor www"
curl -sI https://www.sailingsa.co.za/sailor/ethan-kruger-15515

echo ""
echo "=============================================="
echo "STEP 2 — Canonical tag (HTML)"
echo "=============================================="
echo "Homepage canonical:"
curl -sL https://sailingsa.co.za | grep -i 'rel="canonical"' | head -3
echo "Sailor page canonical:"
curl -sL https://sailingsa.co.za/sailor/ethan-kruger-15515 | grep -i 'rel="canonical"' | head -3

echo ""
echo "=============================================="
echo "STEP 3 — Sitemap"
echo "=============================================="
curl -sI https://sailingsa.co.za/sitemap.xml
echo "Content (first 40 lines):"
curl -sL https://sailingsa.co.za/sitemap.xml | head -40

echo ""
echo "=============================================="
echo "STEP 4 — Robots.txt"
echo "=============================================="
curl -sL https://sailingsa.co.za/robots.txt

echo ""
echo "=============================================="
echo "STEP 5 — Admin noindex"
echo "=============================================="
curl -sI https://sailingsa.co.za/admin
echo "noindex in body:"
curl -sL https://sailingsa.co.za/admin 2>/dev/null | grep -i noindex || echo "(none or 403 body)"

echo ""
echo "=============================================="
echo "STEP 6 — Redirect chain"
echo "=============================================="
curl -sIL https://sailingsa.co.za

echo ""
echo "=============================================="
echo "DONE"
echo "=============================================="
