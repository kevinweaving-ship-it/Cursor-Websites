#!/usr/bin/env bash
# Live data only: SAS 1536 first_name Tim -> Timothy. Keep ID. Nickname Tim.
# See sailingsa/deploy/SSH_LIVE.md. No api.py change. No API restart.
set -euo pipefail
SERVER=102.218.215.253
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SSH_OPTS="-o StrictHostKeyChecking=no"
[ -f "$KEY" ] && SSH_OPTS="$SSH_OPTS -i $KEY"

ssh $SSH_OPTS "root@${SERVER}" 'psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -v ON_ERROR_STOP=1' <<'SQL'
BEGIN;
UPDATE public.sas_id_personal
SET first_name = 'Timothy',
    full_name = 'Timothy Kerry',
    nickname = COALESCE(NULLIF(TRIM(nickname), ''), 'Tim')
WHERE sa_sailing_id::text = '1536'
  AND last_name = 'Kerry'
  AND first_name IN ('Tim', 'Timothy');
UPDATE public.results
SET helm_name = 'Timothy Kerry'
WHERE helm_sa_sailing_id::text = '1536'
  AND helm_name IN ('Tim Kerry', 'Timothy Kerry');
UPDATE public.results
SET crew_name = 'Timothy Kerry'
WHERE crew_sa_sailing_id::text = '1536'
  AND crew_name IN ('Tim Kerry', 'Timothy Kerry');
COMMIT;
SELECT sa_sailing_id, first_name, last_name, full_name, nickname, primary_club
FROM public.sas_id_personal
WHERE sa_sailing_id::text = '1536';
SELECT result_id, helm_name, helm_sa_sailing_id
FROM public.results
WHERE helm_sa_sailing_id::text = '1536'
ORDER BY result_id;
SQL
