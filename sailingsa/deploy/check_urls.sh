#!/bin/bash
# URL health check for sailingsa.co.za — run from repo root: bash sailingsa/deploy/check_urls.sh
set -e

BASE="${SAILINGSA_BASE:-https://sailingsa.co.za}"

URLS=(
"/"
"/index.html"
"/login.html"
"/signup.html"
"/regatta_viewer.html"
"/events"
"/stats"
"/clubs"
"/classes"
"/about"
"/admin/dashboard"
"/sailor/1"
"/regatta/1"
)

echo "Checking URLs (BASE=$BASE)..."
echo ""

for url in "${URLS[@]}"; do
  code=$(curl -o /dev/null -s -w "%{http_code}" --connect-timeout 15 "$BASE$url" || echo "000")
  echo "$code  $url"
done

echo ""
echo "--- sitemap.xml (first 30 lines) ---"
curl -sS --connect-timeout 15 "$BASE/sitemap.xml" | head -30
echo ""
echo "(full sitemap: curl -s $BASE/sitemap.xml | wc -c bytes)"
