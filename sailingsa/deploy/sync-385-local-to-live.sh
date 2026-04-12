#!/bin/bash
# Export regatta 385 from local DB and sync to live. Keeps 385 results identical.
# Run from project root. Requires: python3, expect.
set -e
cd "$(dirname "$0")/../.."
echo "=== Export 385 from local DB ==="
python3 sailingsa/deploy/export_regatta_385_data.py
echo ""
echo "=== Sync 385 to live ==="
expect sailingsa/deploy/sync_regatta_385_to_live.exp
