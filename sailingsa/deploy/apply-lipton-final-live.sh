#!/usr/bin/env bash
# Apply official Lipton 2026 final scores + Final status on live DB.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER="${DEPLOY_SERVER:-root@102.218.215.253}"
DBURL="${DB_URL:-postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master}"
TS="$(date +%Y%m%d_%H%M%S)"
SQL="/tmp/lipton_final_${TS}.sql"

python3 "$ROOT/sailingsa/deploy/apply_lipton_final_results.py" >"$SQL"
echo "Generated $SQL ($(wc -l <"$SQL") lines)"

ssh_cmd() {
  if [[ -n "${SSHPASS:-}" ]] && command -v sshpass >/dev/null 2>&1; then
    sshpass -e ssh -o StrictHostKeyChecking=no "$@"
  elif [[ -f "${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}" ]]; then
    ssh -i "${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}" -o StrictHostKeyChecking=no "$@"
  else
    ssh -o StrictHostKeyChecking=no "$@"
  fi
}

scp_cmd() {
  if [[ -n "${SSHPASS:-}" ]] && command -v sshpass >/dev/null 2>&1; then
    sshpass -e scp -o StrictHostKeyChecking=no "$@"
  elif [[ -f "${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}" ]]; then
    scp -i "${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}" -o StrictHostKeyChecking=no "$@"
  else
    scp -o StrictHostKeyChecking=no "$@"
  fi
}

echo "=== Backup proof row (J-Walker) before ==="
ssh_cmd "$SERVER" "psql '$DBURL' -t -A -c \"SELECT result_id, race_scores FROM results WHERE regatta_id='2026-08-29-lipton-challenge-cup' AND sail_number='173';\""

scp_cmd "$SQL" "$SERVER:/tmp/lipton_final.sql"
echo "=== Apply SQL on live ==="
ssh_cmd "$SERVER" "psql '$DBURL' -f /tmp/lipton_final.sql"

echo "=== Verify regatta status ==="
ssh_cmd "$SERVER" "psql '$DBURL' -c \"SELECT regatta_id, result_status, as_at_time FROM regattas WHERE regatta_id='2026-08-29-lipton-challenge-cup';\""

echo "=== Verify J-Walker race_scores ==="
ssh_cmd "$SERVER" "psql '$DBURL' -t -A -c \"SELECT race_scores FROM results WHERE regatta_id='2026-08-29-lipton-challenge-cup' AND sail_number='173';\""

echo "=== Live page status line ==="
curl -sf "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup" | rg -o 'Results are[^<]+' | head -1

echo "Done."
