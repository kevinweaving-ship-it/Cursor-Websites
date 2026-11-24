#!/bin/bash
# Single-worker GSC Request-indexing processor. Does not export cookies.
set -euo pipefail
export PYTHONPATH=/opt/sailingsa-gsc
export TZ=Africa/Johannesburg
exec /var/www/sailingsa/api/venv/bin/python3 -m sailingsa.tools.gsc_daily.manual_index_worker "$@"
