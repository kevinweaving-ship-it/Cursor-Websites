#!/bin/bash
# First-run GSC daily pull. Mac Mini only. No website changes. No secrets copied.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "STOP: run this on Kevin's Mac Mini (authenticated Chrome), not Cloud/Linux."
  exit 2
fi
mkdir -p "$HOME/Library/Application Support/sailingsa/gsc-daily"
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
python3 -m sailingsa.tools.gsc_daily.run_daily "$@"
