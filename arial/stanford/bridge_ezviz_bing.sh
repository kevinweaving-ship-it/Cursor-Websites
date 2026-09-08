#!/bin/bash
# Same as Bing Carport /opt/ezvizpoc/bridge_ezviz.sh, plus decrypt for Stanford EB5s.
# Usage: bridge_ezviz_bing.sh <serial>
set -a
. /opt/ezvizpoc/.env
set +a
export EZVIZ_USERNAME="$EZVIZ_ACCOUNT"
exec /opt/hikpoc/venv/bin/python -m pyezvizapi -r "${EZVIZ_API_URL:-apiieu.ezvizlife.com}" --token-file /opt/ezvizpoc/token.json --save-token \
  stream dump --serial "$1" --format raw --decrypt-video --output - \
  2>>"/opt/ezvizpoc/out/bridge_$1.log"
